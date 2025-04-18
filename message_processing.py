# message_processing.py
import logging
import os
from typing import Any

from langchain_core.messages import HumanMessage, AIMessageChunk, SystemMessage
from langchain_core.runnables import RunnableConfig
from langchain_core.tracers import ConsoleCallbackHandler
from langgraph.pregel.io import AddableValuesDict
import chainlit as cl

from config import RECURSION_LIMIT, MPV_INSTALLED
from utils import handle_error

logger = logging.getLogger(__name__)


async def process_standard_output(res: Any, from_audio: bool = False):
    """Processes the standard output from the agent."""
    try:
        msg: cl.Message
        full_text_response = ""
        if isinstance(res, AddableValuesDict):
            text = res["messages"][-1].content
            if isinstance(text, list):
                chunks = []
                for chunk in text:
                    chunks.append(chunk)

                full_text_response = "\n".join(chunks)
                msg = cl.Message(full_text_response)
                await msg.send()
            else:
                full_text_response = text
                msg = cl.Message(full_text_response)
                await msg.send()
        else:
            # streaming
            msg = cl.Message("")
            await msg.send()

            for chunk in res:
                if isinstance(chunk[0], AIMessageChunk) and len(chunk[0].content) > 0:
                    await msg.stream_token(chunk[0].content)
                    full_text_response += chunk[0].content

            await msg.update()

        if from_audio:
            try:
                from audio_processing import get_audio_response
                audio_elt = cl.Audio(content=get_audio_response(full_text_response))
                audio_elt.auto_play = True
                msg.elements += [audio_elt]
                await msg.update()
                # await cl.Message(content="", elements=[]).send()
            except Exception as e:
                error_message = handle_error("Error generating audio response", e)
                await cl.Message(content=error_message).send()

    except Exception as e:
        error_message = handle_error("Error processing standard output", e)
        await cl.Message(content=error_message).send()


def load_markdown_file(file_path):
    """
    Loads the content of a markdown file.

    Args:
        file_path (str): The path to the markdown file.

    Returns:
        str: The content of the markdown file as a string.
        None: If the file is not found or an error occurs during reading.

    Raises:
        FileNotFoundError: If the specified file does not exist.
        IOError: If there is an error reading the file.
    """
    if not os.path.exists(file_path):
        raise FileNotFoundError(f"Error: The file '{file_path}' was not found.")

    try:
        with open(file_path, 'r', encoding='utf-8') as f:
            content = f.read()
        return content
    except IOError as e:
        print(f"Error reading file '{file_path}': {e}")
        raise # Re-raise the exception after printing the message
    except Exception as e:
        print(f"An unexpected error occurred while reading '{file_path}': {e}")
        raise # Re-raise the exception


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

        #langgraph_md = load_markdown_file("contexts/langgraph.md")

        if previous_messages is None:
            inputs = {"messages": [
                #SystemMessage(content=langgraph_md),
                # HumanMessage(content="if the question is about coding, always make sure you give back to me all code you received from the coding agent"),
                HumanMessage(content=message.content)
            ]}
        else:
            inputs = {"messages": previous_messages + [
                #SystemMessage(content=langgraph_md),
                # HumanMessage(content="if the question is about coding, always make sure you give back to me all code you received from the coding agent"),
                HumanMessage(content=message.content)
            ]}

        runnable_config = RunnableConfig(callbacks=[
            cl.AsyncLangchainCallbackHandler(
                to_ignore=["__start__", "Prompt", "_write"],
            ),
            ConsoleCallbackHandler()], configurable=dict([("thread_id", thread_id)]), recursion_limit=RECURSION_LIMIT)

        res = await app.ainvoke(inputs, config=runnable_config)

        await process_standard_output(res, from_audio=from_audio)

    except Exception as e:
        error_message = handle_error("Error processing message", e)
        await cl.Message(content=error_message).send()
