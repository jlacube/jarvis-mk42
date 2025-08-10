# agents/reasoning_model_agent.py
from langchain_core.prompts import PromptTemplate
from langgraph.graph.state import CompiledStateGraph
from langgraph.prebuilt import create_react_agent

from agent_management import get_allowed_tools_from_env, get_all_tools
from models.models import get_openai_model, get_google_model
from prompts import get_prompt
# from tools.reasoning_tools import sequential_thinking_tool, generate_summary, clear_history # No longer directly used
# from tools.research_tools import get_research_tools # No longer directly used

import chainlit as cl


async def get_reasoning_model_agent() -> CompiledStateGraph:
    agent_name = "Reasoning_Model_Agent"  # Define the agent name
    allowed_tools = get_allowed_tools_from_env(agent_name)  # Get allowed tools from .env
    tools = get_all_tools(allowed_tools)  # Load only allowed tools

    prompt_template = PromptTemplate(template=get_prompt("reasoning_model_agent"),
                                     input_variables=["now", "user_id", "session_id", "user_name", "thread_id"])

    # Try to get Chainlit user session data, fallback to defaults if not available
    try:
        now = cl.user_session.get("now", "Unknown time")
        user_id = cl.user_session.get("user_id", "unknown_user")
        session_id = cl.user_session.get("session_id", "unknown_session")
        user_name = cl.user_session.get("user_name", "Unknown User")
        thread_id = cl.user_session.get("thread_id", "unknown_thread")
    except Exception:
        # Fallback values when Chainlit context is not available
        from datetime import datetime
        now = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        user_id = "test_user"
        session_id = "test_session"
        user_name = "Test User"
        thread_id = "test_thread"

    prompt = prompt_template.invoke(input=dict([
        ("now", now),
        ("user_id", user_id),
        ("session_id", session_id),
        ("user_name", user_name),
        ("thread_id", thread_id)
    ]))

    agent = create_react_agent(
        name="Reasoning_Model_Agent",
        # model=get_openai_model(streaming=False),
        model=get_google_model(streaming=False),
        tools=tools, # Pass the filtered tools
        prompt=str(prompt)
    )

    return agent
