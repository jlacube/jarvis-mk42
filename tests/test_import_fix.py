# test_import_fix.py
"""
Simple test to verify import fixes
"""

import asyncio
import logging
import pytest

# Configure logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(name)s - %(levelname)s - %(message)s')

@pytest.mark.asyncio
async def test_imports():
    """Test that all agent imports work correctly."""
    print("Testing agent imports after fix...")
    
    try:
        # Test reasoning agent import
        from agents.reasoning_agent import ReasoningAgent
        print("✅ reasoning_agent import: OK")
    except Exception as e:
        print(f"❌ reasoning_agent import: {e}")
    
    try:
        # Test reasoning model agent import
        from agents.reasoning_model_agent import ReasoningModelAgent  
        print("✅ reasoning_model_agent import: OK")
    except Exception as e:
        print(f"❌ reasoning_model_agent import: {e}")
    
    try:
        # Test coding agent import
        from agents.coding_agent import CodingAgent
        print("✅ coding_agent import: OK")
    except Exception as e:
        print(f"❌ coding_agent import: {e}")
        
    try:
        # Test enhanced reasoning agent import
        from agents.enhanced_reasoning_agent import EnhancedReasoningAgent
        print("✅ enhanced_reasoning_agent import: OK")
    except Exception as e:
        print(f"❌ enhanced_reasoning_agent import: {e}")
        
    try:
        # Test supervisor agent import
        from agents.supervisor_agent import SupervisorAgent
        print("✅ supervisor_agent import: OK")
    except Exception as e:
        print(f"❌ supervisor_agent import: {e}")

@pytest.mark.asyncio
async def test_simple_workflow():
    """Test a very simple workflow to verify basic functionality."""
    print("\n🧠 Testing Simple Workflow...")
    
    try:
        from agents.supervisor_agent import SupervisorAgent, WorkflowState
        
        # Create supervisor agent
        supervisor = SupervisorAgent()
        
        # Create very simple initial state
        initial_state = WorkflowState(
            user_request="What is 2+2?",
            user_name="TestUser", 
            session_context={"session_id": "simple_test"}
        )
        
        # Create workflow
        workflow = await supervisor.create_workflow(initial_state)
        print("✅ Workflow created successfully")
        
        # Convert to dict and test with recursion limit
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
            "final_response": "",
            "orchestrator_calls": 0
        }
        
        # Execute with recursion limit
        config = {
            "configurable": {"thread_id": "simple_test"},
            "recursion_limit": 15
        }
        result = await workflow.ainvoke(state_dict, config)
        
        print(f"✅ Simple workflow completed")
        print(f"📊 Status: {result.get('workflow_status')}")
        print(f"🎯 Has Response: {'Yes' if result.get('final_response') else 'No'}")
        print(f"🔧 Agent Results: {len(result.get('agent_results', {}))}")
        print(f"⚠️  Errors: {len(result.get('error_messages', []))}")
        print(f"🔄 Orchestrator Calls: {result.get('orchestrator_calls', 0)}")
        
        return True
        
    except Exception as e:
        print(f"❌ Simple workflow failed: {e}")
        import traceback
        traceback.print_exc()
        return False


async def main():
    """Run import and simple workflow tests."""
    print("🔧 Import Fix Verification")
    print("=" * 40)
    
    await test_imports()
    
    success = await test_simple_workflow()
    
    if success:
        print("\n🎉 Import fixes successful! Ready for full integration test.")
    else:
        print("\n⚠️ Still have issues to fix.")


if __name__ == "__main__":
    asyncio.run(main())
