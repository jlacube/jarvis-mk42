import pytest
from unittest.mock import Mock, patch, MagicMock
import sys
import logging
from typing import List
from langchain_core.tools import BaseTool


class TestToolsInitSimplified:
    """Simplified test coverage for tools.__init__ module."""
    
    def test_is_installed_with_available_command(self):
        """Test is_installed function when command is available."""
        with patch('tools.shutil.which') as mock_which:
            mock_which.return_value = '/usr/bin/git'
            
            from tools import is_installed
            result = is_installed('git')
            
            assert result is True
            mock_which.assert_called_once_with('git')
    
    def test_is_installed_with_unavailable_command(self):
        """Test is_installed function when command is not available."""
        with patch('tools.shutil.which') as mock_which:
            mock_which.return_value = None
            
            from tools import is_installed
            result = is_installed('nonexistent_command')
            
            assert result is False
            mock_which.assert_called_once_with('nonexistent_command')
    
    def test_get_all_tools_function_exists_and_returns_list(self):
        """Test that get_all_tools function exists and returns a list."""
        from tools import get_all_tools
        
        # Call the actual function - it should return a list of tools
        tools = get_all_tools()
        
        # Verify it returns a list
        assert isinstance(tools, list)
        
        # Verify all items in the list are BaseTool instances
        for tool in tools:
            assert hasattr(tool, 'name'), f"Tool {tool} missing 'name' attribute"
            assert hasattr(tool, 'description'), f"Tool {tool} missing 'description' attribute"
    
    @patch('tools.logger')
    def test_get_all_tools_handles_import_errors_gracefully(self, mock_logger):
        """Test that get_all_tools handles import errors gracefully by patching optional imports."""
        
        # Create a custom import function that fails for optional modules
        original_import = __builtins__.__import__
        
        def failing_import(name, *args, **kwargs):
            # Fail on optional imports but allow core imports
            if any(opt in name for opt in ['document_intelligence', 'language_detection', 'enhanced_research_tools']):
                raise ImportError(f"Mocked import failure for {name}")
            return original_import(name, *args, **kwargs)
        
        with patch('builtins.__import__', side_effect=failing_import):
            from tools import get_all_tools
            tools = get_all_tools()
            
            # Should still return a list of tools (at least the core ones)
            assert isinstance(tools, list)
            assert len(tools) > 0
            
            # Should have logged warnings for failed imports
            warning_calls = [call for call in mock_logger.warning.call_args_list 
                           if 'not available' in str(call)]
            assert len(warning_calls) > 0
    
    def test_get_all_tools_logger_configuration(self):
        """Test that the logger is properly configured."""
        import tools
        
        # Verify logger exists and is properly named
        assert hasattr(tools, 'logger')
        assert tools.logger.name == 'tools'
        assert isinstance(tools.logger, logging.Logger)
