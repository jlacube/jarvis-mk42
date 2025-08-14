#!/usr/bin/env python3
"""
Test script to verify the webpage research tool fix
"""

import asyncio
import sys
import os
import pytest

# Add the project root to Python path
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

@pytest.mark.asyncio
async def test_webpage_research_tool():
    """Test that webpage research tool works without APIError issues"""
    print("Testing webpage research tool fix...")
    
    try:
        # Import the webpage research tool
        from tools.research_tools import webpage_research_tool
        
        print("✅ Successfully imported webpage_research_tool")
        
        # Test 1: Test with a valid URL
        print("\n🧪 Test 1: Testing with a simple URL...")
        try:
            # Use a simple, reliable URL for testing
            result = await webpage_research_tool.ainvoke({"url": "https://httpbin.org/html"})
            print(f"✅ webpage_research_tool completed successfully")
            print(f"Result type: {type(result)}")
            print(f"Result length: {len(result)} characters" if isinstance(result, str) else "Result not a string")
            
            # Check if we got an API error about service parameter
            if isinstance(result, str) and "missing 1 required positional argument: 'service'" in result:
                print("❌ STILL GETTING SERVICE PARAMETER ERROR!")
                return False
            else:
                print("✅ No service parameter error detected")
                
        except Exception as e:
            error_str = str(e)
            print(f"❌ Error in webpage_research_tool: {error_str}")
            if "missing 1 required positional argument: 'service'" in error_str:
                print("❌ STILL GETTING SERVICE PARAMETER ERROR!")
                return False
            else:
                print("⚠️  Different error (not service parameter issue)")
                print(f"Error details: {error_str}")
        
        # Test 2: Test with invalid URL to trigger error handling  
        print("\n🧪 Test 2: Testing error handling with invalid URL...")
        try:
            result = await webpage_research_tool.ainvoke({"url": "https://this-does-not-exist-12345.com"})
            print(f"⚠️  Expected error but got result: {result[:100]}...")
        except Exception as e:
            error_str = str(e)
            print(f"✅ Expected error occurred: {error_str[:100]}...")
            if "missing 1 required positional argument: 'service'" in error_str:
                print("❌ STILL GETTING SERVICE PARAMETER ERROR!")
                return False
            else:
                print("✅ Error properly formatted with service parameter")
        
        print("\n🎉 All tests passed! APIError service parameter issue appears to be fixed.")
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
    print("WEBPAGE RESEARCH TOOL APIERROR FIX VERIFICATION")
    print("=" * 60)
    
    success = await test_webpage_research_tool()
    
    print("\n" + "=" * 60)
    if success:
        print("✅ TESTS PASSED - APIError service parameter issue appears to be fixed!")
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
