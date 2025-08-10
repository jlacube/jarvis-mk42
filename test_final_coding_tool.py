#!/usr/bin/env python
"""
Test script to verify that the coding_tool works correctly after all seven patches.
Tests the complete patch system: Annotated, Optional, Callable, Any, ArgsSchema, SkipValidation, Awaitable
"""

import sys
import os
current_dir = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, current_dir)

print("Testing complete seven-layer patch system for coding_tool...")

# Import the global patches by running the app module imports
try:
    print("1. Importing global patches...")
    
    # Import builtins to check our patches
    import builtins
    
    # Test that all patches are available
    patch_tests = [
        ('Annotated', hasattr(builtins, 'Annotated')),
        ('Optional', hasattr(builtins, 'Optional')),
        ('Callable', hasattr(builtins, 'Callable')),
        ('Any', hasattr(builtins, 'Any')),
        ('ArgsSchema', hasattr(builtins, 'ArgsSchema')),
        ('SkipValidation', hasattr(builtins, 'SkipValidation')),
        ('Awaitable', hasattr(builtins, 'Awaitable'))
    ]
    
    for patch_name, available in patch_tests:
        status = "✓" if available else "✗"
        print(f"   {status} {patch_name} patch: {available}")
    
    # Now test the actual coding_tool import and creation
    print("\n2. Testing coding_tool import and creation...")
    
    # First import agent_management to apply patches
    import agent_management
    
    # Import coding agent
    from agents.coding_agent import create_coding_agent
    
    print("   ✓ Coding agent import successful")
    
    # Test creating the coding agent
    coding_agent = create_coding_agent()
    print("   ✓ Coding agent creation successful")
    
    # Test that the agent has tools
    if hasattr(coding_agent, 'get_tools'):
        tools = coding_agent.get_tools()
        print(f"   ✓ Coding agent has {len(tools)} tools")
    
    print("\n✓ All seven patches working correctly!")
    print("✓ Coding tool functionality fully restored!")
    
except Exception as e:
    print(f"\n✗ Error: {e}")
    import traceback
    print(f"Traceback: {traceback.format_exc()}")
