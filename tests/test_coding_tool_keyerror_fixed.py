#!/usr/bin/env python
"""
Test script to isolate the KeyError('tool_input') issue in coding_tool.
"""

import sys
import os
import pytest
import asyncio

current_dir = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, current_dir)

@pytest.mark.asyncio
async def test_all_tools():
    """Test multiple tools with simple queries"""
    try:
        # Import app to apply patches
        import app
        
        # Import the tools
        from tools.agents_tools import coding_tool, reasoning_tool, research_tool
        
        print("✓ Imports successful")
        
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
            result = await coding_tool.ainvoke({"query": "Write a hello world function"})
            print(f"✓ coding_tool Success: {result[:50]}...")
        except Exception as e:
            print(f"✗ coding_tool Error: {e}")
        
        return True
        
    except Exception as e:
        print(f"✗ Import Error: {e}")
        return False

if __name__ == "__main__":
    # For direct execution
    print("Testing coding_tool for KeyError('tool_input') issue...")
    result = asyncio.run(test_all_tools())
    print(f"Test result: {result}")
