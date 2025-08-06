#!/usr/bin/env python3
"""
JARVIS-MK42 Application Performance Monitoring (APM) System
========================================================

This module provides comprehensive application performance monitoring including:
- Real-time performance metrics collection
- Resource utilization monitoring  
- Response time tracking
- Error rate monitoring
- Custom metrics and alerting
- Performance profiling and analysis
"""

import os
import sys
import json
import time
import psutil
import threading
from datetime import datetime, timedelta
from typing import Dict, List, Optional, Any, Callable
from dataclasses import dataclass, field
from collections import defaultdict, deque
from enum import Enum
import logging
import traceback
from functools import wraps
from pathlib import Path

# Add project root to path
current_dir = os.path.dirname(os.path.abspath(__file__))
project_root = os.path.dirname(current_dir)
if project_root not in sys.path:
    sys.path.insert(0, project_root)

from utils.logging_config import get_logger

logger = get_logger(__name__)


class MetricType(Enum):
    """Types of performance metrics"""
    COUNTER = "counter"         # Monotonically increasing values
    GAUGE = "gauge"            # Point-in-time values
    HISTOGRAM = "histogram"     # Distribution of values
    TIMER = "timer"            # Duration measurements


class AlertSeverity(Enum):
    """Alert severity levels"""
    INFO = "info"
    WARNING = "warning"
    ERROR = "error"
    CRITICAL = "critical"


@dataclass
class MetricPoint:
    """Single metric data point"""
    timestamp: datetime
    value: float
    tags: Dict[str, str] = field(default_factory=dict)
    metadata: Dict[str, Any] = field(default_factory=dict)


@dataclass
class PerformanceAlert:
    """Performance alert definition"""
    name: str
    metric_name: str
    condition: str  # e.g., "> 90", "< 0.1"
    threshold: float
    severity: AlertSeverity
    cooldown_minutes: int = 5
    description: str = ""
    last_triggered: Optional[datetime] = None


@dataclass
class SystemSnapshot:
    """System resource snapshot"""
    timestamp: datetime
    cpu_percent: float
    memory_percent: float
    memory_used_mb: float
    memory_available_mb: float
    disk_usage_percent: float
    disk_used_gb: float
    disk_free_gb: float
    network_bytes_sent: int
    network_bytes_recv: int
    process_count: int
    thread_count: int
    open_files: int
    load_average: List[float] = field(default_factory=list)


class MetricCollector:
    """Thread-safe metric collection system"""
    
    def __init__(self, max_points_per_metric: int = 1000):
        self.metrics: Dict[str, deque] = defaultdict(lambda: deque(maxlen=max_points_per_metric))
        self.lock = threading.Lock()
        self.start_time = datetime.utcnow()
    
    def record_counter(self, name: str, value: float = 1, tags: Dict[str, str] = None):
        """Record a counter metric (accumulating value)"""
        with self.lock:
            point = MetricPoint(
                timestamp=datetime.utcnow(),
                value=value,
                tags=tags or {}
            )
            self.metrics[name].append(point)
    
    def record_gauge(self, name: str, value: float, tags: Dict[str, str] = None):
        """Record a gauge metric (point-in-time value)"""
        with self.lock:
            point = MetricPoint(
                timestamp=datetime.utcnow(),
                value=value,
                tags=tags or {}
            )
            self.metrics[name].append(point)
    
    def record_timer(self, name: str, duration_ms: float, tags: Dict[str, str] = None):
        """Record a timer metric (duration measurement)"""
        with self.lock:
            point = MetricPoint(
                timestamp=datetime.utcnow(),
                value=duration_ms,
                tags=tags or {}
            )
            self.metrics[name].append(point)
    
    def get_metric_summary(self, name: str, minutes: int = 60) -> Dict[str, Any]:
        """Get summary statistics for a metric over time window"""
        with self.lock:
            if name not in self.metrics:
                return None
            
            now = datetime.utcnow()
            cutoff = now - timedelta(minutes=minutes)
            
            # Filter points within time window
            points = [p for p in self.metrics[name] if p.timestamp >= cutoff]
            
            if not points:
                return None
            
            values = [p.value for p in points]
            
            return {
                'name': name,
                'count': len(points),
                'min': min(values),
                'max': max(values),
                'avg': sum(values) / len(values),
                'sum': sum(values),
                'latest': values[-1],
                'time_window_minutes': minutes,
                'first_timestamp': points[0].timestamp.isoformat(),
                'last_timestamp': points[-1].timestamp.isoformat()
            }
    
    def get_all_metrics(self) -> Dict[str, List[Dict[str, Any]]]:
        """Get all current metrics"""
        with self.lock:
            result = {}
            for name, points in self.metrics.items():
                result[name] = [
                    {
                        'timestamp': p.timestamp.isoformat(),
                        'value': p.value,
                        'tags': p.tags
                    }
                    for p in points
                ]
            return result


class SystemMonitor:
    """System resource monitoring"""
    
    def __init__(self, collector: MetricCollector):
        self.collector = collector
        self.monitoring = False
        self.monitor_thread = None
        self._initial_network = self._get_network_stats()
    
    def start_monitoring(self, interval_seconds: int = 30):
        """Start system monitoring in background thread"""
        if self.monitoring:
            return
        
        self.monitoring = True
        self.monitor_thread = threading.Thread(
            target=self._monitor_loop,
            args=(interval_seconds,),
            daemon=True
        )
        self.monitor_thread.start()
        logger.info(f"System monitoring started with {interval_seconds}s interval")
    
    def stop_monitoring(self):
        """Stop system monitoring"""
        self.monitoring = False
        if self.monitor_thread:
            self.monitor_thread.join(timeout=5)
        logger.info("System monitoring stopped")
    
    def _monitor_loop(self, interval_seconds: int):
        """Main monitoring loop"""
        while self.monitoring:
            try:
                snapshot = self._collect_system_metrics()
                self._record_system_metrics(snapshot)
                time.sleep(interval_seconds)
            except Exception as e:
                logger.error(f"Error in system monitoring: {e}")
                time.sleep(interval_seconds)
    
    def _collect_system_metrics(self) -> SystemSnapshot:
        """Collect current system metrics"""
        try:
            # CPU metrics
            cpu_percent = psutil.cpu_percent(interval=1)
            
            # Memory metrics
            memory = psutil.virtual_memory()
            
            # Disk metrics
            disk = psutil.disk_usage('/')
            
            # Network metrics
            network = psutil.net_io_counters()
            
            # Process metrics
            process_count = len(psutil.pids())
            
            # Current process info
            current_process = psutil.Process()
            thread_count = current_process.num_threads()
            open_files = len(current_process.open_files()) if hasattr(current_process, 'open_files') else 0
            
            # Load average (Unix-like systems only)
            load_avg = list(os.getloadavg()) if hasattr(os, 'getloadavg') else []
            
            return SystemSnapshot(
                timestamp=datetime.utcnow(),
                cpu_percent=cpu_percent,
                memory_percent=memory.percent,
                memory_used_mb=memory.used / (1024 * 1024),
                memory_available_mb=memory.available / (1024 * 1024),
                disk_usage_percent=disk.percent,
                disk_used_gb=disk.used / (1024 * 1024 * 1024),
                disk_free_gb=disk.free / (1024 * 1024 * 1024),
                network_bytes_sent=network.bytes_sent,
                network_bytes_recv=network.bytes_recv,
                process_count=process_count,
                thread_count=thread_count,
                open_files=open_files,
                load_average=load_avg
            )
            
        except Exception as e:
            logger.error(f"Error collecting system metrics: {e}")
            return SystemSnapshot(
                timestamp=datetime.utcnow(),
                cpu_percent=0,
                memory_percent=0,
                memory_used_mb=0,
                memory_available_mb=0,
                disk_usage_percent=0,
                disk_used_gb=0,
                disk_free_gb=0,
                network_bytes_sent=0,
                network_bytes_recv=0,
                process_count=0,
                thread_count=0,
                open_files=0
            )
    
    def _record_system_metrics(self, snapshot: SystemSnapshot):
        """Record system metrics to collector"""
        self.collector.record_gauge("system.cpu.percent", snapshot.cpu_percent)
        self.collector.record_gauge("system.memory.percent", snapshot.memory_percent)
        self.collector.record_gauge("system.memory.used_mb", snapshot.memory_used_mb)
        self.collector.record_gauge("system.memory.available_mb", snapshot.memory_available_mb)
        self.collector.record_gauge("system.disk.usage_percent", snapshot.disk_usage_percent)
        self.collector.record_gauge("system.disk.used_gb", snapshot.disk_used_gb)
        self.collector.record_gauge("system.disk.free_gb", snapshot.disk_free_gb)
        self.collector.record_counter("system.network.bytes_sent", snapshot.network_bytes_sent)
        self.collector.record_counter("system.network.bytes_recv", snapshot.network_bytes_recv)
        self.collector.record_gauge("system.process.count", snapshot.process_count)
        self.collector.record_gauge("system.thread.count", snapshot.thread_count)
        self.collector.record_gauge("system.files.open", snapshot.open_files)
        
        if snapshot.load_average:
            for i, load in enumerate(snapshot.load_average):
                self.collector.record_gauge(f"system.load.avg_{i+1}min", load)
    
    def _get_network_stats(self):
        """Get initial network statistics"""
        try:
            return psutil.net_io_counters()
        except:
            return None


class AlertManager:
    """Performance alerting system"""
    
    def __init__(self, collector: MetricCollector):
        self.collector = collector
        self.alerts: List[PerformanceAlert] = []
        self.alert_handlers: List[Callable] = []
        self._setup_default_alerts()
    
    def _setup_default_alerts(self):
        """Setup default performance alerts"""
        self.alerts = [
            PerformanceAlert(
                name="High CPU Usage",
                metric_name="system.cpu.percent",
                condition=">",
                threshold=90.0,
                severity=AlertSeverity.WARNING,
                cooldown_minutes=5,
                description="CPU usage is above 90%"
            ),
            PerformanceAlert(
                name="Critical CPU Usage",
                metric_name="system.cpu.percent", 
                condition=">",
                threshold=95.0,
                severity=AlertSeverity.CRITICAL,
                cooldown_minutes=2,
                description="CPU usage is critically high (>95%)"
            ),
            PerformanceAlert(
                name="High Memory Usage",
                metric_name="system.memory.percent",
                condition=">",
                threshold=85.0,
                severity=AlertSeverity.WARNING,
                cooldown_minutes=5,
                description="Memory usage is above 85%"
            ),
            PerformanceAlert(
                name="Critical Memory Usage",
                metric_name="system.memory.percent",
                condition=">",
                threshold=95.0,
                severity=AlertSeverity.CRITICAL,
                cooldown_minutes=2,
                description="Memory usage is critically high (>95%)"
            ),
            PerformanceAlert(
                name="Low Disk Space",
                metric_name="system.disk.usage_percent",
                condition=">",
                threshold=90.0,
                severity=AlertSeverity.WARNING,
                cooldown_minutes=30,
                description="Disk usage is above 90%"
            ),
            PerformanceAlert(
                name="High Response Time",
                metric_name="app.response_time_ms",
                condition=">",
                threshold=5000.0,  # 5 seconds
                severity=AlertSeverity.WARNING,
                cooldown_minutes=5,
                description="Application response time is above 5 seconds"
            )
        ]
    
    def add_alert_handler(self, handler: Callable):
        """Add alert notification handler"""
        self.alert_handlers.append(handler)
    
    def check_alerts(self):
        """Check all alerts and trigger notifications"""
        now = datetime.utcnow()
        
        for alert in self.alerts:
            try:
                # Get recent metric data
                summary = self.collector.get_metric_summary(alert.metric_name, minutes=5)
                if not summary:
                    continue
                
                # Check if alert is in cooldown
                if alert.last_triggered:
                    cooldown_end = alert.last_triggered + timedelta(minutes=alert.cooldown_minutes)
                    if now < cooldown_end:
                        continue
                
                # Evaluate alert condition
                current_value = summary['latest']
                triggered = self._evaluate_condition(current_value, alert.condition, alert.threshold)
                
                if triggered:
                    alert.last_triggered = now
                    self._trigger_alert(alert, current_value, summary)
                    
            except Exception as e:
                logger.error(f"Error checking alert {alert.name}: {e}")
    
    def _evaluate_condition(self, value: float, condition: str, threshold: float) -> bool:
        """Evaluate alert condition"""
        if condition == ">":
            return value > threshold
        elif condition == "<":
            return value < threshold
        elif condition == ">=":
            return value >= threshold
        elif condition == "<=":
            return value <= threshold
        elif condition == "==":
            return abs(value - threshold) < 0.001  # Float equality
        elif condition == "!=":
            return abs(value - threshold) >= 0.001
        else:
            logger.error(f"Unknown condition: {condition}")
            return False
    
    def _trigger_alert(self, alert: PerformanceAlert, current_value: float, summary: Dict[str, Any]):
        """Trigger alert notifications"""
        alert_data = {
            'alert': alert,
            'current_value': current_value,
            'threshold': alert.threshold,
            'summary': summary,
            'timestamp': datetime.utcnow().isoformat()
        }
        
        logger.warning(f"ALERT: {alert.name} - {alert.description} (Current: {current_value:.2f}, Threshold: {alert.threshold})")
        
        # Notify all handlers
        for handler in self.alert_handlers:
            try:
                handler(alert_data)
            except Exception as e:
                logger.error(f"Error in alert handler: {e}")


class PerformanceProfiler:
    """Function and method performance profiler"""
    
    def __init__(self, collector: MetricCollector):
        self.collector = collector
        self.enabled = True
    
    def profile_function(self, func_name: str = None):
        """Decorator to profile function performance"""
        def decorator(func):
            @wraps(func)
            def wrapper(*args, **kwargs):
                if not self.enabled:
                    return func(*args, **kwargs)
                
                name = func_name or f"{func.__module__}.{func.__name__}"
                start_time = time.time()
                
                try:
                    result = func(*args, **kwargs)
                    self.collector.record_counter(f"function.{name}.calls", 1)
                    return result
                except Exception as e:
                    self.collector.record_counter(f"function.{name}.errors", 1)
                    raise
                finally:
                    duration_ms = (time.time() - start_time) * 1000
                    self.collector.record_timer(f"function.{name}.duration_ms", duration_ms)
                    
            return wrapper
        return decorator
    
    def time_block(self, block_name: str):
        """Context manager for timing code blocks"""
        return TimingContext(self.collector, block_name)


class TimingContext:
    """Context manager for timing operations"""
    
    def __init__(self, collector: MetricCollector, operation_name: str):
        self.collector = collector
        self.operation_name = operation_name
        self.start_time = None
    
    def __enter__(self):
        self.start_time = time.time()
        return self
    
    def __exit__(self, exc_type, exc_val, exc_tb):
        duration_ms = (time.time() - self.start_time) * 1000
        self.collector.record_timer(f"operation.{self.operation_name}.duration_ms", duration_ms)
        
        if exc_type is not None:
            self.collector.record_counter(f"operation.{self.operation_name}.errors", 1)
        else:
            self.collector.record_counter(f"operation.{self.operation_name}.success", 1)


class APMSystem:
    """
    Main Application Performance Monitoring system.
    
    Coordinates all performance monitoring components including
    metrics collection, system monitoring, alerting, and profiling.
    """
    
    def __init__(self):
        self.collector = MetricCollector()
        self.system_monitor = SystemMonitor(self.collector)
        self.alert_manager = AlertManager(self.collector)
        self.profiler = PerformanceProfiler(self.collector)
        self.running = False
        self._setup_alert_handlers()
        logger.info("APM system initialized")
    
    def _setup_alert_handlers(self):
        """Setup default alert handlers"""
        def log_alert_handler(alert_data):
            alert = alert_data['alert']
            logger.warning(
                f"PERFORMANCE ALERT: {alert.name} | "
                f"Current: {alert_data['current_value']:.2f} | "
                f"Threshold: {alert.threshold} | "
                f"Severity: {alert.severity.value}"
            )
        
        self.alert_manager.add_alert_handler(log_alert_handler)
    
    def start(self, system_monitor_interval: int = 30, alert_check_interval: int = 60):
        """Start the APM system"""
        if self.running:
            return
        
        self.running = True
        
        # Start system monitoring
        self.system_monitor.start_monitoring(system_monitor_interval)
        
        # Start alert checking thread
        self.alert_thread = threading.Thread(
            target=self._alert_check_loop,
            args=(alert_check_interval,),
            daemon=True
        )
        self.alert_thread.start()
        
        logger.info("APM system started")
    
    def stop(self):
        """Stop the APM system"""
        if not self.running:
            return
        
        self.running = False
        self.system_monitor.stop_monitoring()
        
        logger.info("APM system stopped")
    
    def _alert_check_loop(self, interval_seconds: int):
        """Alert checking loop"""
        while self.running:
            try:
                self.alert_manager.check_alerts()
                time.sleep(interval_seconds)
            except Exception as e:
                logger.error(f"Error in alert checking: {e}")
                time.sleep(interval_seconds)
    
    def record_request(self, endpoint: str, method: str, status_code: int, 
                      duration_ms: float, user_id: str = None):
        """Record HTTP request metrics"""
        tags = {
            'endpoint': endpoint,
            'method': method,
            'status': str(status_code),
            'status_class': f"{status_code // 100}xx"
        }
        
        if user_id:
            tags['user_id'] = user_id
        
        self.collector.record_counter("app.requests.total", 1, tags)
        self.collector.record_timer("app.response_time_ms", duration_ms, tags)
        
        if status_code >= 400:
            self.collector.record_counter("app.requests.errors", 1, tags)
    
    def record_agent_execution(self, agent_name: str, success: bool, duration_ms: float):
        """Record agent execution metrics"""
        tags = {
            'agent': agent_name,
            'success': str(success).lower()
        }
        
        self.collector.record_counter("agent.executions.total", 1, tags)
        self.collector.record_timer("agent.duration_ms", duration_ms, tags)
        
        if not success:
            self.collector.record_counter("agent.executions.errors", 1, tags)
    
    def get_dashboard_data(self) -> Dict[str, Any]:
        """Get comprehensive dashboard data"""
        now = datetime.utcnow()
        
        # System metrics
        system_metrics = {
            'cpu': self.collector.get_metric_summary("system.cpu.percent"),
            'memory': self.collector.get_metric_summary("system.memory.percent"),
            'disk': self.collector.get_metric_summary("system.disk.usage_percent"),
        }
        
        # Application metrics
        app_metrics = {
            'requests_total': self.collector.get_metric_summary("app.requests.total"),
            'response_time': self.collector.get_metric_summary("app.response_time_ms"),
            'errors_total': self.collector.get_metric_summary("app.requests.errors"),
        }
        
        # Agent metrics
        agent_metrics = {
            'executions_total': self.collector.get_metric_summary("agent.executions.total"),
            'execution_time': self.collector.get_metric_summary("agent.duration_ms"),
            'execution_errors': self.collector.get_metric_summary("agent.executions.errors"),
        }
        
        # Recent alerts
        recent_alerts = [
            {
                'name': alert.name,
                'severity': alert.severity.value,
                'last_triggered': alert.last_triggered.isoformat() if alert.last_triggered else None
            }
            for alert in self.alert_manager.alerts
            if alert.last_triggered and alert.last_triggered > (now - timedelta(hours=24))
        ]
        
        return {
            'timestamp': now.isoformat(),
            'system_metrics': system_metrics,
            'application_metrics': app_metrics,
            'agent_metrics': agent_metrics,
            'recent_alerts': recent_alerts,
            'uptime_seconds': (now - self.collector.start_time).total_seconds()
        }
    
    def export_metrics_json(self, filepath: str = None):
        """Export all metrics to JSON file"""
        if not filepath:
            filepath = os.path.join(project_root, "monitoring", f"metrics_{datetime.utcnow().strftime('%Y%m%d_%H%M%S')}.json")
        
        Path(filepath).parent.mkdir(parents=True, exist_ok=True)
        
        data = {
            'export_timestamp': datetime.utcnow().isoformat(),
            'dashboard_data': self.get_dashboard_data(),
            'all_metrics': self.collector.get_all_metrics()
        }
        
        with open(filepath, 'w') as f:
            json.dump(data, f, indent=2, default=str)
        
        logger.info(f"Metrics exported to {filepath}")


# Global APM system instance
_apm_system = None

def get_apm_system() -> APMSystem:
    """Get or create the global APM system instance"""
    global _apm_system
    if _apm_system is None:
        _apm_system = APMSystem()
    return _apm_system


# Convenient decorators for performance monitoring
def monitor_performance(func_name: str = None):
    """Decorator for monitoring function performance"""
    apm = get_apm_system()
    return apm.profiler.profile_function(func_name)


def time_operation(operation_name: str):
    """Context manager for timing operations"""
    apm = get_apm_system()
    return apm.profiler.time_block(operation_name)


def main():
    """Command line interface for APM system"""
    import argparse
    
    parser = argparse.ArgumentParser(description="JARVIS-MK42 APM System")
    parser.add_argument('--dashboard', action='store_true', help='Show dashboard data')
    parser.add_argument('--start', action='store_true', help='Start APM monitoring')
    parser.add_argument('--export', help='Export metrics to JSON file')
    
    args = parser.parse_args()
    
    apm = get_apm_system()
    
    if args.dashboard:
        dashboard = apm.get_dashboard_data()
        print(json.dumps(dashboard, indent=2))
    
    elif args.start:
        print("Starting APM system...")
        apm.start()
        print("APM system started. Press Ctrl+C to stop.")
        try:
            while True:
                time.sleep(1)
        except KeyboardInterrupt:
            print("\nStopping APM system...")
            apm.stop()
            print("APM system stopped.")
    
    elif args.export:
        apm.export_metrics_json(args.export)
        print(f"Metrics exported to {args.export}")
    
    else:
        print("JARVIS-MK42 APM System")
        print("Use --dashboard, --start, or --export <filename>")


if __name__ == "__main__":
    main()
