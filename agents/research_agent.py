# agents/research_agent.py
from langgraph.prebuilt import create_react_agent

from models.models import get_openai_model, get_google_model
from prompts import get_prompt
from agent_management import get_all_tools, get_allowed_tools_from_env

async def get_research_agent():
    """
    Creates and returns a research agent with appropriate tools and model.
    
    This function:
    1. Defines a research agent with a specific name
    2. Retrieves the list of allowed tools from environment variables
    3. Loads only the tools allowed for this agent
    4. Creates a ReAct agent using the Google model and research prompt
    
    Returns:
        Agent: A configured ReAct agent ready to handle research tasks
        
    Note:
        The agent uses a non-streaming model to ensure complete responses
        for research queries.
    """
    agent_name = "Research_Agent" # Define the agent name
    allowed_tools = get_allowed_tools_from_env(agent_name) # Get allowed tools from .env
    tools = get_all_tools(allowed_tools) # Load only allowed tools

    agent = create_react_agent(
        name=agent_name,
        model=get_google_model(streaming=False),
        tools=tools,
        prompt=str(get_prompt("research_agent"))
    )

    return agent