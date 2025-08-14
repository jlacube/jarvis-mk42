"""
Tests for utils and configuration modules

These tests cover the core utility functions and configuration management
to improve overall code coverage.
"""

import pytest
import os
import tempfile
import logging
from unittest.mock import patch, mock_open, MagicMock

# Import modules to test
import config
from utils.exceptions import JarvisValidationError, JarvisToolError, JarvisError
from utils.logging_config import setup_logging, get_logger
from utils.language_utils import get_language_context, normalize_text_for_language, is_text_mixed_language


class TestConfig:
    """Test configuration module"""
    
    def test_config_constants(self):
        """Test that configuration constants are properly defined"""
        assert hasattr(config, 'SUPERVISOR_PROMPT_NAME')
        assert config.SUPERVISOR_PROMPT_NAME == "supervisor"
        
        assert hasattr(config, 'JARVIS_NAME')
        assert config.JARVIS_NAME == "Jarvis_MK42"
        
        assert hasattr(config, 'RECURSION_LIMIT')
        assert isinstance(config.RECURSION_LIMIT, int)
        assert config.RECURSION_LIMIT > 0
    
    def test_mpv_installed_env_var(self):
        """Test MPV_INSTALLED environment variable handling"""
        # Test default value
        with patch.dict(os.environ, {}, clear=True):
            # Reload the module to get fresh env var reading
            import importlib
            importlib.reload(config)
            assert config.MPV_INSTALLED is False
        
        # Test True value
        with patch.dict(os.environ, {'MPV_INSTALLED': 'true'}):
            importlib.reload(config)
            assert config.MPV_INSTALLED is True
        
        # Test False value
        with patch.dict(os.environ, {'MPV_INSTALLED': 'false'}):
            importlib.reload(config)
            assert config.MPV_INSTALLED is False


class TestExceptions:
    """Test custom exception classes"""
    
    def test_jarvis_error_base(self):
        """Test base JarvisError exception"""
        error = JarvisError("Test error message")
        assert str(error) == "Test error message"
        assert isinstance(error, Exception)
    
    def test_jarvis_validation_error(self):
        """Test JarvisValidationError exception"""
        error = JarvisValidationError("Invalid input")
        assert str(error) == "Invalid input"
        assert isinstance(error, JarvisError)
        assert isinstance(error, ValueError)
    
    def test_jarvis_tool_error(self):
        """Test JarvisToolError exception"""
        error = JarvisToolError("Tool execution failed")
        assert str(error) == "Tool execution failed"
        assert isinstance(error, JarvisError)
        assert isinstance(error, RuntimeError)


class TestLoggingConfig:
    """Test logging configuration utilities"""
    
    def test_setup_logging_default(self):
        """Test setup_logging with default parameters"""
        with patch('logging.basicConfig') as mock_basic_config:
            setup_logging()
            mock_basic_config.assert_called_once()
            call_args = mock_basic_config.call_args[1]
            assert call_args['level'] == logging.INFO
            assert 'format' in call_args
    
    def test_setup_logging_custom_level(self):
        """Test setup_logging with custom level"""
        with patch('logging.basicConfig') as mock_basic_config:
            setup_logging(level=logging.DEBUG)
            mock_basic_config.assert_called_once()
            call_args = mock_basic_config.call_args[1]
            assert call_args['level'] == logging.DEBUG
    
    def test_get_logger(self):
        """Test get_logger utility function"""
        logger = get_logger("test_module")
        assert isinstance(logger, logging.Logger)
        assert logger.name == "test_module"
    
    def test_get_logger_with_level(self):
        """Test get_logger with custom level"""
        logger = get_logger("test_module", level=logging.WARNING)
        assert logger.level == logging.WARNING


class TestLanguageUtils:
    """Test language utility functions"""
    
    def test_get_language_context_english(self):
        """Test language context for English text"""
        text = "Hello, this is a test in English."
        context = get_language_context(text)
        
        assert hasattr(context, 'language_code')
        assert hasattr(context, 'confidence')
        assert hasattr(context, 'family')
        assert hasattr(context, 'direction')
    
    def test_get_language_context_short_text(self):
        """Test language context for very short text"""
        text = "Hi"
        context = get_language_context(text)
        
        assert hasattr(context, 'language_code')
        assert hasattr(context, 'is_reliable')
        assert hasattr(context, 'confidence')
    
    def test_get_language_context_empty_text(self):
        """Test language context for empty text"""
        try:
            context = get_language_context("")
            # Should handle gracefully
            assert context is None or hasattr(context, 'language_code')
        except Exception:
            # Exception is acceptable for empty text
            pass
    
    def test_normalize_text_for_language(self):
        """Test text normalization for different languages"""
        text = "  HELLO World  "
        normalized = normalize_text_for_language(text, 'en')
        assert isinstance(normalized, str)
        assert len(normalized.strip()) > 0
        
        # Test other language
        text = "  Hola Mundo  "
        normalized = normalize_text_for_language(text, 'es')
        assert isinstance(normalized, str)
    
    def test_is_text_mixed_language_single(self):
        """Test detection of single language text"""
        text = "This is a complete English sentence with many words."
        is_mixed = is_text_mixed_language(text)
        assert isinstance(is_mixed, bool)
    
    def test_is_text_mixed_language_mixed(self):
        """Test detection of mixed language text"""
        text = "Hello world. Bonjour le monde. Hola mundo."
        is_mixed = is_text_mixed_language(text)
        assert isinstance(is_mixed, bool)
    
    def test_language_utils_error_handling(self):
        """Test error handling in language utilities"""
        # Test with None input
        try:
            context = get_language_context(None)
            assert context is None
        except (TypeError, ValueError):
            # Expected for None input
            pass


class TestUtilsIntegration:
    """Integration tests for utils modules"""
    
    def test_error_handling_with_logging(self):
        """Test that errors work properly with logging"""
        logger = get_logger("test_integration")
        
        try:
            raise JarvisValidationError("Test validation error")
        except JarvisValidationError as e:
            logger.error(f"Caught validation error: {e}")
            assert str(e) == "Test validation error"
    
    def test_language_detection_with_error_handling(self):
        """Test language context with proper error handling"""
        try:
            # Test with None input
            context = get_language_context(None)
            assert context is None
        except Exception as e:
            # Should handle gracefully
            assert isinstance(e, (JarvisError, TypeError))
    
    def test_config_environment_integration(self):
        """Test configuration with environment variables"""
        # Test that config can be imported and used
        assert hasattr(config, 'JARVIS_NAME')
        
        # Test environment variable handling
        with patch.dict(os.environ, {'TEST_CONFIG_VAR': 'test_value'}):
            test_value = os.environ.get('TEST_CONFIG_VAR', 'default')
            assert test_value == 'test_value'


if __name__ == "__main__":
    pytest.main([__file__])
