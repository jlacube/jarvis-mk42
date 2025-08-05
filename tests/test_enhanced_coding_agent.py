"""
Tests for Enhanced Coding Agent

This module contains comprehensive tests for the Enhanced Coding Agent,
including tests for code analysis, code review, collaborative workflows,
and integration with the communication framework and language detection system.
"""

import pytest
import pytest_asyncio
import asyncio
from unittest.mock import Mock, patch, AsyncMock
from datetime import datetime
from typing import Dict, List, Any
import sys
import os

# Add the project root to Python path
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from agents.enhanced_coding_agent import (
    EnhancedCodingAgent, 
    create_enhanced_coding_agent,
    CodeAnalysisResult,
    DevelopmentWorkflow,
    CollaborativeSession
)

class TestEnhancedCodingAgent:
    """Test class for Enhanced Coding Agent"""
    
    @pytest_asyncio.fixture
    async def agent(self):
        """Create test agent instance"""
        agent = EnhancedCodingAgent(
            agent_id="test_coding_agent",
            model_config={"provider": "openai", "model": "gpt-4", "temperature": 0.2}
        )
        await agent.initialize()
        return agent
    
    @pytest.mark.asyncio
    async def test_agent_initialization(self):
        """Test agent initialization and basic properties"""
        agent = EnhancedCodingAgent(agent_id="test_agent")
        
        # Test basic properties
        assert agent.agent_id == "test_agent"
        assert agent.agent_name == "Enhanced Coding Agent"
        assert len(agent.supported_languages) > 0
        assert len(agent.development_workflows) > 0
        
        # Test initialization
        success = await agent.initialize()
        assert success == True
        assert len(agent.coding_tools) > 0

    @pytest.mark.asyncio
    async def test_code_analysis_python(self, agent):
        """Test Python code analysis"""
        python_code = '''
def factorial(n):
    """Calculate factorial of a number."""
    if n <= 1:
        return 1
    return n * factorial(n - 1)

class Calculator:
    """Simple calculator class."""
    
    def add(self, a, b):
        return a + b
    
    def multiply(self, a, b):
        return a * b
'''
        
        result = await agent.analyze_code(
            code=python_code,
            file_path="test.py",
            language="python"
        )
        
        assert isinstance(result, CodeAnalysisResult)
        assert result.language == "python"
        assert result.quality_score > 0
        assert result.complexity_score > 0
        assert result.metrics["lines_of_code"] > 10
        assert len(result.suggestions) > 0
        
        print(f"✓ Python analysis - Quality: {result.quality_score}, Complexity: {result.complexity_score}")

    @pytest.mark.asyncio
    async def test_code_analysis_javascript(self, agent):
        """Test JavaScript code analysis"""
        js_code = '''
const greeting = "Hello, World!";

function add(a, b) {
    return a + b;
}

const multiply = (x, y) => x * y;

class Person {
    constructor(name) {
        this.name = name;
    }
    
    greet() {
        return `Hello, ${this.name}!`;
    }
}
'''
        
        result = await agent.analyze_code(
            code=js_code,
            file_path="test.js",
            language="javascript"
        )
        
        assert isinstance(result, CodeAnalysisResult)
        assert result.language == "javascript"
        assert result.quality_score > 0
        assert result.complexity_score > 0
        
        print(f"✓ JavaScript analysis - Quality: {result.quality_score}, Complexity: {result.complexity_score}")

    @pytest.mark.asyncio
    async def test_code_analysis_syntax_error(self, agent):
        """Test code analysis with syntax errors"""
        bad_python_code = '''
def broken_function(
    print("This function has syntax error"
    return "incomplete"
'''
        
        result = await agent.analyze_code(
            code=bad_python_code,
            language="python"
        )
        
        assert isinstance(result, CodeAnalysisResult)
        assert result.quality_score == 0  # Should be 0 due to syntax error
        assert len(result.issues) > 0
        assert any(issue["type"] == "syntax" for issue in result.issues)
        
        print(f"✓ Syntax error detection working correctly")

    @pytest.mark.asyncio
    async def test_language_detection(self, agent):
        """Test automatic language detection"""
        # Test Python code
        python_code = "def hello():\n    print('Hello World')"
        result = await agent.analyze_code(python_code, language="auto")
        assert result.language == "python"
        
        # Test JavaScript code
        js_code = "function hello() {\n    console.log('Hello World');\n}"
        result = await agent.analyze_code(js_code, language="auto")
        assert result.language == "javascript"
        
        print("✓ Language detection working correctly")

    @pytest.mark.asyncio
    async def test_code_review(self, agent):
        """Test comprehensive code review functionality"""
        test_code = '''
def calculate_total(items):
    """Calculate total price of items."""
    total = 0
    for item in items:
        total += item['price'] * item['quantity']
    return total

def apply_discount(total, discount_percent):
    """Apply discount to total."""
    if discount_percent < 0 or discount_percent > 100:
        raise ValueError("Invalid discount percentage")
    return total * (1 - discount_percent / 100)
'''
        
        review_result = await agent.review_code(
            code=test_code,
            review_criteria=["functionality", "readability", "maintainability"]
        )
        
        assert "overall_score" in review_result
        assert "criteria_scores" in review_result
        assert "recommendations" in review_result
        assert "approved" in review_result
        assert isinstance(review_result["approved"], bool)
        
        # Check that all criteria were evaluated
        for criterion in ["functionality", "readability", "maintainability"]:
            assert criterion in review_result["criteria_scores"]
            assert 0 <= review_result["criteria_scores"][criterion] <= 100
        
        print(f"✓ Code review completed - Score: {review_result['overall_score']:.1f}%, Approved: {review_result['approved']}")

    @pytest.mark.asyncio
    async def test_development_workflows(self, agent):
        """Test development workflow management"""
        # Check that workflows are initialized
        assert len(agent.development_workflows) > 0
        
        # Check specific workflows
        expected_workflows = ["agile", "tdd", "code_review", "refactoring"]
        for workflow_name in expected_workflows:
            assert workflow_name in agent.development_workflows
            workflow = agent.development_workflows[workflow_name]
            assert isinstance(workflow, DevelopmentWorkflow)
            assert len(workflow.stages) > 0
            assert len(workflow.quality_gates) > 0
        
        print(f"✓ Development workflows available: {list(agent.development_workflows.keys())}")

    @pytest.mark.asyncio
    async def test_collaborative_session(self, agent):
        """Test collaborative session management"""
        # Start a collaborative session
        participants = ["agent_1", "agent_2", "agent_3"]
        focus_area = "refactoring"
        project_context = {"project": "test_project", "language": "python"}
        
        session_id = await agent.start_collaborative_session(
            participants=participants,
            focus_area=focus_area,
            project_context=project_context
        )
        
        assert session_id is not None
        assert session_id in agent.collaborative_sessions
        
        session = agent.collaborative_sessions[session_id]
        assert isinstance(session, CollaborativeSession)
        assert session.participants == participants
        assert session.focus_area == focus_area
        assert "project" in session.shared_context
        
        print(f"✓ Collaborative session created: {session_id}")

    @pytest.mark.asyncio
    async def test_agent_status(self, agent):
        """Test agent status reporting"""
        status = await agent.get_agent_status()
        
        # Check base status fields
        assert "agent_id" in status
        assert "state" in status
        assert "capabilities" in status
        
        # Check coding-specific status fields
        assert "development_workflows_available" in status
        assert "coding_tools_available" in status
        assert "supported_languages" in status
        assert "supported_languages_list" in status
        
        # Verify values
        assert status["development_workflows_available"] > 0
        assert status["coding_tools_available"] > 0
        assert status["supported_languages"] > 0
        assert len(status["supported_languages_list"]) > 0
        
        print(f"✓ Agent status: {status['supported_languages']} languages, {status['development_workflows_available']} workflows")

    @pytest.mark.asyncio
    async def test_coding_history(self, agent):
        """Test coding history tracking"""
        # Perform some analyses to build history
        test_codes = [
            ("def test1(): pass", "python"),
            ("function test2() {}", "javascript"),
            ("class Test3 {}", "java")
        ]
        
        for code, language in test_codes:
            await agent.analyze_code(code, language=language)
        
        # Get history
        history = await agent.get_coding_history(limit=5)
        
        assert len(history) >= len(test_codes)
        for entry in history:
            assert "language" in entry
            assert "quality_score" in entry
            assert "complexity_score" in entry
            assert "timestamp" in entry
        
        print(f"✓ Coding history tracked: {len(history)} analyses")

    @pytest.mark.asyncio
    async def test_collaboration_message_handling(self, agent):
        """Test handling of collaboration messages from other agents"""
        # Test code review request
        review_message = {
            "type": "code_review_request",
            "content": "Please review this code",
            "metadata": {
                "code": "def simple_function():\n    return 'hello'",
                "criteria": ["functionality", "readability"],
                "request_id": "test_123"
            }
        }
        
        response = await agent.handle_collaboration_message(review_message)
        
        assert response is not None
        assert response["message_type"] == "code_review_response"
        assert "review_result" in response["metadata"]
        assert response["metadata"]["original_request_id"] == "test_123"
        
        print("✓ Code review message handling working")
        
        # Test code analysis request
        analysis_message = {
            "type": "code_analysis_request",
            "content": "Please analyze this code",
            "metadata": {
                "code": "console.log('Hello World');",
                "language": "javascript",
                "request_id": "test_456"
            }
        }
        
        response = await agent.handle_collaboration_message(analysis_message)
        
        assert response is not None
        assert response["message_type"] == "code_analysis_response"
        assert "analysis_result" in response["metadata"]
        assert response["metadata"]["original_request_id"] == "test_456"
        
        print("✓ Code analysis message handling working")

    @pytest.mark.asyncio
    async def test_internal_request_processing(self, agent):
        """Test internal request processing"""
        # Test code analysis request
        analysis_request = "analyze this code"
        context = {
            "code": "def example():\n    return 42",
            "file_path": "example.py"
        }
        
        result = await agent._process_request_internal(
            request=analysis_request,
            context=context,
            language_context=None,
            task_id="test_task_1"
        )
        
        assert result["success"] == True
        assert result["task_id"] == "test_task_1"
        assert "result" in result
        
        print("✓ Internal analysis request processing working")
        
        # Test code review request
        review_request = "review this code"
        context = {
            "code": "function add(a, b) { return a + b; }",
            "criteria": ["functionality"]
        }
        
        result = await agent._process_request_internal(
            request=review_request,
            context=context,
            language_context=None,
            task_id="test_task_2"
        )
        
        assert result["success"] == True
        assert result["task_id"] == "test_task_2"
        assert "result" in result
        
        print("✓ Internal review request processing working")

    @pytest.mark.asyncio
    async def test_language_extension_detection(self, agent):
        """Test language detection from file extensions"""
        test_files = [
            ("test.py", "python"),
            ("test.js", "javascript"),
            ("test.ts", "typescript"),
            ("test.java", "java"),
            ("test.go", "go"),
            ("test.rs", "rust")
        ]
        
        for file_path, expected_lang in test_files:
            detected_lang = agent._detect_language_from_extension(file_path)
            assert detected_lang == expected_lang
        
        print("✓ File extension language detection working")

# Integration tests
class TestEnhancedCodingAgentIntegration:
    """Integration tests for Enhanced Coding Agent"""
    
    @pytest.mark.asyncio
    async def test_factory_function(self):
        """Test agent creation via factory function"""
        agent = await create_enhanced_coding_agent(
            agent_id="factory_test_agent",
            model_config={"provider": "openai", "model": "gpt-4", "temperature": 0.2}
        )
        
        assert agent.agent_id == "factory_test_agent"
        assert agent.model_config["provider"] == "openai"
        assert len(agent.coding_tools) > 0
        
        print("✓ Factory function working correctly")

    @pytest.mark.asyncio
    async def test_end_to_end_workflow(self):
        """Test complete workflow from analysis to review"""
        agent = await create_enhanced_coding_agent(agent_id="workflow_test_agent")
        
        # Sample code for testing
        test_code = '''
def fibonacci(n):
    """Generate fibonacci sequence up to n terms."""
    if n <= 0:
        return []
    elif n == 1:
        return [0]
    elif n == 2:
        return [0, 1]
    
    sequence = [0, 1]
    for i in range(2, n):
        next_value = sequence[i-1] + sequence[i-2]
        sequence.append(next_value)
    
    return sequence

# Test the function
if __name__ == "__main__":
    result = fibonacci(10)
    print(f"Fibonacci sequence: {result}")
'''
        
        # Step 1: Analyze code
        analysis = await agent.analyze_code(test_code, "fibonacci.py", "python")
        assert analysis.language == "python"
        assert analysis.quality_score > 0
        
        # Step 2: Review code
        review = await agent.review_code(
            test_code,
            ["functionality", "readability", "maintainability", "performance"]
        )
        assert "overall_score" in review
        assert review["overall_score"] > 0
        
        # Step 3: Check history
        history = await agent.get_coding_history()
        assert len(history) > 0
        
        # Step 4: Get status
        status = await agent.get_agent_status()
        assert status["total_analysis_performed"] > 0
        
        print(f"✓ End-to-end workflow completed successfully")
        print(f"  Analysis Quality: {analysis.quality_score:.1f}")
        print(f"  Review Score: {review['overall_score']:.1f}%")
        print(f"  Review Approved: {review['approved']}")

# Run the tests
async def run_enhanced_coding_agent_tests():
    """Run all Enhanced Coding Agent tests"""
    print("Running Enhanced Coding Agent Tests...")
    
    try:
        # Basic tests
        test_instance = TestEnhancedCodingAgent()
        
        # Test initialization
        await test_instance.test_agent_initialization()
        
        # Create agent for other tests
        agent = EnhancedCodingAgent(agent_id="test_agent")
        await agent.initialize()
        
        # Run all tests
        await test_instance.test_code_analysis_python(agent)
        await test_instance.test_code_analysis_javascript(agent)
        await test_instance.test_code_analysis_syntax_error(agent)
        await test_instance.test_language_detection(agent)
        await test_instance.test_code_review(agent)
        await test_instance.test_development_workflows(agent)
        await test_instance.test_collaborative_session(agent)
        await test_instance.test_agent_status(agent)
        await test_instance.test_coding_history(agent)
        await test_instance.test_collaboration_message_handling(agent)
        await test_instance.test_internal_request_processing(agent)
        await test_instance.test_language_extension_detection(agent)
        
        # Integration tests
        integration_test = TestEnhancedCodingAgentIntegration()
        await integration_test.test_factory_function()
        await integration_test.test_end_to_end_workflow()
        
        print("✅ All basic tests passed!")
        
        # Summary
        print("\n📊 Enhanced Coding Agent Test Summary:")
        print(f"✓ Agent initialized successfully")
        print(f"✓ Code analysis working for multiple languages")
        print(f"✓ Code review functionality operational")
        print(f"✓ Development workflows available")
        print(f"✓ Collaborative sessions supported")
        print(f"✓ Language detection working")
        print(f"✓ Message handling functional")
        print(f"✓ History tracking operational")
        print(f"✓ Integration tests passed")
        
        return True
        
    except Exception as e:
        print(f"❌ Test execution failed: {e}")
        import traceback
        traceback.print_exc()
        return False

if __name__ == "__main__":
    # Run the tests
    result = asyncio.run(run_enhanced_coding_agent_tests())
    if result:
        print("\n🎉 All Enhanced Coding Agent tests completed successfully!")
    else:
        print("\n❌ Some tests failed. Please check the output above.")
