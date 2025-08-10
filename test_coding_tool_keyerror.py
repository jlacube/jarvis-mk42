#!/usr/bin/env python
"""
Test script to isolate the KeyError('tool_input') issue in coding_tool.
"""

import sys
import os
current_dir = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, current_dir)

print("Testing coding_tool for KeyError('tool_input') issue...")

try:
    # Import app to apply patches
    import app
    
    # Import the tools
    from tools.agents_tools import coding_tool, reasoning_tool, research_tool
    
    print("✓ Imports successful")
    
    # Test multiple tools with simple queries
    import asyncio
    
    async def test_all_tools():
        try:
            print("Testing reasoning_tool with simple query...")
            result = await reasoning_tool.ainvoke({"query": "What is 2+2?"})
            print(f"✓ reasoning_tool Success: {result[:50]}...")
        except Exception as e:
            print(f"✗ reasoning_tool Error: {e}")
        
        try:
            print("Testing research_tool with simple query...")
            result = await research_tool.ainvoke({"query": "What is Python?"})
            print(f"✓ research_tool Success: {result[:50]}...")
        except Exception as e:
            print(f"✗ research_tool Error: {e}")
        
        try:
            print("Testing coding_tool with simple query...")
            result = await coding_tool.ainvoke({"query": "Write a simple hello world function"})
            print(f"✓ coding_tool Success: {result[:50]}...")
            return True
        except Exception as e:
            print(f"✗ coding_tool Error: {e}")
            import traceback
            print(f"Traceback: {traceback.format_exc()}")
            return False
    
    # Run the test
    success = asyncio.run(test_all_tools())
    
    if success:
        print("\n✓ coding_tool working correctly!")
    else:
        print("\n✗ coding_tool has issues!")
    
except Exception as e:
    print(f"\n✗ Error during setup: {e}")
    import traceback
    print(f"Traceback: {traceback.format_exc()}")
