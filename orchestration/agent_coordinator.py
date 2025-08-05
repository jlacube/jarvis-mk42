# orchestration/agent_coordinator.py
"""
Agent Coordinator for Multi-Agent Orchestration
===============================================

This module provides coordination and communication services between
specialized agents in the Jarvis-MK42 multi-agent system. It manages:

- Agent registration and capability discovery
- Inter-agent communication and message routing
- Load balancing and resource allocation
- Agent health monitoring and failover
- Shared context and memory management
"""

import logging
import asyncio
from datetime import datetime, timedelta
from typing import Dict, List, Optional, Any, Callable, Union
from dataclasses import dataclass, field
from enum import Enum
from concurrent.futures import ThreadPoolExecutor, Future

from pydantic import BaseModel, Field
from langchain_core.messages import BaseMessage, HumanMessage, AIMessage

from agents.supervisor_agent import AgentType
from utils.logging_config import get_logger
from utils.exceptions import CoordinationError, AgentError

logger = get_logger(__name__)


class AgentStatus(Enum):
    """Status of individual agents."""
    UNKNOWN = "unknown"
    INITIALIZING = "initializing"
    READY = "ready"
    BUSY = "busy"
    ERROR = "error"
    OFFLINE = "offline"


class MessageType(Enum):
    """Types of inter-agent messages."""
    TASK_REQUEST = "task_request"
    TASK_RESPONSE = "task_response"
    CONTEXT_SHARE = "context_share"
    STATUS_UPDATE = "status_update"
    ERROR_REPORT = "error_report"
    COORDINATION = "coordination"


@dataclass
class AgentInfo:
    """Information about a registered agent."""
    agent_type: AgentType
    name: str
    description: str
    capabilities: List[str]
    status: AgentStatus = AgentStatus.UNKNOWN
    last_seen: datetime = field(default_factory=datetime.now)
    current_load: int = 0
    max_concurrent_tasks: int = 3
    average_response_time: float = 0.0
    success_rate: float = 1.0
    total_tasks_completed: int = 0
    metadata: Dict[str, Any] = field(default_factory=dict)


@dataclass
class AgentMessage:
    """Inter-agent communication message."""
    id: str
    message_type: MessageType
    from_agent: str
    to_agent: str
    content: Dict[str, Any]
    timestamp: datetime = field(default_factory=datetime.now)
    correlation_id: Optional[str] = None
    priority: int = 1  # 1=low, 2=medium, 3=high, 4=critical
    ttl: Optional[datetime] = None  # Time to live


class SharedContext(BaseModel):
    """Shared context and memory between agents."""
    session_id: str = Field(description="Session identifier")
    user_id: str = Field(description="User identifier")
    conversation_history: List[Dict[str, Any]] = Field(default_factory=list)
    shared_variables: Dict[str, Any] = Field(default_factory=dict)
    task_context: Dict[str, Any] = Field(default_factory=dict)
    agent_results: Dict[str, Any] = Field(default_factory=dict)
    created_at: datetime = Field(default_factory=datetime.now)
    updated_at: datetime = Field(default_factory=datetime.now)


class AgentRegistry:
    """Registry for managing agent information and capabilities."""
    
    def __init__(self):
        """Initialize the agent registry."""
        self.agents: Dict[str, AgentInfo] = {}
        self.agent_instances: Dict[str, Any] = {}
        self.capability_index: Dict[str, List[str]] = {}
        
        logger.info("Agent registry initialized")
    
    def register_agent(
        self,
        agent_id: str,
        agent_info: AgentInfo,
        agent_instance: Optional[Any] = None
    ) -> bool:
        """
        Register an agent with the registry.
        
        Args:
            agent_id: Unique identifier for the agent
            agent_info: Agent information and capabilities
            agent_instance: Optional agent instance for direct invocation
            
        Returns:
            True if registered successfully, False otherwise
        """
        try:
            self.agents[agent_id] = agent_info
            
            if agent_instance:
                self.agent_instances[agent_id] = agent_instance
            
            # Update capability index
            for capability in agent_info.capabilities:
                if capability not in self.capability_index:
                    self.capability_index[capability] = []
                self.capability_index[capability].append(agent_id)
            
            logger.info("Registered agent: %s (%s)", agent_id, agent_info.agent_type.value)
            return True
            
        except Exception as e:
            logger.error("Error registering agent %s: %s", agent_id, str(e))
            return False
    
    def unregister_agent(self, agent_id: str) -> bool:
        """
        Unregister an agent from the registry.
        
        Args:
            agent_id: Identifier of the agent to unregister
            
        Returns:
            True if unregistered successfully, False otherwise
        """
        try:
            if agent_id not in self.agents:
                return False
            
            agent_info = self.agents[agent_id]
            
            # Remove from capability index
            for capability in agent_info.capabilities:
                if capability in self.capability_index:
                    self.capability_index[capability] = [
                        aid for aid in self.capability_index[capability] 
                        if aid != agent_id
                    ]
                    if not self.capability_index[capability]:
                        del self.capability_index[capability]
            
            # Remove from registries
            del self.agents[agent_id]
            if agent_id in self.agent_instances:
                del self.agent_instances[agent_id]
            
            logger.info("Unregistered agent: %s", agent_id)
            return True
            
        except Exception as e:
            logger.error("Error unregistering agent %s: %s", agent_id, str(e))
            return False
    
    def get_agents_by_capability(self, capability: str) -> List[str]:
        """Get list of agent IDs that have a specific capability."""
        return self.capability_index.get(capability, [])
    
    def get_agents_by_type(self, agent_type: AgentType) -> List[str]:
        """Get list of agent IDs of a specific type."""
        return [
            agent_id for agent_id, info in self.agents.items()
            if info.agent_type == agent_type
        ]
    
    def get_available_agents(self, agent_type: Optional[AgentType] = None) -> List[str]:
        """Get list of available (ready and not overloaded) agents."""
        available = []
        
        for agent_id, info in self.agents.items():
            if agent_type and info.agent_type != agent_type:
                continue
            
            if (info.status == AgentStatus.READY and 
                info.current_load < info.max_concurrent_tasks):
                available.append(agent_id)
        
        return available
    
    def update_agent_status(self, agent_id: str, status: AgentStatus) -> bool:
        """Update an agent's status."""
        try:
            if agent_id not in self.agents:
                return False
            
            self.agents[agent_id].status = status
            self.agents[agent_id].last_seen = datetime.now()
            
            logger.debug("Updated agent %s status to %s", agent_id, status.value)
            return True
            
        except Exception as e:
            logger.error("Error updating agent status: %s", str(e))
            return False
    
    def update_agent_metrics(
        self,
        agent_id: str,
        response_time: Optional[float] = None,
        success: Optional[bool] = None
    ) -> bool:
        """Update agent performance metrics."""
        try:
            if agent_id not in self.agents:
                return False
            
            agent = self.agents[agent_id]
            
            if response_time is not None:
                # Update average response time
                total_time = agent.average_response_time * agent.total_tasks_completed
                agent.total_tasks_completed += 1
                agent.average_response_time = (total_time + response_time) / agent.total_tasks_completed
            
            if success is not None:
                # Update success rate
                if agent.total_tasks_completed > 0:
                    current_successes = agent.success_rate * (agent.total_tasks_completed - 1)
                    if success:
                        current_successes += 1
                    agent.success_rate = current_successes / agent.total_tasks_completed
            
            return True
            
        except Exception as e:
            logger.error("Error updating agent metrics: %s", str(e))
            return False


class AgentCoordinator:
    """
    Central coordinator for multi-agent communication and collaboration.
    
    This class manages the coordination between specialized agents, providing:
    - Agent registration and discovery
    - Inter-agent communication and message routing  
    - Load balancing and resource allocation
    - Shared context and memory management
    - Health monitoring and failover
    """
    
    def __init__(self, max_workers: int = 10):
        """
        Initialize the agent coordinator.
        
        Args:
            max_workers: Maximum number of worker threads for async operations
        """
        self.registry = AgentRegistry()
        self.message_queue: List[AgentMessage] = []
        self.shared_contexts: Dict[str, SharedContext] = {}
        self.message_handlers: Dict[MessageType, List[Callable]] = {}
        self.executor = ThreadPoolExecutor(max_workers=max_workers)
        
        # Message correlation tracking
        self.pending_requests: Dict[str, Future] = {}
        
        # Health monitoring
        self.health_check_interval = 60  # seconds
        self.last_health_check = datetime.now()
        
        logger.info("Agent coordinator initialized")
    
    def register_agent(
        self,
        agent_id: str,
        agent_type: AgentType,
        capabilities: List[str],
        agent_instance: Optional[Any] = None
    ) -> bool:
        """
        Register an agent with the coordinator.
        
        Args:
            agent_id: Unique identifier for the agent
            agent_type: Type of the agent
            capabilities: List of agent capabilities
            agent_instance: Optional agent instance
            
        Returns:
            True if registered successfully, False otherwise
        """
        try:
            agent_info = AgentInfo(
                agent_type=agent_type,
                name=agent_id,
                description=f"{agent_type.value} agent",
                capabilities=capabilities,
                status=AgentStatus.READY
            )
            
            return self.registry.register_agent(agent_id, agent_info, agent_instance)
            
        except Exception as e:
            logger.error("Error registering agent %s: %s", agent_id, str(e))
            return False
    
    async def send_message(
        self,
        from_agent: str,
        to_agent: str,
        message_type: MessageType,
        content: Dict[str, Any],
        priority: int = 1,
        timeout: Optional[float] = None
    ) -> Optional[Dict[str, Any]]:
        """
        Send a message between agents.
        
        Args:
            from_agent: Source agent ID
            to_agent: Target agent ID
            message_type: Type of message
            content: Message content
            priority: Message priority (1-4)
            timeout: Response timeout in seconds
            
        Returns:
            Response content if expecting a response, None otherwise
        """
        try:
            message = AgentMessage(
                id=f"msg_{datetime.now().strftime('%Y%m%d_%H%M%S_%f')}",
                message_type=message_type,
                from_agent=from_agent,
                to_agent=to_agent,
                content=content,
                priority=priority,
                ttl=datetime.now() + timedelta(minutes=5) if timeout else None
            )
            
            # Add to message queue
            self.message_queue.append(message)
            self.message_queue.sort(key=lambda m: (-m.priority, m.timestamp))
            
            logger.debug(
                "Sent message %s: %s -> %s (%s)",
                message.id, from_agent, to_agent, message_type.value
            )
            
            # If expecting a response, wait for it
            if message_type == MessageType.TASK_REQUEST:
                return await self._wait_for_response(message.id, timeout or 30.0)
            
            return None
            
        except Exception as e:
            logger.error("Error sending message: %s", str(e))
            raise CoordinationError(f"Failed to send message: {str(e)}")
    
    async def _wait_for_response(self, message_id: str, timeout: float) -> Optional[Dict[str, Any]]:
        """Wait for a response to a message."""
        try:
            # Create future for response
            future = self.executor.submit(self._wait_for_response_sync, message_id, timeout)
            self.pending_requests[message_id] = future
            
            # Wait for response
            result = await asyncio.wrap_future(future)
            
            # Clean up
            if message_id in self.pending_requests:
                del self.pending_requests[message_id]
            
            return result
            
        except Exception as e:
            logger.error("Error waiting for response: %s", str(e))
            return None
    
    def _wait_for_response_sync(self, message_id: str, timeout: float) -> Optional[Dict[str, Any]]:
        """Synchronous response waiting."""
        start_time = datetime.now()
        
        while (datetime.now() - start_time).total_seconds() < timeout:
            # Check for response messages
            for i, message in enumerate(self.message_queue):
                if (message.message_type == MessageType.TASK_RESPONSE and
                    message.correlation_id == message_id):
                    
                    # Remove from queue and return content
                    response = self.message_queue.pop(i)
                    return response.content
            
            # Wait briefly before checking again
            asyncio.sleep(0.1)
        
        logger.warning("Response timeout for message %s", message_id)
        return None
    
    async def delegate_task(
        self,
        task_description: str,
        agent_type: AgentType,
        context: Dict[str, Any],
        session_id: str
    ) -> Optional[Dict[str, Any]]:
        """
        Delegate a task to an appropriate agent.
        
        Args:
            task_description: Description of the task
            agent_type: Type of agent needed
            context: Task context and parameters
            session_id: Session identifier for context sharing
            
        Returns:
            Task result or None if failed
        """
        try:
            # Find available agent
            available_agents = self.registry.get_available_agents(agent_type)
            
            if not available_agents:
                logger.warning("No available agents of type %s", agent_type.value)
                return None
            
            # Select best agent (simple load balancing)
            selected_agent = self._select_best_agent(available_agents)
            
            # Update agent load
            self.registry.agents[selected_agent].current_load += 1
            self.registry.update_agent_status(selected_agent, AgentStatus.BUSY)
            
            try:
                # Send task request
                task_content = {
                    "description": task_description,
                    "context": context,
                    "session_id": session_id
                }
                
                result = await self.send_message(
                    from_agent="coordinator",
                    to_agent=selected_agent,
                    message_type=MessageType.TASK_REQUEST,
                    content=task_content,
                    priority=2,
                    timeout=60.0
                )
                
                # Update metrics
                if result:
                    self.registry.update_agent_metrics(selected_agent, success=True)
                else:
                    self.registry.update_agent_metrics(selected_agent, success=False)
                
                return result
                
            finally:
                # Update agent load and status
                self.registry.agents[selected_agent].current_load -= 1
                if self.registry.agents[selected_agent].current_load == 0:
                    self.registry.update_agent_status(selected_agent, AgentStatus.READY)
            
        except Exception as e:
            logger.error("Error delegating task: %s", str(e))
            return None
    
    def _select_best_agent(self, available_agents: List[str]) -> str:
        """Select the best agent from available options."""
        if len(available_agents) == 1:
            return available_agents[0]
        
        # Simple selection based on load and success rate
        best_agent = available_agents[0]
        best_score = 0.0
        
        for agent_id in available_agents:
            agent_info = self.registry.agents[agent_id]
            
            # Calculate score based on load and success rate
            load_factor = 1.0 - (agent_info.current_load / agent_info.max_concurrent_tasks)
            success_factor = agent_info.success_rate
            
            score = (load_factor * 0.6) + (success_factor * 0.4)
            
            if score > best_score:
                best_score = score
                best_agent = agent_id
        
        return best_agent
    
    def get_shared_context(self, session_id: str) -> SharedContext:
        """Get or create shared context for a session."""
        if session_id not in self.shared_contexts:
            self.shared_contexts[session_id] = SharedContext(session_id=session_id, user_id="unknown")
        
        return self.shared_contexts[session_id]
    
    def update_shared_context(
        self,
        session_id: str,
        updates: Dict[str, Any]
    ) -> bool:
        """Update shared context for a session."""
        try:
            context = self.get_shared_context(session_id)
            
            for key, value in updates.items():
                if hasattr(context, key):
                    setattr(context, key, value)
                else:
                    context.shared_variables[key] = value
            
            context.updated_at = datetime.now()
            
            logger.debug("Updated shared context for session %s", session_id)
            return True
            
        except Exception as e:
            logger.error("Error updating shared context: %s", str(e))
            return False
    
    def add_message_handler(
        self,
        message_type: MessageType,
        handler: Callable[[AgentMessage], None]
    ) -> None:
        """Add a message handler for specific message types."""
        if message_type not in self.message_handlers:
            self.message_handlers[message_type] = []
        
        self.message_handlers[message_type].append(handler)
        logger.debug("Added message handler for %s", message_type.value)
    
    async def process_message_queue(self) -> None:
        """Process pending messages in the queue."""
        try:
            messages_processed = 0
            
            while self.message_queue:
                message = self.message_queue.pop(0)
                
                # Check TTL
                if message.ttl and datetime.now() > message.ttl:
                    logger.warning("Message %s expired", message.id)
                    continue
                
                # Process message
                await self._process_message(message)
                messages_processed += 1
                
                # Limit processing per cycle
                if messages_processed >= 10:
                    break
            
            if messages_processed > 0:
                logger.debug("Processed %d messages", messages_processed)
            
        except Exception as e:
            logger.error("Error processing message queue: %s", str(e))
    
    async def _process_message(self, message: AgentMessage) -> None:
        """Process an individual message."""
        try:
            # Call registered handlers
            if message.message_type in self.message_handlers:
                for handler in self.message_handlers[message.message_type]:
                    try:
                        handler(message)
                    except Exception as e:
                        logger.error("Error in message handler: %s", str(e))
            
            # Handle specific message types
            if message.message_type == MessageType.STATUS_UPDATE:
                await self._handle_status_update(message)
            elif message.message_type == MessageType.ERROR_REPORT:
                await self._handle_error_report(message)
            
        except Exception as e:
            logger.error("Error processing message %s: %s", message.id, str(e))
    
    async def _handle_status_update(self, message: AgentMessage) -> None:
        """Handle agent status update messages."""
        try:
            agent_id = message.from_agent
            status_data = message.content
            
            if "status" in status_data:
                status = AgentStatus(status_data["status"])
                self.registry.update_agent_status(agent_id, status)
            
        except Exception as e:
            logger.error("Error handling status update: %s", str(e))
    
    async def _handle_error_report(self, message: AgentMessage) -> None:
        """Handle agent error report messages."""
        try:
            agent_id = message.from_agent
            error_data = message.content
            
            logger.error("Agent %s reported error: %s", agent_id, error_data.get("error", "Unknown"))
            
            # Update agent status to error
            self.registry.update_agent_status(agent_id, AgentStatus.ERROR)
            
        except Exception as e:
            logger.error("Error handling error report: %s", str(e))
    
    def get_coordination_statistics(self) -> Dict[str, Any]:
        """Get coordination statistics and metrics."""
        try:
            stats = {
                "registered_agents": len(self.registry.agents),
                "active_agents": len([
                    a for a in self.registry.agents.values()
                    if a.status == AgentStatus.READY
                ]),
                "busy_agents": len([
                    a for a in self.registry.agents.values()
                    if a.status == AgentStatus.BUSY
                ]),
                "pending_messages": len(self.message_queue),
                "active_contexts": len(self.shared_contexts),
                "agent_breakdown": {}
            }
            
            # Agent type breakdown
            for agent_info in self.registry.agents.values():
                agent_type = agent_info.agent_type.value
                if agent_type not in stats["agent_breakdown"]:
                    stats["agent_breakdown"][agent_type] = {
                        "count": 0,
                        "ready": 0,
                        "busy": 0,
                        "average_load": 0.0
                    }
                
                breakdown = stats["agent_breakdown"][agent_type]
                breakdown["count"] += 1
                
                if agent_info.status == AgentStatus.READY:
                    breakdown["ready"] += 1
                elif agent_info.status == AgentStatus.BUSY:
                    breakdown["busy"] += 1
                
                breakdown["average_load"] += agent_info.current_load
            
            # Calculate average loads
            for agent_type_stats in stats["agent_breakdown"].values():
                if agent_type_stats["count"] > 0:
                    agent_type_stats["average_load"] /= agent_type_stats["count"]
            
            return stats
            
        except Exception as e:
            logger.error("Error calculating coordination statistics: %s", str(e))
            return {"error": str(e)}


# Export main classes
__all__ = [
    "AgentCoordinator",
    "AgentRegistry", 
    "AgentStatus",
    "AgentInfo",
    "AgentMessage",
    "SharedContext",
    "MessageType"
]
