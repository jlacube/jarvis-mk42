# orchestration/workflow_engine.py
"""
Workflow Engine for Multi-Agent Orchestration
==============================================

This module provides the core workflow execution engine using LangGraph.
It manages the creation, execution, and monitoring of multi-agent workflows
with support for:

- Dynamic workflow construction based on task requirements
- State management and persistence across workflow steps
- Error recovery and fallback mechanisms  
- Real-time workflow monitoring and debugging
- Template-based workflow reuse and customization
"""

import logging
import uuid
from datetime import datetime, timedelta
from typing import Dict, List, Optional, Any, Callable, Union
from dataclasses import dataclass, field
from enum import Enum

from pydantic import BaseModel, Field
from langchain_core.messages import BaseMessage, HumanMessage, AIMessage, SystemMessage
from langgraph.graph import StateGraph, START, END
from langgraph.checkpoint.memory import MemorySaver
from langgraph.checkpoint.base import BaseCheckpointSaver
from langgraph.types import Send

from utils.logging_config import get_logger
from utils.exceptions import WorkflowError, AgentError

logger = get_logger(__name__)


class WorkflowStatus(Enum):
    """Enumeration of workflow execution statuses."""
    CREATED = "created"
    PLANNING = "planning" 
    EXECUTING = "executing"
    PAUSED = "paused"
    COMPLETED = "completed"
    FAILED = "failed"
    CANCELLED = "cancelled"


class NodeType(Enum):
    """Types of nodes in a workflow."""
    ORCHESTRATOR = "orchestrator"
    AGENT = "agent"
    TOOL = "tool"
    CONDITION = "condition"
    AGGREGATOR = "aggregator"
    SYNTHESIZER = "synthesizer"


@dataclass
class WorkflowNode:
    """Definition of a workflow node."""
    id: str
    name: str
    node_type: NodeType
    function: Callable
    dependencies: List[str] = field(default_factory=list)
    metadata: Dict[str, Any] = field(default_factory=dict)


@dataclass 
class WorkflowEdge:
    """Definition of a workflow edge."""
    from_node: str
    to_node: str
    condition: Optional[Callable] = None
    metadata: Dict[str, Any] = field(default_factory=dict)


class WorkflowTemplate(BaseModel):
    """Template for reusable workflow patterns."""
    id: str = Field(description="Unique template identifier")
    name: str = Field(description="Human-readable template name")
    description: str = Field(description="Template description and use cases")
    nodes: List[Dict[str, Any]] = Field(description="Node definitions")
    edges: List[Dict[str, Any]] = Field(description="Edge definitions")
    parameters: Dict[str, Any] = Field(default_factory=dict, description="Template parameters")
    created_at: datetime = Field(default_factory=datetime.now)
    version: str = Field(default="1.0.0")


class WorkflowExecution(BaseModel):
    """Track execution of a workflow instance."""
    id: str = Field(description="Unique execution identifier")
    template_id: Optional[str] = Field(default=None, description="Template used for this execution")
    status: WorkflowStatus = Field(default=WorkflowStatus.CREATED)
    created_at: datetime = Field(default_factory=datetime.now)
    started_at: Optional[datetime] = None
    completed_at: Optional[datetime] = None
    input_data: Dict[str, Any] = Field(default_factory=dict)
    output_data: Dict[str, Any] = Field(default_factory=dict)
    current_node: Optional[str] = None
    execution_history: List[Dict[str, Any]] = Field(default_factory=list)
    error_messages: List[str] = Field(default_factory=list)
    metadata: Dict[str, Any] = Field(default_factory=dict)


class WorkflowEngine:
    """
    Core workflow engine for multi-agent orchestration.
    
    This class provides the foundation for creating, executing, and managing
    complex multi-agent workflows using LangGraph. It supports:
    
    - Dynamic workflow construction based on task requirements
    - Template-based workflow reuse and customization
    - State management and persistence
    - Error recovery and debugging support
    - Real-time execution monitoring
    """
    
    def __init__(self, checkpointer: Optional[BaseCheckpointSaver] = None):
        """
        Initialize the workflow engine.
        
        Args:
            checkpointer: Optional checkpointer for state persistence
        """
        self.checkpointer = checkpointer or MemorySaver()
        self.templates: Dict[str, WorkflowTemplate] = {}
        self.executions: Dict[str, WorkflowExecution] = {}
        self.active_workflows: Dict[str, Any] = {}
        
        logger.info("Workflow engine initialized")
    
    def register_template(self, template: WorkflowTemplate) -> None:
        """
        Register a workflow template for reuse.
        
        Args:
            template: The workflow template to register
        """
        try:
            self.templates[template.id] = template
            logger.info("Registered workflow template: %s", template.name)
            
        except Exception as e:
            logger.error("Error registering template %s: %s", template.name, str(e))
            raise WorkflowError(f"Failed to register template: {str(e)}")
    
    def create_workflow(
        self,
        nodes: List[WorkflowNode],
        edges: List[WorkflowEdge],
        state_schema: type,
        execution_id: Optional[str] = None
    ) -> str:
        """
        Create a new workflow from nodes and edges.
        
        Args:
            nodes: List of workflow nodes
            edges: List of workflow edges  
            state_schema: State schema for the workflow
            execution_id: Optional custom execution ID
            
        Returns:
            Execution ID for the created workflow
        """
        try:
            if execution_id is None:
                execution_id = str(uuid.uuid4())
            
            # Create workflow execution record
            execution = WorkflowExecution(
                id=execution_id,
                status=WorkflowStatus.CREATED,
                input_data={}
            )
            self.executions[execution_id] = execution
            
            # Build LangGraph workflow
            workflow = StateGraph(state_schema)
            
            # Add nodes
            for node in nodes:
                workflow.add_node(node.id, node.function)
                logger.debug("Added node: %s (%s)", node.name, node.node_type.value)
            
            # Add edges
            for edge in edges:
                # Handle START and END as special LangGraph constants
                from_node = START if edge.from_node == "START" else edge.from_node
                to_node = END if edge.to_node == "END" else edge.to_node
                
                if edge.condition:
                    # Conditional edge
                    workflow.add_conditional_edges(
                        from_node,
                        edge.condition,
                        {to_node: to_node}
                    )
                else:
                    # Regular edge
                    workflow.add_edge(from_node, to_node)
                
                logger.debug("Added edge: %s -> %s", edge.from_node, edge.to_node)
            
            # Compile workflow
            compiled_workflow = workflow.compile(checkpointer=self.checkpointer)
            self.active_workflows[execution_id] = compiled_workflow
            
            logger.info("Created workflow with execution ID: %s", execution_id)
            return execution_id
            
        except Exception as e:
            logger.error("Error creating workflow: %s", str(e))
            raise WorkflowError(f"Failed to create workflow: {str(e)}")
    
    def create_from_template(
        self,
        template_id: str,
        parameters: Dict[str, Any],
        execution_id: Optional[str] = None
    ) -> str:
        """
        Create a workflow from a registered template.
        
        Args:
            template_id: ID of the template to use
            parameters: Parameters to customize the template
            execution_id: Optional custom execution ID
            
        Returns:
            Execution ID for the created workflow
        """
        try:
            if template_id not in self.templates:
                raise WorkflowError(f"Template not found: {template_id}")
            
            template = self.templates[template_id]
            
            if execution_id is None:
                execution_id = str(uuid.uuid4())
            
            # Create execution record
            execution = WorkflowExecution(
                id=execution_id,
                template_id=template_id,
                status=WorkflowStatus.CREATED,
                input_data=parameters
            )
            self.executions[execution_id] = execution
            
            # TODO: Implement template instantiation with parameters
            # This would involve parsing the template nodes/edges and
            # substituting parameters as needed
            
            logger.info("Created workflow from template %s: %s", template.name, execution_id)
            return execution_id
            
        except Exception as e:
            logger.error("Error creating workflow from template: %s", str(e))
            raise WorkflowError(f"Failed to create workflow from template: {str(e)}")
    
    async def execute_workflow(
        self,
        execution_id: str,
        input_data: Dict[str, Any],
        config: Optional[Dict[str, Any]] = None
    ) -> Dict[str, Any]:
        """
        Execute a workflow asynchronously.
        
        Args:
            execution_id: ID of the workflow execution
            input_data: Input data for the workflow
            config: Optional execution configuration
            
        Returns:
            Workflow output data
        """
        try:
            if execution_id not in self.executions:
                raise WorkflowError(f"Execution not found: {execution_id}")
            
            if execution_id not in self.active_workflows:
                raise WorkflowError(f"Workflow not compiled: {execution_id}")
            
            execution = self.executions[execution_id]
            workflow = self.active_workflows[execution_id]
            
            # Update execution status
            execution.status = WorkflowStatus.EXECUTING
            execution.started_at = datetime.now()
            execution.input_data.update(input_data)
            
            logger.info("Starting workflow execution: %s", execution_id)
            
            # Execute workflow
            config_dict = config or {}
            config_dict["configurable"] = config_dict.get("configurable", {})
            config_dict["configurable"]["thread_id"] = execution_id
            
            result = await workflow.ainvoke(input_data, config=config_dict)
            
            # Update execution record
            execution.status = WorkflowStatus.COMPLETED
            execution.completed_at = datetime.now()
            execution.output_data = result
            
            logger.info("Completed workflow execution: %s", execution_id)
            return result
            
        except Exception as e:
            logger.error("Error executing workflow %s: %s", execution_id, str(e))
            
            # Update execution record with error
            if execution_id in self.executions:
                execution = self.executions[execution_id]
                execution.status = WorkflowStatus.FAILED
                execution.error_messages.append(str(e))
                execution.completed_at = datetime.now()
            
            raise WorkflowError(f"Workflow execution failed: {str(e)}")
    
    def get_execution_status(self, execution_id: str) -> Optional[WorkflowExecution]:
        """
        Get the status of a workflow execution.
        
        Args:
            execution_id: ID of the workflow execution
            
        Returns:
            WorkflowExecution object or None if not found
        """
        return self.executions.get(execution_id)
    
    def pause_workflow(self, execution_id: str) -> bool:
        """
        Pause a running workflow.
        
        Args:
            execution_id: ID of the workflow execution
            
        Returns:
            True if paused successfully, False otherwise
        """
        try:
            if execution_id not in self.executions:
                return False
            
            execution = self.executions[execution_id]
            if execution.status == WorkflowStatus.EXECUTING:
                execution.status = WorkflowStatus.PAUSED
                logger.info("Paused workflow execution: %s", execution_id)
                return True
            
            return False
            
        except Exception as e:
            logger.error("Error pausing workflow %s: %s", execution_id, str(e))
            return False
    
    def resume_workflow(self, execution_id: str) -> bool:
        """
        Resume a paused workflow.
        
        Args:
            execution_id: ID of the workflow execution
            
        Returns:
            True if resumed successfully, False otherwise
        """
        try:
            if execution_id not in self.executions:
                return False
            
            execution = self.executions[execution_id]
            if execution.status == WorkflowStatus.PAUSED:
                execution.status = WorkflowStatus.EXECUTING
                logger.info("Resumed workflow execution: %s", execution_id)
                return True
            
            return False
            
        except Exception as e:
            logger.error("Error resuming workflow %s: %s", execution_id, str(e))
            return False
    
    def cancel_workflow(self, execution_id: str) -> bool:
        """
        Cancel a workflow execution.
        
        Args:
            execution_id: ID of the workflow execution
            
        Returns:
            True if cancelled successfully, False otherwise
        """
        try:
            if execution_id not in self.executions:
                return False
            
            execution = self.executions[execution_id]
            if execution.status in [WorkflowStatus.EXECUTING, WorkflowStatus.PAUSED]:
                execution.status = WorkflowStatus.CANCELLED
                execution.completed_at = datetime.now()
                logger.info("Cancelled workflow execution: %s", execution_id)
                return True
            
            return False
            
        except Exception as e:
            logger.error("Error cancelling workflow %s: %s", execution_id, str(e))
            return False
    
    def cleanup_completed_workflows(self, max_age_hours: int = 24) -> int:
        """
        Clean up completed workflow executions older than the specified age.
        
        Args:
            max_age_hours: Maximum age in hours for completed workflows
            
        Returns:
            Number of workflows cleaned up
        """
        try:
            cutoff_time = datetime.now() - timedelta(hours=max_age_hours)
            cleanup_count = 0
            
            executions_to_remove = []
            for execution_id, execution in self.executions.items():
                if (execution.status in [WorkflowStatus.COMPLETED, WorkflowStatus.FAILED, WorkflowStatus.CANCELLED]
                    and execution.completed_at 
                    and execution.completed_at < cutoff_time):
                    executions_to_remove.append(execution_id)
            
            for execution_id in executions_to_remove:
                del self.executions[execution_id]
                if execution_id in self.active_workflows:
                    del self.active_workflows[execution_id]
                cleanup_count += 1
            
            if cleanup_count > 0:
                logger.info("Cleaned up %d completed workflows", cleanup_count)
            
            return cleanup_count
            
        except Exception as e:
            logger.error("Error during workflow cleanup: %s", str(e))
            return 0
    
    def get_workflow_statistics(self) -> Dict[str, Any]:
        """
        Get statistics about workflow executions.
        
        Returns:
            Dictionary containing execution statistics
        """
        try:
            stats = {
                "total_executions": len(self.executions),
                "active_workflows": len(self.active_workflows),
                "registered_templates": len(self.templates),
                "status_breakdown": {},
                "average_execution_time": None,
                "success_rate": 0.0
            }
            
            # Calculate status breakdown
            for execution in self.executions.values():
                status = execution.status.value
                stats["status_breakdown"][status] = stats["status_breakdown"].get(status, 0) + 1
            
            # Calculate average execution time and success rate
            completed_executions = [
                e for e in self.executions.values() 
                if e.status in [WorkflowStatus.COMPLETED, WorkflowStatus.FAILED]
                and e.started_at and e.completed_at
            ]
            
            if completed_executions:
                total_time = sum(
                    (e.completed_at - e.started_at).total_seconds()
                    for e in completed_executions
                )
                stats["average_execution_time"] = total_time / len(completed_executions)
                
                successful_executions = len([
                    e for e in completed_executions 
                    if e.status == WorkflowStatus.COMPLETED
                ])
                stats["success_rate"] = successful_executions / len(completed_executions)
            
            return stats
            
        except Exception as e:
            logger.error("Error calculating workflow statistics: %s", str(e))
            return {"error": str(e)}


# Common workflow templates
def create_simple_agent_template() -> WorkflowTemplate:
    """Create a template for simple agent workflows."""
    return WorkflowTemplate(
        id="simple_agent",
        name="Simple Agent Workflow",
        description="Single agent workflow for straightforward tasks",
        nodes=[
            {
                "id": "agent",
                "name": "Primary Agent",
                "type": "agent",
                "function": "process_request"
            }
        ],
        edges=[
            {
                "from_node": "START",
                "to_node": "agent"
            },
            {
                "from_node": "agent", 
                "to_node": "END"
            }
        ]
    )


def create_orchestrator_worker_template() -> WorkflowTemplate:
    """Create a template for orchestrator-worker workflows."""
    return WorkflowTemplate(
        id="orchestrator_worker",
        name="Orchestrator-Worker Workflow",
        description="Multi-agent workflow with central orchestration",
        nodes=[
            {
                "id": "orchestrator",
                "name": "Orchestrator",
                "type": "orchestrator",
                "function": "plan_and_delegate"
            },
            {
                "id": "synthesizer",
                "name": "Synthesizer",
                "type": "synthesizer", 
                "function": "aggregate_results"
            }
        ],
        edges=[
            {
                "from_node": "START",
                "to_node": "orchestrator"
            },
            {
                "from_node": "orchestrator",
                "to_node": "synthesizer",
                "condition": "route_to_workers_or_synthesizer"
            },
            {
                "from_node": "synthesizer",
                "to_node": "END"
            }
        ]
    )


# Export main classes and functions
__all__ = [
    "WorkflowEngine",
    "WorkflowTemplate", 
    "WorkflowExecution",
    "WorkflowNode",
    "WorkflowEdge",
    "WorkflowStatus",
    "NodeType",
    "create_simple_agent_template",
    "create_orchestrator_worker_template"
]
