#!/usr/bin/env python3
"""
Test script for geometry_tool to verify it works correctly.
"""
import asyncio
import sys
import os
import pytest

# Add the current directory to Python path
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from tools.geometry_tool import geometry_tool

@pytest.mark.asyncio
async def test_geometry_tool():
    """Test the geometry_tool with various inputs."""
    
    test_cases = [
        "a circle with center at (2,3) and radius 5",
        "a line from (0,0) to (5,5)",
        "a point at (10,20)",
        "a square with corners at (0,0), (1,0), (1,1), (0,1)"
    ]
    
    print("Testing geometry_tool...")
    print("=" * 50)
    
    for i, test_case in enumerate(test_cases, 1):
        print(f"\nTest {i}: {test_case}")
        print("-" * 30)
        
        try:
            result = await geometry_tool(test_case)
            print(f"Result: {result}")
        except Exception as e:
            print(f"Error: {e}")
            import traceback
            traceback.print_exc()
        
        print("-" * 30)

if __name__ == "__main__":
    asyncio.run(test_geometry_tool())
