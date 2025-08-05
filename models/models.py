import os

from langchain_openai import ChatOpenAI
from langchain_anthropic import ChatAnthropic
from langchain_mistralai import ChatMistralAI
from langchain_google_genai import ChatGoogleGenerativeAI

# Import the new configuration system
from config.settings import get_settings

def get_anthropic_model(streaming:bool = False, temperature:int = 0):
    settings = get_settings()
    return ChatAnthropic(
        model="claude-3-5-haiku-20241022",
        temperature=temperature or settings.models.default_temperature,
        max_tokens=settings.models.default_max_tokens,
        streaming=streaming or settings.models.streaming
    )

def get_mistral_ai_model(streaming:bool = False, temperature:int = 0):
    settings = get_settings()
    return ChatMistralAI(
        model="mistral-small-latest",
        max_tokens=32000,
        temperature=temperature or settings.models.default_temperature,
        streaming=streaming or settings.models.streaming
    )

def get_google_reasoning_model(streaming:bool = False, temperature:int = 0):
    settings = get_settings()
    return ChatGoogleGenerativeAI(
        model="gemini-2.5-pro-exp-03-25",
        temperature=temperature or settings.models.default_temperature,
        max_tokens=65536,
        disable_streaming=(not (streaming or settings.models.streaming))
    )

def get_google_model(streaming:bool = False, temperature:int = 0):
    settings = get_settings()
    return ChatGoogleGenerativeAI(
        model="gemini-2.0-flash",
        temperature=temperature or settings.models.default_temperature,
        max_tokens=settings.models.default_max_tokens,
        disable_streaming=(not (streaming or settings.models.streaming))
    )

def get_openai_model(streaming:bool = False, temperature:int = 0):
    settings = get_settings()
    return ChatOpenAI(
        model_name="gpt-4o-mini",
        temperature=temperature or settings.models.default_temperature,
        max_tokens=settings.models.default_max_tokens,
        streaming=streaming or settings.models.streaming
    )

def get_openai_reasoning_model(streaming:bool = False):
    settings = get_settings()
    return ChatOpenAI(
        model_name="o3-mini",
        max_tokens=settings.models.default_max_tokens,
        streaming=streaming or settings.models.streaming
    )
