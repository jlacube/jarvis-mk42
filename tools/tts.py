import asyncio

from elevenlabs import VoiceSettings
from langchain_community.tools.eleven_labs import ElevenLabsText2SpeechTool
from langchain.tools import tool

from dotenv import load_dotenv

import elevenlabs

load_dotenv()

# Initialize the ElevenLabs TTS tool
tts_tool = ElevenLabsText2SpeechTool(voice_id="wDsJlOXPqcvIUKdLXjDs")

#@tool
async def generate_audio_response(text: str) -> str:
    """
    Generate an audio response using the ElevenLabs LangChain community wrapper for text-to-speech.

    Args:
        text (str): The text to convert to speech.

    Returns:
        str: confirmation that the audio was generated or error if any
    """

    #tts_tool.stream_speech(text)

    from elevenlabs import ElevenLabs
    client = ElevenLabs()

    speech_stream = client.text_to_speech.convert_as_stream(
        voice_id="wDsJlOXPqcvIUKdLXjDs",
        output_format="mp3_44100_128",
        text=text,
        model_id="eleven_multilingual_v2",
    )

    elevenlabs.stream(speech_stream)

    return "The audio generated has been played to the user"


def get_audio_response(text: str) -> bytes:
    """
    Generate an audio response using the ElevenLabs LangChain community wrapper for text-to-speech.

    Args:
        text (str): The text to convert to speech.

    Returns:
        bytes: audio binary data
    """

    #tts_tool.stream_speech(text)

    from elevenlabs import ElevenLabs
    client = ElevenLabs()

    audio_bytes = b''
    for chunk in client.text_to_speech.convert(
        voice_id="wDsJlOXPqcvIUKdLXjDs",
        output_format="mp3_44100_128",
        text=text,
        model_id="eleven_multilingual_v2",
        voice_settings=VoiceSettings(speed=1.2)
    ):
        audio_bytes += chunk

    return audio_bytes

    #await cl.Message(
    #    content=query,
    #    elements=[cl.Audio(name="audio", content=audio_data)]
    #).send()


# Example usage
async def main():
    try:
        result = generate_audio_response("Hello, this is a test of ElevenLabs text-to-speech.")
        print(f"Audio generated")
    except Exception as e:
        print(f"Error: {e}")

# To run the main function, you would typically use an async event loop.

if __name__ == "__main__":
    asyncio.run(main())
