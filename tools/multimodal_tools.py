import io
import time
import logging

import requests
from chainlit import Image
from langchain_core.tools import tool
from openai import OpenAI

import chainlit as cl
from pydantic import BaseModel

from audio_processing import get_audio_response


@tool
async def imager_tool(query: str) -> str:
    """
    Generate an image based on the provided text prompt using Google's Imagen model.
    
    This tool leverages Google's generative AI capabilities to create an image
    based on the descriptive text in the query. The generated image is sent directly
    to the user in the chat interface.
    
    Args:
        query (str): A detailed text description of the image to generate.
                    More specific and descriptive prompts tend to yield better results.
    
    Returns:
        str: A confirmation message that the image was generated and sent to the user,
             or an error message if the generation failed.
    
    Side Effects:
        - Creates and sends a Chainlit message containing the generated image
        - The message includes the original query as context
    
    Error Handling:
        - Catches and logs any exceptions during image generation
        - Returns a descriptive error message when generation fails
    
    Example:
        result = await imager_tool("A futuristic city with flying cars and neon lights at sunset")
    """
    try:
        from google import genai
        from google.genai import types
        client = genai.Client()

        generation_model = "imagen-3.0-generate-002"

        image = client.models.generate_images(
            model=generation_model,
            prompt=query,
            config=types.GenerateImagesConfig(
                number_of_images=1,
                aspect_ratio="4:3",
            ),
        )

        img_data = image.generated_images[0].image.image_bytes

        await cl.Message(
            content=query,
            elements=[cl.Image(name="img", content=img_data)]
        ).send()

        return "The image generated has been sent to the user"
    except Exception as e:
        logging.error(f"Error in imager_tool: {e}")
        return f"Error generating image: {e}"


@tool
async def video_tool(query: str) -> str:
    """
    Generates a short video based on the provided text description.
    
    This tool uses Google's Veo generative AI model to create a short video (5 seconds)
    that visualizes the content described in the query. The generated video is sent
    directly to the user in the chat interface.
    
    Args:
        query (str): A detailed text description of the video content to generate.
                    More specific and descriptive prompts tend to yield better results.
                    
    Returns:
        str: A confirmation message that the video was generated and sent to the user,
             or an error message if the generation failed.
             
    Implementation Details:
        - Uses Google's Veo model (veo-2.0-generate-001) for video generation
        - Creates a 5-second video in 16:9 aspect ratio
        - Polls the operation until completion
        - Downloads the video data and sends it to the user
        - Cleans up temporary files after processing
        
    Error Handling:
        - Catches and logs any exceptions during video generation
        - Returns a descriptive error message when generation fails
        
    Example:
        result = await video_tool("A drone flying over a futuristic city at sunset")
    """
    try:
        from google import genai
        from google.genai import types
        client = genai.Client(project="gen-lang-client-0911926804")

        generation_model = "veo-2.0-generate-001"

        operation = client.models.generate_videos(
            model=generation_model,
            prompt=query,
            config=types.GenerateVideosConfig(
                number_of_videos=1,
                duration_seconds=5,
                aspect_ratio="16:9"
            ),
        )

        while not operation.done:
            time.sleep(5)
            operation = client.operations.get(operation)
            print(operation)

        if operation.response.generated_videos[0].video.video_bytes is not None:
            video_data = operation.response.generated_videos[0].video.video_bytes
        else:
            video_data = client.files.download(file=operation.response.generated_videos[0].video)
            client.files.delete(name=operation.response.generated_videos[0].video.uri)

        await cl.Message(
            content=query,
            elements=[cl.Video(name="video", content=video_data)]
        ).send()

        return "The video generated has been sent to the user"
    except Exception as e:
        logging.error(f"Error in video_tool: {e}")
        return f"Error generating video: {e}"


@tool
async def vocalizer_tool(query: str) -> str:
    """
    Converts text to speech and sends the resulting audio to the user.
    
    This tool uses ElevenLabs' text-to-speech technology to generate natural-sounding
    speech from the provided text. The generated audio is sent directly to the user
    in the chat interface.
    
    Args:
        query (str): The text content to be converted to speech. This can be a sentence,
                    paragraph, or longer text that should be vocalized.
                    
    Returns:
        str: A confirmation message that the audio was generated and sent to the user,
             or an error message if the generation failed.
             
    Implementation Details:
        - Uses the get_audio_response function to generate audio data
        - Creates a Chainlit message with the audio attached as an element
        - The original text is included in the message for context
        
    Error Handling:
        - Catches and logs any exceptions during audio generation
        - Returns a descriptive error message when generation fails
        
    Example:
        result = await vocalizer_tool("Hello, I'm Jarvis. How may I assist you today?")
    """
    try:
        audio_data = get_audio_response(query)

        await cl.Message(
            content=query,
            elements=[cl.Audio(name="audio", content=audio_data)]
        ).send()

        return "The audio generated has been sent to the user"
    except Exception as e:
        logging.error(f"Error in vocalizer_tool: {e}")
        return f"Error generating audio: {e}"


class BoundingBox(BaseModel):
    box_2d: list[int]
    label: str

VISION_INSTRUCTIONS="""Return bounding boxes as an array with labels. Never return masks. Limit to 25 objects.
    If an object is present multiple times, give each object a unique label according to its distinct characteristics (colors, size, position, etc..)."""



async def plot_bounding_boxes(image_bytes: bytes, bounding_boxes: list[BoundingBox]) -> io.BytesIO:
    """
    Plots bounding boxes on an image with markers for each a name, using PIL, normalized coordinates, and different colors.
    Args:
        image_bytes: The image data.
        bounding_boxes: A list of bounding boxes containing the name of the object
        and their positions in normalized [y1 x1 y2 x2] format.
    """

    # Load the image
    from PIL import Image, ImageColor, ImageDraw, ImageFont
    with Image.open(io.BytesIO(image_bytes)) as im:
        width, height = im.size
        # Create a drawing object
        draw = ImageDraw.Draw(im)
        colors = list(ImageColor.colormap.keys())

        # Load a font
        font = ImageFont.load_default(size=int(min(width, height) / 100))

        # Iterate over the bounding boxes
        for i, bbox in enumerate(bounding_boxes):
            # Convert normalized coordinates to absolute coordinates
            y1, x1, y2, x2 = bbox.box_2d
            abs_y1 = int(y1 / 1000 * height)
            abs_x1 = int(x1 / 1000 * width)
            abs_y2 = int(y2 / 1000 * height)
            abs_x2 = int(x2 / 1000 * width)

            # Select a color from the list
            color = colors[i % len(colors)]

            # Draw the bounding box
            draw.rectangle(((abs_x1, abs_y1), (abs_x2, abs_y2)), outline=color, width=4)
            # Draw the text
            if bbox.label:
                draw.text((abs_x1 + 8, abs_y1 + 6), bbox.label, fill=color, font=font)

        img_data = io.BytesIO()

        im.save(img_data, format='PNG')

        return img_data



@tool
async def imager_vision_tool(query: str) -> str:
    """
    Analyzes images using Google's Gemini vision model and identifies objects with bounding boxes.
    
    This tool processes images from the user's session, performs object detection based on
    the query, and returns annotated images with bounding boxes around detected objects.
    
    Args:
        query (str): Instructions for the image analysis, such as "Identify all objects in this image"
                    or "Find all people in this photo"
                    
    Returns:
        str: A confirmation message that the analysis was completed and results sent to the user
        
    Implementation Details:
        - Retrieves images from the user's session
        - Uses Google's Gemini 2.0 Flash model for vision analysis
        - Applies bounding box detection with labels
        - Plots the bounding boxes on the original images
        - Sends both the parsed response and annotated images back to the user
        
    Note:
        The images are handled directly by this tool from the user session, so they don't
        need to be passed as parameters to the function.
        
    Example:
        result = await imager_vision_tool("Identify all objects in this image and label them")
    """

    from google import genai
    from google.genai import types
    client = genai.Client()

    generation_model = "gemini-2.0-flash-001"

    images:[cl.ImageElement] = cl.user_session.get("images")
    parts = [types.Part.from_bytes(data=image.content, mime_type=image.mime) for image in images]

    response = client.models.generate_content(
        model=generation_model,
        contents=[query] + parts,
        config=types.GenerateContentConfig(
            system_instruction=VISION_INSTRUCTIONS,
            temperature=0.5,
            response_mime_type="application/json",
            response_schema=list[BoundingBox]
        ),
    )

    cl_images = []
    for image in images:
        img_data:io.BytesIO = await plot_bounding_boxes(image_bytes=image.content, bounding_boxes=response.parsed)
        cl_images.append(cl.Image(name="img", content=img_data.getvalue()))

    await cl.Message(content=str(response.parsed), elements=cl_images).send()

    return "The processing was done successully and the response was send to the user"



