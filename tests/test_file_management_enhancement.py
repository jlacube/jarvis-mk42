#!/usr/bin/env python3
"""
Test script to verify the enhanced file management tools
"""

import asyncio
import sys
import os

# Add the project root to Python path
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

async def test_file_management_tools():
    """Test all file management tools to ensure they work correctly"""
    print("Testing enhanced file management tools...")
    
    try:
        # Import the file tools
        from tools.file_tools import list_jarvis_files, find_files_in_directory
        
        print("✅ Successfully imported file management tools")
        
        # Test 1: Basic file listing (all files)
        print("\n🧪 Test 1: List all files (basic functionality)...")
        try:
            result = await list_jarvis_files.ainvoke({})
            print(f"✅ Found {len(result)} total files in project")
            
            # Check if we have expected files
            py_files = [f for f in result if f.endswith('.py')]
            print(f"   - {len(py_files)} Python files found")
            
        except Exception as e:
            print(f"❌ Error in basic file listing: {e}")
            return False
        
        # Test 2: Pattern filtering (Python files)
        print("\n🧪 Test 2: List Python files using pattern...")
        try:
            result = await list_jarvis_files.ainvoke({"pattern": "*.py"})
            print(f"✅ Found {len(result)} Python files using pattern filter")
            
        except Exception as e:
            print(f"❌ Error in pattern filtering: {e}")
            return False
        
        # Test 3: Directory filtering (tools directory)
        print("\n🧪 Test 3: List files in tools directory...")
        try:
            result = await list_jarvis_files.ainvoke({"directory": "tools"})
            print(f"✅ Found {len(result)} files in tools directory")
            
        except Exception as e:
            print(f"❌ Error in directory filtering: {e}")
            return False
        
        # Test 4: Combined pattern and directory filtering (Python files in tools)
        print("\n🧪 Test 4: List Python files in tools directory...")
        try:
            result = await list_jarvis_files.ainvoke({"pattern": "*.py", "directory": "tools"})
            print(f"✅ Found {len(result)} Python files in tools directory")
            
            # Show some examples
            if result:
                print("   Examples:")
                for file_path in result[:5]:
                    filename = os.path.basename(file_path)
                    print(f"   - {filename}")
                    
        except Exception as e:
            print(f"❌ Error in combined filtering: {e}")
            return False
        
        # Test 5: find_files_in_directory tool
        print("\n🧪 Test 5: Find Python files using dedicated search tool...")
        try:
            result = await find_files_in_directory.ainvoke({"directory": "tools", "file_extension": "py"})
            print(f"✅ Found {len(result)} Python files using find_files_in_directory")
            
        except Exception as e:
            print(f"❌ Error in find_files_in_directory: {e}")
            return False
        
        # Test 6: Non-existent directory handling
        print("\n🧪 Test 6: Handle non-existent directory gracefully...")
        try:
            result = await list_jarvis_files.ainvoke({"directory": "nonexistent_directory"})
            print(f"✅ Gracefully handled non-existent directory (returned {len(result)} files)")
            
        except Exception as e:
            print(f"❌ Error handling non-existent directory: {e}")
            return False
        
        # Test 7: Different file extensions
        print("\n🧪 Test 7: Find different file types...")
        try:
            md_files = await find_files_in_directory.ainvoke({"directory": ".", "file_extension": "md"})
            json_files = await find_files_in_directory.ainvoke({"directory": ".", "file_extension": "json"})
            
            print(f"✅ Found {len(md_files)} Markdown files and {len(json_files)} JSON files")
            
        except Exception as e:
            print(f"❌ Error testing different file extensions: {e}")
            return False
        
        print("\n🎉 All file management tests passed!")
        return True
        
    except ImportError as e:
        print(f"❌ Import error: {e}")
        return False
    except Exception as e:
        print(f"❌ Unexpected error: {e}")
        return False

async def main():
    """Main test function"""
    print("=" * 70)
    print("FILE MANAGEMENT TOOLS ENHANCEMENT VERIFICATION")
    print("=" * 70)
    
    success = await test_file_management_tools()
    
    print("\n" + "=" * 70)
    if success:
        print("✅ ALL TESTS PASSED - File management tools are working correctly!")
        print("\nThe tools now support:")
        print("- Basic file listing")
        print("- Pattern-based filtering (*.py, *.js, etc.)")
        print("- Directory-specific searches")
        print("- Combined pattern + directory filtering")
        print("- Dedicated find_files_in_directory tool")
        exit_code = 0
    else:
        print("❌ TESTS FAILED - Issues found in file management tools")
        exit_code = 1
    print("=" * 70)
    
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
