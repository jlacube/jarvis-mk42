import pytest
import io
from unittest.mock import patch, AsyncMock, MagicMock

from tools.multimodal_tools import imager_tool, video_tool, vocalizer_tool, imager_vision_tool

@pytest.mark.asyncio
async def test_imager_tool_with_mocks():
    """Test imager_tool with properly mocked dependencies."""
    test_query = "A serene mountain landscape at sunset"
    
    # Create mock for the Google genai client
    mock_client = MagicMock()
    mock_client.models.generate_images.return_value = MagicMock(
        generated_images=[MagicMock(image=MagicMock(image_bytes=b'fake_image_data'))]
    )
    
    # Mock Chainlit components
    mock_image = MagicMock()
    mock_message = MagicMock()
    mock_message.send = AsyncMock()
    
    with patch('google.genai.Client', return_value=mock_client), \
         patch('chainlit.Image', return_value=mock_image), \
         patch('chainlit.Message', return_value=mock_message):
        
        result = await imager_tool.ainvoke(test_query)
        
        # Should succeed with proper mocking
        assert "generated" in result.lower(), f"Expected success message, got: {result}"
        
        # Check that the client was called
        mock_client.models.generate_images.assert_called_once()

@pytest.mark.asyncio
async def test_video_tool_with_mocks():
    """Test video_tool with properly mocked dependencies."""
    test_query = "A drone flying over mountains"
    
    # Create mock for the Google genai client and operation
    mock_client = MagicMock()
    mock_operation = MagicMock()
    mock_operation.done = True
    mock_operation.response.generated_videos = [
        MagicMock(video=MagicMock(video_bytes=b'fake_video_data'))
    ]
    
    mock_client.models.generate_videos.return_value = mock_operation
    
    # Mock Chainlit components
    mock_video = MagicMock()
    mock_message = MagicMock()
    mock_message.send = AsyncMock()
    
    with patch('google.genai.Client', return_value=mock_client), \
         patch('chainlit.Video', return_value=mock_video), \
         patch('chainlit.Message', return_value=mock_message), \
         patch('time.sleep'):  # Patch sleep to avoid waiting
        
        result = await video_tool.ainvoke(test_query)
        
        # Should succeed with proper mocking
        assert "generated" in result.lower(), f"Expected success message, got: {result}"
        
        # Check that the client was called
        mock_client.models.generate_videos.assert_called_once()

@pytest.mark.asyncio
async def test_vocalizer_tool_with_mocks():
    """Test vocalizer_tool with properly mocked dependencies."""
    test_query = "Hello, this is a test message for text-to-speech."
    
    # Mock the audio processing function
    mock_audio_response = b'fake_audio_data'
    
    # Mock Chainlit components
    mock_audio = MagicMock()
    mock_message = MagicMock()
    mock_message.send = AsyncMock()
    
    with patch('audio_processing.get_audio_response', return_value=mock_audio_response), \
         patch('chainlit.Audio', return_value=mock_audio), \
         patch('chainlit.Message', return_value=mock_message):
        
        result = await vocalizer_tool.ainvoke(test_query)
        
        # Should succeed with proper mocking
        assert "generated" in result.lower() or "successfully" in result.lower(), f"Expected success message, got: {result}"

def test_imager_vision_tool():
    """Test imager_vision_tool (non-async test)."""
    # This test will work since it doesn't try to invoke the tool
    assert imager_vision_tool.name == "imager_vision_tool"
    assert "analyze" in imager_vision_tool.description.lower()
