# orchestration/task_planner.py
"""
Task Planner for Multi-Agent Orchestration
==========================================

This module provides intelligent task decomposition and planning capabilities
for multi-agent workflows. It analyzes user requests and creates detailed
execution plans that can be executed by the workflow engine.

Key features:
- Automatic task complexity analysis and classification
- Intelligent task decomposition into agent-specific subtasks
- Dependency management and execution ordering
- Dynamic replanning based on intermediate results
- Resource estimation and optimization
"""

import logging
from datetime import datetime, timedelta
from typing import Dict, List, Optional, Any, Set, Tuple
from dataclasses import dataclass, field
from enum import Enum

from pydantic import BaseModel, Field
from langchain_core.messages import HumanMessage, SystemMessage

from agents.supervisor_agent import TaskComplexity, AgentType, TaskAnalysis
from models.models import get_google_model
from utils.logging_config import get_logger
from utils.exceptions import PlanningError

logger = get_logger(__name__)


class SubTaskStatus(Enum):
    """Status of individual subtasks."""
    PENDING = "pending"
    READY = "ready"
    EXECUTING = "executing"
    COMPLETED = "completed"
    FAILED = "failed"
    SKIPPED = "skipped"


class SubTaskPriority(Enum):
    """Priority levels for subtasks."""
    LOW = "low"
    MEDIUM = "medium"
    HIGH = "high"
    CRITICAL = "critical"


@dataclass
class SubTask:
    """Individual subtask within a larger plan."""
    id: str
    name: str
    description: str
    assigned_agent: AgentType
    dependencies: List[str] = field(default_factory=list)
    status: SubTaskStatus = SubTaskStatus.PENDING
    priority: SubTaskPriority = SubTaskPriority.MEDIUM
    estimated_duration: Optional[timedelta] = None
    actual_duration: Optional[timedelta] = None
    input_requirements: Dict[str, Any] = field(default_factory=dict)
    output_specification: Dict[str, Any] = field(default_factory=dict)
    error_messages: List[str] = field(default_factory=list)
    metadata: Dict[str, Any] = field(default_factory=dict)
    created_at: datetime = field(default_factory=datetime.now)
    started_at: Optional[datetime] = None
    completed_at: Optional[datetime] = None


class TaskPlan(BaseModel):
    """Complete execution plan for a user request."""
    id: str = Field(description="Unique plan identifier")
    name: str = Field(description="Human-readable plan name")
    description: str = Field(description="Plan description and objectives")
    user_request: str = Field(description="Original user request")
    complexity: TaskComplexity = Field(description="Overall task complexity")
    subtasks: List[Dict[str, Any]] = Field(description="List of subtasks (serialized)")
    execution_order: List[str] = Field(description="Ordered list of subtask IDs")
    required_agents: List[str] = Field(description="List of required agent types")
    estimated_total_duration: Optional[float] = Field(default=None, description="Estimated duration in seconds")
    success_criteria: List[str] = Field(default_factory=list, description="Criteria for successful completion")
    fallback_strategies: Dict[str, str] = Field(default_factory=dict)
    created_at: datetime = Field(default_factory=datetime.now)
    updated_at: datetime = Field(default_factory=datetime.now)
    version: int = Field(default=1)
    metadata: Dict[str, Any] = Field(default_factory=dict)


class TaskPlanner:
    """
    Intelligent task planner for multi-agent workflows.
    
    This class analyzes user requests and creates detailed execution plans
    that can be executed by specialized agents. It provides:
    
    - Task complexity analysis and classification
    - Intelligent task decomposition
    - Dependency resolution and execution ordering
    - Resource estimation and optimization
    - Dynamic replanning capabilities
    """
    
    def __init__(self):
        """Initialize the task planner."""
        self.model = get_google_model()
        self.plans: Dict[str, TaskPlan] = {}
        self.subtask_templates: Dict[str, Dict[str, Any]] = {}
        
        # Load common subtask templates
        self._initialize_templates()
        
        logger.info("Task planner initialized")
    
    def _initialize_templates(self):
        """Initialize common subtask templates."""
        self.subtask_templates = {
            "research_query": {
                "name": "Research Query",
                "description": "Conduct research on a specific topic or question",
                "agent": AgentType.RESEARCH,
                "input_requirements": {"query": "str", "depth": "optional[str]"},
                "output_specification": {"findings": "str", "sources": "list[str]"},
                "estimated_duration": timedelta(minutes=2)
            },
            "analyze_data": {
                "name": "Analyze Data",
                "description": "Perform analysis on provided data or information",
                "agent": AgentType.REASONING,
                "input_requirements": {"data": "any", "analysis_type": "str"},
                "output_specification": {"analysis": "str", "insights": "list[str]"},
                "estimated_duration": timedelta(minutes=3)
            },
            "generate_code": {
                "name": "Generate Code",
                "description": "Create code based on specifications",
                "agent": AgentType.CODING,
                "input_requirements": {"requirements": "str", "language": "optional[str]"},
                "output_specification": {"code": "str", "explanation": "str"},
                "estimated_duration": timedelta(minutes=5)
            },
            "process_document": {
                "name": "Process Document",
                "description": "Analyze and extract information from documents",
                "agent": AgentType.DOCUMENT_INTELLIGENCE,
                "input_requirements": {"document_path": "str", "extraction_type": "str"},
                "output_specification": {"content": "str", "metadata": "dict"},
                "estimated_duration": timedelta(minutes=2)
            },
            "generate_image": {
                "name": "Generate Image",
                "description": "Create visual content based on specifications",
                "agent": AgentType.MULTIMODAL,
                "input_requirements": {"prompt": "str", "style": "optional[str]"},
                "output_specification": {"image_url": "str", "description": "str"},
                "estimated_duration": timedelta(minutes=1)
            }
        }
    
    async def create_plan(
        self,
        user_request: str,
        context: Dict[str, Any],
        plan_id: Optional[str] = None
    ) -> TaskPlan:
        """
        Create a comprehensive execution plan for a user request.
        
        Args:
            user_request: The user's request or question
            context: Additional context including user info, session data, etc.
            plan_id: Optional custom plan ID
            
        Returns:
            Detailed TaskPlan object
        """
        try:
            if plan_id is None:
                plan_id = f"plan_{datetime.now().strftime('%Y%m%d_%H%M%S')}"
            
            logger.info("Creating plan for request: %s", user_request[:100])
            
            # Analyze task complexity and requirements
            task_analysis = await self._analyze_task_requirements(user_request, context)
            
            # Decompose into subtasks
            subtasks = await self._decompose_task(user_request, task_analysis, context)
            
            # Resolve dependencies and create execution order
            execution_order = self._resolve_dependencies(subtasks)
            
            # Estimate durations and create success criteria
            total_duration = self._estimate_total_duration(subtasks)
            success_criteria = self._generate_success_criteria(user_request, subtasks)
            
            # Create plan
            plan = TaskPlan(
                id=plan_id,
                name=f"Plan for: {user_request[:50]}...",
                description=f"Execution plan to fulfill user request: {user_request}",
                user_request=user_request,
                complexity=task_analysis.complexity,
                subtasks=[self._serialize_subtask(st) for st in subtasks],
                execution_order=execution_order,
                required_agents=[agent.value for agent in task_analysis.required_agents],
                estimated_total_duration=total_duration,
                success_criteria=success_criteria,
                fallback_strategies=self._generate_fallback_strategies(subtasks)
            )
            
            # Store plan
            self.plans[plan_id] = plan
            
            logger.info(
                "Created plan %s with %d subtasks, estimated duration: %.1f minutes",
                plan_id, len(subtasks), total_duration / 60 if total_duration else 0
            )
            
            return plan
            
        except Exception as e:
            logger.error("Error creating plan: %s", str(e))
            raise PlanningError(f"Failed to create execution plan: {str(e)}")
    
    async def _analyze_task_requirements(
        self,
        user_request: str,
        context: Dict[str, Any]
    ) -> TaskAnalysis:
        """Analyze task requirements using the supervisor agent's analysis logic."""
        try:
            # Import here to avoid circular imports
            from agents.supervisor_agent import SupervisorAgent
            
            supervisor = SupervisorAgent()
            analysis = supervisor.analyze_task(user_request, context)
            
            logger.debug("Task analysis: complexity=%s, agents=%s", 
                        analysis.complexity.value, [a.value for a in analysis.required_agents])
            
            return analysis
            
        except Exception as e:
            logger.error("Error in task analysis: %s", str(e))
            # Fallback analysis
            return TaskAnalysis(
                complexity=TaskComplexity.MODERATE,
                primary_domain="general",
                required_agents=[AgentType.REASONING],
                subtasks=[user_request],
                dependencies={},
                estimated_steps=2,
                confidence=0.5
            )
    
    async def _decompose_task(
        self,
        user_request: str,
        task_analysis: TaskAnalysis,
        context: Dict[str, Any]
    ) -> List[SubTask]:
        """Decompose a task into specific subtasks."""
        try:
            subtasks = []
            
            # Generate detailed decomposition using LLM
            decomposition_prompt = f"""
            Break down the following user request into specific, actionable subtasks for a multi-agent system.
            
            User Request: "{user_request}"
            
            Task Analysis:
            - Complexity: {task_analysis.complexity.value}
            - Required Agents: {[agent.value for agent in task_analysis.required_agents]}
            - Primary Domain: {task_analysis.primary_domain}
            
            Available Agent Types and Capabilities:
            - REASONING: Complex problem solving, step-by-step analysis, logical inference
            - RESEARCH: Internet research, fact-checking, information gathering
            - CODING: Software development, debugging, code generation
            - DOCUMENT_INTELLIGENCE: Document analysis, content extraction, format conversion
            - MULTIMODAL: Image/video processing, visual content creation
            
            For each subtask, provide:
            1. Clear name and description
            2. Which agent should handle it
            3. What inputs are needed
            4. What outputs are expected
            5. Any dependencies on other subtasks
            6. Priority level (low/medium/high/critical)
            
            Format your response as a structured list of subtasks.
            """
            
            response = self.model.invoke([
                SystemMessage(content="You are an expert task planner for multi-agent systems."),
                HumanMessage(content=decomposition_prompt)
            ])
            
            # Parse LLM response and create SubTask objects
            subtasks = self._parse_decomposition_response(response.content, task_analysis)
            
            logger.debug("Decomposed task into %d subtasks", len(subtasks))
            return subtasks
            
        except Exception as e:
            logger.error("Error in task decomposition: %s", str(e))
            # Fallback: create simple subtasks based on analysis
            return self._create_fallback_subtasks(user_request, task_analysis)
    
    def _parse_decomposition_response(
        self,
        response: str,
        task_analysis: TaskAnalysis
    ) -> List[SubTask]:
        """Parse LLM decomposition response into SubTask objects."""
        subtasks = []
        
        try:
            # For now, create subtasks based on the original analysis
            # In a full implementation, this would parse the LLM response
            for i, subtask_desc in enumerate(task_analysis.subtasks):
                agent_type = (task_analysis.required_agents[i % len(task_analysis.required_agents)]
                             if task_analysis.required_agents else AgentType.REASONING)
                
                subtask = SubTask(
                    id=f"subtask_{i+1}",
                    name=f"Subtask {i+1}",
                    description=subtask_desc,
                    assigned_agent=agent_type,
                    priority=SubTaskPriority.MEDIUM
                )
                subtasks.append(subtask)
            
            return subtasks
            
        except Exception as e:
            logger.error("Error parsing decomposition response: %s", str(e))
            return self._create_fallback_subtasks("", task_analysis)
    
    def _create_fallback_subtasks(
        self,
        user_request: str,
        task_analysis: TaskAnalysis
    ) -> List[SubTask]:
        """Create fallback subtasks when decomposition fails."""
        subtasks = []
        
        for i, agent_type in enumerate(task_analysis.required_agents):
            subtask = SubTask(
                id=f"fallback_subtask_{i+1}",
                name=f"{agent_type.value.title()} Task",
                description=f"Process user request using {agent_type.value} agent",
                assigned_agent=agent_type,
                priority=SubTaskPriority.MEDIUM
            )
            subtasks.append(subtask)
        
        return subtasks
    
    def _resolve_dependencies(self, subtasks: List[SubTask]) -> List[str]:
        """Resolve dependencies and create execution order."""
        try:
            # Topological sort to handle dependencies
            in_degree = {}
            graph = {}
            
            # Initialize
            for subtask in subtasks:
                in_degree[subtask.id] = 0
                graph[subtask.id] = []
            
            # Build dependency graph
            for subtask in subtasks:
                for dep_id in subtask.dependencies:
                    if dep_id in graph:
                        graph[dep_id].append(subtask.id)
                        in_degree[subtask.id] += 1
            
            # Topological sort
            queue = [task_id for task_id, degree in in_degree.items() if degree == 0]
            execution_order = []
            
            while queue:
                current = queue.pop(0)
                execution_order.append(current)
                
                for neighbor in graph[current]:
                    in_degree[neighbor] -= 1
                    if in_degree[neighbor] == 0:
                        queue.append(neighbor)
            
            # Check for cycles
            if len(execution_order) != len(subtasks):
                logger.warning("Dependency cycle detected, using fallback ordering")
                execution_order = [st.id for st in subtasks]
            
            return execution_order
            
        except Exception as e:
            logger.error("Error resolving dependencies: %s", str(e))
            return [st.id for st in subtasks]
    
    def _estimate_total_duration(self, subtasks: List[SubTask]) -> Optional[float]:
        """Estimate total execution duration in seconds."""
        try:
            total_seconds = 0.0
            
            for subtask in subtasks:
                if subtask.estimated_duration:
                    total_seconds += subtask.estimated_duration.total_seconds()
                else:
                    # Default estimation based on agent type
                    agent_defaults = {
                        AgentType.REASONING: 180,  # 3 minutes
                        AgentType.RESEARCH: 120,   # 2 minutes
                        AgentType.CODING: 300,     # 5 minutes
                        AgentType.DOCUMENT_INTELLIGENCE: 90,  # 1.5 minutes
                        AgentType.MULTIMODAL: 60   # 1 minute
                    }
                    total_seconds += agent_defaults.get(subtask.assigned_agent, 120)
            
            return total_seconds
            
        except Exception as e:
            logger.error("Error estimating duration: %s", str(e))
            return None
    
    def _generate_success_criteria(
        self,
        user_request: str,
        subtasks: List[SubTask]
    ) -> List[str]:
        """Generate success criteria for the plan."""
        criteria = [
            "All subtasks completed successfully",
            "User request fully addressed",
            "Results are coherent and comprehensive"
        ]
        
        # Add agent-specific criteria
        agent_types = {st.assigned_agent for st in subtasks}
        
        if AgentType.RESEARCH in agent_types:
            criteria.append("Research findings are current and well-sourced")
        
        if AgentType.CODING in agent_types:
            criteria.append("Generated code is functional and well-documented")
        
        if AgentType.DOCUMENT_INTELLIGENCE in agent_types:
            criteria.append("Document analysis is complete and accurate")
        
        return criteria
    
    def _generate_fallback_strategies(self, subtasks: List[SubTask]) -> Dict[str, str]:
        """Generate fallback strategies for potential failures."""
        strategies = {}
        
        for subtask in subtasks:
            if subtask.assigned_agent == AgentType.RESEARCH:
                strategies[subtask.id] = "Use alternative research agent or cached information"
            elif subtask.assigned_agent == AgentType.CODING:
                strategies[subtask.id] = "Provide code template or documentation instead"
            elif subtask.assigned_agent == AgentType.DOCUMENT_INTELLIGENCE:
                strategies[subtask.id] = "Use text extraction fallback methods"
            else:
                strategies[subtask.id] = "Skip non-critical subtask or use simplified approach"
        
        return strategies
    
    def _serialize_subtask(self, subtask: SubTask) -> Dict[str, Any]:
        """Serialize SubTask to dictionary for JSON storage."""
        return {
            "id": subtask.id,
            "name": subtask.name,
            "description": subtask.description,
            "assigned_agent": subtask.assigned_agent.value,
            "dependencies": subtask.dependencies,
            "status": subtask.status.value,
            "priority": subtask.priority.value,
            "estimated_duration": subtask.estimated_duration.total_seconds() if subtask.estimated_duration else None,
            "actual_duration": subtask.actual_duration.total_seconds() if subtask.actual_duration else None,
            "input_requirements": subtask.input_requirements,
            "output_specification": subtask.output_specification,
            "error_messages": subtask.error_messages,
            "metadata": subtask.metadata,
            "created_at": subtask.created_at.isoformat(),
            "started_at": subtask.started_at.isoformat() if subtask.started_at else None,
            "completed_at": subtask.completed_at.isoformat() if subtask.completed_at else None
        }
    
    def get_plan(self, plan_id: str) -> Optional[TaskPlan]:
        """Get a plan by ID."""
        return self.plans.get(plan_id)
    
    def update_subtask_status(
        self,
        plan_id: str,
        subtask_id: str,
        status: SubTaskStatus,
        result: Optional[Dict[str, Any]] = None
    ) -> bool:
        """Update the status of a subtask."""
        try:
            if plan_id not in self.plans:
                return False
            
            plan = self.plans[plan_id]
            
            # Find and update subtask
            for subtask_data in plan.subtasks:
                if subtask_data["id"] == subtask_id:
                    subtask_data["status"] = status.value
                    
                    if status == SubTaskStatus.EXECUTING:
                        subtask_data["started_at"] = datetime.now().isoformat()
                    elif status in [SubTaskStatus.COMPLETED, SubTaskStatus.FAILED]:
                        subtask_data["completed_at"] = datetime.now().isoformat()
                        
                        if subtask_data["started_at"]:
                            start_time = datetime.fromisoformat(subtask_data["started_at"])
                            duration = (datetime.now() - start_time).total_seconds()
                            subtask_data["actual_duration"] = duration
                    
                    if result:
                        subtask_data["metadata"]["result"] = result
                    
                    plan.updated_at = datetime.now()
                    return True
            
            return False
            
        except Exception as e:
            logger.error("Error updating subtask status: %s", str(e))
            return False
    
    def get_next_ready_subtasks(self, plan_id: str) -> List[Dict[str, Any]]:
        """Get subtasks that are ready to execute (dependencies met)."""
        try:
            if plan_id not in self.plans:
                return []
            
            plan = self.plans[plan_id]
            ready_subtasks = []
            
            # Get completed subtasks
            completed_ids = {
                st["id"] for st in plan.subtasks 
                if st["status"] == SubTaskStatus.COMPLETED.value
            }
            
            # Find ready subtasks
            for subtask_data in plan.subtasks:
                if subtask_data["status"] == SubTaskStatus.PENDING.value:
                    # Check if all dependencies are completed
                    dependencies_met = all(
                        dep_id in completed_ids 
                        for dep_id in subtask_data["dependencies"]
                    )
                    
                    if dependencies_met:
                        ready_subtasks.append(subtask_data)
            
            return ready_subtasks
            
        except Exception as e:
            logger.error("Error getting ready subtasks: %s", str(e))
            return []


# Export main classes and functions
__all__ = [
    "TaskPlanner",
    "TaskPlan", 
    "SubTask",
    "SubTaskStatus",
    "SubTaskPriority"
]
