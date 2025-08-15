#!/usr/bin/env python3
"""
Test the coding agent creation directly to see if ArgsSchema error occurs
"""

import sys
import os
import pytest

# Add the project root to Python path
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

@pytest.mark.asyncio
async def test_coding_agent_creation():
    """Test creating the coding agent to see if ArgsSchema error occurs during agent creation"""
    
    print("Testing coding agent creation...")
    
    try:
        # Import the coding agent module
        from agents.coding_agent import get_coding_agent
        
        print("✅ Successfully imported get_coding_agent")
        
        # Try to create the coding agent
        agent = await get_coding_agent()
        
        print("✅ Successfully created coding agent")
        print(f"Agent type: {type(agent)}")
        
        # Check the tools that were included
        if hasattr(agent, 'tools'):
            tool_names = [tool.name for tool in agent.tools]
            print(f"Agent tools: {tool_names}")
            
            # Check if sequential_thinking_tool was properly excluded
            if 'sequential_thinking_tool' in tool_names:
                print("⚠️  WARNING: sequential_thinking_tool is still in the agent!")
                return False
            else:
                print("✅ sequential_thinking_tool properly excluded from agent")
        
        return True
        
    except NameError as e:
        if "ArgsSchema" in str(e):
            print(f"❌ FAILED: ArgsSchema error during agent creation: {e}")
            return False
        elif "Annotated" in str(e):
            print(f"❌ FAILED: Annotated error during agent creation: {e}")
            return False
        else:
            print(f"❌ FAILED: Other NameError during agent creation: {e}")
            return False
            
    except Exception as e:
        print(f"❌ FAILED: Unexpected error during agent creation: {e}")
        import traceback
        traceback.print_exc()
        return False

if __name__ == "__main__":
    import asyncio
    
    print("=" * 60)
    print("TESTING CODING AGENT CREATION AFTER SEQUENTIAL_THINKING_TOOL REMOVAL")
    print("=" * 60)
    
    success = asyncio.run(test_coding_agent_creation())
    
    if success:
        print("\n✅ TEST PASSED: Coding agent creation works without ArgsSchema error")
    else:
        print("\n❌ TEST FAILED: Coding agent creation still has issues")
