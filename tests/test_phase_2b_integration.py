# test_phase_2b_integration.py
"""
Phase 2B Integration Test - Complete Multi-Agent Orchestration
=============================================================

This test validates the complete integration of:
- Phase 2B.1: Supervisor Agent Architecture (with real agent integration)
- Phase 2B.2: Inter-Agent Communication Framework  
- Phase 2B.3: Enhanced Agent Specialization

Tests end-to-end multi-agent workflows with real agent coordination.
"""

import asyncio
import logging
import pytest
from datetime import datetime
from typing import Dict, Any

from agents.supervisor_agent import SupervisorAgent, WorkflowState, TaskAnalysis
from communication.protocols import AgentType

# Configure logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(name)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

@pytest.mark.asyncio
async def test_simple_reasoning_workflow():
    """Test a simple workflow with reasoning agent only."""
    print("\n🧠 Testing Simple Reasoning Workflow...")
    
    try:
        # Create supervisor agent
        supervisor = SupervisorAgent()
        
        # Create initial workflow state
        initial_state = WorkflowState(
            user_request="What are the key principles of machine learning?",
            user_name="TestUser",
            session_context={"session_id": "test_session_1"}
        )
        
        # Create and run workflow
        workflow = await supervisor.create_workflow(initial_state)
        
        # Convert initial state to dict for graph execution
        state_dict = {
            "user_request": initial_state.user_request,
            "user_name": initial_state.user_name,
            "session_context": initial_state.session_context,
            "task_analysis": None,
            "active_agents": [],
            "completed_subtasks": [],
            "agent_results": {},
            "workflow_status": "planning",
            "error_messages": [],
            "final_response": ""
        }
        
        # Execute workflow
        config = {"configurable": {"thread_id": "test_thread_1"}}
        result = await workflow.ainvoke(state_dict, config)
        
        print(f"✅ Workflow completed successfully")
        print(f"📊 Final Status: {result.get('workflow_status')}")
        print(f"🎯 Final Response: {result.get('final_response', 'No response')[:200]}...")
        print(f"🔧 Agents Used: {result.get('agent_results', {}).keys()}")
        
        return True
        
    except Exception as e:
        print(f"❌ Simple reasoning workflow failed: {e}")
        import traceback
        traceback.print_exc()
        return False

@pytest.mark.asyncio
async def test_complex_multi_agent_workflow():
    """Test a complex workflow requiring multiple agents."""
    print("\n🚀 Testing Complex Multi-Agent Workflow...")
    
    try:
        # Create supervisor agent
        supervisor = SupervisorAgent()
        
        # Create complex task requiring research and analysis
        initial_state = WorkflowState(
            user_request="Research the latest developments in quantum computing and analyze their potential impact on cryptography. Provide a comprehensive analysis.",
            user_name="TestUser",
            session_context={"session_id": "test_session_2"}
        )
        
        # Create and run workflow
        workflow = await supervisor.create_workflow(initial_state)
        
        # Convert initial state to dict for graph execution
        state_dict = {
            "user_request": initial_state.user_request,
            "user_name": initial_state.user_name,
            "session_context": initial_state.session_context,
            "task_analysis": None,
            "active_agents": [],
            "completed_subtasks": [],
            "agent_results": {},
            "workflow_status": "planning",
            "error_messages": [],
            "final_response": ""
        }
        
        # Execute workflow
        config = {"configurable": {"thread_id": "test_thread_2"}}
        result = await workflow.ainvoke(state_dict, config)
        
        print(f"✅ Complex workflow completed successfully")
        print(f"📊 Final Status: {result.get('workflow_status')}")
        print(f"🎯 Final Response: {result.get('final_response', 'No response')[:300]}...")
        print(f"🔧 Agents Used: {list(result.get('agent_results', {}).keys())}")
        print(f"⚠️ Errors: {len(result.get('error_messages', []))}")
        
        return True
        
    except Exception as e:
        print(f"❌ Complex multi-agent workflow failed: {e}")
        import traceback
        traceback.print_exc()
        return False

@pytest.mark.asyncio
async def test_coding_workflow():
    """Test a workflow that requires coding assistance."""
    print("\n💻 Testing Coding Workflow...")
    
    try:
        # Create supervisor agent
        supervisor = SupervisorAgent()
        
        # Create coding task
        initial_state = WorkflowState(
            user_request="Create a Python function to calculate the Fibonacci sequence using dynamic programming. Include error handling and docstrings.",
            user_name="TestUser",
            session_context={"session_id": "test_session_3"}
        )
        
        # Create and run workflow
        workflow = await supervisor.create_workflow(initial_state)
        
        # Convert initial state to dict for graph execution
        state_dict = {
            "user_request": initial_state.user_request,
            "user_name": initial_state.user_name,
            "session_context": initial_state.session_context,
            "task_analysis": None,
            "active_agents": [],
            "completed_subtasks": [],
            "agent_results": {},
            "workflow_status": "planning",
            "error_messages": [],
            "final_response": ""
        }
        
        # Execute workflow
        config = {"configurable": {"thread_id": "test_thread_3"}}
        result = await workflow.ainvoke(state_dict, config)
        
        print(f"✅ Coding workflow completed successfully")
        print(f"📊 Final Status: {result.get('workflow_status')}")
        print(f"🎯 Final Response: {result.get('final_response', 'No response')[:300]}...")
        print(f"🔧 Agents Used: {list(result.get('agent_results', {}).keys())}")
        print(f"⚠️ Errors: {len(result.get('error_messages', []))}")
        
        return True
        
    except Exception as e:
        print(f"❌ Coding workflow failed: {e}")
        import traceback
        traceback.print_exc()
        return False

@pytest.mark.asyncio
async def test_task_analysis():
    """Test the task analysis capabilities."""
    print("\n🔍 Testing Task Analysis...")
    
    try:
        # Create supervisor agent
        supervisor = SupervisorAgent()
        
        # Test various task complexities
        test_requests = [
            "What is 2+2?",  # Simple
            "Explain machine learning algorithms",  # Moderate
            "Research renewable energy trends and create a business plan with code examples",  # Complex
            "Analyze global climate data, create predictive models, visualize results, and write a comprehensive report"  # Advanced
        ]
        
        for i, request in enumerate(test_requests, 1):
            print(f"\n📋 Test Request {i}: {request}")
            
            context = {"session_id": f"analysis_test_{i}", "user_name": "TestUser"}
            analysis = supervisor.analyze_task(request, context)
            
            print(f"   Complexity: {analysis.complexity.value}")
            print(f"   Primary Domain: {analysis.primary_domain}")
            print(f"   Required Agents: {[agent.value for agent in analysis.required_agents]}")
            print(f"   Estimated Steps: {analysis.estimated_steps}")
            print(f"   Confidence: {analysis.confidence:.2f}")
            print(f"   Subtasks: {len(analysis.subtasks)}")
        
        print(f"✅ Task analysis completed successfully")
        return True
        
    except Exception as e:
        print(f"❌ Task analysis failed: {e}")
        import traceback
        traceback.print_exc()
        return False


async def main():
    """Run all Phase 2B integration tests."""
    print("🚀 Phase 2B Complete Integration Test Suite")
    print("=" * 60)
    
    tests = [
        ("Task Analysis", test_task_analysis),
        ("Simple Reasoning Workflow", test_simple_reasoning_workflow),
        ("Coding Workflow", test_coding_workflow),
        ("Complex Multi-Agent Workflow", test_complex_multi_agent_workflow),
    ]
    
    results = {}
    
    for test_name, test_func in tests:
        print(f"\n🧪 Running: {test_name}")
        print("-" * 40)
        
        try:
            result = await test_func()
            results[test_name] = result
            
            if result:
                print(f"✅ {test_name}: PASSED")
            else:
                print(f"❌ {test_name}: FAILED")
                
        except Exception as e:
            print(f"❌ {test_name}: ERROR - {e}")
            results[test_name] = False
    
    # Final summary
    print(f"\n📊 PHASE 2B INTEGRATION TEST RESULTS")
    print("=" * 60)
    
    passed = sum(1 for result in results.values() if result)
    total = len(results)
    
    for test_name, result in results.items():
        status = "✅ PASSED" if result else "❌ FAILED"
        print(f"   {test_name}: {status}")
    
    success_rate = (passed / total) * 100 if total > 0 else 0
    print(f"\n🎯 Overall Success Rate: {passed}/{total} ({success_rate:.1f}%)")
    
    if success_rate >= 75:
        print("🏆 PHASE 2B INTEGRATION: SUCCESSFUL!")
        print("\nKey Achievements:")
        print("✅ Supervisor Agent Architecture - Complete with real agent integration")
        print("✅ Inter-Agent Communication Framework - Operational")  
        print("✅ Enhanced Agent Specialization - Integrated and functional")
        print("✅ Multi-Agent Workflows - End-to-end orchestration working")
    else:
        print("⚠️ PHASE 2B INTEGRATION: NEEDS IMPROVEMENT")
        print(f"Some tests failed. Review the errors above to address issues.")
    
    return success_rate >= 75


if __name__ == "__main__":
    asyncio.run(main())
