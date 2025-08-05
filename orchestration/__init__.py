# orchestration/__init__.py
"""
Multi-Agent Orchestration System
================================

This package provides the core orchestration infrastructure for Jarvis-MK42's
multi-agent system. It includes:

- Workflow Engine: LangGraph-based workflow management and execution
- Task Planner: Intelligent task decomposition and planning
- Agent Coordinator: Inter-agent communication and coordination
- State Manager: Shared state and context management
- Error Handler: Comprehensive error recovery and fallback strategies

The orchestration system enables sophisticated multi-agent workflows that can
handle complex tasks requiring collaboration between specialized agents.
"""

from .workflow_engine import WorkflowEngine, WorkflowTemplate, WorkflowExecution
from .task_planner import TaskPlanner, TaskPlan, SubTask
from .agent_coordinator import AgentCoordinator, AgentRegistry, AgentStatus

__all__ = [
    "WorkflowEngine",
    "WorkflowTemplate", 
    "WorkflowExecution",
    "TaskPlanner",
    "TaskPlan",
    "SubTask",
    "AgentCoordinator",
    "AgentRegistry",
    "AgentStatus"
]

__version__ = "1.0.0"
