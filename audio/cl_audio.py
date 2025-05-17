import io
import os
import wave
import logging
from typing import AsyncGenerator

import requests
from pydantic import SecretStr

elevenlabs_key = SecretStr(os.getenv('ELEVENLABS_API_KEY'))

from elevenlabs import ElevenLabs

client = ElevenLabs(
    api_key=f"{elevenlabs_key.get_secret_value()}",
)

def pcm_to_wav_buffer(pcm_data: bytes) -> bytes:
    try:
        wav_buffer = io.BytesIO()
        with wave.open(wav_buffer, 'wb') as wav_file:
            wav_file.setnchannels(1)
            wav_file.setsampwidth(2)
            wav_file.setframerate(24000)
            wav_file.writeframes(pcm_data)

        wav_buffer.seek(0)
        return wav_buffer.read()
    except Exception as e:
        logging.error(f"WAV buffer conversion failed: {e}")
        raise


async def elevenlabs_stt(file: io.BytesIO) -> str:
    headers = {
        'xi-api-key': f'{elevenlabs_key.get_secret_value()}'
    }

    form_data = { "model_id" : "scribe_v1", "language": "en" }

    files = { "file": file }

    response = requests.post("https://api.elevenlabs.io/v1/speech-to-text", headers=headers, files=files, data=form_data).json()
    return response['text']


def elevenlabs_tts(text: str) -> bytes:
    response = client.text_to_speech.convert(
        voice_id="JBFqnCBsd6RMkjVDRZzb",
        output_format="mp3_44100_128",
        text=text,
        model_id="eleven_multilingual_v2",
    )

    bytes_chunks = []
    for chunk in response:
        bytes_chunks.append(chunk)

    return b''.join(bytes_chunks)

