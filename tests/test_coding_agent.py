#!/usr/bin/env python3
"""
Test script to isolate the Annotated import issue in the coding agent.
"""

import sys
import traceback

def test_imports():
    """Test basic imports that might be causing issues."""
    try:
        print("Testing basic LangChain imports...")
        from langchain_core.tools import tool
        print("✓ langchain_core.tools imported successfully")
        
        from langgraph.prebuilt import create_react_agent
        print("✓ langgraph.prebuilt.create_react_agent imported successfully")
        
        from typing import Annotated, Optional, List
        print("✓ typing.Annotated imported successfully")
        
        return True
    except Exception as e:
        print(f"✗ Import error: {e}")
        traceback.print_exc()
        return False

def test_simple_tool():
    """Test creating a simple tool."""
    try:
        print("\nTesting simple tool creation...")
        from langchain_core.tools import tool
        
        @tool
        def simple_test_tool(query: str) -> str:
            """A simple test tool."""
            return f"Test response for: {query}"
        
        print(f"✓ Simple tool created: {simple_test_tool.name}")
        return simple_test_tool
    except Exception as e:
        print(f"✗ Tool creation error: {e}")
        traceback.print_exc()
        return None

def test_agent_creation():
    """Test creating a minimal agent."""
    try:
        print("\nTesting agent creation...")
        from langgraph.prebuilt import create_react_agent
        from models.models import get_google_reasoning_model
        
        # Get the model
        model = get_google_reasoning_model(streaming=False)
        print("✓ Model obtained successfully")
        
        # Create simple tool
        simple_tool = test_simple_tool()
        if not simple_tool:
            return False
        
        # Try to create agent
        print("Creating agent with simple tool...")
        agent = create_react_agent(
            name="Test_Agent",
            model=model,
            tools=[simple_tool],
            prompt="You are a helpful assistant."
        )
        print("✓ Agent created successfully")
        return agent
    except Exception as e:
        print(f"✗ Agent creation error: {e}")
        traceback.print_exc()
        return None

def test_complex_tool():
    """Test creating a tool with Optional parameters like the ones in reasoning_tools."""
    try:
        print("\nTesting complex tool creation...")
        from langchain_core.tools import tool
        from typing import Optional
        
        @tool
        def complex_test_tool(
            query: str, 
            optional_param: Optional[str] = None,
            optional_int: Optional[int] = None
        ) -> str:
            """A complex test tool with optional parameters."""
            return f"Complex test response for: {query}, {optional_param}, {optional_int}"
        
        print(f"✓ Complex tool created: {complex_test_tool.name}")
        return complex_test_tool
    except Exception as e:
        print(f"✗ Complex tool creation error: {e}")
        traceback.print_exc()
        return None

def test_agent_with_complex_tool():
    """Test creating an agent with a complex tool."""
    try:
        print("\nTesting agent creation with complex tool...")
        from langgraph.prebuilt import create_react_agent
        from models.models import get_google_reasoning_model
        
        # Get the model
        model = get_google_reasoning_model(streaming=False)
        
        # Create complex tool
        complex_tool = test_complex_tool()
        if not complex_tool:
            return False
        
        # Try to create agent
        print("Creating agent with complex tool...")
        agent = create_react_agent(
            name="Test_Complex_Agent",
            model=model,
            tools=[complex_tool],
            prompt="You are a helpful assistant."
        )
        print("✓ Agent with complex tool created successfully")
        return agent
    except Exception as e:
        print(f"✗ Agent with complex tool creation error: {e}")
        traceback.print_exc()
        return None

if __name__ == "__main__":
    print("Starting coding agent test...")
    print("=" * 50)
    
    # Test 1: Basic imports
    if not test_imports():
        print("❌ Basic imports failed")
        sys.exit(1)
    
    # Test 2: Simple tool
    simple_tool = test_simple_tool()
    if not simple_tool:
        print("❌ Simple tool creation failed")
        sys.exit(1)
    
    # Test 3: Simple agent
    simple_agent = test_agent_creation()
    if not simple_agent:
        print("❌ Simple agent creation failed")
        sys.exit(1)
    
    # Test 4: Complex tool
    complex_tool = test_complex_tool()
    if not complex_tool:
        print("❌ Complex tool creation failed")
        sys.exit(1)
    
    # Test 5: Agent with complex tool
    complex_agent = test_agent_with_complex_tool()
    if not complex_agent:
        print("❌ Agent with complex tool creation failed")
        sys.exit(1)
    
    print("\n" + "=" * 50)
    print("✅ All tests passed! The issue might be elsewhere.")
    print("✅ LangChain/LangGraph and typing imports are working correctly.")
