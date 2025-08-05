# ai/adaptive_learning.py
"""
Adaptive Learning System for Phase 2B.4
=======================================

Advanced adaptive learning capabilities including:
- Experience replay and memory consolidation
- Incremental learning and knowledge updates
- Personalization and user preference adaptation
- Performance optimization through reinforcement learning
- Meta-learning and learning-to-learn capabilities

Enables continuous improvement and personalization of AI capabilities.
"""

import asyncio
import logging
import pickle
import json
from abc import ABC, abstractmethod
from datetime import datetime, timedelta
from typing import Dict, List, Optional, Any, Union, Tuple, Callable
from dataclasses import dataclass, field
from enum import Enum
import numpy as np  
from pathlib import Path
import sqlite3
from collections import defaultdict, deque
import hashlib

from .config import get_settings

logger = logging.getLogger(__name__)
settings = get_settings()


class LearningType(Enum):
    """Types of learning supported"""
    SUPERVISED = "supervised"
    UNSUPERVISED = "unsupervised"
    REINFORCEMENT = "reinforcement"
    META = "meta"
    INCREMENTAL = "incremental"
    TRANSFER = "transfer"


class ExperienceType(Enum):
    """Types of experiences for learning"""
    SUCCESS = "success"
    FAILURE = "failure"
    CORRECTION = "correction"
    FEEDBACK = "feedback"
    EXPLORATION = "exploration"
    EXPLOITATION = "exploitation"


class PersonalizationDomain(Enum):
    """Domains for personalization"""
    COMMUNICATION_STYLE = "communication_style"
    TASK_PREFERENCES = "task_preferences"
    COMPLEXITY_LEVEL = "complexity_level"
    RESPONSE_FORMAT = "response_format"
    INTERACTION_PATTERNS = "interaction_patterns"


@dataclass
class Experience:
    """Individual learning experience"""
    experience_id: str
    experience_type: ExperienceType
    context: Dict[str, Any]
    action: Dict[str, Any]
    outcome: Dict[str, Any]
    reward: float
    confidence: float
    timestamp: datetime = field(default_factory=datetime.now)
    metadata: Dict[str, Any] = field(default_factory=dict)
    learned_from: bool = False
    
    
@dataclass
class LearningUpdate:
    """Update from learning process"""
    update_id: str
    learning_type: LearningType
    source_experiences: List[str]  # Experience IDs
    knowledge_delta: Dict[str, Any]  # What was learned
    confidence_change: float
    performance_impact: float
    timestamp: datetime = field(default_factory=datetime.now)
    validation_score: Optional[float] = None


@dataclass
class PersonalizationProfile:
    """User personalization profile"""
    user_id: str
    preferences: Dict[PersonalizationDomain, Dict[str, Any]] = field(default_factory=dict)
    interaction_history: List[Dict[str, Any]] = field(default_factory=list)
    learning_patterns: Dict[str, Any] = field(default_factory=dict)
    adaptation_weights: Dict[str, float] = field(default_factory=dict)
    last_updated: datetime = field(default_factory=datetime.now)
    total_interactions: int = 0


class LearningComponent(ABC):
    """Abstract base class for learning components"""
    
    def __init__(self, component_id: str, learning_type: LearningType):
        self.component_id = component_id
        self.learning_type = learning_type
        self.learning_history = []
        self.performance_metrics = {}
        
    @abstractmethod
    async def learn(self, experiences: List[Experience]) -> LearningUpdate:
        """Learn from experiences"""
        pass
    
    @abstractmethod
    async def apply_learning(self, update: LearningUpdate) -> bool:
        """Apply learning update"""
        pass
    
    def get_performance_metrics(self) -> Dict[str, Any]:
        """Get performance metrics for this component"""
        return self.performance_metrics.copy()


class ExperienceReplay(LearningComponent):
    """
    Experience replay system for consolidating and learning from past experiences
    Implements sophisticated memory consolidation and selective replay
    """
    
    def __init__(self):
        super().__init__("experience_replay", LearningType.REINFORCEMENT)
        self.experience_buffer = deque(maxlen=10000)  # Configurable buffer size
        self.priority_buffer = {}  # For prioritized replay
        self.consolidation_policy = "recency_and_importance"
        self.replay_batch_size = 32
        
    async def store_experience(self, experience: Experience) -> None:
        """Store new experience in buffer"""
        try:
            # Add to main buffer
            self.experience_buffer.append(experience)
            
            # Calculate priority for prioritized replay
            priority = await self._calculate_priority(experience)
            self.priority_buffer[experience.experience_id] = priority
            
            # Trigger consolidation if buffer is getting full
            if len(self.experience_buffer) > 8000:  # 80% of max
                await self._consolidate_experiences()
            
            logger.debug(f"Stored experience {experience.experience_id} with priority {priority:.3f}")
            
        except Exception as e:
            logger.error(f"Failed to store experience: {e}")
    
    async def replay_experiences(
        self, 
        batch_size: Optional[int] = None,
        strategy: str = "prioritized"
    ) -> List[Experience]:
        """Replay experiences for learning"""
        
        batch_size = batch_size or self.replay_batch_size
        
        try:
            if strategy == "prioritized":
                replayed = await self._prioritized_replay(batch_size)
            elif strategy == "recent":
                replayed = await self._recent_replay(batch_size)
            elif strategy == "diverse":
                replayed = await self._diverse_replay(batch_size)
            else:
                replayed = await self._random_replay(batch_size)
            
            # Mark experiences as learned from
            for exp in replayed:
                exp.learned_from = True
            
            logger.info(f"Replayed {len(replayed)} experiences using {strategy} strategy")
            return replayed
            
        except Exception as e:
            logger.error(f"Experience replay failed: {e}")
            return []
    
    async def learn(self, experiences: List[Experience]) -> LearningUpdate:
        """Learn from replayed experiences through pattern extraction"""
        start_time = datetime.now()
        update_id = f"replay_update_{start_time.isoformat()}"
        
        try:
            # Analyze patterns in experiences
            patterns = await self._extract_patterns(experiences)
            
            # Identify successful strategies
            successful_strategies = await self._identify_successful_strategies(experiences)
            
            # Update knowledge based on patterns
            knowledge_delta = {
                'patterns_discovered': patterns,
                'successful_strategies': successful_strategies,
                'experience_insights': await self._extract_insights(experiences),
                'learned_rules': await self._extract_rules(experiences)
            }
            
            # Calculate confidence and performance impact
            confidence_change = await self._calculate_confidence_impact(experiences)
            performance_impact = await self._estimate_performance_impact(knowledge_delta)
            
            update = LearningUpdate(
                update_id=update_id,
                learning_type=self.learning_type,
                source_experiences=[exp.experience_id for exp in experiences],
                knowledge_delta=knowledge_delta,
                confidence_change=confidence_change,
                performance_impact=performance_impact
            )
            
            self.learning_history.append(update)
            logger.info(f"Experience replay learning completed: {len(experiences)} experiences processed")
            
            return update
            
        except Exception as e:
            logger.error(f"Experience replay learning failed: {e}")
            return LearningUpdate(
                update_id=f"error_{start_time.isoformat()}",
                learning_type=self.learning_type,
                source_experiences=[],
                knowledge_delta={"error": str(e)},
                confidence_change=0.0,
                performance_impact=0.0
            )
    
    async def apply_learning(self, update: LearningUpdate) -> bool:
        """Apply learning from experience replay"""
        try:
            # Update performance metrics based on learned patterns
            patterns = update.knowledge_delta.get('patterns_discovered', {})
            strategies = update.knowledge_delta.get('successful_strategies', [])
            
            # Update internal knowledge
            if patterns:
                self.performance_metrics['learned_patterns'] = patterns
            if strategies:
                self.performance_metrics['preferred_strategies'] = strategies
            
            self.performance_metrics['last_learning_update'] = datetime.now()
            self.performance_metrics['total_updates'] = self.performance_metrics.get('total_updates', 0) + 1
            
            logger.info(f"Applied experience replay learning update {update.update_id}")
            return True
            
        except Exception as e:
            logger.error(f"Failed to apply experience replay learning: {e}")
            return False
    
    async def _calculate_priority(self, experience: Experience) -> float:
        """Calculate priority for experience replay"""
        # Factors affecting priority
        recency_factor = 1.0  # More recent experiences have higher priority
        importance_factor = abs(experience.reward)  # Higher reward magnitude = higher priority
        confidence_factor = 1.0 - experience.confidence  # Lower confidence = higher priority (more to learn)
        
        # Experience type weights
        type_weights = {
            ExperienceType.SUCCESS: 0.8,
            ExperienceType.FAILURE: 1.2,  # Learn more from failures
            ExperienceType.CORRECTION: 1.5,  # Very important for learning
            ExperienceType.FEEDBACK: 1.0,
            ExperienceType.EXPLORATION: 0.9,
            ExperienceType.EXPLOITATION: 0.7
        }
        
        type_weight = type_weights.get(experience.experience_type, 1.0)
        
        priority = (recency_factor + importance_factor + confidence_factor) * type_weight
        return min(10.0, max(0.1, priority))  # Clamp between 0.1 and 10.0
    
    async def _consolidate_experiences(self) -> None:
        """Consolidate experiences to make room for new ones"""
        try:
            # Keep high-priority experiences and recent ones
            experiences_to_keep = []
            
            # Sort by priority and recency
            sorted_experiences = sorted(
                self.experience_buffer,
                key=lambda exp: (
                    self.priority_buffer.get(exp.experience_id, 0.5),
                    exp.timestamp
                ),
                reverse=True
            )
            
            # Keep top 50% by priority and all from last 24 hours
            cutoff_time = datetime.now() - timedelta(hours=24)
            for exp in sorted_experiences:
                if (len(experiences_to_keep) < len(sorted_experiences) // 2 or 
                    exp.timestamp > cutoff_time):
                    experiences_to_keep.append(exp)
            
            # Update buffer
            self.experience_buffer.clear()
            self.experience_buffer.extend(experiences_to_keep)
            
            logger.info(f"Consolidated experience buffer: kept {len(experiences_to_keep)} experiences")
            
        except Exception as e:
            logger.error(f"Experience consolidation failed: {e}")
    
    async def _prioritized_replay(self, batch_size: int) -> List[Experience]:
        """Replay experiences based on priority"""
        if not self.experience_buffer:
            return []
        
        # Sort by priority
        experiences_with_priority = [
            (exp, self.priority_buffer.get(exp.experience_id, 0.5))
            for exp in self.experience_buffer
        ]
        experiences_with_priority.sort(key=lambda x: x[1], reverse=True)
        
        # Select top experiences
        selected = [exp for exp, _ in experiences_with_priority[:batch_size]]
        return selected
    
    async def _recent_replay(self, batch_size: int) -> List[Experience]:
        """Replay most recent experiences"""
        return list(self.experience_buffer)[-batch_size:]
    
    async def _diverse_replay(self, batch_size: int) -> List[Experience]:
        """Replay diverse set of experiences"""
        if not self.experience_buffer:
            return []
        
        # Group by experience type
        type_groups = defaultdict(list)
        for exp in self.experience_buffer:
            type_groups[exp.experience_type].append(exp)
        
        # Sample from each type
        selected = []
        types = list(type_groups.keys())
        samples_per_type = batch_size // len(types) if types else 0
        
        for exp_type in types:
            samples = min(samples_per_type, len(type_groups[exp_type]))
            selected.extend(type_groups[exp_type][-samples:])  # Recent from each type
        
        return selected[:batch_size]
    
    async def _random_replay(self, batch_size: int) -> List[Experience]:
        """Randomly replay experiences"""
        if not self.experience_buffer:
            return []
        
        import random
        return random.sample(list(self.experience_buffer), min(batch_size, len(self.experience_buffer)))
    
    async def _extract_patterns(self, experiences: List[Experience]) -> Dict[str, Any]:
        """Extract patterns from experiences"""
        patterns = {
            'context_patterns': await self._analyze_context_patterns(experiences),
            'action_patterns': await self._analyze_action_patterns(experiences),
            'outcome_patterns': await self._analyze_outcome_patterns(experiences),
            'temporal_patterns': await self._analyze_temporal_patterns(experiences)
        }
        return patterns
    
    async def _analyze_context_patterns(self, experiences: List[Experience]) -> Dict[str, Any]:
        """Analyze patterns in experience contexts"""
        context_features = defaultdict(list)
        
        for exp in experiences:
            for key, value in exp.context.items():
                context_features[key].append(value)
        
        # Simple pattern analysis
        patterns = {}
        for feature, values in context_features.items():
            if len(set(values)) > 1:  # Has variation
                patterns[f"{feature}_variety"] = len(set(values))
                patterns[f"{feature}_most_common"] = max(set(values), key=values.count)
        
        return patterns
    
    async def _analyze_action_patterns(self, experiences: List[Experience]) -> Dict[str, Any]:
        """Analyze patterns in actions taken"""
        action_types = defaultdict(int)
        successful_actions = defaultdict(int)
        
        for exp in experiences:
            action_type = exp.action.get('type', 'unknown')
            action_types[action_type] += 1
            
            if exp.reward > 0:  # Successful outcome
                successful_actions[action_type] += 1
        
        return {
            'action_distribution': dict(action_types),
            'success_rates': {
                action: successful_actions[action] / action_types[action]
                for action in action_types
            }
        }
    
    async def _analyze_outcome_patterns(self, experiences: List[Experience]) -> Dict[str, Any]:
        """Analyze patterns in outcomes"""
        rewards = [exp.reward for exp in experiences]
        confidences = [exp.confidence for exp in experiences]
        
        return {
            'average_reward': sum(rewards) / len(rewards) if rewards else 0,
            'reward_variance': np.var(rewards) if rewards else 0,
            'average_confidence': sum(confidences) / len(confidences) if confidences else 0,
            'success_rate': sum(1 for r in rewards if r > 0) / len(rewards) if rewards else 0
        }
    
    async def _analyze_temporal_patterns(self, experiences: List[Experience]) -> Dict[str, Any]:
        """Analyze temporal patterns in experiences"""
        if len(experiences) < 2:
            return {}
        
        sorted_experiences = sorted(experiences, key=lambda x: x.timestamp)
        
        # Time intervals between experiences
        intervals = []
        for i in range(1, len(sorted_experiences)):
            interval = (sorted_experiences[i].timestamp - sorted_experiences[i-1].timestamp).total_seconds()
            intervals.append(interval)
        
        return {
            'average_interval': sum(intervals) / len(intervals) if intervals else 0,
            'experience_frequency': len(experiences) / (
                (sorted_experiences[-1].timestamp - sorted_experiences[0].timestamp).total_seconds() / 3600
            ) if len(experiences) > 1 else 0  # experiences per hour
        }
    
    async def _identify_successful_strategies(self, experiences: List[Experience]) -> List[Dict[str, Any]]:
        """Identify successful strategies from experiences"""
        successful_experiences = [exp for exp in experiences if exp.reward > 0]
        
        strategies = []
        for exp in successful_experiences:
            strategy = {
                'context_type': exp.context.get('type', 'unknown'),
                'action_taken': exp.action,
                'success_score': exp.reward,
                'confidence': exp.confidence
            }
            strategies.append(strategy)
        
        # Sort by success score
        strategies.sort(key=lambda x: x['success_score'], reverse=True)
        return strategies[:10]  # Top 10 strategies
    
    async def _extract_insights(self, experiences: List[Experience]) -> List[str]:
        """Extract actionable insights from experiences"""
        insights = []
        
        # Analyze success vs failure patterns
        successes = [exp for exp in experiences if exp.reward > 0]
        failures = [exp for exp in experiences if exp.reward <= 0]
        
        if successes and failures:
            insights.append(f"Success rate: {len(successes) / len(experiences):.2%}")
            
        # Common failure patterns
        if failures:
            failure_contexts = [exp.context.get('type', 'unknown') for exp in failures]
            most_common_failure = max(set(failure_contexts), key=failure_contexts.count)
            insights.append(f"Most common failure context: {most_common_failure}")
        
        return insights
    
    async def _extract_rules(self, experiences: List[Experience]) -> List[Dict[str, Any]]:
        """Extract rules from experiences"""
        rules = []
        
        # Simple rule extraction based on context-action-outcome patterns
        context_action_outcomes = defaultdict(list)
        
        for exp in experiences:
            context_key = str(sorted(exp.context.items()))
            action_key = str(sorted(exp.action.items()))
            key = (context_key, action_key)
            context_action_outcomes[key].append(exp.reward)
        
        # Generate rules for patterns with consistent outcomes
        for (context, action), rewards in context_action_outcomes.items():
            if len(rewards) >= 3 and all(r > 0 for r in rewards):  # Consistently successful
                rules.append({
                    'rule_type': 'success_pattern',
                    'context': context,
                    'action': action,
                    'expected_outcome': 'positive',
                    'confidence': min(rewards) / max(rewards) if max(rewards) > 0 else 0,
                    'sample_size': len(rewards)
                })
        
        return rules
    
    async def _calculate_confidence_impact(self, experiences: List[Experience]) -> float:
        """Calculate impact on confidence from learning"""
        if not experiences:
            return 0.0
        
        # Higher confidence impact for more diverse and successful experiences
        success_rate = sum(1 for exp in experiences if exp.reward > 0) / len(experiences)
        diversity = len(set(exp.experience_type for exp in experiences)) / len(ExperienceType)
        
        return (success_rate + diversity) / 2 * 0.1  # Small confidence boost
    
    async def _estimate_performance_impact(self, knowledge_delta: Dict[str, Any]) -> float:
        """Estimate performance impact of learned knowledge"""
        # Simple heuristic based on amount of knowledge gained
        patterns_count = len(knowledge_delta.get('patterns_discovered', {}))
        strategies_count = len(knowledge_delta.get('successful_strategies', []))
        rules_count = len(knowledge_delta.get('learned_rules', []))
        
        impact = (patterns_count + strategies_count + rules_count) / 100  # Normalized impact
        return min(1.0, max(0.0, impact))


class IncrementalLearning(LearningComponent):
    """
    Incremental learning system for continuous knowledge updates
    Learns from new information without forgetting previous knowledge
    """
    
    def __init__(self):
        super().__init__("incremental_learning", LearningType.INCREMENTAL)
        self.knowledge_base = {}
        self.learning_rate = 0.1
        self.forgetting_factor = 0.99  # Prevent catastrophic forgetting
        self.update_threshold = 0.05  # Minimum change to trigger update
        
    async def learn(self, experiences: List[Experience]) -> LearningUpdate:
        """Learn incrementally from new experiences"""
        start_time = datetime.now()
        update_id = f"incremental_update_{start_time.isoformat()}"
        
        try:
            # Process new information
            new_knowledge = await self._process_new_information(experiences)
            
            # Update existing knowledge incrementally
            knowledge_delta = await self._update_knowledge_incrementally(new_knowledge)
            
            # Prevent catastrophic forgetting
            await self._apply_forgetting_prevention()
            
            update = LearningUpdate(
                update_id=update_id,
                learning_type=self.learning_type,
                source_experiences=[exp.experience_id for exp in experiences],
                knowledge_delta=knowledge_delta,
                confidence_change=0.05,  # Small incremental confidence gain
                performance_impact=0.02   # Small incremental improvement
            )
            
            self.learning_history.append(update)
            logger.info(f"Incremental learning completed: {len(experiences)} experiences processed")
            
            return update
            
        except Exception as e:
            logger.error(f"Incremental learning failed: {e}")
            return LearningUpdate(
                update_id=f"error_{start_time.isoformat()}",
                learning_type=self.learning_type,
                source_experiences=[],
                knowledge_delta={"error": str(e)},
                confidence_change=0.0,
                performance_impact=0.0
            )
    
    async def apply_learning(self, update: LearningUpdate) -> bool:
        """Apply incremental learning update"""
        try:
            knowledge_delta = update.knowledge_delta
            
            # Merge new knowledge with existing knowledge base
            for key, value in knowledge_delta.items():
                if key == "error":
                    continue
                    
                if key in self.knowledge_base:
                    # Incremental update
                    self.knowledge_base[key] = await self._merge_knowledge(
                        self.knowledge_base[key], value
                    )
                else:
                    # New knowledge
                    self.knowledge_base[key] = value
            
            self.performance_metrics['knowledge_base_size'] = len(self.knowledge_base)
            self.performance_metrics['last_update'] = datetime.now()
            
            logger.info(f"Applied incremental learning update {update.update_id}")
            return True
            
        except Exception as e:
            logger.error(f"Failed to apply incremental learning: {e}")
            return False
    
    async def _process_new_information(self, experiences: List[Experience]) -> Dict[str, Any]:
        """Process new information from experiences"""
        new_knowledge = {}
        
        for exp in experiences:
            # Extract learnable information
            if exp.reward > 0:  # Successful experience
                context_signature = self._generate_context_signature(exp.context)
                
                if context_signature not in new_knowledge:
                    new_knowledge[context_signature] = {
                        'successful_actions': [],
                        'context_features': exp.context,
                        'success_count': 0,
                        'total_reward': 0.0
                    }
                
                new_knowledge[context_signature]['successful_actions'].append(exp.action)
                new_knowledge[context_signature]['success_count'] += 1
                new_knowledge[context_signature]['total_reward'] += exp.reward
        
        return new_knowledge
    
    def _generate_context_signature(self, context: Dict[str, Any]) -> str:
        """Generate unique signature for context"""
        # Create reproducible hash of context
        context_str = json.dumps(context, sort_keys=True)
        return hashlib.md5(context_str.encode()).hexdigest()
    
    async def _update_knowledge_incrementally(self, new_knowledge: Dict[str, Any]) -> Dict[str, Any]:
        """Update knowledge base incrementally"""
        knowledge_delta = {}
        
        for signature, new_info in new_knowledge.items():
            if signature in self.knowledge_base:
                # Incremental update of existing knowledge
                existing = self.knowledge_base[signature]
                
                # Update success statistics
                old_count = existing.get('success_count', 0)
                new_count = new_info['success_count']
                total_count = old_count + new_count
                
                old_reward = existing.get('total_reward', 0.0)
                new_reward = new_info['total_reward']
                total_reward = old_reward + new_reward
                
                # Weighted average for continuous values
                updated_info = {
                    'successful_actions': existing['successful_actions'] + new_info['successful_actions'],
                    'context_features': existing['context_features'],  # Keep original features
                    'success_count': total_count,
                    'total_reward': total_reward,
                    'average_reward': total_reward / total_count if total_count > 0 else 0
                }
                
                self.knowledge_base[signature] = updated_info
                knowledge_delta[signature] = {'type': 'updated', 'new_data': updated_info}
                
            else:
                # New knowledge
                new_info['average_reward'] = (
                    new_info['total_reward'] / new_info['success_count'] 
                    if new_info['success_count'] > 0 else 0
                )
                self.knowledge_base[signature] = new_info
                knowledge_delta[signature] = {'type': 'new', 'new_data': new_info}
        
        return knowledge_delta
    
    async def _apply_forgetting_prevention(self) -> None:
        """Apply strategies to prevent catastrophic forgetting"""
        # Apply forgetting factor to reduce influence of very old knowledge
        for signature, knowledge in self.knowledge_base.items():
            if 'last_accessed' in knowledge:
                time_since_access = (datetime.now() - knowledge['last_accessed']).days
                if time_since_access > 30:  # More than 30 days
                    # Gradually reduce influence
                    decay_factor = self.forgetting_factor ** (time_since_access - 30)
                    knowledge['influence_weight'] = knowledge.get('influence_weight', 1.0) * decay_factor
            
            knowledge['last_accessed'] = datetime.now()
    
    async def _merge_knowledge(self, existing: Any, new: Any) -> Any:
        """Merge new knowledge with existing knowledge"""
        if isinstance(existing, dict) and isinstance(new, dict):
            merged = existing.copy()
            for key, value in new.items():
                if key in merged:
                    merged[key] = await self._merge_knowledge(merged[key], value)
                else:
                    merged[key] = value
            return merged
        elif isinstance(existing, list) and isinstance(new, list):
            return existing + new
        elif isinstance(existing, (int, float)) and isinstance(new, (int, float)):
            # Weighted average
            return existing * (1 - self.learning_rate) + new * self.learning_rate
        else:
            # Default: prefer new information
            return new


class PersonalizationEngine(LearningComponent):
    """
    Personalization engine for adapting to user preferences and patterns
    Learns individual user preferences and adapts behavior accordingly
    """
    
    def __init__(self):
        super().__init__("personalization", LearningType.SUPERVISED)
        self.user_profiles = {}
        self.adaptation_strategies = {}
        self.personalization_db_path = "personalization.db"
        self._init_database()
        
    def _init_database(self) -> None:
        """Initialize personalization database"""
        try:
            conn = sqlite3.connect(self.personalization_db_path)
            cursor = conn.cursor()
            
            cursor.execute('''
                CREATE TABLE IF NOT EXISTS user_profiles (
                    user_id TEXT PRIMARY KEY,
                    profile_data TEXT,
                    last_updated TIMESTAMP,
                    total_interactions INTEGER
                )
            ''')
            
            cursor.execute('''
                CREATE TABLE IF NOT EXISTS interaction_history (
                    interaction_id TEXT PRIMARY KEY,
                    user_id TEXT,
                    interaction_data TEXT,
                    timestamp TIMESTAMP,
                    satisfaction_score REAL,
                    FOREIGN KEY (user_id) REFERENCES user_profiles (user_id)
                )
            ''')
            
            conn.commit()
            conn.close()
            
        except Exception as e:
            logger.error(f"Failed to initialize personalization database: {e}")
    
    async def learn(self, experiences: List[Experience]) -> LearningUpdate:
        """Learn user preferences from experiences"""
        start_time = datetime.now()
        update_id = f"personalization_update_{start_time.isoformat()}"
        
        try:
            # Group experiences by user
            user_experiences = defaultdict(list)
            for exp in experiences:
                user_id = exp.context.get('user_id', 'default_user')
                user_experiences[user_id].append(exp)
            
            # Learn preferences for each user
            knowledge_delta = {}
            for user_id, user_exps in user_experiences.items():
                user_learning = await self._learn_user_preferences(user_id, user_exps)
                knowledge_delta[user_id] = user_learning
            
            update = LearningUpdate(
                update_id=update_id,
                learning_type=self.learning_type,
                source_experiences=[exp.experience_id for exp in experiences],
                knowledge_delta=knowledge_delta,
                confidence_change=0.02,
                performance_impact=0.03
            )
            
            self.learning_history.append(update)
            logger.info(f"Personalization learning completed for {len(user_experiences)} users")
            
            return update
            
        except Exception as e:
            logger.error(f"Personalization learning failed: {e}")
            return LearningUpdate(
                update_id=f"error_{start_time.isoformat()}",
                learning_type=self.learning_type,
                source_experiences=[],
                knowledge_delta={"error": str(e)},
                confidence_change=0.0,
                performance_impact=0.0
            )
    
    async def apply_learning(self, update: LearningUpdate) -> bool:
        """Apply personalization learning"""
        try:
            for user_id, user_learning in update.knowledge_delta.items():
                if user_id == "error":
                    continue
                    
                # Update user profile
                if user_id not in self.user_profiles:
                    self.user_profiles[user_id] = PersonalizationProfile(user_id=user_id)
                
                profile = self.user_profiles[user_id]
                
                # Update preferences
                for domain, preferences in user_learning.get('preferences', {}).items():
                    if isinstance(domain, str):
                        domain = PersonalizationDomain(domain)
                    profile.preferences[domain] = preferences
                
                # Update learning patterns
                profile.learning_patterns.update(user_learning.get('learning_patterns', {}))
                
                # Update adaptation weights
                profile.adaptation_weights.update(user_learning.get('adaptation_weights', {}))
                
                profile.last_updated = datetime.now()
                
                # Save to database
                await self._save_user_profile(profile)
            
            logger.info(f"Applied personalization learning update {update.update_id}")
            return True
            
        except Exception as e:
            logger.error(f"Failed to apply personalization learning: {e}")
            return False
    
    async def _learn_user_preferences(self, user_id: str, experiences: List[Experience]) -> Dict[str, Any]:
        """Learn preferences for a specific user"""
        preferences = {}
        learning_patterns = {}
        adaptation_weights = {}
        
        # Analyze communication style preferences
        communication_prefs = await self._analyze_communication_preferences(experiences)
        if communication_prefs:
            preferences[PersonalizationDomain.COMMUNICATION_STYLE.value] = communication_prefs
        
        # Analyze task preferences
        task_prefs = await self._analyze_task_preferences(experiences)
        if task_prefs:
            preferences[PersonalizationDomain.TASK_PREFERENCES.value] = task_prefs
        
        # Analyze complexity level preferences
        complexity_prefs = await self._analyze_complexity_preferences(experiences)
        if complexity_prefs:
            preferences[PersonalizationDomain.COMPLEXITY_LEVEL.value] = complexity_prefs
        
        # Analyze response format preferences
        format_prefs = await self._analyze_format_preferences(experiences)
        if format_prefs:
            preferences[PersonalizationDomain.RESPONSE_FORMAT.value] = format_prefs
        
        # Learn interaction patterns
        interaction_patterns = await self._analyze_interaction_patterns(experiences)
        if interaction_patterns:
            preferences[PersonalizationDomain.INTERACTION_PATTERNS.value] = interaction_patterns
        
        # Extract learning patterns
        learning_patterns = await self._extract_learning_patterns(experiences)
        
        # Calculate adaptation weights
        adaptation_weights = await self._calculate_adaptation_weights(experiences)
        
        return {
            'preferences': preferences,
            'learning_patterns': learning_patterns,
            'adaptation_weights': adaptation_weights,
            'total_experiences': len(experiences)
        }
    
    async def _analyze_communication_preferences(self, experiences: List[Experience]) -> Dict[str, Any]:
        """Analyze communication style preferences"""
        communication_data = []
        
        for exp in experiences:
            if 'communication_style' in exp.context:
                style = exp.context['communication_style']
                satisfaction = exp.reward
                communication_data.append((style, satisfaction))
        
        if not communication_data:
            return {}
        
        # Find preferred communication styles
        style_scores = defaultdict(list)
        for style, satisfaction in communication_data:
            style_scores[style].append(satisfaction)
        
        # Calculate average satisfaction for each style
        style_preferences = {
            style: sum(scores) / len(scores)
            for style, scores in style_scores.items()
        }
        
        return {
            'preferred_styles': sorted(style_preferences.items(), key=lambda x: x[1], reverse=True),
            'style_scores': style_preferences
        }
    
    async def _analyze_task_preferences(self, experiences: List[Experience]) -> Dict[str, Any]:
        """Analyze task preferences"""
        task_data = []
        
        for exp in experiences:
            task_type = exp.context.get('task_type', 'unknown')
            satisfaction = exp.reward
            complexity = exp.context.get('complexity', 'medium')
            task_data.append((task_type, complexity, satisfaction))
        
        if not task_data:
            return {}
        
        # Analyze task type preferences
        task_scores = defaultdict(list)
        complexity_scores = defaultdict(list)
        
        for task_type, complexity, satisfaction in task_data:
            task_scores[task_type].append(satisfaction)
            complexity_scores[complexity].append(satisfaction)
        
        return {
            'preferred_task_types': {
                task: sum(scores) / len(scores)
                for task, scores in task_scores.items()
            },
            'preferred_complexity': {
                complexity: sum(scores) / len(scores)
                for complexity, scores in complexity_scores.items()
            }
        }
    
    async def _analyze_complexity_preferences(self, experiences: List[Experience]) -> Dict[str, Any]:
        """Analyze complexity level preferences"""
        complexity_data = []
        
        for exp in experiences:
            complexity = exp.context.get('complexity_level', 'medium')
            satisfaction = exp.reward
            confidence = exp.confidence
            complexity_data.append((complexity, satisfaction, confidence))
        
        if not complexity_data:
            return {}
        
        complexity_analysis = defaultdict(lambda: {'satisfaction': [], 'confidence': []})
        
        for complexity, satisfaction, confidence in complexity_data:
            complexity_analysis[complexity]['satisfaction'].append(satisfaction)
            complexity_analysis[complexity]['confidence'].append(confidence)
        
        # Calculate optimal complexity level
        complexity_scores = {}
        for complexity, data in complexity_analysis.items():
            avg_satisfaction = sum(data['satisfaction']) / len(data['satisfaction'])
            avg_confidence = sum(data['confidence']) / len(data['confidence'])
            # Combined score weighted toward satisfaction
            complexity_scores[complexity] = avg_satisfaction * 0.7 + avg_confidence * 0.3
        
        return {
            'optimal_complexity': max(complexity_scores.items(), key=lambda x: x[1])[0] if complexity_scores else 'medium',
            'complexity_scores': complexity_scores
        }
    
    async def _analyze_format_preferences(self, experiences: List[Experience]) -> Dict[str, Any]:
        """Analyze response format preferences"""
        format_data = []
        
        for exp in experiences:
            response_format = exp.context.get('response_format', 'standard')
            satisfaction = exp.reward
            format_data.append((response_format, satisfaction))
        
        if not format_data:
            return {}
        
        format_scores = defaultdict(list)
        for format_type, satisfaction in format_data:
            format_scores[format_type].append(satisfaction)
        
        format_preferences = {
            format_type: sum(scores) / len(scores)
            for format_type, scores in format_scores.items()
        }
        
        return {
            'preferred_formats': sorted(format_preferences.items(), key=lambda x: x[1], reverse=True),
            'format_scores': format_preferences
        }
    
    async def _analyze_interaction_patterns(self, experiences: List[Experience]) -> Dict[str, Any]:
        """Analyze interaction patterns"""
        if len(experiences) < 2:
            return {}
        
        # Sort by timestamp
        sorted_experiences = sorted(experiences, key=lambda x: x.timestamp)
        
        # Calculate interaction intervals
        intervals = []
        for i in range(1, len(sorted_experiences)):
            interval = (sorted_experiences[i].timestamp - sorted_experiences[i-1].timestamp).total_seconds()
            intervals.append(interval)
        
        # Analyze session patterns
        session_lengths = []
        current_session_start = sorted_experiences[0].timestamp
        
        for i, interval in enumerate(intervals):
            if interval > 3600:  # More than 1 hour gap = new session
                session_length = (sorted_experiences[i].timestamp - current_session_start).total_seconds()
                session_lengths.append(session_length)
                current_session_start = sorted_experiences[i+1].timestamp
        
        # Add final session
        if sorted_experiences:
            final_session = (sorted_experiences[-1].timestamp - current_session_start).total_seconds()
            session_lengths.append(final_session)
        
        return {
            'average_interaction_interval': sum(intervals) / len(intervals) if intervals else 0,
            'average_session_length': sum(session_lengths) / len(session_lengths) if session_lengths else 0,
            'total_sessions': len(session_lengths),
            'interaction_frequency': len(experiences) / (
                (sorted_experiences[-1].timestamp - sorted_experiences[0].timestamp).days + 1
            ) if len(experiences) > 1 else 0
        }
    
    async def _extract_learning_patterns(self, experiences: List[Experience]) -> Dict[str, Any]:
        """Extract learning patterns from user experiences"""
        learning_patterns = {
            'learns_from_failures': 0,
            'prefers_examples': 0,
            'asks_followup_questions': 0,
            'retention_rate': 0
        }
        
        # Simple pattern analysis
        failures = [exp for exp in experiences if exp.reward <= 0]
        if failures:
            # Check if user learns from failures (improved performance after failures)
            for failure in failures:
                # Find subsequent experiences
                subsequent = [exp for exp in experiences if exp.timestamp > failure.timestamp]
                if subsequent and any(exp.reward > failure.reward for exp in subsequent[:3]):
                    learning_patterns['learns_from_failures'] += 1
        
        # Normalize patterns
        total_experiences = len(experiences)
        if total_experiences > 0:
            for pattern in learning_patterns:
                learning_patterns[pattern] = learning_patterns[pattern] / total_experiences
        
        return learning_patterns
    
    async def _calculate_adaptation_weights(self, experiences: List[Experience]) -> Dict[str, float]:
        """Calculate weights for different adaptation strategies"""
        weights = {
            'responsiveness': 0.5,  # How responsive to user feedback
            'proactiveness': 0.3,   # How proactive in suggesting improvements
            'creativity': 0.4,      # How creative in responses
            'formality': 0.5        # Level of formality
        }
        
        # Adjust weights based on user feedback patterns
        positive_feedback = sum(1 for exp in experiences if exp.reward > 0.5)
        total_feedback = len(experiences)
        
        if total_feedback > 0:
            satisfaction_rate = positive_feedback / total_feedback
            
            # Higher satisfaction = maintain current approach
            if satisfaction_rate > 0.8:
                weights['responsiveness'] = min(1.0, weights['responsiveness'] + 0.1)
            elif satisfaction_rate < 0.4:
                weights['responsiveness'] = max(0.1, weights['responsiveness'] - 0.1)
        
        return weights
    
    async def _save_user_profile(self, profile: PersonalizationProfile) -> None:
        """Save user profile to database"""
        try:
            conn = sqlite3.connect(self.personalization_db_path)
            cursor = conn.cursor()
            
            profile_data = {
                'preferences': {k.value if hasattr(k, 'value') else k: v for k, v in profile.preferences.items()},
                'learning_patterns': profile.learning_patterns,
                'adaptation_weights': profile.adaptation_weights,
                'total_interactions': profile.total_interactions
            }
            
            cursor.execute('''
                INSERT OR REPLACE INTO user_profiles 
                (user_id, profile_data, last_updated, total_interactions)
                VALUES (?, ?, ?, ?)
            ''', (
                profile.user_id,
                json.dumps(profile_data),
                profile.last_updated,
                profile.total_interactions
            ))
            
            conn.commit()
            conn.close()
            
        except Exception as e:
            logger.error(f"Failed to save user profile: {e}")
    
    async def get_user_profile(self, user_id: str) -> Optional[PersonalizationProfile]:
        """Get user profile by ID"""
        if user_id in self.user_profiles:
            return self.user_profiles[user_id]
        
        # Try to load from database
        try:
            conn = sqlite3.connect(self.personalization_db_path)
            cursor = conn.cursor()
            
            cursor.execute(
                'SELECT profile_data, last_updated, total_interactions FROM user_profiles WHERE user_id = ?',
                (user_id,)
            )
            
            result = cursor.fetchone()
            conn.close()
            
            if result:
                profile_data, last_updated, total_interactions = result
                data = json.loads(profile_data)
                
                profile = PersonalizationProfile(
                    user_id=user_id,
                    preferences={
                        PersonalizationDomain(k): v 
                        for k, v in data.get('preferences', {}).items()
                    },
                    learning_patterns=data.get('learning_patterns', {}),
                    adaptation_weights=data.get('adaptation_weights', {}),
                    last_updated=datetime.fromisoformat(last_updated) if last_updated else datetime.now(),
                    total_interactions=total_interactions or 0
                )
                
                self.user_profiles[user_id] = profile
                return profile
                
        except Exception as e:
            logger.error(f"Failed to load user profile: {e}")
        
        return None


class AdaptiveLearningSystem:
    """
    Main adaptive learning system coordinating all learning components
    Provides unified interface for continuous learning and improvement
    """
    
    def __init__(self):
        self.experience_replay = ExperienceReplay()
        self.incremental_learning = IncrementalLearning()
        self.personalization_engine = PersonalizationEngine()
        
        self.learning_components = [
            self.experience_replay,
            self.incremental_learning,
            self.personalization_engine
        ]
        
        self.learning_coordination_policy = "balanced"  # balanced, experience_focused, personalization_focused
        self.learning_history = []
        
    async def process_experiences(
        self,
        experiences: List[Experience],
        learning_types: Optional[List[LearningType]] = None,
        coordination_policy: Optional[str] = None
    ) -> Dict[str, Any]:
        """Process experiences through all relevant learning components"""
        
        coordination_policy = coordination_policy or self.learning_coordination_policy
        learning_types = learning_types or [comp.learning_type for comp in self.learning_components]
        
        start_time = datetime.now()
        learning_session_id = f"learning_session_{start_time.isoformat()}"
        
        try:
            # Store experiences in experience replay buffer
            for experience in experiences:
                await self.experience_replay.store_experience(experience)
            
            # Coordinate learning across components
            learning_results = await self._coordinate_learning(
                experiences, learning_types, coordination_policy
            )
            
            # Apply learning updates
            application_results = await self._apply_learning_updates(learning_results)
            
            # Analyze learning session
            session_analysis = await self._analyze_learning_session(
                experiences, learning_results, application_results
            )
            
            # Create comprehensive result
            result = {
                'session_id': learning_session_id,
                'experiences_processed': len(experiences),
                'learning_components_used': [comp.component_id for comp in self.learning_components 
                                           if comp.learning_type in learning_types],
                'learning_results': learning_results,
                'application_results': application_results,
                'session_analysis': session_analysis,
                'processing_time': (datetime.now() - start_time).total_seconds(),
                'overall_success': all(application_results.values())
            }
            
            self.learning_history.append(result)
            
            logger.info(f"Adaptive learning session completed: {len(experiences)} experiences, "
                       f"{len(learning_results)} components, success: {result['overall_success']}")
            
            return result
            
        except Exception as e:
            logger.error(f"Adaptive learning session failed: {e}")
            return {
                'session_id': learning_session_id,
                'error': str(e),
                'success': False,
                'processing_time': (datetime.now() - start_time).total_seconds()
            }
    
    async def _coordinate_learning(
        self, 
        experiences: List[Experience], 
        learning_types: List[LearningType],
        coordination_policy: str
    ) -> Dict[str, LearningUpdate]:
        """Coordinate learning across multiple components"""
        
        learning_results = {}
        
        # Determine which components to use based on policy
        if coordination_policy == "experience_focused":
            # Focus on experience replay and incremental learning
            priority_components = [
                self.experience_replay, 
                self.incremental_learning
            ]
        elif coordination_policy == "personalization_focused":
            # Focus on personalization
            priority_components = [
                self.personalization_engine,
                self.incremental_learning
            ]
        else:  # balanced
            priority_components = self.learning_components
        
        # Execute learning in priority order
        for component in priority_components:
            if component.learning_type in learning_types:
                try:
                    # Select relevant experiences for this component
                    relevant_experiences = await self._select_relevant_experiences(
                        experiences, component.learning_type
                    )
                    
                    if relevant_experiences:
                        learning_update = await component.learn(relevant_experiences)
                        learning_results[component.component_id] = learning_update
                        
                        logger.debug(f"Learning completed for {component.component_id}: "
                                   f"{len(relevant_experiences)} experiences")
                    
                except Exception as e:
                    logger.error(f"Learning failed for {component.component_id}: {e}")
                    learning_results[component.component_id] = LearningUpdate(
                        update_id=f"error_{datetime.now().isoformat()}",
                        learning_type=component.learning_type,
                        source_experiences=[],
                        knowledge_delta={"error": str(e)},
                        confidence_change=0.0,
                        performance_impact=0.0
                    )
        
        return learning_results
    
    async def _select_relevant_experiences(
        self, 
        experiences: List[Experience], 
        learning_type: LearningType
    ) -> List[Experience]:
        """Select experiences relevant to a specific learning type"""
        
        if learning_type == LearningType.REINFORCEMENT:
            # Experience replay benefits from all experiences, especially failures and corrections
            return [exp for exp in experiences 
                   if exp.experience_type in [ExperienceType.FAILURE, ExperienceType.CORRECTION, 
                                            ExperienceType.SUCCESS, ExperienceType.FEEDBACK]]
        
        elif learning_type == LearningType.INCREMENTAL:
            # Incremental learning uses successful experiences and corrections
            return [exp for exp in experiences 
                   if exp.experience_type in [ExperienceType.SUCCESS, ExperienceType.CORRECTION]]
        
        elif learning_type == LearningType.SUPERVISED:
            # Personalization uses experiences with user feedback
            return [exp for exp in experiences 
                   if 'user_id' in exp.context and exp.experience_type == ExperienceType.FEEDBACK]
        
        else:
            # Default: return all experiences
            return experiences
    
    async def _apply_learning_updates(self, learning_results: Dict[str, LearningUpdate]) -> Dict[str, bool]:
        """Apply learning updates to components"""
        
        application_results = {}
        
        for component_id, learning_update in learning_results.items():
            try:
                # Find component
                component = next(
                    (comp for comp in self.learning_components if comp.component_id == component_id),
                    None
                )
                
                if component:
                    success = await component.apply_learning(learning_update)
                    application_results[component_id] = success
                    
                    if success:
                        logger.debug(f"Applied learning update for {component_id}")
                    else:
                        logger.warning(f"Failed to apply learning update for {component_id}")
                else:
                    logger.error(f"Component not found: {component_id}")
                    application_results[component_id] = False
                    
            except Exception as e:
                logger.error(f"Failed to apply learning update for {component_id}: {e}")
                application_results[component_id] = False
        
        return application_results
    
    async def _analyze_learning_session(
        self,
        experiences: List[Experience],
        learning_results: Dict[str, LearningUpdate],
        application_results: Dict[str, bool]
    ) -> Dict[str, Any]:
        """Analyze the learning session for insights"""
        
        analysis = {
            'experience_distribution': self._analyze_experience_distribution(experiences),
            'learning_effectiveness': self._analyze_learning_effectiveness(learning_results),
            'application_success_rate': sum(application_results.values()) / len(application_results) if application_results else 0,
            'knowledge_acquisition': self._analyze_knowledge_acquisition(learning_results),
            'performance_impact_estimate': self._estimate_session_performance_impact(learning_results)
        }
        
        return analysis
    
    def _analyze_experience_distribution(self, experiences: List[Experience]) -> Dict[str, Any]:
        """Analyze distribution of experience types"""
        type_counts = defaultdict(int)
        for exp in experiences:
            type_counts[exp.experience_type.value] += 1
        
        return {
            'total_experiences': len(experiences),
            'type_distribution': dict(type_counts),
            'success_rate': type_counts[ExperienceType.SUCCESS.value] / len(experiences) if experiences else 0,
            'failure_rate': type_counts[ExperienceType.FAILURE.value] / len(experiences) if experiences else 0
        }
    
    def _analyze_learning_effectiveness(self, learning_results: Dict[str, LearningUpdate]) -> Dict[str, Any]:
        """Analyze effectiveness of learning"""
        if not learning_results:
            return {'no_learning_results': True}
        
        confidence_changes = [result.confidence_change for result in learning_results.values()]
        performance_impacts = [result.performance_impact for result in learning_results.values()]
        
        return {
            'components_learned': len(learning_results),
            'average_confidence_change': sum(confidence_changes) / len(confidence_changes),
            'average_performance_impact': sum(performance_impacts) / len(performance_impacts),
            'total_confidence_gain': sum(confidence_changes),
            'total_performance_gain': sum(performance_impacts)
        }
    
    def _analyze_knowledge_acquisition(self, learning_results: Dict[str, LearningUpdate]) -> Dict[str, Any]:
        """Analyze knowledge acquired during learning"""
        knowledge_types = set()
        total_knowledge_items = 0
        
        for result in learning_results.values():
            knowledge_delta = result.knowledge_delta
            for key in knowledge_delta.keys():
                if key != "error":
                    knowledge_types.add(key)
                    if isinstance(knowledge_delta[key], (list, dict)):
                        total_knowledge_items += len(knowledge_delta[key])
                    else:
                        total_knowledge_items += 1
        
        return {
            'knowledge_types_acquired': len(knowledge_types),
            'total_knowledge_items': total_knowledge_items,
            'knowledge_diversity': len(knowledge_types) / len(learning_results) if learning_results else 0
        }
    
    def _estimate_session_performance_impact(self, learning_results: Dict[str, LearningUpdate]) -> float:
        """Estimate overall performance impact of the learning session"""
        if not learning_results:
            return 0.0
        
        # Weighted sum of individual component impacts
        component_weights = {
            'experience_replay': 0.4,
            'incremental_learning': 0.4,
            'personalization': 0.2
        }
        
        total_impact = 0.0
        for component_id, result in learning_results.items():
            weight = component_weights.get(component_id, 0.33)
            total_impact += result.performance_impact * weight
        
        return min(1.0, max(0.0, total_impact))
    
    async def trigger_experience_replay(
        self, 
        batch_size: Optional[int] = None,
        strategy: str = "prioritized"
    ) -> Dict[str, Any]:
        """Manually trigger experience replay learning"""
        
        try:
            # Replay experiences
            replayed_experiences = await self.experience_replay.replay_experiences(
                batch_size=batch_size,
                strategy=strategy
            )
            
            if not replayed_experiences:
                return {
                    'success': False,
                    'message': 'No experiences available for replay',
                    'replayed_count': 0
                }
            
            # Learn from replayed experiences
            learning_update = await self.experience_replay.learn(replayed_experiences)
            
            # Apply learning
            success = await self.experience_replay.apply_learning(learning_update)
            
            return {
                'success': success,
                'replayed_count': len(replayed_experiences),
                'learning_update_id': learning_update.update_id,
                'performance_impact': learning_update.performance_impact,
                'confidence_change': learning_update.confidence_change
            }
            
        except Exception as e:
            logger.error(f"Experience replay trigger failed: {e}")
            return {
                'success': False,
                'error': str(e),
                'replayed_count': 0
            }
    
    def get_learning_statistics(self) -> Dict[str, Any]:
        """Get comprehensive learning statistics"""
        
        component_stats = {}
        for component in self.learning_components:
            component_stats[component.component_id] = {
                'learning_type': component.learning_type.value,
                'updates_applied': len(component.learning_history),
                'performance_metrics': component.get_performance_metrics()
            }
        
        return {
            'total_learning_sessions': len(self.learning_history),
            'component_statistics': component_stats,
            'experience_buffer_size': len(self.experience_replay.experience_buffer),
            'user_profiles_count': len(self.personalization_engine.user_profiles),
            'knowledge_base_size': len(self.incremental_learning.knowledge_base),
            'overall_learning_effectiveness': self._calculate_overall_effectiveness()
        }
    
    def _calculate_overall_effectiveness(self) -> float:
        """Calculate overall learning effectiveness"""
        if not self.learning_history:
            return 0.0
        
        successful_sessions = sum(1 for session in self.learning_history if session.get('overall_success', False))
        return successful_sessions / len(self.learning_history)


# Export main classes
__all__ = [
    'AdaptiveLearningSystem',
    'ExperienceReplay',
    'IncrementalLearning',
    'PersonalizationEngine',
    'Experience',
    'LearningUpdate',
    'PersonalizationProfile',
    'LearningType',
    'ExperienceType',
    'PersonalizationDomain'
]
