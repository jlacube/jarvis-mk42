# Jarvis-MK42 Tool Tests

This directory contains tests for the individual tools used by Jarvis-MK42. These tests are designed to verify that each tool works correctly in isolation, without requiring the full agent framework.

## Test Structure

The tests are organized by tool category:

- `test_file_tools.py`: Tests for file operations (listing, reading, writing)
- `test_math_tools.py`: Tests for mathematical and calculation tools
- `test_research_tools.py`: Tests for web research and information retrieval tools
- `test_reasoning_tools.py`: Tests for reasoning and thought process tools
- `test_plotting.py`: Tests for data visualization tools
- `test_agents_tools.py`: Tests for agent interaction tools
- `test_multimodal_tools.py`: Tests for multimodal (image, audio, video) tools

## Running Tests

You can run the tests using the `run_tool_tests.py` script from the root directory:

```bash
# Run all tests
python run_tool_tests.py

# Run specific test categories
python run_tool_tests.py file math

# Run a single test category
python run_tool_tests.py research
```

## Test Design Principles

1. **Isolation**: Each test focuses on a specific tool functionality, isolating it from other components.
2. **Mocking**: External dependencies (APIs, services) are mocked to ensure tests are reliable and don't require external connections.
3. **Coverage**: Tests aim to cover both normal operation and error handling paths.
4. **Environment**: Tests can be configured via environment variables (see .env file).

## Tool Invocation Pattern

Tools in Jarvis-MK42 follow the LangChain tool invocation pattern. When testing tools:

1. Use the `.ainvoke()` method instead of directly calling the function:
   ```python
   # DO NOT: result = my_tool(param1="value1", param2="value2")
   # DO: 
   result = await my_tool.ainvoke({
       "param1": "value1", 
       "param2": "value2"
   })
   ```

2. When a tool returns JSON in a response format, parse it correctly:
   ```python
   # For tools that return JSON in content format
   result = await json_returning_tool.ainvoke({"param": "value"})
   if "content" in result and isinstance(result["content"], list):
       json_content = json.loads(result["content"][0]["text"])
   ```

3. For tools requiring Chainlit context, mock the necessary components:
   ```python
   # Mock Chainlit message context
   with patch("chainlit.context.message", Mock(id="msg_123")):
       result = await my_tool.ainvoke({"param": "value"})
   ```

## Adding New Tests

When adding a new tool to Jarvis-MK42, you should also add corresponding tests:

1. Create a new test file following the naming pattern `test_*_tools.py`
2. Use pytest fixtures from `conftest.py` for shared setup
3. Include both positive and negative test cases
4. Mock external dependencies to avoid network calls
5. Update the `run_tool_tests.py` script to include your new test category

## Environment Setup

Some tests require environment variables to be set. Create a `.env` file with:

```
# API Keys for external services
SERPER_API_KEY=your_serper_api_key
PERPLEXITY_API_KEY=your_perplexity_api_key
ELEVENLABS_API_KEY=your_elevenlabs_api_key

# Test configuration
TEST_ENVIRONMENT=development
```
