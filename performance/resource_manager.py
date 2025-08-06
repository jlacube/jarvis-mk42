#!/usr/bin/env python3
"""
JARVIS-MK42 Resource Manager
===========================

This module provides comprehensive resource management and monitoring:
- Advanced system resource monitoring (CPU, Memory, Disk, Network)
- Auto-scaling triggers based on resource utilization patterns
- Container and process optimization with resource limits
- Resource allocation and scheduling optimization
- Dynamic resource provisioning and deprovisioning
- Resource health checks and anomaly detection
"""

import os
import sys
import json
import time
import asyncio
import threading
import subprocess
from datetime import datetime, timedelta
from typing import Dict, List, Optional, Any, Callable, Union, Tuple
from dataclasses import dataclass, field
from enum import Enum
from collections import defaultdict, deque
import platform
import shutil
from concurrent.futures import ThreadPoolExecutor, Future
import statistics

# Add project root to path
current_dir = os.path.dirname(os.path.abspath(__file__))
project_root = os.path.dirname(current_dir)
if project_root not in sys.path:
    sys.path.insert(0, project_root)

from utils.logging_config import get_logger

logger = get_logger(__name__)


class ResourceType(Enum):
    """Types of system resources"""
    CPU = "cpu"
    MEMORY = "memory"
    DISK = "disk"
    NETWORK = "network"
    GPU = "gpu"
    PROCESS = "process"
    CONTAINER = "container"
    SERVICE = "service"


class ResourceStatus(Enum):
    """Resource health status"""
    HEALTHY = "healthy"
    WARNING = "warning"
    CRITICAL = "critical"
    UNKNOWN = "unknown"
    DEGRADED = "degraded"


class ScalingDirection(Enum):
    """Auto-scaling directions"""
    UP = "up"
    DOWN = "down"
    STABLE = "stable"


@dataclass
class ResourceMetric:
    """Individual resource metric measurement"""
    resource_type: ResourceType
    name: str
    value: float
    unit: str
    timestamp: datetime = field(default_factory=datetime.now)
    metadata: Dict[str, Any] = field(default_factory=dict)
    
    def is_critical(self, threshold: float) -> bool:
        """Check if metric exceeds critical threshold"""
        return self.value > threshold
    
    def is_warning(self, threshold: float) -> bool:
        """Check if metric exceeds warning threshold"""
        return self.value > threshold


@dataclass
class ResourceThresholds:
    """Resource monitoring thresholds"""
    warning_threshold: float
    critical_threshold: float
    auto_scale_up_threshold: float
    auto_scale_down_threshold: float
    
    def get_status(self, value: float) -> ResourceStatus:
        """Determine resource status based on value"""
        if value >= self.critical_threshold:
            return ResourceStatus.CRITICAL
        elif value >= self.warning_threshold:
            return ResourceStatus.WARNING
        else:
            return ResourceStatus.HEALTHY


@dataclass
class ProcessInfo:
    """Process information and metrics"""
    pid: int
    name: str
    cpu_percent: float = 0.0
    memory_mb: float = 0.0
    memory_percent: float = 0.0
    threads: int = 0
    handles: int = 0
    status: str = "unknown"
    create_time: datetime = field(default_factory=datetime.now)
    cmdline: List[str] = field(default_factory=list)


@dataclass
class ContainerInfo:
    """Container information and metrics"""
    container_id: str
    name: str
    image: str
    status: str
    cpu_percent: float = 0.0
    memory_mb: float = 0.0
    memory_limit_mb: float = 0.0
    network_rx_mb: float = 0.0
    network_tx_mb: float = 0.0
    disk_read_mb: float = 0.0
    disk_write_mb: float = 0.0


@dataclass
class ScalingRecommendation:
    """Auto-scaling recommendation"""
    resource_type: ResourceType
    direction: ScalingDirection
    current_value: float
    target_value: float
    confidence: float  # 0.0 to 1.0
    reasoning: str
    estimated_impact: Dict[str, Any] = field(default_factory=dict)


class SystemResourceMonitor:
    """Cross-platform system resource monitoring"""
    
    def __init__(self):
        self.platform = platform.system()
        self.is_windows = self.platform == "Windows"
        self.is_linux = self.platform == "Linux"
        self.is_mac = self.platform == "Darwin"
    
    def get_cpu_usage(self) -> Dict[str, Any]:
        """Get CPU usage metrics"""
        try:
            if self.is_windows:
                return self._get_cpu_usage_windows()
            else:
                return self._get_cpu_usage_unix()
        except Exception as e:
            logger.error(f"Error getting CPU usage: {e}")
            return {'total_percent': 0.0, 'per_core': [], 'load_average': []}
    
    def _get_cpu_usage_windows(self) -> Dict[str, Any]:
        """Get CPU usage on Windows using wmic"""
        try:
            # Get overall CPU usage
            result = subprocess.run([
                'wmic', 'cpu', 'get', 'loadpercentage', '/value'
            ], capture_output=True, text=True, timeout=10)
            
            cpu_percent = 0.0
            for line in result.stdout.split('\n'):
                if 'LoadPercentage=' in line:
                    cpu_percent = float(line.split('=')[1])
                    break
            
            # Get core count
            result = subprocess.run([
                'wmic', 'cpu', 'get', 'NumberOfCores,NumberOfLogicalProcessors', '/value'
            ], capture_output=True, text=True, timeout=10)
            
            cores = 1
            for line in result.stdout.split('\n'):
                if 'NumberOfLogicalProcessors=' in line:
                    cores = int(line.split('=')[1])
                    break
            
            return {
                'total_percent': cpu_percent,
                'core_count': cores,
                'per_core': [cpu_percent] * cores,  # Approximation
                'load_average': []  # Not available on Windows
            }
            
        except Exception as e:
            logger.error(f"Error getting Windows CPU usage: {e}")
            return {'total_percent': 0.0, 'core_count': 1, 'per_core': [], 'load_average': []}
    
    def _get_cpu_usage_unix(self) -> Dict[str, Any]:
        """Get CPU usage on Unix systems"""
        try:
            # Get CPU usage from top command
            result = subprocess.run([
                'top', '-bn1'
            ], capture_output=True, text=True, timeout=10)
            
            cpu_percent = 0.0
            for line in result.stdout.split('\n'):
                if 'Cpu(s):' in line or '%Cpu(s):' in line:
                    # Parse line like: %Cpu(s): 12.5 us,  2.1 sy,  0.0 ni, 85.4 id
                    parts = line.split()
                    for i, part in enumerate(parts):
                        if 'us' in part or 'user' in part:
                            cpu_percent += float(parts[i-1])
                        if 'sy' in part or 'system' in part:
                            cpu_percent += float(parts[i-1])
                    break
            
            # Get load average
            load_avg = []
            try:
                with open('/proc/loadavg', 'r') as f:
                    load_values = f.read().strip().split()
                    load_avg = [float(x) for x in load_values[:3]]
            except:
                pass
            
            return {
                'total_percent': cpu_percent,
                'per_core': [],  # Would need more complex parsing
                'load_average': load_avg
            }
            
        except Exception as e:
            logger.error(f"Error getting Unix CPU usage: {e}")
            return {'total_percent': 0.0, 'per_core': [], 'load_average': []}
    
    def get_memory_usage(self) -> Dict[str, Any]:
        """Get memory usage metrics"""
        try:
            if self.is_windows:
                return self._get_memory_usage_windows()
            else:
                return self._get_memory_usage_unix()
        except Exception as e:
            logger.error(f"Error getting memory usage: {e}")
            return {'total_mb': 0, 'used_mb': 0, 'free_mb': 0, 'percent': 0.0}
    
    def _get_memory_usage_windows(self) -> Dict[str, Any]:
        """Get memory usage on Windows"""
        try:
            # Get total physical memory
            result = subprocess.run([
                'wmic', 'computersystem', 'get', 'TotalPhysicalMemory', '/value'
            ], capture_output=True, text=True, timeout=10)
            
            total_bytes = 0
            for line in result.stdout.split('\n'):
                if 'TotalPhysicalMemory=' in line:
                    total_bytes = int(line.split('=')[1])
                    break
            
            # Get available memory
            result = subprocess.run([
                'wmic', 'OS', 'get', 'TotalVisibleMemorySize,FreePhysicalMemory', '/value'
            ], capture_output=True, text=True, timeout=10)
            
            free_kb = 0
            for line in result.stdout.split('\n'):
                if 'FreePhysicalMemory=' in line:
                    free_kb = int(line.split('=')[1])
                    break
            
            total_mb = total_bytes / (1024 * 1024)
            free_mb = free_kb / 1024
            used_mb = total_mb - free_mb
            percent = (used_mb / total_mb) * 100 if total_mb > 0 else 0
            
            return {
                'total_mb': round(total_mb, 1),
                'used_mb': round(used_mb, 1),
                'free_mb': round(free_mb, 1),
                'percent': round(percent, 1)
            }
            
        except Exception as e:
            logger.error(f"Error getting Windows memory usage: {e}")
            return {'total_mb': 0, 'used_mb': 0, 'free_mb': 0, 'percent': 0.0}
    
    def _get_memory_usage_unix(self) -> Dict[str, Any]:
        """Get memory usage on Unix systems"""
        try:
            with open('/proc/meminfo', 'r') as f:
                meminfo = f.read()
            
            total_kb = 0
            available_kb = 0
            free_kb = 0
            
            for line in meminfo.split('\n'):
                if line.startswith('MemTotal:'):
                    total_kb = int(line.split()[1])
                elif line.startswith('MemAvailable:'):
                    available_kb = int(line.split()[1])
                elif line.startswith('MemFree:'):
                    free_kb = int(line.split()[1])
            
            # Use MemAvailable if available, otherwise use MemFree
            effective_free_kb = available_kb if available_kb > 0 else free_kb
            
            total_mb = total_kb / 1024
            free_mb = effective_free_kb / 1024
            used_mb = total_mb - free_mb
            percent = (used_mb / total_mb) * 100 if total_mb > 0 else 0
            
            return {
                'total_mb': round(total_mb, 1),
                'used_mb': round(used_mb, 1),
                'free_mb': round(free_mb, 1),
                'percent': round(percent, 1)
            }
            
        except Exception as e:
            logger.error(f"Error getting Unix memory usage: {e}")
            return {'total_mb': 0, 'used_mb': 0, 'free_mb': 0, 'percent': 0.0}
    
    def get_disk_usage(self, path: str = None) -> Dict[str, Any]:
        """Get disk usage for specified path or root"""
        try:
            if path is None:
                path = "/" if not self.is_windows else "C:\\"
            
            total, used, free = shutil.disk_usage(path)
            
            total_gb = total / (1024**3)
            used_gb = used / (1024**3)
            free_gb = free / (1024**3)
            percent = (used_gb / total_gb) * 100 if total_gb > 0 else 0
            
            return {
                'path': path,
                'total_gb': round(total_gb, 1),
                'used_gb': round(used_gb, 1),
                'free_gb': round(free_gb, 1),
                'percent': round(percent, 1)
            }
            
        except Exception as e:
            logger.error(f"Error getting disk usage for {path}: {e}")
            return {'path': path, 'total_gb': 0, 'used_gb': 0, 'free_gb': 0, 'percent': 0.0}
    
    def get_network_usage(self) -> Dict[str, Any]:
        """Get network usage statistics"""
        try:
            if self.is_windows:
                return self._get_network_usage_windows()
            else:
                return self._get_network_usage_unix()
        except Exception as e:
            logger.error(f"Error getting network usage: {e}")
            return {'bytes_sent': 0, 'bytes_recv': 0, 'packets_sent': 0, 'packets_recv': 0}
    
    def _get_network_usage_windows(self) -> Dict[str, Any]:
        """Get network usage on Windows"""
        try:
            result = subprocess.run([
                'typeperf', '-sc', '1', '\\Network Interface(*)\\Bytes Total/sec'
            ], capture_output=True, text=True, timeout=10)
            
            # This is a simplified implementation
            # Real implementation would parse typeperf output
            return {
                'bytes_sent': 0,
                'bytes_recv': 0,
                'packets_sent': 0,
                'packets_recv': 0,
                'interfaces': []
            }
            
        except Exception as e:
            logger.error(f"Error getting Windows network usage: {e}")
            return {'bytes_sent': 0, 'bytes_recv': 0, 'packets_sent': 0, 'packets_recv': 0}
    
    def _get_network_usage_unix(self) -> Dict[str, Any]:
        """Get network usage on Unix systems"""
        try:
            with open('/proc/net/dev', 'r') as f:
                lines = f.readlines()
            
            total_bytes_recv = 0
            total_bytes_sent = 0
            total_packets_recv = 0
            total_packets_sent = 0
            interfaces = []
            
            for line in lines[2:]:  # Skip header lines
                if ':' in line:
                    parts = line.split(':')
                    interface = parts[0].strip()
                    if interface != 'lo':  # Skip loopback
                        stats = parts[1].split()
                        bytes_recv = int(stats[0])
                        packets_recv = int(stats[1])
                        bytes_sent = int(stats[8])
                        packets_sent = int(stats[9])
                        
                        total_bytes_recv += bytes_recv
                        total_bytes_sent += bytes_sent
                        total_packets_recv += packets_recv
                        total_packets_sent += packets_sent
                        
                        interfaces.append({
                            'name': interface,
                            'bytes_recv': bytes_recv,
                            'bytes_sent': bytes_sent,
                            'packets_recv': packets_recv,
                            'packets_sent': packets_sent
                        })
            
            return {
                'bytes_sent': total_bytes_sent,
                'bytes_recv': total_bytes_recv,
                'packets_sent': total_packets_sent,
                'packets_recv': total_packets_recv,
                'interfaces': interfaces
            }
            
        except Exception as e:
            logger.error(f"Error getting Unix network usage: {e}")
            return {'bytes_sent': 0, 'bytes_recv': 0, 'packets_sent': 0, 'packets_recv': 0}
    
    def get_processes(self, limit: int = 10) -> List[ProcessInfo]:
        """Get top processes by resource usage"""
        try:
            if self.is_windows:
                return self._get_processes_windows(limit)
            else:
                return self._get_processes_unix(limit)
        except Exception as e:
            logger.error(f"Error getting processes: {e}")
            return []
    
    def _get_processes_windows(self, limit: int) -> List[ProcessInfo]:
        """Get processes on Windows"""
        try:
            result = subprocess.run([
                'tasklist', '/fo', 'csv'
            ], capture_output=True, text=True, timeout=15)
            
            processes = []
            lines = result.stdout.split('\n')[1:]  # Skip header
            
            for line in lines[:limit]:
                if line.strip():
                    parts = [p.strip('"') for p in line.split('","')]
                    if len(parts) >= 5:
                        try:
                            memory_str = parts[4].replace(',', '').replace(' K', '')
                            memory_kb = int(memory_str) if memory_str.isdigit() else 0
                            
                            process = ProcessInfo(
                                pid=int(parts[1]),
                                name=parts[0],
                                memory_mb=memory_kb / 1024,
                                status=parts[3]
                            )
                            processes.append(process)
                        except:
                            continue
            
            return processes
            
        except Exception as e:
            logger.error(f"Error getting Windows processes: {e}")
            return []
    
    def _get_processes_unix(self, limit: int) -> List[ProcessInfo]:
        """Get processes on Unix systems"""
        try:
            result = subprocess.run([
                'ps', 'aux', '--sort=-pmem'
            ], capture_output=True, text=True, timeout=15)
            
            processes = []
            lines = result.stdout.split('\n')[1:]  # Skip header
            
            for line in lines[:limit]:
                if line.strip():
                    parts = line.split()
                    if len(parts) >= 11:
                        try:
                            process = ProcessInfo(
                                pid=int(parts[1]),
                                name=parts[10] if len(parts) > 10 else 'unknown',
                                cpu_percent=float(parts[2]),
                                memory_percent=float(parts[3]),
                                status=parts[7] if len(parts) > 7 else 'unknown'
                            )
                            processes.append(process)
                        except:
                            continue
            
            return processes
            
        except Exception as e:
            logger.error(f"Error getting Unix processes: {e}")
            return []


class ResourceHealthChecker:
    """Resource health monitoring and anomaly detection"""
    
    def __init__(self, history_size: int = 1000):
        self.history_size = history_size
        self.metric_history: Dict[str, deque] = defaultdict(
            lambda: deque(maxlen=history_size)
        )
        self.thresholds: Dict[ResourceType, ResourceThresholds] = {
            ResourceType.CPU: ResourceThresholds(70.0, 90.0, 80.0, 30.0),
            ResourceType.MEMORY: ResourceThresholds(80.0, 95.0, 85.0, 40.0),
            ResourceType.DISK: ResourceThresholds(85.0, 95.0, 90.0, 50.0),
        }
        self.anomaly_sensitivity = 2.0  # Standard deviations for anomaly detection
    
    def update_metric_history(self, metric: ResourceMetric):
        """Update metric history for trend analysis"""
        key = f"{metric.resource_type.value}_{metric.name}"
        self.metric_history[key].append({
            'value': metric.value,
            'timestamp': metric.timestamp
        })
    
    def check_resource_health(self, metric: ResourceMetric) -> ResourceStatus:
        """Check resource health status"""
        thresholds = self.thresholds.get(metric.resource_type)
        if not thresholds:
            return ResourceStatus.UNKNOWN
        
        return thresholds.get_status(metric.value)
    
    def detect_anomaly(self, metric: ResourceMetric) -> bool:
        """Detect if metric value is anomalous"""
        key = f"{metric.resource_type.value}_{metric.name}"
        history = self.metric_history[key]
        
        if len(history) < 10:  # Not enough history
            return False
        
        values = [h['value'] for h in history]
        mean = statistics.mean(values)
        stdev = statistics.stdev(values) if len(values) > 1 else 0
        
        if stdev == 0:
            return False
        
        z_score = abs(metric.value - mean) / stdev
        return z_score > self.anomaly_sensitivity
    
    def get_trend_analysis(self, 
                          resource_type: ResourceType,
                          metric_name: str,
                          window_minutes: int = 30) -> Dict[str, Any]:
        """Analyze metric trend over time window"""
        key = f"{resource_type.value}_{metric_name}"
        history = self.metric_history[key]
        
        if len(history) < 2:
            return {'trend': 'insufficient_data', 'slope': 0.0, 'r_squared': 0.0}
        
        # Filter to time window
        cutoff_time = datetime.now() - timedelta(minutes=window_minutes)
        recent_data = [
            h for h in history
            if h['timestamp'] > cutoff_time
        ]
        
        if len(recent_data) < 2:
            return {'trend': 'insufficient_data', 'slope': 0.0, 'r_squared': 0.0}
        
        # Calculate linear regression
        n = len(recent_data)
        x = list(range(n))
        y = [d['value'] for d in recent_data]
        
        # Simple linear regression
        x_mean = sum(x) / n
        y_mean = sum(y) / n
        
        numerator = sum((x[i] - x_mean) * (y[i] - y_mean) for i in range(n))
        denominator = sum((x[i] - x_mean) ** 2 for i in range(n))
        
        if denominator == 0:
            slope = 0
        else:
            slope = numerator / denominator
        
        # Determine trend direction
        if abs(slope) < 0.1:
            trend = 'stable'
        elif slope > 0:
            trend = 'increasing'
        else:
            trend = 'decreasing'
        
        return {
            'trend': trend,
            'slope': slope,
            'data_points': n,
            'time_window_minutes': window_minutes,
            'current_value': y[-1] if y else 0,
            'min_value': min(y) if y else 0,
            'max_value': max(y) if y else 0,
            'avg_value': y_mean
        }


class AutoScaler:
    """Auto-scaling decision engine"""
    
    def __init__(self,
                 cooldown_minutes: int = 5,
                 confidence_threshold: float = 0.7):
        self.cooldown_minutes = cooldown_minutes
        self.confidence_threshold = confidence_threshold
        self.last_scaling_actions: Dict[str, datetime] = {}
        self.scaling_history: List[Dict[str, Any]] = []
    
    def should_scale(self,
                    resource_type: ResourceType,
                    current_metrics: List[ResourceMetric],
                    trend_analysis: Dict[str, Any]) -> Optional[ScalingRecommendation]:
        """Determine if scaling action is recommended"""
        
        # Check cooldown period
        key = f"{resource_type.value}"
        last_action = self.last_scaling_actions.get(key)
        if last_action:
            minutes_since_last = (datetime.now() - last_action).total_seconds() / 60
            if minutes_since_last < self.cooldown_minutes:
                return None
        
        # Analyze current state
        avg_utilization = sum(m.value for m in current_metrics) / len(current_metrics)
        trend = trend_analysis.get('trend', 'stable')
        slope = trend_analysis.get('slope', 0.0)
        
        # Scaling decision logic
        scale_up_reasons = []
        scale_down_reasons = []
        confidence = 0.0
        
        # CPU scaling logic
        if resource_type == ResourceType.CPU:
            if avg_utilization > 80.0:
                scale_up_reasons.append(f"High CPU utilization: {avg_utilization:.1f}%")
                confidence += 0.4
            
            if trend == 'increasing' and slope > 1.0:
                scale_up_reasons.append("CPU utilization trending upward")
                confidence += 0.3
            
            if avg_utilization < 30.0 and trend != 'increasing':
                scale_down_reasons.append(f"Low CPU utilization: {avg_utilization:.1f}%")
                confidence += 0.3
        
        # Memory scaling logic
        elif resource_type == ResourceType.MEMORY:
            if avg_utilization > 85.0:
                scale_up_reasons.append(f"High memory utilization: {avg_utilization:.1f}%")
                confidence += 0.5
            
            if avg_utilization < 40.0 and trend != 'increasing':
                scale_down_reasons.append(f"Low memory utilization: {avg_utilization:.1f}%")
                confidence += 0.2
        
        # Determine scaling direction and create recommendation
        if scale_up_reasons and confidence >= self.confidence_threshold:
            direction = ScalingDirection.UP
            target_value = min(avg_utilization * 0.7, 70.0)  # Target 70% utilization
            reasoning = "; ".join(scale_up_reasons)
            
        elif scale_down_reasons and confidence >= self.confidence_threshold:
            direction = ScalingDirection.DOWN
            target_value = max(avg_utilization * 1.3, 50.0)  # Target 50% utilization
            reasoning = "; ".join(scale_down_reasons)
            
        else:
            direction = ScalingDirection.STABLE
            target_value = avg_utilization
            reasoning = "No scaling action recommended"
        
        if direction != ScalingDirection.STABLE:
            # Record scaling action
            self.last_scaling_actions[key] = datetime.now()
            self.scaling_history.append({
                'timestamp': datetime.now(),
                'resource_type': resource_type.value,
                'direction': direction.value,
                'current_value': avg_utilization,
                'target_value': target_value,
                'confidence': confidence,
                'reasoning': reasoning
            })
        
        return ScalingRecommendation(
            resource_type=resource_type,
            direction=direction,
            current_value=avg_utilization,
            target_value=target_value,
            confidence=confidence,
            reasoning=reasoning,
            estimated_impact={
                'efficiency_gain': 0.1 if direction == ScalingDirection.UP else 0.05,
                'cost_impact': 0.2 if direction == ScalingDirection.UP else -0.15
            }
        )
    
    def get_scaling_history(self, limit: int = 50) -> List[Dict[str, Any]]:
        """Get recent scaling history"""
        return self.scaling_history[-limit:]


class ResourceManager:
    """Main resource management orchestrator"""
    
    def __init__(self,
                 monitoring_interval: int = 30,
                 enable_auto_scaling: bool = True):
        
        self.monitoring_interval = monitoring_interval
        self.enable_auto_scaling = enable_auto_scaling
        
        self.system_monitor = SystemResourceMonitor()
        self.health_checker = ResourceHealthChecker()
        self.auto_scaler = AutoScaler()
        
        self.current_metrics: Dict[ResourceType, List[ResourceMetric]] = {}
        self.monitoring_thread: Optional[threading.Thread] = None
        self.shutdown_event = threading.Event()
        
        self.resource_callbacks: Dict[ResourceType, List[Callable]] = defaultdict(list)
        self.alert_callbacks: List[Callable[[ResourceMetric, ResourceStatus], None]] = []
        self.scaling_callbacks: List[Callable[[ScalingRecommendation], None]] = []
        
        logger.info("Resource Manager initialized")
    
    def start_monitoring(self):
        """Start resource monitoring"""
        if self.monitoring_thread and self.monitoring_thread.is_alive():
            logger.warning("Resource monitoring already running")
            return
        
        self.shutdown_event.clear()
        self.monitoring_thread = threading.Thread(
            target=self._monitoring_loop,
            daemon=True,
            name="resource-monitor"
        )
        self.monitoring_thread.start()
        logger.info("Resource monitoring started")
    
    def stop_monitoring(self):
        """Stop resource monitoring"""
        self.shutdown_event.set()
        if self.monitoring_thread:
            self.monitoring_thread.join(timeout=10)
        logger.info("Resource monitoring stopped")
    
    def _monitoring_loop(self):
        """Main monitoring loop"""
        while not self.shutdown_event.is_set():
            try:
                self._collect_metrics()
                self._analyze_health()
                
                if self.enable_auto_scaling:
                    self._check_scaling_opportunities()
                
            except Exception as e:
                logger.error(f"Error in monitoring loop: {e}")
            
            # Wait for next interval
            self.shutdown_event.wait(timeout=self.monitoring_interval)
    
    def _collect_metrics(self):
        """Collect all resource metrics"""
        timestamp = datetime.now()
        
        # CPU metrics
        cpu_data = self.system_monitor.get_cpu_usage()
        cpu_metric = ResourceMetric(
            resource_type=ResourceType.CPU,
            name="utilization",
            value=cpu_data['total_percent'],
            unit="percent",
            timestamp=timestamp,
            metadata=cpu_data
        )
        self._store_metric(cpu_metric)
        
        # Memory metrics
        memory_data = self.system_monitor.get_memory_usage()
        memory_metric = ResourceMetric(
            resource_type=ResourceType.MEMORY,
            name="utilization",
            value=memory_data['percent'],
            unit="percent",
            timestamp=timestamp,
            metadata=memory_data
        )
        self._store_metric(memory_metric)
        
        # Disk metrics
        disk_data = self.system_monitor.get_disk_usage()
        disk_metric = ResourceMetric(
            resource_type=ResourceType.DISK,
            name="utilization",
            value=disk_data['percent'],
            unit="percent",
            timestamp=timestamp,
            metadata=disk_data
        )
        self._store_metric(disk_metric)
        
        # Network metrics
        network_data = self.system_monitor.get_network_usage()
        network_metric = ResourceMetric(
            resource_type=ResourceType.NETWORK,
            name="bytes_total",
            value=network_data['bytes_sent'] + network_data['bytes_recv'],
            unit="bytes",
            timestamp=timestamp,
            metadata=network_data
        )
        self._store_metric(network_metric)
    
    def _store_metric(self, metric: ResourceMetric):
        """Store metric and update history"""
        if metric.resource_type not in self.current_metrics:
            self.current_metrics[metric.resource_type] = []
        
        self.current_metrics[metric.resource_type].append(metric)
        
        # Keep only recent metrics (last hour)
        cutoff_time = datetime.now() - timedelta(hours=1)
        self.current_metrics[metric.resource_type] = [
            m for m in self.current_metrics[metric.resource_type]
            if m.timestamp > cutoff_time
        ]
        
        # Update health checker history
        self.health_checker.update_metric_history(metric)
        
        # Notify callbacks
        for callback in self.resource_callbacks[metric.resource_type]:
            try:
                callback(metric)
            except Exception as e:
                logger.error(f"Error in resource callback: {e}")
    
    def _analyze_health(self):
        """Analyze resource health and trigger alerts"""
        for resource_type, metrics in self.current_metrics.items():
            if not metrics:
                continue
            
            latest_metric = metrics[-1]
            status = self.health_checker.check_resource_health(latest_metric)
            
            # Check for anomalies
            is_anomaly = self.health_checker.detect_anomaly(latest_metric)
            
            # Trigger alerts for critical status or anomalies
            if status in [ResourceStatus.CRITICAL, ResourceStatus.WARNING] or is_anomaly:
                for callback in self.alert_callbacks:
                    try:
                        callback(latest_metric, status)
                    except Exception as e:
                        logger.error(f"Error in alert callback: {e}")
                
                if status == ResourceStatus.CRITICAL:
                    logger.critical(f"Critical resource status: {resource_type.value} at {latest_metric.value:.1f}%")
                elif is_anomaly:
                    logger.warning(f"Resource anomaly detected: {resource_type.value} at {latest_metric.value:.1f}")
    
    def _check_scaling_opportunities(self):
        """Check for auto-scaling opportunities"""
        for resource_type, metrics in self.current_metrics.items():
            if not metrics or resource_type not in [ResourceType.CPU, ResourceType.MEMORY]:
                continue
            
            # Get recent metrics (last 10 minutes)
            recent_time = datetime.now() - timedelta(minutes=10)
            recent_metrics = [m for m in metrics if m.timestamp > recent_time]
            
            if len(recent_metrics) < 3:
                continue
            
            # Get trend analysis
            trend_analysis = self.health_checker.get_trend_analysis(
                resource_type, "utilization", window_minutes=10
            )
            
            # Check scaling recommendation
            recommendation = self.auto_scaler.should_scale(
                resource_type, recent_metrics, trend_analysis
            )
            
            if recommendation and recommendation.direction != ScalingDirection.STABLE:
                logger.info(f"Scaling recommendation: {recommendation.reasoning}")
                
                # Notify scaling callbacks
                for callback in self.scaling_callbacks:
                    try:
                        callback(recommendation)
                    except Exception as e:
                        logger.error(f"Error in scaling callback: {e}")
    
    def register_resource_callback(self, resource_type: ResourceType, callback: Callable):
        """Register callback for specific resource type updates"""
        self.resource_callbacks[resource_type].append(callback)
    
    def register_alert_callback(self, callback: Callable[[ResourceMetric, ResourceStatus], None]):
        """Register callback for resource alerts"""
        self.alert_callbacks.append(callback)
    
    def register_scaling_callback(self, callback: Callable[[ScalingRecommendation], None]):
        """Register callback for scaling recommendations"""
        self.scaling_callbacks.append(callback)
    
    def get_current_status(self) -> Dict[str, Any]:
        """Get current resource status"""
        status = {
            'timestamp': datetime.now().isoformat(),
            'monitoring_enabled': self.monitoring_thread is not None and self.monitoring_thread.is_alive(),
            'auto_scaling_enabled': self.enable_auto_scaling,
            'resources': {}
        }
        
        for resource_type, metrics in self.current_metrics.items():
            if not metrics:
                continue
                
            latest = metrics[-1]
            health_status = self.health_checker.check_resource_health(latest)
            
            trend_analysis = self.health_checker.get_trend_analysis(
                resource_type, "utilization", window_minutes=30
            )
            
            status['resources'][resource_type.value] = {
                'current_value': latest.value,
                'unit': latest.unit,
                'status': health_status.value,
                'trend': trend_analysis.get('trend', 'unknown'),
                'data_points': len(metrics),
                'last_updated': latest.timestamp.isoformat(),
                'metadata': latest.metadata
            }
        
        return status
    
    def get_comprehensive_report(self) -> Dict[str, Any]:
        """Get comprehensive resource management report"""
        status = self.get_current_status()
        
        # Add scaling history
        status['scaling_history'] = self.auto_scaler.get_scaling_history(limit=20)
        
        # Add process information
        top_processes = self.system_monitor.get_processes(limit=10)
        status['top_processes'] = [
            {
                'pid': p.pid,
                'name': p.name,
                'cpu_percent': p.cpu_percent,
                'memory_mb': p.memory_mb,
                'memory_percent': p.memory_percent,
                'status': p.status
            }
            for p in top_processes
        ]
        
        # Add system information
        status['system_info'] = {
            'platform': self.system_monitor.platform,
            'monitoring_interval_seconds': self.monitoring_interval
        }
        
        return status


# Global resource manager instance
_resource_manager: Optional[ResourceManager] = None


def get_resource_manager() -> ResourceManager:
    """Get global resource manager instance"""
    global _resource_manager
    if _resource_manager is None:
        _resource_manager = ResourceManager()
    return _resource_manager


def main():
    """CLI interface for resource manager"""
    import argparse
    
    parser = argparse.ArgumentParser(description="JARVIS-MK42 Resource Manager")
    parser.add_argument('--monitor', action='store_true', help='Start resource monitoring')
    parser.add_argument('--status', action='store_true', help='Show current status')
    parser.add_argument('--report', action='store_true', help='Show comprehensive report')
    parser.add_argument('--interval', type=int, default=30, help='Monitoring interval in seconds')
    
    args = parser.parse_args()
    
    manager = get_resource_manager()
    
    try:
        if args.monitor:
            print(f"Starting resource monitoring (interval: {args.interval}s)...")
            manager.monitoring_interval = args.interval
            manager.start_monitoring()
            
            try:
                while True:
                    time.sleep(10)
                    status = manager.get_current_status()
                    print(f"\n[{status['timestamp']}]")
                    for resource, data in status['resources'].items():
                        print(f"{resource.upper()}: {data['current_value']:.1f}% ({data['status']}) - {data['trend']}")
            except KeyboardInterrupt:
                print("\nStopping monitoring...")
        
        elif args.report:
            report = manager.get_comprehensive_report()
            print(json.dumps(report, indent=2, default=str))
        
        else:
            status = manager.get_current_status()
            print("Resource Manager Status:")
            for resource, data in status['resources'].items():
                print(f"{resource.upper()}: {data['current_value']:.1f}% ({data['status']}) - {data['trend']}")
    
    finally:
        manager.stop_monitoring()


if __name__ == "__main__":
    main()
