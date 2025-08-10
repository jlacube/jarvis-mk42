# chainlit_setup.py
import datetime
import json
import logging
import uuid

import chainlit as cl
from chainlit.config import ThreadDict
from chainlit.data.sql_alchemy import SQLAlchemyDataLayer
from langchain_core.messages import HumanMessage, AIMessage
from sqlalchemy import create_engine
from typing import List, Optional

from agent_management import initialize_agent
from utils.legacy import handle_error
from utils.logging_config import get_logger
from utils.exceptions import SessionError

logger = get_logger(__name__)


def serialize_json(obj):
    """
    Custom JSON serializer that handles Python objects including lists.
    This fixes SQLite parameter binding errors for list types.
    """
    return json.dumps(obj, default=str, ensure_ascii=False)


def deserialize_json(obj):
    """
    Custom JSON deserializer that handles JSON strings back to Python objects.
    """
    if obj is None:
        return None
    try:
        return json.loads(obj)
    except (json.JSONDecodeError, TypeError):
        return obj


@cl.data_layer
def get_data_layer():
    """
    Configure Chainlit to use SQLAlchemy with async SQLite for data persistence.
    This resolves PostgreSQL connection errors by using a local SQLite database.
    """
    return SQLAlchemyDataLayer(
        conninfo="sqlite+aiosqlite:///./chainlit.db"
    )


async def init_chainlit():
    """
    Initializes the Chainlit session with user and thread information.
    
    This function:
    1. Retrieves or creates session, user, and thread identifiers
    2. Initializes the agent with contextual information
    3. Stores session data for later use
    
    The initialization process sets up:
    - Unique identifiers for the session, user, and thread
    - Current timestamp for context awareness
    - The agent instance with appropriate configurations
    
    All these components are stored in the user_session for access throughout 
    the conversation lifecycle.
    
    Error Handling:
    - Catches and logs any exceptions during initialization
    - Sends a user-friendly error message if initialization fails
    """
    try:
        session_id = str(uuid.uuid4()) if cl.context.session.id is None else cl.context.session.id

        if cl.context.session.user is not None:
            user_id = cl.context.session.user.identifier if cl.context.session.user.identifier else str(uuid.uuid4())
            user_name = "" if cl.context.session.user.identifier is None else cl.context.session.user.identifier
        else:
            user_id = str(uuid.uuid4())
            user_name = "Anonymous"
        thread_id = cl.context.session.thread_id
        now = datetime.datetime.now(datetime.timezone.utc)

        app = await initialize_agent(now, user_id, session_id, user_name, thread_id)

        if app:
            cl.user_session.set("app", app)
            cl.user_session.set("now", now)
            cl.user_session.set("user_id", user_id)
            cl.user_session.set("user_name", user_name)
            cl.user_session.set("session_id", session_id)
            cl.user_session.set("thread_id", thread_id)
        else:
            await cl.Message(content="Failed to initialize the agent.").send()

    except Exception as e:
        error_message = handle_error("Error initializing Chainlit", e)
        await cl.Message(content=error_message).send()


@cl.on_chat_resume
async def on_chat_resume(thread: ThreadDict):
    """
    Handles resumption of a previous chat session.
    
    This function:
    1. Retrieves up to 50 most recent messages from the previous thread
    2. Converts them to the appropriate message types (HumanMessage or AIMessage)
    3. Stores them in the user session for context
    4. Initializes a new Chainlit session with this historical context
    
    Args:
        thread (ThreadDict): The thread dictionary containing previous conversation data
        
    Error Handling:
        - Catches and logs any exceptions during chat resumption
        - Sends a user-friendly error message if resumption fails
        
    Note:
        This function ensures that the agent has access to conversation history
        when a user resumes a previous session, maintaining continuity.
    """
    try:
        previous_messages_raw = [m for m in thread["steps"][-50:] if m["type"] in ["user_message", "assistant_message"]]

        previous_messages: List[HumanMessage | AIMessage] = []
        for previous_message_raw in previous_messages_raw:
            if len(previous_message_raw["output"]) == 0:
                continue

            if previous_message_raw["type"] == "user_message":
                previous_messages.append(HumanMessage(content=previous_message_raw["output"]))
            elif previous_message_raw["type"] == "assistant_message":
                previous_messages.append(AIMessage(content=previous_message_raw["output"]))

        cl.user_session.set("previous_messages", previous_messages)

        await init_chainlit()

    except Exception as e:
        error_message = handle_error("Error resuming chat", e)
        await cl.Message(content=error_message).send()


@cl.on_chat_start
async def start():
    """
    Initializes a new chat session when a user starts a conversation.
    
    This function is triggered when a user begins a new chat with the system.
    It calls init_chainlit() to set up all necessary session parameters and
    initialize the agent for the conversation.
    
    No previous context is loaded since this is a fresh conversation.
    
    Note:
        This is the entry point for new conversations in the Chainlit interface.
    """
    await init_chainlit()
