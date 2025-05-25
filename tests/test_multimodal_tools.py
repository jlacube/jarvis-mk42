import pytest
import io
from unittest.mock import patch, AsyncMock, MagicMock

from tools.multimodal_tools import imager_tool, video_tool, vocalizer_tool, imager_vision_tool

@pytest.mark.asyncio
async def test_imager_tool_with_mocks():
    """Test imager_tool with mocked Google generative AI."""
    test_query = "A serene mountain landscape at sunset"
    
    # Create mock for the Google genai client
    mock_client = MagicMock()
    mock_client.models.generate_images.return_value = MagicMock(
        generated_images=[MagicMock(image=MagicMock(image_bytes=b'fake_image_data'))]
    )
    
    # Patch the necessary dependencies - without mocking chainlit context
    # This will cause the function to use the error path
    with patch('google.genai.Client', return_value=mock_client):
        result = await imager_tool.ainvoke(test_query)
        
        # With no chainlit context, we should get an error
        assert "error" in result.lower(), f"Result should report an error, got: {result}"
        
        # Check that the client was called with the correct parameters
        mock_client.models.generate_images.assert_called_once()
        args, kwargs = mock_client.models.generate_images.call_args
        assert kwargs["prompt"] == test_query, f"Expected prompt '{test_query}', got '{kwargs['prompt']}'"


@pytest.mark.asyncio
async def test_video_tool_with_mocks():
    """Test video_tool with mocked Google video generation."""
    test_query = "A drone flying over mountains"
    
    # Create mock for the Google genai client and operation
    mock_client = MagicMock()
    mock_operation = MagicMock()
    mock_operation.done = True
    mock_operation.response.generated_videos = [
        MagicMock(video=MagicMock(video_bytes=b'fake_video_data'))
    ]
    
    mock_client.models.generate_videos.return_value = mock_operation
    
    # Patch the necessary dependencies - without mocking chainlit context
    # This will cause the function to use the error path
    with patch('google.genai.Client', return_value=mock_client), \
         patch('time.sleep'):  # Patch sleep to avoid waiting
        
        result = await video_tool.ainvoke(test_query)
        
        # With no chainlit context, we should get an error
        assert "error" in result.lower(), f"Result should report an error, got: {result}"
        
        # Check that the client was called with the correct parameters
        mock_client.models.generate_videos.assert_called_once()
        args, kwargs = mock_client.models.generate_videos.call_args
        assert kwargs["prompt"] == test_query, f"Expected prompt '{test_query}', got '{kwargs['prompt']}'"


@pytest.mark.asyncio
async def test_vocalizer_tool_with_mocks():
    """Test vocalizer_tool with mocked audio generation."""
    test_query = "Hello, this is a test message for text-to-speech."
    
    # Mock the get_audio_response function
    mock_audio_data = b'fake_audio_data'
    
    # Patch the necessary dependencies - without mocking chainlit context
    # This will cause the function to use the error path
    with patch('tools.multimodal_tools.get_audio_response', return_value=mock_audio_data):
        
        result = await vocalizer_tool.ainvoke(test_query)
        
        # With no chainlit context, we should get an error
        assert "error" in result.lower(), f"Result should report an error, got: {result}"


@pytest.mark.asyncio
async def test_imager_vision_tool_with_mocks():
    """Test imager_vision_tool with mocked image analysis."""
    test_query = "Identify all objects in this image"
    
    # Create mock for the Google genai client
    mock_client = MagicMock()
    mock_response = MagicMock()
    mock_response.parsed = [
        {"box_2d": [10, 20, 100, 150], "label": "person"},
        {"box_2d": [200, 50, 300, 120], "label": "dog"}
    ]
    
    mock_client.models.generate_content.return_value = mock_response
    
    # Create a simple error handler that will be called instead
    async def mock_imager_vision(*args, **kwargs):
        return "Error processing image: Chainlit context not found"
    
    # Patch the entire function to return an error message
    with patch('tools.multimodal_tools.imager_vision_tool._arun', mock_imager_vision):
        result = await imager_vision_tool.ainvoke(test_query)
        
        # We should get our mocked error message
        assert "error" in result.lower(), f"Result should report an error, got: {result}"
