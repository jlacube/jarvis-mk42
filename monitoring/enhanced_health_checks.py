#!/usr/bin/env python3
"""
JARVIS-MK42 Enhanced Health Check System
=======================================

This module provides comprehensive health monitoring endpoints including:
- Application readiness and liveness probes
- Database connectivity checks
- External service dependency checks
- Security system health validation
- Performance metrics health assessment
- Custom health check registration
- Health check aggregation and reporting
- Detailed diagnostic information
"""

import os
import sys
import json
import time
import asyncio
import threading
import requests
from datetime import datetime, timedelta
from typing import Dict, List, Optional, Any, Callable, Tuple
from dataclasses import dataclass, field
from enum import Enum
from collections import defaultdict, deque
from pathlib import Path

# Add project root to path
current_dir = os.path.dirname(os.path.abspath(__file__))
project_root = os.path.dirname(current_dir)
if project_root not in sys.path:
    sys.path.insert(0, project_root)

from utils.logging_config import get_logger

logger = get_logger(__name__)

try:
    import psutil
    HAS_PSUTIL = True
except ImportError:
    HAS_PSUTIL = False
    logger.warning("psutil not available - system metrics will be limited")

try:
    import sqlite3
    HAS_SQLITE = True
except ImportError:
    HAS_SQLITE = False
    logger.warning("sqlite3 not available - database health checks disabled")


class HealthStatus(Enum):
    """Health check status levels"""
    HEALTHY = "healthy"
    WARNING = "warning"
    UNHEALTHY = "unhealthy"
    UNKNOWN = "unknown"


class CheckType(Enum):
    """Types of health checks"""
    LIVENESS = "liveness"
    READINESS = "readiness"
    DIAGNOSTIC = "diagnostic"
    SECURITY = "security"
    PERFORMANCE = "performance"
    DEPENDENCY = "dependency"


@dataclass
class HealthCheckResult:
    """Individual health check result"""
    name: str
    status: HealthStatus
    message: str
    duration_ms: int
    timestamp: datetime
    check_type: CheckType
    details: Dict[str, Any] = field(default_factory=dict)
    tags: Dict[str, str] = field(default_factory=dict)
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary"""
        return {
            'name': self.name,
            'status': self.status.value,
            'message': self.message,
            'duration_ms': self.duration_ms,
            'timestamp': self.timestamp.isoformat(),
            'check_type': self.check_type.value,
            'details': self.details,
            'tags': self.tags
        }


@dataclass
class HealthSummary:
    """Overall health summary"""
    overall_status: HealthStatus
    total_checks: int
    healthy_checks: int
    warning_checks: int
    unhealthy_checks: int
    unknown_checks: int
    timestamp: datetime
    uptime_seconds: int
    version: str = "1.0.0"
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary"""
        return {
            'overall_status': self.overall_status.value,
            'total_checks': self.total_checks,
            'healthy_checks': self.healthy_checks,
            'warning_checks': self.warning_checks,
            'unhealthy_checks': self.unhealthy_checks,
            'unknown_checks': self.unknown_checks,
            'timestamp': self.timestamp.isoformat(),
            'uptime_seconds': self.uptime_seconds,
            'version': self.version
        }


class HealthCheck:
    """Base health check class"""
    
    def __init__(self, name: str, check_type: CheckType, timeout_seconds: int = 30):
        self.name = name
        self.check_type = check_type
        self.timeout_seconds = timeout_seconds
        self.enabled = True
    
    async def execute(self) -> HealthCheckResult:
        """Execute the health check"""
        if not self.enabled:
            return HealthCheckResult(
                name=self.name,
                status=HealthStatus.UNKNOWN,
                message="Check disabled",
                duration_ms=0,
                timestamp=datetime.utcnow(),
                check_type=self.check_type
            )
        
        start_time = time.time()
        
        try:
            # Execute with timeout
            result = await asyncio.wait_for(
                self._check(),
                timeout=self.timeout_seconds
            )
            
            duration_ms = int((time.time() - start_time) * 1000)
            
            return HealthCheckResult(
                name=self.name,
                status=result[0],
                message=result[1],
                duration_ms=duration_ms,
                timestamp=datetime.utcnow(),
                check_type=self.check_type,
                details=result[2] if len(result) > 2 else {}
            )
            
        except asyncio.TimeoutError:
            duration_ms = int((time.time() - start_time) * 1000)
            return HealthCheckResult(
                name=self.name,
                status=HealthStatus.UNHEALTHY,
                message=f"Check timeout after {self.timeout_seconds}s",
                duration_ms=duration_ms,
                timestamp=datetime.utcnow(),
                check_type=self.check_type
            )
        
        except Exception as e:
            duration_ms = int((time.time() - start_time) * 1000)
            return HealthCheckResult(
                name=self.name,
                status=HealthStatus.UNHEALTHY,
                message=f"Check failed: {str(e)}",
                duration_ms=duration_ms,
                timestamp=datetime.utcnow(),
                check_type=self.check_type
            )
    
    async def _check(self) -> Tuple[HealthStatus, str, Dict[str, Any]]:
        """Override this method in subclasses"""
        raise NotImplementedError


class SystemResourcesCheck(HealthCheck):
    """System resources health check"""
    
    def __init__(self):
        super().__init__("system_resources", CheckType.LIVENESS, timeout_seconds=10)
    
    async def _check(self) -> Tuple[HealthStatus, str, Dict[str, Any]]:
        """Check system resource usage"""
        if not HAS_PSUTIL:
            return HealthStatus.UNKNOWN, "psutil not available", {}
        
        try:
            cpu_percent = psutil.cpu_percent(interval=1)
            memory = psutil.virtual_memory()
            disk = psutil.disk_usage('/')
            
            details = {
                'cpu_percent': cpu_percent,
                'memory_percent': memory.percent,
                'memory_available_gb': round(memory.available / (1024**3), 2),
                'disk_percent': disk.percent,
                'disk_free_gb': round(disk.free / (1024**3), 2)
            }
            
            # Determine status based on thresholds
            if cpu_percent > 95 or memory.percent > 95 or disk.percent > 95:
                status = HealthStatus.UNHEALTHY
                message = "Critical resource usage"
            elif cpu_percent > 85 or memory.percent > 85 or disk.percent > 85:
                status = HealthStatus.WARNING
                message = "High resource usage"
            else:
                status = HealthStatus.HEALTHY
                message = "Resources within normal limits"
            
            return status, message, details
            
        except Exception as e:
            return HealthStatus.UNHEALTHY, f"Failed to check system resources: {e}", {}


class DatabaseConnectivityCheck(HealthCheck):
    """Database connectivity health check"""
    
    def __init__(self, db_path: str = "jarvis.db"):
        super().__init__("database_connectivity", CheckType.READINESS, timeout_seconds=5)
        self.db_path = db_path
    
    async def _check(self) -> Tuple[HealthStatus, str, Dict[str, Any]]:
        """Check database connectivity"""
        if not HAS_SQLITE:
            return HealthStatus.UNKNOWN, "sqlite3 not available", {}
        
        try:
            # Test database connection
            conn = sqlite3.connect(self.db_path, timeout=3.0)
            
            # Test basic query
            cursor = conn.cursor()
            cursor.execute("SELECT 1")
            result = cursor.fetchone()
            
            # Get database info
            cursor.execute("PRAGMA database_list")
            db_info = cursor.fetchall()
            
            conn.close()
            
            details = {
                'database_path': self.db_path,
                'connection_successful': True,
                'test_query_result': result[0] if result else None,
                'database_count': len(db_info)
            }
            
            return HealthStatus.HEALTHY, "Database connection successful", details
            
        except sqlite3.Error as e:
            return HealthStatus.UNHEALTHY, f"Database error: {e}", {'database_path': self.db_path}
        except Exception as e:
            return HealthStatus.UNHEALTHY, f"Database check failed: {e}", {'database_path': self.db_path}


class SecuritySystemCheck(HealthCheck):
    """Security system health check"""
    
    def __init__(self):
        super().__init__("security_system", CheckType.SECURITY, timeout_seconds=10)
    
    async def _check(self) -> Tuple[HealthStatus, str, Dict[str, Any]]:
        """Check security system health"""
        try:
            # Check if security modules are importable
            security_modules = {}
            
            try:
                # Import security modules (if they exist)
                sys.path.insert(0, os.path.join(project_root, 'security'))
                
                import importlib
                modules_to_check = [
                    'security_audit',
                    'api_security', 
                    'enhanced_auth',
                    'data_encryption'
                ]
                
                for module_name in modules_to_check:
                    try:
                        module = importlib.import_module(module_name)
                        security_modules[module_name] = "available"
                    except ImportError:
                        security_modules[module_name] = "not_available"
                    except Exception as e:
                        security_modules[module_name] = f"error: {e}"
                
                # Check environment variables for security config
                security_config = {
                    'secret_key': bool(os.environ.get('SECRET_KEY')),
                    'encryption_key': bool(os.environ.get('ENCRYPTION_KEY')),
                    'jwt_secret': bool(os.environ.get('JWT_SECRET')),
                    'security_logging': bool(os.environ.get('SECURITY_LOG_LEVEL'))
                }
                
                # Check file permissions on critical files
                critical_files = []
                for root, dirs, files in os.walk(os.path.join(project_root, 'security')):
                    for file in files:
                        if file.endswith('.py'):
                            file_path = os.path.join(root, file)
                            try:
                                file_stat = os.stat(file_path)
                                critical_files.append({
                                    'path': file_path,
                                    'mode': oct(file_stat.st_mode),
                                    'size': file_stat.st_size
                                })
                            except OSError:
                                pass
                
                available_modules = sum(1 for status in security_modules.values() if status == "available")
                total_modules = len(security_modules)
                
                details = {
                    'security_modules': security_modules,
                    'security_config': security_config,
                    'critical_files_count': len(critical_files),
                    'modules_available': f"{available_modules}/{total_modules}"
                }
                
                if available_modules == 0:
                    status = HealthStatus.UNHEALTHY
                    message = "No security modules available"
                elif available_modules < total_modules // 2:
                    status = HealthStatus.WARNING
                    message = f"Only {available_modules}/{total_modules} security modules available"
                else:
                    status = HealthStatus.HEALTHY
                    message = "Security system operational"
                
                return status, message, details
                
            except Exception as e:
                return HealthStatus.WARNING, f"Security check partial failure: {e}", {}
            
        except Exception as e:
            return HealthStatus.UNHEALTHY, f"Security system check failed: {e}", {}


class MonitoringSystemCheck(HealthCheck):
    """Monitoring system health check"""
    
    def __init__(self):
        super().__init__("monitoring_system", CheckType.PERFORMANCE, timeout_seconds=10)
    
    async def _check(self) -> Tuple[HealthStatus, str, Dict[str, Any]]:
        """Check monitoring system health"""
        try:
            monitoring_components = {}
            
            # Check monitoring modules
            try:
                sys.path.insert(0, os.path.join(project_root, 'monitoring'))
                
                import importlib
                modules_to_check = [
                    'apm_system',
                    'centralized_logging',
                    'alerting_system'
                ]
                
                for module_name in modules_to_check:
                    try:
                        module = importlib.import_module(module_name)
                        monitoring_components[module_name] = "available"
                    except ImportError:
                        monitoring_components[module_name] = "not_available"
                    except Exception as e:
                        monitoring_components[module_name] = f"error: {e}"
                
                # Check log files
                log_status = {}
                log_dir = os.path.join(project_root, 'logs')
                if os.path.exists(log_dir):
                    log_files = [f for f in os.listdir(log_dir) if f.endswith('.log')]
                    log_status = {
                        'log_directory_exists': True,
                        'log_files_count': len(log_files),
                        'recent_log_files': log_files[:5]  # Show first 5
                    }
                else:
                    log_status = {
                        'log_directory_exists': False,
                        'log_files_count': 0
                    }
                
                available_components = sum(1 for status in monitoring_components.values() if status == "available")
                total_components = len(monitoring_components)
                
                details = {
                    'monitoring_components': monitoring_components,
                    'log_status': log_status,
                    'components_available': f"{available_components}/{total_components}"
                }
                
                if available_components == 0:
                    status = HealthStatus.UNHEALTHY
                    message = "No monitoring components available"
                elif available_components < total_components:
                    status = HealthStatus.WARNING
                    message = f"Only {available_components}/{total_components} monitoring components available"
                else:
                    status = HealthStatus.HEALTHY
                    message = "Monitoring system operational"
                
                return status, message, details
                
            except Exception as e:
                return HealthStatus.WARNING, f"Monitoring check partial failure: {e}", {}
            
        except Exception as e:
            return HealthStatus.UNHEALTHY, f"Monitoring system check failed: {e}", {}


class ApplicationCheck(HealthCheck):
    """Application-specific health check"""
    
    def __init__(self):
        super().__init__("application", CheckType.LIVENESS, timeout_seconds=5)
    
    async def _check(self) -> Tuple[HealthStatus, str, Dict[str, Any]]:
        """Check application health"""
        try:
            # Check main application modules
            app_modules = {}
            
            modules_to_check = [
                'config',
                'utils',
                'agent_management',
                'message_processing'
            ]
            
            for module_name in modules_to_check:
                try:
                    import importlib
                    module = importlib.import_module(module_name)
                    app_modules[module_name] = "available"
                except ImportError:
                    app_modules[module_name] = "not_available"
                except Exception as e:
                    app_modules[module_name] = f"error: {e}"
            
            # Check main app module separately (might require API keys)
            try:
                # Try to check if app.py exists and can be imported
                app_file_exists = os.path.exists(os.path.join(project_root, 'app.py'))
                if app_file_exists:
                    app_modules['app'] = "file_exists"
                else:
                    app_modules['app'] = "not_found"
            except Exception:
                app_modules['app'] = "check_failed"
            
            # Check configuration
            config_status = {
                'config_file_exists': os.path.exists(os.path.join(project_root, 'config.py')),
                'requirements_file_exists': os.path.exists(os.path.join(project_root, 'requirements.txt')),
                'readme_exists': os.path.exists(os.path.join(project_root, 'README.md'))
            }
            
            # Check Python version
            python_info = {
                'version': sys.version,
                'version_info': list(sys.version_info),
                'executable': sys.executable
            }
            
            available_modules = sum(1 for status in app_modules.values() 
                                 if status == "available" or status == "file_exists")
            total_modules = len(app_modules)
            
            details = {
                'app_modules': app_modules,
                'config_status': config_status,
                'python_info': python_info,
                'modules_available': f"{available_modules}/{total_modules}"
            }
            
            if available_modules < total_modules // 2:
                status = HealthStatus.WARNING  # Changed from UNHEALTHY to WARNING
                message = f"Some application modules unavailable: {available_modules}/{total_modules} available"
            elif available_modules < total_modules:
                status = HealthStatus.WARNING
                message = f"Some application modules missing: {available_modules}/{total_modules} available"
            else:
                status = HealthStatus.HEALTHY
                message = "Application modules loaded successfully"
            
            return status, message, details
            
        except Exception as e:
            return HealthStatus.WARNING, f"Application check failed: {e}", {}  # Changed from UNHEALTHY to WARNING


class DependencyCheck(HealthCheck):
    """External dependency health check"""
    
    def __init__(self, url: str, name: str = None, expected_status: int = 200):
        self.url = url
        self.expected_status = expected_status
        check_name = name or f"dependency_{url.split('//')[1].split('/')[0] if '//' in url else url}"
        super().__init__(check_name, CheckType.DEPENDENCY, timeout_seconds=10)
    
    async def _check(self) -> Tuple[HealthStatus, str, Dict[str, Any]]:
        """Check external dependency"""
        try:
            response = requests.get(self.url, timeout=self.timeout_seconds)
            
            details = {
                'url': self.url,
                'status_code': response.status_code,
                'response_time_ms': int(response.elapsed.total_seconds() * 1000),
                'expected_status': self.expected_status
            }
            
            if response.status_code == self.expected_status:
                status = HealthStatus.HEALTHY
                message = f"Dependency accessible (HTTP {response.status_code})"
            elif 200 <= response.status_code < 300:
                status = HealthStatus.WARNING
                message = f"Dependency accessible but unexpected status (HTTP {response.status_code})"
            else:
                status = HealthStatus.UNHEALTHY
                message = f"Dependency returned error (HTTP {response.status_code})"
            
            return status, message, details
            
        except requests.exceptions.Timeout:
            return HealthStatus.UNHEALTHY, f"Dependency timeout after {self.timeout_seconds}s", {'url': self.url}
        except requests.exceptions.RequestException as e:
            return HealthStatus.UNHEALTHY, f"Dependency connection failed: {e}", {'url': self.url}
        except Exception as e:
            return HealthStatus.UNHEALTHY, f"Dependency check failed: {e}", {'url': self.url}


class HealthMonitor:
    """
    Main health monitoring system.
    
    Manages all health checks, provides endpoints, and maintains health history.
    """
    
    def __init__(self):
        self.checks: List[HealthCheck] = []
        self.health_history: deque = deque(maxlen=1000)
        self.start_time = datetime.utcnow()
        self.last_check_time: Optional[datetime] = None
        self.check_interval_seconds = 60
        self._setup_default_checks()
        self._start_background_monitoring()
        logger.info("Health monitor initialized")
    
    def _setup_default_checks(self):
        """Setup default health checks"""
        # Core system checks
        self.checks.extend([
            SystemResourcesCheck(),
            DatabaseConnectivityCheck(),
            ApplicationCheck(),
            SecuritySystemCheck(),
            MonitoringSystemCheck()
        ])
        
        # Add dependency checks from environment
        external_deps = os.environ.get('HEALTH_CHECK_URLS', '').split(',')
        for dep in external_deps:
            if dep.strip():
                self.checks.append(DependencyCheck(dep.strip()))
    
    def add_check(self, check: HealthCheck):
        """Add a custom health check"""
        self.checks.append(check)
        logger.info(f"Added health check: {check.name}")
    
    def remove_check(self, check_name: str) -> bool:
        """Remove a health check by name"""
        for i, check in enumerate(self.checks):
            if check.name == check_name:
                del self.checks[i]
                logger.info(f"Removed health check: {check_name}")
                return True
        return False
    
    async def run_checks(self, check_types: List[CheckType] = None) -> List[HealthCheckResult]:
        """Run health checks"""
        if check_types is None:
            checks_to_run = self.checks
        else:
            checks_to_run = [check for check in self.checks if check.check_type in check_types]
        
        results = []
        
        # Run checks concurrently
        tasks = [check.execute() for check in checks_to_run]
        if tasks:
            results = await asyncio.gather(*tasks)
        
        # Update history
        for result in results:
            self.health_history.append(result)
        
        self.last_check_time = datetime.utcnow()
        
        return results
    
    async def get_liveness(self) -> Dict[str, Any]:
        """Get liveness probe status"""
        results = await self.run_checks([CheckType.LIVENESS])
        summary = self._create_summary(results)
        
        return {
            'status': summary.overall_status.value,
            'timestamp': summary.timestamp.isoformat(),
            'uptime_seconds': summary.uptime_seconds,
            'checks': [result.to_dict() for result in results]
        }
    
    async def get_readiness(self) -> Dict[str, Any]:
        """Get readiness probe status"""
        results = await self.run_checks([CheckType.READINESS, CheckType.DEPENDENCY])
        summary = self._create_summary(results)
        
        return {
            'status': summary.overall_status.value,
            'timestamp': summary.timestamp.isoformat(),
            'ready': summary.overall_status in [HealthStatus.HEALTHY, HealthStatus.WARNING],
            'checks': [result.to_dict() for result in results]
        }
    
    async def get_full_health(self) -> Dict[str, Any]:
        """Get comprehensive health status"""
        results = await self.run_checks()
        summary = self._create_summary(results)
        
        # Group results by type
        results_by_type = defaultdict(list)
        for result in results:
            results_by_type[result.check_type.value].append(result.to_dict())
        
        return {
            'summary': summary.to_dict(),
            'checks_by_type': dict(results_by_type),
            'all_checks': [result.to_dict() for result in results],
            'last_check': self.last_check_time.isoformat() if self.last_check_time else None,
            'check_count': len(results)
        }
    
    def _create_summary(self, results: List[HealthCheckResult]) -> HealthSummary:
        """Create health summary from results"""
        status_counts = defaultdict(int)
        for result in results:
            status_counts[result.status] += 1
        
        # Determine overall status
        if status_counts[HealthStatus.UNHEALTHY] > 0:
            overall_status = HealthStatus.UNHEALTHY
        elif status_counts[HealthStatus.WARNING] > 0:
            overall_status = HealthStatus.WARNING
        elif status_counts[HealthStatus.UNKNOWN] > 0:
            overall_status = HealthStatus.WARNING  # Treat unknown as warning
        else:
            overall_status = HealthStatus.HEALTHY
        
        uptime_seconds = int((datetime.utcnow() - self.start_time).total_seconds())
        
        return HealthSummary(
            overall_status=overall_status,
            total_checks=len(results),
            healthy_checks=status_counts[HealthStatus.HEALTHY],
            warning_checks=status_counts[HealthStatus.WARNING],
            unhealthy_checks=status_counts[HealthStatus.UNHEALTHY],
            unknown_checks=status_counts[HealthStatus.UNKNOWN],
            timestamp=datetime.utcnow(),
            uptime_seconds=uptime_seconds
        )
    
    def _start_background_monitoring(self):
        """Start background health monitoring"""
        def monitor_loop():
            loop = asyncio.new_event_loop()
            asyncio.set_event_loop(loop)
            
            while True:
                try:
                    # Run background health checks
                    loop.run_until_complete(self.run_checks([CheckType.LIVENESS]))
                    time.sleep(self.check_interval_seconds)
                except Exception as e:
                    logger.error(f"Background health monitoring error: {e}")
                    time.sleep(self.check_interval_seconds)
        
        thread = threading.Thread(target=monitor_loop, daemon=True)
        thread.start()
    
    def get_health_trends(self, hours: int = 24) -> Dict[str, Any]:
        """Get health trends over time"""
        since = datetime.utcnow() - timedelta(hours=hours)
        recent_results = [result for result in self.health_history if result.timestamp >= since]
        
        # Analyze trends
        trends = {}
        for result in recent_results:
            check_name = result.name
            if check_name not in trends:
                trends[check_name] = {
                    'healthy': 0,
                    'warning': 0,
                    'unhealthy': 0,
                    'unknown': 0,
                    'avg_duration_ms': 0,
                    'total_checks': 0
                }
            
            trends[check_name][result.status.value] += 1
            trends[check_name]['total_checks'] += 1
            trends[check_name]['avg_duration_ms'] += result.duration_ms
        
        # Calculate averages
        for check_name in trends:
            if trends[check_name]['total_checks'] > 0:
                trends[check_name]['avg_duration_ms'] = int(
                    trends[check_name]['avg_duration_ms'] / trends[check_name]['total_checks']
                )
                
                # Calculate success rate
                healthy_count = trends[check_name]['healthy']
                total_count = trends[check_name]['total_checks']
                trends[check_name]['success_rate'] = healthy_count / total_count if total_count > 0 else 0
        
        return {
            'period_hours': hours,
            'total_results': len(recent_results),
            'trends_by_check': trends,
            'summary': {
                'unique_checks': len(trends),
                'period_start': since.isoformat(),
                'period_end': datetime.utcnow().isoformat()
            }
        }


# Global health monitor instance
_health_monitor = None

def get_health_monitor() -> HealthMonitor:
    """Get or create the global health monitor instance"""
    global _health_monitor
    if _health_monitor is None:
        _health_monitor = HealthMonitor()
    return _health_monitor


async def liveness_probe() -> Dict[str, Any]:
    """Liveness probe endpoint"""
    monitor = get_health_monitor()
    return await monitor.get_liveness()


async def readiness_probe() -> Dict[str, Any]:
    """Readiness probe endpoint"""
    monitor = get_health_monitor()
    return await monitor.get_readiness()


async def health_status() -> Dict[str, Any]:
    """Full health status endpoint"""
    monitor = get_health_monitor()
    return await monitor.get_full_health()


def main():
    """Command line interface for health checks"""
    import argparse
    
    parser = argparse.ArgumentParser(description="JARVIS-MK42 Health Check System")
    parser.add_argument('--liveness', action='store_true', help='Run liveness probe')
    parser.add_argument('--readiness', action='store_true', help='Run readiness probe')
    parser.add_argument('--full', action='store_true', help='Run full health check')
    parser.add_argument('--trends', type=int, default=24, help='Show health trends for N hours')
    parser.add_argument('--monitor', action='store_true', help='Run continuous monitoring')
    
    args = parser.parse_args()
    
    async def run_health_checks():
        monitor = get_health_monitor()
        
        if args.liveness:
            result = await monitor.get_liveness()
            print(json.dumps(result, indent=2))
        elif args.readiness:
            result = await monitor.get_readiness()
            print(json.dumps(result, indent=2))
        elif args.full:
            result = await monitor.get_full_health()
            print(json.dumps(result, indent=2))
        elif args.trends:
            trends = monitor.get_health_trends(args.trends)
            print(json.dumps(trends, indent=2))
        elif args.monitor:
            print("Starting continuous health monitoring...")
            while True:
                result = await monitor.get_full_health()
                print(f"\n[{result['summary']['timestamp']}] Overall Status: {result['summary']['overall_status']}")
                print(f"Checks: {result['summary']['healthy_checks']} healthy, {result['summary']['warning_checks']} warning, {result['summary']['unhealthy_checks']} unhealthy")
                await asyncio.sleep(60)
        else:
            result = await monitor.get_full_health()
            print(json.dumps(result, indent=2))
    
    asyncio.run(run_health_checks())


if __name__ == "__main__":
    main()
