import os
from typing import Any, Coroutine

from langchain_core.tools import tool

@tool
async def list_jarvis_files() -> list:
    """
    Lists all files in Jarvis directory and its subdirectories.
    
    This tool scans the base directory and returns all file paths, excluding hidden files 
    and directories (those starting with a dot).
    
    Returns:
        list: A list of strings, where each string is the full path to a file.
              Returns an empty list if the directory doesn't exist or is not a directory.
              
    Example:
        The output might look like: ["./app.py", "./tools/file_tools.py", ...]
    """
    return list_files_recursive(".")


def list_files_recursive(directory: str) -> list:
    """
    Lists all files in the given directory and its subdirectories.
    
    This helper function performs the actual recursive directory traversal,
    filtering out hidden files and directories, and excludes the .venv directory.
    
    Args:
        directory (str): The path to the directory to scan.
        
    Returns:
        list: A list of strings, where each string is the full path to a file.
              Returns an empty list if the directory doesn't exist or is not a directory.
              
    Note:
        Directories starting with ".\." and files starting with "." are excluded from results.
        The .venv directory is also excluded at any depth.
    """
    file_paths = []  # Initialize an empty list to store file paths
    # Check if the provided path is a valid directory
    if not os.path.isdir(directory):
        print(f"Error: '{directory}' is not a valid directory.")
        return file_paths

    for root, dirnames, filenames in os.walk(directory):
        # Exclude .venv and hidden directories at any depth
        dirnames[:] = [d for d in dirnames if not d.startswith('.') and d != '.venv']
        if root.startswith(".\\."):
            continue

        for filename in filenames:
            if filename.startswith("."):
                continue
            filepath = os.path.join(root, filename)
            file_paths.append(filepath)

    return file_paths


@tool
async def read_file_content(filepath: str) -> str | None:
    """
    Reads the content of a file and returns it as a string.
    
    This tool safely opens a file with UTF-8 encoding and returns its contents.
    It includes comprehensive error handling for common file operations issues.
    
    Args:
        filepath (str): The full path to the file to read. Can be absolute or relative 
                        to the current working directory.
    
    Returns:
        str: The content of the file as a single string.
        None: If the file cannot be found or read due to any error.
    
    Error Handling:
        - FileNotFoundError: When the specified file does not exist
        - IOError: For permission issues or other I/O related errors
        - General exceptions: For any other unexpected errors
        
    Example:
        content = await read_file_content("./prompts/supervisor.md")
    """
    try:
        # Open the file in read mode ('r') with UTF-8 encoding
        # Using 'with' ensures the file is automatically closed even if errors occur
        with open(filepath, 'r', encoding='utf-8') as file:
            # Read the entire content of the file
            content = file.read()
            return content
    except FileNotFoundError:
        # Handle the case where the file does not exist
        print(f"Error: File not found at '{filepath}'")
        return None
    except IOError:
        # Handle other potential input/output errors (e.g., permissions)
        print(f"Error: Could not read file at '{filepath}'")
        return None
    except Exception as e:
        # Handle any other unexpected errors
        print(f"An unexpected error occurred while reading '{filepath}': {e}")
        return None

import os # Assuming standard Python environment for the tool's execution

# Hypothetical base path for the Jarvis directory within the tool's execution environment.
# This might be configured differently depending on the actual deployment.
JARVIS_BASE_DIR = "." # Or adjust as needed

@tool
async def write_file_tool(
    filename: str,
    content: str,
    overwrite: bool = False
) -> dict:
    """Writes the given content to a specified file in the Jarvis directory.

    Args:
        filename (str): The name (or relative path within Jarvis directory) of the file to write.
        content (str): The string content to write to the file.
        overwrite (bool, optional): If True, allows overwriting an existing file.
                                    Defaults to False, preventing overwrites.
                                    **Railguard:** The calling agent MUST obtain user permission
                                    before setting this to True if the file exists.

    Returns:
        dict: A dictionary containing the status ('success' or 'error') and a message.
              Example success: {"status": "success", "message": "File 'my_file.txt' written successfully."}
              Example error: {"status": "error", "message": "File 'my_file.txt' already exists. Set overwrite=True to replace it."}
              Example error: {"status": "error", "message": "Error writing file: [specific OS error]"}

    Raises:
        # This tool aims to return errors in the dictionary, not raise exceptions directly to the caller.
        # Internal exceptions like IOError are caught and reported in the return dictionary.
    """
    # Ensure the filename is relative and prevent path traversal
    if ".." in filename or filename.startswith("/"):
        return {"status": "error", "message": "Invalid filename. Path traversal is not allowed."}

    # Construct the full path within the assumed Jarvis directory
    # Ensure the base directory exists (this might be handled by the environment)
    try:
        if not os.path.exists(JARVIS_BASE_DIR):
             os.makedirs(JARVIS_BASE_DIR, exist_ok=True) # Create base dir if it doesn't exist
    except OSError as e:
         return {"status": "error", "message": f"Error ensuring base directory exists: {e}"}


    full_path = os.path.join(JARVIS_BASE_DIR, filename)

    # Create subdirectories if they don't exist
    try:
        dir_name = os.path.dirname(full_path)
        if dir_name: # Only create if filename includes a path
            os.makedirs(dir_name, exist_ok=True)
    except OSError as e:
        return {"status": "error", "message": f"Error creating directories for '{filename}': {e}"}


    # Railguard Check: Check for existence if overwrite is False
    if not overwrite and os.path.exists(full_path):
        return {
            "status": "error",
            "message": f"File '{filename}' already exists at '{full_path}'. User permission is required to overwrite (call with overwrite=True)."
        }

    # Write the file
    try:
        with open(full_path, 'w', encoding='utf-8') as f:
            f.write(content)
        return {
            "status": "success",
            "message": f"File '{filename}' written successfully to '{full_path}'."
        }
    except IOError as e:
        return {
            "status": "error",
            "message": f"Error writing file '{filename}' to '{full_path}': {e}"
        }
    except Exception as e: # Catch any other unexpected errors
        return {
            "status": "error",
            "message": f"An unexpected error occurred while writing '{filename}' to '{full_path}': {e}"
        }

# Example Usage (Illustrative - how the agent would use it conceptually):
#
# 1. Agent checks if file exists using list_jarvis_files() -> finds 'existing_file.txt'
# 2. Agent asks user: "File 'existing_file.txt' already exists. Overwrite?"
# 3. User confirms: "Yes"
# 4. Agent calls: write_file_tool(filename='existing_file.txt', content='New content', overwrite=True)
#
# --- OR ---
#
# 1. Agent checks if file exists using list_jarvis_files() -> does not find 'new_file.txt'
# 2. Agent calls: write_file_tool(filename='new_file.txt', content='Initial content', overwrite=False) # overwrite=False is default
