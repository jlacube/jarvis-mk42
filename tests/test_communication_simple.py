# tests/test_communication_simple.py
"""
Simple integration tests for Phase 2B.2 Communication Framework.
These tests validate individual components work correctly.
"""

import asyncio
import pytest
from datetime import datetime

from communication.protocols import AgentMessage, MessageType, AgentType
from communication.context_manager import ContextManager, ContextScope
from communication.conflict_resolver import ConflictResolver, ConflictType, ConflictSeverity


@pytest.mark.asyncio
class TestSimpleCommunication:
    """Simple tests for individual components."""
    
    async def test_context_manager_basic_operations(self):
        """Test basic context manager operations."""
        manager = ContextManager()
        await manager.start()
        
        # Create context
        context = await manager.get_context("test", ContextScope.TASK)
        assert context is not None
        
        # Set and get value
        version = await context.set("key1", "value1", "agent1", AgentType.CODING, "test")
        assert version == 1
        
        value = await context.get("key1")
        assert value == "value1"
        
        # Update value
        version2 = await context.set("key1", "value2", "agent1", AgentType.CODING, "update")
        assert version2 == 2
        
        updated_value = await context.get("key1")
        assert updated_value == "value2"
        
        await manager.stop()
        print("✅ Context Manager basic operations work correctly")
    
    async def test_conflict_resolver_basic_operations(self):
        """Test basic conflict resolver operations."""
        resolver = ConflictResolver()
        
        # Create conflict
        conflict = await resolver.create_conflict(
            "test-conflict",
            ConflictType.STRATEGY_CHOICE,
            "Test conflict",
            ConflictSeverity.LOW
        )
        
        assert conflict.context.conflict_id == "test-conflict"
        
        # Add positions
        result1 = await resolver.add_position(
            "test-conflict",
            "agent1",
            AgentType.CODING,
            "option_a",
            0.8
        )
        assert result1 is True
        
        result2 = await resolver.add_position(
            "test-conflict",
            "agent2",
            AgentType.REASONING,
            "option_b",
            0.6
        )
        assert result2 is True
        
        # Get conflict
        retrieved = resolver.get_conflict("test-conflict")
        assert retrieved is not None
        assert len(retrieved.positions) == 2
        
        print("✅ Conflict Resolver basic operations work correctly")
    
    def test_message_protocols(self):
        """Test message protocol creation."""
        # Test AgentMessage
        message = AgentMessage(
            type=MessageType.REQUEST,
            sender_id="test-agent",
            sender_type=AgentType.CODING,
            subject="Test Message",
            content={"test": "data"}
        )
        
        assert message.type == MessageType.REQUEST
        assert message.sender_id == "test-agent"
        assert message.sender_type == AgentType.CODING
        assert message.subject == "Test Message"
        assert message.content["test"] == "data"
        
        print("✅ Message Protocols work correctly")
    
    async def test_complete_workflow_simulation(self):
        """Test a complete workflow using context manager and conflict resolver."""
        # Initialize components
        context_manager = ContextManager()
        conflict_resolver = ConflictResolver()
        
        await context_manager.start()
        
        # Create workflow context
        workflow_ctx = await context_manager.get_context("workflow-123", ContextScope.WORKFLOW)
        
        # Step 1: Initial task assignment
        await workflow_ctx.set(
            "current_task",
            {"type": "code_analysis", "file": "main.py"},
            "supervisor",
            AgentType.SUPERVISOR,
            "Task assigned"
        )
        
        # Step 2: Agents start working and update progress
        await workflow_ctx.set(
            "progress",
            {"coding": 0.3, "analysis": 0.1},
            "coding-agent",
            AgentType.CODING,
            "Progress update"
        )
        
        # Step 3: Conflict arises - different approaches
        conflict = await conflict_resolver.create_conflict(
            "approach-conflict",
            ConflictType.STRATEGY_CHOICE,
            "Different analysis approaches proposed"
        )
        
        await conflict_resolver.add_position(
            "approach-conflict",
            "coding-agent",
            AgentType.CODING,
            {"approach": "static_analysis", "estimated_time": 10},
            0.7,
            "Static analysis is faster"
        )
        
        await conflict_resolver.add_position(
            "approach-conflict",
            "reasoning-agent", 
            AgentType.REASONING,
            {"approach": "dynamic_analysis", "estimated_time": 20},
            0.9,
            "Dynamic analysis is more thorough"
        )
        
        # Step 4: Resolve conflict
        from communication.conflict_resolver import ResolutionStrategy
        resolution = await conflict_resolver.resolve_conflict(
            "approach-conflict",
            ResolutionStrategy.WEIGHTED_VOTE
        )
        
        # Should choose dynamic_analysis due to higher confidence
        assert resolution["approach"] == "dynamic_analysis"
        
        # Step 5: Update workflow with resolution
        await workflow_ctx.set(
            "chosen_approach",
            resolution,
            "supervisor",
            AgentType.SUPERVISOR,
            "Conflict resolved"
        )
        
        # Verify final state
        task = await workflow_ctx.get("current_task")
        approach = await workflow_ctx.get("chosen_approach")
        
        assert task["type"] == "code_analysis"
        assert approach["approach"] == "dynamic_analysis"
        
        # Check stats
        ctx_stats = context_manager.get_stats()
        resolver_stats = conflict_resolver.get_stats()
        
        assert ctx_stats["total_contexts"] >= 1
        assert resolver_stats["resolved_conflicts"] == 1
        
        await context_manager.stop()
        
        print("✅ Complete workflow simulation successful")
        print(f"   - Context operations: {ctx_stats['total_contexts']} contexts")
        print(f"   - Conflict resolution: {resolver_stats['resolved_conflicts']} resolved")


if __name__ == "__main__":
    # Run simple tests
    pytest.main([__file__, "-v", "-s"])
