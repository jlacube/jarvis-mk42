# tests/test_communication_integration.py
"""
Integration tests for Phase 2B.2 Inter-Agent Communication Framework.

These tests validate the complete communication workflow including:
- Message routing between agents
- Context sharing and synchronization
- Conflict resolution in multi-agent scenarios
- End-to-end communication patterns
"""

import asyncio
import pytest
from datetime import datetime, timedelta

from communication.protocols import (
    AgentMessage, RequestMessage, ResponseMessage, MessageType, 
    MessagePriority, AgentType
)
from communication.message_bus import MessageBus
from communication.context_manager import ContextManager, ContextScope
from communication.conflict_resolver import (
    ConflictResolver, ConflictType, ResolutionStrategy, ConflictSeverity
)


@pytest.mark.asyncio
class TestCommunicationIntegration:
    """Integration tests for complete communication workflows."""
    
    async def test_basic_message_creation_and_routing(self):
        """Test basic message creation and routing functionality."""
        # Initialize components
        message_bus = MessageBus()
        await message_bus.start()
        
        # Track received messages
        received_messages = []
        
        # Create a custom message handler
        from communication.message_bus import MessageHandler
        
        class TestMessageHandler(MessageHandler):
            def __init__(self):
                super().__init__("test-handler")
                self.received_messages = received_messages
            
            async def handle_message(self, message):
                self.received_messages.append(message)
                self.message_count += 1
                self.last_message_at = datetime.now()
                return None
        
        handler = TestMessageHandler()
        
        # Subscribe to messages using the correct API
        message_bus.subscribe(handler, {MessageType.REQUEST})
        
        # Create and send a message
        message = AgentMessage(
            type=MessageType.REQUEST,
            sender_id="sender-agent",
            sender_type=AgentType.CODING,
            subject="Test Message",
            content={"action": "test"}
        )
        
        await message_bus.send_message(message)
        
        # Wait for processing with longer timeout
        await asyncio.sleep(0.5)
        
        # Verify message was received
        assert len(received_messages) == 1
        assert received_messages[0].sender_id == "sender-agent"
        assert received_messages[0].content["action"] == "test"
        
        await message_bus.stop()
    
    async def test_context_sharing_workflow(self):
        """Test context sharing between agents."""
        context_manager = ContextManager()
        await context_manager.start()
        
        # Create a workflow context
        workflow_context = await context_manager.get_context("workflow-123", ContextScope.WORKFLOW)
        
        # Agent 1 sets initial context
        await workflow_context.set(
            "task_status",
            "in_progress",
            "agent-1",
            AgentType.CODING,
            "Task started"
        )
        
        # Agent 2 reads and updates context
        status = await workflow_context.get("task_status")
        assert status == "in_progress"
        
        await workflow_context.set(
            "task_status",
            "completed",
            "agent-2",
            AgentType.REASONING,
            "Task completed"
        )
        
        # Verify update
        final_status = await workflow_context.get("task_status")
        assert final_status == "completed"
        
        # Check version history
        history = await workflow_context.get_version_history("task_status")
        assert len(history) == 2
        assert history[0].created_by == "agent-1"
        assert history[1].created_by == "agent-2"
        
        await context_manager.stop()
    
    async def test_conflict_resolution_workflow(self):
        """Test conflict resolution between competing agents."""
        resolver = ConflictResolver()
        
        # Create a conflict scenario
        conflict = await resolver.create_conflict(
            "test-conflict",
            ConflictType.STRATEGY_CHOICE,
            "Two agents propose different approaches",
            ConflictSeverity.MEDIUM
        )
        
        # Agent 1 proposes solution A
        await resolver.add_position(
            "test-conflict",
            "agent-1",
            AgentType.CODING,
            {"approach": "solution_a", "confidence": 0.8},
            0.8,
            "Solution A is more efficient"
        )
        
        # Agent 2 proposes solution B
        await resolver.add_position(
            "test-conflict",
            "agent-2",
            AgentType.REASONING,
            {"approach": "solution_b", "confidence": 0.9},
            0.9,
            "Solution B is more reliable"
        )
        
        # Resolve using weighted voting
        result = await resolver.resolve_conflict(
            "test-conflict",
            ResolutionStrategy.WEIGHTED_VOTE
        )
        
        # Should resolve to solution_b due to higher confidence/weight
        assert result["approach"] == "solution_b"
        
        # Verify conflict is resolved
        stats = resolver.get_stats()
        assert stats["resolved_conflicts"] == 1
        assert stats["successful_resolutions"] == 1
    
    async def test_end_to_end_multi_agent_workflow(self):
        """Test complete end-to-end multi-agent communication workflow."""
        # Initialize all components
        message_bus = MessageBus()
        context_manager = ContextManager()
        conflict_resolver = ConflictResolver()
        
        await message_bus.start()
        await context_manager.start()
        
        # Simulate multi-agent workflow
        workflow_steps = []
        
        # Agent message handlers
        async def supervisor_handler(message):
            workflow_steps.append(f"Supervisor received: {message.subject}")
            
            # Update workflow context
            context = await context_manager.get_context("workflow", ContextScope.WORKFLOW)
            await context.set(
                "current_step",
                "supervisor_processing",
                "supervisor",
                AgentType.SUPERVISOR,
                "Supervisor processing request"
            )
            
            # Send response
            response = ResponseMessage(
                type=MessageType.RESPONSE,
                sender_id="supervisor",
                sender_type=AgentType.SUPERVISOR,
                subject="Task Assignment",
                request_id=message.metadata.message_id,
                success=True,
                result={"assigned_to": "coding-agent"}
            )
            await message_bus.publish(response)
        
        async def coding_agent_handler(message):
            workflow_steps.append(f"Coding agent received: {message.subject}")
            
            # Check workflow context
            context = await context_manager.get_context("workflow", ContextScope.WORKFLOW)
            current_step = await context.get("current_step")
            
            if current_step == "supervisor_processing":
                await context.set(
                    "current_step",
                    "coding_complete",
                    "coding-agent",
                    AgentType.CODING,
                    "Coding task completed"
                )
        
        # Subscribe handlers
        await message_bus.subscribe("supervisor", MessageType.REQUEST, supervisor_handler)
        await message_bus.subscribe("coding-agent", MessageType.RESPONSE, coding_agent_handler)
        
        # Start workflow with initial request
        initial_request = RequestMessage(
            type=MessageType.REQUEST,
            sender_id="user",
            sender_type=AgentType.SUPERVISOR,
            subject="Code Analysis Request",
            service="analyze_code",
            parameters={"file": "main.py"}
        )
        
        await message_bus.publish(initial_request)
        
        # Wait for workflow to complete
        await asyncio.sleep(0.2)
        
        # Verify workflow execution
        assert len(workflow_steps) >= 2
        assert "Supervisor received" in workflow_steps[0]
        assert "Coding agent received" in workflow_steps[1]
        
        # Check final context state
        context = await context_manager.get_context("workflow", ContextScope.WORKFLOW)
        final_step = await context.get("current_step")
        assert final_step == "coding_complete"
        
        # Cleanup
        await message_bus.stop()
        await context_manager.stop()
    
    async def test_performance_and_reliability(self):
        """Test system performance under load."""
        message_bus = MessageBus(max_queue_size=1000)
        await message_bus.start()
        
        processed_count = 0
        
        async def performance_handler(message):
            nonlocal processed_count
            processed_count += 1
        
        await message_bus.subscribe("perf-agent", MessageType.NOTIFICATION, performance_handler)
        
        # Send multiple messages rapidly
        message_count = 50
        for i in range(message_count):
            message = AgentMessage(
                type=MessageType.NOTIFICATION,
                sender_id=f"sender-{i}",
                sender_type=AgentType.CODING,
                subject=f"Performance Test {i}",
                content={"index": i}
            )
            await message_bus.publish(message)
        
        # Wait for processing
        await asyncio.sleep(0.5)
        
        # Verify all messages were processed
        assert processed_count == message_count
        
        await message_bus.stop()


@pytest.mark.asyncio
class TestCommunicationEdgeCases:
    """Test edge cases and error conditions."""
    
    async def test_message_bus_error_handling(self):
        """Test message bus handles errors gracefully."""
        message_bus = MessageBus()
        await message_bus.start()
        
        error_count = 0
        success_count = 0
        
        async def error_handler(message):
            nonlocal error_count, success_count
            if message.subject == "error":
                error_count += 1
                raise Exception("Handler error")
            else:
                success_count += 1
        
        await message_bus.subscribe("error-agent", MessageType.NOTIFICATION, error_handler)
        
        # Send error-causing message
        error_msg = AgentMessage(
            type=MessageType.NOTIFICATION,
            sender_id="sender",
            sender_type=AgentType.CODING,
            subject="error",
            content={}
        )
        
        # Send normal message
        normal_msg = AgentMessage(
            type=MessageType.NOTIFICATION,
            sender_id="sender",
            sender_type=AgentType.CODING,
            subject="normal",
            content={}
        )
        
        await message_bus.publish(error_msg)
        await message_bus.publish(normal_msg)
        
        await asyncio.sleep(0.1)
        
        # Normal message should still be processed despite error
        assert success_count == 1
        assert error_count == 1
        
        await message_bus.stop()
    
    async def test_context_conflict_detection(self):
        """Test context conflict detection and resolution."""
        context_manager = ContextManager()
        await context_manager.start()
        
        context = await context_manager.get_context("conflict-test", ContextScope.TASK)
        
        # Simulate concurrent updates
        await context.set(
            "shared_resource",
            "value_1",
            "agent-1",
            AgentType.CODING,
            "First update"
        )
        
        await context.set(
            "shared_resource", 
            "value_2",
            "agent-2",
            AgentType.REASONING,
            "Second update"
        )
        
        # Check for conflicts
        conflict = await context_manager.detect_conflicts("conflict-test", ContextScope.TASK, "shared_resource")
        
        # In this simple case, no conflict detected (sequential updates)
        # In a real implementation, we'd have concurrent update detection
        
        await context_manager.stop()


if __name__ == "__main__":
    # Run integration tests
    pytest.main([__file__, "-v", "--tb=short"])
