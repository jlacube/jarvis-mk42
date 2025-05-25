import pytest
import re
from unittest.mock import patch, AsyncMock, MagicMock

from tools.agents_tools import research_tool, reasoning_tool, coding_tool

# Since these tools require agents that may be complex to initialize in tests,
# we'll use mocking to test the tool functions independently


@pytest.mark.asyncio
async def test_research_tool_with_mocks():
    """Test research_tool with mocked agent."""
    test_query = "What are the benefits of Python for data science?"
    expected_response = "Python is great for data science because of libraries like pandas, numpy, and scikit-learn."
    
    # Create a mock for the agent
    mock_agent = AsyncMock()
    mock_agent.ainvoke = AsyncMock(return_value={
        "messages": [
            # First message is from user, second from assistant
            MagicMock(), 
            MagicMock(content=expected_response)
        ]
    })
    
    # Patch the get_research_agent function to return our mock
    with patch('tools.agents_tools.get_research_agent', return_value=mock_agent):
        result = await research_tool.ainvoke(test_query)
        
        # Check that the result matches our expected response
        assert result == expected_response, f"Expected '{expected_response}', got '{result}'"
        
        # Check that ainvoke was called with the correct input
        calls = mock_agent.ainvoke.call_args_list
        assert len(calls) == 1, "Agent's ainvoke should be called exactly once"
        
        # Check that the query was passed correctly
        call_kwargs = calls[0].kwargs
        assert "input" in call_kwargs, "ainvoke should be called with 'input' parameter"
        assert "messages" in call_kwargs["input"], "Input should contain 'messages'"
        assert len(call_kwargs["input"]["messages"]) == 1, "Input should contain exactly one message"
        assert call_kwargs["input"]["messages"][0].content == test_query, f"Message content should be '{test_query}'"


@pytest.mark.asyncio
async def test_reasoning_tool_with_mocks():
    """Test reasoning_tool with mocked agent."""
    test_query = "How should I approach solving a complex optimization problem?"
    expected_response = "First, identify the objective function. Then determine the constraints. Finally, select an appropriate algorithm."
    
    # Create a mock for the agent
    mock_agent = AsyncMock()
    mock_agent.ainvoke = AsyncMock(return_value={
        "messages": [MagicMock(), MagicMock(content=expected_response)]
    })
    
    # Patch the get_reasoning_agent function to return our mock
    with patch('tools.agents_tools.get_reasoning_agent', return_value=mock_agent):
        result = await reasoning_tool.ainvoke(test_query)
        
        # Check that the result matches our expected response
        assert result == expected_response, f"Expected '{expected_response}', got '{result}'"
        
        # Check that ainvoke was called with the correct input
        mock_agent.ainvoke.assert_called_once()


@pytest.mark.asyncio
async def test_coding_tool_with_mocks():
    """Test coding_tool with mocked agent."""
    test_query = "Write a Python function to find prime numbers up to n"
    code_response = [
        """def sieve_of_eratosthenes(n):
    \"\"\"Find all prime numbers up to n using Sieve of Eratosthenes.\"\"\"
    primes = []
    prime = [True for i in range(n+1)]
    p = 2
    while p * p <= n:
        if prime[p]:
            for i in range(p * p, n+1, p):
                prime[i] = False
        p += 1
    for p in range(2, n+1):
        if prime[p]:
            primes.append(p)
    return primes"""
    ]
    
    # Create a mock for the agent
    mock_agent = AsyncMock()
    mock_agent.ainvoke = AsyncMock(return_value={
        "messages": [MagicMock(), MagicMock(content=code_response)]
    })
    
    # Patch the get_coding_agent function to return our mock
    with patch('tools.agents_tools.get_coding_agent', return_value=mock_agent):
        result = await coding_tool.ainvoke(test_query)
        
        # Check that the result contains expected code by checking for key elements
        assert "def sieve_of_eratosthenes" in result, "Result should contain function definition"
        assert "primes = []" in result, "Result should contain primes list initialization"
        assert "return primes" in result, "Result should return primes list"
        
        # Check that ainvoke was called with the correct input
        mock_agent.ainvoke.assert_called_once()
