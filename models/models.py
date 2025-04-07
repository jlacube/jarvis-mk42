import os

from langchain_openai import ChatOpenAI
from langchain_anthropic import ChatAnthropic
from langchain_mistralai import ChatMistralAI
from langchain_google_genai import ChatGoogleGenerativeAI


def get_anthropic_model(streaming:bool = False, temperature:int = 0):
    return ChatAnthropic(
        model="claude-3-5-haiku-20241022",
        temperature=temperature,
        max_tokens=8192,
        streaming=streaming
    )

def get_mistral_ai_model(streaming:bool = False, temperature:int = 0):
    return ChatMistralAI(
        model="mistral-small-latest",
        max_tokens=32000,
        temperature=temperature,
        streaming=streaming
    )

def get_google_reasoning_model(streaming:bool = False, temperature:int = 0):
    return ChatGoogleGenerativeAI(
        model="gemini-2.5-pro-exp-03-25",
        temperature=temperature,
        max_tokens=65536,
        disable_streaming=(not streaming)
    )

def get_google_model(streaming:bool = False, temperature:int = 0):
    return ChatGoogleGenerativeAI(
        model="gemini-2.0-flash",
        temperature=temperature,
        max_tokens=8192,
        disable_streaming=(not streaming)
    )

def get_openai_model(streaming:bool = False, temperature:int = 0):
    return ChatOpenAI(
        model_name="gpt-4o-mini",
        temperature=temperature,
        max_tokens=8192,
        streaming=streaming
    )

def get_openai_reasoning_model(streaming:bool = False):
    return ChatOpenAI(
        model_name="o3-mini",
        max_tokens=8192,
        streaming=streaming
    )
