import logging
import sys  # Import sys for sys.exit on fatal error

import chainlit as cl
from chainlit.cli import run_chainlit

# Import the other modules
from chainlit_setup import start, on_chat_resume
from audio_processing import on_audio_start, on_audio_chunk, on_audio_end
from message_processing import on_message
from users import *

import asyncpg
import boto3

# --- Improved logging configuration ---
log_formatter = logging.Formatter('%(asctime)s - %(name)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__) # Create a specific logger for this module
logger.setLevel(logging.INFO)

# Handler for the console
stream_handler = logging.StreamHandler()
stream_handler.setFormatter(log_formatter)
logger.addHandler(stream_handler)

# Handler for a file (optional but recommended)
try:
    file_handler = logging.FileHandler("app.log") # Log file name
    file_handler.setFormatter(log_formatter)
    logger.addHandler(file_handler)
except Exception as e:
    logger.error(f"Failed to configure file logging: {e}")


# --- Chainlit decorators are in their respective modules ---
# This file only serves as the entry point

if __name__ == "__main__":
    """
    Main entry point for the Jarvis application.
    
    This script:
    1. Configures comprehensive logging for the application
    2. Launches the Chainlit application with appropriate error handling
    3. Ensures clean exit with proper status codes on errors
    
    The actual application logic is organized in separate modules:
    - chainlit_setup.py: Handles session initialization and management
    - audio_processing.py: Processes audio input/output
    - message_processing.py: Handles text message processing
    - users.py: Manages user data and authentication
    
    Error Handling:
    - Specific handling for import errors (missing dependencies)
    - Generic exception handling for unhandled errors
    - Proper logging of all errors with stack traces
    - Appropriate exit codes for different error types
    """
    logger.info("Starting Chainlit application...")
    try:
        # Run the Chainlit application
        # Detailed exception handling should be in the functions
        # called by Chainlit (on_message, on_audio_end, etc.)
        run_chainlit(__file__)
    except ImportError as e:
        logger.critical(f"Critical import error: {e}. Make sure all dependencies are installed.")
        sys.exit(1) # Exit with an error code
    except Exception as e:
        # Catch any other unhandled exception at the top level
        logger.critical(f"An unhandled error caused the application to stop: {e}", exc_info=True)
        # exc_info=True adds the stack trace to the log entry
        sys.exit(1) # Exit with an error code
    finally:
        logger.info("Stopping Chainlit application.")