#!/usr/bin/env python3
"""
Test runner for the Jarvis-MK42 tools.

This script runs tests for individual tools without requiring the full agent framework.
It allows developers to verify that each tool is working correctly in isolation.

Usage:
    python run_tool_tests.py                # Run all tests
    python run_tool_tests.py file           # Run file tool tests only
    python run_tool_tests.py math research  # Run math and research tool tests
"""

import sys
import pytest
import os
from dotenv import load_dotenv

# Load environment variables
load_dotenv()

def main():
    """Run the tests based on command line arguments."""
    # Available test categories
    test_categories = {
        "file": "test_file_tools.py",
        "math": "test_math_tools.py",
        "research": "test_research_tools.py",
        "reasoning": "test_reasoning_tools.py",
        "plotting": "test_plotting.py",
        "agents": "test_agents_tools.py",
        "multimodal": "test_multimodal_tools.py",
    }
    
    # Get the directory of this script
    script_dir = os.path.dirname(os.path.abspath(__file__))
    tests_dir = os.path.join(script_dir, "tests")
    
    # Default arguments for pytest
    pytest_args = ["-v", tests_dir]
    
    # If specific categories are provided, only run those tests
    if len(sys.argv) > 1:
        selected_tests = []
        
        for category in sys.argv[1:]:
            if category.lower() in test_categories:
                selected_tests.append(os.path.join(tests_dir, test_categories[category.lower()]))
            else:
                print(f"Warning: Unknown test category '{category}'")
                print(f"Available categories: {', '.join(test_categories.keys())}")
        
        if selected_tests:
            # Replace the default argument with specific test files
            pytest_args = ["-v"] + selected_tests
      # Print which tests will be run
    print(f"Running tests: {' '.join(pytest_args[1:])}")
    
    # Run the tests with -xvs flags for better error reporting
    return pytest.main(["-xvs"] + pytest_args[1:])

if __name__ == "__main__":
    sys.exit(main())
