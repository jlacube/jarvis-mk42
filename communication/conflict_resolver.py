# communication/conflict_resolver.py
"""
Conflict Resolution System for Multi-Agent Communication

This module provides sophisticated conflict resolution capabilities for handling
competing agent recommendations, conflicting context updates, and resource
contention in multi-agent systems. Features include:
- Multiple resolution strategies (voting, priority-based, consensus)
- Agent expertise weighting and trust scoring
- Dynamic strategy selection based on conflict type
- Resolution history tracking and learning
- Escalation mechanisms for unresolved conflicts
"""

import asyncio
import json
import logging
from datetime import datetime, timedelta
from typing import Any, Dict, List, Optional, Set, Union, Callable, Tuple
from dataclasses import dataclass, field
from enum import Enum
from collections import defaultdict, Counter
import statistics

from .protocols import AgentType, MessageType
from .context_manager import ContextConflict, MergeStrategy
from utils.logging_config import get_logger
from utils.exceptions import CoordinationError

logger = get_logger(__name__)


class ConflictType(Enum):
    """Types of conflicts that can occur in multi-agent systems."""
    CONTEXT_UPDATE = "context_update"      # Conflicting context modifications
    TASK_ASSIGNMENT = "task_assignment"    # Multiple agents claiming same task
    RESOURCE_ACCESS = "resource_access"    # Competing resource requests
    STRATEGY_CHOICE = "strategy_choice"    # Different recommended approaches
    PRIORITY_CONFLICT = "priority_conflict"  # Conflicting priority assignments
    DATA_INCONSISTENCY = "data_inconsistency"  # Inconsistent data between agents
    WORKFLOW_ROUTING = "workflow_routing"    # Different workflow paths


class ResolutionStrategy(Enum):
    """Strategies for resolving conflicts."""
    MAJORITY_VOTE = "majority_vote"        # Simple majority voting
    WEIGHTED_VOTE = "weighted_vote"        # Vote weighted by agent expertise
    PRIORITY_BASED = "priority_based"      # Based on agent priority/role
    CONSENSUS_BUILDING = "consensus_building"  # Iterative consensus process
    EXPERT_OVERRIDE = "expert_override"    # Defer to most expert agent
    RANDOM_SELECTION = "random_selection"  # Random choice (last resort)
    ESCALATION = "escalation"              # Escalate to supervisor
    MERGE_COMPATIBLE = "merge_compatible"  # Merge non-conflicting parts
    TEMPORAL_ORDERING = "temporal_ordering"  # First-come-first-served
    COST_OPTIMIZATION = "cost_optimization"  # Choose lowest cost option


class ConflictSeverity(Enum):
    """Severity levels for conflicts."""
    LOW = "low"           # Minor conflicts, auto-resolvable
    MEDIUM = "medium"     # Moderate conflicts, require strategy
    HIGH = "high"         # Serious conflicts, may need escalation
    CRITICAL = "critical"  # System-threatening conflicts


@dataclass
class AgentPosition:
    """Represents an agent's position in a conflict."""
    agent_id: str
    agent_type: AgentType
    position_data: Any
    confidence: float = 0.5  # 0.0 to 1.0
    reasoning: str = ""
    supporting_evidence: List[str] = field(default_factory=list)
    timestamp: datetime = field(default_factory=datetime.now)
    vote_weight: float = 1.0
    expertise_score: float = 0.5  # 0.0 to 1.0


@dataclass
class ConflictContext:
    """Context information for a conflict."""
    conflict_id: str
    conflict_type: ConflictType
    severity: ConflictSeverity
    description: str
    affected_resources: List[str] = field(default_factory=list)
    stakeholder_agents: List[str] = field(default_factory=list)
    deadline: Optional[datetime] = None
    max_resolution_time: timedelta = field(default_factory=lambda: timedelta(minutes=5))
    escalation_threshold: int = 3  # Number of failed resolution attempts
    metadata: Dict[str, Any] = field(default_factory=dict)


@dataclass
class Conflict:
    """Represents a conflict between agents."""
    context: ConflictContext
    positions: List[AgentPosition] = field(default_factory=list)
    created_at: datetime = field(default_factory=datetime.now)
    updated_at: datetime = field(default_factory=datetime.now)
    resolution_attempts: int = 0
    resolution_strategy: Optional[ResolutionStrategy] = None
    resolved_at: Optional[datetime] = None
    resolution_data: Optional[Any] = None
    resolution_confidence: float = 0.0
    resolver_id: Optional[str] = None
    
    def add_position(self, position: AgentPosition):
        """Add an agent's position to the conflict."""
        # Remove existing position from same agent
        self.positions = [p for p in self.positions if p.agent_id != position.agent_id]
        self.positions.append(position)
        self.updated_at = datetime.now()
    
    def get_position(self, agent_id: str) -> Optional[AgentPosition]:
        """Get a specific agent's position."""
        for position in self.positions:
            if position.agent_id == agent_id:
                return position
        return None
    
    def get_positions_by_type(self, agent_type: AgentType) -> List[AgentPosition]:
        """Get all positions from agents of a specific type."""
        return [p for p in self.positions if p.agent_type == agent_type]
    
    def is_expired(self) -> bool:
        """Check if the conflict has exceeded its resolution deadline."""
        if not self.context.deadline:
            return False
        return datetime.now() > self.context.deadline
    
    def time_remaining(self) -> Optional[timedelta]:
        """Get remaining time before deadline."""
        if not self.context.deadline:
            return None
        remaining = self.context.deadline - datetime.now()
        return remaining if remaining.total_seconds() > 0 else timedelta(0)


class ConflictResolver:
    """
    Main conflict resolution engine for multi-agent systems.
    
    Provides comprehensive conflict resolution including:
    - Automatic conflict detection and classification
    - Dynamic strategy selection based on conflict characteristics
    - Agent expertise evaluation and weighting
    - Resolution execution and validation
    - Learning from resolution outcomes
    """
    
    def __init__(self):
        # Active conflicts
        self._active_conflicts: Dict[str, Conflict] = {}
        self._resolved_conflicts: List[Conflict] = []
        
        # Agent expertise tracking
        self._agent_expertise: Dict[str, Dict[str, float]] = defaultdict(lambda: defaultdict(float))
        self._agent_trust_scores: Dict[str, float] = defaultdict(lambda: 0.5)
        self._agent_resolution_history: Dict[str, List[bool]] = defaultdict(list)
        
        # Strategy effectiveness tracking
        self._strategy_success_rates: Dict[ResolutionStrategy, List[bool]] = defaultdict(list)
        self._strategy_by_conflict_type: Dict[ConflictType, Dict[ResolutionStrategy, List[bool]]] = \
            defaultdict(lambda: defaultdict(list))
        
        # Resolution handlers
        self._resolution_handlers: Dict[ResolutionStrategy, Callable] = {
            ResolutionStrategy.MAJORITY_VOTE: self._resolve_majority_vote,
            ResolutionStrategy.WEIGHTED_VOTE: self._resolve_weighted_vote,
            ResolutionStrategy.PRIORITY_BASED: self._resolve_priority_based,
            ResolutionStrategy.CONSENSUS_BUILDING: self._resolve_consensus_building,
            ResolutionStrategy.EXPERT_OVERRIDE: self._resolve_expert_override,
            ResolutionStrategy.RANDOM_SELECTION: self._resolve_random_selection,
            ResolutionStrategy.MERGE_COMPATIBLE: self._resolve_merge_compatible,
            ResolutionStrategy.TEMPORAL_ORDERING: self._resolve_temporal_ordering,
            ResolutionStrategy.COST_OPTIMIZATION: self._resolve_cost_optimization
        }
        
        # Configuration
        self._min_positions_for_resolution = 2
        self._max_resolution_attempts = 3
        self._escalation_timeout = timedelta(minutes=10)
        
        # Statistics
        self._total_conflicts = 0
        self._successful_resolutions = 0
        self._escalated_conflicts = 0
        
        logger.info("ConflictResolver initialized")
    
    async def create_conflict(
        self,
        conflict_id: str,
        conflict_type: ConflictType,
        description: str,
        severity: ConflictSeverity = ConflictSeverity.MEDIUM,
        affected_resources: List[str] = None,
        stakeholder_agents: List[str] = None,
        deadline: Optional[datetime] = None,
        metadata: Dict[str, Any] = None
    ) -> Conflict:
        """
        Create a new conflict for resolution.
        
        Args:
            conflict_id: Unique identifier for the conflict
            conflict_type: Type of conflict
            description: Human-readable description
            severity: Severity level
            affected_resources: List of affected resources
            stakeholder_agents: List of stakeholder agent IDs
            deadline: Optional resolution deadline
            metadata: Additional context data
            
        Returns:
            Created Conflict instance
        """
        if conflict_id in self._active_conflicts:
            raise CoordinationError(f"Conflict {conflict_id} already exists")
        
        # Set default deadline based on severity
        if not deadline:
            deadline_minutes = {
                ConflictSeverity.LOW: 2,
                ConflictSeverity.MEDIUM: 5,
                ConflictSeverity.HIGH: 10,
                ConflictSeverity.CRITICAL: 30
            }.get(severity, 5)
            deadline = datetime.now() + timedelta(minutes=deadline_minutes)
        
        context = ConflictContext(
            conflict_id=conflict_id,
            conflict_type=conflict_type,
            severity=severity,
            description=description,
            affected_resources=affected_resources or [],
            stakeholder_agents=stakeholder_agents or [],
            deadline=deadline,
            metadata=metadata or {}
        )
        
        conflict = Conflict(context=context)
        self._active_conflicts[conflict_id] = conflict
        self._total_conflicts += 1
        
        logger.info(
            "Created conflict: %s (%s, %s) - deadline: %s",
            conflict_id,
            conflict_type.value,
            severity.value,
            deadline.strftime("%H:%M:%S") if deadline else "None"
        )
        
        return conflict
    
    async def add_position(
        self,
        conflict_id: str,
        agent_id: str,
        agent_type: AgentType,
        position_data: Any,
        confidence: float = 0.5,
        reasoning: str = "",
        supporting_evidence: List[str] = None
    ) -> bool:
        """
        Add an agent's position to a conflict.
        
        Args:
            conflict_id: ID of the conflict
            agent_id: ID of the agent
            agent_type: Type of the agent
            position_data: The agent's proposed position/solution
            confidence: Confidence level (0.0 to 1.0)
            reasoning: Explanation for the position
            supporting_evidence: Supporting evidence/references
            
        Returns:
            True if position was added successfully
        """
        if conflict_id not in self._active_conflicts:
            logger.error("Conflict %s not found", conflict_id)
            return False
        
        conflict = self._active_conflicts[conflict_id]
        
        # Calculate expertise score for this agent/conflict type
        expertise_score = self._calculate_expertise_score(
            agent_id,
            agent_type,
            conflict.context.conflict_type
        )
        
        # Calculate vote weight
        trust_score = self._agent_trust_scores[agent_id]
        vote_weight = (expertise_score + trust_score + confidence) / 3.0
        
        position = AgentPosition(
            agent_id=agent_id,
            agent_type=agent_type,
            position_data=position_data,
            confidence=confidence,
            reasoning=reasoning,
            supporting_evidence=supporting_evidence or [],
            vote_weight=vote_weight,
            expertise_score=expertise_score
        )
        
        conflict.add_position(position)
        
        logger.debug(
            "Added position to conflict %s from agent %s (weight: %.2f)",
            conflict_id,
            agent_id,
            vote_weight
        )
        
        # Auto-resolve if we have enough positions
        if len(conflict.positions) >= self._min_positions_for_resolution:
            await self._attempt_auto_resolution(conflict)
        
        return True
    
    async def resolve_conflict(
        self,
        conflict_id: str,
        strategy: Optional[ResolutionStrategy] = None,
        resolver_id: str = "system"
    ) -> Optional[Any]:
        """
        Resolve a conflict using the specified or optimal strategy.
        
        Args:
            conflict_id: ID of the conflict to resolve
            strategy: Resolution strategy to use (None for auto-select)
            resolver_id: ID of the entity requesting resolution
            
        Returns:
            Resolution data if successful, None otherwise
        """
        if conflict_id not in self._active_conflicts:
            logger.error("Conflict %s not found", conflict_id)
            return None
        
        conflict = self._active_conflicts[conflict_id]
        
        # Check if already resolved
        if conflict.resolved_at:
            logger.warning("Conflict %s already resolved", conflict_id)
            return conflict.resolution_data
        
        # Check for timeout/deadline
        if conflict.is_expired():
            logger.warning("Conflict %s has exceeded deadline", conflict_id)
            return await self._escalate_conflict(conflict, "deadline_exceeded")
        
        # Select strategy if not provided
        if not strategy:
            strategy = await self._select_optimal_strategy(conflict)
        
        conflict.resolution_attempts += 1
        conflict.resolution_strategy = strategy
        conflict.resolver_id = resolver_id
        
        logger.info(
            "Attempting to resolve conflict %s using strategy %s (attempt %d)",
            conflict_id,
            strategy.value,
            conflict.resolution_attempts
        )
        
        try:
            # Execute resolution strategy
            if strategy == ResolutionStrategy.ESCALATION:
                return await self._escalate_conflict(conflict, "strategy_escalation")
            
            if strategy not in self._resolution_handlers:
                logger.error("No handler for resolution strategy: %s", strategy.value)
                return await self._escalate_conflict(conflict, "no_handler")
            
            handler = self._resolution_handlers[strategy]
            resolution_data = await handler(conflict)
            
            if resolution_data is not None:
                # Mark as resolved
                conflict.resolved_at = datetime.now()
                conflict.resolution_data = resolution_data
                conflict.resolution_confidence = self._calculate_resolution_confidence(conflict)
                
                # Move to resolved conflicts
                self._resolved_conflicts.append(conflict)
                del self._active_conflicts[conflict_id]
                
                # Update statistics
                self._successful_resolutions += 1
                self._strategy_success_rates[strategy].append(True)
                self._strategy_by_conflict_type[conflict.context.conflict_type][strategy].append(True)
                
                # Update agent trust scores
                await self._update_agent_scores(conflict, True)
                
                logger.info(
                    "Successfully resolved conflict %s with confidence %.2f",
                    conflict_id,
                    conflict.resolution_confidence
                )
                
                return resolution_data
            
            else:
                # Resolution failed
                self._strategy_success_rates[strategy].append(False)
                self._strategy_by_conflict_type[conflict.context.conflict_type][strategy].append(False)
                
                # Try escalation if max attempts reached
                if conflict.resolution_attempts >= self._max_resolution_attempts:
                    return await self._escalate_conflict(conflict, "max_attempts_reached")
                
                logger.warning(
                    "Failed to resolve conflict %s using strategy %s",
                    conflict_id,
                    strategy.value
                )
                
                return None
        
        except Exception as e:
            logger.error(
                "Error resolving conflict %s: %s",
                conflict_id,
                str(e)
            )
            
            self._strategy_success_rates[strategy].append(False)
            return await self._escalate_conflict(conflict, f"error: {str(e)}")
    
    async def _attempt_auto_resolution(self, conflict: Conflict):
        """Attempt automatic resolution when enough positions are available."""
        if len(conflict.positions) < self._min_positions_for_resolution:
            return
        
        # Only auto-resolve low severity conflicts
        if conflict.context.severity in [ConflictSeverity.LOW, ConflictSeverity.MEDIUM]:
            strategy = await self._select_optimal_strategy(conflict)
            await self.resolve_conflict(conflict.context.conflict_id, strategy, "auto")
    
    async def _select_optimal_strategy(self, conflict: Conflict) -> ResolutionStrategy:
        """
        Select the optimal resolution strategy based on conflict characteristics.
        
        Uses machine learning-like approach to select strategy based on:
        - Conflict type and severity
        - Number and types of agent positions
        - Historical success rates
        - Time constraints
        """
        conflict_type = conflict.context.conflict_type
        severity = conflict.context.severity
        num_positions = len(conflict.positions)
        time_remaining = conflict.time_remaining()
        
        # Get strategy success rates for this conflict type
        type_strategies = self._strategy_by_conflict_type[conflict_type]
        
        # Calculate scores for each strategy
        strategy_scores = {}
        
        for strategy in ResolutionStrategy:
            if strategy == ResolutionStrategy.ESCALATION:
                continue  # Skip escalation in normal selection
            
            score = 0.0
            
            # Historical success rate (40% weight)
            if strategy in type_strategies and type_strategies[strategy]:
                success_rate = sum(type_strategies[strategy]) / len(type_strategies[strategy])
                score += success_rate * 0.4
            else:
                # Default scores for strategies without history
                default_scores = {
                    ResolutionStrategy.MAJORITY_VOTE: 0.7,
                    ResolutionStrategy.WEIGHTED_VOTE: 0.8,
                    ResolutionStrategy.PRIORITY_BASED: 0.6,
                    ResolutionStrategy.CONSENSUS_BUILDING: 0.9,
                    ResolutionStrategy.EXPERT_OVERRIDE: 0.8,
                    ResolutionStrategy.RANDOM_SELECTION: 0.3,
                    ResolutionStrategy.MERGE_COMPATIBLE: 0.7,
                    ResolutionStrategy.TEMPORAL_ORDERING: 0.5,
                    ResolutionStrategy.COST_OPTIMIZATION: 0.6
                }
                score += default_scores.get(strategy, 0.5) * 0.4
            
            # Appropriateness for conflict type (30% weight)
            type_appropriateness = {
                ConflictType.CONTEXT_UPDATE: {
                    ResolutionStrategy.MERGE_COMPATIBLE: 0.9,
                    ResolutionStrategy.TEMPORAL_ORDERING: 0.8,
                    ResolutionStrategy.WEIGHTED_VOTE: 0.7
                },
                ConflictType.TASK_ASSIGNMENT: {
                    ResolutionStrategy.PRIORITY_BASED: 0.9,
                    ResolutionStrategy.EXPERT_OVERRIDE: 0.8,
                    ResolutionStrategy.WEIGHTED_VOTE: 0.7
                },
                ConflictType.STRATEGY_CHOICE: {
                    ResolutionStrategy.CONSENSUS_BUILDING: 0.9,
                    ResolutionStrategy.WEIGHTED_VOTE: 0.8,
                    ResolutionStrategy.EXPERT_OVERRIDE: 0.7
                }
            }
            
            if conflict_type in type_appropriateness:
                appropriateness = type_appropriateness[conflict_type].get(strategy, 0.5)
            else:
                appropriateness = 0.5
            
            score += appropriateness * 0.3
            
            # Time constraints (20% weight)
            if time_remaining and time_remaining.total_seconds() > 0:
                quick_strategies = {
                    ResolutionStrategy.PRIORITY_BASED: 0.9,
                    ResolutionStrategy.EXPERT_OVERRIDE: 0.8,
                    ResolutionStrategy.MAJORITY_VOTE: 0.7,
                    ResolutionStrategy.RANDOM_SELECTION: 0.9,
                    ResolutionStrategy.TEMPORAL_ORDERING: 0.8
                }
                
                slow_strategies = {
                    ResolutionStrategy.CONSENSUS_BUILDING: 0.3,
                    ResolutionStrategy.MERGE_COMPATIBLE: 0.5
                }
                
                if time_remaining.total_seconds() < 60:  # Less than 1 minute
                    time_factor = quick_strategies.get(strategy, 0.5)
                else:
                    time_factor = slow_strategies.get(strategy, 0.7)
                
                score += time_factor * 0.2
            else:
                score += 0.5 * 0.2
            
            # Number of positions factor (10% weight)
            if num_positions >= 3:
                vote_strategies = [ResolutionStrategy.MAJORITY_VOTE, ResolutionStrategy.WEIGHTED_VOTE]
                if strategy in vote_strategies:
                    score += 0.8 * 0.1
                else:
                    score += 0.5 * 0.1
            else:
                single_strategies = [ResolutionStrategy.EXPERT_OVERRIDE, ResolutionStrategy.PRIORITY_BASED]
                if strategy in single_strategies:
                    score += 0.8 * 0.1
                else:
                    score += 0.5 * 0.1
            
            strategy_scores[strategy] = score
        
        # Select strategy with highest score
        best_strategy = max(strategy_scores.items(), key=lambda x: x[1])[0]
        
        logger.debug(
            "Selected strategy %s for conflict %s (score: %.2f)",
            best_strategy.value,
            conflict.context.conflict_id,
            strategy_scores[best_strategy]
        )
        
        return best_strategy
    
    async def _resolve_majority_vote(self, conflict: Conflict) -> Any:
        """Resolve conflict using simple majority voting."""
        if len(conflict.positions) < 2:
            return None
        
        # Group positions by data
        position_groups = defaultdict(list)
        for position in conflict.positions:
            # Use JSON serialization for grouping
            try:
                key = json.dumps(position.position_data, sort_keys=True, default=str)
            except (TypeError, ValueError):
                key = str(position.position_data)
            position_groups[key].append(position)
        
        # Find majority
        majority_threshold = len(conflict.positions) / 2
        for key, positions in position_groups.items():
            if len(positions) > majority_threshold:
                return positions[0].position_data
        
        # No majority found
        return None
    
    async def _resolve_weighted_vote(self, conflict: Conflict) -> Any:
        """Resolve conflict using weighted voting based on agent expertise."""
        if len(conflict.positions) < 2:
            return None
        
        # Group positions and calculate weighted votes
        position_groups = defaultdict(float)
        position_data_map = {}
        
        for position in conflict.positions:
            try:
                key = json.dumps(position.position_data, sort_keys=True, default=str)
            except (TypeError, ValueError):
                key = str(position.position_data)
            
            position_groups[key] += position.vote_weight
            position_data_map[key] = position.position_data
        
        # Find position with highest weighted vote
        if position_groups:
            winning_key = max(position_groups.items(), key=lambda x: x[1])[0]
            return position_data_map[winning_key]
        
        return None
    
    async def _resolve_priority_based(self, conflict: Conflict) -> Any:
        """Resolve conflict based on agent priority/type hierarchy."""
        if not conflict.positions:
            return None
        
        # Agent type priority order (higher priority first)
        type_priority = {
            AgentType.SUPERVISOR: 4,
            AgentType.REASONING: 3,
            AgentType.CODING: 2,
            AgentType.RESEARCH: 1
        }
        
        # Sort by priority then by confidence
        sorted_positions = sorted(
            conflict.positions,
            key=lambda p: (type_priority.get(p.agent_type, 0), p.confidence),
            reverse=True
        )
        
        return sorted_positions[0].position_data
    
    async def _resolve_consensus_building(self, conflict: Conflict) -> Any:
        """Resolve conflict through iterative consensus building."""
        # This is a simplified implementation
        # In practice, this would involve multiple rounds of agent communication
        
        if len(conflict.positions) < 2:
            return None
        
        # For now, find position with highest average of confidence and vote weight
        best_position = max(
            conflict.positions,
            key=lambda p: (p.confidence + p.vote_weight) / 2
        )
        
        return best_position.position_data
    
    async def _resolve_expert_override(self, conflict: Conflict) -> Any:
        """Resolve conflict by deferring to the most expert agent."""
        if not conflict.positions:
            return None
        
        # Find position with highest expertise score
        expert_position = max(conflict.positions, key=lambda p: p.expertise_score)
        return expert_position.position_data
    
    async def _resolve_random_selection(self, conflict: Conflict) -> Any:
        """Resolve conflict by random selection (last resort)."""
        if not conflict.positions:
            return None
        
        import random
        selected_position = random.choice(conflict.positions)
        return selected_position.position_data
    
    async def _resolve_merge_compatible(self, conflict: Conflict) -> Any:
        """Resolve conflict by merging compatible positions."""
        if not conflict.positions:
            return None
        
        # Simple merge for dictionary-like data
        merged_data = {}
        
        for position in conflict.positions:
            if isinstance(position.position_data, dict):
                # Weight the contribution by vote weight
                for key, value in position.position_data.items():
                    if key not in merged_data:
                        merged_data[key] = value
                    # For conflicting keys, use weighted average for numeric values
                    elif isinstance(value, (int, float)) and isinstance(merged_data[key], (int, float)):
                        # Simple average - could be improved with actual weighting
                        merged_data[key] = (merged_data[key] + value) / 2
        
        return merged_data if merged_data else conflict.positions[0].position_data
    
    async def _resolve_temporal_ordering(self, conflict: Conflict) -> Any:
        """Resolve conflict using temporal ordering (first-come-first-served)."""
        if not conflict.positions:
            return None
        
        # Sort by timestamp
        earliest_position = min(conflict.positions, key=lambda p: p.timestamp)
        return earliest_position.position_data
    
    async def _resolve_cost_optimization(self, conflict: Conflict) -> Any:
        """Resolve conflict by choosing the lowest cost option."""
        if not conflict.positions:
            return None
        
        # Look for cost information in position data or metadata
        positions_with_cost = []
        
        for position in conflict.positions:
            cost = None
            
            if isinstance(position.position_data, dict):
                cost = position.position_data.get('cost') or position.position_data.get('estimated_cost')
            
            if cost is None and hasattr(position, 'metadata'):
                cost = position.metadata.get('cost')
            
            if cost is not None:
                try:
                    positions_with_cost.append((position, float(cost)))
                except (ValueError, TypeError):
                    pass
        
        if positions_with_cost:
            # Select position with lowest cost
            lowest_cost_position = min(positions_with_cost, key=lambda x: x[1])[0]
            return lowest_cost_position.position_data
        
        # Fallback to first position if no cost information
        return conflict.positions[0].position_data
    
    async def _escalate_conflict(self, conflict: Conflict, reason: str) -> Any:
        """Escalate conflict to supervisor or external resolver."""
        logger.warning(
            "Escalating conflict %s: %s",
            conflict.context.conflict_id,
            reason
        )
        
        self._escalated_conflicts += 1
        
        # Mark as resolved with escalation
        conflict.resolved_at = datetime.now()
        conflict.resolution_strategy = ResolutionStrategy.ESCALATION
        conflict.resolution_data = {
            "escalated": True,
            "reason": reason,
            "requires_manual_resolution": True,
            "escalation_time": datetime.now().isoformat()
        }
        
        # Move to resolved conflicts
        self._resolved_conflicts.append(conflict)
        if conflict.context.conflict_id in self._active_conflicts:
            del self._active_conflicts[conflict.context.conflict_id]
        
        return conflict.resolution_data
    
    def _calculate_expertise_score(
        self,
        agent_id: str,
        agent_type: AgentType,
        conflict_type: ConflictType
    ) -> float:
        """Calculate expertise score for an agent on a specific conflict type."""
        # Base score by agent type
        base_scores = {
            AgentType.SUPERVISOR: 0.8,
            AgentType.REASONING: 0.7,
            AgentType.CODING: 0.6,
            AgentType.RESEARCH: 0.6
        }
        
        base_score = base_scores.get(agent_type, 0.5)
        
        # Type-specific expertise
        type_expertise = self._agent_expertise[agent_id].get(conflict_type.value, 0.5)
        
        # Combine scores
        return (base_score + type_expertise) / 2
    
    def _calculate_resolution_confidence(self, conflict: Conflict) -> float:
        """Calculate confidence in the resolution."""
        if not conflict.positions:
            return 0.0
        
        # Factors that increase confidence:
        # - High agreement between positions
        # - High confidence of participating agents
        # - Expertise of agents
        # - Appropriateness of resolution strategy
        
        avg_confidence = statistics.mean(p.confidence for p in conflict.positions)
        avg_expertise = statistics.mean(p.expertise_score for p in conflict.positions)
        
        # Agreement factor (simplified)
        unique_positions = len(set(str(p.position_data) for p in conflict.positions))
        agreement_factor = 1.0 - (unique_positions - 1) / len(conflict.positions)
        
        # Strategy confidence
        strategy_confidence = 0.7  # Default
        if conflict.resolution_strategy in self._strategy_success_rates:
            recent_successes = self._strategy_success_rates[conflict.resolution_strategy][-10:]
            if recent_successes:
                strategy_confidence = sum(recent_successes) / len(recent_successes)
        
        # Weighted combination
        confidence = (
            avg_confidence * 0.3 +
            avg_expertise * 0.2 +
            agreement_factor * 0.3 +
            strategy_confidence * 0.2
        )
        
        return min(1.0, max(0.0, confidence))
    
    async def _update_agent_scores(self, conflict: Conflict, success: bool):
        """Update agent trust and expertise scores based on resolution outcome."""
        for position in conflict.positions:
            agent_id = position.agent_id
            conflict_type = conflict.context.conflict_type.value
            
            # Update resolution history
            self._agent_resolution_history[agent_id].append(success)
            
            # Keep only recent history
            history = self._agent_resolution_history[agent_id]
            if len(history) > 50:
                history = history[-50:]
                self._agent_resolution_history[agent_id] = history
            
            # Update trust score
            if history:
                success_rate = sum(history) / len(history)
                self._agent_trust_scores[agent_id] = success_rate
            
            # Update expertise score for this conflict type
            if success:
                current_expertise = self._agent_expertise[agent_id][conflict_type]
                # Gradually increase expertise (learning rate = 0.1)
                self._agent_expertise[agent_id][conflict_type] = min(1.0, current_expertise + 0.1)
            else:
                # Slightly decrease expertise on failure
                current_expertise = self._agent_expertise[agent_id][conflict_type]
                self._agent_expertise[agent_id][conflict_type] = max(0.0, current_expertise - 0.05)
    
    def get_active_conflicts(self) -> List[Conflict]:
        """Get list of active conflicts."""
        return list(self._active_conflicts.values())
    
    def get_conflict(self, conflict_id: str) -> Optional[Conflict]:
        """Get a specific conflict by ID."""
        return self._active_conflicts.get(conflict_id)
    
    def get_stats(self) -> Dict[str, Any]:
        """Get comprehensive conflict resolution statistics."""
        # Strategy effectiveness
        strategy_stats = {}
        for strategy, results in self._strategy_success_rates.items():
            if results:
                strategy_stats[strategy.value] = {
                    "total_attempts": len(results),
                    "success_rate": sum(results) / len(results),
                    "recent_success_rate": sum(results[-10:]) / len(results[-10:]) if results[-10:] else 0
                }
        
        # Agent performance
        agent_stats = {}
        for agent_id, trust_score in self._agent_trust_scores.items():
            history = self._agent_resolution_history.get(agent_id, [])
            agent_stats[agent_id] = {
                "trust_score": trust_score,
                "total_participations": len(history),
                "expertise": dict(self._agent_expertise[agent_id])
            }
        
        return {
            "total_conflicts": self._total_conflicts,
            "active_conflicts": len(self._active_conflicts),
            "resolved_conflicts": len(self._resolved_conflicts),
            "successful_resolutions": self._successful_resolutions,
            "escalated_conflicts": self._escalated_conflicts,
            "success_rate": self._successful_resolutions / max(1, self._total_conflicts),
            "strategy_effectiveness": strategy_stats,
            "agent_performance": agent_stats,
            "config": {
                "min_positions_for_resolution": self._min_positions_for_resolution,
                "max_resolution_attempts": self._max_resolution_attempts,
                "escalation_timeout_minutes": self._escalation_timeout.total_seconds() / 60
            }
        }
