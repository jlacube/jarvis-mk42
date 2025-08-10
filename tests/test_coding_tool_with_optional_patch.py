#!/usr/bin/env python3
"""
Test script to verify coding_tool functionality works with Optional patch
"""

import asyncio
import sys
import os

# Add the project root directory to the Python path
current_dir = os.path.dirname(os.path.abspath(__file__))
project_root = os.path.dirname(current_dir)
if project_root not in sys.path:
    sys.path.insert(0, project_root)

# Import the coding_tool directly
from tools.agents_tools import coding_tool

async def test_coding_tool():
    """Test the coding_tool with Optional patch in place"""
    print("Testing coding_tool with Optional patch...")
    
    try:
        # Test a simple coding request using the proper async method
        result = await coding_tool.ainvoke({"query": "Write a Python function to calculate fibonacci numbers using an iterative approach"})
        print("✓ Coding tool executed successfully!")
        print("Result preview:", str(result)[:200] + "..." if len(str(result)) > 200 else str(result))
        return True
        
    except Exception as e:
        print(f"✗ Coding tool failed with error: {e}")
        import traceback
        traceback.print_exc()
        return False

if __name__ == "__main__":
    print("Testing coding_tool functionality with Optional patch...")
    success = asyncio.run(test_coding_tool())
    
    if success:
        print("\n🎉 SUCCESS: coding_tool is working correctly with Optional patch!")
        sys.exit(0)
    else:
        print("\n❌ FAILURE: coding_tool still has issues")
        sys.exit(1)
