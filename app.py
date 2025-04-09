# app.py
import logging

import chainlit as cl
from chainlit.cli import run_chainlit

# Import the other modules
from chainlit_setup import start, on_chat_resume
from audio_processing import on_audio_start, on_audio_chunk, on_audio_end
from message_processing import on_message
from users import *

import asyncpg
import boto3

# Configure logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')

# Chainlit decorators are now in their respective modules
# This file only serves as the entry point

if __name__ == "__main__":
    run_chainlit(__file__)
