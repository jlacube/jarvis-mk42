import os
from typing import Any, Coroutine

from langchain_core.tools import tool

@tool
async def list_jarvis_files() -> list:
    """
    Lists all files in Jarvis directory and its subdirectories.

    Returns:
    list: A list of strings, where each string is the full path to a file.
          Returns an empty list if the directory doesn't exist or is not a directory.
    """
    return list_files_recursive(".")


def list_files_recursive(directory:str ) -> list:
    """
    Lists all files in the given directory and its subdirectories.

    Args:
    directory (str): The path to the directory to scan.

    Returns:
    list: A list of strings, where each string is the full path to a file.
          Returns an empty list if the directory doesn't exist or is not a directory.
    """
    file_paths = []  # Initialize an empty list to store file paths
    # Check if the provided path is a valid directory
    if not os.path.isdir(directory):
        print(f"Error: '{directory}' is not a valid directory.")
        return file_paths

    # os.walk generates the file names in a directory tree
    # by walking the tree either top-down or bottom-up.
    for root, _, filenames in os.walk(directory):
        if root.startswith(".\\."): # and root != ".":
            continue

        for filename in filenames:
            if filename.startswith("."):
                continue

            # Construct the full file path by joining the root directory and filename
            filepath = os.path.join(root, filename)
            file_paths.append(filepath) # Add the full file path to the list

    return file_paths


@tool
async def read_file_content(filepath: str) -> str | None:
    """
    Reads the content of a file and returns it as a string.

    Args:
    filepath (str): The full path to the file to read.

    Returns:
    str: The content of the file as a single string.
         Returns None if the file cannot be found or read.
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
