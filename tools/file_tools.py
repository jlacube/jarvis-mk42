import os
from typing import Any, Coroutine, List, Dict
from pathlib import Path

from langchain_core.tools import tool
from utils.exceptions import ValidationError, ToolError
from utils.legacy import sanitize_filename, get_safe_file_path
from utils.logging_config import get_logger, log_async_function_call
from config.settings import get_settings

logger = get_logger(__name__)

@log_async_function_call
@tool
async def list_jarvis_files() -> List[str]:
    """
    Lists all files in Jarvis directory and its subdirectories.
    
    This tool scans the base directory and returns all file paths, excluding hidden files 
    and directories (those starting with a dot).
    
    Returns:
        List[str]: A list of strings, where each string is the full path to a file.
                   Returns an empty list if the directory doesn't exist or is not a directory.
              
    Example:
        The output might look like: ["./app.py", "./tools/file_tools.py", ...]
        
    Security:
        - Only lists files within the project directory
        - Excludes hidden files and system directories
        - Filters out sensitive files like .env
    """
    try:
        settings = get_settings()
        base_directory = str(settings.project_root)
        return list_files_recursive(base_directory)
    except Exception as e:
        logger.error(f"Error listing files: {e}")
        raise ToolError(f"Failed to list files: {str(e)}")


def list_files_recursive(directory: str) -> List[str]:
    """
    Lists all files in the given directory and its subdirectories.
    
    This helper function performs the actual recursive directory traversal,
    filtering out hidden files and directories, and excludes sensitive directories.
    
    Args:
        directory (str): The path to the directory to scan.
        
    Returns:
        List[str]: A list of strings, where each string is the full path to a file.
                   Returns an empty list if the directory doesn't exist or is not a directory.
              
    Security Features:
        - Excludes hidden directories and files (starting with ".")
        - Excludes sensitive directories (.venv, .git, __pycache__, node_modules)
        - Excludes sensitive files (.env, *.key, *.pem, *.p12)
        - Limits file listing to prevent excessive resource usage
    """
    file_paths = []
    max_files = 1000  # Prevent excessive resource usage
    
    # Directories to exclude for security and performance
    excluded_dirs = {'.venv', '.git', '__pycache__', 'node_modules', '.pytest_cache', '.coverage'}
    
    # File patterns to exclude for security
    excluded_patterns = {'.env', '.key', '.pem', '.p12', '.pfx', '.crt', '.cer'}
    
    try:
        # Validate directory path
        directory_path = Path(directory).resolve()
        
        if not directory_path.exists() or not directory_path.is_dir():
            logger.warning(f"Directory '{directory}' is not valid or accessible")
            return file_paths

        for root, dirnames, filenames in os.walk(directory):
            # Filter out excluded directories
            dirnames[:] = [d for d in dirnames 
                         if not d.startswith('.') and d not in excluded_dirs]
            
            # Process files in current directory
            for filename in filenames:
                # Skip hidden files and excluded patterns
                if filename.startswith('.'):
                    continue
                
                # Skip files with excluded extensions or patterns
                if any(pattern in filename.lower() for pattern in excluded_patterns):
                    continue
                
                # Add file to list
                file_path = os.path.join(root, filename)
                file_paths.append(file_path)
                
                # Prevent excessive resource usage
                if len(file_paths) >= max_files:
                    logger.warning(f"File listing truncated at {max_files} files")
                    break
            
            if len(file_paths) >= max_files:
                break
                
    except Exception as e:
        logger.error(f"Error during recursive file listing: {e}")
        raise ToolError(f"Failed to list files recursively: {str(e)}")

    logger.info(f"Listed {len(file_paths)} files from directory: {directory}")
    return file_paths


@log_async_function_call
@tool
async def read_file_content(filepath: str) -> str:
    """
    Reads the content of a file and returns it as a string.
    
    This tool safely opens a file with UTF-8 encoding and returns its contents.
    It includes comprehensive error handling and security validation.
    
    Args:
        filepath (str): The full path to the file to read. Must be within the project directory.
    
    Returns:
        str: The content of the file as a single string.
    
    Raises:
        ValidationError: If the filepath is invalid or outside allowed directories
        ToolError: If the file cannot be read due to I/O errors
        
    Security Features:
        - Validates file path to prevent directory traversal
        - Restricts access to project directory only
        - Prevents reading of sensitive files
        - Limits file size to prevent memory exhaustion
        
    Example:
        content = await read_file_content("./prompts/supervisor.md")
    """
    try:
        # Validate and sanitize file path
        settings = get_settings()
        base_directory = str(settings.project_root)
        
        # Resolve the file path and ensure it's within the base directory
        file_path = Path(filepath).resolve()
        base_path = Path(base_directory).resolve()
        
        try:
            file_path.relative_to(base_path)
        except ValueError:
            raise ValidationError(f"File path '{filepath}' is outside allowed directory")
        
        # Check if file exists
        if not file_path.exists():
            raise ToolError(f"File not found: {filepath}")
        
        if not file_path.is_file():
            raise ToolError(f"Path is not a file: {filepath}")
        
        # Check file size to prevent memory exhaustion
        max_file_size = 10 * 1024 * 1024  # 10MB
        file_size = file_path.stat().st_size
        if file_size > max_file_size:
            raise ToolError(f"File too large ({file_size} bytes). Maximum size is {max_file_size} bytes")
        
        # Check for sensitive files
        sensitive_patterns = {'.env', '.key', '.pem', '.p12', '.pfx', '.crt', '.cer'}
        if any(pattern in file_path.name.lower() for pattern in sensitive_patterns):
            raise ValidationError(f"Access to sensitive file '{filepath}' is not allowed")
        
        # Read file content
        with open(file_path, 'r', encoding='utf-8') as file:
            content = file.read()
            
        logger.info(f"Successfully read file: {filepath} ({file_size} bytes)")
        return content
        
    except (ValidationError, ToolError):
        # Re-raise validation and tool errors
        raise
    except UnicodeDecodeError as e:
        raise ToolError(f"Cannot decode file '{filepath}': {str(e)}")
    except PermissionError:
        raise ToolError(f"Permission denied reading file: {filepath}")
    except Exception as e:
        logger.error(f"Unexpected error reading file '{filepath}': {e}")
        raise ToolError(f"Failed to read file '{filepath}': {str(e)}")


@log_async_function_call
@tool
async def write_file_tool(
    filename: str,
    content: str,
    overwrite: bool = False
) -> Dict[str, str]:
    """
    Writes the given content to a specified file in the Jarvis directory.

    Args:
        filename (str): The name (or relative path within Jarvis directory) of the file to write.
        content (str): The string content to write to the file.
        overwrite (bool, optional): If True, allows overwriting an existing file.
                                    Defaults to False, preventing overwrites.

    Returns:
        Dict[str, str]: A dictionary containing the status ('success' or 'error') and a message.
                       Example success: {"status": "success", "message": "File 'my_file.txt' written successfully."}
                       Example error: {"status": "error", "message": "File 'my_file.txt' already exists."}

    Security Features:
        - Validates filename to prevent path traversal
        - Restricts writing to project directory only
        - Prevents overwriting sensitive files
        - Limits content size to prevent storage exhaustion
    """
    try:
        # Validate inputs
        if not filename or not isinstance(filename, str):
            return {"status": "error", "message": "Filename must be a non-empty string"}
        
        if not isinstance(content, str):
            return {"status": "error", "message": "Content must be a string"}
        
        # Limit content size
        max_content_size = 1024 * 1024  # 1MB
        if len(content.encode('utf-8')) > max_content_size:
            return {"status": "error", "message": f"Content too large. Maximum size is {max_content_size} bytes"}
        
        # Get base directory and validate file path
        settings = get_settings()
        base_directory = str(settings.project_root)
        
        try:
            safe_path = get_safe_file_path(base_directory, filename)
        except ValidationError as e:
            return {"status": "error", "message": f"Invalid filename: {e.message}"}
        
        file_path = Path(safe_path)
        
        # Check for sensitive files
        sensitive_patterns = {'.env', '.key', '.pem', '.p12', '.pfx', '.crt', '.cer'}
        if any(pattern in file_path.name.lower() for pattern in sensitive_patterns):
            return {"status": "error", "message": "Cannot write to sensitive file types"}
        
        # Check if file exists and handle overwrite logic
        if file_path.exists() and not overwrite:
            return {
                "status": "error", 
                "message": f"File '{filename}' already exists. Set overwrite=True to replace it."
            }
        
        # Create parent directories if they don't exist
        file_path.parent.mkdir(parents=True, exist_ok=True)
        
        # Write the file
        with open(file_path, 'w', encoding='utf-8') as f:
            f.write(content)
        
        logger.info(f"Successfully wrote file: {filename} ({len(content)} characters)")
        return {
            "status": "success",
            "message": f"File '{filename}' written successfully."
        }
        
    except PermissionError:
        return {"status": "error", "message": f"Permission denied writing to '{filename}'"}
    except OSError as e:
        return {"status": "error", "message": f"OS error writing file '{filename}': {str(e)}"}
    except Exception as e:
        logger.error(f"Unexpected error writing file '{filename}': {e}")
        return {"status": "error", "message": f"Failed to write file '{filename}': {str(e)}"}


def get_file_tools():
    """Get all file tools for agent use."""
    return [
        list_jarvis_files,
        read_file_content,
        write_file_tool
    ]
