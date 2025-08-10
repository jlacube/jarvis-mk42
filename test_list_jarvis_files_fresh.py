#!/usr/bin/env python
"""
Fresh test to check if list_jarvis_files KeyError is resolved.
"""

import sys
import os
current_dir = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, current_dir)

print("Testing fresh import of list_jarvis_files...")

try:
    # Import app to apply patches
    import app
    
    # Import the tool directly
    from tools.file_tools import list_jarvis_files
    
    print("✓ Direct import successful")
    print(f"Function name: {list_jarvis_files.name}")
    print(f"Tool description: {list_jarvis_files.description[:100]}...")
    print(f"Tool type: {type(list_jarvis_files)}")
    
    # Check if it's actually a tool or just a function
    from langchain_core.tools import BaseTool
    if isinstance(list_jarvis_files, BaseTool):
        print("✓ It's a proper LangChain tool")
    else:
        print("✗ It's not a LangChain tool, it's a function")
        
    # Also check the function signature at the raw level
    import inspect
    sig = inspect.signature(list_jarvis_files.__wrapped__ if hasattr(list_jarvis_files, '__wrapped__') else list_jarvis_files)
    print(f"Function signature: {sig}")
    print(f"Function parameters: {list(sig.parameters.keys())}")
    
    # Test the tool invocation
    import asyncio
    
    async def test_tool():
        try:
            print("Testing list_jarvis_files with .ainvoke...")
            result = await list_jarvis_files.ainvoke({})
            print(f"✓ Success: {len(result) if result else 0} files found")
            return True
        except Exception as e:
            print(f"✗ Error: {e}")
            import traceback
            print(f"Traceback: {traceback.format_exc()}")
            return False
    
    # Run the test
    success = asyncio.run(test_tool())
    
    if success:
        print("\n✓ list_jarvis_files working correctly!")
    else:
        print("\n✗ list_jarvis_files has issues!")
    
except Exception as e:
    print(f"\n✗ Error during setup: {e}")
    import traceback
    print(f"Traceback: {traceback.format_exc()}")
