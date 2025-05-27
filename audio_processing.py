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

# Import for language detection
try:
    from langdetect import detect
except ImportError:
    logging.warning("langdetect not installed. Language detection will not work.")
    detect = None

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


@cl.on_audio_end
async def on_audio_end():
    """Handles the end of audio input and processes the audio."""
    try:
        chunks: List[bytes] = cl.user_session.get("chunks")
        wav_buffer = pcm_to_wav_buffer(b"".join(chunks))
        audio_file = io.BytesIO(wav_buffer)
        audio_file.name = 'audio.wav'
        
        # Get user's language if it exists in session
        user_language = cl.user_session.get("user_language", None)
        
        # Transcribe with auto-detection or user's language if known
        response = await elevenlabs_stt(audio_file, language=user_language)

        # Store the transcription and flag it as coming from audio
        await cl.Message(content=response, type="user_message").send()
        
        # Save the transcription language for future response
        try:
            # Only update user_language if we don't have one yet or if confident in detection
            if user_language is None and len(response.split()) > 3:  # Only detect if we have enough words
                cl.user_session.set("user_language", detect(response))
                logger.info(f"Detected language from audio input: {detect(response)}")
        except Exception as e:
            logger.warning(f"Language detection failed: {e}")
            
        from message_processing import on_message
        await on_message(cl.Message(content=response, metadata={"from_audio": True}))

        cl.user_session.set("chunks", [])
    except Exception as e:
        error_message = handle_error("Error ending audio", e)
        await cl.Message(content=error_message).send()


def get_audio_response(text: str) -> bytes:
    """Gets the audio response as bytes."""
    try:
        # Get the user's language from the session if available
        user_language = cl.user_session.get("user_language", None)
        
        return elevenlabs_tts(text, language=user_language)
    except Exception as e:
        error_message = handle_error("Error getting audio response", e)
        logger.error(error_message)
        return b""  # Return empty bytes on error
