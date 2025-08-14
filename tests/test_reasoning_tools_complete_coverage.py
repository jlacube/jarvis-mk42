"""
Complete test coverage for tools.reasoning_tools module.
Targets missing lines: 37, 39, 41, 43, 45, 47, 71-72, 109, 114-116, 133-134, 241, 245, 275, 283
"""
import pytest
from unittest.mock import patch, MagicMock
import json

from tools.reasoning_tools import (
    sequential_thinking_tool, 
    generate_summary, 
    clear_history,
    sequential_thinking_server,
    SequentialThinkingServer,
    ThoughtData,
    get_reasoning_tools
)


class TestReasoningToolsCompleteCoverage:
    """Test all missing lines in reasoning tools for 100% coverage."""

    def setup_method(self):
        """Reset the server state before each test."""
        sequential_thinking_server.thought_history.clear()
        sequential_thinking_server.branches.clear()

    @pytest.mark.asyncio
    async def test_thought_number_adjustment(self):
        """Test thought number exceeding total thoughts (line 109)."""
        result = await sequential_thinking_tool.ainvoke({
            "user_id": "user1",
            "thread_id": "thread1", 
            "thought": "Exceeding total",
            "thought_number": 5,  # Greater than total_thoughts
            "total_thoughts": 3,  # Should be adjusted to 5
            "next_thought_needed": False
        })
        
        response_data = json.loads(result["content"][0]["text"])
        assert response_data["thoughtNumber"] == 5
        assert response_data["totalThoughts"] == 5  # Should be adjusted

    @pytest.mark.asyncio
    async def test_branch_creation_and_tracking(self):
        """Test branch creation and tracking (lines 114-116)."""
        # Create first thought
        await sequential_thinking_tool.ainvoke({
            "user_id": "user1",
            "thread_id": "thread1",
            "thought": "Initial thought",
            "thought_number": 1,
            "total_thoughts": 3,
            "next_thought_needed": True
        })

        # Create a branch
        result = await sequential_thinking_tool.ainvoke({
            "user_id": "user1",
            "thread_id": "thread1",
            "thought": "Branch thought",
            "thought_number": 2,
            "total_thoughts": 3,
            "branch_from_thought": 1,
            "branch_id": "exploration_branch",
            "next_thought_needed": True
        })

        # Verify branch was created and tracked
        response_data = json.loads(result["content"][0]["text"])
        assert "exploration_branch" in response_data["branches"]
        
        # Verify the branch exists in server state
        assert "exploration_branch" in sequential_thinking_server.branches
        assert len(sequential_thinking_server.branches["exploration_branch"]) == 1

    @pytest.mark.asyncio
    async def test_exception_handling(self):
        """Test exception handling path (lines 133-134)."""
        # Mock the server to raise an exception
        with patch.object(sequential_thinking_server, 'validate_thought_data', side_effect=Exception("Test error")):
            result = await sequential_thinking_tool.ainvoke({
                "user_id": "user1",
                "thread_id": "thread1",
                "thought": "This will cause an error",
                "thought_number": 1,
                "total_thoughts": 1,
                "next_thought_needed": False
            })
            
            response_data = json.loads(result["content"][0]["text"])
            assert response_data["error"] == "Test error"
            assert response_data["status"] == "failed"

    @pytest.mark.asyncio
    async def test_generate_summary_no_user_history(self):
        """Test summary generation with no user history (line 241)."""
        result = await generate_summary.ainvoke({
            "user_id": "nonexistent_user",
            "thread_id": "thread1"
        })
        
        assert result["summary"] == "No thoughts recorded yet"

    @pytest.mark.asyncio
    async def test_generate_summary_no_thread_history(self):
        """Test summary generation with no thread history (line 245)."""
        # Create user but no thread history
        sequential_thinking_server.thought_history["user1"] = {}
        
        result = await generate_summary.ainvoke({
            "user_id": "user1",
            "thread_id": "nonexistent_thread"
        })
        
        assert result["summary"] == "No thoughts recorded yet"

    @pytest.mark.asyncio
    async def test_clear_thoughts_history_no_user(self):
        """Test clearing history with no user (line 275)."""
        result = await clear_history.ainvoke({
            "user_id": "nonexistent_user",
            "thread_id": "thread1"
        })
        
        assert result["status"] == "success"
        assert result["message"] == "Nothing to clear"

    @pytest.mark.asyncio
    async def test_clear_thoughts_history_no_thread(self):
        """Test clearing history with no thread (line 283)."""
        # Create user but no thread history
        sequential_thinking_server.thought_history["user1"] = {}
        
        result = await clear_history.ainvoke({
            "user_id": "user1",
            "thread_id": "nonexistent_thread"
        })
        
        assert result["status"] == "success"
        assert result["message"] == "Nothing to clear"

    def test_get_reasoning_tools(self):
        """Test get_reasoning_tools function."""
        tools = get_reasoning_tools()
        assert len(tools) == 3
        assert sequential_thinking_tool in tools
        assert generate_summary in tools
        assert clear_history in tools

    @pytest.mark.asyncio
    async def test_complete_workflow_with_branches_and_revisions(self):
        """Test complete workflow to ensure all paths are covered."""
        # Create initial thought
        await sequential_thinking_tool.ainvoke({
            "user_id": "user1",
            "thread_id": "thread1",
            "thought": "Initial analysis",
            "thought_number": 1,
            "total_thoughts": 5,
            "next_thought_needed": True
        })
        
        # Create a branch
        await sequential_thinking_tool.ainvoke({
            "user_id": "user1",
            "thread_id": "thread1", 
            "thought": "Alternative approach",
            "thought_number": 2,
            "total_thoughts": 5,
            "branch_from_thought": 1,
            "branch_id": "alt_approach",
            "next_thought_needed": True
        })
        
        # Create a revision
        await sequential_thinking_tool.ainvoke({
            "user_id": "user1",
            "thread_id": "thread1",
            "thought": "Revised initial analysis",
            "thought_number": 3,
            "total_thoughts": 5,
            "is_revision": True,
            "revises_thought": 1,
            "next_thought_needed": True
        })
        
        # Generate summary
        summary = await generate_summary.ainvoke({
            "user_id": "user1",
            "thread_id": "thread1"
        })
        
        assert summary["summary"]["totalThoughts"] == 3
        assert len(summary["summary"]["timeline"]) == 3
        
        # Clear history
        clear_result = await clear_history.ainvoke({
            "user_id": "user1",
            "thread_id": "thread1"
        })
        
        assert clear_result["status"] == "success"
        assert clear_result["message"] == "Thought history cleared"
        
        # Verify history is cleared - when cleared, it returns empty summary format
        summary_after_clear = await generate_summary.ainvoke({
            "user_id": "user1",
            "thread_id": "thread1"
        })
        
        assert summary_after_clear["summary"]["totalThoughts"] == 0
        assert summary_after_clear["summary"]["timeline"] == []

    @pytest.mark.asyncio
    async def test_validate_thought_data_direct_calls(self):
        """Test validation errors by calling methods directly (lines 37, 39, 41, 43, 45, 47)."""
        # Test invalid user_id type (line 37)
        with pytest.raises(ValueError, match="Invalid user_id: must be a string"):
            sequential_thinking_server.validate_thought_data(
                123, "thread1", "test", 1, 1, False, None, None, None, None, False
            )

        # Test invalid thread_id type (line 39) 
        with pytest.raises(ValueError, match="Invalid thread_id: must be a string"):
            sequential_thinking_server.validate_thought_data(
                "user1", None, "test", 1, 1, False, None, None, None, None, False
            )

        # Test invalid thought type (line 41)
        with pytest.raises(ValueError, match="Invalid thought: must be a string"):
            sequential_thinking_server.validate_thought_data(
                "user1", "thread1", ["not", "string"], 1, 1, False, None, None, None, None, False
            )

        # Test invalid thought_number type (line 43)
        with pytest.raises(ValueError, match="Invalid thoughtNumber: must be a number"):
            sequential_thinking_server.validate_thought_data(
                "user1", "thread1", "test", "not_number", 1, False, None, None, None, None, False
            )

        # Test invalid total_thoughts type (line 45)
        with pytest.raises(ValueError, match="Invalid totalThoughts: must be a number"):
            sequential_thinking_server.validate_thought_data(
                "user1", "thread1", "test", 1, "not_number", False, None, None, None, None, False
            )

        # Test invalid next_thought_needed type (line 47)
        with pytest.raises(ValueError, match="Invalid nextThoughtNeeded: must be a boolean"):
            sequential_thinking_server.validate_thought_data(
                "user1", "thread1", "test", 1, 1, False, None, None, None, None, "not_boolean"
            )

    @pytest.mark.asyncio
    async def test_clear_history_with_existing_data(self):
        """Test clearing history when data exists (lines 277-278)."""
        # Create some history first
        await sequential_thinking_tool.ainvoke({
            "user_id": "user1",
            "thread_id": "thread1",
            "thought": "Test thought",
            "thought_number": 1,
            "total_thoughts": 1,
            "next_thought_needed": False
        })

        # Verify history exists
        summary = await generate_summary.ainvoke({
            "user_id": "user1",
            "thread_id": "thread1"
        })
        assert summary["summary"]["totalThoughts"] == 1

        # Clear history (lines 277-278)
        result = await clear_history.ainvoke({
            "user_id": "user1",
            "thread_id": "thread1"
        })
        
        assert result["status"] == "success"
        assert result["message"] == "Thought history cleared"

        # Verify history is cleared - when cleared, it returns empty summary format  
        summary_after = await generate_summary.ainvoke({
            "user_id": "user1",
            "thread_id": "thread1"
        })
        assert summary_after["summary"]["totalThoughts"] == 0
        assert summary_after["summary"]["timeline"] == []
