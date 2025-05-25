# agent_management.py
import logging
import importlib
import os
import pkgutil
import inspect
from datetime import datetime

import chainlit as cl
from langchain_core.tools import BaseTool
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
    
    This function checks for environment variables in the format "{AGENT_NAME}_ALLOWED_TOOLS"
    and parses the comma-separated list of tool names.
    
    Args:
        agent_name (str): The name of the agent to get allowed tools for
                          (will be converted to uppercase for env var matching)
                          
    Returns:
        list[str]: A list of allowed tool names if specified in environment
        None: If no tool list is specified or if the .env file is missing
        
    Example:
        If .env contains: RESEARCH_AGENT_ALLOWED_TOOLS=google_search_tool,webpage_research_tool
        Then get_allowed_tools_from_env("Research_Agent") returns:
        ["google_search_tool", "webpage_research_tool"]
    """
    tool_list_str = os.getenv(f"{agent_name.upper()}_ALLOWED_TOOLS")
    if tool_list_str:
        return [tool.strip() for tool in tool_list_str.split(",")]
    return None

def get_all_tools(allowed_tools: list[str], user_name: str) -> list[BaseTool]:
    """
    Dynamically discovers and loads tools from the 'tools' package.
    
    This function scans the tools package and its modules, finding all tools
    that are instances of BaseTool. It filters the tools based on the allowed_tools
    list if provided, and applies user-specific restrictions.
    
    Args:
        allowed_tools (list[str]): List of tool names to load. If None, all tools are loaded.
        user_name (str): The username, used for authorization of restricted tools
        
    Returns:
        list[BaseTool]: List of instantiated tool objects ready for use by an agent
        
    Note:
        - Some tools may have user-specific restrictions (e.g., video_tool)
        - The function logs information about loaded and excluded tools
    """
    tools = []
    try:
        # Try to add the current directory to sys.path if it's not already there
        import sys
        import os
        current_dir = os.path.dirname(os.path.abspath(__file__))
        if current_dir not in sys.path:
            sys.path.insert(0, current_dir)
            
        package = importlib.import_module(TOOLS_PACKAGE)

        for _, module_name, is_pkg in pkgutil.walk_packages(package.__path__, package.__name__ + "."):
            try:
                module = importlib.import_module(module_name)

                for name, obj in inspect.getmembers(module):
                    if name == 'cl':
                        continue

                    if isinstance(obj, BaseTool):
                        if allowed_tools is None or name in allowed_tools:
                            if obj.name == 'video_tool':
                                if user_name == 'jerome':
                                    tools.append(obj)
                                    logger.info(f"Loaded tool: {name} from module {module_name} - allowed for user {user_name}")
                                else:
                                    logger.warning(f"Tool excluded: {obj.name} for user {user_name}")
                            else:
                                tools.append(obj)
                                logger.info(f"Loaded tool: {name} from module {module_name} - allowed for user {user_name}")
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


async def create_agent(prompt: str, user_name: str = "", agent_name: str = JARVIS_NAME) -> any:
    """
    Creates an agent with the specified prompt and tools.
    
    This function sets up a React agent with the appropriate model, tools, and prompt.
    It uses a memory-based checkpointer to maintain state across interactions.
    
    Args:
        prompt (str): The system prompt to use for the agent
        user_name (str, optional): The username, used for tool access control. Defaults to "".
        agent_name (str, optional): The name to assign to the agent. Defaults to JARVIS_NAME.
        
    Returns:
        any: The created agent instance, or None if an error occurs
        
    Error Handling:
        - Catches and logs all exceptions during agent creation
        - Sends an error message to the user via Chainlit if an error occurs
    """
    try:
        model = get_google_model()
        allowed_tools = get_allowed_tools_from_env(agent_name)
        tools = get_all_tools(allowed_tools, user_name)
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
    """
    Initializes the agent with user-specific context.
    
    This function creates an agent with a personalized prompt that includes the current 
    datetime, user information, and session context.
    
    Args:
        now (datetime): The current datetime
        user_id (str): The user's unique identifier
        session_id (str): The current session identifier
        user_name (str): The user's name
        thread_id (str): The current conversation thread identifier
        
    Returns:
        any: The initialized agent instance, or None if an error occurs
        
    Note:
        - Imports SUPERVISOR_PROMPT_NAME inside the function to avoid circular dependencies
        - Uses load_prompt to format the supervisor prompt with contextual information
    """
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
        app = await create_agent(prompt, user_name)
        return app
    except Exception as e:
        error_message = handle_error("Error initializing agent", e)
        await cl.Message(content=error_message).send()
        return None
