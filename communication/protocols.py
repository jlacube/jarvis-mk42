# communication/protocols.py
"""
Communication Protocols and Data Structures for Inter-Agent Communication

This module defines the standard message formats, data structures, and communication
patterns used throughout the multi-agent system for consistent and reliable
agent-to-agent communication.
"""

import uuid
from datetime import datetime
from enum import Enum
from typing import Any, Dict, List, Optional, Union, Literal
from dataclasses import dataclass, field
from pydantic import BaseModel, Field


class MessageType(Enum):
    """Types of messages in the inter-agent communication system."""
    REQUEST = "request"
    RESPONSE = "response"
    NOTIFICATION = "notification"
    BROADCAST = "broadcast"
    CONTEXT_UPDATE = "context_update"
    CONFLICT_RESOLUTION = "conflict_resolution"
    HEARTBEAT = "heartbeat"
    ERROR = "error"


class MessagePriority(Enum):
    """Priority levels for message processing."""
    LOW = 1
    NORMAL = 2
    HIGH = 3
    URGENT = 4
    CRITICAL = 5


class AgentType(Enum):
    """Types of agents in the system."""
    SUPERVISOR = "supervisor"
    REASONING = "reasoning"
    RESEARCH = "research" 
    CODING = "coding"
    MULTIMODAL = "multimodal"
    DOCUMENT_INTELLIGENCE = "document_intelligence"


class MessageStatus(Enum):
    """Status of message processing."""
    PENDING = "pending"
    PROCESSING = "processing"
    DELIVERED = "delivered"
    ACKNOWLEDGED = "acknowledged"
    FAILED = "failed"
    TIMEOUT = "timeout"


@dataclass
class MessageMetadata:
    """Metadata for message tracking and routing."""
    message_id: str = field(default_factory=lambda: str(uuid.uuid4()))
    correlation_id: Optional[str] = None
    conversation_id: Optional[str] = None
    created_at: datetime = field(default_factory=datetime.now)
    expires_at: Optional[datetime] = None
    retry_count: int = 0
    max_retries: int = 3
    tags: Dict[str, str] = field(default_factory=dict)


class AgentMessage(BaseModel):
    """Base message class for all inter-agent communication."""
    
    # Core message properties
    type: MessageType = Field(description="Type of message")
    priority: MessagePriority = Field(default=MessagePriority.NORMAL, description="Message priority")
    
    # Routing information
    sender_id: str = Field(description="ID of the sending agent")
    sender_type: AgentType = Field(description="Type of the sending agent")
    recipient_id: Optional[str] = Field(default=None, description="ID of the target recipient (None for broadcasts)")
    recipient_type: Optional[AgentType] = Field(default=None, description="Type of the target recipient")
    
    # Message content
    subject: str = Field(description="Message subject or title")
    content: Dict[str, Any] = Field(default_factory=dict, description="Message payload")
    
    # Message tracking
    metadata: MessageMetadata = Field(default_factory=MessageMetadata)
    status: MessageStatus = Field(default=MessageStatus.PENDING)
    
    # Context information
    context_id: Optional[str] = Field(default=None, description="Associated context ID")
    workflow_id: Optional[str] = Field(default=None, description="Associated workflow ID")
    
    class Config:
        use_enum_values = True


class RequestMessage(AgentMessage):
    """Request message for agent-to-agent service calls."""
    type: Literal[MessageType.REQUEST] = MessageType.REQUEST
    
    # Request-specific fields
    service: str = Field(description="Requested service or operation")
    parameters: Dict[str, Any] = Field(default_factory=dict, description="Service parameters")
    timeout_seconds: Optional[int] = Field(default=30, description="Request timeout")
    expects_response: bool = Field(default=True, description="Whether a response is expected")


class ResponseMessage(AgentMessage):
    """Response message for request-response patterns."""
    type: Literal[MessageType.RESPONSE] = MessageType.RESPONSE
    
    # Response-specific fields
    request_id: str = Field(description="ID of the original request message")
    success: bool = Field(description="Whether the request was successful")
    result: Dict[str, Any] = Field(default_factory=dict, description="Response data")
    error_message: Optional[str] = Field(default=None, description="Error description if failed")
    execution_time_ms: Optional[int] = Field(default=None, description="Processing time in milliseconds")


class NotificationMessage(AgentMessage):
    """Notification message for status updates and events."""
    type: Literal[MessageType.NOTIFICATION] = MessageType.NOTIFICATION
    
    # Notification-specific fields
    event_type: str = Field(description="Type of event or notification")
    event_data: Dict[str, Any] = Field(default_factory=dict, description="Event details")
    is_persistent: bool = Field(default=False, description="Whether notification should be stored")


class BroadcastMessage(AgentMessage):
    """Broadcast message for system-wide announcements."""
    type: Literal[MessageType.BROADCAST] = MessageType.BROADCAST
    
    # Broadcast-specific fields
    target_agents: List[AgentType] = Field(default_factory=list, description="Target agent types (empty = all)")
    announcement_type: str = Field(description="Type of announcement")
    announcement_data: Dict[str, Any] = Field(default_factory=dict, description="Announcement details")


class ContextUpdate(AgentMessage):
    """Message for sharing context updates between agents."""
    type: Literal[MessageType.CONTEXT_UPDATE] = MessageType.CONTEXT_UPDATE
    
    # Context update fields
    context_key: str = Field(description="Key identifying the context being updated")
    update_type: Literal["create", "update", "delete", "merge"] = Field(description="Type of context update")
    context_data: Dict[str, Any] = Field(default_factory=dict, description="Updated context data")
    version: int = Field(default=1, description="Context version number")
    merge_strategy: Optional[str] = Field(default=None, description="Strategy for merging conflicting updates")


class ConflictResolutionRequest(AgentMessage):
    """Message for requesting conflict resolution between competing recommendations."""
    type: Literal[MessageType.CONFLICT_RESOLUTION] = MessageType.CONFLICT_RESOLUTION
    
    # Conflict resolution fields
    conflict_type: str = Field(description="Type of conflict to resolve")
    competing_options: List[Dict[str, Any]] = Field(description="List of conflicting options/recommendations")
    resolution_criteria: Dict[str, Any] = Field(default_factory=dict, description="Criteria for resolution")
    timeout_seconds: int = Field(default=60, description="Resolution timeout")


class CommunicationProtocol:
    """
    Protocol definitions and utilities for inter-agent communication.
    
    This class provides standardized patterns and utilities for common
    communication scenarios in the multi-agent system.
    """
    
    @staticmethod
    def create_request(
        sender_id: str,
        sender_type: AgentType,
        recipient_id: str,
        recipient_type: AgentType,
        service: str,
        parameters: Dict[str, Any] = None,
        subject: str = None,
        priority: MessagePriority = MessagePriority.NORMAL,
        timeout_seconds: int = 30,
        context_id: str = None,
        workflow_id: str = None
    ) -> RequestMessage:
        """Create a standardized request message."""
        return RequestMessage(
            sender_id=sender_id,
            sender_type=sender_type,
            recipient_id=recipient_id,
            recipient_type=recipient_type,
            subject=subject or f"Request: {service}",
            service=service,
            parameters=parameters or {},
            priority=priority,
            timeout_seconds=timeout_seconds,
            context_id=context_id,
            workflow_id=workflow_id
        )
    
    @staticmethod
    def create_response(
        request: RequestMessage,
        sender_id: str,
        sender_type: AgentType,
        success: bool,
        result: Dict[str, Any] = None,
        error_message: str = None,
        execution_time_ms: int = None
    ) -> ResponseMessage:
        """Create a response message for a given request."""
        return ResponseMessage(
            sender_id=sender_id,
            sender_type=sender_type,
            recipient_id=request.sender_id,
            recipient_type=request.sender_type,
            subject=f"Response: {request.subject}",
            request_id=request.metadata.message_id,
            success=success,
            result=result or {},
            error_message=error_message,
            execution_time_ms=execution_time_ms,
            context_id=request.context_id,
            workflow_id=request.workflow_id,
            metadata=MessageMetadata(correlation_id=request.metadata.message_id)
        )
    
    @staticmethod
    def create_notification(
        sender_id: str,
        sender_type: AgentType,
        event_type: str,
        event_data: Dict[str, Any] = None,
        subject: str = None,
        recipient_id: str = None,
        recipient_type: AgentType = None,
        priority: MessagePriority = MessagePriority.NORMAL,
        is_persistent: bool = False,
        context_id: str = None,
        workflow_id: str = None
    ) -> NotificationMessage:
        """Create a standardized notification message."""
        return NotificationMessage(
            sender_id=sender_id,
            sender_type=sender_type,
            recipient_id=recipient_id,
            recipient_type=recipient_type,
            subject=subject or f"Notification: {event_type}",
            event_type=event_type,
            event_data=event_data or {},
            priority=priority,
            is_persistent=is_persistent,
            context_id=context_id,
            workflow_id=workflow_id
        )
    
    @staticmethod
    def create_broadcast(
        sender_id: str,
        sender_type: AgentType,
        announcement_type: str,
        announcement_data: Dict[str, Any] = None,
        subject: str = None,
        target_agents: List[AgentType] = None,
        priority: MessagePriority = MessagePriority.NORMAL,
        context_id: str = None,
        workflow_id: str = None
    ) -> BroadcastMessage:
        """Create a standardized broadcast message."""
        return BroadcastMessage(
            sender_id=sender_id,
            sender_type=sender_type,
            subject=subject or f"Broadcast: {announcement_type}",
            target_agents=target_agents or [],
            announcement_type=announcement_type,
            announcement_data=announcement_data or {},
            priority=priority,
            context_id=context_id,
            workflow_id=workflow_id
        )
    
    @staticmethod
    def create_context_update(
        sender_id: str,
        sender_type: AgentType,
        context_key: str,
        update_type: Literal["create", "update", "delete", "merge"],
        context_data: Dict[str, Any],
        version: int = 1,
        subject: str = None,
        recipient_id: str = None,
        recipient_type: AgentType = None,
        merge_strategy: str = None,
        context_id: str = None,
        workflow_id: str = None
    ) -> ContextUpdate:
        """Create a standardized context update message."""
        return ContextUpdate(
            sender_id=sender_id,
            sender_type=sender_type,
            recipient_id=recipient_id,
            recipient_type=recipient_type,
            subject=subject or f"Context Update: {context_key}",
            context_key=context_key,
            update_type=update_type,
            context_data=context_data,
            version=version,
            merge_strategy=merge_strategy,
            context_id=context_id,
            workflow_id=workflow_id
        )


# Message validation utilities
def validate_message(message: AgentMessage) -> List[str]:
    """Validate a message and return list of validation errors."""
    errors = []
    
    # Check required fields
    if not message.sender_id:
        errors.append("sender_id is required")
    if not message.subject:
        errors.append("subject is required")
    
    # Check recipient requirements for targeted messages
    if message.type in [MessageType.REQUEST, MessageType.RESPONSE] and not message.recipient_id:
        errors.append("recipient_id is required for request/response messages")
    
    # Check request-specific requirements
    if isinstance(message, RequestMessage):
        if not message.service:
            errors.append("service is required for request messages")
    
    # Check response-specific requirements
    if isinstance(message, ResponseMessage):
        if not message.request_id:
            errors.append("request_id is required for response messages")
    
    return errors


# Message type registry for serialization/deserialization
MESSAGE_TYPE_REGISTRY = {
    MessageType.REQUEST: RequestMessage,
    MessageType.RESPONSE: ResponseMessage,
    MessageType.NOTIFICATION: NotificationMessage,
    MessageType.BROADCAST: BroadcastMessage,
    MessageType.CONTEXT_UPDATE: ContextUpdate,
    MessageType.CONFLICT_RESOLUTION: ConflictResolutionRequest
}
