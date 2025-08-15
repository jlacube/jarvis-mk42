# tests/test_document_intelligence_fixed.py
"""
Fixed integration tests for Enhanced Document Intelligence Tools
"""

import asyncio
import os
import tempfile
import pytest
from unittest.mock import patch, AsyncMock, MagicMock
from pathlib import Path

from tools.document_intelligence import DocumentProcessor, get_document_intelligence_tools
from utils.exceptions import JarvisValidationError, JarvisAPIError, JarvisToolError


class TestDocumentProcessor:
    """Test suite for DocumentProcessor class"""
    
    @pytest.fixture
    def processor(self):
        """Create a DocumentProcessor instance for testing"""
        return DocumentProcessor()
    
    @pytest.fixture
    def sample_text_file(self):
        """Create a temporary text file for testing"""
        with tempfile.NamedTemporaryFile(mode='w', suffix='.txt', delete=False) as f:
            f.write("This is a sample text document.\nIt has multiple lines.\nUsed for testing purposes.")
            return f.name
    
    def test_processor_initialization(self, processor):
        """Test DocumentProcessor initializes correctly"""
        assert processor is not None
        assert processor.text_splitter is not None
        # Note: No model attribute in current implementation
    
    @pytest.mark.asyncio
    async def test_process_text_document(self, processor, sample_text_file):
        """Test processing a text document"""
        try:
            result = await processor.process_document(sample_text_file)
            
            # Verify structure matches actual implementation
            assert result['analysis']['content_type'] == 'text'
            assert result['metadata']['file_path'] == sample_text_file
            assert 'content' in result
            assert 'metadata' in result
            assert 'analysis' in result
            assert result['metadata']['word_count'] > 0
            assert result['metadata']['char_count'] > 0
            
        finally:
            os.unlink(sample_text_file)
    
    @pytest.mark.asyncio
    async def test_file_size_validation(self, processor):
        """Test file size validation"""
        # Create a large file content that exceeds the limit
        large_content = b"x" * (60 * 1024 * 1024)  # 60MB, exceeds 50MB limit
        
        # Use in-memory content to test validation
        with tempfile.NamedTemporaryFile(suffix='.txt', delete=False) as f:
            temp_path = f.name
        
        try:
            with pytest.raises(JarvisToolError, match="Failed to process document"):
                await processor.process_document(temp_path, large_content)
        finally:
            if os.path.exists(temp_path):
                os.unlink(temp_path)
    
    @pytest.mark.asyncio
    async def test_unsupported_file_type(self, processor):
        """Test handling of unsupported file types - should still process as text"""
        with tempfile.NamedTemporaryFile(suffix='.xyz', delete=False) as f:
            f.write(b"test content")
            temp_path = f.name
        
        try:
            # Current implementation tries to decode as text for unknown formats
            result = await processor.process_document(temp_path)
            assert result['analysis']['content_type'] == 'text'
        finally:
            os.unlink(temp_path)
    
    @pytest.mark.asyncio
    async def test_nonexistent_file(self, processor):
        """Test handling of nonexistent files"""
        with pytest.raises(JarvisToolError, match="Failed to process document"):
            await processor.process_document("/nonexistent/file.txt")
    
    @pytest.mark.asyncio
    async def test_empty_file_processing(self, processor):
        """Test processing empty file"""
        with tempfile.NamedTemporaryFile(mode='w', suffix='.txt', delete=False) as f:
            f.write("")  # Empty file
            temp_path = f.name
        
        try:
            result = await processor.process_document(temp_path)
            assert result['analysis']['content_type'] == 'text'
            assert result['metadata']['word_count'] == 0
            assert result['metadata']['char_count'] == 0
        finally:
            os.unlink(temp_path)
    
    @pytest.mark.asyncio
    async def test_csv_processing(self, processor):
        """Test CSV file processing"""
        csv_content = "name,age,city\nJohn,25,New York\nJane,30,Boston\nBob,35,Chicago"
        
        with tempfile.NamedTemporaryFile(mode='w', suffix='.csv', delete=False) as f:
            f.write(csv_content)
            temp_path = f.name
        
        try:
            result = await processor.process_document(temp_path)
            assert result['analysis']['content_type'] == 'csv'
            assert 'John' in result['content']
            assert 'Boston' in result['content']
        finally:
            os.unlink(temp_path)


class TestDocumentTools:
    """Test suite for document intelligence tools"""
    
    @pytest.mark.asyncio
    async def test_analyze_document_tool_success(self):
        """Test successful document analysis tool execution"""
        content = "This is a comprehensive test document for the enhanced document intelligence system. It contains multiple sentences with various topics including artificial intelligence, machine learning, and natural language processing. The document serves as a benchmark for testing the analysis capabilities of the system."
        
        with tempfile.NamedTemporaryFile(mode='w', suffix='.txt', delete=False) as f:
            f.write(content)
            temp_path = f.name
        
        try:
            tools = get_document_intelligence_tools()
            analyze_tool = next(tool for tool in tools if tool.name == "analyze_document_tool")
            
            result = await analyze_tool.arun({"file_path": temp_path})
            
            # Check for expected content in the analysis report
            assert "Document analysis completed successfully" in result
            assert "File Information" in result
            assert "Content Analysis" in result
            assert "Word Count" in result
            assert temp_path in result
            
        finally:
            os.unlink(temp_path)
    
    @pytest.mark.asyncio
    async def test_analyze_document_tool_empty_path(self):
        """Test document analysis tool with empty path"""
        tools = get_document_intelligence_tools()
        analyze_tool = next(tool for tool in tools if tool.name == "analyze_document_tool")
        
        result = await analyze_tool.arun({"file_path": ""})
        
        # Should return error message
        assert "Error analyzing document" in result
    
    @pytest.mark.asyncio
    async def test_analyze_document_tool_none_path(self):
        """Test document analysis tool with None path"""
        tools = get_document_intelligence_tools()
        analyze_tool = next(tool for tool in tools if tool.name == "analyze_document_tool")
        
        result = await analyze_tool.arun({"file_path": None})
        
        # Should return error message
        assert "Error analyzing document" in result
    
    @pytest.mark.asyncio
    async def test_analyze_document_tool_nonexistent_file(self):
        """Test document analysis tool with nonexistent file"""
        tools = get_document_intelligence_tools()
        analyze_tool = next(tool for tool in tools if tool.name == "analyze_document_tool")
        
        result = await analyze_tool.arun({"file_path": "/nonexistent/path/file.txt"})
        
        # Should return error message
        assert "Error analyzing document" in result
    
    @pytest.mark.asyncio
    async def test_compare_documents_tool_success(self):
        """Test successful document comparison tool execution"""
        content1 = "This is the first document for comparison testing."
        content2 = "This is the second document for comparison testing with additional content."
        
        with tempfile.NamedTemporaryFile(mode='w', suffix='.txt', delete=False) as f1:
            f1.write(content1)
            temp_path1 = f1.name
        
        with tempfile.NamedTemporaryFile(mode='w', suffix='.txt', delete=False) as f2:
            f2.write(content2)
            temp_path2 = f2.name
        
        try:
            tools = get_document_intelligence_tools()
            compare_tool = next(tool for tool in tools if tool.name == "compare_documents_tool")
            
            result = await compare_tool.arun({"file_path1": temp_path1, "file_path2": temp_path2})
            
            # Check for expected content in the comparison report
            assert "Document comparison completed" in result
            assert "similarity_ratio" in result
            
        finally:
            os.unlink(temp_path1)
            os.unlink(temp_path2)
    
    @pytest.mark.asyncio
    async def test_compare_documents_tool_same_file(self):
        """Test document comparison tool with same file"""
        content = "This is a test document for same file comparison."
        
        with tempfile.NamedTemporaryFile(mode='w', suffix='.txt', delete=False) as f:
            f.write(content)
            temp_path = f.name
        
        try:
            tools = get_document_intelligence_tools()
            compare_tool = next(tool for tool in tools if tool.name == "compare_documents_tool")
            
            result = await compare_tool.arun({"file_path1": temp_path, "file_path2": temp_path})
            
            # Should show 100% similarity
            assert "similarity_ratio': 1.0" in result
            
        finally:
            os.unlink(temp_path)
    
    @pytest.mark.asyncio
    async def test_compare_documents_tool_error_handling(self):
        """Test document comparison tool error handling"""
        tools = get_document_intelligence_tools()
        compare_tool = next(tool for tool in tools if tool.name == "compare_documents_tool")
        
        result = await compare_tool.arun({"file_path1": "/nonexistent1.txt", "file_path2": "/nonexistent2.txt"})
        
        # Should return error message
        assert "Error comparing documents" in result
    
    def test_get_document_intelligence_tools(self):
        """Test getting document intelligence tools"""
        tools = get_document_intelligence_tools()
        
        assert len(tools) >= 2  # Should have at least analyze and compare tools
        tool_names = [tool.name for tool in tools]
        assert "analyze_document_tool" in tool_names
        assert "compare_documents_tool" in tool_names


class TestIntegration:
    """Integration tests for full workflow scenarios"""
    
    @pytest.mark.asyncio
    async def test_full_workflow_text_document(self):
        """Test complete workflow with a text document"""
        content = "This is a comprehensive integration test document. It contains structured content for testing the complete document intelligence workflow including processing, analysis, and tool integration."
        
        with tempfile.NamedTemporaryFile(mode='w', suffix='.txt', delete=False) as f:
            f.write(content)
            temp_path = f.name
        
        try:
            # Step 1: Process document directly
            processor = DocumentProcessor()
            result = await processor.process_document(temp_path)
            
            assert result['analysis']['content_type'] == 'text'
            assert result['metadata']['word_count'] > 0
            
            # Step 2: Use tool interface
            tools = get_document_intelligence_tools()
            analyze_tool = next(tool for tool in tools if tool.name == "analyze_document_tool")
            
            tool_result = await analyze_tool.arun({"file_path": temp_path})
            assert "Document analysis completed successfully" in tool_result
            
        finally:
            os.unlink(temp_path)
    
    @pytest.mark.asyncio
    async def test_error_recovery_and_logging(self):
        """Test error recovery and logging mechanisms"""
        processor = DocumentProcessor()
        
        # Test with invalid file path
        try:
            await processor.process_document("/invalid/path/file.txt")
            assert False, "Should have raised an exception"
        except JarvisToolError as e:
            assert "Failed to process document" in str(e)
    
    @pytest.mark.asyncio
    async def test_performance_with_large_content(self):
        """Test performance with larger content"""
        # Create a moderately large document
        content = "This is a performance test document. " * 100
        content += "\n".join([f"Line {i}: Additional content for testing performance and scalability." for i in range(100)])
        
        with tempfile.NamedTemporaryFile(mode='w', suffix='.txt', delete=False) as f:
            f.write(content)
            temp_path = f.name
        
        try:
            # Process the document
            tools = get_document_intelligence_tools()
            analyze_tool = next(tool for tool in tools if tool.name == "analyze_document_tool")
            
            result = await analyze_tool.arun({"file_path": temp_path})
            
            # Should complete successfully
            assert "Document analysis completed successfully" in result
            assert "Processing Time" in result
            
        finally:
            os.unlink(temp_path)


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
