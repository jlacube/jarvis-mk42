# message_processing.py
import logging
import os
from typing import Any, Dict
from datetime import datetime

from langchain_core.messages import HumanMessage, AIMessageChunk, SystemMessage
from langchain_core.runnables import RunnableConfig
from langchain_core.tracers import ConsoleCallbackHandler
import chainlit as cl

# Import from new configuration system
from config.settings import get_settings
from utils.logging_config import get_logger
from utils.exceptions import ValidationError, AudioProcessingError
from utils.legacy import handle_error, validate_user_input

# Import for language detection
try:
    from langdetect import detect
except ImportError:
    logging.warning("langdetect not installed. Language detection will not work.")
    detect = None

logger = get_logger(__name__)


async def process_standard_output(res: Any, from_audio: bool = False):
    """
    Processes the standard output from the agent and sends it to the user.
    
    This function handles different types of output from the agent, including
    streaming and non-streaming responses. It supports both text and structured data.
    
    Args:
        res (Any): The response from the agent, which can be:
                  - Dict: Contains messages to be processed
                  - Stream: Contains chunks to be processed incrementally
        from_audio (bool, optional): Whether the original input was from audio.
                                    Defaults to False.
    
    Implementation Details:
        - For dictionary responses, the function extracts and formats the message content
        - For streaming responses, it processes chunks incrementally
        - Handles cases where message content might be a list or string
        
    Note:
        This function is designed to work with Chainlit's messaging system.
    """
    try:
        msg: cl.Message
        full_text_response = ""
        if isinstance(res, dict) and "messages" in res:
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
                # Get the user's language for consistent TTS
                user_language = cl.user_session.get("user_language")
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
    """
    Extracts and processes image attachments from a Chainlit message.
    
    This function identifies any image files attached to a message, reads their
    binary content, and prepares them for processing by the agent.
    
    Args:
        msg (cl.Message): The message object potentially containing image attachments
        
    Returns:
        list: A list of processed image objects with their content loaded,
              ready for analysis or generation tasks
              
    Processing Details:
        - Filters message elements to only include those with "image" in MIME type
        - Reads each image file's binary content and attaches it to the file object
        - Handles errors gracefully with appropriate logging
        
    Error Handling:
        - FileNotFoundError: When an image file path is invalid
        - General exceptions: For any other image processing errors
    """
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

def extract_documents_from_message(msg: cl.Message):
    """
    Extracts and processes document attachments from a Chainlit message.
    
    This function identifies any document files attached to a message, reads their
    binary content, and prepares them for processing by the document intelligence tools.
    
    Args:
        msg (cl.Message): The message object potentially containing document attachments
        
    Returns:
        list: A list of processed document objects with their content loaded,
              ready for analysis by document intelligence tools
              
    Processing Details:
        - Filters message elements to only include documents (PDF, Word, text files, etc.)
        - Reads each document file's binary content and attaches it to the file object
        - Handles errors gracefully with appropriate logging
        
    Error Handling:
        - FileNotFoundError: When a document file path is invalid
        - General exceptions: For any other document processing errors
    """
    documents = []

    if msg.elements is None:
        return documents

    # Processing documents exclusively - support common document types
    document_mime_types = [
        "application/pdf",
        "application/msword",
        "application/vnd.openxmlformats-officedocument.wordprocessingml.document",
        "text/plain",
        "text/markdown",
        "application/rtf",
        "application/vnd.oasis.opendocument.text"
    ]
    
    document_files = [file for file in msg.elements 
                     if any(mime_type in file.mime for mime_type in document_mime_types)]

    for document_file in document_files:
        # Read the document
        try:
            with open(document_file.path, "rb") as f:
                document_file.content = f.read()
            documents.append(document_file)
        except FileNotFoundError:
            logger.error(f"Document file not found at path: {document_file.path}")
        except Exception as e:
            logger.error(f"Error reading document file {document_file.path}: {e}", exc_info=True)

    return documents

@cl.on_message
async def on_message(message: cl.Message):
    """
    Processes incoming messages from users and generates appropriate responses.
    
    This Chainlit event handler function:
    1. Validates and sanitizes user input
    2. Extracts any images from the message
    3. Retrieves or initializes the agent for response generation
    4. Manages conversation history through session variables
    5. Invokes the agent with appropriate configuration
    6. Processes and sends the agent's response to the user
    
    Args:
        message (cl.Message): The incoming message from the user, potentially
                             containing text content and/or file attachments
                             
    Processing Flow:
        1. Validate and sanitize user input
        2. Extract and process any images attached to the message
        3. Verify agent initialization or re-initialize if needed
        4. Retrieve user and session context from user_session
        5. Create appropriate inputs for the agent including conversation history
        6. Configure and invoke the agent with the user's message
        7. Process the agent's response and send it back to the user
        8. Update conversation history with both user message and agent response
        
    Error Handling:
        - Validates input length and content
        - Catches and logs exceptions during message processing
        - Attempts to re-initialize the agent if it's not available
        - Generates user-friendly error messages for any failures
        
    Note:
        This function supports both text-based and audio-based conversations
        through the 'from_audio' metadata flag.
    """
    try:
        # Validate user input
        if not message.content:
            await cl.Message(content="I received an empty message. Please send me a message to assist you.").send()
            return
            
        try:
            # Validate and sanitize the input
            sanitized_content = validate_user_input(message.content, max_length=50000)
            message.content = sanitized_content
        except ValidationError as e:
            await cl.Message(content=f"Invalid input: {e.message}").send()
            return
        
        images = extract_images_from_message(message)
        if images:
            cl.user_session.set("images", images)
            
        documents = extract_documents_from_message(message)
        if documents:
            cl.user_session.set("documents", documents)

        # Import here to avoid circular dependency
        from chainlit_setup import init_chainlit

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

        # Detect language from the message if not already set in session
        if not cl.user_session.get("user_language") and len(message.content.strip()) > 0:
            try:
                if detect:
                    detected_language = detect(message.content)
                    if len(message.content.split()) > 3:  # Only detect if we have enough words
                        cl.user_session.set("user_language", detected_language)
                        logger.info(f"Detected language from text input: {detected_language}")
            except Exception as e:
                logger.warning(f"Language detection failed: {e}")

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

        settings = get_settings()
        runnable_config = RunnableConfig(callbacks=[
            cl.AsyncLangchainCallbackHandler(
                to_ignore=["__start__", "Prompt", "_write"],
            ),
            ConsoleCallbackHandler()], configurable=dict([("thread_id", thread_id)]), recursion_limit=settings.models.recursion_limit)

        logger.info(f"Invoking agent for thread_id: {thread_id}")
        res = await app.ainvoke(inputs, config=runnable_config)
        logger.info(f"Agent invocation completed for thread_id: {thread_id}")


        # Store the AI response in the session history as well
        if isinstance(res, dict) and "messages" in res:
             ai_response_message = res["messages"][-1] # Assuming the last message is the AI response
             updated_messages = cl.user_session.get("previous_messages")
             if updated_messages:
                 cl.user_session.set("previous_messages", updated_messages + [ai_response_message])
                 logger.debug(f"Appended AI response to previous_messages for session {session_id}")


        await process_standard_output(res, from_audio=from_audio)

    except ValidationError as e:
        logger.warning(f"Input validation failed: {e}")
        await cl.Message(content=f"Invalid input: {e.message}").send()
    except Exception as e:
        logger.error(f"Error processing message: {e}", exc_info=True) # Log the full error with traceback
        error_message = handle_error("Error processing message", e)
        await cl.Message(content=error_message).send()

