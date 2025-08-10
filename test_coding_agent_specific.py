#!/usr/bin/env python3
"""
Test script to specifically test the tools used by the coding agent.
"""

import sys
import traceback
import os

# Set up the environment like the main app
os.chdir("c:\\Sandbox\\Git\\jarvis-mk42")
sys.path.insert(0, "c:\\Sandbox\\Git\\jarvis-mk42")

def test_coding_agent_imports():
    """Test the specific imports that the coding agent uses."""
    try:
        print("Testing coding agent specific imports...")
        
        # Test the specific tools imported by coding agent
        from tools.file_tools import list_jarvis_files, read_file_content
        print("✓ file_tools imported successfully")
        
        from tools.reasoning_model_tool import reasoning_model_tool
        print("✓ reasoning_model_tool imported successfully")
        
        from tools.reasoning_tools import sequential_thinking_tool, generate_summary, clear_history
        print("✓ reasoning_tools imported successfully")
        
        from tools.research_tools import get_research_tools
        print("✓ research_tools.get_research_tools imported successfully")
        
        return True
    except Exception as e:
        print(f"✗ Coding agent import error: {e}")
        traceback.print_exc()
        return False

def test_tool_creation():
    """Test creating the specific tools used by coding agent."""
    try:
        print("\nTesting coding agent tool creation...")
        
        # Import the tools
        from tools.file_tools import list_jarvis_files, read_file_content
        from tools.reasoning_model_tool import reasoning_model_tool
        from tools.reasoning_tools import sequential_thinking_tool, generate_summary, clear_history
        from tools.research_tools import get_research_tools
        
        # Test that the tools are properly decorated
        tools = [list_jarvis_files, read_file_content, sequential_thinking_tool, generate_summary, clear_history, reasoning_model_tool]
        
        for tool in tools:
            print(f"✓ Tool {tool.name} created successfully")
        
        # Test get_research_tools function
        research_tools = get_research_tools()
        print(f"✓ Research tools obtained: {len(research_tools)} tools")
        
        return tools + research_tools
    except Exception as e:
        print(f"✗ Tool creation error: {e}")
        traceback.print_exc()
        return None

def test_agent_creation_with_real_tools():
    """Test creating an agent with the actual tools used by coding agent."""
    try:
        print("\nTesting agent creation with real coding agent tools...")
        
        # Import what we need but skip the model for now
        from langgraph.prebuilt import create_react_agent
        
        # Get the tools
        tools = test_tool_creation()
        if not tools:
            return False
        
        # Just test the tool filtering logic (like in coding agent)
        allowed_tools = ["list_jarvis_files", "read_file_content", "sequential_thinking_tool", 
                        "generate_summary", "clear_history", "reasoning_model_tool"]
        
        # Filter tools like the coding agent does
        filtered_tools = [tool for tool in tools if tool.name in allowed_tools]
        print(f"✓ Filtered tools: {[tool.name for tool in filtered_tools]}")
        
        # Test if we can at least get the function signatures
        for tool in filtered_tools:
            print(f"  - {tool.name}: {tool.description[:50]}...")
        
        print("✓ Tool filtering and inspection successful")
        return True
    except Exception as e:
        print(f"✗ Agent tool testing error: {e}")
        traceback.print_exc()
        return False

def test_pydantic_validation():
    """Test if there's a Pydantic validation issue with the tools."""
    try:
        print("\nTesting Pydantic validation of tool schemas...")
        
        # Import Pydantic to test schema creation
        from pydantic import BaseModel, create_model
        from typing import Optional, get_type_hints
        import inspect
        
        # Get the tools
        tools = test_tool_creation()
        if not tools:
            return False
        
        # Test schema creation for each tool
        for tool in tools:
            if hasattr(tool, 'func'):
                func = tool.func
                sig = inspect.signature(func)
                type_hints = get_type_hints(func)
                
                print(f"  - Testing {tool.name}:")
                print(f"    Signature: {sig}")
                print(f"    Type hints: {type_hints}")
                
                # Test if we can create a Pydantic model from this
                fields = {}
                for param_name, param in sig.parameters.items():
                    if param_name in type_hints:
                        param_type = type_hints[param_name]
                        default = param.default if param.default != inspect.Parameter.empty else ...
                        fields[param_name] = (param_type, default)
                
                if fields:
                    try:
                        test_model = create_model(f"{tool.name}_model", **fields)
                        print(f"    ✓ Pydantic model created successfully")
                    except Exception as model_error:
                        print(f"    ✗ Pydantic model creation failed: {model_error}")
                        if "Annotated" in str(model_error):
                            print(f"    🎯 FOUND ANNOTATED ERROR: {model_error}")
                            return False
        
        print("✓ All Pydantic validations passed")
        return True
    except Exception as e:
        print(f"✗ Pydantic validation error: {e}")
        if "Annotated" in str(e):
            print(f"🎯 FOUND ANNOTATED ERROR: {e}")
        traceback.print_exc()
        return False

if __name__ == "__main__":
    print("Starting coding agent specific test...")
    print("=" * 60)
    
    # Test 1: Coding agent imports
    if not test_coding_agent_imports():
        print("❌ Coding agent imports failed")
        sys.exit(1)
    
    # Test 2: Tool creation
    tools = test_tool_creation()
    if not tools:
        print("❌ Tool creation failed")
        sys.exit(1)
    
    # Test 3: Agent tool processing
    if not test_agent_creation_with_real_tools():
        print("❌ Agent tool processing failed")
        sys.exit(1)
    
    # Test 4: Pydantic validation
    if not test_pydantic_validation():
        print("❌ Pydantic validation failed")
        sys.exit(1)
    
    print("\n" + "=" * 60)
    print("✅ All coding agent specific tests passed!")
    print("The Annotated issue might be in the actual agent execution or model interaction.")
