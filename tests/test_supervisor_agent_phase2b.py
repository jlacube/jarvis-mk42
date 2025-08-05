# tests/test_supervisor_agent_phase2b.py
"""
Test Suite for Phase 2B Supervisor Agent and Multi-Agent Orchestration
======================================================================

This test suite validates the supervisor agent foundation and multi-agent
orchestration capabilities including:

- Supervisor agent initialization and task analysis
- Workflow creation and execution
- Task planning and decomposition
- Agent coordination and communication
- Error handling and recovery mechanisms
"""

import pytest
import asyncio
from datetime import datetime, timedelta
from unittest.mock import Mock, AsyncMock, patch

from agents.supervisor_agent import (
    SupervisorAgent, TaskComplexity, AgentType, TaskAnalysis, WorkflowState,
    create_supervisor_agent
)
from orchestration.workflow_engine import (
    WorkflowEngine, WorkflowTemplate, WorkflowExecution, WorkflowStatus,
    WorkflowNode, WorkflowEdge, NodeType
)
from orchestration.task_planner import (
    TaskPlanner, TaskPlan, SubTask, SubTaskStatus, SubTaskPriority
)
from orchestration.agent_coordinator import (
    AgentCoordinator, AgentRegistry, AgentStatus, AgentInfo, MessageType
)


class TestSupervisorAgent:
    """Test cases for the SupervisorAgent class."""
    
    @pytest.fixture
    def supervisor_agent(self):
        """Create a supervisor agent for testing."""
        return SupervisorAgent()
    
    def test_supervisor_agent_initialization(self, supervisor_agent):
        """Test supervisor agent initialization."""
        assert supervisor_agent is not None
        assert len(supervisor_agent.agent_capabilities) == 5
        assert AgentType.REASONING in supervisor_agent.agent_capabilities
        assert AgentType.RESEARCH in supervisor_agent.agent_capabilities
        assert AgentType.CODING in supervisor_agent.agent_capabilities
        assert AgentType.DOCUMENT_INTELLIGENCE in supervisor_agent.agent_capabilities
        assert AgentType.MULTIMODAL in supervisor_agent.agent_capabilities
    
    def test_task_analysis_simple(self, supervisor_agent):
        """Test task analysis for simple requests."""
        context = {
            "user_name": "test_user",
            "session_id": "test_session"
        }
        
        analysis = supervisor_agent.analyze_task("What is 2 + 2?", context)
        
        assert isinstance(analysis, TaskAnalysis)
        assert analysis.complexity in [TaskComplexity.SIMPLE, TaskComplexity.MODERATE]
        assert len(analysis.required_agents) >= 1
        assert analysis.confidence > 0.0
    
    def test_task_analysis_complex(self, supervisor_agent):
        """Test task analysis for complex requests."""
        context = {
            "user_name": "test_user",
            "session_id": "test_session"
        }
        
        complex_request = (
            "Research the latest AI developments, write Python code to analyze trends, "
            "and create visualizations showing the progress over time"
        )
        
        analysis = supervisor_agent.analyze_task(complex_request, context)
        
        assert isinstance(analysis, TaskAnalysis)
        assert analysis.complexity in [TaskComplexity.COMPLEX, TaskComplexity.ADVANCED]
        assert len(analysis.required_agents) >= 2
        assert AgentType.RESEARCH in analysis.required_agents
        assert AgentType.CODING in analysis.required_agents
    
    def test_agent_selection(self, supervisor_agent):
        """Test agent selection based on task analysis."""
        task_analysis = TaskAnalysis(
            complexity=TaskComplexity.COMPLEX,
            primary_domain="technical",
            required_agents=[AgentType.RESEARCH, AgentType.CODING],
            subtasks=["Research AI trends", "Generate analysis code"],
            dependencies={},
            estimated_steps=3,
            confidence=0.8
        )
        
        selected_agents = supervisor_agent.select_agents(task_analysis)
        
        assert len(selected_agents) == 2
        assert AgentType.RESEARCH in selected_agents
        assert AgentType.CODING in selected_agents
    
    def test_format_agent_capabilities(self, supervisor_agent):
        """Test agent capabilities formatting."""
        formatted = supervisor_agent._format_agent_capabilities()
        
        assert isinstance(formatted, str)
        assert "Reasoning Agent" in formatted
        assert "Research Agent" in formatted
        assert "Coding Agent" in formatted
        assert "Document Intelligence Agent" in formatted
        assert "Multimodal Agent" in formatted
    
    @pytest.mark.asyncio
    async def test_create_workflow(self, supervisor_agent):
        """Test workflow creation."""
        initial_state = WorkflowState(
            user_request="Test request",
            user_name="test_user",
            session_context={"session_id": "test_session"}
        )
        
        workflow = await supervisor_agent.create_workflow(initial_state)
        
        assert workflow is not None
        # Note: Full workflow testing would require more complex setup
    
    def test_orchestrator_node(self, supervisor_agent):
        """Test orchestrator node processing."""
        state = {
            "user_request": "Test request",
            "user_name": "test_user",
            "session_context": {"session_id": "test_session"},
            "workflow_status": "planning"
        }
        
        result = supervisor_agent._orchestrator_node(state)
        
        assert isinstance(result, dict)
        assert "task_analysis" in result
        assert "active_agents" in result
        assert result["workflow_status"] == "executing"
    
    def test_synthesizer_node(self, supervisor_agent):
        """Test synthesizer node processing."""
        state = {
            "user_request": "Test request",
            "agent_results": {
                "research": "Research findings here",
                "coding": "Code implementation here"
            }
        }
        
        result = supervisor_agent._synthesizer_node(state)
        
        assert isinstance(result, dict)
        assert "final_response" in result
        assert result["workflow_status"] == "complete"
        assert len(result["final_response"]) > 0


class TestWorkflowEngine:
    """Test cases for the WorkflowEngine class."""
    
    @pytest.fixture
    def workflow_engine(self):
        """Create a workflow engine for testing."""
        return WorkflowEngine()
    
    def test_workflow_engine_initialization(self, workflow_engine):
        """Test workflow engine initialization."""
        assert workflow_engine is not None
        assert workflow_engine.checkpointer is not None
        assert len(workflow_engine.templates) == 0
        assert len(workflow_engine.executions) == 0
        assert len(workflow_engine.active_workflows) == 0
    
    def test_register_template(self, workflow_engine):
        """Test workflow template registration."""
        template = WorkflowTemplate(
            id="test_template",
            name="Test Template", 
            description="A test template",
            nodes=[],
            edges=[]
        )
        
        workflow_engine.register_template(template)
        
        assert "test_template" in workflow_engine.templates
        assert workflow_engine.templates["test_template"].name == "Test Template"
    
    def test_create_workflow(self, workflow_engine):
        """Test workflow creation from nodes and edges."""
        from typing_extensions import TypedDict
        
        class TestState(TypedDict):
            input: str
            output: str
        
        def test_node(state):
            return {"output": f"Processed: {state.get('input', '')}"}
        
        nodes = [
            WorkflowNode(
                id="test_node",
                name="Test Node",
                node_type=NodeType.AGENT,
                function=test_node
            )
        ]
        
        edges = [
            WorkflowEdge(from_node="START", to_node="test_node"),
            WorkflowEdge(from_node="test_node", to_node="END")
        ]
        
        execution_id = workflow_engine.create_workflow(nodes, edges, TestState)
        
        assert execution_id is not None
        assert execution_id in workflow_engine.executions
        assert execution_id in workflow_engine.active_workflows
        assert workflow_engine.executions[execution_id].status == WorkflowStatus.CREATED
    
    def test_get_execution_status(self, workflow_engine):
        """Test getting execution status."""
        # Create a mock execution
        execution = WorkflowExecution(
            id="test_execution",
            status=WorkflowStatus.EXECUTING
        )
        workflow_engine.executions["test_execution"] = execution
        
        status = workflow_engine.get_execution_status("test_execution")
        
        assert status is not None
        assert status.id == "test_execution"
        assert status.status == WorkflowStatus.EXECUTING
    
    def test_pause_workflow(self, workflow_engine):
        """Test workflow pausing."""
        execution = WorkflowExecution(
            id="test_execution",
            status=WorkflowStatus.EXECUTING
        )
        workflow_engine.executions["test_execution"] = execution
        
        result = workflow_engine.pause_workflow("test_execution")
        
        assert result is True
        assert workflow_engine.executions["test_execution"].status == WorkflowStatus.PAUSED
    
    def test_resume_workflow(self, workflow_engine):
        """Test workflow resuming."""
        execution = WorkflowExecution(
            id="test_execution",
            status=WorkflowStatus.PAUSED
        )
        workflow_engine.executions["test_execution"] = execution
        
        result = workflow_engine.resume_workflow("test_execution")
        
        assert result is True
        assert workflow_engine.executions["test_execution"].status == WorkflowStatus.EXECUTING
    
    def test_cancel_workflow(self, workflow_engine):
        """Test workflow cancellation."""
        execution = WorkflowExecution(
            id="test_execution",
            status=WorkflowStatus.EXECUTING
        )
        workflow_engine.executions["test_execution"] = execution
        
        result = workflow_engine.cancel_workflow("test_execution")
        
        assert result is True
        assert workflow_engine.executions["test_execution"].status == WorkflowStatus.CANCELLED
    
    def test_cleanup_completed_workflows(self, workflow_engine):
        """Test cleanup of old completed workflows."""
        # Create old completed execution
        old_execution = WorkflowExecution(
            id="old_execution",
            status=WorkflowStatus.COMPLETED,
            completed_at=datetime.now() - timedelta(hours=25)
        )
        
        # Create recent execution
        recent_execution = WorkflowExecution(
            id="recent_execution",
            status=WorkflowStatus.COMPLETED,
            completed_at=datetime.now() - timedelta(hours=1)
        )
        
        workflow_engine.executions["old_execution"] = old_execution
        workflow_engine.executions["recent_execution"] = recent_execution
        
        cleanup_count = workflow_engine.cleanup_completed_workflows(max_age_hours=24)
        
        assert cleanup_count == 1
        assert "old_execution" not in workflow_engine.executions
        assert "recent_execution" in workflow_engine.executions
    
    def test_get_workflow_statistics(self, workflow_engine):
        """Test workflow statistics generation."""
        # Add some test executions
        workflow_engine.executions["exec1"] = WorkflowExecution(
            id="exec1", status=WorkflowStatus.COMPLETED
        )
        workflow_engine.executions["exec2"] = WorkflowExecution(
            id="exec2", status=WorkflowStatus.EXECUTING
        )
        
        stats = workflow_engine.get_workflow_statistics()
        
        assert isinstance(stats, dict)
        assert stats["total_executions"] == 2
        assert "status_breakdown" in stats
        assert "success_rate" in stats


class TestTaskPlanner:
    """Test cases for the TaskPlanner class."""
    
    @pytest.fixture
    def task_planner(self):
        """Create a task planner for testing."""
        return TaskPlanner()
    
    def test_task_planner_initialization(self, task_planner):
        """Test task planner initialization."""
        assert task_planner is not None
        assert task_planner.model is not None
        assert len(task_planner.subtask_templates) > 0
        assert "research_query" in task_planner.subtask_templates
        assert "generate_code" in task_planner.subtask_templates
    
    @pytest.mark.asyncio
    async def test_create_plan(self, task_planner):
        """Test plan creation."""
        user_request = "Research Python best practices and create example code"
        context = {
            "user_name": "test_user",
            "session_id": "test_session"
        }
        
        with patch.object(task_planner, '_analyze_task_requirements') as mock_analyze:
            mock_analyze.return_value = TaskAnalysis(
                complexity=TaskComplexity.COMPLEX,
                primary_domain="programming",
                required_agents=[AgentType.RESEARCH, AgentType.CODING],
                subtasks=["Research Python practices", "Generate example code"],
                dependencies={},
                estimated_steps=2,
                confidence=0.8
            )
            
            plan = await task_planner.create_plan(user_request, context)
        
        assert isinstance(plan, TaskPlan)
        assert plan.user_request == user_request
        assert plan.complexity == TaskComplexity.COMPLEX
        assert len(plan.subtasks) >= 1
        assert len(plan.execution_order) >= 1
    
    def test_resolve_dependencies(self, task_planner):
        """Test dependency resolution."""
        subtasks = [
            SubTask(
                id="task1", 
                name="Task 1", 
                description="First task",
                assigned_agent=AgentType.RESEARCH
            ),
            SubTask(
                id="task2", 
                name="Task 2", 
                description="Second task",
                assigned_agent=AgentType.CODING,
                dependencies=["task1"]
            )
        ]
        
        execution_order = task_planner._resolve_dependencies(subtasks)
        
        assert len(execution_order) == 2
        assert execution_order.index("task1") < execution_order.index("task2")
    
    def test_estimate_total_duration(self, task_planner):
        """Test duration estimation."""
        subtasks = [
            SubTask(
                id="task1",
                name="Task 1",
                description="Research task",
                assigned_agent=AgentType.RESEARCH,
                estimated_duration=timedelta(minutes=2)
            ),
            SubTask(
                id="task2",
                name="Task 2", 
                description="Coding task",
                assigned_agent=AgentType.CODING,
                estimated_duration=timedelta(minutes=5)
            )
        ]
        
        total_duration = task_planner._estimate_total_duration(subtasks)
        
        assert total_duration == 420.0  # 7 minutes in seconds
    
    def test_generate_success_criteria(self, task_planner):
        """Test success criteria generation."""
        subtasks = [
            SubTask(
                id="task1",
                name="Research Task",
                description="Research something",
                assigned_agent=AgentType.RESEARCH
            ),
            SubTask(
                id="task2",
                name="Code Task",
                description="Generate code",
                assigned_agent=AgentType.CODING
            )
        ]
        
        criteria = task_planner._generate_success_criteria("Test request", subtasks)
        
        assert isinstance(criteria, list)
        assert len(criteria) >= 3
        assert any("research" in c.lower() for c in criteria)
        assert any("code" in c.lower() for c in criteria)
    
    def test_update_subtask_status(self, task_planner):
        """Test subtask status updates."""
        # Create a plan first
        plan = TaskPlan(
            id="test_plan",
            name="Test Plan",
            description="Test plan",
            user_request="Test request",
            complexity=TaskComplexity.SIMPLE,
            subtasks=[{
                "id": "task1",
                "name": "Task 1",
                "status": SubTaskStatus.PENDING.value,
                "started_at": None,
                "completed_at": None
            }],
            execution_order=["task1"],
            required_agents=["reasoning"]
        )
        task_planner.plans["test_plan"] = plan
        
        result = task_planner.update_subtask_status(
            "test_plan", 
            "task1", 
            SubTaskStatus.EXECUTING
        )
        
        assert result is True
        assert plan.subtasks[0]["status"] == SubTaskStatus.EXECUTING.value
        assert plan.subtasks[0]["started_at"] is not None
    
    def test_get_next_ready_subtasks(self, task_planner):
        """Test getting ready subtasks."""
        plan = TaskPlan(
            id="test_plan",
            name="Test Plan",
            description="Test plan",
            user_request="Test request",
            complexity=TaskComplexity.SIMPLE,
            subtasks=[
                {
                    "id": "task1",
                    "name": "Task 1",
                    "status": SubTaskStatus.COMPLETED.value,
                    "dependencies": []
                },
                {
                    "id": "task2",
                    "name": "Task 2", 
                    "status": SubTaskStatus.PENDING.value,
                    "dependencies": ["task1"]
                }
            ],
            execution_order=["task1", "task2"],
            required_agents=["reasoning"]
        )
        task_planner.plans["test_plan"] = plan
        
        ready_subtasks = task_planner.get_next_ready_subtasks("test_plan")
        
        assert len(ready_subtasks) == 1
        assert ready_subtasks[0]["id"] == "task2"


class TestAgentCoordinator:
    """Test cases for the AgentCoordinator class."""
    
    @pytest.fixture
    def agent_coordinator(self):
        """Create an agent coordinator for testing."""
        return AgentCoordinator()
    
    def test_agent_coordinator_initialization(self, agent_coordinator):
        """Test agent coordinator initialization."""
        assert agent_coordinator is not None
        assert isinstance(agent_coordinator.registry, AgentRegistry)
        assert len(agent_coordinator.message_queue) == 0
        assert len(agent_coordinator.shared_contexts) == 0
    
    def test_register_agent(self, agent_coordinator):
        """Test agent registration."""
        result = agent_coordinator.register_agent(
            agent_id="test_agent",
            agent_type=AgentType.REASONING,
            capabilities=["logical_reasoning", "problem_solving"]
        )
        
        assert result is True
        assert "test_agent" in agent_coordinator.registry.agents
        assert agent_coordinator.registry.agents["test_agent"].agent_type == AgentType.REASONING
    
    @pytest.mark.asyncio
    async def test_send_message(self, agent_coordinator):
        """Test message sending."""
        # Register agents first
        agent_coordinator.register_agent("agent1", AgentType.REASONING, ["test"])
        agent_coordinator.register_agent("agent2", AgentType.RESEARCH, ["test"])
        
        result = await agent_coordinator.send_message(
            from_agent="agent1",
            to_agent="agent2", 
            message_type=MessageType.CONTEXT_SHARE,
            content={"test": "data"}
        )
        
        # For non-request messages, result should be None
        assert result is None
        assert len(agent_coordinator.message_queue) == 1
    
    def test_get_shared_context(self, agent_coordinator):
        """Test shared context management."""
        context = agent_coordinator.get_shared_context("test_session")
        
        assert context is not None
        assert context.session_id == "test_session"
        assert "test_session" in agent_coordinator.shared_contexts
    
    def test_update_shared_context(self, agent_coordinator):
        """Test shared context updates."""
        result = agent_coordinator.update_shared_context(
            "test_session",
            {"test_key": "test_value"}
        )
        
        assert result is True
        context = agent_coordinator.get_shared_context("test_session")
        assert context.shared_variables["test_key"] == "test_value"
    
    def test_get_coordination_statistics(self, agent_coordinator):
        """Test coordination statistics."""
        # Register some test agents
        agent_coordinator.register_agent("agent1", AgentType.REASONING, ["test"])
        agent_coordinator.register_agent("agent2", AgentType.RESEARCH, ["test"])
        
        stats = agent_coordinator.get_coordination_statistics()
        
        assert isinstance(stats, dict)
        assert stats["registered_agents"] == 2
        assert "agent_breakdown" in stats
        assert "reasoning" in stats["agent_breakdown"]
        assert "research" in stats["agent_breakdown"]


class TestAgentRegistry:
    """Test cases for the AgentRegistry class."""
    
    @pytest.fixture
    def agent_registry(self):
        """Create an agent registry for testing."""
        return AgentRegistry()
    
    def test_agent_registry_initialization(self, agent_registry):
        """Test agent registry initialization."""
        assert agent_registry is not None
        assert len(agent_registry.agents) == 0
        assert len(agent_registry.agent_instances) == 0
        assert len(agent_registry.capability_index) == 0
    
    def test_register_agent(self, agent_registry):
        """Test agent registration."""
        agent_info = AgentInfo(
            agent_type=AgentType.REASONING,
            name="Test Agent",
            description="A test agent",
            capabilities=["reasoning", "analysis"]
        )
        
        result = agent_registry.register_agent("test_agent", agent_info)
        
        assert result is True
        assert "test_agent" in agent_registry.agents
        assert "reasoning" in agent_registry.capability_index
        assert "analysis" in agent_registry.capability_index
        assert "test_agent" in agent_registry.capability_index["reasoning"]
    
    def test_unregister_agent(self, agent_registry):
        """Test agent unregistration."""
        # Register agent first
        agent_info = AgentInfo(
            agent_type=AgentType.REASONING,
            name="Test Agent",
            description="A test agent", 
            capabilities=["reasoning"]
        )
        agent_registry.register_agent("test_agent", agent_info)
        
        # Unregister
        result = agent_registry.unregister_agent("test_agent")
        
        assert result is True
        assert "test_agent" not in agent_registry.agents
        assert "reasoning" not in agent_registry.capability_index
    
    def test_get_agents_by_capability(self, agent_registry):
        """Test getting agents by capability."""
        agent_info = AgentInfo(
            agent_type=AgentType.RESEARCH,
            name="Research Agent",
            description="A research agent",
            capabilities=["web_search", "fact_checking"]
        )
        agent_registry.register_agent("research_agent", agent_info)
        
        agents = agent_registry.get_agents_by_capability("web_search")
        
        assert len(agents) == 1
        assert "research_agent" in agents
    
    def test_get_agents_by_type(self, agent_registry):
        """Test getting agents by type."""
        agent_info = AgentInfo(
            agent_type=AgentType.CODING,
            name="Coding Agent",
            description="A coding agent",
            capabilities=["code_generation"]
        )
        agent_registry.register_agent("coding_agent", agent_info)
        
        agents = agent_registry.get_agents_by_type(AgentType.CODING)
        
        assert len(agents) == 1
        assert "coding_agent" in agents
    
    def test_get_available_agents(self, agent_registry):
        """Test getting available agents."""
        # Register ready agent
        ready_agent = AgentInfo(
            agent_type=AgentType.REASONING,
            name="Ready Agent",
            description="A ready agent",
            capabilities=["reasoning"],
            status=AgentStatus.READY,
            current_load=0,
            max_concurrent_tasks=3
        )
        agent_registry.register_agent("ready_agent", ready_agent)
        
        # Register busy agent
        busy_agent = AgentInfo(
            agent_type=AgentType.RESEARCH,
            name="Busy Agent",
            description="A busy agent",
            capabilities=["research"],
            status=AgentStatus.BUSY,
            current_load=3,
            max_concurrent_tasks=3
        )
        agent_registry.register_agent("busy_agent", busy_agent)
        
        available = agent_registry.get_available_agents()
        
        assert len(available) == 1
        assert "ready_agent" in available
        assert "busy_agent" not in available
    
    def test_update_agent_status(self, agent_registry):
        """Test agent status updates."""
        agent_info = AgentInfo(
            agent_type=AgentType.REASONING,
            name="Test Agent",
            description="A test agent",
            capabilities=["reasoning"]
        )
        agent_registry.register_agent("test_agent", agent_info)
        
        result = agent_registry.update_agent_status("test_agent", AgentStatus.BUSY)
        
        assert result is True
        assert agent_registry.agents["test_agent"].status == AgentStatus.BUSY
    
    def test_update_agent_metrics(self, agent_registry):
        """Test agent metrics updates."""
        agent_info = AgentInfo(
            agent_type=AgentType.REASONING,
            name="Test Agent",
            description="A test agent",
            capabilities=["reasoning"],
            total_tasks_completed=0,
            average_response_time=0.0,
            success_rate=1.0
        )
        agent_registry.register_agent("test_agent", agent_info)
        
        result = agent_registry.update_agent_metrics(
            "test_agent", 
            response_time=2.5, 
            success=True
        )
        
        assert result is True
        assert agent_registry.agents["test_agent"].total_tasks_completed == 1
        assert agent_registry.agents["test_agent"].average_response_time == 2.5
        assert agent_registry.agents["test_agent"].success_rate == 1.0


@pytest.mark.asyncio
async def test_create_supervisor_agent():
    """Test supervisor agent factory function."""
    supervisor = await create_supervisor_agent()
    
    assert supervisor is not None
    assert isinstance(supervisor, SupervisorAgent)


@pytest.mark.integration
class TestPhase2BIntegration:
    """Integration tests for Phase 2B multi-agent orchestration."""
    
    @pytest.mark.asyncio
    async def test_full_workflow_integration(self):
        """Test full integration of supervisor agent with orchestration components."""
        # Create components
        supervisor = SupervisorAgent()
        coordinator = AgentCoordinator()
        planner = TaskPlanner()
        
        # Register mock agents
        coordinator.register_agent("reasoning_agent", AgentType.REASONING, ["reasoning"])
        coordinator.register_agent("research_agent", AgentType.RESEARCH, ["research"])
        
        # Test task analysis and planning
        user_request = "Research AI trends and provide analysis"
        context = {"user_name": "test_user", "session_id": "test_session"}
        
        analysis = supervisor.analyze_task(user_request, context)
        assert analysis is not None
        
        plan = await planner.create_plan(user_request, context)
        assert plan is not None
        
        # Test shared context
        shared_context = coordinator.get_shared_context("test_session")
        assert shared_context is not None
        
        # Verify integration works
        assert len(coordinator.registry.agents) == 2
        assert len(plan.subtasks) >= 1
        assert analysis.complexity in [TaskComplexity.MODERATE, TaskComplexity.COMPLEX]


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
