# communication/context_manager.py
"""
Context Manager for Shared State in Multi-Agent Communication

This module provides sophisticated context management capabilities that enable
agents to share and synchronize state across complex workflows. Features include:
- Hierarchical context scoping (global, workflow, conversation, task)
- Version control and conflict resolution for concurrent updates
- Context persistence and restoration
- Event-driven context change notifications
- Memory-efficient storage with automatic cleanup
"""

import asyncio
import json
import logging
from datetime import datetime, timedelta
from typing import Any, Dict, List, Optional, Set, Union, Callable
from dataclasses import dataclass, field
from enum import Enum
from collections import defaultdict
import weakref

from .protocols import AgentType, ContextUpdate, MessageType
from utils.logging_config import get_logger
from utils.exceptions import CoordinationError

logger = get_logger(__name__)


class ContextScope(Enum):
    """Hierarchical scopes for context data."""
    GLOBAL = "global"           # System-wide context
    WORKFLOW = "workflow"       # Workflow-specific context
    CONVERSATION = "conversation"  # Conversation-specific context
    TASK = "task"              # Individual task context
    AGENT = "agent"            # Agent-specific context


class ContextAccessLevel(Enum):
    """Access levels for context data."""
    READ_ONLY = "read_only"
    READ_WRITE = "read_write"
    ADMIN = "admin"


class MergeStrategy(Enum):
    """Strategies for merging conflicting context updates."""
    LAST_WRITER_WINS = "last_writer_wins"
    FIRST_WRITER_WINS = "first_writer_wins"
    MERGE_DEEP = "merge_deep"
    MERGE_SHALLOW = "merge_shallow"
    REQUIRE_MANUAL = "require_manual"


@dataclass
class ContextVersion:
    """Version information for context data."""
    version: int
    created_at: datetime
    created_by: str
    agent_type: AgentType
    change_summary: str
    parent_version: Optional[int] = None
    is_merged: bool = False
    merge_sources: List[int] = field(default_factory=list)


@dataclass
class ContextMetadata:
    """Metadata for context entries."""
    key: str
    scope: ContextScope
    created_at: datetime = field(default_factory=datetime.now)
    updated_at: datetime = field(default_factory=datetime.now)
    created_by: str = ""
    updated_by: str = ""
    access_level: ContextAccessLevel = ContextAccessLevel.READ_WRITE
    tags: Set[str] = field(default_factory=set)
    expires_at: Optional[datetime] = None
    is_persistent: bool = True
    change_count: int = 0
    size_bytes: int = 0


@dataclass
class ContextConflict:
    """Information about context update conflicts."""
    key: str
    scope: ContextScope
    conflicting_versions: List[ContextVersion]
    current_value: Any
    proposed_values: List[Any]
    merge_strategy: MergeStrategy
    requires_resolution: bool = True
    created_at: datetime = field(default_factory=datetime.now)
    resolution_deadline: Optional[datetime] = None


class SharedContext:
    """
    Thread-safe container for shared context data with versioning.
    
    Provides efficient storage and retrieval of context data with support for:
    - Version control and history tracking
    - Conflict detection and resolution
    - Change notifications
    - Automatic cleanup of expired data
    """
    
    def __init__(self, context_id: str, scope: ContextScope):
        self.context_id = context_id
        self.scope = scope
        
        # Data storage
        self._data: Dict[str, Any] = {}
        self._metadata: Dict[str, ContextMetadata] = {}
        self._versions: Dict[str, List[ContextVersion]] = defaultdict(list)
        self._locks: Dict[str, asyncio.Lock] = defaultdict(asyncio.Lock)
        
        # Change tracking
        self._change_listeners: List[Callable] = []
        self._version_counter = 0
        self._last_modified = datetime.now()
        
        logger.debug("SharedContext created: %s (%s)", context_id, scope.value)
    
    async def get(self, key: str, default: Any = None) -> Any:
        """Get a value from the context."""
        async with self._locks[key]:
            return self._data.get(key, default)
    
    async def set(
        self,
        key: str,
        value: Any,
        agent_id: str,
        agent_type: AgentType,
        change_summary: str = "",
        access_level: ContextAccessLevel = ContextAccessLevel.READ_WRITE,
        expires_at: Optional[datetime] = None,
        tags: Set[str] = None
    ) -> int:
        """
        Set a value in the context with version tracking.
        
        Args:
            key: Context key
            value: Value to store
            agent_id: ID of the agent making the change
            agent_type: Type of the agent
            change_summary: Description of the change
            access_level: Access level for the data
            expires_at: Optional expiration time
            tags: Optional tags for categorization
            
        Returns:
            New version number
        """
        async with self._locks[key]:
            self._version_counter += 1
            current_time = datetime.now()
            
            # Create version record
            version = ContextVersion(
                version=self._version_counter,
                created_at=current_time,
                created_by=agent_id,
                agent_type=agent_type,
                change_summary=change_summary or f"Updated {key}",
                parent_version=self._get_current_version(key)
            )
            
            # Update data
            old_value = self._data.get(key)
            self._data[key] = value
            
            # Update or create metadata
            if key not in self._metadata:
                self._metadata[key] = ContextMetadata(
                    key=key,
                    scope=self.scope,
                    created_by=agent_id,
                    access_level=access_level,
                    tags=tags or set(),
                    expires_at=expires_at
                )
            else:
                metadata = self._metadata[key]
                metadata.updated_at = current_time
                metadata.updated_by = agent_id
                metadata.change_count += 1
                if tags:
                    metadata.tags.update(tags)
                if expires_at:
                    metadata.expires_at = expires_at
            
            # Calculate size
            try:
                self._metadata[key].size_bytes = len(json.dumps(value, default=str))
            except (TypeError, ValueError):
                self._metadata[key].size_bytes = len(str(value))
            
            # Store version
            self._versions[key].append(version)
            self._last_modified = current_time
            
            # Notify listeners
            await self._notify_change(key, old_value, value, version)
            
            logger.debug(
                "Context updated: %s[%s] = %s (v%d) by %s",
                self.context_id,
                key,
                str(value)[:100],
                version.version,
                agent_id
            )
            
            return version.version
    
    async def update(
        self,
        updates: Dict[str, Any],
        agent_id: str,
        agent_type: AgentType,
        change_summary: str = "",
        merge_strategy: MergeStrategy = MergeStrategy.LAST_WRITER_WINS
    ) -> Dict[str, int]:
        """
        Update multiple keys atomically.
        
        Args:
            updates: Dictionary of key-value pairs to update
            agent_id: ID of the agent making changes
            agent_type: Type of the agent
            change_summary: Description of the changes
            merge_strategy: Strategy for handling conflicts
            
        Returns:
            Dictionary mapping keys to their new version numbers
        """
        results = {}
        
        # Sort keys to prevent deadlocks
        sorted_keys = sorted(updates.keys())
        
        # Acquire locks in order
        async with asyncio.gather(*[self._locks[key] for key in sorted_keys]):
            for key, value in updates.items():
                version = await self.set(
                    key, value, agent_id, agent_type, 
                    change_summary or f"Batch update: {key}",
                    ContextAccessLevel.READ_WRITE
                )
                results[key] = version
        
        return results
    
    async def delete(self, key: str, agent_id: str, agent_type: AgentType) -> bool:
        """Delete a key from the context."""
        async with self._locks[key]:
            if key not in self._data:
                return False
            
            old_value = self._data[key]
            del self._data[key]
            
            # Create deletion version record
            self._version_counter += 1
            version = ContextVersion(
                version=self._version_counter,
                created_at=datetime.now(),
                created_by=agent_id,
                agent_type=agent_type,
                change_summary=f"Deleted {key}",
                parent_version=self._get_current_version(key)
            )
            
            self._versions[key].append(version)
            
            # Update metadata
            if key in self._metadata:
                self._metadata[key].updated_at = datetime.now()
                self._metadata[key].updated_by = agent_id
                self._metadata[key].change_count += 1
            
            # Notify listeners
            await self._notify_change(key, old_value, None, version)
            
            logger.debug(
                "Context deleted: %s[%s] (v%d) by %s",
                self.context_id,
                key,
                version.version,
                agent_id
            )
            
            return True
    
    async def get_metadata(self, key: str) -> Optional[ContextMetadata]:
        """Get metadata for a context key."""
        return self._metadata.get(key)
    
    async def get_version_history(self, key: str) -> List[ContextVersion]:
        """Get version history for a context key."""
        return self._versions.get(key, [])
    
    async def get_version(self, key: str, version: int) -> Optional[Any]:
        """Get a specific version of a context value."""
        # For now, we only store current values
        # In a full implementation, this would retrieve historical values
        if key in self._data and version == self._get_current_version(key):
            return self._data[key]
        return None
    
    def _get_current_version(self, key: str) -> Optional[int]:
        """Get the current version number for a key."""
        versions = self._versions.get(key, [])
        return versions[-1].version if versions else None
    
    async def _notify_change(
        self,
        key: str,
        old_value: Any,
        new_value: Any,
        version: ContextVersion
    ):
        """Notify change listeners of context updates."""
        for listener in self._change_listeners:
            try:
                await listener(self.context_id, key, old_value, new_value, version)
            except Exception as e:
                logger.error(
                    "Error notifying context change listener: %s",
                    str(e)
                )
    
    def add_change_listener(self, listener: Callable):
        """Add a change listener callback."""
        self._change_listeners.append(listener)
    
    def remove_change_listener(self, listener: Callable):
        """Remove a change listener callback."""
        if listener in self._change_listeners:
            self._change_listeners.remove(listener)
    
    async def cleanup_expired(self) -> int:
        """Remove expired context entries."""
        current_time = datetime.now()
        expired_keys = []
        
        for key, metadata in self._metadata.items():
            if metadata.expires_at and metadata.expires_at < current_time:
                expired_keys.append(key)
        
        for key in expired_keys:
            await self.delete(key, "system", AgentType.SUPERVISOR)
        
        logger.debug(
            "Cleaned up %d expired context entries from %s",
            len(expired_keys),
            self.context_id
        )
        
        return len(expired_keys)
    
    def get_stats(self) -> Dict[str, Any]:
        """Get statistics about the context."""
        total_size = sum(m.size_bytes for m in self._metadata.values())
        
        return {
            "context_id": self.context_id,
            "scope": self.scope.value,
            "key_count": len(self._data),
            "total_size_bytes": total_size,
            "version_count": self._version_counter,
            "last_modified": self._last_modified,
            "change_listeners": len(self._change_listeners)
        }


class ContextManager:
    """
    Central manager for all shared contexts in the multi-agent system.
    
    Provides comprehensive context management including:
    - Hierarchical context scoping
    - Context lifecycle management
    - Cross-context operations
    - Conflict detection and resolution
    - Performance monitoring and optimization
    """
    
    def __init__(self, enable_persistence: bool = False):
        self.enable_persistence = enable_persistence
        
        # Context storage
        self._contexts: Dict[str, SharedContext] = {}
        self._context_hierarchy: Dict[ContextScope, Set[str]] = defaultdict(set)
        
        # Conflict management
        self._conflicts: List[ContextConflict] = []
        self._conflict_resolvers: Dict[MergeStrategy, Callable] = {
            MergeStrategy.LAST_WRITER_WINS: self._resolve_last_writer_wins,
            MergeStrategy.FIRST_WRITER_WINS: self._resolve_first_writer_wins,
            MergeStrategy.MERGE_DEEP: self._resolve_merge_deep,
            MergeStrategy.MERGE_SHALLOW: self._resolve_merge_shallow
        }
        
        # Performance and cleanup
        self._cleanup_task: Optional[asyncio.Task] = None
        self._cleanup_interval = 300  # 5 minutes
        self._max_context_age = timedelta(hours=24)
        
        # Statistics
        self._operation_count = 0
        self._conflict_count = 0
        
        logger.info("ContextManager initialized")
    
    async def start(self):
        """Start the context manager and cleanup tasks."""
        if self._cleanup_task is None:
            self._cleanup_task = asyncio.create_task(self._cleanup_loop())
            logger.info("ContextManager started")
    
    async def stop(self):
        """Stop the context manager and cleanup tasks."""
        if self._cleanup_task:
            self._cleanup_task.cancel()
            try:
                await self._cleanup_task
            except asyncio.CancelledError:
                pass
            self._cleanup_task = None
            logger.info("ContextManager stopped")
    
    async def get_context(
        self,
        context_id: str,
        scope: ContextScope,
        create_if_missing: bool = True
    ) -> Optional[SharedContext]:
        """
        Get or create a shared context.
        
        Args:
            context_id: Unique identifier for the context
            scope: Scope level for the context
            create_if_missing: Whether to create context if it doesn't exist
            
        Returns:
            SharedContext instance or None if not found and not created
        """
        full_id = f"{scope.value}:{context_id}"
        
        if full_id not in self._contexts:
            if create_if_missing:
                context = SharedContext(context_id, scope)
                self._contexts[full_id] = context
                self._context_hierarchy[scope].add(full_id)
                
                logger.debug(
                    "Created new context: %s (%s)",
                    context_id,
                    scope.value
                )
            else:
                return None
        
        return self._contexts[full_id]
    
    async def delete_context(self, context_id: str, scope: ContextScope) -> bool:
        """Delete a shared context."""
        full_id = f"{scope.value}:{context_id}"
        
        if full_id in self._contexts:
            del self._contexts[full_id]
            self._context_hierarchy[scope].discard(full_id)
            
            logger.info("Deleted context: %s (%s)", context_id, scope.value)
            return True
        
        return False
    
    async def broadcast_update(
        self,
        update: ContextUpdate,
        target_scopes: List[ContextScope] = None
    ) -> List[str]:
        """
        Broadcast a context update to multiple contexts.
        
        Args:
            update: Context update message
            target_scopes: List of scopes to update (None = all)
            
        Returns:
            List of context IDs that were updated
        """
        updated_contexts = []
        scopes = target_scopes or list(ContextScope)
        
        for scope in scopes:
            for context_full_id in self._context_hierarchy[scope]:
                context = self._contexts[context_full_id]
                
                try:
                    if update.update_type == "create" or update.update_type == "update":
                        await context.set(
                            update.context_key,
                            update.context_data,
                            update.sender_id,
                            update.sender_type,
                            f"Broadcast update: {update.subject}"
                        )
                    elif update.update_type == "delete":
                        await context.delete(
                            update.context_key,
                            update.sender_id,
                            update.sender_type
                        )
                    
                    updated_contexts.append(context_full_id)
                    
                except Exception as e:
                    logger.error(
                        "Error broadcasting update to context %s: %s",
                        context_full_id,
                        str(e)
                    )
        
        logger.debug(
            "Broadcast update applied to %d contexts",
            len(updated_contexts)
        )
        
        return updated_contexts
    
    async def detect_conflicts(
        self,
        context_id: str,
        scope: ContextScope,
        key: str
    ) -> Optional[ContextConflict]:
        """
        Detect conflicts in context updates.
        
        This is a simplified implementation. A full implementation would
        track concurrent updates and detect actual conflicts.
        """
        context = await self.get_context(context_id, scope, create_if_missing=False)
        if not context:
            return None
        
        # Get version history
        versions = await context.get_version_history(key)
        if len(versions) < 2:
            return None
        
        # Check for rapid successive updates (potential conflict indicator)
        recent_versions = [v for v in versions if 
                          (datetime.now() - v.created_at).total_seconds() < 60]
        
        if len(recent_versions) > 2:
            return ContextConflict(
                key=key,
                scope=scope,
                conflicting_versions=recent_versions,
                current_value=await context.get(key),
                proposed_values=[],  # Would contain conflicting values
                merge_strategy=MergeStrategy.LAST_WRITER_WINS
            )
        
        return None
    
    async def resolve_conflict(
        self,
        conflict: ContextConflict,
        resolution_strategy: MergeStrategy = None
    ) -> bool:
        """
        Resolve a context conflict using the specified strategy.
        
        Args:
            conflict: Conflict to resolve
            resolution_strategy: Strategy to use (overrides conflict's strategy)
            
        Returns:
            True if conflict was resolved successfully
        """
        strategy = resolution_strategy or conflict.merge_strategy
        
        if strategy not in self._conflict_resolvers:
            logger.error("Unknown conflict resolution strategy: %s", strategy.value)
            return False
        
        try:
            resolver = self._conflict_resolvers[strategy]
            await resolver(conflict)
            
            # Remove from conflicts list
            if conflict in self._conflicts:
                self._conflicts.remove(conflict)
            
            self._conflict_count += 1
            
            logger.info(
                "Resolved conflict for %s using strategy %s",
                conflict.key,
                strategy.value
            )
            
            return True
            
        except Exception as e:
            logger.error(
                "Error resolving conflict for %s: %s",
                conflict.key,
                str(e)
            )
            return False
    
    async def _resolve_last_writer_wins(self, conflict: ContextConflict):
        """Resolve conflict by keeping the last written value."""
        # Current value is already the last written value
        pass
    
    async def _resolve_first_writer_wins(self, conflict: ContextConflict):
        """Resolve conflict by keeping the first written value."""
        # Would need to restore the first value
        # This is a simplified implementation
        pass
    
    async def _resolve_merge_deep(self, conflict: ContextConflict):
        """Resolve conflict by deep merging dictionaries."""
        if not conflict.proposed_values:
            return
        
        # Deep merge implementation would go here
        # This is a simplified placeholder
        pass
    
    async def _resolve_merge_shallow(self, conflict: ContextConflict):
        """Resolve conflict by shallow merging dictionaries."""
        if not conflict.proposed_values:
            return
        
        # Shallow merge implementation would go here
        # This is a simplified placeholder
        pass
    
    async def _cleanup_loop(self):
        """Background task for cleaning up expired contexts and data."""
        logger.info("Context cleanup loop started")
        
        while True:
            try:
                await asyncio.sleep(self._cleanup_interval)
                
                # Clean up expired data in all contexts
                total_cleaned = 0
                for context in self._contexts.values():
                    cleaned = await context.cleanup_expired()
                    total_cleaned += cleaned
                
                # Clean up old conflicts
                current_time = datetime.now()
                expired_conflicts = [
                    c for c in self._conflicts 
                    if c.resolution_deadline and c.resolution_deadline < current_time
                ]
                
                for conflict in expired_conflicts:
                    await self.resolve_conflict(conflict, MergeStrategy.LAST_WRITER_WINS)
                
                if total_cleaned > 0 or expired_conflicts:
                    logger.info(
                        "Cleanup completed: %d expired entries, %d expired conflicts",
                        total_cleaned,
                        len(expired_conflicts)
                    )
                
            except asyncio.CancelledError:
                break
            except Exception as e:
                logger.error("Error in context cleanup loop: %s", str(e))
        
        logger.info("Context cleanup loop stopped")
    
    def get_stats(self) -> Dict[str, Any]:
        """Get comprehensive context manager statistics."""
        context_stats = {}
        total_keys = 0
        total_size = 0
        
        for scope, context_ids in self._context_hierarchy.items():
            scope_stats = {
                "context_count": len(context_ids),
                "contexts": {}
            }
            
            for context_id in context_ids:
                if context_id in self._contexts:
                    stats = self._contexts[context_id].get_stats()
                    scope_stats["contexts"][context_id] = stats
                    total_keys += stats["key_count"]
                    total_size += stats["total_size_bytes"]
            
            context_stats[scope.value] = scope_stats
        
        return {
            "total_contexts": len(self._contexts),
            "total_keys": total_keys,
            "total_size_bytes": total_size,
            "operation_count": self._operation_count,
            "conflict_count": self._conflict_count,
            "active_conflicts": len(self._conflicts),
            "contexts_by_scope": context_stats,
            "cleanup_interval_seconds": self._cleanup_interval
        }
