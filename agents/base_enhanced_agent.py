# agents/base_enhanced_agent.py
"""
Base Enhanced Agent with Communication Framework Integration
===========================================================

This module provides a base class for all enhanced agents in Phase 2B.3,
integrating them with the Phase 2B.2 Inter-Agent Communication Framework.

Key Features:
- Integration with MessageBus for inter-agent messaging
- Shared context management through ContextManager
- Conflict resolution awareness and participation
- Language detection and multi-language support
- Enhanced orchestration capabilities
- Unified agent lifecycle management

All enhanced agents in Phase 2B.3 should inherit from BaseEnhancedAgent to
ensure consistent communication patterns and capabilities.
"""

import asyncio
import logging
from abc import ABC, abstractmethod
from datetime import datetime
from typing import Dict, List, Optional, Any, Union, Callable
from dataclasses import dataclass
from enum import Enum

import chainlit as cl
from langchain_core.messages import HumanMessage, AIMessage, SystemMessage
from langgraph.graph import StateGraph

# Import Phase 2B.2 Communication Framework
from communication.protocols import (
    AgentMessage, MessageType, MessagePriority, AgentType,
    RequestMessage, ResponseMessage, NotificationMessage
)
from communication.message_bus import MessageBus, MessageHandler
from communication.context_manager import ContextManager, ContextScope
from communication.conflict_resolver import (
    ConflictResolver, ConflictType, ResolutionStrategy, ConflictSeverity
)

# Import language detection capabilities
from tools.language_detection import detect_text_language, get_language_display_name
from utils.language_utils import get_language_context, is_text_mixed_language
from utils.logging_config import get_logger

logger = get_logger(__name__)


class AgentState(Enum):
    """Enhanced agent states for lifecycle management."""
    INITIALIZING = "initializing"
    READY = "ready"
    PROCESSING = "processing"
    COMMUNICATING = "communicating"
    WAITING = "waiting"
    ERROR = "error"
    SHUTDOWN = "shutdown"


class CommunicationMode(Enum):
    """Communication modes for different types of agent interactions."""
    STANDALONE = "standalone"      # Agent operates independently
    COLLABORATIVE = "collaborative"  # Agent participates in multi-agent workflow
    DELEGATING = "delegating"      # Agent delegates work to other agents
    RESPONDING = "responding"      # Agent responding to delegation


@dataclass
class AgentCapabilities:
    """Definition of enhanced agent capabilities."""
    primary_functions: List[str]
    supported_languages: List[str]
    communication_modes: List[CommunicationMode]
    conflict_resolution_strategies: List[ResolutionStrategy]
    context_scopes: List[ContextScope]
    max_concurrent_tasks: int = 3
    supports_streaming: bool = True
    requires_context: bool = True


@dataclass
class AgentMetrics:
    """Metrics for agent performance tracking."""
    tasks_completed: int = 0
    messages_sent: int = 0
    messages_received: int = 0
    conflicts_participated: int = 0
    conflicts_resolved: int = 0
    failed_requests: int = 0
    average_response_time: float = 0.0
    success_rate: float = 1.0
    last_activity: Optional[datetime] = None


class BaseEnhancedAgent(MessageHandler, ABC):
    """
    Base class for all enhanced agents with communication framework integration.
    
    This class provides the foundation for all Phase 2B.3 enhanced agents,
    ensuring consistent integration with the communication framework and
    standardized multi-agent capabilities.
    """
    
    def __init__(
        self,
        agent_id: str,
        agent_type: AgentType,
        agent_name: str,
        capabilities: AgentCapabilities,
        message_bus: Optional[MessageBus] = None,
        context_manager: Optional[ContextManager] = None,
        conflict_resolver: Optional[ConflictResolver] = None
    ):
        """
        Initialize the enhanced agent with communication capabilities.
        
        Args:
            agent_id: Unique identifier for this agent instance
            agent_type: Type of agent (from AgentType enum)
            agent_name: Human-readable agent name
            capabilities: Agent capabilities definition
            message_bus: Message bus for inter-agent communication
            context_manager: Context manager for shared state
            conflict_resolver: Conflict resolver for handling conflicts
        """
        # Initialize MessageHandler
        super().__init__(handler_id=agent_id)
        
        self.agent_id = agent_id
        self.agent_type = agent_type
        self.agent_name = agent_name
        self.capabilities = capabilities
        
        # Communication framework components
        self.message_bus = message_bus
        self.context_manager = context_manager
        self.conflict_resolver = conflict_resolver
        
        # Agent state management
        self.state = AgentState.INITIALIZING
        self.communication_mode = CommunicationMode.STANDALONE
        self.current_context_id: Optional[str] = None
        self.active_tasks: Dict[str, Any] = {}
        
        # Performance metrics
        self.metrics = AgentMetrics()
        
        # Language support
        self.current_language = "en"  # Default to English
        self.language_confidence = 1.0
        
        # Message subscriptions
        self.message_subscriptions: List[str] = []
        
        # Initialize logging
        self.logger = get_logger(f"{self.__class__.__name__}_{agent_id}")
        
    async def initialize(self) -> bool:
        """
        Initialize the agent and its communication capabilities.
        
        Returns:
            bool: True if initialization successful
        """
        try:
            self.logger.info(f"Initializing enhanced agent {self.agent_name} ({self.agent_id})")
            
            # Initialize communication components if not provided
            if not self.message_bus:
                self.message_bus = MessageBus()
                await self.message_bus.start()
                
            if not self.context_manager:
                self.context_manager = ContextManager()
                await self.context_manager.start()
                
            if not self.conflict_resolver:
                self.conflict_resolver = ConflictResolver()
            
            # Subscribe to relevant messages
            await self._setup_message_subscriptions()
            
            # Initialize agent-specific components
            await self._initialize_agent_specific()
            
            self.state = AgentState.READY
            self.metrics.last_activity = datetime.now()
            
            self.logger.info(f"Agent {self.agent_name} initialized successfully")
            return True
            
        except Exception as e:
            self.logger.error(f"Failed to initialize agent {self.agent_name}: {e}")
            self.state = AgentState.ERROR
            return False
    
    async def shutdown(self) -> bool:
        """
        Gracefully shutdown the agent and cleanup resources.
        
        Returns:
            bool: True if shutdown successful
        """
        try:
            self.logger.info(f"Shutting down agent {self.agent_name}")
            
            self.state = AgentState.SHUTDOWN
            
            # Unsubscribe from messages
            if self.message_bus:
                for subscription_id in self.message_subscriptions:
                    self.message_bus.unsubscribe(subscription_id)
            
            # Complete active tasks
            for task_id in list(self.active_tasks.keys()):
                await self._cleanup_task(task_id)
            
            # Agent-specific cleanup
            await self._cleanup_agent_specific()
            
            self.logger.info(f"Agent {self.agent_name} shutdown complete")
            return True
            
        except Exception as e:
            self.logger.error(f"Error during agent shutdown: {e}")
            return False
    
    async def process_request(
        self,
        request: str,
        context: Optional[Dict[str, Any]] = None,
        language: Optional[str] = None
    ) -> Dict[str, Any]:
        """
        Process a user request with language detection and context awareness.
        
        Args:
            request: User request to process
            context: Optional context information
            language: Optional language override
            
        Returns:
            Dict[str, Any]: Processing result with metadata
        """
        self.state = AgentState.PROCESSING
        task_id = f"task_{datetime.now().isoformat()}"
        
        try:
            # Detect language if not provided
            if not language:
                lang_code, confidence, is_reliable = detect_text_language(request)
                self.current_language = lang_code
                self.language_confidence = confidence
            else:
                self.current_language = language
                self.language_confidence = 1.0
            
            # Get language context
            lang_context = get_language_context(request)
            
            # Log language detection
            self.logger.info(f"Processing request in {lang_context.language_name} "
                           f"(confidence: {lang_context.confidence:.2f})")
            
            # Update context if available
            if self.context_manager and context:
                await self._update_shared_context(task_id, context)
            
            # Process the request (agent-specific implementation)
            result = await self._process_request_internal(
                request, context, lang_context, task_id
            )
            
            # Update metrics
            self.metrics.tasks_completed += 1
            self.metrics.last_activity = datetime.now()
            
            # Calculate success rate
            if 'success' in result:
                successes = self.metrics.tasks_completed if result['success'] else self.metrics.tasks_completed - 1
                self.metrics.success_rate = successes / self.metrics.tasks_completed
            
            self.state = AgentState.READY
            return result
            
        except Exception as e:
            self.logger.error(f"Error processing request: {e}")
            self.state = AgentState.ERROR
            return {
                'success': False,
                'error': str(e),
                'agent_id': self.agent_id,
                'task_id': task_id
            }
        finally:
            # Cleanup task
            if task_id in self.active_tasks:
                await self._cleanup_task(task_id)
    
    async def send_message(
        self,
        recipient_id: str,
        recipient_type: AgentType,
        subject: str,
        content: Dict[str, Any],
        message_type: MessageType = MessageType.NOTIFICATION,
        priority: MessagePriority = MessagePriority.NORMAL
    ) -> bool:
        """
        Send a message to another agent.
        
        Args:
            recipient_id: ID of recipient agent
            recipient_type: Type of recipient agent
            subject: Message subject
            content: Message content
            message_type: Type of message
            priority: Message priority
            
        Returns:
            bool: True if message sent successfully
        """
        if not self.message_bus:
            self.logger.error("Cannot send message: MessageBus not initialized")
            return False
        
        try:
            message = AgentMessage(
                type=message_type,
                sender_id=self.agent_id,
                sender_type=self.agent_type,
                recipient_id=recipient_id,
                recipient_type=recipient_type,
                subject=subject,
                content=content,
                priority=priority
            )
            
            await self.message_bus.send_message(message)
            self.metrics.messages_sent += 1
            
            self.logger.info(f"Message sent to {recipient_id}: {subject}")
            return True
            
        except Exception as e:
            self.logger.error(f"Failed to send message: {e}")
            return False
    
    async def participate_in_conflict(
        self,
        conflict_id: str,
        position: Dict[str, Any],
        confidence: float,
        reasoning: str = ""
    ) -> bool:
        """
        Participate in a conflict resolution.
        
        Args:
            conflict_id: ID of the conflict
            position: Agent's position on the conflict
            confidence: Confidence in the position (0.0 to 1.0)
            reasoning: Optional reasoning for the position
            
        Returns:
            bool: True if participation successful
        """
        if not self.conflict_resolver:
            self.logger.error("Cannot participate in conflict: ConflictResolver not initialized")
            return False
        
        try:
            await self.conflict_resolver.add_position(
                conflict_id=conflict_id,
                agent_id=self.agent_id,
                agent_type=self.agent_type,
                position=position,
                confidence=confidence,
                reasoning=reasoning
            )
            
            self.metrics.conflicts_participated += 1
            self.logger.info(f"Participated in conflict {conflict_id} with confidence {confidence}")
            return True
            
        except Exception as e:
            self.logger.error(f"Failed to participate in conflict: {e}")
            return False
    
    def get_metrics(self) -> AgentMetrics:
        """Get current agent performance metrics."""
        return self.metrics
    
    def get_status(self) -> Dict[str, Any]:
        """Get current agent status information."""
        return {
            'agent_id': self.agent_id,
            'agent_type': self.agent_type.value,
            'agent_name': self.agent_name,
            'state': self.state.value,
            'communication_mode': self.communication_mode.value,
            'current_language': self.current_language,
            'language_confidence': self.language_confidence,
            'active_tasks': len(self.active_tasks),
            'metrics': {
                'tasks_completed': self.metrics.tasks_completed,
                'messages_sent': self.metrics.messages_sent,
                'messages_received': self.metrics.messages_received,
                'success_rate': self.metrics.success_rate,
                'last_activity': self.metrics.last_activity.isoformat() if self.metrics.last_activity else None
            },
            'capabilities': {
                'primary_functions': self.capabilities.primary_functions,
                'supported_languages': self.capabilities.supported_languages,
                'communication_modes': [mode.value for mode in self.capabilities.communication_modes],
                'max_concurrent_tasks': self.capabilities.max_concurrent_tasks
            }
        }
    
    # Abstract methods that must be implemented by subclasses
    @abstractmethod
    async def _initialize_agent_specific(self) -> None:
        """Initialize agent-specific components. Override in subclasses."""
        pass
    
    @abstractmethod
    async def _cleanup_agent_specific(self) -> None:
        """Cleanup agent-specific resources. Override in subclasses."""
        pass
    
    @abstractmethod
    async def _process_request_internal(
        self,
        request: str,
        context: Optional[Dict[str, Any]],
        language_context: Any,
        task_id: str
    ) -> Dict[str, Any]:
        """Process request internally. Override in subclasses."""
        pass
    
    # Private helper methods
    async def _setup_message_subscriptions(self) -> None:
        """Setup message subscriptions based on agent capabilities."""
        if not self.message_bus:
            return
        
        # Subscribe to relevant message types
        message_types = {
            MessageType.REQUEST,
            MessageType.NOTIFICATION,
            MessageType.BROADCAST
        }
        
        # Subscribe this agent as a message handler
        subscription_id = self.message_bus.subscribe(
            handler=self,
            message_types=message_types
        )
        
        self.message_subscriptions.append(subscription_id)
    
    async def handle_message(self, message: AgentMessage) -> Optional[AgentMessage]:
        """
        MessageHandler implementation - handle incoming messages from other agents.
        """
        return await self._handle_message(message)

    async def _handle_message(self, message: AgentMessage) -> Optional[AgentMessage]:
        """Handle incoming messages from other agents."""
        try:
            self.metrics.messages_received += 1
            self.logger.info(f"Received message from {message.sender_id}: {message.subject}")
            
            # Process message based on type and return potential response
            if message.type == MessageType.REQUEST:
                return await self._handle_request_message(message)
            elif message.type == MessageType.NOTIFICATION:
                return await self._handle_notification_message(message)
            elif message.type == MessageType.BROADCAST:
                return await self._handle_broadcast_message(message)
            
            return None
            
        except Exception as e:
            self.logger.error(f"Error handling message: {e}")
            return None
    
    async def _handle_request_message(self, message: AgentMessage) -> Optional[AgentMessage]:
        """Handle request messages from other agents."""
        # Default implementation - can be overridden by subclasses
        self.logger.info(f"Processing request from {message.sender_id}")
        
        # Create acknowledgment response
        response = AgentMessage(
            sender_id=self.agent_id,
            sender_type=self.agent_type,
            recipient_id=message.sender_id,
            recipient_type=message.sender_type,
            subject=f"Re: {message.subject}",
            content={"status": "received", "message_id": message.id},
            message_type=MessageType.RESPONSE,
            priority=message.priority
        )
        
        return response
    
    async def _handle_notification_message(self, message: AgentMessage) -> Optional[AgentMessage]:
        """Handle notification messages from other agents."""
        # Default implementation - can be overridden by subclasses
        self.logger.info(f"Received notification from {message.sender_id}: {message.subject}")
        return None
    
    async def _handle_broadcast_message(self, message: AgentMessage) -> Optional[AgentMessage]:
        """Handle broadcast messages."""
        # Default implementation - can be overridden by subclasses
        self.logger.info(f"Received broadcast: {message.subject}")
        return None
    
    async def _update_shared_context(self, task_id: str, context: Dict[str, Any]) -> None:
        """Update shared context with task information."""
        if not self.context_manager:
            return
        
        try:
            task_context = await self.context_manager.get_context(
                task_id, ContextScope.TASK
            )
            
            await task_context.set(
                f"{self.agent_id}_status",
                {
                    "agent_id": self.agent_id,
                    "agent_type": self.agent_type.value,
                    "status": self.state.value,
                    "context": context,
                    "timestamp": datetime.now().isoformat()
                },
                self.agent_id,
                self.agent_type,
                f"Status update from {self.agent_name}"
            )
            
        except Exception as e:
            self.logger.error(f"Error updating shared context: {e}")
    
    async def _cleanup_task(self, task_id: str) -> None:
        """Cleanup resources for a completed task."""
        if task_id in self.active_tasks:
            del self.active_tasks[task_id]
        
        # Additional cleanup can be implemented by subclasses
