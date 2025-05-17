#!/usr/bin/env python3

import json
import sys
from typing import Any, Dict, List, Optional, Union

from langchain_core.tools import tool


class ThoughtData:
    def __init__(self, user_id: str, thread_id: str, thought: str, thought_number: int, total_thoughts: int,
                 is_revision: Optional[bool] = None, revises_thought: Optional[int] = None,
                 branch_from_thought: Optional[int] = None, branch_id: Optional[str] = None,
                 needs_more_thoughts: Optional[bool] = None, next_thought_needed: bool = True):
        self.user_id = user_id
        self.thread_id = thread_id
        self.thought = thought
        self.thought_number = thought_number
        self.total_thoughts = total_thoughts
        self.is_revision = is_revision
        self.revises_thought = revises_thought
        self.branch_from_thought = branch_from_thought
        self.branch_id = branch_id
        self.needs_more_thoughts = needs_more_thoughts
        self.next_thought_needed = next_thought_needed

class SequentialThinkingServer:
    def __init__(self):
        self.thought_history: Dict[str, Dict[str, List[ThoughtData]]] = {}
        self.branches: Dict[str, List[ThoughtData]] = {}

    def validate_thought_data(self, user_id: str, thread_id: str, thought: str, thought_number: int, total_thoughts: int,
                 is_revision: Optional[bool], revises_thought: Optional[int],
                 branch_from_thought: Optional[int], branch_id: Optional[str],
                 needs_more_thoughts: Optional[bool], next_thought_needed: bool) -> ThoughtData:
        if not isinstance(user_id, str):
            raise ValueError('Invalid user_id: must be a string')
        if not isinstance(thread_id, str):
            raise ValueError('Invalid thread_id: must be a string')
        if not isinstance(thought, str):
            raise ValueError('Invalid thought: must be a string')
        if not isinstance(thought_number, int):
            raise ValueError('Invalid thoughtNumber: must be a number')
        if not isinstance(total_thoughts, int):
            raise ValueError('Invalid totalThoughts: must be a number')
        if not isinstance(next_thought_needed, bool):
            raise ValueError('Invalid nextThoughtNeeded: must be a boolean')

        return ThoughtData(
            user_id=user_id,
            thread_id=thread_id,
            thought=thought,
            thought_number=thought_number,
            total_thoughts=total_thoughts,
            next_thought_needed=next_thought_needed,
            is_revision=is_revision,
            revises_thought=revises_thought,
            branch_from_thought=branch_from_thought,
            branch_id=branch_id,
            needs_more_thoughts=needs_more_thoughts
        )

    def format_thought(self, thought_data: ThoughtData) -> str:
        prefix = ''
        context = ''

        if thought_data.is_revision:
            prefix = '🔄 Revision'
            context = f' (revising thought {thought_data.revises_thought})'
        elif thought_data.branch_from_thought:
            prefix = '🌿 Branch'
            context = f' (from thought {thought_data.branch_from_thought}, ID: {thought_data.branch_id})'
        else:
            prefix = '💭 Thought'

        header = f'{prefix} {thought_data.thought_number}/{thought_data.total_thoughts}{context}'
        border = str("-" * (max(len(header), len(thought_data.thought)) + 4))

        return f"""
┌{border}┐
│ {header} │
├{border}┤
│ {thought_data.thought.ljust(len(border) - 2)} │
└{border}┘"""

    def append_thought_history(self, history: ThoughtData):
        user_history = self.thought_history.get(history.user_id)
        if user_history is None:
            user_history = {}
            self.thought_history[history.user_id] = user_history

        thread_history = user_history.get(history.thread_id)
        if thread_history is None:
            thread_history = []
            user_history[history.thread_id] = thread_history

        thread_history.append(history)

    def process_thought(self, user_id:str, thread_id:str, thought: str, thought_number: int, total_thoughts: int,
                 is_revision: Optional[bool] = None, revises_thought: Optional[int] = None,
                 branch_from_thought: Optional[int] = None, branch_id: Optional[str] = None,
                 needs_more_thoughts: Optional[bool] = None, next_thought_needed: bool = True) -> Dict[str, Any]:

        try:
            validated_input = self.validate_thought_data(user_id, thread_id, thought, thought_number, total_thoughts,
                 is_revision, revises_thought, branch_from_thought, branch_id, needs_more_thoughts, next_thought_needed)

            if validated_input.thought_number > validated_input.total_thoughts:
                validated_input.total_thoughts = validated_input.thought_number

            self.append_thought_history(validated_input)

            if validated_input.branch_from_thought and validated_input.branch_id:
                if validated_input.branch_id not in self.branches:
                    self.branches[validated_input.branch_id] = []
                self.branches[validated_input.branch_id].append(validated_input)

            formatted_thought = self.format_thought(validated_input)
            print(formatted_thought, file=sys.stderr)

            return {
                "content": [{
                    "type": "text",
                    "text": json.dumps({
                        "thoughtNumber": validated_input.thought_number,
                        "totalThoughts": validated_input.total_thoughts,
                        "nextThoughtNeeded": validated_input.next_thought_needed,
                        "branches": list(self.branches.keys()),
                        "thoughtHistoryLength": len(self.thought_history)
                    }, indent=2)
                }]
            }
        except Exception as error:
            return {
                "content": [{
                    "type": "text",
                    "text": json.dumps({
                        "error": str(error),
                        "status": 'failed'
                    }, indent=2)
                }],
                "isError": True
            }

sequential_thinking_server = SequentialThinkingServer()

@tool
async def sequential_thinking_tool(user_id: str, thread_id: str, thought: str, thought_number: int, total_thoughts: int,
                 is_revision: Optional[bool] = None, revises_thought: Optional[int] = None,
                 branch_from_thought: Optional[int] = None, branch_id: Optional[str] = None,
                 needs_more_thoughts: Optional[bool] = None, next_thought_needed: bool = True):
    """
    A detailed tool for dynamic and reflective problem-solving through thoughts.

    This tool helps analyze problems through a flexible thinking process that can adapt and evolve.

    Each thought can build on, question, or revise previous insights as understanding deepens.

    When to use this tool:
    - Breaking down complex problems into steps
    - Planning and design with room for revision
    - Analysis that might need course correction
    - Problems where the full scope might not be clear initially
    - Problems that require a multi-step solution
    - Tasks that need to maintain context over multiple steps
    - Situations where irrelevant information needs to be filtered out

    Key features:
    - You can adjust total_thoughts up or down as you progress
    - You can question or revise previous thoughts
    - You can add more thoughts even after reaching what seemed like the end
    - You can express uncertainty and explore alternative approaches
    - Not every thought needs to build linearly - you can branch or backtrack
    - Generates a solution hypothesis
    - Verifies the hypothesis based on the Chain of Thought steps
    - Repeats the process until satisfied
    - Provides a correct answer

    Parameters explained:
    - user_id: id of the user to be able to identify thoughts' owner
    - thread_id: id of the conversation with the user, to stick to a given context
    - thought: Your current thinking step, which can include:
      * Regular analytical steps
      * Revisions of previous thoughts
      * Questions about previous decisions
      * Realizations about needing more analysis
      * Changes in approach
      * Hypothesis generation
      * Hypothesis verification
    - next_thought_needed: True if you need more thinking, even if at what seemed like the end
    - thought_number: Current number in sequence (can go beyond initial total if needed)
    - total_thoughts: Current estimate of thoughts needed (can be adjusted up/down)
    - is_revision: A boolean indicating if this thought revises previous thinking
    - revises_thought: If is_revision is true, which thought number is being reconsidered
    - branch_from_thought: If branching, which thought number is the branching point
    - branch_id: Identifier for the current branch (if any)
    - needs_more_thoughts: If reaching end but realizing more thoughts needed

    You should:
    1. Start with an initial estimate of needed thoughts, but be ready to adjust
    2. Feel free to question or revise previous thoughts
    3. Don't hesitate to add more thoughts if needed, even at the 'end'
    4. Express uncertainty when present
    5. Mark thoughts that revise previous thinking or branch into new paths
    6. Ignore information that is irrelevant to the current step
    7. Generate a solution hypothesis when appropriate
    8. Verify the hypothesis based on the Chain of Thought steps
    9. Repeat the process until satisfied with the solution
    10. Provide a single, ideally correct answer as the final output
    11. Only set next_thought_needed to false when truly done and a satisfactory answer is reached
    """

    result = sequential_thinking_server.process_thought(
        user_id=user_id,
        thread_id=thread_id,
        thought=thought,
        thought_number=thought_number,
        total_thoughts=total_thoughts,
        is_revision=is_revision,
        revises_thought=revises_thought,
        branch_from_thought=branch_from_thought,
        branch_id=branch_id,
        needs_more_thoughts=needs_more_thoughts,
        next_thought_needed=next_thought_needed
    )

    return result

# Rewrite generate_summary to generate an LLM summary like: concat thought number. thought + \r\n
@tool
async def generate_summary(user_id: str, thread_id: str) -> dict:
    """
    Generate a summary of the entire thinking process
    - user_id: id of the user
    - thread_id: thread_id of the conversation

    return a formatted summary of the thoughts
    """
    user_history = sequential_thinking_server.thought_history.get(user_id)
    if user_history is None:
        return {"summary": "No thoughts recorded yet"}

    thought_history = user_history.get(thread_id)
    if thought_history is None:
        return {"summary": "No thoughts recorded yet"}

     # Create summary
    summary = {
        "totalThoughts": len(thought_history),
        "timeline": [
            {
                "number": t.thought_number,
                "thought": t.thought
            } for t in sorted(thought_history, key=lambda x: x.thought_number)
        ]
    }

    return {"summary": summary}


@tool
async def clear_history(user_id: str, thread_id: str) -> dict:
    """
    Clear the thought history
    - user_id: user id to clear the thoughts history for
    - thread_id: thread_id of the conversation to clear the thoughts history
    """

    user_history = sequential_thinking_server.thought_history.get(user_id)
    if user_history is None:
        return {"status": "success", "message": "Nothing to clear"}

    thought_history = user_history.get(thread_id)
    if thought_history is None:
        return {"status": "success", "message": "Nothing to clear"}

    thought_history.clear()
    return {"status": "success", "message": "Thought history cleared"}

