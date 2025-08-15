# tests/test_communication.py
"""
Comprehensive test suite for the Inter-Agent Communication Framework.

Tests cover:
- Message protocols and validation
- Async message bus functionality
- Context management and shared state
- Conflict resolution strategies
- Integration scenarios
- Performance and reliability
"""

import asyncio
import pytest
import json
from datetime import datetime, timedelta
from typing import Any, Dict, List, Optional
from unittest.mock import AsyncMock, MagicMock, patch

from communication.protocols import (
    AgentMessage, RequestMessage, ResponseMessage, ContextUpdate,
    NotificationMessage, BroadcastMessage,
    MessageType, MessagePriority, MessageStatus, AgentType, CommunicationProtocol,
    validate_message
)
from communication.message_bus import MessageBus, MessageQueue, MessageRouter, MessageHandler
from communication.context_manager import (
    SharedContext, ContextManager, ContextScope, ContextAccessLevel,
    MergeStrategy, ContextVersion, ContextConflict
)
from communication.conflict_resolver import (
    ConflictResolver, Conflict, ConflictType, ResolutionStrategy,
    ConflictSeverity, AgentPosition, ConflictContext
)


class TestMessageProtocols:
    """Test suite for message protocols and validation."""
    
    def test_agent_message_creation(self):
        """Test basic agent message creation and validation."""
        message = AgentMessage(
            type=MessageType.REQUEST,
            sender_id="agent-1",
            sender_type=AgentType.CODING,
            priority=MessagePriority.HIGH,
            subject="Test Message",
            content={"test": "data"}
        )
        
        assert message.type == MessageType.REQUEST
        assert message.sender_id == "agent-1"
        assert message.sender_type == AgentType.CODING
        assert message.priority == MessagePriority.HIGH
        assert message.subject == "Test Message"
        assert message.content == {"test": "data"}
        assert message.metadata is not None
        assert message.status == MessageStatus.PENDING
    
    def test_request_message_creation(self):
        """Test request message creation and validation."""
        request = RequestMessage(
            sender_id="agent-1",
            sender_type=AgentType.CODING,
            recipient_id="agent-2",
            subject="Analysis Request",
            service="analysis",
            parameters={"file": "test.py"},
            timeout_seconds=30
        )
        
        assert request.type == MessageType.REQUEST
        assert request.recipient_id == "agent-2"
        assert request.service == "analysis"
        assert request.parameters == {"file": "test.py"}
        assert request.timeout_seconds == 30
        assert request.expects_response is True
    
    def test_response_message_creation(self):
        """Test response message creation and validation."""
        response = ResponseMessage(
            sender_id="agent-2",
            sender_type=AgentType.REASONING,
            request_id="req-001",
            service="analysis",
            subject="Analysis Response",
            success=True,
            result={"analysis": "complete"},
            error_message=None
        )
        
        assert response.type == MessageType.RESPONSE
        assert response.request_id == "req-001"
        assert response.success is True
        assert response.result == {"analysis": "complete"}
        assert response.error_message is None
    
    def test_context_update_creation(self):
        """Test context update message creation."""
        update = ContextUpdate(
            sender_id="agent-1",
            sender_type=AgentType.SUPERVISOR,
            subject="Context Update",
            service="context",
            context_key="current_task",
            context_data={"task_id": "task-123"},
            update_type="update"
        )
        
        assert update.type == MessageType.CONTEXT_UPDATE
        assert update.context_key == "current_task"
        assert update.context_data == {"task_id": "task-123"}
        assert update.update_type == "update"
    
    def test_message_serialization(self):
        """Test message serialization and deserialization."""
        message = AgentMessage(
            sender_id="agent-1",
            sender_type=AgentType.CODING,
            type=MessageType.NOTIFICATION,
            subject="Test",
            content={"key": "value"}
        )
        
        # Test to_dict
        data = message.model_dump(mode='json')  # Use mode='json' to serialize enums as strings
        assert isinstance(data, dict)
        assert data["metadata"]["message_id"] is not None
        assert data["sender_type"] == "coding"  # Enum value string
        
        # Test from_dict
        restored = AgentMessage.model_validate(data)
        assert restored.metadata.message_id == message.metadata.message_id
        assert restored.sender_id == message.sender_id
        assert restored.sender_type == message.sender_type
    
    def test_communication_protocol_validation(self):
        """Test communication protocol validation functions."""
        # Valid message with recipient for REQUEST type
        message = AgentMessage(
            sender_id="agent-1",
            sender_type=AgentType.CODING,
            recipient_id="agent-2",
            type=MessageType.REQUEST,
            subject="Test",
            content={}
        )
        
        # Test validation - should return empty list for valid message
        validation_errors = validate_message(message)
        assert validation_errors == []
        assert CommunicationProtocol.is_valid_agent_id("agent-123") is True
        assert CommunicationProtocol.is_valid_agent_id("invalid id") is False


@pytest.mark.asyncio
class TestMessageBus:
    """Test suite for async message bus functionality."""
    
    async def test_message_bus_creation(self):
        """Test message bus creation and initialization."""
        bus = MessageBus()
        assert bus.max_queue_size == 1000
        assert bus.overflow_policy.value == "drop_oldest"
        assert not bus._is_running
        
        await bus.start()
        assert bus._processor_task is not None
        assert bus._is_running
        
        await bus.stop()
        assert not bus._is_running
        assert bus._processor_task.cancelled()
    
    async def test_message_queue_operations(self):
        """Test message queue priority handling."""
        queue = MessageQueue(max_size=10)
        
        # Add messages with different priorities
        high_msg = AgentMessage(
            sender_id="agent-1",
            sender_type=AgentType.SUPERVISOR,
            type=MessageType.REQUEST,
            priority=MessagePriority.HIGH,
            subject="High Priority",
            content={}
        )
        
        low_msg = AgentMessage(
            sender_id="agent-2", 
            sender_type=AgentType.CODING,
            type=MessageType.NOTIFICATION,
            priority=MessagePriority.LOW,
            subject="Low Priority",
            content={}
        )
        
        # Add low priority first, then high priority
        await queue.put(low_msg)
        await queue.put(high_msg)
        
        # High priority should come out first
        first_msg = await queue.get()
        assert first_msg.metadata.message_id == high_msg.metadata.message_id
        assert first_msg.priority == MessagePriority.HIGH
        
        second_msg = await queue.get()
        assert second_msg.metadata.message_id == low_msg.metadata.message_id
        assert second_msg.priority == MessagePriority.LOW
    
    async def test_message_router_subscriptions(self):
        """Test message router subscription and filtering."""
        router = MessageRouter()
        
        # Create test message handlers
        class TestHandler1(MessageHandler):
            def __init__(self):
                super().__init__("test-handler-1")
                self.received_messages = []
                
            async def handle_message(self, message: AgentMessage) -> Optional[AgentMessage]:
                self.received_messages.append(message)
                return None
        
        class TestHandler2(MessageHandler):
            def __init__(self):
                super().__init__("test-handler-2")
                self.received_messages = []
                
            async def handle_message(self, message: AgentMessage) -> Optional[AgentMessage]:
                self.received_messages.append(message)
                return None
        
        handler1 = TestHandler1()
        handler2 = TestHandler2()
        
        # Subscribe to different message types
        router.subscribe(handler1, {MessageType.REQUEST})
        router.subscribe(handler2, {MessageType.NOTIFICATION})
        
        # Test routing
        request_msg = AgentMessage(
            sender_id="sender",
            sender_type=AgentType.CODING,
            type=MessageType.REQUEST,
            subject="Test Request",
            content={}
        )
        
        await router.route_message(request_msg)
        
        # Only handler1 should receive the message
        assert len(handler1.received_messages) == 1
        assert len(handler2.received_messages) == 0
        assert handler1.received_messages[0] == request_msg
    
    async def test_message_bus_integration(self):
        """Test complete message bus integration."""
        bus = MessageBus()
        await bus.start()
        
        # Create test handler
        class IntegrationTestHandler(MessageHandler):
            def __init__(self):
                super().__init__("integration-test-handler")
                self.received_messages = []
                
            async def handle_message(self, message: AgentMessage) -> Optional[AgentMessage]:
                self.received_messages.append(message)
                return None
        
        handler = IntegrationTestHandler()
        
        # Subscribe to messages
        bus.subscribe(handler, {MessageType.REQUEST})
        
        # Publish a message
        message = AgentMessage(
            sender_id="sender",
            sender_type=AgentType.CODING,
            recipient_id="integration-test-handler",  # Add recipient for REQUEST message
            type=MessageType.REQUEST,
            subject="Test",
            content={"test": True}
        )
        
        await bus.send_message(message)
        
        # Wait for processing
        await asyncio.sleep(0.1)
        
        # Check message was received
        assert len(handler.received_messages) == 1
        assert handler.received_messages[0].metadata.message_id == message.metadata.message_id
        
        await bus.stop()


@pytest.mark.asyncio
class TestContextManager:
    """Test suite for context management and shared state."""
    
    async def test_shared_context_operations(self):
        """Test basic shared context operations."""
        context = SharedContext("test-context", ContextScope.TASK)
        
        # Test set and get
        version = await context.set(
            "key1",
            "value1",
            "agent-1",
            AgentType.CODING,
            "Initial value"
        )
        
        assert version == 1
        
        value = await context.get("key1")
        assert value == "value1"
        
        # Test update
        version2 = await context.set(
            "key1",
            "value2", 
            "agent-1",
            AgentType.CODING,
            "Updated value"
        )
        
        assert version2 == 2
        
        updated_value = await context.get("key1")
        assert updated_value == "value2"
    
    async def test_context_versioning(self):
        """Test context version tracking."""
        context = SharedContext("test-context", ContextScope.WORKFLOW)
        
        # Create multiple versions
        await context.set("key1", "v1", "agent-1", AgentType.CODING, "Version 1")
        await context.set("key1", "v2", "agent-2", AgentType.REASONING, "Version 2")
        await context.set("key1", "v3", "agent-1", AgentType.CODING, "Version 3")
        
        # Check version history
        history = await context.get_version_history("key1")
        assert len(history) == 3
        assert history[0].version == 1
        assert history[0].created_by == "agent-1"
        assert history[1].version == 2
        assert history[1].created_by == "agent-2"
        assert history[2].version == 3
        assert history[2].created_by == "agent-1"
    
    async def test_context_metadata(self):
        """Test context metadata tracking."""
        context = SharedContext("test-context", ContextScope.CONVERSATION)
        
        # Set value with metadata
        await context.set(
            "test-key",
            {"data": "value"},
            "agent-1",
            AgentType.CODING,
            "Test value",
            ContextAccessLevel.READ_WRITE,
            datetime.now() + timedelta(hours=1),
            {"tag1", "tag2"}
        )
        
        metadata = await context.get_metadata("test-key")
        assert metadata is not None
        assert metadata.key == "test-key"
        assert metadata.scope == ContextScope.CONVERSATION
        assert metadata.created_by == "agent-1"
        assert metadata.access_level == ContextAccessLevel.READ_WRITE
        assert "tag1" in metadata.tags
        assert "tag2" in metadata.tags
        assert metadata.expires_at is not None
    
    async def test_context_manager_operations(self):
        """Test context manager operations."""
        manager = ContextManager()
        await manager.start()
        
        # Get/create context
        context = await manager.get_context("test-ctx", ContextScope.TASK)
        assert context is not None
        assert context.context_id == "test-ctx"
        assert context.scope == ContextScope.TASK
        
        # Same context should be returned on subsequent calls
        context2 = await manager.get_context("test-ctx", ContextScope.TASK)
        assert context is context2
        
        # Delete context
        deleted = await manager.delete_context("test-ctx", ContextScope.TASK)
        assert deleted is True
        
        # Context should be gone
        context3 = await manager.get_context("test-ctx", ContextScope.TASK, create_if_missing=False)
        assert context3 is None
        
        await manager.stop()
    
    async def test_context_broadcast_update(self):
        """Test broadcasting updates to multiple contexts."""
        manager = ContextManager()
        await manager.start()
        
        # Create multiple contexts
        ctx1 = await manager.get_context("ctx1", ContextScope.TASK)
        ctx2 = await manager.get_context("ctx2", ContextScope.TASK)
        
        # Broadcast update
        update = ContextUpdate(
            sender_id="agent-1",
            sender_type=AgentType.SUPERVISOR,
            subject="Shared Data Update",
            context_key="shared_data",
            context_data={"broadcast": True},
            update_type="update"
        )
        
        updated_contexts = await manager.broadcast_update(update, [ContextScope.TASK])
        assert len(updated_contexts) == 2
        
        # Check both contexts received the update
        value1 = await ctx1.get("shared_data")
        value2 = await ctx2.get("shared_data")
        
        assert value1 == {"broadcast": True}
        assert value2 == {"broadcast": True}
        
        await manager.stop()


@pytest.mark.asyncio
class TestConflictResolver:
    """Test suite for conflict resolution strategies."""
    
    async def test_conflict_creation(self):
        """Test conflict creation and management."""
        resolver = ConflictResolver()
        
        conflict = await resolver.create_conflict(
            "test-conflict",
            ConflictType.STRATEGY_CHOICE,
            "Test conflict description",
            ConflictSeverity.MEDIUM,
            ["resource1", "resource2"],
            ["agent1", "agent2"]
        )
        
        assert conflict.context.conflict_id == "test-conflict"
        assert conflict.context.conflict_type == ConflictType.STRATEGY_CHOICE
        assert conflict.context.severity == ConflictSeverity.MEDIUM
        assert len(conflict.context.affected_resources) == 2
        assert len(conflict.context.stakeholder_agents) == 2
        assert len(conflict.positions) == 0
    
    async def test_agent_positions(self):
        """Test adding agent positions to conflicts."""
        resolver = ConflictResolver()
        
        conflict = await resolver.create_conflict(
            "test-conflict",
            ConflictType.TASK_ASSIGNMENT,
            "Task assignment conflict",
            ConflictSeverity.HIGH
        )
        
        # Add positions from different agents
        await resolver.add_position(
            "test-conflict",
            "agent-1",
            AgentType.CODING,
            {"approach": "method_a"},
            0.8,
            "Method A is more efficient"
        )
        
        await resolver.add_position(
            "test-conflict",
            "agent-2", 
            AgentType.REASONING,
            {"approach": "method_b"},
            0.9,
            "Method B is more reliable"
        )
        
        retrieved_conflict = resolver.get_conflict("test-conflict")
        assert len(retrieved_conflict.positions) == 2
        
        position1 = retrieved_conflict.get_position("agent-1")
        assert position1 is not None
        assert position1.position_data == {"approach": "method_a"}
        assert position1.confidence == 0.8
    
    async def test_majority_vote_resolution(self):
        """Test majority vote conflict resolution."""
        resolver = ConflictResolver()
        
        conflict = await resolver.create_conflict(
            "majority-test",
            ConflictType.STRATEGY_CHOICE,
            "Majority vote test",
            ConflictSeverity.HIGH  # Use HIGH to avoid auto-resolution
        )
        
        # Add positions - 2 for option A, 1 for option B
        await resolver.add_position(
            "majority-test",
            "agent-1",
            AgentType.CODING,
            "option_a",
            0.7
        )
        
        await resolver.add_position(
            "majority-test",
            "agent-2",
            AgentType.REASONING,
            "option_a",
            0.8
        )
        
        await resolver.add_position(
            "majority-test",
            "agent-3",
            AgentType.RESEARCH,
            "option_b",
            0.9
        )
        
        # Resolve using majority vote
        result = await resolver.resolve_conflict(
            "majority-test",
            ResolutionStrategy.MAJORITY_VOTE
        )
        
        assert result == "option_a"  # Should win with 2 votes vs 1
    
    async def test_priority_based_resolution(self):
        """Test priority-based conflict resolution."""
        resolver = ConflictResolver()
        
        conflict = await resolver.create_conflict(
            "priority-test",
            ConflictType.TASK_ASSIGNMENT,
            "Priority-based test",
            ConflictSeverity.HIGH
        )
        
        # Add positions from different agent types
        await resolver.add_position(
            "priority-test",
            "agent-coding",
            AgentType.CODING,
            "coding_solution",
            0.7
        )
        
        await resolver.add_position(
            "priority-test",
            "agent-supervisor",
            AgentType.SUPERVISOR,
            "supervisor_solution",
            0.6  # Lower confidence but higher priority type
        )
        
        # Resolve using priority-based strategy
        result = await resolver.resolve_conflict(
            "priority-test",
            ResolutionStrategy.PRIORITY_BASED
        )
        
        assert result == "supervisor_solution"  # Supervisor should win despite lower confidence
    
    async def test_weighted_vote_resolution(self):
        """Test weighted vote resolution with expertise."""
        resolver = ConflictResolver()
        
        # Manually set some expertise scores
        resolver._agent_expertise["expert-agent"]["strategy_choice"] = 0.9
        resolver._agent_expertise["novice-agent"]["strategy_choice"] = 0.3
        
        conflict = await resolver.create_conflict(
            "weighted-test",
            ConflictType.STRATEGY_CHOICE,
            "Weighted vote test",
            ConflictSeverity.HIGH
        )
        
        await resolver.add_position(
            "weighted-test",
            "expert-agent",
            AgentType.REASONING,
            "expert_choice",
            0.9
        )
        
        await resolver.add_position(
            "weighted-test",
            "novice-agent",
            AgentType.CODING,
            "novice_choice",
            0.8
        )
        
        result = await resolver.resolve_conflict(
            "weighted-test",
            ResolutionStrategy.WEIGHTED_VOTE
        )
        
        # Expert should win despite there being only one vote for each option
        # because the expert has higher weight
        assert result == "expert_choice"
    
    async def test_conflict_escalation(self):
        """Test conflict escalation when resolution fails."""
        resolver = ConflictResolver()
        
        conflict = await resolver.create_conflict(
            "escalation-test",
            ConflictType.RESOURCE_ACCESS,
            "Escalation test",
            deadline=datetime.now() - timedelta(minutes=1)  # Already expired
        )
        
        await resolver.add_position(
            "escalation-test",
            "agent-1",
            AgentType.CODING,
            "position1",
            0.5
        )
        
        # Try to resolve expired conflict
        result = await resolver.resolve_conflict("escalation-test")
        
        assert isinstance(result, dict)
        assert result.get("escalated") is True
        assert "deadline_exceeded" in result.get("reason", "")
    
    async def test_conflict_resolver_stats(self):
        """Test conflict resolver statistics tracking."""
        resolver = ConflictResolver()
        
        # Create and resolve a conflict
        await resolver.create_conflict(
            "stats-test",
            ConflictType.STRATEGY_CHOICE,
            "Statistics test"
        )
        
        await resolver.add_position(
            "stats-test",
            "agent-1",
            AgentType.CODING,
            "solution",
            0.8
        )
        
        await resolver.resolve_conflict("stats-test", ResolutionStrategy.EXPERT_OVERRIDE)
        
        stats = resolver.get_stats()
        
        assert stats["total_conflicts"] == 1
        assert stats["successful_resolutions"] == 1
        assert stats["active_conflicts"] == 0
        assert stats["resolved_conflicts"] == 1
        assert ResolutionStrategy.EXPERT_OVERRIDE.value in stats["strategy_effectiveness"]


@pytest.mark.asyncio
class TestIntegrationScenarios:
    """Integration tests for complete communication workflows."""
    
    async def test_multi_agent_workflow_communication(self):
        """Test complete multi-agent workflow with communication."""
        # Setup components
        message_bus = MessageBus()
        context_manager = ContextManager()
        conflict_resolver = ConflictResolver()
        
        await message_bus.start()
        await context_manager.start()
        
        # Track received messages
        received_messages = []

        # Create message handlers
        class SupervisorHandler(MessageHandler):
            def __init__(self):
                super().__init__("supervisor")
                
            async def handle_message(self, message: AgentMessage) -> Optional[AgentMessage]:
                received_messages.append(("supervisor", message))
                
                # Supervisor processes task requests
                if message.type == MessageType.REQUEST:
                    # Update shared context
                    context = await context_manager.get_context("workflow", ContextScope.WORKFLOW)
                    await context.set(
                        "current_task",
                        message.parameters,
                        "supervisor",
                        AgentType.SUPERVISOR,
                        "Task assignment"
                    )
                    
                    # Send response
                    response = ResponseMessage(
                        sender_id="supervisor",
                        sender_type=AgentType.SUPERVISOR,
                        recipient_id=message.sender_id,
                        subject="Task Assignment Response",
                        request_id=message.metadata.message_id,
                        success=True,
                        result={"status": "assigned"}
                    )
                    await message_bus.send_message(response)
                return None
        
        class CodingAgentHandler(MessageHandler):
            def __init__(self):
                super().__init__("coding-agent")
                
            async def handle_message(self, message: AgentMessage) -> Optional[AgentMessage]:
                received_messages.append(("coding", message))
                return None
        
        supervisor_handler = SupervisorHandler()
        coding_agent_handler = CodingAgentHandler()
        
        # Subscribe agents to messages
        message_bus.subscribe(supervisor_handler, {MessageType.REQUEST})
        message_bus.subscribe(coding_agent_handler, {MessageType.RESPONSE})
        
        # Simulate workflow
        task_request = RequestMessage(
            sender_id="coding-agent",
            sender_type=AgentType.CODING,
            recipient_id="supervisor",
            subject="Task Assignment Request",
            service="task_assignment",
            parameters={"task": "implement_feature_x"}
        )
        
        await message_bus.send_message(task_request)
        
        # Wait for processing
        await asyncio.sleep(0.2)
        
        # Verify communication happened
        supervisor_messages = [msg for agent, msg in received_messages if agent == "supervisor"]
        coding_messages = [msg for agent, msg in received_messages if agent == "coding"]
        
        assert len(supervisor_messages) == 1
        assert len(coding_messages) == 1
        assert supervisor_messages[0].type == MessageType.REQUEST
        assert coding_messages[0].type == MessageType.RESPONSE
        
        # Verify context was updated
        context = await context_manager.get_context("workflow", ContextScope.WORKFLOW)
        task_data = await context.get("current_task")
        assert task_data == {"task": "implement_feature_x"}
        
        # Cleanup
        await message_bus.stop()
        await context_manager.stop()
    
    async def test_conflict_resolution_workflow(self):
        """Test conflict resolution in multi-agent workflow."""
        resolver = ConflictResolver()
        
        # Create conflict scenario: two agents propose different solutions
        conflict = await resolver.create_conflict(
            "implementation-conflict",
            ConflictType.STRATEGY_CHOICE,
            "Two agents propose different implementation approaches",
            ConflictSeverity.HIGH
        )
        
        # Agent 1 proposes approach A
        await resolver.add_position(
            "implementation-conflict",
            "coding-agent-1",
            AgentType.CODING,
            {
                "approach": "microservices",
                "estimated_time": 5,
                "complexity": "high",
                "maintainability": "excellent"
            },
            0.8,
            "Microservices provide better scalability and maintainability"
        )
        
        # Agent 2 proposes approach B
        await resolver.add_position(
            "implementation-conflict",
            "coding-agent-2",
            AgentType.CODING,
            {
                "approach": "monolithic",
                "estimated_time": 2,
                "complexity": "medium",
                "maintainability": "good"
            },
            0.7,
            "Monolithic is faster to implement and simpler for current requirements"
        )
        
        # Supervisor agent provides expert opinion
        await resolver.add_position(
            "implementation-conflict",
            "supervisor",
            AgentType.SUPERVISOR,
            {
                "approach": "microservices",
                "estimated_time": 5,
                "complexity": "high",
                "maintainability": "excellent",
                "strategic_alignment": "high"
            },
            0.9,
            "Microservices align better with long-term architecture goals"
        )
        
        # Resolve conflict using weighted voting
        result = await resolver.resolve_conflict(
            "implementation-conflict",
            ResolutionStrategy.WEIGHTED_VOTE
        )
        
        # Should resolve to microservices due to supervisor's high weight
        assert result["approach"] == "microservices"
        
        # Verify conflict is resolved (moved from active to resolved)
        active_conflict = resolver.get_conflict("implementation-conflict")
        assert active_conflict is None  # Should be None as it's been resolved
    
    async def test_context_synchronization_across_agents(self):
        """Test context synchronization across multiple agents."""
        context_manager = ContextManager()
        await context_manager.start()
        
        # Create contexts for different scopes
        global_ctx = await context_manager.get_context("global", ContextScope.GLOBAL)
        workflow_ctx = await context_manager.get_context("wf-001", ContextScope.WORKFLOW)
        task_ctx = await context_manager.get_context("task-001", ContextScope.TASK)
        
        # Simulate different agents updating different contexts
        await global_ctx.set(
            "system_config",
            {"max_agents": 5, "timeout": 30},
            "system",
            AgentType.SUPERVISOR,
            "System configuration"
        )
        
        await workflow_ctx.set(
            "current_phase",
            "implementation",
            "supervisor",
            AgentType.SUPERVISOR,
            "Workflow phase update"
        )
        
        await task_ctx.set(
            "assigned_agent",
            "coding-agent-1",
            "supervisor",
            AgentType.SUPERVISOR,
            "Task assignment"
        )
        
        # Broadcast update to workflow contexts
        update = ContextUpdate(
            sender_id="supervisor",
            sender_type=AgentType.SUPERVISOR,
            subject="Priority Update",
            context_key="priority",
            context_data={"priority": "high"},
            update_type="update"
        )
        
        updated_contexts = await context_manager.broadcast_update(
            update,
            [ContextScope.WORKFLOW]
        )
        
        # Verify update was applied
        assert len(updated_contexts) >= 1
        priority = await workflow_ctx.get("priority")
        assert priority == {"priority": "high"}  # Updated to match dict format
        
        # Test context stats
        stats = context_manager.get_stats()
        assert stats["total_contexts"] >= 3
        assert "global" in stats["contexts_by_scope"]
        assert "workflow" in stats["contexts_by_scope"]
        assert "task" in stats["contexts_by_scope"]
        
        await context_manager.stop()


@pytest.mark.asyncio
class TestPerformanceAndReliability:
    """Test suite for performance and reliability characteristics."""
    
    async def test_message_bus_throughput(self):
        """Test message bus can handle high throughput."""
        bus = MessageBus(max_queue_size=5000)
        await bus.start()
        
        received_count = 0
        
        class ThroughputHandler(MessageHandler):
            def __init__(self):
                super().__init__("test-agent")
            
            async def handle_message(self, message: AgentMessage) -> Optional[AgentMessage]:
                nonlocal received_count
                received_count += 1
                return None
        
        throughput_handler = ThroughputHandler()
        bus.subscribe(throughput_handler, {MessageType.NOTIFICATION})
        
        # Send many messages rapidly
        message_count = 100
        for i in range(message_count):
            message = NotificationMessage(
                sender_id="sender",
                sender_type=AgentType.CODING,
                subject=f"Message {i}",
                event_type="throughput_test",
                event_data={"index": i}
            )
            await bus.send_message(message)
        
        # Wait for processing
        await asyncio.sleep(1.0)
        
        # Should have received all messages
        assert received_count == message_count
        
        await bus.stop()
    
    async def test_context_concurrent_access(self):
        """Test context manager handles concurrent access correctly."""
        context = SharedContext("concurrent-test", ContextScope.TASK)
        
        # Simulate concurrent updates
        async def update_worker(worker_id: int):
            for i in range(10):
                await context.set(
                    f"key_{worker_id}_{i}",
                    f"value_{worker_id}_{i}",
                    f"agent-{worker_id}",
                    AgentType.CODING,
                    f"Update {i} from worker {worker_id}"
                )
        
        # Run multiple workers concurrently
        workers = [update_worker(i) for i in range(5)]
        await asyncio.gather(*workers)
        
        # Verify all updates were applied
        stats = context.get_stats()
        assert stats["key_count"] == 50  # 5 workers * 10 updates each
        assert stats["version_count"] == 50
    
    async def test_conflict_resolver_performance(self):
        """Test conflict resolver performance with many conflicts."""
        resolver = ConflictResolver()
        
        # Create multiple conflicts
        conflict_count = 20
        for i in range(conflict_count):
            await resolver.create_conflict(
                f"perf-conflict-{i}",
                ConflictType.STRATEGY_CHOICE,
                f"Performance test conflict {i}",
                ConflictSeverity.LOW
            )
            
            # Add positions
            await resolver.add_position(
                f"perf-conflict-{i}",
                "agent-1",
                AgentType.CODING,
                f"solution_a_{i}",
                0.7
            )
            
            await resolver.add_position(
                f"perf-conflict-{i}",
                "agent-2",
                AgentType.REASONING,
                f"solution_b_{i}",
                0.8
            )
        
        # Resolve all conflicts
        start_time = asyncio.get_event_loop().time()
        
        for i in range(conflict_count):
            await resolver.resolve_conflict(f"perf-conflict-{i}")
        
        end_time = asyncio.get_event_loop().time()
        resolution_time = end_time - start_time
        
        # Should resolve quickly (less than 1 second for 20 conflicts)
        assert resolution_time < 1.0
        
        # Verify all conflicts were resolved
        stats = resolver.get_stats()
        assert stats["resolved_conflicts"] == conflict_count
        assert stats["successful_resolutions"] == conflict_count
    
    async def test_error_handling_and_recovery(self):
        """Test error handling and recovery mechanisms."""
        bus = MessageBus()
        await bus.start()
        
        # Handler that raises exceptions
        error_count = 0
        
        class FaultyHandler(MessageHandler):
            def __init__(self):
                super().__init__("test-agent")
            
            async def handle_message(self, message: AgentMessage) -> Optional[AgentMessage]:
                nonlocal error_count
                error_count += 1
                if error_count <= 2:
                    raise Exception(f"Handler error {error_count}")
                # Succeed on third try
                return None
        
        faulty_handler = FaultyHandler()
        bus.subscribe(faulty_handler, {MessageType.REQUEST})
        
        # Send message that will cause handler errors
        message = RequestMessage(
            sender_id="sender",
            sender_type=AgentType.CODING,
            recipient_id="test-agent",
            subject="Error Test",
            service="error_test",
            parameters={}
        )
        
        # Bus should handle errors gracefully and continue processing
        await bus.send_message(message)
        await asyncio.sleep(0.1)
        
        # Send another message that should succeed
        success_message = RequestMessage(
            sender_id="sender",
            sender_type=AgentType.CODING,
            recipient_id="test-agent",
            subject="Success Test",
            service="success_test",
            parameters={}
        )
        
        await bus.send_message(success_message)
        await asyncio.sleep(0.1)
        
        # Should have attempted to process both messages
        assert error_count >= 2
        
        await bus.stop()


if __name__ == "__main__":
    # Run tests
    pytest.main([__file__, "-v", "--tb=short"])
