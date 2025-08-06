#!/usr/bin/env python3
"""
JARVIS-MK42 Centralized Logging Infrastructure
==========================================

This module provides centralized logging capabilities including:
- Structured JSON logging
- Log aggregation and forwarding
- Real-time log monitoring and analysis
- Log retention and archival
- Security event logging
- Performance event logging
- Integration with monitoring and alerting systems
"""

import os
import sys
import json
import logging
import logging.handlers
import threading
import time
from datetime import datetime, timedelta
from typing import Dict, List, Optional, Any, Union
from dataclasses import dataclass, asdict
from enum import Enum
from pathlib import Path
from collections import deque, defaultdict
import gzip
import shutil

# Add project root to path
current_dir = os.path.dirname(os.path.abspath(__file__))
project_root = os.path.dirname(current_dir)
if project_root not in sys.path:
    sys.path.insert(0, project_root)

from utils.logging_config import get_logger

base_logger = get_logger(__name__)


class LogLevel(Enum):
    """Enhanced log levels"""
    DEBUG = "DEBUG"
    INFO = "INFO" 
    WARNING = "WARNING"
    ERROR = "ERROR"
    CRITICAL = "CRITICAL"
    SECURITY = "SECURITY"     # Security events
    PERFORMANCE = "PERFORMANCE"  # Performance events
    AUDIT = "AUDIT"           # Audit trail events


class LogCategory(Enum):
    """Log event categories"""
    SYSTEM = "system"
    APPLICATION = "application"
    SECURITY = "security"
    PERFORMANCE = "performance"
    AGENT = "agent"
    USER = "user"
    API = "api"
    DATABASE = "database"
    NETWORK = "network"


@dataclass
class StructuredLogEntry:
    """Structured log entry with metadata"""
    timestamp: datetime
    level: LogLevel
    category: LogCategory
    message: str
    logger_name: str
    module: str
    function: str
    line_number: int
    thread_id: str
    process_id: int
    user_id: Optional[str] = None
    session_id: Optional[str] = None
    request_id: Optional[str] = None
    client_ip: Optional[str] = None
    metadata: Dict[str, Any] = None
    tags: List[str] = None
    stack_trace: Optional[str] = None
    
    def __post_init__(self):
        if self.metadata is None:
            self.metadata = {}
        if self.tags is None:
            self.tags = []
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary for JSON serialization"""
        return {
            'timestamp': self.timestamp.isoformat(),
            'level': self.level.value,
            'category': self.category.value,
            'message': self.message,
            'logger_name': self.logger_name,
            'module': self.module,
            'function': self.function,
            'line_number': self.line_number,
            'thread_id': self.thread_id,
            'process_id': self.process_id,
            'user_id': self.user_id,
            'session_id': self.session_id,
            'request_id': self.request_id,
            'client_ip': self.client_ip,
            'metadata': self.metadata,
            'tags': self.tags,
            'stack_trace': self.stack_trace
        }


class LogBuffer:
    """Thread-safe circular buffer for log entries"""
    
    def __init__(self, max_size: int = 10000):
        self.buffer = deque(maxlen=max_size)
        self.lock = threading.Lock()
        self.total_count = 0
    
    def add(self, entry: StructuredLogEntry):
        """Add log entry to buffer"""
        with self.lock:
            self.buffer.append(entry)
            self.total_count += 1
    
    def get_recent(self, count: int = 100) -> List[StructuredLogEntry]:
        """Get recent log entries"""
        with self.lock:
            return list(self.buffer)[-count:]
    
    def get_filtered(self, level: LogLevel = None, category: LogCategory = None, 
                    since: datetime = None, user_id: str = None) -> List[StructuredLogEntry]:
        """Get filtered log entries"""
        with self.lock:
            entries = list(self.buffer)
        
        if level:
            entries = [e for e in entries if e.level == level]
        if category:
            entries = [e for e in entries if e.category == category]
        if since:
            entries = [e for e in entries if e.timestamp >= since]
        if user_id:
            entries = [e for e in entries if e.user_id == user_id]
        
        return entries
    
    def get_statistics(self) -> Dict[str, Any]:
        """Get buffer statistics"""
        with self.lock:
            entries = list(self.buffer)
        
        if not entries:
            return {'total_entries': 0}
        
        # Count by level
        level_counts = defaultdict(int)
        category_counts = defaultdict(int)
        
        for entry in entries:
            level_counts[entry.level.value] += 1
            category_counts[entry.category.value] += 1
        
        return {
            'total_entries': len(entries),
            'total_logged': self.total_count,
            'oldest_entry': entries[0].timestamp.isoformat(),
            'newest_entry': entries[-1].timestamp.isoformat(),
            'level_distribution': dict(level_counts),
            'category_distribution': dict(category_counts)
        }


class JSONFormatter(logging.Formatter):
    """Custom JSON formatter for structured logging"""
    
    def format(self, record: logging.LogRecord) -> str:
        """Format log record as JSON"""
        try:
            # Extract structured information
            entry = StructuredLogEntry(
                timestamp=datetime.fromtimestamp(record.created),
                level=LogLevel(record.levelname),
                category=getattr(record, 'category', LogCategory.APPLICATION),
                message=record.getMessage(),
                logger_name=record.name,
                module=record.module or 'unknown',
                function=record.funcName or 'unknown',
                line_number=record.lineno,
                thread_id=str(record.thread),
                process_id=record.process,
                user_id=getattr(record, 'user_id', None),
                session_id=getattr(record, 'session_id', None),
                request_id=getattr(record, 'request_id', None),
                client_ip=getattr(record, 'client_ip', None),
                metadata=getattr(record, 'metadata', {}),
                tags=getattr(record, 'tags', []),
                stack_trace=self.formatException(record.exc_info) if record.exc_info else None
            )
            
            return json.dumps(entry.to_dict(), default=str)
            
        except Exception as e:
            # Fallback to standard formatting if JSON fails
            return f"LOG_FORMAT_ERROR: {str(e)} | Original: {record.getMessage()}"


class LogAggregator:
    """Log aggregation and forwarding system"""
    
    def __init__(self, buffer_size: int = 10000):
        self.buffer = LogBuffer(buffer_size)
        self.handlers: List[logging.Handler] = []
        self.forwarding_enabled = False
        self.forwarding_thread = None
        self.log_files: Dict[str, str] = {}
        self._setup_file_handlers()
    
    def _setup_file_handlers(self):
        """Setup file-based log handlers"""
        log_dir = Path(project_root) / "logs"
        log_dir.mkdir(exist_ok=True)
        
        # Main application log
        app_log = log_dir / "jarvis.log"
        app_handler = logging.handlers.RotatingFileHandler(
            app_log, maxBytes=10*1024*1024, backupCount=5  # 10MB files, 5 backups
        )
        app_handler.setFormatter(JSONFormatter())
        self.handlers.append(app_handler)
        self.log_files['application'] = str(app_log)
        
        # Security events log
        security_log = log_dir / "security.log"
        security_handler = logging.handlers.RotatingFileHandler(
            security_log, maxBytes=5*1024*1024, backupCount=10  # 5MB files, 10 backups
        )
        security_handler.setFormatter(JSONFormatter())
        security_handler.addFilter(self._security_filter)
        self.handlers.append(security_handler)
        self.log_files['security'] = str(security_log)
        
        # Performance log
        performance_log = log_dir / "performance.log"
        performance_handler = logging.handlers.RotatingFileHandler(
            performance_log, maxBytes=5*1024*1024, backupCount=5
        )
        performance_handler.setFormatter(JSONFormatter())
        performance_handler.addFilter(self._performance_filter)
        self.handlers.append(performance_handler)
        self.log_files['performance'] = str(performance_log)
        
        # Error log (WARNING and above)
        error_log = log_dir / "errors.log"
        error_handler = logging.handlers.RotatingFileHandler(
            error_log, maxBytes=5*1024*1024, backupCount=10
        )
        error_handler.setFormatter(JSONFormatter())
        error_handler.setLevel(logging.WARNING)
        self.handlers.append(error_handler)
        self.log_files['errors'] = str(error_log)
        
        base_logger.info(f"Log handlers initialized with files: {list(self.log_files.keys())}")
    
    def _security_filter(self, record):
        """Filter for security-related log entries"""
        return (hasattr(record, 'category') and record.category == LogCategory.SECURITY) or \
               record.levelname == 'SECURITY'
    
    def _performance_filter(self, record):
        """Filter for performance-related log entries"""
        return (hasattr(record, 'category') and record.category == LogCategory.PERFORMANCE) or \
               record.levelname == 'PERFORMANCE'
    
    def add_entry(self, entry: StructuredLogEntry):
        """Add log entry to aggregator"""
        self.buffer.add(entry)
        
        # Forward to configured handlers
        log_record = self._create_log_record(entry)
        for handler in self.handlers:
            try:
                handler.handle(log_record)
            except Exception as e:
                base_logger.error(f"Error in log handler: {e}")
    
    def _create_log_record(self, entry: StructuredLogEntry) -> logging.LogRecord:
        """Create LogRecord from StructuredLogEntry"""
        record = logging.LogRecord(
            name=entry.logger_name,
            level=getattr(logging, entry.level.value),
            pathname=entry.module,
            lineno=entry.line_number,
            msg=entry.message,
            args=(),
            exc_info=None,
            func=entry.function,
            sinfo=entry.stack_trace
        )
        
        # Add custom attributes
        record.category = entry.category
        record.user_id = entry.user_id
        record.session_id = entry.session_id
        record.request_id = entry.request_id
        record.client_ip = entry.client_ip
        record.metadata = entry.metadata
        record.tags = entry.tags
        record.thread = int(entry.thread_id) if entry.thread_id.isdigit() else 0
        record.process = entry.process_id
        record.created = entry.timestamp.timestamp()
        
        return record
    
    def get_recent_logs(self, count: int = 100, **filters) -> List[Dict[str, Any]]:
        """Get recent log entries as dictionaries"""
        entries = self.buffer.get_filtered(**filters)
        return [entry.to_dict() for entry in entries[-count:]]
    
    def get_log_statistics(self) -> Dict[str, Any]:
        """Get comprehensive logging statistics"""
        buffer_stats = self.buffer.get_statistics()
        
        # File sizes
        file_sizes = {}
        for log_type, path in self.log_files.items():
            try:
                file_sizes[log_type] = os.path.getsize(path) if os.path.exists(path) else 0
            except:
                file_sizes[log_type] = 0
        
        return {
            'buffer_statistics': buffer_stats,
            'file_sizes_bytes': file_sizes,
            'handlers_count': len(self.handlers),
            'log_files': self.log_files
        }
    
    def archive_old_logs(self, days_to_keep: int = 30):
        """Archive and compress old log files"""
        log_dir = Path(project_root) / "logs"
        archive_dir = log_dir / "archive"
        archive_dir.mkdir(exist_ok=True)
        
        cutoff_date = datetime.now() - timedelta(days=days_to_keep)
        archived_count = 0
        
        for log_file in log_dir.glob("*.log.*"):
            try:
                # Check file modification time
                file_time = datetime.fromtimestamp(log_file.stat().st_mtime)
                if file_time < cutoff_date:
                    # Compress and move to archive
                    archive_name = archive_dir / f"{log_file.name}.gz"
                    with open(log_file, 'rb') as f_in:
                        with gzip.open(archive_name, 'wb') as f_out:
                            shutil.copyfileobj(f_in, f_out)
                    
                    log_file.unlink()  # Remove original
                    archived_count += 1
                    
            except Exception as e:
                base_logger.error(f"Error archiving {log_file}: {e}")
        
        base_logger.info(f"Archived {archived_count} old log files")
        return archived_count


class EnhancedLogger:
    """Enhanced logger with structured logging capabilities"""
    
    def __init__(self, name: str, aggregator: LogAggregator):
        self.name = name
        self.aggregator = aggregator
        self.context: Dict[str, Any] = {}
    
    def set_context(self, **context):
        """Set logging context for this logger"""
        self.context.update(context)
    
    def clear_context(self):
        """Clear logging context"""
        self.context.clear()
    
    def _log(self, level: LogLevel, category: LogCategory, message: str, 
            exc_info=None, **metadata):
        """Internal logging method"""
        import inspect
        
        # Get caller information
        frame = inspect.currentframe().f_back.f_back
        module = frame.f_globals.get('__name__', 'unknown')
        function = frame.f_code.co_name
        line_number = frame.f_lineno
        
        # Merge context and metadata
        combined_metadata = {**self.context, **metadata}
        
        entry = StructuredLogEntry(
            timestamp=datetime.utcnow(),
            level=level,
            category=category,
            message=message,
            logger_name=self.name,
            module=module,
            function=function,
            line_number=line_number,
            thread_id=str(threading.current_thread().ident),
            process_id=os.getpid(),
            metadata=combined_metadata,
            stack_trace=self._format_exception(exc_info) if exc_info else None
        )
        
        self.aggregator.add_entry(entry)
    
    def _format_exception(self, exc_info) -> str:
        """Format exception information"""
        import traceback
        return ''.join(traceback.format_exception(*exc_info))
    
    # Convenience logging methods
    def debug(self, message: str, **metadata):
        self._log(LogLevel.DEBUG, LogCategory.APPLICATION, message, **metadata)
    
    def info(self, message: str, **metadata):
        self._log(LogLevel.INFO, LogCategory.APPLICATION, message, **metadata)
    
    def warning(self, message: str, **metadata):
        self._log(LogLevel.WARNING, LogCategory.APPLICATION, message, **metadata)
    
    def error(self, message: str, exc_info=None, **metadata):
        self._log(LogLevel.ERROR, LogCategory.APPLICATION, message, exc_info=exc_info, **metadata)
    
    def critical(self, message: str, exc_info=None, **metadata):
        self._log(LogLevel.CRITICAL, LogCategory.APPLICATION, message, exc_info=exc_info, **metadata)
    
    # Specialized logging methods
    def security(self, message: str, **metadata):
        self._log(LogLevel.SECURITY, LogCategory.SECURITY, message, **metadata)
    
    def performance(self, message: str, **metadata):
        self._log(LogLevel.PERFORMANCE, LogCategory.PERFORMANCE, message, **metadata)
    
    def audit(self, message: str, **metadata):
        self._log(LogLevel.AUDIT, LogCategory.SECURITY, message, **metadata)
    
    def agent_event(self, message: str, **metadata):
        self._log(LogLevel.INFO, LogCategory.AGENT, message, **metadata)
    
    def user_event(self, message: str, **metadata):
        self._log(LogLevel.INFO, LogCategory.USER, message, **metadata)
    
    def api_event(self, message: str, **metadata):
        self._log(LogLevel.INFO, LogCategory.API, message, **metadata)


class CentralizedLoggingSystem:
    """
    Main centralized logging system.
    
    Coordinates log aggregation, structured logging, and provides
    a unified interface for all logging operations.
    """
    
    def __init__(self):
        self.aggregator = LogAggregator()
        self.loggers: Dict[str, EnhancedLogger] = {}
        self.monitoring_enabled = True
        base_logger.info("Centralized logging system initialized")
    
    def get_logger(self, name: str) -> EnhancedLogger:
        """Get or create enhanced logger"""
        if name not in self.loggers:
            self.loggers[name] = EnhancedLogger(name, self.aggregator)
        return self.loggers[name]
    
    def get_recent_logs(self, count: int = 100, **filters) -> List[Dict[str, Any]]:
        """Get recent log entries"""
        return self.aggregator.get_recent_logs(count, **filters)
    
    def get_security_events(self, hours: int = 24) -> List[Dict[str, Any]]:
        """Get recent security events"""
        since = datetime.utcnow() - timedelta(hours=hours)
        return self.aggregator.get_recent_logs(
            count=1000,
            category=LogCategory.SECURITY,
            since=since
        )
    
    def get_error_summary(self, hours: int = 24) -> Dict[str, Any]:
        """Get error summary for time period"""
        since = datetime.utcnow() - timedelta(hours=hours)
        
        error_entries = self.aggregator.buffer.get_filtered(
            level=LogLevel.ERROR,
            since=since
        )
        critical_entries = self.aggregator.buffer.get_filtered(
            level=LogLevel.CRITICAL,
            since=since
        )
        
        return {
            'time_period_hours': hours,
            'error_count': len(error_entries),
            'critical_count': len(critical_entries),
            'total_issues': len(error_entries) + len(critical_entries),
            'recent_errors': [entry.to_dict() for entry in error_entries[-10:]],
            'recent_critical': [entry.to_dict() for entry in critical_entries[-10:]]
        }
    
    def get_system_health_logs(self) -> Dict[str, Any]:
        """Get system health information from logs"""
        stats = self.aggregator.get_log_statistics()
        error_summary = self.get_error_summary()
        
        return {
            'logging_statistics': stats,
            'error_summary': error_summary,
            'security_events_24h': len(self.get_security_events()),
            'system_status': 'healthy' if error_summary['total_issues'] < 10 else 'degraded'
        }
    
    def archive_logs(self, days_to_keep: int = 30):
        """Archive old log files"""
        return self.aggregator.archive_old_logs(days_to_keep)
    
    def export_logs(self, filepath: str, **filters):
        """Export filtered logs to JSON file"""
        entries = self.aggregator.get_recent_logs(count=10000, **filters)
        
        export_data = {
            'export_timestamp': datetime.utcnow().isoformat(),
            'filter_criteria': filters,
            'entry_count': len(entries),
            'entries': entries
        }
        
        Path(filepath).parent.mkdir(parents=True, exist_ok=True)
        with open(filepath, 'w') as f:
            json.dump(export_data, f, indent=2, default=str)
        
        base_logger.info(f"Exported {len(entries)} log entries to {filepath}")


# Global logging system instance
_logging_system = None

def get_logging_system() -> CentralizedLoggingSystem:
    """Get or create the global logging system instance"""
    global _logging_system
    if _logging_system is None:
        _logging_system = CentralizedLoggingSystem()
    return _logging_system


def get_enhanced_logger(name: str) -> EnhancedLogger:
    """Get enhanced logger instance"""
    system = get_logging_system()
    return system.get_logger(name)


def main():
    """Command line interface for logging system"""
    import argparse
    
    parser = argparse.ArgumentParser(description="JARVIS-MK42 Centralized Logging System")
    parser.add_argument('--recent', type=int, default=50, help='Show recent log entries')
    parser.add_argument('--security', action='store_true', help='Show security events')
    parser.add_argument('--errors', action='store_true', help='Show error summary')
    parser.add_argument('--health', action='store_true', help='Show system health from logs')
    parser.add_argument('--export', help='Export logs to JSON file')
    parser.add_argument('--archive', type=int, help='Archive logs older than N days')
    
    args = parser.parse_args()
    
    logging_system = get_logging_system()
    
    if args.recent:
        logs = logging_system.get_recent_logs(args.recent)
        for log in logs:
            print(f"{log['timestamp']} [{log['level']}] {log['message']}")
    
    elif args.security:
        events = logging_system.get_security_events()
        print(f"Security events in last 24 hours: {len(events)}")
        for event in events[-10:]:
            print(f"{event['timestamp']} [{event['level']}] {event['message']}")
    
    elif args.errors:
        summary = logging_system.get_error_summary()
        print(json.dumps(summary, indent=2))
    
    elif args.health:
        health = logging_system.get_system_health_logs()
        print(json.dumps(health, indent=2))
    
    elif args.export:
        logging_system.export_logs(args.export)
        print(f"Logs exported to {args.export}")
    
    elif args.archive is not None:
        count = logging_system.archive_logs(args.archive)
        print(f"Archived {count} log files older than {args.archive} days")
    
    else:
        print("JARVIS-MK42 Centralized Logging System")
        print("Use --recent, --security, --errors, --health, --export, or --archive")


if __name__ == "__main__":
    main()
