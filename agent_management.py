# agent_management.py
import logging
import importlib
import os
import pkgutil
import inspect
from datetime import datetime

import chainlit as cl
from langchain_core.tools import StructuredTool, BaseTool
from langgraph.prebuilt import create_react_agent
from config import JARVIS_NAME
from models.models import get_google_model
from utils import load_prompt, handle_error
from langgraph.checkpoint.memory import MemorySaver

logger = logging.getLogger(__name__)

# Define the package where tools are located
TOOLS_PACKAGE = "tools"

def get_allowed_tools_from_env(agent_name: str) -> list[str] | None:
    """
    Reads the allowed tool list from the .env file for a given agent.
    Returns None if no tool list is specified or if the .env file is missing.
    """
    tool_list_str = os.getenv(f"{agent_name.upper()}_ALLOWED_TOOLS")
    if tool_list_str:
        return [tool.strip() for tool in tool_list_str.split(",")]
    return None

def get_all_tools(allowed_tools: list[str] | None = None) -> list[BaseTool]:
    """
    Dynamically discovers and loads tools from the 'tools' package.
    If allowed_tools is specified, only those tools are loaded.
    """
    tools = []
    try:
        package = importlib.import_module(TOOLS_PACKAGE)

        for _, module_name, is_pkg in pkgutil.walk_packages(package.__path__, package.__name__ + "."):
            try:
                module = importlib.import_module(module_name)

                for name, obj in inspect.getmembers(module):
                    if name == 'cl':
                        continue

                    if isinstance(obj, BaseTool):
                        if allowed_tools is None or name in allowed_tools:
                            tools.append(obj)
                            logger.info(f"Loaded tool: {name} from module {module_name}")
                        else:
                            logger.info(f"Tool {name} from module {module_name} is not allowed and will not be loaded.")

            except ImportError as e:
                logger.warning(f"Could not import module {module_name}: {e}")
            except Exception as e:
                logger.error(f"Error loading tools from module {module_name}: {e}")

    except ImportError as e:
        logger.error(f"Could not import tools package {TOOLS_PACKAGE}: {e}")
    except Exception as e:
        logger.error(f"Error loading tools: {e}")

    if not tools:
        logger.warning("No tools were loaded. Check the tools package and its modules.")

    return tools


async def create_agent(prompt: str, agent_name: str = JARVIS_NAME) -> any:
    """Creates the agent."""
    try:
        model = get_google_model()
        allowed_tools = get_allowed_tools_from_env(agent_name)
        tools = get_all_tools(allowed_tools)
        app = create_react_agent(
            name=JARVIS_NAME,
            model=model,
            tools=tools,
            prompt=prompt,
            checkpointer=MemorySaver()
        )
        return app
    except Exception as e:
        error_message = handle_error("Error creating agent", e)
        await cl.Message(content=error_message).send()
        return None


async def initialize_agent(now: datetime, user_id: str, session_id: str, user_name: str, thread_id: str):
    """Initializes the agent."""
    try:
        from config import SUPERVISOR_PROMPT_NAME  # Import here to avoid circular dependency
        prompt_kwargs = {
            "now": now,
            "user_id": user_id,
            "session_id": session_id,
            "user_name": user_name,
            "thread_id": thread_id
        }
        prompt = load_prompt(SUPERVISOR_PROMPT_NAME, **prompt_kwargs)
        app = await create_agent(prompt)
        return app
    except Exception as e:
        error_message = handle_error("Error initializing agent", e)
        await cl.Message(content=error_message).send()
        return None
