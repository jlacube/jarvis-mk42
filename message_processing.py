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
# Assuming extract_images_from_message is in utils.py
# If it's elsewhere, adjust the import accordingly.
from utils import handle_error#, extract_images_from_message

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
            except Exception as e:
                logger.error("Error generating audio response: %s", str(e))
                raise

    except Exception as e:
        logger.error("Error processing standard output: %s", str(e))
        raise


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
        # Using logger instead of print for consistency
        logger.error(f"Error reading file '{file_path}': {e}")
        raise # Re-raise the exception after logging
    except Exception as e:
        # Using logger instead of print for consistency
        logger.error(f"An unexpected error occurred while reading '{file_path}': {e}", exc_info=True)
        raise # Re-raise the exception


def extract_images_from_message(msg: cl.Message):
    images = []

    if msg.elements is None:
        return images

    # Processing images exclusively
    image_files = [file for file in msg.elements if "image" in file.mime]

    for image_file in image_files:
        # Read the image
        try:
            with open(image_file.path, "rb") as f:
                image_file.content = f.read()
            images.append(image_file)
        except FileNotFoundError:
            logger.error(f"Image file not found at path: {image_file.path}")
        except Exception as e:
            logger.error(f"Error reading image file {image_file.path}: {e}", exc_info=True)


    return images

@cl.on_message
async def on_message(message: cl.Message):
    """Handles incoming messages from the user."""
    try:
        images = extract_images_from_message(message)
        if images:
            cl.user_session.set("images", images)

        from chainlit_setup import init_chainlit  # Import here to avoid circular dependency

        app = cl.user_session.get("app")
        if not app:
            logger.warning("Agent not initialized in user session. Attempting re-initialization.")
            await cl.Message(content="The agent is not initialized. Please start a new chat.").send()
            await init_chainlit()  # Attempt to re-initialize if it's not there.
            app = cl.user_session.get("app")  # Get the app again after re-initialization
            if not app:
                logger.error("Failed to initialize agent even after re-attempt. Aborting message processing.")
                return  # If still not initialized, exit.

        user_id = cl.user_session.get("user_id")
        user_name = cl.user_session.get("user_name")
        session_id = cl.user_session.get("session_id")
        thread_id = cl.user_session.get("thread_id")
        previous_messages = cl.user_session.get("previous_messages")
        from_audio = message.metadata.get("from_audio", False) if message.metadata else False

        #langgraph_md = load_markdown_file("contexts/langgraph.md") # Consider adding error handling if needed

        # Prepare inputs for the agent, including previous messages if they exist
        current_input = HumanMessage(content=message.content)
        logger.info(f"Processing message from user {user_name} (ID: {user_id}): {message.content[:100]}...") # Log message processing start

        if previous_messages is None:
            inputs = {"messages": [current_input]}
            # Initialize previous_messages for the session
            cl.user_session.set("previous_messages", [current_input])
            logger.debug(f"Initialized previous_messages for session {session_id}")
        else:
            inputs = {"messages": previous_messages + [current_input]}
            # Update previous_messages for the session
            cl.user_session.set("previous_messages", previous_messages + [current_input])
            logger.debug(f"Appended current message to previous_messages for session {session_id}")


        runnable_config = RunnableConfig(callbacks=[
            cl.AsyncLangchainCallbackHandler(
                to_ignore=["__start__", "Prompt", "_write"],
            ),
            ConsoleCallbackHandler()], configurable=dict([("thread_id", thread_id)]), recursion_limit=RECURSION_LIMIT)

        logger.info(f"Invoking agent for thread_id: {thread_id}")
        res = await app.ainvoke(inputs, config=runnable_config)
        logger.info(f"Agent invocation completed for thread_id: {thread_id}")


        # Store the AI response in the session history as well
        if isinstance(res, AddableValuesDict) and "messages" in res:
             ai_response_message = res["messages"][-1] # Assuming the last message is the AI response
             updated_messages = cl.user_session.get("previous_messages")
             if updated_messages:
                 cl.user_session.set("previous_messages", updated_messages + [ai_response_message])
                 logger.debug(f"Appended AI response to previous_messages for session {session_id}")


        await process_standard_output(res, from_audio=from_audio)

    except Exception as e:
        logger.error(f"Error processing message: {e}", exc_info=True) # Log the full error with traceback
        error_message = handle_error("Error processing message", e)
        raise

