#!/usr/bin/env python3
"""
Debug the None function issue in tools.
"""

import sys
import traceback
import os

# Set up the environment like the main app
os.chdir("c:\\Sandbox\\Git\\jarvis-mk42")
sys.path.insert(0, "c:\\Sandbox\\Git\\jarvis-mk42")

def debug_tools():
    """Debug which tool has the None function issue."""
    try:
        print("Debugging tools to find None function...")
        
        # Import the tools
        from tools.file_tools import list_jarvis_files, read_file_content
        from tools.reasoning_model_tool import reasoning_model_tool
        from tools.reasoning_tools import sequential_thinking_tool, generate_summary, clear_history
        from tools.research_tools import get_research_tools
        
        # Test individual tools first
        individual_tools = [
            ("list_jarvis_files", list_jarvis_files),
            ("read_file_content", read_file_content),
            ("reasoning_model_tool", reasoning_model_tool),
            ("sequential_thinking_tool", sequential_thinking_tool),
            ("generate_summary", generate_summary),
            ("clear_history", clear_history)
        ]
        
        print("\nChecking individual tools:")
        for name, tool in individual_tools:
            print(f"  - {name}:")
            print(f"    Tool object: {tool}")
            print(f"    Tool type: {type(tool)}")
            if hasattr(tool, 'func'):
                print(f"    Tool.func: {tool.func}")
                print(f"    Tool.func type: {type(tool.func)}")
            if hasattr(tool, 'name'):
                print(f"    Tool.name: {tool.name}")
            print()
        
        # Test research tools
        print("Checking research tools:")
        research_tools = get_research_tools()
        for i, tool in enumerate(research_tools):
            print(f"  - Research tool {i}:")
            print(f"    Tool object: {tool}")
            print(f"    Tool type: {type(tool)}")
            if hasattr(tool, 'func'):
                print(f"    Tool.func: {tool.func}")
                print(f"    Tool.func type: {type(tool.func)}")
            if hasattr(tool, 'name'):
                print(f"    Tool.name: {tool.name}")
            print()
        
        return True
    except Exception as e:
        print(f"✗ Debug error: {e}")
        traceback.print_exc()
        return False

if __name__ == "__main__":
    print("Starting tool debugging...")
    print("=" * 60)
    
    debug_tools()
