from typing import Any

from langchain_core.messages import HumanMessage
from langchain_core.runnables import RunnableConfig
from langchain_core.tools import tool
from langchain_core.tracers import ConsoleCallbackHandler
from langgraph.graph.graph import CompiledGraph

from agents.reasoning_model_agent import get_reasoning_model_agent


@tool
async def reasoning_model_tool(query: str) -> str:
    """Call a reasoning agent to perform deep thinking, deep analysis

    :param query: query of the user or the supervisor agent
    :return: steps that will need to happen to solve the problem
    """
    agent:CompiledGraph = await get_reasoning_model_agent()
    inputs = {"messages": [HumanMessage(content=query)]}

    res = await agent.ainvoke(input=inputs)

    return res["messages"][-1].content