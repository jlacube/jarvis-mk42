"""
JARVIS-MK42 Monitoring Module
============================

This module provides comprehensive monitoring capabilities including:
- Application Performance Monitoring (APM)
- Centralized structured logging
- Alert management and notification system
- Enhanced health check endpoints
- System metrics collection and analysis
"""

from .apm_system import (
    APMSystem,
    MetricCollector,
    SystemMonitor,
    AlertManager as APMAlertManager,
    PerformanceProfiler,
    get_apm_system
)

from .centralized_logging import (
    CentralizedLoggingSystem,
    StructuredLogEntry,
    LogAggregator,
    EnhancedLogger,
    get_logging_system
)

from .alerting_system import (
    AlertManager,
    Alert,
    AlertRule,
    AlertSeverity,
    AlertStatus,
    NotificationChannel,
    NotificationConfig,
    get_alert_manager,
    create_alert
)

from .enhanced_health_checks import (
    HealthMonitor,
    HealthCheck,
    HealthCheckResult,
    HealthStatus,
    CheckType,
    SystemResourcesCheck,
    DatabaseConnectivityCheck,
    SecuritySystemCheck,
    MonitoringSystemCheck,
    ApplicationCheck,
    DependencyCheck,
    get_health_monitor,
    liveness_probe,
    readiness_probe,
    health_status
)

__version__ = "1.0.0"
__author__ = "JARVIS-MK42"

# Global system instances
_apm_system = None
_logging_system = None
_alert_manager = None
_health_monitor = None


def initialize_monitoring_systems():
    """Initialize all monitoring systems"""
    global _apm_system, _logging_system, _alert_manager, _health_monitor
    
    try:
        # Initialize systems
        _logging_system = get_logging_system()
        _apm_system = get_apm_system()
        _alert_manager = get_alert_manager()
        _health_monitor = get_health_monitor()
        
        # Create integration between systems
        _setup_monitoring_integration()
        
        print("✓ All monitoring systems initialized successfully")
        return True
        
    except Exception as e:
        print(f"✗ Failed to initialize monitoring systems: {e}")
        return False


def _setup_monitoring_integration():
    """Setup integration between monitoring systems"""
    try:
        # Connect APM alerts to alert manager
        apm = get_apm_system()
        alert_mgr = get_alert_manager()
        
        # Set up alert forwarding (if APM system supports it)
        if hasattr(apm, 'set_alert_callback'):
            apm.set_alert_callback(lambda rule, title, msg, data: 
                alert_mgr.create_alert(rule, title, msg, data))
        
        # Connect health monitor to alerting
        health_mon = get_health_monitor()
        
        # Add health check for alert system
        class AlertSystemHealthCheck(HealthCheck):
            def __init__(self):
                super().__init__("alert_system", CheckType.DIAGNOSTIC, timeout_seconds=5)
            
            async def _check(self):
                try:
                    dashboard = alert_mgr.get_alert_dashboard()
                    active_count = dashboard['statistics']['active_alerts']
                    
                    if active_count > 100:  # Too many active alerts
                        return HealthStatus.WARNING, f"High active alert count: {active_count}", {'active_alerts': active_count}
                    else:
                        return HealthStatus.HEALTHY, f"Alert system operational ({active_count} active alerts)", {'active_alerts': active_count}
                
                except Exception as e:
                    return HealthStatus.UNHEALTHY, f"Alert system check failed: {e}", {}
        
        health_mon.add_check(AlertSystemHealthCheck())
        
    except Exception as e:
        print(f"Warning: Could not setup monitoring integration: {e}")


def get_monitoring_status():
    """Get status of all monitoring systems"""
    status = {
        'apm_system': _apm_system is not None,
        'logging_system': _logging_system is not None,
        'alert_manager': _alert_manager is not None,
        'health_monitor': _health_monitor is not None,
        'integration_configured': True
    }
    
    return status


# Convenience functions for common operations
def log_structured(level, message, **kwargs):
    """Log a structured message"""
    try:
        logging_system = get_logging_system()
        logging_system.log_structured(level, message, **kwargs)
    except Exception:
        # Fallback to standard logging
        import logging
        logging.getLogger(__name__).log(getattr(logging, level.upper()), message)


def record_metric(name, value, tags=None):
    """Record a metric value"""
    try:
        apm_system = get_apm_system()
        apm_system.record_metric(name, value, tags or {})
    except Exception:
        # Silently fail if APM not available
        pass


def create_monitoring_alert(rule_name, title, message, source_data=None):
    """Create a monitoring alert"""
    try:
        alert_manager = get_alert_manager()
        return alert_manager.create_alert(rule_name, title, message, source_data)
    except Exception:
        # Fallback to console
        print(f"ALERT [{rule_name}]: {title} - {message}")
        return None


__all__ = [
    # APM System
    'APMSystem', 'MetricCollector', 'SystemMonitor', 'PerformanceProfiler', 'get_apm_system',
    
    # Logging System  
    'CentralizedLoggingSystem', 'StructuredLogEntry', 'LogAggregator', 'EnhancedLogger', 'get_logging_system',
    
    # Alert System
    'AlertManager', 'Alert', 'AlertRule', 'AlertSeverity', 'AlertStatus', 
    'NotificationChannel', 'NotificationConfig', 'get_alert_manager', 'create_alert',
    
    # Health System
    'HealthMonitor', 'HealthCheck', 'HealthCheckResult', 'HealthStatus', 'CheckType',
    'SystemResourcesCheck', 'DatabaseConnectivityCheck', 'SecuritySystemCheck', 
    'MonitoringSystemCheck', 'ApplicationCheck', 'DependencyCheck',
    'get_health_monitor', 'liveness_probe', 'readiness_probe', 'health_status',
    
    # Integration functions
    'initialize_monitoring_systems', 'get_monitoring_status',
    'log_structured', 'record_metric', 'create_monitoring_alert'
]
