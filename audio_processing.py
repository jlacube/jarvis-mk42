# audio_processing.py
import io
import logging
from typing import List

import chainlit as cl
from langchain_core.messages import HumanMessage
from langchain_core.runnables import RunnableConfig

from audio.cl_audio import pcm_to_wav_buffer, elevenlabs_stt, elevenlabs_tts
from config import RECURSION_LIMIT
from message_processing import process_standard_output
#from message_processing import on_message
from utils import handle_error

logger = logging.getLogger(__name__)


@cl.on_audio_start
async def on_audio_start():
    """Handles the start of audio input."""
    try:
        cl.user_session.set("audio_message", True)
        cl.user_session.set("chunks", [])
        return True
    except Exception as e:
        error_message = handle_error("Error starting audio", e)
        logger.error(error_message)
        return False


@cl.on_audio_chunk
async def on_audio_chunk(chunk: cl.InputAudioChunk):
    """Handles incoming audio chunks."""
    try:
        chunks = cl.user_session.get("chunks") + [chunk.data]
        cl.user_session.set("chunks", chunks)
    except Exception as e:
        error_message = handle_error("Error processing audio chunk", e)
        logger.error(error_message)


@cl.on_message
async def on_message(message: cl.Message):
    """Handles incoming messages from the user."""
    try:
        from chainlit_setup import init_chainlit  # Import here to avoid circular dependency

        app = cl.user_session.get("app")
        if not app:
            await cl.Message(content="The agent is not initialized. Please start a new chat.").send()
            await init_chainlit()  # Attempt to re-initialize if it's not there.
            app = cl.user_session.get("app")  # Get the app again after re-initialization
            if not app:
                return  # If still not initialized, exit.

        user_id = cl.user_session.get("user_id")
        user_name = cl.user_session.get("user_name")
        session_id = cl.user_session.get("session_id")
        thread_id = cl.user_session.get("thread_id")
        previous_messages = cl.user_session.get("previous_messages")
        from_audio = message.metadata.get("from_audio", False) if message.metadata else False

        if previous_messages is None:
            inputs = {"messages": [
                # HumanMessage(content="if the question is about coding, always make sure you give back to me all code you received from the coding agent"),
                HumanMessage(content=message.content)
            ]}
        else:
            inputs = {"messages": previous_messages + [
                # HumanMessage(content="if the question is about coding, always make sure you give back to me all code you received from the coding agent"),
                HumanMessage(content=message.content)
            ]}

        runnable_config = RunnableConfig(callbacks=[
            cl.AsyncLangchainCallbackHandler(
                to_ignore=["__start__", "Prompt", "_write"],
            ),
            cl.ConsoleCallbackHandler()], configurable=dict([("thread_id", thread_id)]), recursion_limit=RECURSION_LIMIT)

        res = await app.ainvoke(inputs, config=runnable_config)

        await process_standard_output(res, from_audio=from_audio)

    except Exception as e:
        error_message = handle_error("Error processing message", e)
        await cl.Message(content=error_message).send()


@cl.on_audio_end
async def on_audio_end():
    """Handles the end of audio input and processes the audio."""
    try:
        chunks: List[bytes] = cl.user_session.get("chunks")
        wav_buffer = pcm_to_wav_buffer(b"".join(chunks))
        audio_file = io.BytesIO(wav_buffer)
        audio_file.name = 'audio.wav'

        response = await elevenlabs_stt(audio_file)

        await cl.Message(content=response, type="user_message").send()
        await on_message(cl.Message(content=response, metadata={"from_audio": True}))

        cl.user_session.set("chunks", [])
    except Exception as e:
        error_message = handle_error("Error ending audio", e)
        await cl.Message(content=error_message).send()


def get_audio_response(text: str) -> bytes:
    """Gets the audio response as bytes."""
    try:
        return elevenlabs_tts(text)  # Assuming elevenlabs_tts returns bytes
    except Exception as e:
        error_message = handle_error("Error getting audio response", e)
        logger.error(error_message)
        return b""  # Return empty bytes on error
