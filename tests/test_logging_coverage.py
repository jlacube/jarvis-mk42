"""
Comprehensive tests for utils.logging_config module
"""

import pytest
import logging
import tempfile
import json
import os
from unittest.mock import patch, MagicMock, Mock
from pathlib import Path


class TestLoggingConfigCoverage:
    """Test logging configuration for high coverage"""
    
    def test_json_formatter_basic_functionality(self):
        """Test JSONFormatter basic message formatting"""
        # Import directly with mocked dependencies
        import importlib.util
        spec = importlib.util.spec_from_file_location("logging_config", "utils/logging_config.py")
        logging_module = importlib.util.module_from_spec(spec)
        
        # Mock the config.settings import
        mock_settings = MagicMock()
        with patch.dict('sys.modules', {'config.settings': mock_settings}):
            spec.loader.exec_module(logging_module)
        
        JSONFormatter = logging_module.JSONFormatter
        
        # Create a formatter and test basic functionality
        formatter = JSONFormatter()
        
        # Create a mock log record
        record = logging.LogRecord(
            name="test_logger",
            level=logging.INFO,
            pathname="/test/path.py",
            lineno=123,
            msg="Test message",
            args=(),
            exc_info=None
        )
        record.module = "test_module"
        record.funcName = "test_function"
        
        # Format the record
        formatted = formatter.format(record)
        
        # Parse the JSON output
        log_data = json.loads(formatted)
        
        # Verify the basic structure
        assert log_data["level"] == "INFO"
        assert log_data["logger"] == "test_logger"
        assert log_data["message"] == "Test message"
        assert log_data["module"] == "test_module"
        assert log_data["function"] == "test_function"
        assert log_data["line"] == 123
        assert "timestamp" in log_data
    
    def test_json_formatter_with_exception(self):
        """Test JSONFormatter with exception information"""
        import importlib.util
        spec = importlib.util.spec_from_file_location("logging_config", "utils/logging_config.py")
        logging_module = importlib.util.module_from_spec(spec)
        
        mock_settings = MagicMock()
        with patch.dict('sys.modules', {'config.settings': mock_settings}):
            spec.loader.exec_module(logging_module)
        
        JSONFormatter = logging_module.JSONFormatter
        formatter = JSONFormatter()
        
        # Create a record with exception info
        try:
            raise ValueError("Test exception")
        except ValueError:
            import sys
            exc_info = sys.exc_info()
        
        record = logging.LogRecord(
            name="test_logger",
            level=logging.ERROR,
            pathname="/test/path.py",
            lineno=123,
            msg="Error occurred",
            args=(),
            exc_info=exc_info
        )
        record.module = "test_module"
        record.funcName = "test_function"
        
        formatted = formatter.format(record)
        log_data = json.loads(formatted)
        
        assert log_data["level"] == "ERROR"
        assert log_data["message"] == "Error occurred"
        assert "exception" in log_data
        assert "ValueError" in log_data["exception"]
    
    def test_json_formatter_with_extra_fields(self):
        """Test JSONFormatter with extra contextual fields"""
        import importlib.util
        spec = importlib.util.spec_from_file_location("logging_config", "utils/logging_config.py")
        logging_module = importlib.util.module_from_spec(spec)
        
        mock_settings = MagicMock()
        with patch.dict('sys.modules', {'config.settings': mock_settings}):
            spec.loader.exec_module(logging_module)
        
        JSONFormatter = logging_module.JSONFormatter
        formatter = JSONFormatter()
        
        # Create a record with extra fields
        record = logging.LogRecord(
            name="test_logger",
            level=logging.INFO,
            pathname="/test/path.py",
            lineno=123,
            msg="Test message",
            args=(),
            exc_info=None
        )
        record.module = "test_module"
        record.funcName = "test_function"
        
        # Add extra fields
        record.user_id = "user123"
        record.session_id = "session456"
        record.request_id = "request789"
        record.tool_name = "test_tool"
        record.agent_name = "test_agent"
        
        formatted = formatter.format(record)
        log_data = json.loads(formatted)
        
        assert log_data["user_id"] == "user123"
        assert log_data["session_id"] == "session456"
        assert log_data["request_id"] == "request789"
        assert log_data["tool_name"] == "test_tool"
        assert log_data["agent_name"] == "test_agent"
    
    def test_contextual_logger_adapter(self):
        """Test ContextualLoggerAdapter functionality"""
        import importlib.util
        spec = importlib.util.spec_from_file_location("logging_config", "utils/logging_config.py")
        logging_module = importlib.util.module_from_spec(spec)
        
        mock_settings = MagicMock()
        with patch.dict('sys.modules', {'config.settings': mock_settings}):
            spec.loader.exec_module(logging_module)
        
        ContextualLoggerAdapter = logging_module.ContextualLoggerAdapter
        
        # Create a mock logger
        mock_logger = Mock()
        context = {"user_id": "test_user", "session_id": "test_session"}
        
        adapter = ContextualLoggerAdapter(mock_logger, context)
        
        # Test process method with no extra kwargs
        msg, kwargs = adapter.process("test message", {})
        assert kwargs["extra"]["user_id"] == "test_user"
        assert kwargs["extra"]["session_id"] == "test_session"
        
        # Test process method with existing extra kwargs
        msg, kwargs = adapter.process("test message", {"extra": {"request_id": "req123"}})
        assert kwargs["extra"]["user_id"] == "test_user"
        assert kwargs["extra"]["session_id"] == "test_session"
        assert kwargs["extra"]["request_id"] == "req123"
    
    def test_get_logger_function(self):
        """Test get_logger function"""
        import importlib.util
        spec = importlib.util.spec_from_file_location("logging_config", "utils/logging_config.py")
        logging_module = importlib.util.module_from_spec(spec)
        
        mock_settings = MagicMock()
        with patch.dict('sys.modules', {'config.settings': mock_settings}):
            spec.loader.exec_module(logging_module)
        
        get_logger = logging_module.get_logger
        ContextualLoggerAdapter = logging_module.ContextualLoggerAdapter
        
        # Test getting a logger with context
        logger_adapter = get_logger("test.module", user_id="user123", tool_name="test_tool")
        
        assert isinstance(logger_adapter, ContextualLoggerAdapter)
        assert logger_adapter.extra["user_id"] == "user123"
        assert logger_adapter.extra["tool_name"] == "test_tool"
        
        # Test getting a logger without context
        logger_adapter_no_context = get_logger("test.module2")
        assert isinstance(logger_adapter_no_context, ContextualLoggerAdapter)
        assert logger_adapter_no_context.extra == {}
    
    def test_log_function_call_decorator_success(self):
        """Test log_function_call decorator for successful function calls"""
        import importlib.util
        spec = importlib.util.spec_from_file_location("logging_config", "utils/logging_config.py")
        logging_module = importlib.util.module_from_spec(spec)
        
        mock_settings = MagicMock()
        with patch.dict('sys.modules', {'config.settings': mock_settings}):
            spec.loader.exec_module(logging_module)
        
        log_function_call = logging_module.log_function_call
        
        # Mock the get_logger function to avoid actual logging
        with patch.object(logging_module, 'get_logger') as mock_get_logger:
            mock_logger = Mock()
            mock_get_logger.return_value = mock_logger
            
            @log_function_call
            def test_function(arg1, arg2, kwarg1=None):
                return f"result_{arg1}_{arg2}_{kwarg1}"
            
            # Call the decorated function
            result = test_function("a", "b", kwarg1="c")
            
            # Verify the result
            assert result == "result_a_b_c"
            
            # Verify logging calls
            assert mock_get_logger.called
            assert mock_logger.info.call_count == 2  # Start and completion
            assert mock_logger.error.call_count == 0  # No errors
    
    def test_log_function_call_decorator_exception(self):
        """Test log_function_call decorator for functions that raise exceptions"""
        import importlib.util
        spec = importlib.util.spec_from_file_location("logging_config", "utils/logging_config.py")
        logging_module = importlib.util.module_from_spec(spec)
        
        mock_settings = MagicMock()
        with patch.dict('sys.modules', {'config.settings': mock_settings}):
            spec.loader.exec_module(logging_module)
        
        log_function_call = logging_module.log_function_call
        
        with patch.object(logging_module, 'get_logger') as mock_get_logger:
            mock_logger = Mock()
            mock_get_logger.return_value = mock_logger
            
            @log_function_call
            def failing_function():
                raise ValueError("Test error")
            
            # Call the decorated function and expect exception
            with pytest.raises(ValueError, match="Test error"):
                failing_function()
            
            # Verify logging calls
            assert mock_get_logger.called
            assert mock_logger.info.call_count == 1  # Start only
            assert mock_logger.error.call_count == 1  # Error logged
    
    @pytest.mark.asyncio
    async def test_log_async_function_call_decorator_success(self):
        """Test log_async_function_call decorator for successful async functions"""
        import importlib.util
        spec = importlib.util.spec_from_file_location("logging_config", "utils/logging_config.py")
        logging_module = importlib.util.module_from_spec(spec)
        
        mock_settings = MagicMock()
        with patch.dict('sys.modules', {'config.settings': mock_settings}):
            spec.loader.exec_module(logging_module)
        
        log_async_function_call = logging_module.log_async_function_call
        
        with patch.object(logging_module, 'get_logger') as mock_get_logger:
            mock_logger = Mock()
            mock_get_logger.return_value = mock_logger
            
            @log_async_function_call
            async def async_test_function(value):
                return f"async_result_{value}"
            
            # Call the decorated async function
            result = await async_test_function("test")
            
            # Verify the result
            assert result == "async_result_test"
            
            # Verify logging calls
            assert mock_get_logger.called
            assert mock_logger.info.call_count == 2  # Start and completion
            assert mock_logger.error.call_count == 0  # No errors
    
    @pytest.mark.asyncio
    async def test_log_async_function_call_decorator_exception(self):
        """Test log_async_function_call decorator for async functions that raise exceptions"""
        import importlib.util
        spec = importlib.util.spec_from_file_location("logging_config", "utils/logging_config.py")
        logging_module = importlib.util.module_from_spec(spec)
        
        mock_settings = MagicMock()
        with patch.dict('sys.modules', {'config.settings': mock_settings}):
            spec.loader.exec_module(logging_module)
        
        log_async_function_call = logging_module.log_async_function_call
        
        with patch.object(logging_module, 'get_logger') as mock_get_logger:
            mock_logger = Mock()
            mock_get_logger.return_value = mock_logger
            
            @log_async_function_call
            async def failing_async_function():
                raise RuntimeError("Async test error")
            
            # Call the decorated function and expect exception
            with pytest.raises(RuntimeError, match="Async test error"):
                await failing_async_function()
            
            # Verify logging calls
            assert mock_get_logger.called
            assert mock_logger.info.call_count == 1  # Start only
            assert mock_logger.error.call_count == 1  # Error logged


if __name__ == "__main__":
    pytest.main([__file__])
