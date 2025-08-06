#!/usr/bin/env python3
"""
JARVIS-MK42 Scalability Manager
==============================

This module provides comprehensive scalability management including:
- Load balancing with multiple strategies (round-robin, least-connections, weighted)
- Horizontal scaling preparation and multi-instance coordination
- Resource pooling for connections, threads, and processes
- Auto-scaling triggers based on system metrics
- Queue management for high-load scenarios
- Instance health monitoring and failover
"""

import os
import sys
import json
import time
import asyncio
import threading
import multiprocessing
from datetime import datetime, timedelta
from typing import Dict, List, Optional, Any, Callable, Union, Tuple
from dataclasses import dataclass, field
from enum import Enum
from collections import defaultdict, deque
from concurrent.futures import ThreadPoolExecutor, ProcessPoolExecutor, Future
from queue import Queue, PriorityQueue, Empty
from contextlib import contextmanager
import socket
import psutil
import weakref
import uuid

# Add project root to path
current_dir = os.path.dirname(os.path.abspath(__file__))
project_root = os.path.dirname(current_dir)
if project_root not in sys.path:
    sys.path.insert(0, project_root)

from utils.logging_config import get_logger

logger = get_logger(__name__)


class LoadBalancingStrategy(Enum):
    """Load balancing strategies"""
    ROUND_ROBIN = "round_robin"
    LEAST_CONNECTIONS = "least_connections"
    WEIGHTED_ROUND_ROBIN = "weighted_round_robin"
    LEAST_RESPONSE_TIME = "least_response_time"
    RESOURCE_BASED = "resource_based"
    ADAPTIVE = "adaptive"


class ScalingTrigger(Enum):
    """Auto-scaling trigger types"""
    CPU_USAGE = "cpu_usage"
    MEMORY_USAGE = "memory_usage"
    REQUEST_RATE = "request_rate"
    QUEUE_LENGTH = "queue_length"
    RESPONSE_TIME = "response_time"
    CUSTOM_METRIC = "custom_metric"


class InstanceStatus(Enum):
    """Instance status states"""
    HEALTHY = "healthy"
    DEGRADED = "degraded"
    UNHEALTHY = "unhealthy"
    STARTING = "starting"
    STOPPING = "stopping"
    MAINTENANCE = "maintenance"


@dataclass
class ServiceInstance:
    """Represents a service instance"""
    instance_id: str
    host: str
    port: int
    weight: float = 1.0
    status: InstanceStatus = InstanceStatus.STARTING
    active_connections: int = 0
    total_requests: int = 0
    total_response_time: float = 0.0
    last_health_check: datetime = field(default_factory=datetime.now)
    failure_count: int = 0
    metadata: Dict[str, Any] = field(default_factory=dict)
    
    @property
    def avg_response_time(self) -> float:
        """Calculate average response time"""
        if self.total_requests == 0:
            return 0.0
        return self.total_response_time / self.total_requests
    
    @property
    def is_available(self) -> bool:
        """Check if instance is available for requests"""
        return self.status in [InstanceStatus.HEALTHY, InstanceStatus.DEGRADED]
    
    def update_metrics(self, response_time: float):
        """Update instance metrics"""
        self.total_requests += 1
        self.total_response_time += response_time
        
        # Update status based on performance
        if response_time > 5.0:  # 5 second threshold
            if self.status == InstanceStatus.HEALTHY:
                self.status = InstanceStatus.DEGRADED
        elif self.status == InstanceStatus.DEGRADED and response_time < 1.0:
            self.status = InstanceStatus.HEALTHY


@dataclass
class ScalingRule:
    """Auto-scaling rule configuration"""
    trigger: ScalingTrigger
    threshold_up: float
    threshold_down: float
    scale_up_count: int = 1
    scale_down_count: int = 1
    cooldown_seconds: int = 300
    evaluation_periods: int = 3
    enabled: bool = True
    last_action: Optional[datetime] = None


@dataclass
class ResourcePool:
    """Resource pool configuration and state"""
    pool_type: str
    min_size: int
    max_size: int
    current_size: int = 0
    active_resources: int = 0
    total_created: int = 0
    total_destroyed: int = 0
    creation_time_sum: float = 0.0
    
    @property
    def utilization_rate(self) -> float:
        """Calculate resource utilization rate"""
        if self.current_size == 0:
            return 0.0
        return self.active_resources / self.current_size
    
    @property
    def avg_creation_time(self) -> float:
        """Calculate average resource creation time"""
        if self.total_created == 0:
            return 0.0
        return self.creation_time_sum / self.total_created


class LoadBalancer:
    """Load balancer with multiple strategies"""
    
    def __init__(self, strategy: LoadBalancingStrategy = LoadBalancingStrategy.ROUND_ROBIN):
        self.strategy = strategy
        self.instances: Dict[str, ServiceInstance] = {}
        self.round_robin_counter = 0
        self._lock = threading.RLock()
        self.health_check_interval = 30  # seconds
        self._health_check_thread: Optional[threading.Thread] = None
        self._running = False
    
    def add_instance(self, instance: ServiceInstance):
        """Add service instance to load balancer"""
        with self._lock:
            self.instances[instance.instance_id] = instance
            logger.info(f"Added instance {instance.instance_id} at {instance.host}:{instance.port}")
    
    def remove_instance(self, instance_id: str):
        """Remove service instance from load balancer"""
        with self._lock:
            if instance_id in self.instances:
                del self.instances[instance_id]
                logger.info(f"Removed instance {instance_id}")
    
    def get_next_instance(self) -> Optional[ServiceInstance]:
        """Get next instance based on load balancing strategy"""
        with self._lock:
            available_instances = [
                instance for instance in self.instances.values()
                if instance.is_available
            ]
            
            if not available_instances:
                return None
            
            if self.strategy == LoadBalancingStrategy.ROUND_ROBIN:
                selected = available_instances[self.round_robin_counter % len(available_instances)]
                self.round_robin_counter += 1
                return selected
            
            elif self.strategy == LoadBalancingStrategy.LEAST_CONNECTIONS:
                return min(available_instances, key=lambda x: x.active_connections)
            
            elif self.strategy == LoadBalancingStrategy.WEIGHTED_ROUND_ROBIN:
                # Select based on weights
                total_weight = sum(inst.weight for inst in available_instances)
                if total_weight == 0:
                    return available_instances[0]
                
                # Weighted random selection
                import random
                target = random.uniform(0, total_weight)
                current = 0
                for instance in available_instances:
                    current += instance.weight
                    if current >= target:
                        return instance
                return available_instances[-1]
            
            elif self.strategy == LoadBalancingStrategy.LEAST_RESPONSE_TIME:
                return min(available_instances, key=lambda x: x.avg_response_time)
            
            elif self.strategy == LoadBalancingStrategy.RESOURCE_BASED:
                # Select based on CPU/memory usage (if available in metadata)
                def resource_score(instance):
                    cpu = instance.metadata.get('cpu_usage', 50.0)
                    memory = instance.metadata.get('memory_usage', 50.0)
                    return cpu * 0.6 + memory * 0.4
                
                return min(available_instances, key=resource_score)
            
            else:  # ADAPTIVE
                # Combine multiple factors
                def adaptive_score(instance):
                    connections = instance.active_connections * 10
                    response_time = instance.avg_response_time * 1000  # ms
                    cpu = instance.metadata.get('cpu_usage', 50.0)
                    failure_rate = instance.failure_count * 100
                    
                    return connections + response_time + cpu + failure_rate
                
                return min(available_instances, key=adaptive_score)
    
    def report_request_complete(self, instance_id: str, response_time: float, success: bool):
        """Report completed request metrics"""
        with self._lock:
            instance = self.instances.get(instance_id)
            if instance:
                instance.active_connections = max(0, instance.active_connections - 1)
                if success:
                    instance.update_metrics(response_time)
                    instance.failure_count = max(0, instance.failure_count - 1)
                else:
                    instance.failure_count += 1
    
    def report_request_start(self, instance_id: str):
        """Report request start"""
        with self._lock:
            instance = self.instances.get(instance_id)
            if instance:
                instance.active_connections += 1
    
    def start_health_checks(self):
        """Start health checking thread"""
        if self._running:
            return
        
        self._running = True
        self._health_check_thread = threading.Thread(target=self._health_check_loop, daemon=True)
        self._health_check_thread.start()
        logger.info("Load balancer health checks started")
    
    def stop_health_checks(self):
        """Stop health checking"""
        self._running = False
        if self._health_check_thread:
            self._health_check_thread.join()
    
    def _health_check_loop(self):
        """Health check monitoring loop"""
        while self._running:
            try:
                with self._lock:
                    for instance in self.instances.values():
                        self._check_instance_health(instance)
                
                time.sleep(self.health_check_interval)
                
            except Exception as e:
                logger.error(f"Error in health check loop: {e}")
                time.sleep(10)
    
    def _check_instance_health(self, instance: ServiceInstance):
        """Check health of individual instance"""
        try:
            # Simple TCP connectivity check
            sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
            sock.settimeout(5.0)
            result = sock.connect_ex((instance.host, instance.port))
            sock.close()
            
            if result == 0:
                # Connection successful
                if instance.status == InstanceStatus.UNHEALTHY:
                    instance.status = InstanceStatus.HEALTHY
                    instance.failure_count = 0
                    logger.info(f"Instance {instance.instance_id} recovered")
            else:
                # Connection failed
                instance.failure_count += 1
                if instance.failure_count >= 3:
                    if instance.status != InstanceStatus.UNHEALTHY:
                        instance.status = InstanceStatus.UNHEALTHY
                        logger.warning(f"Instance {instance.instance_id} marked unhealthy")
            
            instance.last_health_check = datetime.now()
            
        except Exception as e:
            logger.error(f"Health check failed for {instance.instance_id}: {e}")
            instance.failure_count += 1
    
    def get_status(self) -> Dict[str, Any]:
        """Get load balancer status"""
        with self._lock:
            instances_by_status = defaultdict(int)
            for instance in self.instances.values():
                instances_by_status[instance.status.value] += 1
            
            total_requests = sum(inst.total_requests for inst in self.instances.values())
            total_connections = sum(inst.active_connections for inst in self.instances.values())
            
            return {
                'strategy': self.strategy.value,
                'total_instances': len(self.instances),
                'instances_by_status': dict(instances_by_status),
                'total_active_connections': total_connections,
                'total_requests_served': total_requests,
                'health_check_enabled': self._running
            }


class ResourcePoolManager:
    """Resource pool manager for connections, threads, processes"""
    
    def __init__(self):
        self.pools: Dict[str, ResourcePool] = {}
        self.thread_pools: Dict[str, ThreadPoolExecutor] = {}
        self.process_pools: Dict[str, ProcessPoolExecutor] = {}
        self.connection_pools: Dict[str, Queue] = {}
        self._lock = threading.RLock()
    
    def create_thread_pool(self, 
                          pool_name: str,
                          min_workers: int = 2,
                          max_workers: int = 20) -> ThreadPoolExecutor:
        """Create or get thread pool"""
        with self._lock:
            if pool_name in self.thread_pools:
                return self.thread_pools[pool_name]
            
            pool = ThreadPoolExecutor(
                max_workers=max_workers,
                thread_name_prefix=f"jarvis-{pool_name}"
            )
            
            self.thread_pools[pool_name] = pool
            self.pools[pool_name] = ResourcePool(
                pool_type="thread",
                min_size=min_workers,
                max_size=max_workers
            )
            
            logger.info(f"Created thread pool '{pool_name}' with {min_workers}-{max_workers} workers")
            return pool
    
    def create_process_pool(self,
                           pool_name: str,
                           min_workers: int = 1,
                           max_workers: int = None) -> ProcessPoolExecutor:
        """Create or get process pool"""
        if max_workers is None:
            max_workers = multiprocessing.cpu_count()
        
        with self._lock:
            if pool_name in self.process_pools:
                return self.process_pools[pool_name]
            
            pool = ProcessPoolExecutor(max_workers=max_workers)
            
            self.process_pools[pool_name] = pool
            self.pools[pool_name] = ResourcePool(
                pool_type="process",
                min_size=min_workers,
                max_size=max_workers
            )
            
            logger.info(f"Created process pool '{pool_name}' with {min_workers}-{max_workers} workers")
            return pool
    
    def create_connection_pool(self,
                              pool_name: str,
                              factory: Callable,
                              min_connections: int = 5,
                              max_connections: int = 50) -> Queue:
        """Create connection pool with factory function"""
        with self._lock:
            if pool_name in self.connection_pools:
                return self.connection_pools[pool_name]
            
            pool_queue = Queue(maxsize=max_connections)
            
            # Pre-create minimum connections
            for _ in range(min_connections):
                try:
                    connection = factory()
                    pool_queue.put(connection)
                except Exception as e:
                    logger.error(f"Failed to create connection for pool {pool_name}: {e}")
            
            self.connection_pools[pool_name] = pool_queue
            self.pools[pool_name] = ResourcePool(
                pool_type="connection",
                min_size=min_connections,
                max_size=max_connections,
                current_size=pool_queue.qsize()
            )
            
            logger.info(f"Created connection pool '{pool_name}' with {min_connections}-{max_connections} connections")
            return pool_queue
    
    @contextmanager
    def get_connection(self, pool_name: str, factory: Callable = None, timeout: float = 5.0):
        """Get connection from pool with context manager"""
        if pool_name not in self.connection_pools:
            if factory is None:
                raise ValueError(f"Pool {pool_name} not found and no factory provided")
            self.create_connection_pool(pool_name, factory)
        
        pool_queue = self.connection_pools[pool_name]
        pool_config = self.pools[pool_name]
        
        connection = None
        try:
            # Try to get existing connection
            try:
                connection = pool_queue.get(timeout=timeout)
                pool_config.active_resources += 1
            except Empty:
                # Create new connection if pool allows
                if pool_config.current_size < pool_config.max_size and factory:
                    start_time = time.time()
                    connection = factory()
                    creation_time = time.time() - start_time
                    
                    pool_config.current_size += 1
                    pool_config.total_created += 1
                    pool_config.creation_time_sum += creation_time
                    pool_config.active_resources += 1
                else:
                    raise TimeoutError(f"No connections available in pool {pool_name}")
            
            yield connection
            
        finally:
            if connection:
                # Return connection to pool
                try:
                    pool_queue.put_nowait(connection)
                    pool_config.active_resources -= 1
                except:
                    # Pool is full, close connection
                    try:
                        if hasattr(connection, 'close'):
                            connection.close()
                    except:
                        pass
                    pool_config.current_size -= 1
    
    def get_pool_status(self) -> Dict[str, Any]:
        """Get status of all resource pools"""
        with self._lock:
            status = {}
            
            for pool_name, pool_config in self.pools.items():
                pool_status = {
                    'type': pool_config.pool_type,
                    'min_size': pool_config.min_size,
                    'max_size': pool_config.max_size,
                    'current_size': pool_config.current_size,
                    'active_resources': pool_config.active_resources,
                    'utilization_rate': pool_config.utilization_rate,
                    'total_created': pool_config.total_created,
                    'avg_creation_time_ms': pool_config.avg_creation_time * 1000
                }
                
                # Add specific pool info
                if pool_config.pool_type == "thread" and pool_name in self.thread_pools:
                    executor = self.thread_pools[pool_name]
                    pool_status['active_threads'] = len(executor._threads)
                
                elif pool_config.pool_type == "process" and pool_name in self.process_pools:
                    executor = self.process_pools[pool_name]
                    pool_status['active_processes'] = len(executor._processes)
                
                elif pool_config.pool_type == "connection" and pool_name in self.connection_pools:
                    queue = self.connection_pools[pool_name]
                    pool_status['available_connections'] = queue.qsize()
                
                status[pool_name] = pool_status
            
            return status
    
    def shutdown_all(self):
        """Shutdown all resource pools"""
        with self._lock:
            # Shutdown thread pools
            for name, pool in self.thread_pools.items():
                try:
                    pool.shutdown(wait=True, timeout=30)
                    logger.info(f"Shutdown thread pool: {name}")
                except Exception as e:
                    logger.error(f"Error shutting down thread pool {name}: {e}")
            
            # Shutdown process pools
            for name, pool in self.process_pools.items():
                try:
                    pool.shutdown(wait=True, timeout=30)
                    logger.info(f"Shutdown process pool: {name}")
                except Exception as e:
                    logger.error(f"Error shutting down process pool {name}: {e}")
            
            # Close connection pools
            for name, queue in self.connection_pools.items():
                try:
                    while not queue.empty():
                        connection = queue.get_nowait()
                        if hasattr(connection, 'close'):
                            connection.close()
                    logger.info(f"Closed connection pool: {name}")
                except Exception as e:
                    logger.error(f"Error closing connection pool {name}: {e}")
            
            self.pools.clear()
            self.thread_pools.clear()
            self.process_pools.clear()
            self.connection_pools.clear()


class AutoScaler:
    """Auto-scaling manager based on system metrics"""
    
    def __init__(self):
        self.scaling_rules: List[ScalingRule] = []
        self.metrics_history: Dict[str, deque] = defaultdict(lambda: deque(maxlen=100))
        self.scale_callbacks: Dict[str, Callable] = {}
        self._monitoring = False
        self._monitor_thread: Optional[threading.Thread] = None
        self.check_interval = 60  # Check every minute
    
    def add_scaling_rule(self, rule: ScalingRule):
        """Add auto-scaling rule"""
        self.scaling_rules.append(rule)
        logger.info(f"Added scaling rule: {rule.trigger.value} up@{rule.threshold_up} down@{rule.threshold_down}")
    
    def register_scale_callback(self, trigger: ScalingTrigger, callback: Callable[[str, int], None]):
        """Register callback for scaling actions"""
        self.scale_callbacks[trigger.value] = callback
    
    def start_monitoring(self):
        """Start auto-scaling monitoring"""
        if self._monitoring:
            return
        
        self._monitoring = True
        self._monitor_thread = threading.Thread(target=self._monitoring_loop, daemon=True)
        self._monitor_thread.start()
        logger.info("Auto-scaler monitoring started")
    
    def stop_monitoring(self):
        """Stop auto-scaling monitoring"""
        self._monitoring = False
        if self._monitor_thread:
            self._monitor_thread.join()
    
    def _monitoring_loop(self):
        """Auto-scaling monitoring loop"""
        while self._monitoring:
            try:
                # Collect current metrics
                metrics = self._collect_metrics()
                
                # Check each scaling rule
                for rule in self.scaling_rules:
                    if not rule.enabled:
                        continue
                    
                    self._evaluate_rule(rule, metrics)
                
                time.sleep(self.check_interval)
                
            except Exception as e:
                logger.error(f"Error in auto-scaling loop: {e}")
                time.sleep(30)
    
    def _collect_metrics(self) -> Dict[str, float]:
        """Collect current system metrics"""
        metrics = {}
        
        try:
            # CPU usage
            metrics['cpu_usage'] = psutil.cpu_percent(interval=1)
            
            # Memory usage
            memory = psutil.virtual_memory()
            metrics['memory_usage'] = memory.percent
            
            # System load (if available)
            try:
                load1, load5, load15 = os.getloadavg()
                metrics['load_1min'] = load1
                metrics['load_5min'] = load5
            except:
                pass
            
            # Add to history
            for metric_name, value in metrics.items():
                self.metrics_history[metric_name].append((datetime.now(), value))
            
        except Exception as e:
            logger.error(f"Error collecting metrics: {e}")
        
        return metrics
    
    def _evaluate_rule(self, rule: ScalingRule, current_metrics: Dict[str, float]):
        """Evaluate scaling rule against current metrics"""
        try:
            metric_value = current_metrics.get(rule.trigger.value.replace('_', ''))
            if metric_value is None:
                return
            
            # Check cooldown
            if rule.last_action:
                time_since_action = datetime.now() - rule.last_action
                if time_since_action.total_seconds() < rule.cooldown_seconds:
                    return
            
            # Get historical data for evaluation
            history = self.metrics_history.get(rule.trigger.value.replace('_', ''), deque())
            if len(history) < rule.evaluation_periods:
                return
            
            # Check if metric exceeds thresholds consistently
            recent_values = [value for _, value in list(history)[-rule.evaluation_periods:]]
            
            scale_up = all(value > rule.threshold_up for value in recent_values)
            scale_down = all(value < rule.threshold_down for value in recent_values)
            
            if scale_up:
                self._trigger_scale_action(rule, "scale_up", rule.scale_up_count)
            elif scale_down:
                self._trigger_scale_action(rule, "scale_down", rule.scale_down_count)
                
        except Exception as e:
            logger.error(f"Error evaluating scaling rule: {e}")
    
    def _trigger_scale_action(self, rule: ScalingRule, action: str, count: int):
        """Trigger scaling action"""
        try:
            logger.info(f"Triggering {action} by {count} for {rule.trigger.value}")
            
            # Call registered callback if available
            callback = self.scale_callbacks.get(rule.trigger.value)
            if callback:
                callback(action, count)
            
            # Update rule
            rule.last_action = datetime.now()
            
        except Exception as e:
            logger.error(f"Error triggering scale action: {e}")
    
    def get_scaling_status(self) -> Dict[str, Any]:
        """Get auto-scaling status"""
        return {
            'monitoring_enabled': self._monitoring,
            'active_rules': len([rule for rule in self.scaling_rules if rule.enabled]),
            'total_rules': len(self.scaling_rules),
            'check_interval_seconds': self.check_interval,
            'metrics_history_length': {k: len(v) for k, v in self.metrics_history.items()}
        }


class ScalabilityManager:
    """Main scalability management system"""
    
    def __init__(self, 
                 load_balancing_strategy: LoadBalancingStrategy = LoadBalancingStrategy.ADAPTIVE):
        self.load_balancer = LoadBalancer(load_balancing_strategy)
        self.resource_pools = ResourcePoolManager()
        self.auto_scaler = AutoScaler()
        self.request_queue = PriorityQueue()
        self.worker_threads = []
        self._running = False
        
        # Setup default resource pools
        self._setup_default_pools()
        
        # Setup default scaling rules
        self._setup_default_scaling_rules()
        
        logger.info("Scalability manager initialized")
    
    def _setup_default_pools(self):
        """Setup default resource pools"""
        # Default thread pool for general tasks
        self.resource_pools.create_thread_pool("general", min_workers=4, max_workers=20)
        
        # High-priority thread pool for critical tasks
        self.resource_pools.create_thread_pool("high_priority", min_workers=2, max_workers=10)
        
        # Background processing pool
        self.resource_pools.create_thread_pool("background", min_workers=2, max_workers=8)
    
    def _setup_default_scaling_rules(self):
        """Setup default auto-scaling rules"""
        # CPU-based scaling
        cpu_rule = ScalingRule(
            trigger=ScalingTrigger.CPU_USAGE,
            threshold_up=80.0,
            threshold_down=30.0,
            scale_up_count=2,
            scale_down_count=1,
            cooldown_seconds=300,
            evaluation_periods=3
        )
        self.auto_scaler.add_scaling_rule(cpu_rule)
        
        # Memory-based scaling
        memory_rule = ScalingRule(
            trigger=ScalingTrigger.MEMORY_USAGE,
            threshold_up=85.0,
            threshold_down=40.0,
            scale_up_count=1,
            scale_down_count=1,
            cooldown_seconds=600,
            evaluation_periods=5
        )
        self.auto_scaler.add_scaling_rule(memory_rule)
    
    def add_service_instance(self, host: str, port: int, weight: float = 1.0) -> str:
        """Add service instance for load balancing"""
        instance_id = f"{host}:{port}_{uuid.uuid4().hex[:8]}"
        instance = ServiceInstance(
            instance_id=instance_id,
            host=host,
            port=port,
            weight=weight
        )
        self.load_balancer.add_instance(instance)
        return instance_id
    
    def submit_request(self, 
                      task: Callable, 
                      priority: int = 5,
                      pool_name: str = "general",
                      timeout: float = 30.0) -> Future:
        """Submit request for processing with load balancing"""
        # Get next available instance (if using distributed setup)
        instance = self.load_balancer.get_next_instance()
        
        # Get thread pool
        thread_pool = self.resource_pools.thread_pools.get(pool_name)
        if not thread_pool:
            thread_pool = self.resource_pools.create_thread_pool(pool_name)
        
        # Submit task
        future = thread_pool.submit(task)
        
        # Track request if instance is available
        if instance:
            self.load_balancer.report_request_start(instance.instance_id)
            
            # Wrap future to report completion
            original_result = future.result
            
            def wrapped_result(timeout=None):
                start_time = time.time()
                try:
                    result = original_result(timeout)
                    response_time = time.time() - start_time
                    self.load_balancer.report_request_complete(
                        instance.instance_id, response_time, True
                    )
                    return result
                except Exception as e:
                    response_time = time.time() - start_time
                    self.load_balancer.report_request_complete(
                        instance.instance_id, response_time, False
                    )
                    raise
            
            future.result = wrapped_result
        
        return future
    
    def start_services(self):
        """Start all scalability services"""
        if self._running:
            return
        
        self._running = True
        
        # Start load balancer health checks
        self.load_balancer.start_health_checks()
        
        # Start auto-scaler monitoring
        self.auto_scaler.start_monitoring()
        
        logger.info("Scalability services started")
    
    def stop_services(self):
        """Stop all scalability services"""
        self._running = False
        
        # Stop monitoring
        self.load_balancer.stop_health_checks()
        self.auto_scaler.stop_monitoring()
        
        # Shutdown resource pools
        self.resource_pools.shutdown_all()
        
        logger.info("Scalability services stopped")
    
    def get_comprehensive_status(self) -> Dict[str, Any]:
        """Get comprehensive scalability status"""
        return {
            'timestamp': datetime.now().isoformat(),
            'services_running': self._running,
            'load_balancer': self.load_balancer.get_status(),
            'resource_pools': self.resource_pools.get_pool_status(),
            'auto_scaler': self.auto_scaler.get_scaling_status(),
            'system_metrics': {
                'cpu_percent': psutil.cpu_percent(),
                'memory_percent': psutil.virtual_memory().percent,
                'disk_usage': psutil.disk_usage('/').percent,
                'active_threads': threading.active_count(),
                'process_count': len(psutil.pids())
            }
        }


# Global scalability manager instance
_scalability_manager: Optional[ScalabilityManager] = None


def get_scalability_manager() -> ScalabilityManager:
    """Get global scalability manager instance"""
    global _scalability_manager
    if _scalability_manager is None:
        _scalability_manager = ScalabilityManager()
    return _scalability_manager


def main():
    """CLI interface for scalability manager"""
    import argparse
    
    parser = argparse.ArgumentParser(description="JARVIS-MK42 Scalability Manager")
    parser.add_argument('--status', action='store_true', help='Show scalability status')
    parser.add_argument('--start', action='store_true', help='Start scalability services')
    parser.add_argument('--stop', action='store_true', help='Stop scalability services')
    
    args = parser.parse_args()
    
    manager = get_scalability_manager()
    
    try:
        if args.start:
            manager.start_services()
            print("Scalability services started")
        
        elif args.stop:
            manager.stop_services()
            print("Scalability services stopped")
        
        elif args.status:
            status = manager.get_comprehensive_status()
            print(json.dumps(status, indent=2))
        
        else:
            status = manager.get_comprehensive_status()
            print("Scalability Manager Status:")
            print(f"Services Running: {status['services_running']}")
            print(f"Load Balancer Instances: {status['load_balancer']['total_instances']}")
            print(f"Resource Pools: {len(status['resource_pools'])}")
            print(f"CPU Usage: {status['system_metrics']['cpu_percent']:.1f}%")
            print(f"Memory Usage: {status['system_metrics']['memory_percent']:.1f}%")
    
    except KeyboardInterrupt:
        print("\nShutting down...")
        manager.stop_services()


if __name__ == "__main__":
    main()
