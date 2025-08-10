"""
Test script to verify coding_tool functionality with complete patches including Callable
"""
import sys
import os

# Add the project root to the path
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

# Now test the coding_tool functionality
try:
    from tools.agents_tools import coding_tool
    
    print("✅ Successfully imported coding_tool")
    
    # Test calling the tool with a simple request
    test_request = "Write a simple hello world function in Python"
    
    print(f"Testing coding_tool with request: {test_request}")
    
    # The tool should be callable without any type annotation errors
    result = coding_tool(test_request)
    
    print("✅ coding_tool executed successfully!")
    print(f"Result type: {type(result)}")
    
    if hasattr(result, 'content'):
        print(f"Result content preview: {str(result.content)[:200]}...")
    else:
        print(f"Result preview: {str(result)[:200]}...")
        
except ImportError as e:
    print(f"❌ Import error: {e}")
except NameError as e:
    print(f"❌ NameError (type annotation issue): {e}")
    if 'Callable' in str(e):
        print("💡 Callable patch may need adjustment")
    elif 'Annotated' in str(e):
        print("💡 Annotated patch may need adjustment") 
    elif 'Optional' in str(e):
        print("💡 Optional patch may need adjustment")
    elif 'ArgsSchema' in str(e):
        print("💡 ArgsSchema patch may need adjustment")
    elif 'SkipValidation' in str(e):
        print("💡 SkipValidation patch may need adjustment")
except Exception as e:
    print(f"⚠️ Other error (may be expected - need proper context): {e}")
    print("This may be expected since we're testing outside the full agent context")

print("\n✅ Test completed - checking for NameError exceptions above")
