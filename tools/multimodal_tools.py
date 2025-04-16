import time

import requests
from langchain_core.tools import tool
from openai import OpenAI

import chainlit as cl

from audio_processing import get_audio_response


@tool
async def imager_tool(query: str) -> str:
    """
    Use an MLLM to create an image based pn the prompt provided by the user as the query parameter
    :param query:
    :return: confirmation that the image was generated or error if any
    """
    #response = OpenAI().images.generate(
    #    model="dall-e-3",
    #    prompt=query,
    #    # quality="hd",
    #    n=1,
    #    size="1024x1024",
    #    style="natural"
    #)

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

    #img_data = requests.get(response.data[0].url,
    #                        stream=True,
    #                        ).content

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