#!/usr/bin/env python3
"""
Direct test of coding_tool functionality after removing sequential_thinking_tool
"""

import sys
import os

# Add the project root to Python path
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

# Import necessary modules
from tools.agents_tools import coding_tool

async def test_coding_tool():
    """Test the coding_tool directly to check for ArgsSchema errors"""
    
    print("Testing coding_tool directly...")
    
    try:
        # Test with a simple coding request using proper invoke method
        result = await coding_tool.ainvoke({"query": "Write a simple hello world function in Python"})
        print(f"SUCCESS: coding_tool executed successfully")
        print(f"Result: {result}")
        return True
        
    except NameError as e:
        if "ArgsSchema" in str(e):
            print(f"FAILED: ArgsSchema error still present: {e}")
            return False
        elif "Annotated" in str(e):
            print(f"FAILED: Annotated error still present: {e}")
            return False
        else:
            print(f"FAILED: Other NameError: {e}")
            return False
            
    except Exception as e:
        print(f"FAILED: Unexpected error: {e}")
        return False

if __name__ == "__main__":
    import asyncio
    
    print("=" * 60)
    print("TESTING CODING_TOOL AFTER SEQUENTIAL_THINKING_TOOL REMOVAL")
    print("=" * 60)
    
    try:
        success = asyncio.run(test_coding_tool())
        
        if success:
            print("\n✅ TEST PASSED: coding_tool works without ArgsSchema error")
        else:
            print("\n❌ TEST FAILED: coding_tool still has issues")
            
    except Exception as e:
        print(f"\n❌ TEST FAILED with exception: {e}")
        import traceback
        traceback.print_exc()
