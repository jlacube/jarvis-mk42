# agents/research_agent.py
from langgraph.prebuilt import create_react_agent

from models.models import get_openai_model, get_google_model
from prompts import get_prompt
#from tools.research_tools import get_research_tools # No longer needed
from agent_management import get_all_tools, get_allowed_tools_from_env # Import from agent_management

async def get_research_agent():
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