# utils/logging_config.py
"""
Enhanced logging configuration for Jarvis-MK42
"""

import logging
import logging.handlers
import sys
from pathlib import Path
from typing import Dict, Any
import json
from datetime import datetime

from config.settings import get_settings

class JSONFormatter(logging.Formatter):
    """Custom JSON formatter for structured logging"""
    
    def format(self, record: logging.LogRecord) -> str:
        # Create log entry dictionary
        log_entry = {
            "timestamp": datetime.utcnow().isoformat(),
            "level": record.levelname,
            "logger": record.name,
            "message": record.getMessage(),
            "module": record.module,
            "function": record.funcName,
            "line": record.lineno,
        }
        
        # Add exception information if present
        if record.exc_info:
            log_entry["exception"] = self.formatException(record.exc_info)
        
        # Add extra fields if present
        if hasattr(record, 'user_id'):
            log_entry["user_id"] = record.user_id
        if hasattr(record, 'session_id'):
            log_entry["session_id"] = record.session_id
        if hasattr(record, 'request_id'):
            log_entry["request_id"] = record.request_id
        if hasattr(record, 'tool_name'):
            log_entry["tool_name"] = record.tool_name
        if hasattr(record, 'agent_name'):
            log_entry["agent_name"] = record.agent_name
        
        return json.dumps(log_entry)

class ContextualLoggerAdapter(logging.LoggerAdapter):
    """Logger adapter that adds contextual information to log records"""
    
    def process(self, msg, kwargs):
        # Add extra context to the record
        if 'extra' not in kwargs:
            kwargs['extra'] = {}
        
        # Merge adapter context with any extra context
        kwargs['extra'].update(self.extra)
        
        return msg, kwargs

def setup_logging():
    """Set up enhanced logging configuration"""
    settings = get_settings()
    
    # Create logs directory if it doesn't exist
    if settings.logging.file_path:
        log_path = Path(settings.logging.file_path)
        log_path.parent.mkdir(parents=True, exist_ok=True)
    
    # Configure root logger
    root_logger = logging.getLogger()
    root_logger.setLevel(getattr(logging, settings.logging.level.upper()))
    
    # Clear any existing handlers
    root_logger.handlers.clear()
    
    # Console handler with colored output for development
    console_handler = logging.StreamHandler(sys.stdout)
    if settings.app.debug:
        console_formatter = logging.Formatter(
            '%(asctime)s - %(name)s - %(levelname)s - %(message)s',
            datefmt='%Y-%m-%d %H:%M:%S'
        )
    else:
        console_formatter = JSONFormatter()
    
    console_handler.setFormatter(console_formatter)
    root_logger.addHandler(console_handler)
    
    # File handler with rotation
    if settings.logging.file_path:
        file_handler = logging.handlers.RotatingFileHandler(
            settings.logging.file_path,
            maxBytes=settings.logging.max_file_size,
            backupCount=settings.logging.backup_count,
            encoding='utf-8'
        )
        file_formatter = JSONFormatter()
        file_handler.setFormatter(file_formatter)
        root_logger.addHandler(file_handler)
    
    # Set specific logger levels
    logging.getLogger("chainlit").setLevel(logging.WARNING)
    logging.getLogger("langchain").setLevel(logging.WARNING)
    logging.getLogger("openai").setLevel(logging.WARNING)
    logging.getLogger("httpx").setLevel(logging.WARNING)
    logging.getLogger("httpcore").setLevel(logging.WARNING)
    
    return root_logger

def get_logger(name: str, **context) -> ContextualLoggerAdapter:
    """Get a contextual logger with optional context"""
    logger = logging.getLogger(name)
    return ContextualLoggerAdapter(logger, context)

def log_function_call(func):
    """Decorator to log function calls with parameters and results"""
    def wrapper(*args, **kwargs):
        logger = get_logger(func.__module__)
        logger.info(f"Calling {func.__name__}", extra={
            "function": func.__name__,
            "args_count": len(args),
            "kwargs_keys": list(kwargs.keys())
        })
        
        try:
            result = func(*args, **kwargs)
            logger.info(f"Completed {func.__name__}", extra={
                "function": func.__name__,
                "success": True
            })
            return result
        except Exception as e:
            logger.error(f"Failed {func.__name__}: {str(e)}", extra={
                "function": func.__name__,
                "success": False,
                "error": str(e)
            }, exc_info=True)
            raise
    
    return wrapper

def log_async_function_call(func):
    """Decorator to log async function calls with parameters and results"""
    import functools
    
    @functools.wraps(func)
    async def wrapper(*args, **kwargs):
        logger = get_logger(func.__module__)
        logger.info(f"Calling {func.__name__}", extra={
            "function": func.__name__,
            "args_count": len(args),
            "kwargs_keys": list(kwargs.keys())
        })
        
        try:
            result = await func(*args, **kwargs)
            logger.info(f"Completed {func.__name__}", extra={
                "function": func.__name__,
                "success": True
            })
            return result
        except Exception as e:
            logger.error(f"Failed {func.__name__}: {str(e)}", extra={
                "function": func.__name__,
                "success": False,
                "error": str(e)
            }, exc_info=True)
            raise
    
    return wrapper
