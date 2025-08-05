# communication/__init__.py
"""
Inter-Agent Communication Framework for Jarvis-MK42

This module provides sophisticated communication capabilities for multi-agent coordination:
- Async message bus for agent-to-agent communication
- Context preservation across agent handoffs  
- Structured data sharing protocols
- Conflict resolution for competing recommendations
- Event-driven architecture for scalable coordination

Key Components:
- MessageBus: Core async messaging infrastructure
- ContextManager: Shared state and memory management
- CommunicationProtocols: Standard message formats and patterns
- ConflictResolver: Handle competing agent recommendations
- EventSystem: Publish-subscribe event handling

Integration:
- Works seamlessly with SupervisorAgent for orchestration
- Extends AgentCoordinator capabilities with advanced messaging
- Database integration for persistent context and message history
- Full async/await support for non-blocking operations
"""

from .protocols import (
    MessageType,
    MessagePriority,
    AgentType,
    AgentMessage,
    RequestMessage,
    ResponseMessage,
    NotificationMessage,
    BroadcastMessage,
    ContextUpdate,
    ConflictResolutionRequest,
    CommunicationProtocol
)

from .message_bus import (
    MessageBus,
    MessageQueue,
    MessageRouter,
    MessageSubscription
)

from .context_manager import (
    ContextManager,
    SharedContext,
    ContextScope,
    ContextAccessLevel,
    MergeStrategy,
    ContextVersion,
    ContextMetadata,
    ContextConflict
)

from .conflict_resolver import (
    ConflictResolver,
    Conflict,
    ConflictType,
    ResolutionStrategy,
    ConflictSeverity,
    AgentPosition,
    ConflictContext
)

__all__ = [
    # Protocols
    "MessageType",
    "MessagePriority",
    "AgentType", 
    "AgentMessage",
    "RequestMessage",
    "ResponseMessage",
    "NotificationMessage",
    "BroadcastMessage",
    "ContextUpdate",
    "ConflictResolutionRequest",
    "CommunicationProtocol",
    
    # Message Bus
    "MessageBus",
    "MessageQueue",
    "MessageRouter",
    "MessageSubscription",
    
    # Context Management
    "ContextManager",
    "SharedContext",
    "ContextScope",
    "ContextAccessLevel",
    "MergeStrategy",
    "ContextVersion",
    "ContextMetadata",
    "ContextConflict",
    
    # Conflict Resolution
    "ConflictResolver",
    "Conflict",
    "ConflictType",
    "ResolutionStrategy",
    "ConflictSeverity",
    "AgentPosition",
    "ConflictContext"
]

# Version information
__version__ = "2.1.0"
__phase__ = "2B.2"
__description__ = "Inter-Agent Communication Framework"
