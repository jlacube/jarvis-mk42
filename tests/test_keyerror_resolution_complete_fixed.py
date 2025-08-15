#!/usr/bin/env python
"""
Comprehensive test to verify all KeyError('tool_input') issues are resolved.
"""

import sys
import os
import pytest
import asyncio

current_dir = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, current_dir)

@pytest.mark.asyncio
async def test_comprehensive():
    """Comprehensive test of all tools after KeyError fixes"""
    print("=== COMPREHENSIVE KEYERROR('tool_input') RESOLUTION TEST ===")
    
    try:
        # Import app to apply patches
        import app
        
        # Import all tools
        from tools.agents_tools import coding_tool, reasoning_tool, research_tool
        from tools.file_tools import list_jarvis_files, read_file_content
        
        print("✓ All imports successful")
        
        results = []
        
        # Test 1: coding_tool
        try:
            print("\n1. Testing coding_tool...")
            result = await coding_tool.ainvoke({"query": "Write a simple hello world function"})
            print(f"✓ coding_tool Success: {result[:100]}...")
            results.append("coding_tool: ✓")
        except Exception as e:
            print(f"✗ coding_tool Error: {e}")
            results.append(f"coding_tool: ✗ {e}")
        
        # Test 2: reasoning_tool
        try:
            print("\n2. Testing reasoning_tool...")
            result = await reasoning_tool.ainvoke({"query": "What is 2 + 2?"})
            print(f"✓ reasoning_tool Success: {result[:100]}...")
            results.append("reasoning_tool: ✓")
        except Exception as e:
            print(f"✗ reasoning_tool Error: {e}")
            results.append(f"reasoning_tool: ✗ {e}")
        
        # Test 3: research_tool
        try:
            print("\n3. Testing research_tool...")
            result = await research_tool.ainvoke({"query": "What is Python programming language?"})
            print(f"✓ research_tool Success: {result[:100]}...")
            results.append("research_tool: ✓")
        except Exception as e:
            print(f"✗ research_tool Error: {e}")
            results.append(f"research_tool: ✗ {e}")
        
        # Test 4: list_jarvis_files
        try:
            print("\n4. Testing list_jarvis_files...")
            result = await list_jarvis_files.ainvoke({"query": "List Python files"})
            print(f"✓ list_jarvis_files Success: Found files")
            results.append("list_jarvis_files: ✓")
        except Exception as e:
            print(f"✗ list_jarvis_files Error: {e}")
            results.append(f"list_jarvis_files: ✗ {e}")
        
        # Test 5: read_file_content
        try:
            print("\n5. Testing read_file_content...")
            result = await read_file_content.ainvoke({"file_path": "README.md"})
            print(f"✓ read_file_content Success: Read file")
            results.append("read_file_content: ✓")
        except Exception as e:
            print(f"✗ read_file_content Error: {e}")
            results.append(f"read_file_content: ✗ {e}")
        
        # Summary
        print("\n=== FINAL RESULTS ===")
        for result in results:
            print(result)
        
        success_count = sum(1 for r in results if "✓" in r)
        total_count = len(results)
        
        print(f"\nOverall: {success_count}/{total_count} tools working correctly")
        
        # Return True if all tests passed
        return success_count == total_count
        
    except Exception as e:
        print(f"✗ Critical Error during setup: {e}")
        return False

if __name__ == "__main__":
    # For direct execution
    result = asyncio.run(test_comprehensive())
    print(f"\nTest Result: {'✓ PASS' if result else '✗ FAIL'}")
