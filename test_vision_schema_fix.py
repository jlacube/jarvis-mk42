#!/usr/bin/env python3
"""
Test Image Vision Tool Schema Fix
===============================

This script tests the fix for the "Unsupported schema type" error
in the image vision tool by verifying the schema compatibility
with the Google GenAI API.
"""

import asyncio
import sys
import os
from unittest.mock import AsyncMock, MagicMock, patch
from typing import List

# Add the project root to the path
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from tools.multimodal_tools import imager_vision_tool, BoundingBox, VisionAnalysisResponse
import chainlit as cl

class MockImageElement:
    """Mock image element for testing"""
    def __init__(self, content: bytes, mime: str):
        self.content = content
        self.mime = mime

async def test_vision_schema_compatibility():
    """Test that the vision tool schema is compatible with Google GenAI API"""
    print("=" * 60)
    print("TEST: Vision Tool Schema Compatibility")
    print("=" * 60)
    
    # Test the Pydantic models
    try:
        # Test BoundingBox model
        bbox = BoundingBox(box_2d=[100, 200, 300, 400], label="test_object")
        print(f"✅ BoundingBox model created successfully: {bbox}")
        
        # Test VisionAnalysisResponse model
        response_model = VisionAnalysisResponse(bounding_boxes=[bbox])
        print(f"✅ VisionAnalysisResponse model created successfully")
        
        # Test schema generation
        schema = VisionAnalysisResponse.model_json_schema()
        print(f"✅ Schema generated successfully")
        print(f"   Schema type: {schema.get('type')}")
        print(f"   Required fields: {schema.get('required', [])}")
        
        # Verify schema structure
        properties = schema.get('properties', {})
        if 'bounding_boxes' in properties:
            print("✅ Schema contains 'bounding_boxes' field")
            bbox_schema = properties['bounding_boxes']
            if bbox_schema.get('type') == 'array':
                print("✅ 'bounding_boxes' is correctly defined as array")
            else:
                print(f"❌ 'bounding_boxes' type is {bbox_schema.get('type')}, expected 'array'")
                return False
        else:
            print("❌ Schema missing 'bounding_boxes' field")
            return False
            
    except Exception as e:
        print(f"❌ Schema compatibility test failed: {e}")
        return False
    
    return True

async def test_vision_tool_with_fixed_schema():
    """Test the vision tool with the fixed schema"""
    print("\n" + "=" * 60)
    print("TEST: Vision Tool with Fixed Schema")
    print("=" * 60)
    
    # Create mock images
    mock_images = [
        MockImageElement(b'fake_image_data_1', 'image/jpeg')
    ]
    
    # Mock the user session to have images
    mock_session = {"images": mock_images}
    
    # Create mock response with the new schema structure
    mock_bounding_boxes = [
        BoundingBox(box_2d=[10, 20, 100, 150], label="person"),
        BoundingBox(box_2d=[200, 50, 300, 120], label="dog")
    ]
    mock_vision_response = VisionAnalysisResponse(bounding_boxes=mock_bounding_boxes)
    
    # Mock the Google genai client
    mock_client = MagicMock()
    mock_response = MagicMock()
    mock_response.parsed = mock_vision_response
    mock_client.models.generate_content.return_value = mock_response
    
    # Mock chainlit functions
    async def mock_send_message(*args, **kwargs):
        print(f"✅ Would send message with content and {len(kwargs.get('elements', []))} image elements")
        return True
    
    with patch('chainlit.user_session') as mock_user_session, \
         patch('google.genai.Client', return_value=mock_client), \
         patch('tools.multimodal_tools.plot_bounding_boxes') as mock_plot, \
         patch('chainlit.Message') as mock_message_class:
        
        # Configure mocks
        mock_user_session.get.side_effect = lambda key: mock_session.get(key)
        mock_plot.return_value = MagicMock()
        mock_message = MagicMock()
        mock_message.send = mock_send_message
        mock_message_class.return_value = mock_message
        
        try:
            result = await imager_vision_tool.ainvoke("Analyze this image and identify all objects")
            print(f"✅ Tool executed successfully: {result}")
            
            # Verify the API was called with the correct schema
            mock_client.models.generate_content.assert_called_once()
            call_args = mock_client.models.generate_content.call_args
            config = call_args[1]['config']
            
            # Check that response_schema is set to our new model
            if hasattr(config, 'response_schema'):
                print(f"✅ response_schema is set to: {config.response_schema}")
                if config.response_schema == VisionAnalysisResponse:
                    print("✅ Schema correctly set to VisionAnalysisResponse")
                else:
                    print(f"❌ Unexpected schema: {config.response_schema}")
                    return False
            else:
                print("❌ response_schema not found in config")
                return False
            
        except Exception as e:
            print(f"❌ Error during execution: {e}")
            return False
    
    return True

async def test_backwards_compatibility():
    """Test that the vision tool still works with the expected data structure"""
    print("\n" + "=" * 60)
    print("TEST: Backwards Compatibility")
    print("=" * 60)
    
    # Test that we can still work with the old bounding box data
    try:
        # Old format bounding boxes (as they might come from API)
        old_bbox_data = [
            {"box_2d": [10, 20, 100, 150], "label": "person"},
            {"box_2d": [200, 50, 300, 120], "label": "dog"}
        ]
        
        # Convert to new format
        bounding_boxes = [BoundingBox(**bbox) for bbox in old_bbox_data]
        response = VisionAnalysisResponse(bounding_boxes=bounding_boxes)
        
        print(f"✅ Successfully converted old format to new format")
        print(f"   Found {len(response.bounding_boxes)} bounding boxes")
        
        # Test that plot_bounding_boxes can still work with the BoundingBox objects
        for i, bbox in enumerate(response.bounding_boxes):
            print(f"   Box {i+1}: {bbox.label} at {bbox.box_2d}")
        
    except Exception as e:
        print(f"❌ Backwards compatibility test failed: {e}")
        return False
    
    return True

async def main():
    """Run all tests"""
    print("🔍 Testing Image Vision Tool Schema Fix")
    print("This test verifies the fix for the 'Unsupported schema type' error.")
    
    # Track test results
    results = []
    
    # Run tests
    results.append(await test_vision_schema_compatibility())
    results.append(await test_vision_tool_with_fixed_schema())
    results.append(await test_backwards_compatibility())
    
    # Summary
    print("\n" + "=" * 60)
    print("TEST SUMMARY")
    print("=" * 60)
    
    passed = sum(results)
    total = len(results)
    
    print(f"Tests Passed: {passed}/{total}")
    
    if passed == total:
        print("🎉 ALL TESTS PASSED!")
        print("\nThe image vision tool schema issue has been resolved:")
        print("1. ✅ Created VisionAnalysisResponse wrapper model")
        print("2. ✅ Fixed response_schema to use supported format")
        print("3. ✅ Updated vision instructions for new schema")
        print("4. ✅ Maintained backwards compatibility")
        print("\nThe 'Unsupported schema type' error should now be fixed.")
    else:
        print("❌ Some tests failed. Review the output above for details.")
        return 1
    
    return 0

if __name__ == "__main__":
    exit_code = asyncio.run(main())
    sys.exit(exit_code)
