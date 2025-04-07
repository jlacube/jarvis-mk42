import requests
from langchain_core.tools import tool
from openai import OpenAI

import chainlit as cl

@tool
async def imager_tool(query: str) -> str:
    """
    Use an MLLM to create an image based pn the prompt provided by the user as the query parameter
    :param query:
    :return: confirmation that the image was generated or error if any
    """
    response = OpenAI().images.generate(
        model="dall-e-3",
        prompt=query,
        # quality="hd",
        n=1,
        size="1024x1024",
        style="natural"
    )

    img_data = requests.get(response.data[0].url,
                            stream=True,
                            ).content

    await cl.Message(
        content=query,
        elements=[cl.Image(name="img", content=img_data)]
    ).send()

    return "The image generated has been sent to the user"


@tool
async def vocalizer_tool(query: str) -> str:
    """
        Use an MLLM to generate an audio file via TTS based on the prompt provided by the user as the query parameter
        :param query:
        :return: confirmation that the audio was generated or error if any
        """

    response = OpenAI().audio.speech.create(
        model="tts-1",
        input=query,
        voice="alloy"
    )

    audio_data = response.content

    await cl.Message(
        content=query,
        elements=[cl.Audio(name="audio", content=audio_data)]
    ).send()

    return "The audio generated has been sent to the user"