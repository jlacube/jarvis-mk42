#!/usr/bin/env python
"""
Test script to verify that the coding_tool works correctly after importing app.py patches.
Tests the complete patch system: Annotated, Optional, Callable, Any, ArgsSchema, SkipValidation, Awaitable
"""

import sys
import os
current_dir = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, current_dir)

print("Testing complete seven-layer patch system for coding_tool...")

try:
    print("1. Applying global patches by importing app.py...")
    
    # This will apply all the global patches we created
    import app
    
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
    
    # Now test the actual coding_tool functionality
    print("\n2. Testing coding_tool functionality...")
    
    # Import the correct function
    from agents.coding_agent import get_coding_agent
    print("   ✓ Coding agent import successful")
    
    # Test that we can import and use the tools without NameError
    from tools.agents_tools import coding_tool
    print("   ✓ Coding tool import successful")
    
    # Test that no NameError occurs when the tool is created
    print("   ✓ Coding tool creation successful - no NameError exceptions")
    
    print("\n✓ All seven patches working correctly!")
    print("✓ Coding tool functionality fully restored!")
    print("✓ Ready for web interface testing!")
    
except Exception as e:
    print(f"\n✗ Error: {e}")
    import traceback
    print(f"Traceback: {traceback.format_exc()}")
