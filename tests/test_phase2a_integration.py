"""
Phase 2A Integration Test: Enhanced Document Intelligence
Testing integration with existing Jarvis system and tool loading
"""

import pytest
import tempfile
import os

def test_document_intelligence_tools_available():
    """Test that document intelligence tools are available in the main tool registry"""
    from tools import get_all_tools
    
    tools = get_all_tools()
    tool_names = [tool.name for tool in tools]
    
    # Check that document intelligence tools are included
    assert 'analyze_document_tool' in tool_names
    assert 'compare_documents_tool' in tool_names
    
    print(f"Total tools available: {len(tools)}")
    print(f"Document intelligence tools integrated successfully!")


@pytest.mark.asyncio
async def test_document_intelligence_end_to_end():
    """Test end-to-end document processing through the tool interface"""
    from tools.document_intelligence import analyze_document_tool
    
    # Create a test document
    test_content = """
    # Phase 2A Test Document
    
    This is a comprehensive test document for validating the enhanced document intelligence capabilities 
    of Jarvis-MK42. The system now includes advanced document processing features including:
    
    ## Features Tested
    - PDF processing with OCR capabilities
    - Word document structure analysis  
    - Excel spreadsheet data extraction
    - CSV data analysis and insights
    - Image text extraction using OCR
    - Multi-document comparison and analysis
    
    ## Technical Capabilities
    The document intelligence system leverages enterprise-grade libraries including PyMuPDF, 
    python-docx, pandas, and pytesseract to provide comprehensive document analysis.
    
    ## Performance Metrics
    - File size limit: 50MB
    - Maximum pages per PDF: 500
    - Supported formats: PDF, DOCX, XLSX, CSV, TXT, JPG, PNG, TIFF
    
    This validates that Phase 2A implementation is working correctly with enhanced document processing.
    """
    
    with tempfile.NamedTemporaryFile(mode='w', suffix='.txt', delete=False) as f:
        f.write(test_content)
        temp_path = f.name
    
    try:
        # Test the tool through its interface
        result = await analyze_document_tool.ainvoke({"file_path": temp_path})
        
        # Verify the analysis results contain expected content
        assert isinstance(result, str)
        assert "Document Analysis" in result
        assert "Phase 2A Test Document" in result
        assert "Word Count" in result
        assert "TEXT" in result  # File type
        assert "Features Tested" in result or "document intelligence" in result.lower()
        
        print("✅ Phase 2A document intelligence integration successful!")
        print(f"Analysis preview: {result[:200]}...")
        
    finally:
        os.unlink(temp_path)


@pytest.mark.asyncio 
async def test_phase2a_csv_processing():
    """Test CSV processing capability specifically"""
    from tools.document_intelligence import analyze_document_tool
    
    # Create test CSV data
    csv_content = """Name,Department,Salary,Years_Experience
John Smith,Engineering,95000,5
Jane Doe,Marketing,75000,3  
Mike Johnson,Sales,82000,7
Sarah Wilson,Engineering,105000,8
David Brown,Marketing,68000,2"""
    
    with tempfile.NamedTemporaryFile(mode='w', suffix='.csv', delete=False) as f:
        f.write(csv_content)
        temp_path = f.name
    
    try:
        result = await analyze_document_tool.ainvoke({"file_path": temp_path})
        
        # Verify CSV-specific processing
        assert "CSV" in result
        assert "Name" in result  # Column name should appear
        assert "Engineering" in result or "Department" in result
        
        print("✅ Phase 2A CSV processing successful!")
        
    finally:
        os.unlink(temp_path)


def test_phase2a_requirements_installed():
    """Test that all Phase 2A dependencies are properly installed"""
    import importlib
    
    required_packages = [
        'PyPDF2',
        'fitz',  # PyMuPDF
        'docx',  # python-docx  
        'pandas',
        'PIL',   # Pillow
        'pytesseract',
        'openpyxl',
        'xlrd'
    ]
    
    installed_packages = []
    missing_packages = []
    
    for package in required_packages:
        try:
            importlib.import_module(package)
            installed_packages.append(package)
        except ImportError:
            missing_packages.append(package)
    
    print(f"✅ Installed packages: {installed_packages}")
    if missing_packages:
        print(f"❌ Missing packages: {missing_packages}")
    
    # All packages should be installed
    assert len(missing_packages) == 0, f"Missing required packages: {missing_packages}"
    assert len(installed_packages) == len(required_packages)


if __name__ == "__main__":
    # Run integration tests
    pytest.main([__file__, "-v", "--tb=short"])
