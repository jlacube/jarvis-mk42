# agent_management.py
import logging
import importlib
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


def get_all_tools():
    """Dynamically discovers and loads all available tools from the 'tools' package,
    only including functions decorated with @tool.
    """
    tools = []
    try:
        # Get the package object
        package = importlib.import_module(TOOLS_PACKAGE)

        # Iterate through all modules in the package
        for _, module_name, is_pkg in pkgutil.walk_packages(package.__path__, package.__name__ + "."):
            try:
                module = importlib.import_module(module_name)

                # Iterate through all objects in the module
                for name, obj in inspect.getmembers(module):
                    if name == 'cl':
                        continue

                    # Check if the object is a function and doesn't start with an underscore
                    if isinstance(obj, BaseTool):
                        tools.append(obj)
                        logger.info(f"Loaded tool: {name} from module {module_name}")
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


async def create_agent(prompt: str):
    """Creates the agent."""
    try:
        model = get_google_model()
        tools = get_all_tools()
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
