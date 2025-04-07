import shutil

from langchain_core.messages import HumanMessage, AIMessage
from langchain_core.tools import tool
from langgraph.graph.graph import CompiledGraph

from agents.coding_agent import get_coding_agent
from agents.reasoning_agent import get_reasoning_agent
from agents.research_agent import get_research_agent

import chainlit as cl

def is_installed(lib_name: str) -> bool:
    lib = shutil.which(lib_name)
    if lib is None:
        return False
    return True


@tool
async def research_tool(query: str) -> str:
    """Call a research agent to perform researches on the Internet

    :param query: query of the user or the supervisor agent
    :return: searches' results
    """
    agent:CompiledGraph = await get_research_agent()
    inputs = {"messages": [HumanMessage(content=query)]}

    res = await agent.ainvoke(input=inputs)

    return res["messages"][-1].content


@tool
async def reasoning_tool(query: str) -> str:
    """Call a reasoning agent to perform deep thinking, deep analysis

    :param query: query of the user or the supervisor agent
    :return: steps that will need to happen to solve the problem
    """
    agent:CompiledGraph = await get_reasoning_agent()
    inputs = {"messages": [HumanMessage(content=query)]}

    #res = await agent.ainvoke(input=inputs, config=RunnableConfig(callbacks=[ConsoleCallbackHandler(),cl.AsyncLangchainCallbackHandler()]), stream_mode="values")
    res = await agent.ainvoke(input=inputs)

    return res["messages"][-1].content

@tool
async def coding_tool(query: str) -> str:
    """Call a coding agent to perform all sorts of tasks around coding

    :param query: query of the user or the supervisor agent
    :return: code blocks or file blocks, along with explanations
    """
    agent:CompiledGraph = await get_coding_agent()
    inputs = {"messages": [HumanMessage(content=query)]}

    res = await agent.ainvoke(input=inputs)

    messages = res["messages"]

    if len(messages) > 2:
        for msg in messages[1:-1]:
            if isinstance(msg, AIMessage):
                await cl.Message(author="Coding Agent", content="\n".join(msg.content)).send()

    return "\n".join(messages[-1].content)

