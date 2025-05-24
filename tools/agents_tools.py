from langchain_core.messages import HumanMessage, AIMessage
from langchain_core.tools import tool
from langgraph.graph.graph import CompiledGraph

from agents.coding_agent import get_coding_agent
from agents.reasoning_agent import get_reasoning_agent
from agents.research_agent import get_research_agent

import chainlit as cl

@tool
async def research_tool(query: str) -> str:
    """
    Invokes a specialized research agent to perform internet-based research.
    
    This tool creates and invokes a research agent that can search the internet,
    analyze information from multiple sources, and synthesize a comprehensive
    response to research queries.
    
    Args:
        query (str): The research question or topic to investigate. This can be
                    from the user directly or from the supervisor agent.
                    
    Returns:
        str: Detailed research findings including facts, analysis, and source citations.
        
    Implementation Details:
        - Creates a new research agent instance for each invocation
        - Formats the query as a HumanMessage for the agent
        - Extracts and returns the final response from the agent's output
        
    Example:
        result = await research_tool("What are the latest developments in quantum computing?")
    """
    agent:CompiledGraph = await get_research_agent()
    inputs = {"messages": [HumanMessage(content=query)]}

    res = await agent.ainvoke(input=inputs)

    return res["messages"][-1].content


@tool
async def reasoning_tool(query: str) -> str:
    """
    Invokes a specialized reasoning agent for deep analysis and problem-solving.
    
    This tool creates and invokes a reasoning agent that can break down complex problems,
    analyze scenarios step-by-step, identify logical connections, and develop
    structured approaches to solving challenging questions.
    
    Args:
        query (str): The problem or question requiring analysis. This can be
                    from the user directly or from the supervisor agent.
                    
    Returns:
        str: A detailed analysis including problem decomposition, step-by-step reasoning,
             logical inferences, and potential solutions.
        
    Implementation Details:
        - Creates a new reasoning agent instance for each invocation
        - Formats the query as a HumanMessage for the agent
        - Extracts and returns the final reasoned response from the agent's output
        
    Example:
        result = await reasoning_tool("How should we approach designing a sustainable urban transportation system?")
    """
    agent:CompiledGraph = await get_reasoning_agent()
    inputs = {"messages": [HumanMessage(content=query)]}

    #res = await agent.ainvoke(input=inputs, config=RunnableConfig(callbacks=[ConsoleCallbackHandler(),cl.AsyncLangchainCallbackHandler()]), stream_mode="values")
    res = await agent.ainvoke(input=inputs)

    return res["messages"][-1].content

@tool
async def coding_tool(query: str) -> str:
    """
    Invokes a specialized coding agent to assist with software development tasks.
    
    This tool creates and invokes a coding agent that can write code, debug issues,
    refactor existing code, explain programming concepts, and provide guidance on
    software development best practices across various programming languages.
    
    Args:
        query (str): The coding question, task description, or code snippet requiring
                    assistance. This can be from the user directly or from the
                    supervisor agent.
                    
    Returns:
        str: A response containing code blocks, explanations, and/or file content
             formatted with appropriate markdown and syntax highlighting.
        
    Implementation Details:
        - Creates a new coding agent instance for each invocation
        - Formats the query as a HumanMessage for the agent
        - Extracts and returns the final code solution from the agent's output
        - Response typically includes both code and explanatory text
        
    Capabilities:
        - Writing new code in various programming languages
        - Debugging and fixing errors in existing code
        - Refactoring code for improved performance or readability
        - Explaining programming concepts and techniques
        - Suggesting best practices and design patterns
        
    Example:
        result = await coding_tool("Write a Python function to find prime numbers up to n")
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