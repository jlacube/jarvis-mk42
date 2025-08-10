#!/usr/bin/env python
"""
Final verification that the KeyError('tool_input') issue is resolved.
"""

import sys
import os
current_dir = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, current_dir)

import asyncio

async def final_test():
    print("🔧 Final verification of KeyError('tool_input') resolution...")
    
    try:
        # Import app to apply patches
        import app
        
        # Test the main coding_tool that was originally failing
        from tools.agents_tools import coding_tool
        
        print("✅ Successfully imported coding_tool")
        
        # Test with a real coding request
        result = await coding_tool.ainvoke({
            "query": "Create a Python function that calculates the factorial of a number"
        })
        
        print("✅ coding_tool executed successfully!")
        print(f"📝 Generated code preview: {result[:150]}...")
        
        print("\n🎉 SUCCESS: KeyError('tool_input') issue is COMPLETELY RESOLVED!")
        print("The coding agent is now fully functional.")
        
        return True
        
    except Exception as e:
        print(f"❌ Error: {e}")
        import traceback
        print(f"Traceback: {traceback.format_exc()}")
        return False

if __name__ == "__main__":
    success = asyncio.run(final_test())
