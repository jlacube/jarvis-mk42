import pytest
import os
import json

from tools.reasoning_tools import sequential_thinking_tool, generate_summary, clear_history

@pytest.mark.asyncio
async def test_sequential_thinking_flow():
    """Test the complete flow of sequential thinking tools."""
    user_id = "test_user"
    thread_id = "test_thread"
    
    # First, clear any existing history
    clear_result = await clear_history.ainvoke({"user_id": user_id, "thread_id": thread_id})
    assert clear_result["status"] == "success", "Clearing history should succeed"
    
    # Add first thought
    result1 = await sequential_thinking_tool.ainvoke({
        "user_id": user_id,
        "thread_id": thread_id,
        "thought": "I need to analyze the problem carefully.",
        "thought_number": 1,
        "total_thoughts": 3
    })
    
    # Parse the JSON string from the response content
    result1_json = json.loads(result1["content"][0]["text"])
    
    # Check if first thought was added successfully
    assert "thoughtNumber" in result1_json, f"Result should contain thoughtNumber field: {result1_json}"
    assert result1_json["thoughtNumber"] == 1, f"First thought should have number 1, got: {result1_json}"
    
    # Add second thought
    result2 = await sequential_thinking_tool.ainvoke({
        "user_id": user_id,
        "thread_id": thread_id,
        "thought": "The problem has several components that need to be addressed separately.",
        "thought_number": 2,
        "total_thoughts": 3
    })
    
    # Parse the JSON string from the response content
    result2_json = json.loads(result2["content"][0]["text"])
    
    # Check if second thought was added successfully
    assert result2_json["thoughtNumber"] == 2, f"Second thought should have number 2, got: {result2_json}"
      # Add third thought
    result3 = await sequential_thinking_tool.ainvoke({
        "user_id": user_id,
        "thread_id": thread_id,
        "thought": "I have identified the solution approach.",
        "thought_number": 3,
        "total_thoughts": 3,
        "next_thought_needed": False
    })
    
    # Parse the JSON string from the response content
    result3_json = json.loads(result3["content"][0]["text"])
    
    # Check if third thought was added successfully
    assert result3_json["thoughtNumber"] == 3, f"Third thought should have number 3, got: {result3_json}"
      # Generate summary
    summary = await generate_summary.ainvoke({"user_id": user_id, "thread_id": thread_id})
    
    # Check if summary contains all thoughts
    assert "totalThoughts" in summary["summary"], f"Summary should contain totalThoughts field: {summary}"
    assert summary["summary"]["totalThoughts"] == 3, f"Summary should have 3 thoughts, got: {summary}"
    
    # Check if timeline contains all thoughts
    assert "timeline" in summary["summary"], f"Summary should contain timeline field: {summary}"
    assert len(summary["summary"]["timeline"]) == 3, f"Timeline should have 3 entries, got: {summary}"
    
    # Clean up
    clear_result = await clear_history.ainvoke({"user_id": user_id, "thread_id": thread_id})
    assert clear_result["status"] == "success", "Clearing history should succeed"

@pytest.mark.asyncio
async def test_thought_revision():
    """Test the revision capability of sequential thinking."""
    user_id = "test_user"
    thread_id = "test_thread"
    
    # First, clear any existing history
    await clear_history.ainvoke({"user_id": user_id, "thread_id": thread_id})
    
    # Add first thought
    await sequential_thinking_tool.ainvoke({
        "user_id": user_id,
        "thread_id": thread_id,
        "thought": "Initial approach to the problem.",
        "thought_number": 1,
        "total_thoughts": 3
    })
    
    # Add second thought
    await sequential_thinking_tool.ainvoke({
        "user_id": user_id,
        "thread_id": thread_id,
        "thought": "Upon further reflection, this approach has flaws.",
        "thought_number": 2,
        "total_thoughts": 3
    })
      # Revise first thought
    revision_result = await sequential_thinking_tool.ainvoke({
        "user_id": user_id,
        "thread_id": thread_id,
        "thought": "A better initial approach would be...",
        "thought_number": 3,
        "total_thoughts": 3,
        "is_revision": True,
        "revises_thought": 1
    })
    
    # Parse the JSON string from the response content
    revision_result_json = json.loads(revision_result["content"][0]["text"])
    
    # Generate summary to verify revision is reflected
    summary = await generate_summary.ainvoke({"user_id": user_id, "thread_id": thread_id})
    
    # Find the revised thought in the timeline
    revised_thoughts = [t for t in summary["summary"]["timeline"] if t["number"] == 3]
    assert len(revised_thoughts) == 1, f"Should have thought with number 3: {summary}"
    
    # Clean up
    await clear_history.ainvoke({"user_id": user_id, "thread_id": thread_id})
