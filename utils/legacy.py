# utils/legacy.py
# Legacy utility functions - moved from utils.py
import datetime
import logging
from typing import Optional, Dict, Any
import traceback

from langchain_core.prompts import PromptTemplate
from prompts import get_prompt
from .exceptions import JarvisError, ConfigurationError, ValidationError
from .logging_config import get_logger

def load_prompt(prompt_name: str, **kwargs: dict) -> str:
    """Loads and formats a prompt.

    Args:
        prompt_name: The name of the prompt to load.
        **kwargs: Keyword arguments to pass to the prompt template.

    Returns:
        The formatted prompt, or a fallback prompt if an error occurred.
        
    Raises:
        ConfigurationError: If the prompt cannot be loaded and no fallback is available.
    """
    logger = get_logger(__name__)
    
    try:
        prompt_template = PromptTemplate(template=get_prompt(prompt_name), input_variables=list(kwargs.keys()))
        prompt = prompt_template.invoke(input=kwargs)
        logger.info(f"Successfully loaded prompt: {prompt_name}")
        return str(prompt)
    except Exception as e:
        logger.error(f"Error loading prompt {prompt_name}: {e}", exc_info=True)
        
        # Return fallback prompt for supervisor, raise error for others
        if prompt_name == "supervisor":
            logger.warning("Using fallback supervisor prompt")
            return "You're a very useful assistant named Jarvis. Be helpful, polite, and professional."
        else:
            raise ConfigurationError(f"Failed to load prompt '{prompt_name}': {str(e)}")


def handle_error(message: str, exception: Exception, context: Optional[Dict[str, Any]] = None) -> str:
    """Enhanced error handling with proper logging and context.

    Args:
        message: A descriptive error message.
        exception: The exception that occurred.
        context: Optional context information to include in logs.

    Returns:
        A user-friendly error message.
    """
    logger = get_logger(__name__)
    
    # Create error context
    error_context = {
        "error_type": type(exception).__name__,
        "error_message": str(exception),
        "traceback": traceback.format_exc()
    }
    
    if context:
        error_context.update(context)
    
    # Log the error with full context
    logger.error(f"{message}: {exception}", extra=error_context, exc_info=True)
    
    # Return user-friendly message based on exception type
    if isinstance(exception, JarvisError):
        # Custom Jarvis errors can have user-friendly messages
        return f"I encountered an issue: {exception.message}"
    elif isinstance(exception, ValueError):
        return f"I received invalid input: {message}. Please check your request and try again."
    elif isinstance(exception, ConnectionError):
        return "I'm having trouble connecting to external services. Please try again in a moment."
    elif isinstance(exception, TimeoutError):
        return "The operation took too long to complete. Please try again with a simpler request."
    else:
        # Generic error message for unexpected exceptions
        return f"I encountered an unexpected issue: {message}. The technical team has been notified."


def validate_user_input(input_text: str, max_length: int = 10000, min_length: int = 1) -> str:
    """Validate and sanitize user input.
    
    Args:
        input_text: The input text to validate
        max_length: Maximum allowed length
        min_length: Minimum required length
        
    Returns:
        Sanitized input text
        
    Raises:
        ValidationError: If input doesn't meet requirements
    """
    if not isinstance(input_text, str):
        raise ValidationError("Input must be a string", field="input_text", value=type(input_text))
    
    # Strip whitespace
    cleaned_input = input_text.strip()
    
    # Check length constraints
    if len(cleaned_input) < min_length:
        raise ValidationError(f"Input must be at least {min_length} characters long", 
                            field="input_text", value=len(cleaned_input))
    
    if len(cleaned_input) > max_length:
        raise ValidationError(f"Input must be no more than {max_length} characters long", 
                            field="input_text", value=len(cleaned_input))
    
    # Basic sanitization - remove null bytes and control characters
    cleaned_input = ''.join(char for char in cleaned_input if ord(char) >= 32 or char in '\n\r\t')
    
    return cleaned_input


def sanitize_filename(filename: str) -> str:
    """Sanitize a filename to prevent path traversal and other security issues.
    
    Args:
        filename: The filename to sanitize
        
    Returns:
        Sanitized filename
        
    Raises:
        ValidationError: If filename is invalid
    """
    if not filename or not isinstance(filename, str):
        raise ValidationError("Filename must be a non-empty string", field="filename", value=filename)
    
    # Remove path separators and other dangerous characters
    dangerous_chars = ['/', '\\', '..', '~', '$', '|', '&', ';', '`', '<', '>', '"', "'"]
    
    for char in dangerous_chars:
        if char in filename:
            raise ValidationError(f"Filename contains invalid character: {char}", 
                                field="filename", value=filename)
    
    # Remove leading/trailing whitespace and dots
    sanitized = filename.strip().strip('.')
    
    if not sanitized:
        raise ValidationError("Filename cannot be empty after sanitization", 
                            field="filename", value=filename)
    
    return sanitized


def get_safe_file_path(base_dir: str, filename: str) -> str:
    """Get a safe file path within the specified base directory.
    
    Args:
        base_dir: The base directory to constrain files to
        filename: The filename to create a path for
        
    Returns:
        Safe absolute file path
        
    Raises:
        ValidationError: If the path would escape the base directory
    """
    import os
    from pathlib import Path
    
    # Sanitize the filename
    safe_filename = sanitize_filename(filename)
    
    # Create the full path
    base_path = Path(base_dir).resolve()
    full_path = (base_path / safe_filename).resolve()
    
    # Ensure the path is within the base directory
    try:
        full_path.relative_to(base_path)
    except ValueError:
        raise ValidationError("File path would escape base directory", 
                            field="filename", value=filename)
    
    return str(full_path)
