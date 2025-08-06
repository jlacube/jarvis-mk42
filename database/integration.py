#!/usr/bin/env python3
"""
JARVIS-MK42 Database & Storage Integration Module
===============================================

This module provides a unified interface for all database and storage management
systems, coordinating their operations and providing centralized monitoring.

Components integrated:
- Database Optimization System
- Storage Management System  
- Backup & Recovery System
- Data Retention & Archival System
- Health monitoring and alerting
- Automated maintenance workflows
"""

import os
import sys
import json
import asyncio
import threading
import schedule
from datetime import datetime, timedelta
from typing import Dict, List, Optional, Any, Callable
from dataclasses import dataclass
from enum import Enum
from pathlib import Path

# Add project root to path
current_dir = os.path.dirname(os.path.abspath(__file__))
project_root = os.path.dirname(current_dir)
if project_root not in sys.path:
    sys.path.insert(0, project_root)

from utils.logging_config import get_logger

# Import our database and storage systems
try:
    from database.optimization import get_database_optimizer, OptimizationLevel
    from storage.management import get_storage_manager
    from database.backup_recovery import get_backup_system, BackupConfiguration, BackupType
    from database.retention_archival import get_retention_system, ComplianceFramework
    HAS_ALL_SYSTEMS = True
except ImportError as e:
    logger = get_logger(__name__)
    logger.error("Failed to import required systems: %s", e)
    HAS_ALL_SYSTEMS = False

logger = get_logger(__name__)


class SystemStatus(Enum):
    """System status levels"""
    HEALTHY = "healthy"
    WARNING = "warning"
    ERROR = "error"
    CRITICAL = "critical"
    MAINTENANCE = "maintenance"


class MaintenanceType(Enum):
    """Types of maintenance operations"""
    DAILY = "daily"
    WEEKLY = "weekly"
    MONTHLY = "monthly"
    ON_DEMAND = "on_demand"


@dataclass
class SystemHealth:
    """Health status for a system component"""
    component: str
    status: SystemStatus
    message: str
    metrics: Dict[str, Any]
    last_check: datetime
    details: Dict[str, Any] = None
    
    def to_dict(self) -> Dict[str, Any]:
        return {
            'component': self.component,
            'status': self.status.value,
            'message': self.message,
            'metrics': self.metrics,
            'last_check': self.last_check.isoformat(),
            'details': self.details or {}
        }


@dataclass
class MaintenanceTask:
    """Maintenance task definition"""
    task_id: str
    name: str
    description: str
    maintenance_type: MaintenanceType
    schedule_pattern: str
    enabled: bool
    last_run: Optional[datetime]
    next_run: Optional[datetime]
    function: Callable[[], Dict[str, Any]]
    
    def to_dict(self) -> Dict[str, Any]:
        return {
            'task_id': self.task_id,
            'name': self.name,
            'description': self.description,
            'maintenance_type': self.maintenance_type.value,
            'schedule_pattern': self.schedule_pattern,
            'enabled': self.enabled,
            'last_run': self.last_run.isoformat() if self.last_run else None,
            'next_run': self.next_run.isoformat() if self.next_run else None
        }


class DatabaseStorageIntegration:
    """
    Central integration system for database and storage management.
    
    Coordinates all database and storage systems, provides unified monitoring,
    and manages automated maintenance workflows.
    """
    
    def __init__(self, base_path: str = ".", database_path: str = "jarvis.db"):
        self.base_path = Path(base_path).resolve()
        self.database_path = database_path
        self.health_status: Dict[str, SystemHealth] = {}
        self.maintenance_tasks: Dict[str, MaintenanceTask] = {}
        self.lock = threading.RLock()
        
        # Initialize system components if available
        if HAS_ALL_SYSTEMS:
            self.db_optimizer = get_database_optimizer(database_path)
            self.storage_manager = get_storage_manager(str(base_path))
            self.backup_system = get_backup_system(str(base_path))
            self.retention_system = get_retention_system(str(base_path))
        else:
            logger.warning("Not all systems available - running in limited mode")
            self.db_optimizer = None
            self.storage_manager = None
            self.backup_system = None
            self.retention_system = None
        
        # Setup maintenance tasks
        self._setup_maintenance_tasks()
        
        # Start monitoring
        self._start_health_monitoring()
        
        logger.info("Database & Storage Integration System initialized for path: %s", self.base_path)
    
    def _setup_maintenance_tasks(self):
        """Setup automated maintenance tasks"""
        if not HAS_ALL_SYSTEMS:
            return
        
        tasks = [
            MaintenanceTask(
                task_id="daily_database_optimization",
                name="Daily Database Optimization",
                description="Perform daily database optimization and statistics update",
                maintenance_type=MaintenanceType.DAILY,
                schedule_pattern="02:00",
                enabled=True,
                last_run=None,
                next_run=None,
                function=self._daily_database_maintenance
            ),
            MaintenanceTask(
                task_id="daily_storage_cleanup",
                name="Daily Storage Cleanup",
                description="Clean up temporary files and optimize storage",
                maintenance_type=MaintenanceType.DAILY,
                schedule_pattern="03:00",
                enabled=True,
                last_run=None,
                next_run=None,
                function=self._daily_storage_maintenance
            ),
            MaintenanceTask(
                task_id="daily_backup",
                name="Daily Database Backup",
                description="Create daily database backup",
                maintenance_type=MaintenanceType.DAILY,
                schedule_pattern="01:00",
                enabled=True,
                last_run=None,
                next_run=None,
                function=self._daily_backup_maintenance
            ),
            MaintenanceTask(
                task_id="weekly_full_maintenance",
                name="Weekly Full System Maintenance",
                description="Comprehensive weekly maintenance including full backup and cleanup",
                maintenance_type=MaintenanceType.WEEKLY,
                schedule_pattern="sunday",
                enabled=True,
                last_run=None,
                next_run=None,
                function=self._weekly_maintenance
            ),
            MaintenanceTask(
                task_id="monthly_retention_processing",
                name="Monthly Retention Processing",
                description="Process expired records and enforce retention policies",
                maintenance_type=MaintenanceType.MONTHLY,
                schedule_pattern="1st",
                enabled=True,
                last_run=None,
                next_run=None,
                function=self._monthly_retention_maintenance
            )
        ]
        
        for task in tasks:
            self.maintenance_tasks[task.task_id] = task
        
        logger.info("Setup %d maintenance tasks", len(tasks))
    
    def _start_health_monitoring(self):
        """Start continuous health monitoring"""
        def monitor_health():
            while True:
                try:
                    self.check_system_health()
                except Exception as e:
                    logger.error("Error in health monitoring: %s", e)
                
                # Check every 5 minutes
                threading.Event().wait(300)
        
        monitor_thread = threading.Thread(target=monitor_health, daemon=True)
        monitor_thread.start()
        logger.info("Health monitoring started")
    
    def check_system_health(self) -> Dict[str, SystemHealth]:
        """
        Check health status of all integrated systems.
        
        Returns:
            Dictionary of system health status
        """
        health_checks = []
        
        if self.db_optimizer:
            health_checks.append(self._check_database_health())
        if self.storage_manager:
            health_checks.append(self._check_storage_health())
        if self.backup_system:
            health_checks.append(self._check_backup_health())
        if self.retention_system:
            health_checks.append(self._check_retention_health())
        
        with self.lock:
            for health in health_checks:
                self.health_status[health.component] = health
        
        return self.health_status
    
    def _check_database_health(self) -> SystemHealth:
        """Check database system health"""
        try:
            stats = self.db_optimizer.get_database_statistics()
            report = self.db_optimizer.get_performance_report(hours=1)
            
            # Determine status based on metrics
            status = SystemStatus.HEALTHY
            messages = []
            
            # Check database size
            size_gb = stats.total_size_bytes / (1024 * 1024 * 1024)
            if size_gb > 10:  # 10GB threshold
                status = SystemStatus.WARNING
                messages.append(f"Database size is large: {size_gb:.1f}GB")
            
            # Check fragmentation
            if stats.fragmentation_percent > 20:
                status = SystemStatus.WARNING
                messages.append(f"High fragmentation: {stats.fragmentation_percent:.1f}%")
            
            # Check slow queries if report has performance metrics
            perf_metrics = report.get('performance_metrics', {})
            if perf_metrics.get('slow_query_count', 0) > 10:
                status = SystemStatus.WARNING
                messages.append(f"Many slow queries: {perf_metrics['slow_query_count']}")
            
            # Check cache hit rate
            if stats.query_cache_hit_rate < 0.8 and stats.query_cache_hit_rate > 0:
                status = SystemStatus.WARNING
                messages.append(f"Low cache hit rate: {stats.query_cache_hit_rate:.1%}")
            
            message = "; ".join(messages) if messages else "Database system healthy"
            
            return SystemHealth(
                component="database",
                status=status,
                message=message,
                metrics={
                    'size_gb': round(size_gb, 2),
                    'fragmentation_percent': stats.fragmentation_percent,
                    'cache_hit_rate': stats.query_cache_hit_rate,
                    'slow_queries_1h': perf_metrics.get('slow_query_count', 0),
                    'avg_query_time_ms': perf_metrics.get('avg_execution_time', 0) * 1000
                },
                last_check=datetime.utcnow(),
                details=stats.to_dict()
            )
            
        except Exception as e:
            return SystemHealth(
                component="database",
                status=SystemStatus.ERROR,
                message=f"Database health check failed: {str(e)}",
                metrics={},
                last_check=datetime.utcnow()
            )
    
    def _check_storage_health(self) -> SystemHealth:
        """Check storage system health"""
        try:
            health = self.storage_manager.get_storage_health()
            
            # Convert health score to status
            if health['health_score'] >= 90:
                status = SystemStatus.HEALTHY
            elif health['health_score'] >= 70:
                status = SystemStatus.WARNING
            else:
                status = SystemStatus.ERROR
            
            message = f"Storage health score: {health['health_score']}/100"
            if health.get('warnings'):
                message += f"; Warnings: {', '.join(health['warnings'])}"
            
            return SystemHealth(
                component="storage",
                status=status,
                message=message,
                metrics={
                    'health_score': health['health_score'],
                    'disk_usage_percent': health['disk_usage']['usage_percent'],
                    'managed_files': health['managed_storage']['total_files'],
                    'managed_size_gb': round(health['managed_storage']['total_size'] / (1024**3), 2)
                },
                last_check=datetime.utcnow(),
                details=health
            )
            
        except Exception as e:
            return SystemHealth(
                component="storage",
                status=SystemStatus.ERROR,
                message=f"Storage health check failed: {str(e)}",
                metrics={},
                last_check=datetime.utcnow()
            )
    
    def _check_backup_health(self) -> SystemHealth:
        """Check backup system health"""
        try:
            status_info = self.backup_system.get_backup_status()
            
            # Determine status
            status = SystemStatus.HEALTHY
            messages = []
            
            # Check success rate
            success_rate = status_info['success_rate']
            if success_rate < 95:
                status = SystemStatus.ERROR
                messages.append(f"Low backup success rate: {success_rate:.1f}%")
            elif success_rate < 98:
                status = SystemStatus.WARNING
                messages.append(f"Backup success rate: {success_rate:.1f}%")
            
            # Check latest backup age
            latest_backup = status_info.get('latest_backup')
            if latest_backup:
                latest_time = datetime.fromisoformat(latest_backup['created_at'])
                hours_since = (datetime.utcnow() - latest_time).total_seconds() / 3600
                
                if hours_since > 48:  # 2 days
                    status = SystemStatus.ERROR
                    messages.append(f"Latest backup is {hours_since:.1f} hours old")
                elif hours_since > 30:  # 30 hours
                    status = SystemStatus.WARNING
                    messages.append(f"Latest backup is {hours_since:.1f} hours old")
            else:
                status = SystemStatus.ERROR
                messages.append("No backups found")
            
            message = "; ".join(messages) if messages else "Backup system healthy"
            
            return SystemHealth(
                component="backup",
                status=status,
                message=message,
                metrics={
                    'total_backups': status_info['total_backups'],
                    'success_rate': success_rate,
                    'failed_backups': status_info['failed_backups'],
                    'total_backup_size_gb': round(status_info['total_backup_size'] / (1024**3), 2)
                },
                last_check=datetime.utcnow(),
                details=status_info
            )
            
        except Exception as e:
            return SystemHealth(
                component="backup",
                status=SystemStatus.ERROR,
                message=f"Backup health check failed: {str(e)}",
                metrics={},
                last_check=datetime.utcnow()
            )
    
    def _check_retention_health(self) -> SystemHealth:
        """Check retention system health"""
        try:
            status_info = self.retention_system.get_retention_status()
            
            # Determine status
            status = SystemStatus.HEALTHY
            messages = []
            
            # Check expired records
            expired_count = status_info['records']['expired']
            total_count = status_info['records']['total']
            
            if total_count > 0:
                expired_percent = (expired_count / total_count) * 100
                
                if expired_percent > 20:
                    status = SystemStatus.WARNING
                    messages.append(f"Many expired records: {expired_count} ({expired_percent:.1f}%)")
                elif expired_percent > 10:
                    status = SystemStatus.WARNING
                    messages.append(f"Some expired records: {expired_count} ({expired_percent:.1f}%)")
            
            # Check legal hold records
            legal_hold_count = status_info['records']['legal_hold']
            if legal_hold_count > 0:
                messages.append(f"Records under legal hold: {legal_hold_count}")
            
            message = "; ".join(messages) if messages else "Retention system healthy"
            
            return SystemHealth(
                component="retention",
                status=status,
                message=message,
                metrics={
                    'total_records': total_count,
                    'expired_records': expired_count,
                    'legal_hold_records': legal_hold_count,
                    'active_policies': status_info['active_policies'],
                    'managed_data_gb': round(status_info['data_volume']['total_bytes'] / (1024**3), 2)
                },
                last_check=datetime.utcnow(),
                details=status_info
            )
            
        except Exception as e:
            return SystemHealth(
                component="retention",
                status=SystemStatus.ERROR,
                message=f"Retention health check failed: {str(e)}",
                metrics={},
                last_check=datetime.utcnow()
            )
    
    def get_overall_health(self) -> Dict[str, Any]:
        """Get overall system health summary"""
        health_status = self.check_system_health()
        
        # Determine overall status
        statuses = [health.status for health in health_status.values()]
        
        if SystemStatus.CRITICAL in statuses:
            overall_status = SystemStatus.CRITICAL
        elif SystemStatus.ERROR in statuses:
            overall_status = SystemStatus.ERROR
        elif SystemStatus.WARNING in statuses:
            overall_status = SystemStatus.WARNING
        else:
            overall_status = SystemStatus.HEALTHY
        
        # Count by status
        status_counts = {}
        for status in SystemStatus:
            status_counts[status.value] = sum(1 for h in health_status.values() if h.status == status)
        
        return {
            'overall_status': overall_status.value,
            'last_check': datetime.utcnow().isoformat(),
            'systems_count': len(health_status),
            'status_distribution': status_counts,
            'systems': {name: health.to_dict() for name, health in health_status.items()},
            'recommendations': self._generate_health_recommendations(health_status)
        }
    
    def _generate_health_recommendations(self, health_status: Dict[str, SystemHealth]) -> List[str]:
        """Generate health improvement recommendations"""
        recommendations = []
        
        for health in health_status.values():
            if health.status in [SystemStatus.WARNING, SystemStatus.ERROR]:
                if health.component == "database":
                    if "fragmentation" in health.message.lower():
                        recommendations.append("Run VACUUM operation to defragment database")
                    if "slow queries" in health.message.lower():
                        recommendations.append("Review and optimize slow queries, consider adding indexes")
                    if "cache hit rate" in health.message.lower():
                        recommendations.append("Increase database cache size for better performance")
                
                elif health.component == "storage":
                    if "disk usage" in health.message.lower():
                        recommendations.append("Free up disk space or add more storage capacity")
                    if "fragmentation" in health.message.lower():
                        recommendations.append("Consolidate small files and compress large files")
                
                elif health.component == "backup":
                    if "success rate" in health.message.lower():
                        recommendations.append("Investigate backup failures and fix underlying issues")
                    if "old" in health.message.lower():
                        recommendations.append("Ensure backup scheduler is running and configured properly")
                
                elif health.component == "retention":
                    if "expired" in health.message.lower():
                        recommendations.append("Process expired records according to retention policies")
        
        return recommendations
    
    def perform_maintenance(self, task_id: str = None, dry_run: bool = False) -> Dict[str, Any]:
        """
        Perform maintenance tasks.
        
        Args:
            task_id: Specific task ID to run (None for all eligible tasks)
            dry_run: If True, only simulate maintenance
            
        Returns:
            Dictionary with maintenance results
        """
        if not HAS_ALL_SYSTEMS:
            return {'error': 'Not all systems available for maintenance'}
        
        results = {
            'maintenance_started': datetime.utcnow().isoformat(),
            'dry_run': dry_run,
            'tasks_run': [],
            'total_duration': 0,
            'errors': []
        }
        
        tasks_to_run = []
        if task_id:
            task = self.maintenance_tasks.get(task_id)
            if task and task.enabled:
                tasks_to_run = [task]
        else:
            # Run all eligible tasks (for manual execution)
            tasks_to_run = [task for task in self.maintenance_tasks.values() if task.enabled]
        
        start_time = datetime.utcnow()
        
        for task in tasks_to_run:
            try:
                logger.info("Starting maintenance task: %s", task.name)
                task_start = datetime.utcnow()
                
                if not dry_run:
                    task_result = task.function()
                else:
                    task_result = {'dry_run': True, 'message': 'Simulated execution'}
                
                task_duration = (datetime.utcnow() - task_start).total_seconds()
                
                task_info = {
                    'task_id': task.task_id,
                    'name': task.name,
                    'duration_seconds': task_duration,
                    'result': task_result,
                    'status': 'completed'
                }
                
                results['tasks_run'].append(task_info)
                
                if not dry_run:
                    task.last_run = datetime.utcnow()
                
                logger.info("Completed maintenance task: %s (%.1fs)", task.name, task_duration)
                
            except Exception as e:
                error_msg = f"Maintenance task {task.name} failed: {str(e)}"
                results['errors'].append(error_msg)
                logger.error(error_msg)
                
                results['tasks_run'].append({
                    'task_id': task.task_id,
                    'name': task.name,
                    'status': 'failed',
                    'error': str(e)
                })
        
        results['total_duration'] = (datetime.utcnow() - start_time).total_seconds()
        results['maintenance_completed'] = datetime.utcnow().isoformat()
        
        return results
    
    def _daily_database_maintenance(self) -> Dict[str, Any]:
        """Daily database maintenance tasks"""
        results = {
            'operations': [],
            'duration': 0,
            'space_saved': 0
        }
        
        start_time = datetime.utcnow()
        
        try:
            # Optimize database
            optimization_result = self.db_optimizer.optimize_database(OptimizationLevel.STANDARD)
            results['operations'].append({
                'name': 'database_optimization',
                'result': optimization_result
            })
            
            # Update query cache
            # This is handled automatically by the optimizer
            
            logger.info("Daily database maintenance completed")
            
        except Exception as e:
            logger.error("Daily database maintenance failed: %s", e)
            raise
        
        results['duration'] = (datetime.utcnow() - start_time).total_seconds()
        return results
    
    def _daily_storage_maintenance(self) -> Dict[str, Any]:
        """Daily storage maintenance tasks"""
        results = {
            'operations': [],
            'duration': 0,
            'space_saved': 0
        }
        
        start_time = datetime.utcnow()
        
        try:
            # Clean up temporary files and compress large files
            cleanup_result = self.storage_manager.perform_cleanup(dry_run=False)
            
            total_space_saved = sum(r.space_saved for r in cleanup_result if r.success)
            
            results['operations'].append({
                'name': 'storage_cleanup',
                'files_processed': len(cleanup_result),
                'space_saved': total_space_saved,
                'successful_operations': sum(1 for r in cleanup_result if r.success)
            })
            
            results['space_saved'] = total_space_saved
            
            logger.info("Daily storage maintenance completed: %.2f MB saved", 
                       total_space_saved / (1024 * 1024))
            
        except Exception as e:
            logger.error("Daily storage maintenance failed: %s", e)
            raise
        
        results['duration'] = (datetime.utcnow() - start_time).total_seconds()
        return results
    
    def _daily_backup_maintenance(self) -> Dict[str, Any]:
        """Daily backup maintenance tasks"""
        results = {
            'operations': [],
            'duration': 0
        }
        
        start_time = datetime.utcnow()
        
        try:
            # Create daily database backup
            backup_id = self.backup_system.create_backup(BackupType.DATABASE_ONLY)
            
            results['operations'].append({
                'name': 'daily_backup',
                'backup_id': backup_id
            })
            
            # Clean up old backups
            cleanup_result = self.backup_system.cleanup_old_backups()
            results['operations'].append({
                'name': 'backup_cleanup',
                'deleted_backups': cleanup_result['deleted_count'],
                'space_freed': cleanup_result['space_freed']
            })
            
            logger.info("Daily backup maintenance completed: backup %s created", backup_id)
            
        except Exception as e:
            logger.error("Daily backup maintenance failed: %s", e)
            raise
        
        results['duration'] = (datetime.utcnow() - start_time).total_seconds()
        return results
    
    def _weekly_maintenance(self) -> Dict[str, Any]:
        """Weekly comprehensive maintenance"""
        results = {
            'operations': [],
            'duration': 0,
            'space_saved': 0
        }
        
        start_time = datetime.utcnow()
        
        try:
            # Aggressive database optimization
            optimization_result = self.db_optimizer.optimize_database(OptimizationLevel.AGGRESSIVE)
            results['operations'].append({
                'name': 'aggressive_database_optimization',
                'result': optimization_result
            })
            
            # Full system backup
            backup_id = self.backup_system.create_backup(BackupType.FULL)
            results['operations'].append({
                'name': 'full_backup',
                'backup_id': backup_id
            })
            
            # Comprehensive storage cleanup
            storage_cleanup = self.storage_manager.perform_cleanup(dry_run=False)
            total_space_saved = sum(r.space_saved for r in storage_cleanup if r.success)
            
            results['operations'].append({
                'name': 'comprehensive_storage_cleanup',
                'files_processed': len(storage_cleanup),
                'space_saved': total_space_saved
            })
            
            results['space_saved'] = total_space_saved
            
            logger.info("Weekly maintenance completed: %.2f MB saved", 
                       total_space_saved / (1024 * 1024))
            
        except Exception as e:
            logger.error("Weekly maintenance failed: %s", e)
            raise
        
        results['duration'] = (datetime.utcnow() - start_time).total_seconds()
        return results
    
    def _monthly_retention_maintenance(self) -> Dict[str, Any]:
        """Monthly retention policy enforcement"""
        results = {
            'operations': [],
            'duration': 0,
            'records_processed': 0
        }
        
        start_time = datetime.utcnow()
        
        try:
            # Process expired records
            expired_result = self.retention_system.process_expired_records(dry_run=False)
            
            results['operations'].append({
                'name': 'process_expired_records',
                'expired_count': expired_result['total_expired'],
                'actions_taken': expired_result['actions_taken'],
                'space_freed': expired_result['space_freed']
            })
            
            results['records_processed'] = expired_result['total_expired']
            
            # Scan for new data records
            scan_result = self.retention_system.scan_directory()
            results['operations'].append({
                'name': 'scan_new_records',
                'files_scanned': scan_result['scanned_files'],
                'records_registered': scan_result['registered_records']
            })
            
            logger.info("Monthly retention maintenance completed: %d records processed", 
                       expired_result['total_expired'])
            
        except Exception as e:
            logger.error("Monthly retention maintenance failed: %s", e)
            raise
        
        results['duration'] = (datetime.utcnow() - start_time).total_seconds()
        return results
    
    def start_scheduler(self):
        """Start the maintenance scheduler"""
        if not HAS_ALL_SYSTEMS:
            logger.warning("Cannot start scheduler - not all systems available")
            return
        
        # Schedule maintenance tasks
        for task in self.maintenance_tasks.values():
            if not task.enabled:
                continue
            
            if task.maintenance_type == MaintenanceType.DAILY:
                schedule.every().day.at(task.schedule_pattern).do(
                    self._run_scheduled_task, task.task_id
                )
            elif task.maintenance_type == MaintenanceType.WEEKLY:
                getattr(schedule.every(), task.schedule_pattern.lower()).do(
                    self._run_scheduled_task, task.task_id
                )
            elif task.maintenance_type == MaintenanceType.MONTHLY:
                # For monthly tasks, we'll check on the 1st of each month
                schedule.every().day.at("04:00").do(
                    self._check_monthly_task, task.task_id
                )
        
        # Start scheduler thread
        def run_scheduler():
            while True:
                schedule.run_pending()
                threading.Event().wait(60)  # Check every minute
        
        scheduler_thread = threading.Thread(target=run_scheduler, daemon=True)
        scheduler_thread.start()
        
        logger.info("Maintenance scheduler started with %d tasks", len(self.maintenance_tasks))
    
    def _run_scheduled_task(self, task_id: str):
        """Run a scheduled maintenance task"""
        try:
            result = self.perform_maintenance(task_id, dry_run=False)
            logger.info("Scheduled task %s completed: %d operations", 
                       task_id, len(result['tasks_run']))
        except Exception as e:
            logger.error("Scheduled task %s failed: %s", task_id, e)
    
    def _check_monthly_task(self, task_id: str):
        """Check if monthly task should run"""
        today = datetime.now()
        if today.day == 1:  # First day of the month
            self._run_scheduled_task(task_id)
    
    def generate_comprehensive_report(self) -> Dict[str, Any]:
        """Generate comprehensive system report"""
        report = {
            'generated_at': datetime.utcnow().isoformat(),
            'system_health': self.get_overall_health(),
            'maintenance_status': {},
            'component_reports': {}
        }
        
        # Maintenance status
        report['maintenance_status'] = {
            'total_tasks': len(self.maintenance_tasks),
            'enabled_tasks': sum(1 for t in self.maintenance_tasks.values() if t.enabled),
            'tasks': [task.to_dict() for task in self.maintenance_tasks.values()]
        }
        
        # Component-specific reports
        if HAS_ALL_SYSTEMS:
            try:
                if self.db_optimizer:
                    report['component_reports']['database'] = {
                        'performance_report': self.db_optimizer.get_performance_report(hours=24),
                        'index_recommendations': [r.to_dict() for r in self.db_optimizer.get_index_recommendations()[:5]]
                    }
            except Exception as e:
                logger.error("Error generating database report: %s", e)
            
            try:
                if self.storage_manager:
                    storage_report = self.storage_manager.generate_storage_report()
                    report['component_reports']['storage'] = storage_report.to_dict()
            except Exception as e:
                logger.error("Error generating storage report: %s", e)
            
            try:
                if self.backup_system:
                    report['component_reports']['backup'] = {
                        'status': self.backup_system.get_backup_status(),
                        'recent_backups': self.backup_system.list_backups()[:10]
                    }
            except Exception as e:
                logger.error("Error generating backup report: %s", e)
            
            try:
                if self.retention_system:
                    report['component_reports']['retention'] = {
                        'status': self.retention_system.get_retention_status(),
                        'compliance_report': self.retention_system.get_compliance_report(days=30)
                    }
            except Exception as e:
                logger.error("Error generating retention report: %s", e)
        
        return report
    
    def export_configuration(self) -> Dict[str, Any]:
        """Export current system configuration"""
        config = {
            'exported_at': datetime.utcnow().isoformat(),
            'base_path': str(self.base_path),
            'database_path': self.database_path,
            'maintenance_tasks': [task.to_dict() for task in self.maintenance_tasks.values()],
            'system_availability': {
                'database_optimizer': self.db_optimizer is not None,
                'storage_manager': self.storage_manager is not None,
                'backup_system': self.backup_system is not None,
                'retention_system': self.retention_system is not None
            }
        }
        
        return config


# Global integration system instance
_integration_system = None

def get_integration_system(base_path: str = ".", database_path: str = "jarvis.db") -> DatabaseStorageIntegration:
    """Get or create the global integration system instance"""
    global _integration_system
    if _integration_system is None:
        _integration_system = DatabaseStorageIntegration(base_path, database_path)
    return _integration_system


def main():
    """Command line interface for the integration system"""
    import argparse
    
    parser = argparse.ArgumentParser(description="JARVIS-MK42 Database & Storage Integration")
    parser.add_argument('--path', default='.', help='Base path for operations')
    parser.add_argument('--database', default='jarvis.db', help='Database file path')
    parser.add_argument('--health', action='store_true', help='Check system health')
    parser.add_argument('--maintenance', help='Run maintenance task by ID')
    parser.add_argument('--dry-run', action='store_true', help='Dry run mode')
    parser.add_argument('--report', action='store_true', help='Generate comprehensive report')
    parser.add_argument('--start-scheduler', action='store_true', help='Start maintenance scheduler')
    parser.add_argument('--config', action='store_true', help='Export configuration')
    
    args = parser.parse_args()
    
    integration = get_integration_system(args.path, args.database)
    
    try:
        if args.health:
            health = integration.get_overall_health()
            print(json.dumps(health, indent=2))
        
        elif args.maintenance:
            print(f"Running maintenance task: {args.maintenance}")
            result = integration.perform_maintenance(args.maintenance, args.dry_run)
            print(json.dumps(result, indent=2, default=str))
        
        elif args.report:
            print("Generating comprehensive report...")
            report = integration.generate_comprehensive_report()
            print(json.dumps(report, indent=2, default=str))
        
        elif args.config:
            config = integration.export_configuration()
            print(json.dumps(config, indent=2))
        
        elif args.start_scheduler:
            print("Starting maintenance scheduler...")
            integration.start_scheduler()
            print("Scheduler started - press Ctrl+C to stop")
            
            try:
                while True:
                    threading.Event().wait(1)
            except KeyboardInterrupt:
                print("\nStopping scheduler...")
        
        else:
            print("JARVIS-MK42 Database & Storage Integration System")
            print("Use --help for available options")
    
    except KeyboardInterrupt:
        print("\nOperation cancelled")
    except Exception as e:
        print(f"Error: {e}")


if __name__ == "__main__":
    main()
