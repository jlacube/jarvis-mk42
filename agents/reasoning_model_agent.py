from langgraph.graph.graph import CompiledGraph
from langgraph.prebuilt import create_react_agent

from models.models import get_openai_reasoning_model, get_google_reasoning_model
from prompts import get_prompt
from tools.research_tools import get_research_tools


async def get_reasoning_model_agent() -> CompiledGraph:
    agent = create_react_agent(
        name="Reasoning_Model_Agent",
        model=get_google_reasoning_model(streaming=False),
        tools=get_research_tools(),
        prompt=str(get_prompt("reasoning_model_agent"))
    )

    return agent