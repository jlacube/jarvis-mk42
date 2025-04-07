from langgraph.prebuilt import create_react_agent

from models.models import get_openai_model, get_google_model
from prompts import get_prompt
from tools.research_tools import get_research_tools


async def get_research_agent():
    agent = create_react_agent(
        name="Research_Agent",
        #model=get_openai_model(),
        model=get_google_model(streaming=False),
        tools=get_research_tools(),
        prompt=str(get_prompt("research_agent"))
    )

    return agent