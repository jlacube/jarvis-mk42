# communication/message_bus.py
"""
Async Message Bus System for Inter-Agent Communication

This module provides a high-performance, async message bus that enables
sophisticated agent-to-agent communication patterns including:
- Request-response messaging
- Publish-subscribe events
- Message routing and filtering
- Priority-based message processing  
- Message persistence and replay
- Error handling and dead letter queues
"""

import asyncio
import logging
from datetime import datetime, timedelta
from typing import Any, Callable, Dict, List, Optional, Set, Union
from collections import defaultdict, deque
from dataclasses import dataclass, field
from enum import Enum
import weakref

from .protocols import (
    AgentMessage, MessageType, MessagePriority, MessageStatus,
    AgentType, RequestMessage, ResponseMessage, validate_message
)
from utils.logging_config import get_logger
from utils.exceptions import CoordinationError

logger = get_logger(__name__)


class QueuePolicy(Enum):
    """Policies for handling message queue overflow."""
    DROP_OLDEST = "drop_oldest"
    DROP_NEWEST = "drop_newest"
    BLOCK = "block"
    RAISE_ERROR = "raise_error"


@dataclass
class MessageSubscription:
    """Subscription details for message handling."""
    handler_id: str
    message_types: Set[MessageType]
    agent_types: Set[AgentType] = field(default_factory=set)
    priority_filter: Optional[MessagePriority] = None
    context_filter: Optional[str] = None
    workflow_filter: Optional[str] = None
    is_active: bool = True
    created_at: datetime = field(default_factory=datetime.now)
    message_count: int = 0
    last_message_at: Optional[datetime] = None


@dataclass  
class MessageQueueStats:
    """Statistics for message queue monitoring."""
    total_messages: int = 0
    pending_messages: int = 0
    processed_messages: int = 0
    failed_messages: int = 0
    average_processing_time_ms: float = 0.0
    oldest_pending_age_seconds: float = 0.0
    queue_depth_by_priority: Dict[MessagePriority, int] = field(default_factory=dict)


class MessageHandler:
    """Base class for message handlers with async support."""
    
    def __init__(self, handler_id: str):
        self.handler_id = handler_id
        self.is_active = True
        self.message_count = 0
        self.last_message_at: Optional[datetime] = None
    
    async def handle_message(self, message: AgentMessage) -> Optional[AgentMessage]:
        """
        Handle an incoming message.
        
        Args:
            message: The message to handle
            
        Returns:
            Optional response message
            
        Raises:
            NotImplementedError: Must be implemented by subclasses
        """
        raise NotImplementedError("Subclasses must implement handle_message")
    
    async def on_error(self, message: AgentMessage, error: Exception) -> None:
        """Handle message processing errors."""
        logger.error(
            "Error handling message %s in handler %s: %s",
            message.metadata.message_id,
            self.handler_id,
            str(error)
        )


class MessageQueue:
    """Priority-based async message queue with overflow protection."""
    
    def __init__(
        self,
        max_size: int = 1000,
        overflow_policy: QueuePolicy = QueuePolicy.DROP_OLDEST
    ):
        self.max_size = max_size
        self.overflow_policy = overflow_policy
        self._queues: Dict[MessagePriority, deque] = {
            priority: deque() for priority in MessagePriority
        }
        self._condition = asyncio.Condition()
        self._stats = MessageQueueStats()
        self._closed = False
    
    async def put(self, message: AgentMessage, block: bool = True) -> bool:
        """
        Add a message to the queue.
        
        Args:
            message: Message to add
            block: Whether to block if queue is full
            
        Returns:
            True if message was added, False otherwise
        """
        async with self._condition:
            if self._closed:
                return False
            
            # Check queue size and apply overflow policy
            current_size = sum(len(q) for q in self._queues.values())
            if current_size >= self.max_size:
                if not await self._handle_overflow(block):
                    return False
            
            # Add message to appropriate priority queue
            self._queues[message.priority].append(message)
            self._stats.total_messages += 1
            self._stats.pending_messages += 1
            self._stats.queue_depth_by_priority[message.priority] = len(self._queues[message.priority])
            
            # Update message status
            message.status = MessageStatus.PENDING
            
            # Notify waiting consumers
            self._condition.notify()
            
            logger.debug(
                "Message %s added to queue with priority %s",
                message.metadata.message_id,
                message.priority.value
            )
            
            return True
    
    async def get(self, timeout: Optional[float] = None) -> Optional[AgentMessage]:
        """
        Get the next highest priority message from the queue.
        
        Args:
            timeout: Maximum time to wait for a message
            
        Returns:
            Next message or None if timeout/closed
        """
        async with self._condition:
            # Wait for messages or timeout
            try:
                await asyncio.wait_for(
                    self._condition.wait_for(lambda: self._has_messages() or self._closed),
                    timeout=timeout
                )
            except asyncio.TimeoutError:
                return None
            
            if self._closed and not self._has_messages():
                return None
            
            # Get highest priority message
            for priority in reversed(list(MessagePriority)):
                if self._queues[priority]:
                    message = self._queues[priority].popleft()
                    message.status = MessageStatus.PROCESSING
                    
                    self._stats.pending_messages -= 1
                    self._stats.queue_depth_by_priority[priority] = len(self._queues[priority])
                    
                    logger.debug(
                        "Message %s retrieved from queue with priority %s",
                        message.metadata.message_id,
                        priority.value
                    )
                    
                    return message
            
            return None
    
    async def _handle_overflow(self, block: bool) -> bool:
        """Handle queue overflow based on policy."""
        if self.overflow_policy == QueuePolicy.BLOCK and block:
            # Wait for space in queue
            await self._condition.wait_for(
                lambda: sum(len(q) for q in self._queues.values()) < self.max_size
            )
            return True
        elif self.overflow_policy == QueuePolicy.DROP_OLDEST:
            # Drop oldest message from lowest priority queue
            for priority in MessagePriority:
                if self._queues[priority]:
                    dropped = self._queues[priority].popleft()
                    logger.warning(
                        "Dropped oldest message %s due to queue overflow",
                        dropped.metadata.message_id
                    )
                    return True
        elif self.overflow_policy == QueuePolicy.DROP_NEWEST:
            # Don't add the new message
            logger.warning("Dropping newest message due to queue overflow")
            return False
        elif self.overflow_policy == QueuePolicy.RAISE_ERROR:
            raise CoordinationError("Message queue is full")
        
        return False
    
    def _has_messages(self) -> bool:
        """Check if queue has any messages."""
        return any(queue for queue in self._queues.values())
    
    async def close(self):
        """Close the queue and notify all waiters."""
        async with self._condition:
            self._closed = True
            self._condition.notify_all()
    
    def get_stats(self) -> MessageQueueStats:
        """Get current queue statistics."""
        # Update oldest pending age
        oldest_time = None
        for queue in self._queues.values():
            for message in queue:
                if oldest_time is None or message.metadata.created_at < oldest_time:
                    oldest_time = message.metadata.created_at
        
        if oldest_time:
            self._stats.oldest_pending_age_seconds = (
                datetime.now() - oldest_time
            ).total_seconds()
        
        return self._stats


class MessageRouter:
    """Routes messages to appropriate handlers based on subscriptions."""
    
    def __init__(self):
        self._subscriptions: Dict[str, MessageSubscription] = {}
        self._handlers: Dict[str, MessageHandler] = {}
        self._message_history: List[AgentMessage] = []
        self._max_history = 1000
    
    def subscribe(
        self,
        handler: MessageHandler,
        message_types: Set[MessageType],
        agent_types: Set[AgentType] = None,
        priority_filter: MessagePriority = None,
        context_filter: str = None,
        workflow_filter: str = None
    ) -> str:
        """
        Subscribe a handler to specific message types and filters.
        
        Args:
            handler: Message handler instance
            message_types: Set of message types to handle
            agent_types: Optional filter by sender agent types
            priority_filter: Optional minimum priority filter
            context_filter: Optional context ID filter
            workflow_filter: Optional workflow ID filter
            
        Returns:
            Subscription ID
        """
        subscription = MessageSubscription(
            handler_id=handler.handler_id,
            message_types=message_types,
            agent_types=agent_types or set(),
            priority_filter=priority_filter,
            context_filter=context_filter,
            workflow_filter=workflow_filter
        )
        
        self._subscriptions[handler.handler_id] = subscription
        self._handlers[handler.handler_id] = handler
        
        logger.info(
            "Handler %s subscribed to message types: %s",
            handler.handler_id,
            [t.value for t in message_types]
        )
        
        return handler.handler_id
    
    def unsubscribe(self, handler_id: str) -> bool:
        """Unsubscribe a handler."""
        if handler_id in self._subscriptions:
            del self._subscriptions[handler_id]
            del self._handlers[handler_id]
            logger.info("Handler %s unsubscribed", handler_id)
            return True
        return False
    
    async def route_message(self, message: AgentMessage) -> List[AgentMessage]:
        """
        Route a message to all matching subscribers.
        
        Args:
            message: Message to route
            
        Returns:
            List of response messages from handlers
        """
        # Store message in history
        self._message_history.append(message)
        if len(self._message_history) > self._max_history:
            self._message_history.pop(0)
        
        responses = []
        matched_handlers = []
        
        # Find matching subscriptions
        for handler_id, subscription in self._subscriptions.items():
            if self._matches_subscription(message, subscription):
                matched_handlers.append(handler_id)
        
        # Route to matching handlers
        for handler_id in matched_handlers:
            try:
                handler = self._handlers[handler_id]
                subscription = self._subscriptions[handler_id]
                
                # Update subscription stats
                subscription.message_count += 1
                subscription.last_message_at = datetime.now()
                
                # Handle message
                response = await handler.handle_message(message)
                if response:
                    responses.append(response)
                
                logger.debug(
                    "Message %s handled by %s",
                    message.metadata.message_id,
                    handler_id
                )
                
            except Exception as e:
                logger.error(
                    "Error routing message %s to handler %s: %s",
                    message.metadata.message_id,
                    handler_id,
                    str(e)
                )
                
                # Call error handler
                try:
                    await handler.on_error(message, e)
                except Exception as error_handler_error:
                    logger.error(
                        "Error in error handler for %s: %s",
                        handler_id,
                        str(error_handler_error)
                    )
        
        message.status = MessageStatus.DELIVERED if matched_handlers else MessageStatus.FAILED
        
        logger.debug(
            "Message %s routed to %d handlers",
            message.metadata.message_id,
            len(matched_handlers)
        )
        
        return responses
    
    def _matches_subscription(self, message: AgentMessage, subscription: MessageSubscription) -> bool:
        """Check if a message matches a subscription."""
        if not subscription.is_active:
            return False
        
        # Check message type
        if message.type not in subscription.message_types:
            return False
        
        # Check agent type filter
        if subscription.agent_types and message.sender_type not in subscription.agent_types:
            return False
        
        # Check priority filter
        if subscription.priority_filter and message.priority.value < subscription.priority_filter.value:
            return False
        
        # Check context filter
        if subscription.context_filter and message.context_id != subscription.context_filter:
            return False
        
        # Check workflow filter
        if subscription.workflow_filter and message.workflow_id != subscription.workflow_filter:
            return False
        
        return True
    
    def get_subscription_stats(self) -> Dict[str, Dict[str, Any]]:
        """Get statistics for all subscriptions."""
        stats = {}
        for handler_id, subscription in self._subscriptions.items():
            stats[handler_id] = {
                "message_types": [t.value for t in subscription.message_types],
                "agent_types": [t.value for t in subscription.agent_types],
                "message_count": subscription.message_count,
                "last_message_at": subscription.last_message_at,
                "is_active": subscription.is_active
            }
        return stats


class MessageBus:
    """
    High-performance async message bus for inter-agent communication.
    
    Provides comprehensive messaging capabilities including:
    - Priority-based message queuing
    - Subscription-based routing
    - Request-response patterns  
    - Message persistence and replay
    - Performance monitoring
    - Error handling and recovery
    """
    
    def __init__(
        self,
        max_queue_size: int = 1000,
        overflow_policy: QueuePolicy = QueuePolicy.DROP_OLDEST,
        enable_persistence: bool = False
    ):
        self.max_queue_size = max_queue_size
        self.overflow_policy = overflow_policy
        self.enable_persistence = enable_persistence
        
        # Core components
        self._message_queue = MessageQueue(max_queue_size, overflow_policy)
        self._router = MessageRouter()
        
        # Processing control
        self._is_running = False
        self._processor_task: Optional[asyncio.Task] = None
        
        # Request-response tracking
        self._pending_requests: Dict[str, asyncio.Future] = {}
        self._request_timeouts: Dict[str, asyncio.Task] = {}
        
        # Performance tracking
        self._processing_times: deque = deque(maxlen=1000)
        self._error_count = 0
        
        logger.info("MessageBus initialized with max_queue_size=%d", max_queue_size)
    
    async def start(self):
        """Start the message bus processing."""
        if self._is_running:
            return
        
        self._is_running = True
        self._processor_task = asyncio.create_task(self._process_messages())
        
        logger.info("MessageBus started")
    
    async def stop(self):
        """Stop the message bus processing."""
        if not self._is_running:
            return
        
        self._is_running = False
        
        # Cancel processor task
        if self._processor_task:
            self._processor_task.cancel()
            try:
                await self._processor_task
            except asyncio.CancelledError:
                pass
        
        # Close message queue
        await self._message_queue.close()
        
        # Cancel pending requests
        for future in self._pending_requests.values():
            if not future.done():
                future.cancel()
        
        # Cancel timeout tasks
        for task in self._request_timeouts.values():
            task.cancel()
        
        logger.info("MessageBus stopped")
    
    async def send_message(self, message: AgentMessage, block: bool = True) -> bool:
        """
        Send a message through the bus.
        
        Args:
            message: Message to send
            block: Whether to block if queue is full
            
        Returns:
            True if message was queued successfully
        """
        # Validate message
        validation_errors = validate_message(message)
        if validation_errors:
            raise CoordinationError(f"Message validation failed: {validation_errors}")
        
        # Queue message for processing
        success = await self._message_queue.put(message, block)
        
        if success:
            logger.debug(
                "Message %s queued for processing",
                message.metadata.message_id
            )
        else:
            logger.warning(
                "Failed to queue message %s",
                message.metadata.message_id
            )
        
        return success
    
    async def send_request(
        self,
        request: RequestMessage,
        timeout_seconds: Optional[int] = None
    ) -> Optional[ResponseMessage]:
        """
        Send a request and wait for response.
        
        Args:
            request: Request message to send
            timeout_seconds: Response timeout (uses request.timeout_seconds if not provided)
            
        Returns:
            Response message or None if timeout
        """
        if not request.expects_response:
            await self.send_message(request)
            return None
        
        timeout = timeout_seconds or request.timeout_seconds or 30
        request_id = request.metadata.message_id
        
        # Create future for response
        response_future = asyncio.Future()
        self._pending_requests[request_id] = response_future
        
        # Set up timeout
        timeout_task = asyncio.create_task(self._handle_request_timeout(request_id, timeout))
        self._request_timeouts[request_id] = timeout_task
        
        try:
            # Send request
            await self.send_message(request)
            
            # Wait for response
            response = await response_future
            return response
            
        except asyncio.TimeoutError:
            logger.warning(
                "Request %s timed out after %d seconds",
                request_id,
                timeout
            )
            return None
            
        finally:
            # Cleanup
            self._pending_requests.pop(request_id, None)
            timeout_task.cancel()
            self._request_timeouts.pop(request_id, None)
    
    def subscribe(
        self,
        handler: MessageHandler,
        message_types: Set[MessageType],
        **filters
    ) -> str:
        """Subscribe a handler to message types with optional filters."""
        return self._router.subscribe(handler, message_types, **filters)
    
    def unsubscribe(self, handler_id: str) -> bool:
        """Unsubscribe a handler."""
        return self._router.unsubscribe(handler_id)
    
    async def _process_messages(self):
        """Main message processing loop."""
        logger.info("Message processing started")
        
        while self._is_running:
            try:
                # Get next message from queue
                message = await self._message_queue.get(timeout=1.0)
                if not message:
                    continue
                
                start_time = datetime.now()
                
                # Route message to handlers
                responses = await self._router.route_message(message)
                
                # Handle responses
                for response in responses:
                    if isinstance(response, ResponseMessage):
                        await self._handle_response(response)
                    else:
                        # Route response message back through the bus
                        await self.send_message(response, block=False)
                
                # Update processing time stats
                processing_time = (datetime.now() - start_time).total_seconds() * 1000
                self._processing_times.append(processing_time)
                
                # Update queue stats
                queue_stats = self._message_queue.get_stats()
                queue_stats.processed_messages += 1
                if self._processing_times:
                    queue_stats.average_processing_time_ms = sum(self._processing_times) / len(self._processing_times)
                
                logger.debug(
                    "Message %s processed in %.2fms",
                    message.metadata.message_id,
                    processing_time
                )
                
            except asyncio.CancelledError:
                break
            except Exception as e:
                self._error_count += 1
                logger.error("Error processing message: %s", str(e))
                
                # Update queue stats
                queue_stats = self._message_queue.get_stats()
                queue_stats.failed_messages += 1
        
        logger.info("Message processing stopped")
    
    async def _handle_response(self, response: ResponseMessage):
        """Handle response message for pending requests."""
        request_id = response.request_id
        
        if request_id in self._pending_requests:
            future = self._pending_requests[request_id]
            if not future.done():
                future.set_result(response)
            
            logger.debug(
                "Response for request %s delivered",
                request_id
            )
        else:
            logger.warning(
                "Received response for unknown request %s",
                request_id
            )
    
    async def _handle_request_timeout(self, request_id: str, timeout_seconds: int):
        """Handle request timeout."""
        try:
            await asyncio.sleep(timeout_seconds)
            
            if request_id in self._pending_requests:
                future = self._pending_requests[request_id]
                if not future.done():
                    future.set_exception(asyncio.TimeoutError())
                
        except asyncio.CancelledError:
            pass
    
    def get_stats(self) -> Dict[str, Any]:
        """Get comprehensive message bus statistics."""
        queue_stats = self._message_queue.get_stats()
        subscription_stats = self._router.get_subscription_stats()
        
        return {
            "is_running": self._is_running,
            "queue_stats": {
                "total_messages": queue_stats.total_messages,
                "pending_messages": queue_stats.pending_messages,
                "processed_messages": queue_stats.processed_messages,
                "failed_messages": queue_stats.failed_messages,
                "average_processing_time_ms": queue_stats.average_processing_time_ms,
                "oldest_pending_age_seconds": queue_stats.oldest_pending_age_seconds,
                "queue_depth_by_priority": {
                    p.value: count for p, count in queue_stats.queue_depth_by_priority.items()
                }
            },
            "subscription_stats": subscription_stats,
            "request_response_stats": {
                "pending_requests": len(self._pending_requests),
                "active_timeouts": len(self._request_timeouts)
            },
            "error_count": self._error_count
        }
