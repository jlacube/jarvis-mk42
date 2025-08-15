# tests/test_multimodal_tools_fixed.py
"""
Fixed integration tests for multimodal tools with proper Chainlit context mocking
"""

import pytest
from unittest.mock import patch, MagicMock, AsyncMock
import asyncio

from tools.multimodal_tools import imager_tool, video_tool, vocalizer_tool, imager_vision_tool


@pytest.fixture
def mock_chainlit_context():
    """Mock Chainlit context for testing"""
    with patch('chainlit.context.get_context') as mock_context, \
         patch('chainlit.Message') as mock_message, \
         patch('chainlit.Image') as mock_image, \
         patch('chainlit.Video') as mock_video, \
         patch('chainlit.Audio') as mock_audio:
        
        # Setup mock context
        mock_ctx = MagicMock()
        mock_ctx.session.thread_id = "test-thread-123"
        mock_context.return_value = mock_ctx
        
        # Setup mock elements
        mock_image.return_value = MagicMock()
        mock_video.return_value = MagicMock()
        mock_audio.return_value = MagicMock()
        
        # Setup mock message
        mock_msg = MagicMock()
        mock_msg.send = AsyncMock()
        mock_message.return_value = mock_msg
        
        yield {
            'context': mock_ctx,
            'message': mock_msg,
            'image': mock_image,
            'video': mock_video,
            'audio': mock_audio
        }


@pytest.mark.asyncio
async def test_imager_tool_with_mocks(mock_chainlit_context):
    """Test imager_tool with mocked image generation."""
    test_query = "A serene mountain landscape at sunset"
    
    # Mock the Google genai client
    mock_client = MagicMock()
    mock_image = MagicMock()
    mock_image.image_bytes = b"mock_image_data"
    mock_generated_image = MagicMock()
    mock_generated_image.image = mock_image
    mock_response = MagicMock()
    mock_response.generated_images = [mock_generated_image]
    
    mock_client.models.generate_image.return_value = mock_response
    
    with patch('tools.multimodal_tools.get_google_genai_client', return_value=mock_client):
        result = await imager_tool.ainvoke({"query": test_query})
        
        # Should succeed and return confirmation
        assert "image generated has been sent to the user" in result.lower()
        
        # Verify chainlit elements were created and message was sent
        mock_chainlit_context['message'].send.assert_called_once()


@pytest.mark.asyncio
async def test_video_tool_with_mocks(mock_chainlit_context):
    """Test video_tool with mocked video generation."""
    test_query = "A drone flying over mountains"
    
    # Mock the Google genai client
    mock_client = MagicMock()
    mock_video = MagicMock()
    mock_video.video_bytes = b"mock_video_data"
    mock_generated_video = MagicMock()
    mock_generated_video.video = mock_video
    mock_response = MagicMock()
    mock_response.generated_videos = [mock_generated_video]
    
    mock_client.models.generate_video.return_value = mock_response
    
    with patch('tools.multimodal_tools.get_google_genai_client', return_value=mock_client):
        result = await video_tool.ainvoke({"query": test_query})
        
        # Should succeed and return confirmation
        assert "video generated has been sent to the user" in result.lower()
        
        # Verify chainlit elements were created and message was sent
        mock_chainlit_context['message'].send.assert_called_once()


@pytest.mark.asyncio
async def test_vocalizer_tool_with_mocks(mock_chainlit_context):
    """Test vocalizer_tool with mocked audio generation."""
    test_query = "Hello, this is a test message for text-to-speech."
    
    # Mock the audio response function
    mock_audio_data = b"mock_audio_data"
    
    with patch('tools.multimodal_tools.get_audio_response', return_value=mock_audio_data):
        result = await vocalizer_tool.ainvoke({"text_input": test_query})
        
        # Should succeed and return confirmation
        assert "audio generated has been sent to the user" in result.lower()
        
        # Verify chainlit elements were created and message was sent
        mock_chainlit_context['message'].send.assert_called_once()


@pytest.mark.asyncio
async def test_imager_vision_tool_with_mocks(mock_chainlit_context):
    """Test imager_vision_tool with mocked image analysis."""
    test_query = "Identify all objects in this image"
    
    # Mock the Google genai client  
    mock_client = MagicMock()
    mock_response = MagicMock()
    mock_response.parsed = [
        {"box_2d": [10, 20, 100, 150], "label": "person"},
        {"box_2d": [200, 50, 300, 120], "label": "dog"}
    ]
    
    mock_client.models.generate_content.return_value = mock_response
    
    with patch('tools.multimodal_tools.get_google_genai_client', return_value=mock_client):
        # Mock image upload from session
        with patch('chainlit.user_session.get', return_value=[{"path": "/tmp/test.jpg"}]):
            result = await imager_vision_tool.ainvoke({"query": test_query})
            
            # Should succeed and return object detection results
            assert "person" in result.lower() or "dog" in result.lower()


@pytest.mark.asyncio
async def test_tools_without_chainlit_context():
    """Test that tools handle missing Chainlit context gracefully."""
    
    # Test each tool without mocking chainlit context
    test_cases = [
        (imager_tool, {"query": "Test image"}),
        (video_tool, {"query": "Test video"}),
        (vocalizer_tool, {"text_input": "Test audio"}),
        (imager_vision_tool, {"query": "Test vision"})
    ]
    
    for tool, test_input in test_cases:
        with pytest.raises(Exception) as exc_info:
            await tool.ainvoke(test_input)
        
        # Should raise a Chainlit context error or tool error
        assert "chainlit" in str(exc_info.value).lower() or "error" in str(exc_info.value).lower()


@pytest.mark.asyncio 
async def test_error_handling_in_tools(mock_chainlit_context):
    """Test error handling in multimodal tools."""
    
    # Test image tool with API error
    with patch('tools.multimodal_tools.get_google_genai_client', side_effect=Exception("API Error")):
        try:
            await imager_tool.ainvoke({"query": "Test"})
            assert False, "Should have raised an exception"
        except Exception as e:
            assert "error generating image" in str(e).lower()
    
    # Test audio tool with generation error
    with patch('tools.multimodal_tools.get_audio_response', side_effect=Exception("Audio Error")):
        try:
            await vocalizer_tool.ainvoke({"text_input": "Test"})
            assert False, "Should have raised an exception"
        except Exception as e:
            assert "error generating audio" in str(e).lower()


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
