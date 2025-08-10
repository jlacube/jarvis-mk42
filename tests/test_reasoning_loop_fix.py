#!/usr/bin/env python3
"""
Test script to verify the reasoning tool infinite loop fix
"""

import asyncio
import sys
import os

# Add the project root to Python path
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

async def test_reasoning_tools():
    """Test that reasoning tools work without infinite loops"""
    print("Testing reasoning tools for infinite loop fix...")
    
    try:
        # Import the reasoning tools
        from tools.agents_tools import reasoning_tool
        from tools.reasoning_model_tool import reasoning_model_tool
        
        print("✅ Successfully imported reasoning tools")
        
        # Test 1: Test reasoning_model_tool directly with a simple query
        print("\n🧪 Test 1: Testing reasoning_model_tool directly...")
        try:
            result = await reasoning_model_tool.ainvoke({"query": "What are the key steps to start a business?"})
            print(f"✅ reasoning_model_tool completed successfully")
            print(f"Result length: {len(result)} characters")
            
            # Check if we got an error response
            if "Error:" in result and "circular call" in result.lower():
                print("❌ DETECTED CIRCULAR CALL ERROR!")
                return False
            elif "Error:" in result:
                print(f"⚠️  Got error but not circular call: {result[:200]}...")
            else:
                print("✅ No circular call error detected")
                
        except Exception as e:
            print(f"❌ Error in reasoning_model_tool: {e}")
            return False
        
        # Test 2: Test reasoning_tool (which should be able to use reasoning_model_tool)
        print("\n🧪 Test 2: Testing reasoning_tool...")
        try:
            result = await reasoning_tool.ainvoke({"query": "Break down the steps to launch a software startup"})
            print(f"✅ reasoning_tool completed successfully")
            print(f"Result length: {len(result)} characters")
            
            # Check if we got an error response
            if "Error:" in result and "circular call" in result.lower():
                print("❌ DETECTED CIRCULAR CALL ERROR!")
                return False
            else:
                print("✅ No circular call error detected")
                
        except Exception as e:
            print(f"❌ Error in reasoning_tool: {e}")
            return False
        
        print("\n🎉 All tests passed! Infinite loop issue appears to be fixed.")
        return True
        
    except ImportError as e:
        print(f"❌ Import error: {e}")
        return False
    except Exception as e:
        print(f"❌ Unexpected error: {e}")
        return False

async def main():
    """Main test function"""
    print("=" * 60)
    print("REASONING TOOLS INFINITE LOOP FIX VERIFICATION")
    print("=" * 60)
    
    success = await test_reasoning_tools()
    
    print("\n" + "=" * 60)
    if success:
        print("✅ TESTS PASSED - Infinite loop issue appears to be fixed!")
        exit_code = 0
    else:
        print("❌ TESTS FAILED - Issues still exist")
        exit_code = 1
    print("=" * 60)
    
    return exit_code

if __name__ == "__main__":
    try:
        exit_code = asyncio.run(main())
        sys.exit(exit_code)
    except KeyboardInterrupt:
        print("\n❌ Test interrupted by user")
        sys.exit(1)
    except Exception as e:
        print(f"\n❌ Unexpected error during testing: {e}")
        sys.exit(1)
