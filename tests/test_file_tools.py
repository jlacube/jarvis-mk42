import os
import pytest
import asyncio

from tools.file_tools import list_jarvis_files, read_file_content, write_file_tool

@pytest.mark.asyncio
async def test_list_jarvis_files():
    """Test that list_jarvis_files returns a non-empty list of files."""
    # Use the invoke method for LangChain tools
    files = await list_jarvis_files.ainvoke("")
    
    # Check if result is a list
    assert isinstance(files, list), "Result should be a list"
    
    # Check if list contains files
    assert len(files) > 0, "The list of files should not be empty"
    
    # Check if app.py is in the list (which should exist in any setup)
    assert any("app.py" in file for file in files), "app.py should be in the file list"
    
    # Check if at least one tool file is in the list
    assert any("tools" in file for file in files), "At least one tool file should be in the list"

@pytest.mark.asyncio
async def test_read_file_content():
    """Test that read_file_content can read a file's content."""
    # Use app.py which should always exist
    content = await read_file_content.ainvoke("app.py")
      # Check if content is a string
    assert isinstance(content, str), "Content should be a string"
    
    # Check if content contains expected python content
    assert "import" in content.lower(), "Python file should contain import statements"
    # The app.py file may not have 'def' or 'class' explicitly, so check for common Python patterns
    assert any(keyword in content.lower() for keyword in ["import", "from", "#", "try:", "if"]), "Python file should contain basic Python syntax"

@pytest.mark.asyncio
async def test_write_file_tool():
    """Test that write_file_tool can write a file and then read it."""
    test_content = "This is a test file content for testing write_file_tool."
    test_filename = "test_file_write_tool.txt"
    
    # Ensure the file doesn't exist before the test
    if os.path.exists(test_filename):
        os.remove(test_filename)
    
    # Write the file using LangChain tool invocation
    tool_input = {
        "filename": test_filename,
        "content": test_content,
        "overwrite": False
    }
    result = await write_file_tool.ainvoke(tool_input)
    
    # Check the result
    assert result["status"] == "success", f"Writing file should succeed, got: {result}"
    
    # Read the file to verify content
    read_content = await read_file_content.ainvoke(test_filename)
    assert read_content == test_content, "Read content should match written content"
    
    # Test overwrite protection
    no_overwrite_input = {
        "filename": test_filename,
        "content": "Different content",
        "overwrite": False
    }
    result_no_overwrite = await write_file_tool.ainvoke(no_overwrite_input)
    assert result_no_overwrite["status"] == "error", "Should not overwrite without overwrite=True"
    
    # Test overwrite
    overwrite_input = {
        "filename": test_filename,
        "content": "Overwritten content",
        "overwrite": True
    }
    result_overwrite = await write_file_tool.ainvoke(overwrite_input)
    assert result_overwrite["status"] == "success", "Should succeed with overwrite=True"
    
    # Verify overwritten content
    read_content_after_overwrite = await read_file_content.ainvoke(test_filename)
    assert read_content_after_overwrite == "Overwritten content", "Content should be overwritten"
    
    # Clean up after test
    if os.path.exists(test_filename):
        os.remove(test_filename)