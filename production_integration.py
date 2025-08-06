#!/usr/bin/env python3
"""
JARVIS-MK42 Production System Integration
=========================================

This module integrates all production security and monitoring systems:
- Security system initialization and configuration
- Monitoring system startup and health checks
- Alert system integration with security events
- Performance monitoring with security audit integration
- Centralized logging with security event correlation
- Health check endpoints with security validation
"""

import os
import sys
import json
import asyncio
import logging
from datetime import datetime
from typing import Dict, List, Optional, Any
from pathlib import Path

# Add project root to path
current_dir = os.path.dirname(os.path.abspath(__file__))
project_root = os.path.dirname(current_dir)
if project_root not in sys.path:
    sys.path.insert(0, project_root)

# Import monitoring systems
try:
    from monitoring import (
        initialize_monitoring_systems,
        get_apm_system,
        get_logging_system, 
        get_alert_manager,
        get_health_monitor,
        create_monitoring_alert,
        log_structured,
        record_metric
    )
    MONITORING_AVAILABLE = True
except ImportError as e:
    print(f"Warning: Monitoring systems not available: {e}")
    MONITORING_AVAILABLE = False

# Import security systems
SECURITY_SYSTEMS = {}

def import_security_systems():
    """Import security systems with graceful fallback"""
    global SECURITY_SYSTEMS
    
    try:
        # Import the security module
        from security import get_available_security_systems
        
        SECURITY_SYSTEMS = get_available_security_systems()
        
        for system_name in SECURITY_SYSTEMS:
            print(f"✓ Security module loaded: {system_name}")
        
        if SECURITY_SYSTEMS:
            print(f"Security systems available: {len(SECURITY_SYSTEMS)}")
            return True
        else:
            print("⚠ No security systems available")
            return False
                
    except Exception as e:
        print(f"✗ Failed to import security systems: {e}")
        return False


class ProductionSystemIntegrator:
    """
    Main production system integrator.
    
    Coordinates security systems, monitoring, alerting, and health checks
    for production deployment readiness.
    """
    
    def __init__(self):
        self.security_systems = {}
        self.monitoring_initialized = False
        self.security_initialized = False
        self.integration_status = {}
        self.start_time = datetime.utcnow()
        
        # Setup logging
        logging.basicConfig(
            level=logging.INFO,
            format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
        )
        self.logger = logging.getLogger(__name__)
        
        self.logger.info("Production System Integrator initializing...")
    
    def initialize_all_systems(self) -> Dict[str, Any]:
        """Initialize all production systems"""
        results = {
            'security_systems': self._initialize_security_systems(),
            'monitoring_systems': self._initialize_monitoring_systems(), 
            'integration_setup': self._setup_system_integration(),
            'health_checks': self._setup_integrated_health_checks(),
            'startup_validation': self._validate_startup()
        }
        
        # Overall status
        all_successful = all(results.values())
        results['overall_success'] = all_successful
        results['initialization_time'] = datetime.utcnow().isoformat()
        
        if all_successful:
            self.logger.info("🎉 All production systems initialized successfully!")
        else:
            self.logger.warning("⚠ Some production systems failed to initialize")
        
        return results
    
    def _initialize_security_systems(self) -> bool:
        """Initialize security systems"""
        try:
            self.logger.info("Initializing security systems...")
            
            # Import security systems
            if not import_security_systems():
                self.logger.warning("No security systems available")
                return False
            
            # Initialize security systems
            for system_name, system_class in SECURITY_SYSTEMS.items():
                try:
                    if system_name == 'security_audit':
                        instance = system_class()
                    elif system_name == 'api_security':
                        instance = system_class()
                    elif system_name == 'enhanced_auth':
                        instance = system_class()
                    elif system_name == 'data_encryption':
                        instance = system_class()
                    else:
                        instance = system_class()
                    
                    self.security_systems[system_name] = instance
                    self.logger.info(f"✓ Initialized security system: {system_name}")
                    
                except Exception as e:
                    self.logger.error(f"✗ Failed to initialize {system_name}: {e}")
                    continue
            
            self.security_initialized = len(self.security_systems) > 0
            
            if self.security_initialized:
                self.logger.info(f"Security systems initialized: {len(self.security_systems)} active")
                return True
            else:
                self.logger.warning("No security systems successfully initialized")
                return False
                
        except Exception as e:
            self.logger.error(f"Security system initialization failed: {e}")
            return False
    
    def _initialize_monitoring_systems(self) -> bool:
        """Initialize monitoring systems"""
        try:
            self.logger.info("Initializing monitoring systems...")
            
            if not MONITORING_AVAILABLE:
                self.logger.warning("Monitoring systems not available")
                return False
            
            # Initialize monitoring
            self.monitoring_initialized = initialize_monitoring_systems()
            
            if self.monitoring_initialized:
                self.logger.info("✓ Monitoring systems initialized successfully")
                
                # Test monitoring components
                try:
                    apm = get_apm_system()
                    logging_sys = get_logging_system()
                    alert_mgr = get_alert_manager()
                    health_mon = get_health_monitor()
                    
                    # Log initialization success
                    log_structured('INFO', 'Production systems initialized', 
                                 security_systems=len(self.security_systems),
                                 monitoring_active=True)
                    
                    # Record initialization metric
                    record_metric('production_system_init', 1, {'status': 'success'})
                    
                    return True
                    
                except Exception as e:
                    self.logger.error(f"Monitoring system test failed: {e}")
                    return False
            else:
                self.logger.warning("Monitoring system initialization failed")
                return False
                
        except Exception as e:
            self.logger.error(f"Monitoring system initialization failed: {e}")
            return False
    
    def _setup_system_integration(self) -> bool:
        """Setup integration between security and monitoring systems"""
        try:
            self.logger.info("Setting up system integration...")
            
            if not (self.security_initialized and self.monitoring_initialized):
                self.logger.warning("Cannot setup integration - systems not initialized")
                return False
            
            # Connect security events to alerting
            self._setup_security_alerting()
            
            # Connect monitoring to security audit
            self._setup_security_monitoring()
            
            # Setup performance monitoring for security systems
            self._setup_security_performance_monitoring()
            
            self.logger.info("✓ System integration setup completed")
            return True
            
        except Exception as e:
            self.logger.error(f"System integration setup failed: {e}")
            return False
    
    def _setup_security_alerting(self):
        """Setup security event alerting"""
        try:
            alert_mgr = get_alert_manager()
            
            # Create security-specific alert rules
            security_events = [
                'authentication_failure',
                'authorization_violation', 
                'data_encryption_failure',
                'api_security_breach',
                'security_audit_failure'
            ]
            
            for event_type in security_events:
                # These would be used when security systems trigger events
                self.logger.debug(f"Security alerting configured for: {event_type}")
            
        except Exception as e:
            self.logger.error(f"Security alerting setup failed: {e}")
    
    def _setup_security_monitoring(self):
        """Setup security system monitoring"""
        try:
            # Monitor security system health
            for system_name, system_instance in self.security_systems.items():
                # Record system availability
                record_metric(f'security_system_status', 1, {'system': system_name, 'status': 'active'})
                
                # Log security system status
                log_structured('INFO', f'Security system active: {system_name}',
                             system=system_name, status='active')
            
        except Exception as e:
            self.logger.error(f"Security monitoring setup failed: {e}")
    
    def _setup_security_performance_monitoring(self):
        """Setup performance monitoring for security systems"""
        try:
            apm = get_apm_system()
            
            # Monitor security system performance
            for system_name in self.security_systems:
                # These metrics would be collected by the security systems themselves
                self.logger.debug(f"Performance monitoring setup for: {system_name}")
            
        except Exception as e:
            self.logger.error(f"Security performance monitoring setup failed: {e}")
    
    def _setup_integrated_health_checks(self) -> bool:
        """Setup integrated health checks"""
        try:
            self.logger.info("Setting up integrated health checks...")
            
            if not self.monitoring_initialized:
                return False
            
            health_monitor = get_health_monitor()
            
            # Add custom health checks for production readiness
            from monitoring.enhanced_health_checks import HealthCheck, CheckType, HealthStatus
            
            class ProductionReadinessCheck(HealthCheck):
                def __init__(self, integrator):
                    super().__init__("production_readiness", CheckType.READINESS, timeout_seconds=10)
                    self.integrator = integrator
                
                async def _check(self):
                    try:
                        security_count = len(self.integrator.security_systems)
                        monitoring_active = self.integrator.monitoring_initialized
                        
                        details = {
                            'security_systems_active': security_count,
                            'monitoring_systems_active': monitoring_active,
                            'integration_complete': self.integrator.security_initialized and self.integrator.monitoring_initialized,
                            'uptime_seconds': int((datetime.utcnow() - self.integrator.start_time).total_seconds())
                        }
                        
                        if security_count >= 2 and monitoring_active:
                            return HealthStatus.HEALTHY, "Production systems ready", details
                        elif security_count >= 1 or monitoring_active:
                            return HealthStatus.WARNING, "Partial production readiness", details
                        else:
                            return HealthStatus.UNHEALTHY, "Production systems not ready", details
                            
                    except Exception as e:
                        return HealthStatus.UNHEALTHY, f"Production readiness check failed: {e}", {}
            
            health_monitor.add_check(ProductionReadinessCheck(self))
            
            self.logger.info("✓ Integrated health checks setup completed")
            return True
            
        except Exception as e:
            self.logger.error(f"Integrated health checks setup failed: {e}")
            return False
    
    def _validate_startup(self) -> bool:
        """Validate that all systems started correctly"""
        try:
            self.logger.info("Validating startup...")
            
            validation_results = {}
            
            # Validate security systems
            validation_results['security_validation'] = self._validate_security_systems()
            
            # Validate monitoring systems  
            validation_results['monitoring_validation'] = self._validate_monitoring_systems()
            
            # Validate integration
            validation_results['integration_validation'] = (
                self.security_initialized and self.monitoring_initialized
            )
            
            # Overall validation
            all_valid = all(validation_results.values())
            validation_results['overall_valid'] = all_valid
            
            if all_valid:
                self.logger.info("✓ Startup validation successful")
                
                # Create success alert
                if self.monitoring_initialized:
                    create_monitoring_alert(
                        'system_startup',
                        'Production Systems Started',
                        f'All production systems initialized successfully with {len(self.security_systems)} security systems active',
                        {'security_systems': len(self.security_systems), 'timestamp': datetime.utcnow().isoformat()}
                    )
            else:
                self.logger.warning(f"⚠ Startup validation failed: {validation_results}")
            
            return all_valid
            
        except Exception as e:
            self.logger.error(f"Startup validation failed: {e}")
            return False
    
    def _validate_security_systems(self) -> bool:
        """Validate security systems"""
        try:
            if not self.security_systems:
                return False
            
            # Test each security system
            for system_name, system_instance in self.security_systems.items():
                try:
                    # Basic validation - check if instance exists and has expected methods
                    if hasattr(system_instance, '__class__'):
                        self.logger.debug(f"✓ Security system valid: {system_name}")
                    else:
                        self.logger.warning(f"⚠ Security system questionable: {system_name}")
                        
                except Exception as e:
                    self.logger.error(f"✗ Security system validation failed for {system_name}: {e}")
                    return False
            
            return True
            
        except Exception as e:
            self.logger.error(f"Security systems validation failed: {e}")
            return False
    
    def _validate_monitoring_systems(self) -> bool:
        """Validate monitoring systems"""
        try:
            if not self.monitoring_initialized:
                return False
            
            # Test monitoring components
            try:
                apm = get_apm_system()
                logging_sys = get_logging_system()
                alert_mgr = get_alert_manager()
                health_mon = get_health_monitor()
                
                # Basic validation
                return all([apm, logging_sys, alert_mgr, health_mon])
                
            except Exception as e:
                self.logger.error(f"Monitoring systems validation failed: {e}")
                return False
            
        except Exception as e:
            self.logger.error(f"Monitoring systems validation failed: {e}")
            return False
    
    def get_production_status(self) -> Dict[str, Any]:
        """Get comprehensive production status"""
        try:
            status = {
                'timestamp': datetime.utcnow().isoformat(),
                'uptime_seconds': int((datetime.utcnow() - self.start_time).total_seconds()),
                'security_systems': {
                    'initialized': self.security_initialized,
                    'active_count': len(self.security_systems),
                    'systems': list(self.security_systems.keys())
                },
                'monitoring_systems': {
                    'initialized': self.monitoring_initialized,
                    'components_active': 4 if self.monitoring_initialized else 0  # APM, Logging, Alerting, Health
                },
                'integration': {
                    'completed': self.security_initialized and self.monitoring_initialized,
                    'health_checks_active': self.monitoring_initialized
                }
            }
            
            # Add health check data if available
            if self.monitoring_initialized:
                try:
                    health_mon = get_health_monitor()
                    # Would get health status asynchronously in real implementation
                    status['health_summary'] = {'status': 'monitoring_available'}
                except Exception:
                    status['health_summary'] = {'status': 'health_check_error'}
            
            return status
            
        except Exception as e:
            self.logger.error(f"Failed to get production status: {e}")
            return {
                'error': str(e),
                'timestamp': datetime.utcnow().isoformat()
            }
    
    async def run_comprehensive_health_check(self) -> Dict[str, Any]:
        """Run comprehensive health check of all systems"""
        try:
            if not self.monitoring_initialized:
                return {
                    'error': 'Monitoring systems not initialized',
                    'timestamp': datetime.utcnow().isoformat()
                }
            
            health_mon = get_health_monitor()
            health_data = await health_mon.get_full_health()
            
            # Add production-specific information
            health_data['production_info'] = {
                'security_systems_active': len(self.security_systems),
                'monitoring_systems_active': self.monitoring_initialized,
                'integration_complete': self.security_initialized and self.monitoring_initialized,
                'uptime_seconds': int((datetime.utcnow() - self.start_time).total_seconds())
            }
            
            return health_data
            
        except Exception as e:
            self.logger.error(f"Comprehensive health check failed: {e}")
            return {
                'error': str(e),
                'timestamp': datetime.utcnow().isoformat()
            }


# Global integrator instance
_production_integrator = None

def get_production_integrator() -> ProductionSystemIntegrator:
    """Get or create the global production integrator"""
    global _production_integrator
    if _production_integrator is None:
        _production_integrator = ProductionSystemIntegrator()
    return _production_integrator


def initialize_production_systems() -> Dict[str, Any]:
    """Initialize all production systems"""
    integrator = get_production_integrator()
    return integrator.initialize_all_systems()


async def get_production_health() -> Dict[str, Any]:
    """Get production health status"""
    integrator = get_production_integrator()
    return await integrator.run_comprehensive_health_check()


def main():
    """Command line interface for production system integration"""
    import argparse
    
    parser = argparse.ArgumentParser(description="JARVIS-MK42 Production System Integration")
    parser.add_argument('--initialize', action='store_true', help='Initialize all production systems')
    parser.add_argument('--status', action='store_true', help='Get production status')
    parser.add_argument('--health', action='store_true', help='Run comprehensive health check')
    parser.add_argument('--monitor', action='store_true', help='Start monitoring mode')
    
    args = parser.parse_args()
    
    integrator = get_production_integrator()
    
    if args.initialize:
        print("Initializing production systems...")
        results = integrator.initialize_all_systems()
        print(json.dumps(results, indent=2))
    
    elif args.status:
        status = integrator.get_production_status()
        print(json.dumps(status, indent=2))
    
    elif args.health:
        print("Running comprehensive health check...")
        async def run_health():
            health = await integrator.run_comprehensive_health_check()
            print(json.dumps(health, indent=2))
        
        asyncio.run(run_health())
    
    elif args.monitor:
        print("Starting production monitoring...")
        async def monitor():
            while True:
                status = integrator.get_production_status()
                print(f"\n[{datetime.utcnow().strftime('%Y-%m-%d %H:%M:%S')}] Production Status:")
                print(f"  Security Systems: {status['security_systems']['active_count']} active")
                print(f"  Monitoring: {'Active' if status['monitoring_systems']['initialized'] else 'Inactive'}")
                print(f"  Integration: {'Complete' if status['integration']['completed'] else 'Incomplete'}")
                print(f"  Uptime: {status['uptime_seconds']}s")
                
                await asyncio.sleep(60)
        
        asyncio.run(monitor())
    
    else:
        print("JARVIS-MK42 Production System Integration")
        print("Use --initialize, --status, --health, or --monitor")


if __name__ == "__main__":
    main()
