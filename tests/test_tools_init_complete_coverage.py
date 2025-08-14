import pytest
from unittest.mock import Mock, patch, MagicMock
import sys
import logging
from typing import List
from langchain_core.tools import BaseTool


class TestToolsInit:
    """Comprehensive test coverage for tools.__init__ module."""
    
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
    
    def test_get_all_tools_core_tools_success(self):
        """Test get_all_tools with successful core tool imports."""
        # Mock all the get_*_tools functions
        mock_file_tools = [Mock(spec=BaseTool)]
        mock_research_tools = [Mock(spec=BaseTool)]
        mock_reasoning_tools = [Mock(spec=BaseTool)]
        mock_math_tools = [Mock(spec=BaseTool)]
        mock_multimodal_tools = [Mock(spec=BaseTool)]
        
        with patch('tools.file_tools.get_file_tools', return_value=mock_file_tools) as mock_get_file, \
             patch('tools.research_tools.get_research_tools', return_value=mock_research_tools) as mock_get_research, \
             patch('tools.reasoning_tools.get_reasoning_tools', return_value=mock_reasoning_tools) as mock_get_reasoning, \
             patch('tools.math_tools.get_math_tools', return_value=mock_math_tools) as mock_get_math, \
             patch('tools.multimodal_tools.get_multimodal_tools', return_value=mock_multimodal_tools) as mock_get_multimodal:
            
            from tools import get_all_tools
            tools = get_all_tools()
            
            # Should have 5 tools (one from each core module)
            assert len(tools) == 5
            assert mock_file_tools[0] in tools
            assert mock_research_tools[0] in tools
            assert mock_reasoning_tools[0] in tools
            assert mock_math_tools[0] in tools
            assert mock_multimodal_tools[0] in tools
            
            # Verify all core functions were called
            mock_get_file.assert_called_once()
            mock_get_research.assert_called_once()
            mock_get_reasoning.assert_called_once()
            mock_get_math.assert_called_once()
            mock_get_multimodal.assert_called_once()
    
    @patch('tools.logger')
    def test_get_all_tools_with_document_intelligence_success(self, mock_logger):
        """Test get_all_tools with successful document intelligence tools import."""
        # Mock core tools
        mock_core_tools = [Mock(spec=BaseTool) for _ in range(5)]
        mock_doc_tools = [Mock(spec=BaseTool)]
        
        with patch('tools.file_tools.get_file_tools', return_value=[mock_core_tools[0]]), \
             patch('tools.research_tools.get_research_tools', return_value=[mock_core_tools[1]]), \
             patch('tools.reasoning_tools.get_reasoning_tools', return_value=[mock_core_tools[2]]), \
             patch('tools.math_tools.get_math_tools', return_value=[mock_core_tools[3]]), \
             patch('tools.multimodal_tools.get_multimodal_tools', return_value=[mock_core_tools[4]]), \
             patch('tools.document_intelligence.get_document_intelligence_tools', return_value=mock_doc_tools):
            
            from tools import get_all_tools
            tools = get_all_tools()
            
            # Should have 6 tools (5 core + 1 document intelligence)
            assert len(tools) == 6
            assert mock_doc_tools[0] in tools
            mock_logger.warning.assert_not_called()
    
    @patch('tools.logger')
    def test_get_all_tools_with_document_intelligence_import_error(self, mock_logger):
        """Test get_all_tools with document intelligence import error."""
        mock_core_tools = [Mock(spec=BaseTool) for _ in range(5)]
        
        with patch('tools.file_tools.get_file_tools', return_value=[mock_core_tools[0]]), \
             patch('tools.research_tools.get_research_tools', return_value=[mock_core_tools[1]]), \
             patch('tools.reasoning_tools.get_reasoning_tools', return_value=[mock_core_tools[2]]), \
             patch('tools.math_tools.get_math_tools', return_value=[mock_core_tools[3]]), \
             patch('tools.multimodal_tools.get_multimodal_tools', return_value=[mock_core_tools[4]]):
            
            # Simulate ImportError for document intelligence
            def mock_import(name, *args, **kwargs):
                if 'document_intelligence' in name:
                    raise ImportError("Module not found")
                return __import__(name, *args, **kwargs)
            
            with patch('builtins.__import__', side_effect=mock_import):
                from tools import get_all_tools
                tools = get_all_tools()
                
                # Should have only 5 core tools
                assert len(tools) == 5
                mock_logger.warning.assert_called_with("Document intelligence tools not available: Module not found")
    
    @patch('tools.logger')
    def test_get_all_tools_with_language_detection_success(self, mock_logger):
        """Test get_all_tools with successful language detection tools import."""
        mock_core_tools = [Mock(spec=BaseTool) for _ in range(5)]
        mock_lang_tools = [Mock(spec=BaseTool)]
        
        with patch('tools.file_tools.get_file_tools', return_value=[mock_core_tools[0]]), \
             patch('tools.research_tools.get_research_tools', return_value=[mock_core_tools[1]]), \
             patch('tools.reasoning_tools.get_reasoning_tools', return_value=[mock_core_tools[2]]), \
             patch('tools.math_tools.get_math_tools', return_value=[mock_core_tools[3]]), \
             patch('tools.multimodal_tools.get_multimodal_tools', return_value=[mock_core_tools[4]]), \
             patch('tools.language_detection.get_language_detection_tools', return_value=mock_lang_tools):
            
            from tools import get_all_tools
            tools = get_all_tools()
            
            # Should have 6 tools (5 core + 1 language detection)
            assert len(tools) == 6
            assert mock_lang_tools[0] in tools
    
    @patch('tools.logger')
    def test_get_all_tools_with_language_detection_import_error(self, mock_logger):
        """Test get_all_tools with language detection import error."""
        mock_core_tools = [Mock(spec=BaseTool) for _ in range(5)]
        
        with patch('tools.file_tools.get_file_tools', return_value=[mock_core_tools[0]]), \
             patch('tools.research_tools.get_research_tools', return_value=[mock_core_tools[1]]), \
             patch('tools.reasoning_tools.get_reasoning_tools', return_value=[mock_core_tools[2]]), \
             patch('tools.math_tools.get_math_tools', return_value=[mock_core_tools[3]]), \
             patch('tools.multimodal_tools.get_multimodal_tools', return_value=[mock_core_tools[4]]):
            
            # Simulate ImportError for language detection by patching the import path  
            def mock_import(name, *args, **kwargs):
                if 'language_detection' in name:
                    raise ImportError("Language detection not available")
                return __import__(name, *args, **kwargs)
            
            with patch('builtins.__import__', side_effect=mock_import):
                from tools import get_all_tools
                tools = get_all_tools()
                
                # Should have only 5 core tools
                assert len(tools) == 5
                mock_logger.warning.assert_called_with("Language detection tools not available: Language detection not available")
    
    @patch('tools.logger')
    def test_get_all_tools_with_enhanced_research_success(self, mock_logger):
        """Test get_all_tools with successful enhanced research tools import."""
        mock_core_tools = [Mock(spec=BaseTool) for _ in range(5)]
        mock_enhanced_tools = [Mock(spec=BaseTool)]
        
        with patch('tools.file_tools.get_file_tools', return_value=[mock_core_tools[0]]), \
             patch('tools.research_tools.get_research_tools', return_value=[mock_core_tools[1]]), \
             patch('tools.reasoning_tools.get_reasoning_tools', return_value=[mock_core_tools[2]]), \
             patch('tools.math_tools.get_math_tools', return_value=[mock_core_tools[3]]), \
             patch('tools.multimodal_tools.get_multimodal_tools', return_value=[mock_core_tools[4]]), \
             patch('tools.enhanced_research_tools.get_enhanced_research_tools', return_value=mock_enhanced_tools):
            
            from tools import get_all_tools
            tools = get_all_tools()
            
            # Should have 6 tools (5 core + 1 enhanced research)
            assert len(tools) == 6
            assert mock_enhanced_tools[0] in tools
    
    @patch('tools.logger')
    def test_get_all_tools_with_enhanced_research_import_error(self, mock_logger):
        """Test get_all_tools with enhanced research import error."""
        mock_core_tools = [Mock(spec=BaseTool) for _ in range(5)]
        
        with patch('tools.file_tools.get_file_tools', return_value=[mock_core_tools[0]]), \
             patch('tools.research_tools.get_research_tools', return_value=[mock_core_tools[1]]), \
             patch('tools.reasoning_tools.get_reasoning_tools', return_value=[mock_core_tools[2]]), \
             patch('tools.math_tools.get_math_tools', return_value=[mock_core_tools[3]]), \
             patch('tools.multimodal_tools.get_multimodal_tools', return_value=[mock_core_tools[4]]):
            
            # Simulate ImportError for enhanced research
            def mock_import(name, *args, **kwargs):
                if 'enhanced_research_tools' in name:
                    raise ImportError("Enhanced research not available")
                return __import__(name, *args, **kwargs)
            
            with patch('builtins.__import__', side_effect=mock_import):
                from tools import get_all_tools
                tools = get_all_tools()
                
                # Should have only 5 core tools
                assert len(tools) == 5
                mock_logger.warning.assert_called_with("Enhanced research tools not available: Enhanced research not available")
    
    def test_get_all_tools_with_plotting_success(self):
        """Test get_all_tools with successful plotting tools import."""
        mock_core_tools = [Mock(spec=BaseTool) for _ in range(5)]
        mock_plotting_tools = [Mock(spec=BaseTool)]
        
        with patch('tools.file_tools.get_file_tools', return_value=[mock_core_tools[0]]), \
             patch('tools.research_tools.get_research_tools', return_value=[mock_core_tools[1]]), \
             patch('tools.reasoning_tools.get_reasoning_tools', return_value=[mock_core_tools[2]]), \
             patch('tools.math_tools.get_math_tools', return_value=[mock_core_tools[3]]), \
             patch('tools.multimodal_tools.get_multimodal_tools', return_value=[mock_core_tools[4]]), \
             patch('tools.plotting.get_plotting_tools', return_value=mock_plotting_tools):
            
            from tools import get_all_tools
            tools = get_all_tools()
            
            # Should have 6 tools (5 core + 1 plotting)
            assert len(tools) == 6
            assert mock_plotting_tools[0] in tools
    
    def test_get_all_tools_with_plotting_import_error(self):
        """Test get_all_tools with plotting import error (silent failure)."""
        mock_core_tools = [Mock(spec=BaseTool) for _ in range(5)]
        
        with patch('tools.file_tools.get_file_tools', return_value=[mock_core_tools[0]]), \
             patch('tools.research_tools.get_research_tools', return_value=[mock_core_tools[1]]), \
             patch('tools.reasoning_tools.get_reasoning_tools', return_value=[mock_core_tools[2]]), \
             patch('tools.math_tools.get_math_tools', return_value=[mock_core_tools[3]]), \
             patch('tools.multimodal_tools.get_multimodal_tools', return_value=[mock_core_tools[4]]):
            
            # Simulate ImportError for plotting (should be silent)
            def mock_import(name, *args, **kwargs):
                if 'plotting' in name:
                    raise ImportError("Plotting not available")
                return __import__(name, *args, **kwargs)
            
            with patch('builtins.__import__', side_effect=mock_import):
                from tools import get_all_tools
                tools = get_all_tools()
                
                # Should have only 5 core tools (plotting failure is silent)
                assert len(tools) == 5
    
    def test_get_all_tools_with_agents_tools_success(self):
        """Test get_all_tools with successful agents tools import."""
        mock_core_tools = [Mock(spec=BaseTool) for _ in range(5)]
        mock_agent_tools = [Mock(spec=BaseTool)]
        
        with patch('tools.file_tools.get_file_tools', return_value=[mock_core_tools[0]]), \
             patch('tools.research_tools.get_research_tools', return_value=[mock_core_tools[1]]), \
             patch('tools.reasoning_tools.get_reasoning_tools', return_value=[mock_core_tools[2]]), \
             patch('tools.math_tools.get_math_tools', return_value=[mock_core_tools[3]]), \
             patch('tools.multimodal_tools.get_multimodal_tools', return_value=[mock_core_tools[4]]), \
             patch('tools.agents_tools.get_agent_tools', return_value=mock_agent_tools):
            
            from tools import get_all_tools
            tools = get_all_tools()
            
            # Should have 6 tools (5 core + 1 agent)
            assert len(tools) == 6
            assert mock_agent_tools[0] in tools
    
    def test_get_all_tools_with_agents_tools_import_error(self):
        """Test get_all_tools with agents tools import error (silent failure)."""
        mock_core_tools = [Mock(spec=BaseTool) for _ in range(5)]
        
        with patch('tools.file_tools.get_file_tools', return_value=[mock_core_tools[0]]), \
             patch('tools.research_tools.get_research_tools', return_value=[mock_core_tools[1]]), \
             patch('tools.reasoning_tools.get_reasoning_tools', return_value=[mock_core_tools[2]]), \
             patch('tools.math_tools.get_math_tools', return_value=[mock_core_tools[3]]), \
             patch('tools.multimodal_tools.get_multimodal_tools', return_value=[mock_core_tools[4]]):
            
            # Simulate ImportError for agents tools (should be silent)
            def mock_import(name, *args, **kwargs):
                if 'agents_tools' in name:
                    raise ImportError("Agents tools not available")
                return __import__(name, *args, **kwargs)
            
            with patch('builtins.__import__', side_effect=mock_import):
                from tools import get_all_tools
                tools = get_all_tools()
                
                # Should have only 5 core tools (agents tools failure is silent)
                assert len(tools) == 5
