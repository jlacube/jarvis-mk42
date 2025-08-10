import asyncio
from typing import Any

from langchain_core.messages import HumanMessage
from langchain_core.runnables import RunnableConfig
from langchain_core.tools import tool
from langchain_core.tracers import ConsoleCallbackHandler
from langgraph.graph.state import CompiledStateGraph

from agents.reasoning_model_agent import get_reasoning_model_agent

# Simple call stack tracking to prevent infinite recursion
_call_stack = set()

@tool
async def reasoning_model_tool(query: str) -> str:
    """Call a reasoning agent to perform deep thinking, deep analysis

    :param query: query of the user or the supervisor agent
    :return: steps that will need to happen to solve the problem
    """
    # Get current task to create a unique identifier for this call
    try:
        current_task = asyncio.current_task()
        task_id = id(current_task) if current_task else 0
        call_id = f"reasoning_model_tool_{task_id}_{query[:50]}"
        
        # Check for circular calls
        if call_id in _call_stack:
            return "Error: Circular call detected in reasoning_model_tool. The reasoning model agent should not call reasoning_model_tool to prevent infinite loops."
        
        # Add this call to the stack
        _call_stack.add(call_id)
        
        try:
            agent:CompiledStateGraph = await get_reasoning_model_agent()
            inputs = {"messages": [HumanMessage(content=query)]}
            res = await agent.ainvoke(input=inputs)
            return res["messages"][-1].content
        finally:
            # Remove from call stack when done
            _call_stack.discard(call_id)
            
    except Exception as e:
        _call_stack.discard(call_id if 'call_id' in locals() else None)
        return f"Error in reasoning_model_tool: {str(e)}"