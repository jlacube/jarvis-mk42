#!/usr/bin/env python3
"""
Test the exact coding agent creation to reproduce the Annotated error.
"""

import sys
import traceback
import os

# Set up the environment like the main app
os.chdir("c:\\Sandbox\\Git\\jarvis-mk42")
sys.path.insert(0, "c:\\Sandbox\\Git\\jarvis-mk42")

async def test_coding_agent_creation():
    """Test creating the actual coding agent to see if we get the Annotated error."""
    try:
        print("Testing actual coding agent creation...")
        
        # Set up a minimal chainlit session context
        import chainlit as cl
        
        # Mock the chainlit user session
        if not hasattr(cl, 'user_session') or cl.user_session is None:
            print("Setting up mock chainlit session...")
            # Create a mock session with required attributes
            class MockSession:
                def __init__(self):
                    self._data = {
                        "now": "2025-08-06T23:40:00",
                        "user_id": "test_user",
                        "session_id": "test_session",
                        "user_name": "test",
                        "thread_id": "test_thread"
                    }
                
                def get(self, key, default=None):
                    return self._data.get(key, default)
                
                def set(self, key, value):
                    self._data[key] = value
            
            cl.user_session = MockSession()
        
        # Now try to create the coding agent
        from agents.coding_agent import get_coding_agent
        
        print("Calling get_coding_agent()...")
        agent = await get_coding_agent()
        
        print("✓ Coding agent created successfully!")
        print(f"Agent type: {type(agent)}")
        
        return agent
    except Exception as e:
        print(f"✗ Coding agent creation error: {e}")
        if "Annotated" in str(e):
            print(f"🎯 FOUND ANNOTATED ERROR: {e}")
        traceback.print_exc()
        return None

def run_async_test():
    """Run the async test."""
    import asyncio
    return asyncio.run(test_coding_agent_creation())

if __name__ == "__main__":
    print("Testing actual coding agent creation...")
    print("=" * 60)
    
    agent = run_async_test()
    
    if agent:
        print("\n" + "=" * 60)
        print("✅ Coding agent creation successful!")
        print("The Annotated error is not in agent creation.")
    else:
        print("\n" + "=" * 60)
        print("❌ Coding agent creation failed!")
        print("Found the source of the Annotated error.")
