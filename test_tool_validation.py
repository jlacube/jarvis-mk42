#!/usr/bin/env python3
"""
Test loading tools that may cause ArgsSchema issues
"""

import sys
import os

# Add the project root to Python path
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

def test_tool_imports():
    """Test importing tools to check for ArgsSchema issues"""
    
    print("Testing tool imports...")
    
    try:
        # Test importing reasoning tools
        print("Importing reasoning_tools...")
        from tools.reasoning_tools import sequential_thinking_tool
        print("✅ Successfully imported sequential_thinking_tool")
        
        # Check the tool's signature
        print(f"Tool name: {sequential_thinking_tool.name}")
        print(f"Tool description: {sequential_thinking_tool.description}")
        
        # Check if it has args_schema
        if hasattr(sequential_thinking_tool, 'args_schema'):
            print(f"Tool has args_schema: {sequential_thinking_tool.args_schema}")
        else:
            print("Tool does not have args_schema attribute")
            
        return True
        
    except NameError as e:
        if "ArgsSchema" in str(e):
            print(f"❌ FAILED: ArgsSchema error: {e}")
            return False
        else:
            print(f"❌ FAILED: Other NameError: {e}")
            return False
            
    except Exception as e:
        print(f"❌ FAILED: Unexpected error: {e}")
        import traceback
        traceback.print_exc()
        return False

def test_langchain_tool_creation():
    """Test creating a LangChain tool with similar signature to sequential_thinking_tool"""
    
    print("\nTesting LangChain tool creation with Optional parameters...")
    
    try:
        from langchain_core.tools import tool
        from typing import Optional
        
        @tool
        def test_tool_with_optionals(
            thought: str,
            next_thought_needed: bool,
            thought_number: int,
            total_thoughts: int,
            is_revision: Optional[bool] = None,
            revises_thought: Optional[int] = None,
            branch_from_thought: Optional[int] = None,
            branch_id: Optional[str] = None,
            needs_more_thoughts: Optional[bool] = None
        ) -> str:
            """Test tool with similar signature to sequential_thinking_tool"""
            return f"Test successful: {thought}"
        
        print("✅ Successfully created test tool with Optional parameters")
        print(f"Tool name: {test_tool_with_optionals.name}")
        
        return True
        
    except NameError as e:
        if "ArgsSchema" in str(e):
            print(f"❌ FAILED: ArgsSchema error in tool creation: {e}")
            return False
        else:
            print(f"❌ FAILED: Other NameError in tool creation: {e}")
            return False
            
    except Exception as e:
        print(f"❌ FAILED: Unexpected error in tool creation: {e}")
        import traceback
        traceback.print_exc()
        return False

if __name__ == "__main__":
    print("=" * 60)
    print("TESTING TOOL IMPORTS AND CREATION FOR ARGSSCHEMA ISSUES")
    print("=" * 60)
    
    success1 = test_tool_imports()
    success2 = test_langchain_tool_creation()
    
    if success1 and success2:
        print("\n✅ ALL TESTS PASSED: No ArgsSchema issues detected")
    else:
        print("\n❌ SOME TESTS FAILED: ArgsSchema issues detected")
