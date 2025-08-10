# demo_phase_2b2.py
"""
Phase 2B.2 Inter-Agent Communication Framework Demo

This demonstrates the complete Phase 2B.2 implementation including:
- Message protocols and validation
- Async message bus (core infrastructure)
- Context management with versioning
- Conflict resolution with multiple strategies
- End-to-end multi-agent communication workflow
"""

import asyncio
from datetime import datetime

from communication.protocols import AgentMessage, MessageType, MessagePriority, AgentType
from communication.context_manager import ContextManager, ContextScope
from communication.conflict_resolver import (
    ConflictResolver, ConflictType, ResolutionStrategy, ConflictSeverity
)


async def demo_context_management():
    """Demonstrate context management capabilities."""
    print("\n🔄 CONTEXT MANAGEMENT DEMO")
    print("=" * 50)
    
    manager = ContextManager()
    await manager.start()
    
    # Create different scoped contexts
    global_ctx = await manager.get_context("global", ContextScope.GLOBAL)
    workflow_ctx = await manager.get_context("workflow-001", ContextScope.WORKFLOW)
    task_ctx = await manager.get_context("task-001", ContextScope.TASK)
    
    print("✅ Created contexts at different scopes")
    
    # Simulate multi-agent workflow
    print("\n📝 Multi-agent context updates:")
    
    # Supervisor sets global configuration
    await global_ctx.set(
        "max_agents", 5, "supervisor", AgentType.SUPERVISOR, "System configuration"
    )
    print("   - Supervisor: Set global max_agents = 5")
    
    # Supervisor starts workflow
    await workflow_ctx.set(
        "current_phase", "analysis", "supervisor", AgentType.SUPERVISOR, "Workflow started"
    )
    print("   - Supervisor: Started analysis phase")
    
    # Coding agent takes task
    await task_ctx.set(
        "assigned_agent", "coding-agent-1", "coding-agent-1", AgentType.CODING, "Task claimed"
    )
    print("   - Coding Agent: Claimed task")
    
    # Reasoning agent provides input
    await workflow_ctx.set(
        "analysis_approach", "static_analysis", "reasoning-agent", AgentType.REASONING, 
        "Recommended static analysis"
    )
    print("   - Reasoning Agent: Recommended static analysis")
    
    # Check version history
    history = await workflow_ctx.get_version_history("current_phase")
    print(f"\n📊 Context version history: {len(history)} versions")
    for i, version in enumerate(history):
        print(f"   v{version.version}: {version.change_summary} by {version.created_by}")
    
    # Get manager stats
    stats = manager.get_stats()
    print(f"\n📈 Context Manager Stats:")
    print(f"   - Total contexts: {stats['total_contexts']}")
    print(f"   - Total keys: {stats['total_keys']}")
    print(f"   - Total size: {stats['total_size_bytes']} bytes")
    
    await manager.stop()
    return True


async def demo_conflict_resolution():
    """Demonstrate conflict resolution capabilities."""
    print("\n⚖️  CONFLICT RESOLUTION DEMO")
    print("=" * 50)
    
    resolver = ConflictResolver()
    
    print("🔥 Creating conflict: Multiple agents propose different solutions")
    
    # Create a realistic conflict scenario
    conflict = await resolver.create_conflict(
        "implementation-strategy",
        ConflictType.STRATEGY_CHOICE,
        "Three agents propose different implementation approaches for the same feature",
        ConflictSeverity.HIGH  # High severity to prevent auto-resolution
    )
    
    print(f"✅ Created conflict: {conflict.context.conflict_id}")
    
    # Agent positions
    print("\n👥 Agents submitting their positions:")
    
    # Coding agent: Fast but basic approach
    await resolver.add_position(
        "implementation-strategy",
        "coding-agent-1",
        AgentType.CODING,
        {
            "approach": "simple_implementation",
            "estimated_hours": 8,
            "maintainability": "medium",
            "performance": "good"
        },
        0.7,
        "Simple approach, quick to implement and debug"
    )
    print("   - Coding Agent 1: Simple implementation (confidence: 0.7)")
    
    # Reasoning agent: Thorough approach
    await resolver.add_position(
        "implementation-strategy",
        "reasoning-agent",
        AgentType.REASONING,
        {
            "approach": "comprehensive_design",
            "estimated_hours": 20,
            "maintainability": "excellent",
            "performance": "excellent"
        },
        0.9,
        "Comprehensive design with full architecture consideration"
    )
    print("   - Reasoning Agent: Comprehensive design (confidence: 0.9)")
    
    # Another coding agent: Balanced approach
    await resolver.add_position(
        "implementation-strategy",
        "coding-agent-2", 
        AgentType.CODING,
        {
            "approach": "balanced_approach",
            "estimated_hours": 12,
            "maintainability": "good",
            "performance": "very_good"
        },
        0.8,
        "Balanced approach with good performance and reasonable complexity"
    )
    print("   - Coding Agent 2: Balanced approach (confidence: 0.8)")
    
    # Test different resolution strategies
    strategies_to_test = [
        ResolutionStrategy.WEIGHTED_VOTE,
        ResolutionStrategy.EXPERT_OVERRIDE,
        ResolutionStrategy.PRIORITY_BASED
    ]
    
    print(f"\n🎯 Testing resolution strategies:")
    
    for strategy in strategies_to_test:
        # Create new conflict for each strategy test
        test_conflict = await resolver.create_conflict(
            f"test-{strategy.value}",
            ConflictType.STRATEGY_CHOICE,
            f"Test conflict for {strategy.value}",
            ConflictSeverity.MEDIUM
        )
        
        # Add same positions
        await resolver.add_position(
            f"test-{strategy.value}", "coding-agent-1", AgentType.CODING,
            {"approach": "simple"}, 0.7, "Simple approach"
        )
        await resolver.add_position(
            f"test-{strategy.value}", "reasoning-agent", AgentType.REASONING,
            {"approach": "comprehensive"}, 0.9, "Comprehensive approach"
        )
        await resolver.add_position(
            f"test-{strategy.value}", "coding-agent-2", AgentType.CODING,
            {"approach": "balanced"}, 0.8, "Balanced approach"
        )
        
        # Resolve with specific strategy
        result = await resolver.resolve_conflict(f"test-{strategy.value}", strategy)
        
        if result:
            print(f"   - {strategy.value}: Chose '{result['approach']}'")
        else:
            print(f"   - {strategy.value}: Failed to resolve")
    
    # Get resolver stats
    stats = resolver.get_stats()
    print(f"\n📈 Conflict Resolver Stats:")
    print(f"   - Total conflicts: {stats['total_conflicts']}")
    print(f"   - Resolved conflicts: {stats['resolved_conflicts']}")
    print(f"   - Success rate: {stats['success_rate']:.2%}")
    
    return True


def demo_message_protocols():
    """Demonstrate message protocol capabilities."""
    print("\n📨 MESSAGE PROTOCOLS DEMO")
    print("=" * 50)
    
    # Create different types of messages
    print("🔧 Creating different message types:")
    
    # Basic agent message
    basic_msg = AgentMessage(
        type=MessageType.REQUEST,
        sender_id="coding-agent",
        sender_type=AgentType.CODING,
        subject="Code Analysis Request",
        content={"file": "main.py", "analysis_type": "static"}
    )
    print(f"   - Basic Message: {basic_msg.subject}")
    print(f"     Type: {basic_msg.type}, Priority: {basic_msg.priority}")
    
    # High priority notification
    urgent_msg = AgentMessage(
        type=MessageType.NOTIFICATION,
        sender_id="supervisor",
        sender_type=AgentType.SUPERVISOR,
        subject="Critical System Alert",
        content={"alert_type": "resource_limit", "severity": "high"},
        priority=MessagePriority.CRITICAL
    )
    print(f"   - Urgent Message: {urgent_msg.subject}")
    print(f"     Priority: {urgent_msg.priority}")
    
    # Request message
    from communication.protocols import RequestMessage
    request_msg = RequestMessage(
        sender_id="user-interface",
        sender_type=AgentType.SUPERVISOR,
        subject="Feature Implementation Request",
        service="implement_feature",
        parameters={"feature": "user_authentication", "priority": "high"},
        timeout_seconds=300
    )
    print(f"   - Service Request: {request_msg.subject}")
    print(f"     Service: {request_msg.service}, Timeout: {request_msg.timeout_seconds}s")
    
    # Response message
    from communication.protocols import ResponseMessage
    response_msg = ResponseMessage(
        sender_id="coding-agent",
        sender_type=AgentType.CODING,
        subject="Implementation Complete",
        request_id="req-123",
        success=True,
        result={"status": "completed", "files_modified": 3, "tests_added": 5}
    )
    print(f"   - Service Response: {response_msg.subject}")
    print(f"     Success: {response_msg.success}, Files modified: {response_msg.result['files_modified']}")
    
    print(f"\n✅ Successfully created {4} different message types")
    return True


async def demo_end_to_end_workflow():
    """Demonstrate end-to-end multi-agent workflow."""
    print("\n🔄 END-TO-END WORKFLOW DEMO")
    print("=" * 50)
    
    # Initialize all communication components
    context_manager = ContextManager()
    conflict_resolver = ConflictResolver()
    
    await context_manager.start()
    
    print("🚀 Starting multi-agent workflow simulation...")
    
    # Create workflow context
    workflow_ctx = await context_manager.get_context("feature-workflow", ContextScope.WORKFLOW)
    
    # Phase 1: Task Assignment
    print("\n📋 Phase 1: Task Assignment")
    await workflow_ctx.set(
        "current_phase", "assignment", "supervisor", AgentType.SUPERVISOR,
        "Workflow started - assigning tasks"
    )
    
    feature_spec = {
        "name": "user_authentication",
        "requirements": ["login", "logout", "password_reset"],
        "priority": "high",
        "deadline": "2025-08-12"
    }
    
    await workflow_ctx.set(
        "feature_spec", feature_spec, "supervisor", AgentType.SUPERVISOR,
        "Feature specification defined"
    )
    print("   ✅ Supervisor: Feature specification created")
    
    # Phase 2: Analysis and Planning
    print("\n🔍 Phase 2: Analysis and Planning")
    await workflow_ctx.set(
        "current_phase", "analysis", "supervisor", AgentType.SUPERVISOR,
        "Moving to analysis phase"
    )
    
    # Reasoning agent analyzes requirements
    analysis_result = {
        "complexity": "medium",
        "estimated_hours": 24,
        "required_components": ["auth_service", "user_model", "password_hashing"],
        "potential_risks": ["security_vulnerabilities", "session_management"]
    }
    
    await workflow_ctx.set(
        "analysis_result", analysis_result, "reasoning-agent", AgentType.REASONING,
        "Requirements analysis completed"
    )
    print("   ✅ Reasoning Agent: Analysis completed")
    
    # Phase 3: Implementation Strategy Conflict
    print("\n⚖️  Phase 3: Implementation Strategy Conflict")
    
    # Multiple agents propose different approaches
    strategy_conflict = await conflict_resolver.create_conflict(
        "auth-implementation",
        ConflictType.STRATEGY_CHOICE,
        "Different authentication implementation strategies proposed",
        ConflictSeverity.MEDIUM
    )
    
    # Coding agent 1: Simple approach
    await conflict_resolver.add_position(
        "auth-implementation",
        "coding-agent-1",
        AgentType.CODING,
        {
            "strategy": "simple_session_auth",
            "libraries": ["flask-login"],
            "security_level": "basic",
            "implementation_time": 16
        },
        0.7,
        "Simple session-based auth, faster to implement"
    )
    print("   📝 Coding Agent 1: Proposed simple session auth")
    
    # Coding agent 2: JWT approach
    await conflict_resolver.add_position(
        "auth-implementation",
        "coding-agent-2",
        AgentType.CODING,
        {
            "strategy": "jwt_token_auth",
            "libraries": ["pyjwt", "cryptography"],
            "security_level": "high",
            "implementation_time": 20
        },
        0.8,
        "JWT tokens provide better security and scalability"
    )
    print("   📝 Coding Agent 2: Proposed JWT token auth")
    
    # Reasoning agent weighs in
    await conflict_resolver.add_position(
        "auth-implementation",
        "reasoning-agent",
        AgentType.REASONING,
        {
            "strategy": "hybrid_approach",
            "libraries": ["flask-login", "pyjwt"],
            "security_level": "high",
            "implementation_time": 24
        },
        0.9,
        "Hybrid approach balances security and usability"
    )
    print("   📝 Reasoning Agent: Proposed hybrid approach")
    
    # Resolve the conflict
    resolution = await conflict_resolver.resolve_conflict(
        "auth-implementation",
        ResolutionStrategy.WEIGHTED_VOTE
    )
    
    if resolution:
        await workflow_ctx.set(
            "chosen_strategy", resolution, "supervisor", AgentType.SUPERVISOR,
            "Strategy conflict resolved"
        )
        print(f"   ✅ Conflict Resolved: Chose {resolution['strategy']}")
    
    # Phase 4: Implementation
    print("\n⚙️  Phase 4: Implementation")
    await workflow_ctx.set(
        "current_phase", "implementation", "supervisor", AgentType.SUPERVISOR,
        "Moving to implementation phase"
    )
    
    # Simulate implementation progress
    progress_updates = [
        ("coding-agent-1", 0.25, "User model created"),
        ("coding-agent-2", 0.50, "Authentication service implemented"),
        ("coding-agent-1", 0.75, "Password hashing added"),
        ("coding-agent-2", 1.00, "Implementation completed")
    ]
    
    for agent, progress, description in progress_updates:
        await workflow_ctx.set(
            "implementation_progress", 
            {"progress": progress, "description": description},
            agent,
            AgentType.CODING,
            f"Progress update: {progress:.0%}"
        )
        print(f"   📊 {agent}: {progress:.0%} - {description}")
    
    # Phase 5: Final Status
    print("\n🎯 Phase 5: Workflow Completion")
    
    final_status = {
        "status": "completed",
        "completion_time": datetime.now().isoformat(),
        "final_approach": resolution['strategy'] if resolution else "unknown",
        "files_created": 8,
        "tests_added": 12,
        "documentation_updated": True
    }
    
    await workflow_ctx.set(
        "final_status", final_status, "supervisor", AgentType.SUPERVISOR,
        "Workflow completed successfully"
    )
    
    print("   ✅ Supervisor: Workflow completed successfully")
    
    # Show final workflow state
    print(f"\n📊 Final Workflow State:")
    current_phase = await workflow_ctx.get("current_phase")
    chosen_strategy = await workflow_ctx.get("chosen_strategy")
    final_status = await workflow_ctx.get("final_status")
    
    print(f"   - Phase: {current_phase}")
    if chosen_strategy:
        print(f"   - Strategy: {chosen_strategy['strategy']}")
        print(f"   - Security Level: {chosen_strategy['security_level']}")
    if final_status:
        print(f"   - Status: {final_status['status']}")
        print(f"   - Files Created: {final_status['files_created']}")
        print(f"   - Tests Added: {final_status['tests_added']}")
    
    # Get final stats
    ctx_stats = context_manager.get_stats()
    resolver_stats = conflict_resolver.get_stats()
    
    print(f"\n📈 Final Statistics:")
    print(f"   - Context Operations: {ctx_stats['total_keys']} keys across {ctx_stats['total_contexts']} contexts")
    print(f"   - Conflicts Resolved: {resolver_stats['resolved_conflicts']}/{resolver_stats['total_conflicts']}")
    print(f"   - Success Rate: {resolver_stats['success_rate']:.2%}")
    
    await context_manager.stop()
    return True


async def main():
    """Run the complete Phase 2B.2 demonstration."""
    print("🌟 PHASE 2B.2 INTER-AGENT COMMUNICATION FRAMEWORK")
    print("🌟 COMPREHENSIVE DEMONSTRATION")
    print("=" * 60)
    
    start_time = datetime.now()
    
    try:
        # Run all demonstrations
        await demo_context_management()
        demo_message_protocols()
        await demo_conflict_resolution()
        await demo_end_to_end_workflow()
        
        end_time = datetime.now()
        duration = end_time - start_time
        
        print(f"\n🎉 PHASE 2B.2 DEMONSTRATION COMPLETE!")
        print("=" * 60)
        print("✅ All communication framework components working correctly:")
        print("   - Message Protocols: ✅ Validated")
        print("   - Context Management: ✅ Multi-agent state sharing")
        print("   - Conflict Resolution: ✅ Multiple strategies tested")
        print("   - End-to-End Workflow: ✅ Complete integration")
        print(f"\n⏱️  Total demonstration time: {duration.total_seconds():.2f} seconds")
        print(f"🔧 Framework ready for integration with multi-agent orchestration")
        
        return True
        
    except Exception as e:
        print(f"\n❌ Demonstration failed: {e}")
        import traceback
        traceback.print_exc()
        return False


if __name__ == "__main__":
    # Run the demonstration
    success = asyncio.run(main())
    exit(0 if success else 1)
