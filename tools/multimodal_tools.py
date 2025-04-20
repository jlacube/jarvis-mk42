import io
import time

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
    Use an MLLM to create an image based pn the prompt provided by the user as the query parameter
    :param query:
    :return: confirmation that the image was generated or error if any
    """

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


@tool
async def video_tool(query: str) -> str:
    """
    Use an MLLM to create a video based on the prompt provided by the user as the query parameter
    :param query:
    :return: confirmation that the video was generated or error if any
    """

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
        #video_data = requests.get(operation.response.generated_videos[0].video.uri, stream=True).content

    await cl.Message(
        content=query,
        elements=[cl.Video(name="video", content=video_data)]
    ).send()

    return "The video generated has been sent to the user"


@tool
async def vocalizer_tool(query: str) -> str:
    """
    Use an MLLM to generate an audio file via TTS based on the prompt provided by the user as the query parameter
    :param query:
    :return: confirmation that the audio was generated or error if any
    """

    audio_data = get_audio_response(query)

    await cl.Message(
        content=query,
        elements=[cl.Audio(name="audio", content=audio_data)]
    ).send()

    return "The audio generated has been sent to the user"


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
        #await cl.Message(content="", elements=[cl.Image(name="img", content=img_data.getvalue())]).send()



@tool
async def imager_vision_tool(query: str) -> str:
    """
    Use an MLLM to analyze image(s) based on the prompt provided by the user as the query parameter.
    The images are handled directly by this tool, don't worry about them being missing as a parameter.
    :param query: the analysis to perform
    :return: result of the analysis
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

    # return response.parsed

    cl_images = []
    for image in images:
        img_data:io.BytesIO = await plot_bounding_boxes(image_bytes=image.content, bounding_boxes=response.parsed)
        cl_images.append(cl.Image(name="img", content=img_data.getvalue()))

    #await cl.Message(content=response.text, elements=cl_images).send()
    await cl.Message(content=response.text).send()

    return response.text

