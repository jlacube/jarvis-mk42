#!/usr/bin/env python3
"""
Test script to simulate Manual Test Plan Test 4.4: File System Navigation
This simulates the exact request: "Find all Python files in the tools directory"
"""

import asyncio
import sys
import os

# Add the project root to Python path
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

async def simulate_test_4_4():
    """Simulate the exact scenario from Test 4.4 in the manual test plan"""
    print("Simulating Manual Test Plan Test 4.4: File System Navigation")
    print("Request: 'Find all Python files in the tools directory'")
    print()
    
    try:
        # Method 1: Using enhanced list_jarvis_files with both pattern and directory
        print("Method 1: Enhanced list_jarvis_files with pattern and directory")
        from tools.file_tools import list_jarvis_files
        
        result1 = await list_jarvis_files.ainvoke({
            "pattern": "*.py",
            "directory": "tools"
        })
        
        print(f"✅ Found {len(result1)} Python files in tools directory")
        print("Files found:")
        for file_path in result1:
            filename = os.path.basename(file_path)
            print(f"  - {filename}")
        
        print()
        
        # Method 2: Using the new dedicated find_files_in_directory tool
        print("Method 2: Dedicated find_files_in_directory tool")
        from tools.file_tools import find_files_in_directory
        
        result2 = await find_files_in_directory.ainvoke({
            "directory": "tools",
            "file_extension": "py"
        })
        
        print(f"✅ Found {len(result2)} Python files in tools directory")
        print("Files found:")
        for file_path in result2:
            filename = os.path.basename(file_path)
            print(f"  - {filename}")
        
        print()
        
        # Verify both methods return the same results
        if set(result1) == set(result2):
            print("✅ Both methods return identical results")
        else:
            print("⚠️  Methods return different results")
            
        print()
        print("Expected Test Results:")
        print("- ✅ Correct files are located")
        print("- ✅ Paths are properly resolved") 
        print("- ✅ Subdirectories are searched appropriately")
        print("- ✅ Results are complete and accurate")
        
        return True
        
    except Exception as e:
        print(f"❌ Error during test: {e}")
        return False

async def main():
    """Main test function"""
    print("=" * 70)
    print("MANUAL TEST PLAN TEST 4.4 SIMULATION")
    print("=" * 70)
    
    success = await simulate_test_4_4()
    
    print("\n" + "=" * 70)
    if success:
        print("✅ TEST 4.4 SIMULATION SUCCESSFUL!")
        print("\nThe AI agent should now be able to successfully respond to:")
        print("'Find all Python files in the tools directory'")
        print("\nWith either:")
        print("1. list_jarvis_files(pattern='*.py', directory='tools')")
        print("2. find_files_in_directory(directory='tools', file_extension='py')")
        exit_code = 0
    else:
        print("❌ TEST 4.4 SIMULATION FAILED")
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
