# chainlit_setup.py
import datetime
import logging
import uuid

import chainlit as cl
from chainlit.config import ThreadDict
from langchain_core.messages import HumanMessage, AIMessage
from typing import List, Optional

from agent_management import initialize_agent
from utils import handle_error

logger = logging.getLogger(__name__)


async def init_chainlit():
    """Initializes the Chainlit session."""
    try:
        session_id = str(uuid.uuid4()) if cl.context.session.id is None else cl.context.session.id

        if cl.context.session.user is not None:
            user_id = str(uuid.uuid4()) if cl.context.session.user is None else cl.context.session.user.id
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
    """Resumes a previous chat session."""
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
    """Starts a new chat session."""
    await init_chainlit()
