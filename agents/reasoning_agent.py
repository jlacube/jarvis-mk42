# agents/reasoning_agent.py
from langchain_core.prompts import PromptTemplate
from langgraph.graph.graph import CompiledGraph
from langgraph.prebuilt import create_react_agent

from agent_management import get_allowed_tools_from_env, get_all_tools
from models.models import get_openai_model, get_google_model
from prompts import get_prompt
from tools.reasoning_model_tool import reasoning_model_tool
from tools.reasoning_tools import sequential_thinking_tool, generate_summary, clear_history
from tools.research_tools import get_research_tools # Import needed because used in the tools list

import chainlit as cl


async def get_reasoning_agent() -> CompiledGraph:
    agent_name = "Reasoning_Agent"  # Define the agent name
    allowed_tools = get_allowed_tools_from_env(agent_name)  # Get allowed tools from .env

    # Filter the explicitly listed tools based on allowed_tools
    explicitly_listed_tools = [sequential_thinking_tool, generate_summary, clear_history, reasoning_model_tool]
    filtered_explicitly_listed_tools = [tool for tool in explicitly_listed_tools if tool.name in (allowed_tools or [])]

    # Get research tools and filter them based on allowed_tools
    research_tools = get_research_tools()
    filtered_research_tools = [tool for tool in research_tools if tool.name in (allowed_tools or [])]

    # Combine the filtered tools
    tools = filtered_explicitly_listed_tools + filtered_research_tools

    prompt_template = PromptTemplate(template=get_prompt("reasoning_agent"),
                                     input_variables=["now", "user_id", "session_id", "user_name", "thread_id"])

    now = cl.user_session.get("now")
    user_id = cl.user_session.get("user_id")
    session_id = cl.user_session.get("session_id")
    user_name = cl.user_session.get("user_name")
    thread_id = cl.user_session.get("thread_id")

    prompt = prompt_template.invoke(input=dict([
        ("now", now),
        ("user_id", user_id),
        ("session_id", session_id),
        ("user_name", user_name),
        ("thread_id", thread_id)
    ]))

    agent = create_react_agent(
        name="Reasoning_Agent",
        # model=get_openai_model(streaming=False),
        model=get_google_model(streaming=False),
        # tools=[reasoning_model_tool],
        tools=tools,
        prompt=str(prompt)
    )

    return agent
