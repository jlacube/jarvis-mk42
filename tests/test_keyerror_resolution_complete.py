#!/usr/bin/env python
"""
Comprehensive test to verify all KeyError('tool_input') issues are resolved.
"""

import sys
import os
current_dir = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, current_dir)

print("=== COMPREHENSIVE KEYERROR('tool_input') RESOLUTION TEST ===")

try:
    # Import app to apply patches
    import app
    
    # Import all tools
    from tools.agents_tools import coding_tool, reasoning_tool, research_tool
    from tools.file_tools import list_jarvis_files, read_file_content
    
    print("✓ All imports successful")
    
    # Test the tools
    import asyncio
    
    async def test_comprehensive():
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
            result = await reasoning_tool.ainvoke({"query": "What is 5+3?"})
            print(f"✓ reasoning_tool Success: {result[:100]}...")
            results.append("reasoning_tool: ✓")
        except Exception as e:
            print(f"✗ reasoning_tool Error: {e}")
            results.append(f"reasoning_tool: ✗ {e}")
        
        # Test 3: list_jarvis_files (the original problem tool)
        try:
            print("\n3. Testing list_jarvis_files directly...")
            result = await list_jarvis_files.ainvoke({"pattern": "*.py"})
            print(f"✓ list_jarvis_files Success: Found {len(result)} Python files")
            results.append("list_jarvis_files: ✓")
        except Exception as e:
            print(f"✗ list_jarvis_files Error: {e}")
            results.append(f"list_jarvis_files: ✗ {e}")
        
        # Test 4: read_file_content
        try:
            print("\n4. Testing read_file_content...")
            result = await read_file_content.ainvoke({"filepath": "README.md"})
            print(f"✓ read_file_content Success: Read {len(result)} characters")
            results.append("read_file_content: ✓")
        except Exception as e:
            print(f"✗ read_file_content Error: {e}")
            results.append(f"read_file_content: ✗ {e}")
        
        print("\n=== FINAL RESULTS ===")
        for result in results:
            print(result)
        
        success_count = sum(1 for r in results if "✓" in r)
        total_count = len(results)
        
        if success_count == total_count:
            print(f"\n🎉 ALL TESTS PASSED! {success_count}/{total_count} tools working correctly")
            print("KeyError('tool_input') issue is COMPLETELY RESOLVED!")
            return True
        else:
            print(f"\n⚠️  Some issues remain: {success_count}/{total_count} tools working")
            return False
    
    # Run the comprehensive test
    success = asyncio.run(test_comprehensive())
    
except Exception as e:
    print(f"\n✗ Error during setup: {e}")
    import traceback
    print(f"Traceback: {traceback.format_exc()}")
    success = False

print("\n=== TEST COMPLETE ===")
