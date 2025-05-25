import os
import sys
import pytest
import asyncio
import logging
from dotenv import load_dotenv

# Add the parent directory to sys.path to import modules correctly
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

# Load environment variables
load_dotenv()

# Configure logging for tests
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[logging.StreamHandler()]
)

# Configure pytest-asyncio to set explicit fixture loop scope
def pytest_configure(config):
    """Set asyncio_default_fixture_loop_scope explicitly to avoid deprecation warnings."""
    config.option.asyncio_default_fixture_loop_scope = "function"
