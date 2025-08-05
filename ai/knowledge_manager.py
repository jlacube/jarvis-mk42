# ai/knowledge_manager.py
"""
Knowledge Management System for Phase 2B.4
==========================================

Advanced knowledge management capabilities including:
- Episodic memory for storing and retrieving specific experiences
- Semantic memory for structured knowledge representation
- Knowledge graph construction and reasoning
- Memory consolidation and organization
- Context-aware knowledge retrieval
- Dynamic knowledge updating and maintenance

Provides intelligent knowledge storage, organization, and retrieval for enhanced AI capabilities.
"""

import asyncio
import logging
import json
import sqlite3
import pickle
from abc import ABC, abstractmethod
from datetime import datetime, timedelta
from typing import Dict, List, Optional, Any, Union, Tuple, Set
from dataclasses import dataclass, field
from enum import Enum
import numpy as np
from pathlib import Path
from collections import defaultdict, deque
import hashlib
import networkx as nx
try:
    from sentence_transformers import SentenceTransformer  # For semantic embeddings
except ImportError:
    SentenceTransformer = None

try:
    import faiss  # For vector similarity search
except ImportError:
    faiss = None

from .config import get_settings

logger = logging.getLogger(__name__)
settings = get_settings()


class MemoryType(Enum):
    """Types of memory systems"""
    EPISODIC = "episodic"      # Specific experiences and events
    SEMANTIC = "semantic"      # General knowledge and facts
    PROCEDURAL = "procedural"  # Skills and procedures
    WORKING = "working"        # Temporary working memory


class KnowledgeType(Enum):
    """Types of knowledge"""
    FACTUAL = "factual"        # Facts and assertions
    PROCEDURAL = "procedural"  # How-to knowledge
    CONCEPTUAL = "conceptual"  # Concepts and relationships
    METACOGNITIVE = "metacognitive"  # Knowledge about knowledge


@dataclass
class EpisodicMemory:
    """Individual episodic memory entry"""
    memory_id: str
    timestamp: datetime
    context: Dict[str, Any]
    participants: List[str]
    events: List[Dict[str, Any]]
    outcomes: Dict[str, Any]
    emotional_valence: float  # -1.0 to 1.0
    importance_score: float   # 0.0 to 1.0
    retrieval_count: int = 0
    last_accessed: datetime = field(default_factory=datetime.now)
    tags: Set[str] = field(default_factory=set)
    related_memories: Set[str] = field(default_factory=set)
    
    
@dataclass 
class SemanticKnowledge:
    """Semantic knowledge entry"""
    knowledge_id: str
    concept: str
    knowledge_type: KnowledgeType
    content: Dict[str, Any]
    confidence: float
    source_memories: Set[str] = field(default_factory=set)  # Episodic memories that support this knowledge
    relationships: Dict[str, float] = field(default_factory=dict)  # Related concepts with strength
    last_updated: datetime = field(default_factory=datetime.now)
    validation_score: float = 0.0
    usage_count: int = 0
    
    
@dataclass
class KnowledgeQuery:
    """Query for knowledge retrieval"""
    query_id: str
    query_text: str
    context: Dict[str, Any] = field(default_factory=dict)
    memory_types: List[MemoryType] = field(default_factory=lambda: [MemoryType.EPISODIC, MemoryType.SEMANTIC])
    max_results: int = 10
    similarity_threshold: float = 0.5
    time_window: Optional[Tuple[datetime, datetime]] = None
    required_tags: Set[str] = field(default_factory=set)
    timestamp: datetime = field(default_factory=datetime.now)


@dataclass
class KnowledgeRetrievalResult:
    """Result from knowledge retrieval"""
    query_id: str
    episodic_memories: List[EpisodicMemory] = field(default_factory=list)
    semantic_knowledge: List[SemanticKnowledge] = field(default_factory=list)
    relevance_scores: Dict[str, float] = field(default_factory=dict)
    retrieval_confidence: float = 0.0
    processing_time: float = 0.0
    total_results: int = 0


class MemorySystem(ABC):
    """Abstract base class for memory systems"""
    
    def __init__(self, system_id: str, memory_type: MemoryType):
        self.system_id = system_id
        self.memory_type = memory_type
        self.storage_path = f"{system_id}_memory.db"
        
    @abstractmethod
    async def store(self, data: Any) -> str:
        """Store data in memory system"""
        pass
    
    @abstractmethod
    async def retrieve(self, query: KnowledgeQuery) -> List[Any]:
        """Retrieve data from memory system"""
        pass
    
    @abstractmethod
    async def update(self, memory_id: str, updates: Dict[str, Any]) -> bool:
        """Update existing memory"""
        pass
    
    @abstractmethod
    async def delete(self, memory_id: str) -> bool:
        """Delete memory"""
        pass


class EpisodicMemorySystem(MemorySystem):
    """
    Episodic memory system for storing and retrieving specific experiences
    Maintains temporal order and contextual information
    """
    
    def __init__(self):
        super().__init__("episodic", MemoryType.EPISODIC)
        self.memories = {}  # In-memory cache
        self.memory_index = {}  # For fast lookup
        self.temporal_index = []  # Chronologically ordered memory IDs
        self._init_database()
        
    def _init_database(self) -> None:
        """Initialize episodic memory database"""
        try:
            conn = sqlite3.connect(self.storage_path)
            cursor = conn.cursor()
            
            cursor.execute('''
                CREATE TABLE IF NOT EXISTS episodic_memories (
                    memory_id TEXT PRIMARY KEY,
                    timestamp TIMESTAMP,
                    context TEXT,
                    participants TEXT,
                    events TEXT,
                    outcomes TEXT,
                    emotional_valence REAL,
                    importance_score REAL,
                    retrieval_count INTEGER,
                    last_accessed TIMESTAMP,
                    tags TEXT,
                    related_memories TEXT
                )
            ''')
            
            cursor.execute('''
                CREATE INDEX IF NOT EXISTS idx_timestamp ON episodic_memories (timestamp)
            ''')
            
            cursor.execute('''
                CREATE INDEX IF NOT EXISTS idx_importance ON episodic_memories (importance_score)
            ''')
            
            conn.commit()
            conn.close()
            
            logger.info("Episodic memory database initialized")
            
        except Exception as e:
            logger.error(f"Failed to initialize episodic memory database: {e}")
    
    async def store(self, memory_data: Dict[str, Any]) -> str:
        """Store episodic memory"""
        try:
            memory_id = f"episodic_{datetime.now().isoformat()}_{hash(str(memory_data)) % 10000}"
            
            # Create episodic memory object
            episodic_memory = EpisodicMemory(
                memory_id=memory_id,
                timestamp=memory_data.get('timestamp', datetime.now()),
                context=memory_data.get('context', {}),
                participants=memory_data.get('participants', []),
                events=memory_data.get('events', []),
                outcomes=memory_data.get('outcomes', {}),
                emotional_valence=memory_data.get('emotional_valence', 0.0),
                importance_score=memory_data.get('importance_score', 0.5),
                tags=set(memory_data.get('tags', []))
            )
            
            # Store in memory cache
            self.memories[memory_id] = episodic_memory
            
            # Update temporal index
            self.temporal_index.append(memory_id)
            self.temporal_index.sort(key=lambda mid: self.memories[mid].timestamp)
            
            # Store in database
            await self._save_to_database(episodic_memory)
            
            # Update memory index for fast retrieval
            await self._update_memory_index(episodic_memory)
            
            logger.debug(f"Stored episodic memory: {memory_id}")
            return memory_id
            
        except Exception as e:
            logger.error(f"Failed to store episodic memory: {e}")
            return ""
    
    async def retrieve(self, query: KnowledgeQuery) -> List[EpisodicMemory]:
        """Retrieve episodic memories based on query"""
        try:
            matching_memories = []
            
            # Load memories from database if not in cache
            await self._load_relevant_memories(query)
            
            # Search through memories
            for memory_id, memory in self.memories.items():
                relevance_score = await self._calculate_relevance(memory, query)
                
                if relevance_score >= query.similarity_threshold:
                    matching_memories.append((memory, relevance_score))
            
            # Sort by relevance
            matching_memories.sort(key=lambda x: x[1], reverse=True)
            
            # Update access statistics
            for memory, _ in matching_memories[:query.max_results]:
                memory.retrieval_count += 1
                memory.last_accessed = datetime.now()
            
            result_memories = [memory for memory, _ in matching_memories[:query.max_results]]
            
            logger.debug(f"Retrieved {len(result_memories)} episodic memories for query {query.query_id}")
            return result_memories
            
        except Exception as e:
            logger.error(f"Failed to retrieve episodic memories: {e}")
            return []
    
    async def update(self, memory_id: str, updates: Dict[str, Any]) -> bool:
        """Update episodic memory"""
        try:
            if memory_id not in self.memories:
                # Try to load from database
                await self._load_memory_from_database(memory_id)
            
            if memory_id in self.memories:
                memory = self.memories[memory_id]
                
                # Apply updates
                for key, value in updates.items():
                    if hasattr(memory, key):
                        if key == 'tags':
                            memory.tags.update(value)
                        elif key == 'related_memories':
                            memory.related_memories.update(value)
                        else:
                            setattr(memory, key, value)
                
                # Update database
                await self._save_to_database(memory)
                
                logger.debug(f"Updated episodic memory: {memory_id}")
                return True
            
            return False
            
        except Exception as e:
            logger.error(f"Failed to update episodic memory: {e}")
            return False
    
    async def delete(self, memory_id: str) -> bool:
        """Delete episodic memory"""
        try:
            # Remove from cache
            if memory_id in self.memories:
                del self.memories[memory_id]
            
            # Remove from temporal index
            if memory_id in self.temporal_index:
                self.temporal_index.remove(memory_id)
            
            # Remove from database
            conn = sqlite3.connect(self.storage_path)
            cursor = conn.cursor()
            cursor.execute('DELETE FROM episodic_memories WHERE memory_id = ?', (memory_id,))
            conn.commit()
            conn.close()
            
            logger.debug(f"Deleted episodic memory: {memory_id}")
            return True
            
        except Exception as e:
            logger.error(f"Failed to delete episodic memory: {e}")
            return False
    
    async def _save_to_database(self, memory: EpisodicMemory) -> None:
        """Save episodic memory to database"""
        try:
            conn = sqlite3.connect(self.storage_path)
            cursor = conn.cursor()
            
            cursor.execute('''
                INSERT OR REPLACE INTO episodic_memories 
                (memory_id, timestamp, context, participants, events, outcomes, 
                 emotional_valence, importance_score, retrieval_count, last_accessed, tags, related_memories)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            ''', (
                memory.memory_id,
                memory.timestamp.isoformat(),
                json.dumps(memory.context),
                json.dumps(memory.participants),
                json.dumps(memory.events),
                json.dumps(memory.outcomes),
                memory.emotional_valence,
                memory.importance_score,
                memory.retrieval_count,
                memory.last_accessed.isoformat(),
                json.dumps(list(memory.tags)),
                json.dumps(list(memory.related_memories))
            ))
            
            conn.commit()
            conn.close()
            
        except Exception as e:
            logger.error(f"Failed to save episodic memory to database: {e}")
    
    async def _load_memory_from_database(self, memory_id: str) -> None:
        """Load specific memory from database"""
        try:
            conn = sqlite3.connect(self.storage_path)
            cursor = conn.cursor()
            
            cursor.execute('SELECT * FROM episodic_memories WHERE memory_id = ?', (memory_id,))
            row = cursor.fetchone()
            conn.close()
            
            if row:
                memory = self._row_to_memory(row)
                self.memories[memory_id] = memory
                
        except Exception as e:
            logger.error(f"Failed to load memory from database: {e}")
    
    async def _load_relevant_memories(self, query: KnowledgeQuery) -> None:
        """Load relevant memories from database based on query"""
        try:
            conn = sqlite3.connect(self.storage_path)
            cursor = conn.cursor()
            
            # Build query based on filters
            sql_query = 'SELECT * FROM episodic_memories'
            conditions = []
            params = []
            
            if query.time_window:
                conditions.append('timestamp BETWEEN ? AND ?')
                params.extend([query.time_window[0].isoformat(), query.time_window[1].isoformat()])
            
            if conditions:
                sql_query += ' WHERE ' + ' AND '.join(conditions)
            
            sql_query += ' ORDER BY importance_score DESC, timestamp DESC LIMIT ?'
            params.append(query.max_results * 2)  # Load more than needed for better filtering
            
            cursor.execute(sql_query, params)
            rows = cursor.fetchall()
            conn.close()
            
            # Convert rows to memory objects
            for row in rows:
                memory = self._row_to_memory(row)
                self.memories[memory.memory_id] = memory
                
        except Exception as e:
            logger.error(f"Failed to load relevant memories: {e}")
    
    def _row_to_memory(self, row: Tuple) -> EpisodicMemory:
        """Convert database row to EpisodicMemory object"""
        return EpisodicMemory(
            memory_id=row[0],
            timestamp=datetime.fromisoformat(row[1]),
            context=json.loads(row[2]),
            participants=json.loads(row[3]),
            events=json.loads(row[4]),
            outcomes=json.loads(row[5]),
            emotional_valence=row[6],
            importance_score=row[7],
            retrieval_count=row[8],
            last_accessed=datetime.fromisoformat(row[9]),
            tags=set(json.loads(row[10])),
            related_memories=set(json.loads(row[11]))
        )
    
    async def _update_memory_index(self, memory: EpisodicMemory) -> None:
        """Update memory index for fast retrieval"""
        # Index by tags
        for tag in memory.tags:
            if tag not in self.memory_index:
                self.memory_index[tag] = set()
            self.memory_index[tag].add(memory.memory_id)
        
        # Index by participants
        for participant in memory.participants:
            participant_key = f"participant:{participant}"
            if participant_key not in self.memory_index:
                self.memory_index[participant_key] = set()
            self.memory_index[participant_key].add(memory.memory_id)
    
    async def _calculate_relevance(self, memory: EpisodicMemory, query: KnowledgeQuery) -> float:
        """Calculate relevance score between memory and query"""
        relevance_factors = []
        
        # Text similarity (simplified - in practice would use embeddings)
        query_text = query.query_text.lower()
        memory_text = (
            json.dumps(memory.context) + " " +
            json.dumps(memory.events) + " " +
            json.dumps(memory.outcomes)
        ).lower()
        
        # Simple keyword matching
        query_words = set(query_text.split())
        memory_words = set(memory_text.split())
        word_overlap = len(query_words & memory_words) / len(query_words) if query_words else 0
        relevance_factors.append(word_overlap)
        
        # Tag matching
        if query.required_tags:
            tag_match = len(query.required_tags & memory.tags) / len(query.required_tags)
            relevance_factors.append(tag_match * 2)  # Weight tag matches more heavily
        
        # Context similarity
        context_similarity = await self._calculate_context_similarity(memory.context, query.context)
        relevance_factors.append(context_similarity)
        
        # Temporal relevance (more recent memories are more relevant)
        days_ago = (datetime.now() - memory.timestamp).days
        temporal_relevance = max(0, 1 - days_ago / 365)  # Decay over a year
        relevance_factors.append(temporal_relevance * 0.5)
        
        # Importance score
        relevance_factors.append(memory.importance_score * 0.3)
        
        # Calculate weighted average
        weights = [0.3, 0.3, 0.2, 0.1, 0.1]  # Adjust weights as needed
        if len(relevance_factors) != len(weights):
            weights = [1.0 / len(relevance_factors)] * len(relevance_factors)
        
        relevance_score = sum(factor * weight for factor, weight in zip(relevance_factors, weights))
        return min(1.0, max(0.0, relevance_score))
    
    async def _calculate_context_similarity(self, memory_context: Dict[str, Any], query_context: Dict[str, Any]) -> float:
        """Calculate similarity between memory context and query context"""
        if not query_context:
            return 0.5  # Neutral similarity if no query context
        
        matching_keys = set(memory_context.keys()) & set(query_context.keys())
        if not matching_keys:
            return 0.0
        
        similarity_scores = []
        for key in matching_keys:
            if memory_context[key] == query_context[key]:
                similarity_scores.append(1.0)
            elif isinstance(memory_context[key], str) and isinstance(query_context[key], str):
                # Simple string similarity
                common_words = set(memory_context[key].lower().split()) & set(query_context[key].lower().split())
                total_words = set(memory_context[key].lower().split()) | set(query_context[key].lower().split())
                similarity_scores.append(len(common_words) / len(total_words) if total_words else 0)
            else:
                similarity_scores.append(0.5)  # Different types, neutral similarity
        
        return sum(similarity_scores) / len(similarity_scores) if similarity_scores else 0.0
    
    async def get_recent_memories(self, days: int = 7, limit: int = 10) -> List[EpisodicMemory]:
        """Get recent memories within specified days"""
        cutoff_date = datetime.now() - timedelta(days=days)
        recent_memories = [
            memory for memory in self.memories.values()
            if memory.timestamp >= cutoff_date
        ]
        
        # Sort by timestamp (most recent first)
        recent_memories.sort(key=lambda m: m.timestamp, reverse=True)
        return recent_memories[:limit]
    
    async def get_important_memories(self, threshold: float = 0.7, limit: int = 10) -> List[EpisodicMemory]:
        """Get memories above importance threshold"""
        important_memories = [
            memory for memory in self.memories.values()
            if memory.importance_score >= threshold
        ]
        
        # Sort by importance score (highest first)
        important_memories.sort(key=lambda m: m.importance_score, reverse=True)
        return important_memories[:limit]


class SemanticMemorySystem(MemorySystem):
    """
    Semantic memory system for structured knowledge representation
    Maintains concepts, relationships, and general knowledge
    """
    
    def __init__(self):
        super().__init__("semantic", MemoryType.SEMANTIC)
        self.knowledge_base = {}  # In-memory cache
        self.concept_graph = nx.DiGraph()  # Knowledge graph
        self.embedding_model = None  # Will be initialized lazily
        self.concept_embeddings = {}  # Concept embeddings for similarity
        self._init_database()
        
    def _init_database(self) -> None:
        """Initialize semantic memory database"""
        try:
            conn = sqlite3.connect(self.storage_path)
            cursor = conn.cursor()
            
            cursor.execute('''
                CREATE TABLE IF NOT EXISTS semantic_knowledge (
                    knowledge_id TEXT PRIMARY KEY,
                    concept TEXT,
                    knowledge_type TEXT,
                    content TEXT,
                    confidence REAL,
                    source_memories TEXT,
                    relationships TEXT,
                    last_updated TIMESTAMP,
                    validation_score REAL,
                    usage_count INTEGER
                )
            ''')
            
            cursor.execute('''
                CREATE INDEX IF NOT EXISTS idx_concept ON semantic_knowledge (concept)
            ''')
            
            cursor.execute('''
                CREATE INDEX IF NOT EXISTS idx_knowledge_type ON semantic_knowledge (knowledge_type)
            ''')
            
            conn.commit()
            conn.close()
            
            logger.info("Semantic memory database initialized")
            
        except Exception as e:
            logger.error(f"Failed to initialize semantic memory database: {e}")
    
    async def store(self, knowledge_data: Dict[str, Any]) -> str:
        """Store semantic knowledge"""
        try:
            knowledge_id = f"semantic_{knowledge_data['concept']}_{hash(str(knowledge_data)) % 10000}"
            
            # Create semantic knowledge object
            semantic_knowledge = SemanticKnowledge(
                knowledge_id=knowledge_id,
                concept=knowledge_data['concept'],
                knowledge_type=KnowledgeType(knowledge_data.get('knowledge_type', 'factual')),
                content=knowledge_data.get('content', {}),
                confidence=knowledge_data.get('confidence', 0.5),
                source_memories=set(knowledge_data.get('source_memories', [])),
                relationships=knowledge_data.get('relationships', {})
            )
            
            # Store in memory cache
            self.knowledge_base[knowledge_id] = semantic_knowledge
            
            # Update knowledge graph
            await self._update_knowledge_graph(semantic_knowledge)
            
            # Store in database
            await self._save_to_database(semantic_knowledge)
            
            # Update concept embeddings
            await self._update_concept_embeddings(semantic_knowledge.concept)
            
            logger.debug(f"Stored semantic knowledge: {knowledge_id}")
            return knowledge_id
            
        except Exception as e:
            logger.error(f"Failed to store semantic knowledge: {e}")
            return ""
    
    async def retrieve(self, query: KnowledgeQuery) -> List[SemanticKnowledge]:
        """Retrieve semantic knowledge based on query"""
        try:
            matching_knowledge = []
            
            # Load relevant knowledge from database
            await self._load_relevant_knowledge(query)
            
            # Search through knowledge base
            for knowledge_id, knowledge in self.knowledge_base.items():
                relevance_score = await self._calculate_semantic_relevance(knowledge, query)
                
                if relevance_score >= query.similarity_threshold:
                    matching_knowledge.append((knowledge, relevance_score))
            
            # Sort by relevance
            matching_knowledge.sort(key=lambda x: x[1], reverse=True)
            
            # Update usage statistics
            for knowledge, _ in matching_knowledge[:query.max_results]:
                knowledge.usage_count += 1
            
            result_knowledge = [knowledge for knowledge, _ in matching_knowledge[:query.max_results]]
            
            logger.debug(f"Retrieved {len(result_knowledge)} semantic knowledge entries for query {query.query_id}")
            return result_knowledge
            
        except Exception as e:
            logger.error(f"Failed to retrieve semantic knowledge: {e}")
            return []
    
    async def update(self, knowledge_id: str, updates: Dict[str, Any]) -> bool:
        """Update semantic knowledge"""
        try:
            if knowledge_id not in self.knowledge_base:
                await self._load_knowledge_from_database(knowledge_id)
            
            if knowledge_id in self.knowledge_base:
                knowledge = self.knowledge_base[knowledge_id]
                
                # Apply updates
                for key, value in updates.items():
                    if hasattr(knowledge, key):
                        if key == 'source_memories':
                            knowledge.source_memories.update(value)
                        elif key == 'relationships':
                            knowledge.relationships.update(value)
                        else:
                            setattr(knowledge, key, value)
                
                knowledge.last_updated = datetime.now()
                
                # Update knowledge graph
                await self._update_knowledge_graph(knowledge)
                
                # Update database
                await self._save_to_database(knowledge)
                
                logger.debug(f"Updated semantic knowledge: {knowledge_id}")
                return True
            
            return False
            
        except Exception as e:
            logger.error(f"Failed to update semantic knowledge: {e}")
            return False
    
    async def delete(self, knowledge_id: str) -> bool:
        """Delete semantic knowledge"""
        try:
            # Remove from cache
            if knowledge_id in self.knowledge_base:
                knowledge = self.knowledge_base[knowledge_id]
                
                # Remove from knowledge graph
                if self.concept_graph.has_node(knowledge.concept):
                    self.concept_graph.remove_node(knowledge.concept)
                
                del self.knowledge_base[knowledge_id]
            
            # Remove from database
            conn = sqlite3.connect(self.storage_path)
            cursor = conn.cursor()
            cursor.execute('DELETE FROM semantic_knowledge WHERE knowledge_id = ?', (knowledge_id,))
            conn.commit()
            conn.close()
            
            logger.debug(f"Deleted semantic knowledge: {knowledge_id}")
            return True
            
        except Exception as e:
            logger.error(f"Failed to delete semantic knowledge: {e}")
            return False
    
    async def _update_knowledge_graph(self, knowledge: SemanticKnowledge) -> None:
        """Update knowledge graph with new or updated knowledge"""
        try:
            # Add concept node if not exists
            if not self.concept_graph.has_node(knowledge.concept):
                self.concept_graph.add_node(
                    knowledge.concept,
                    knowledge_type=knowledge.knowledge_type.value,
                    confidence=knowledge.confidence,
                    usage_count=knowledge.usage_count
                )
            else:
                # Update node attributes
                self.concept_graph.nodes[knowledge.concept].update({
                    'confidence': knowledge.confidence,
                    'usage_count': knowledge.usage_count
                })
            
            # Add relationship edges
            for related_concept, strength in knowledge.relationships.items():
                if not self.concept_graph.has_node(related_concept):
                    self.concept_graph.add_node(related_concept)
                
                # Add or update edge
                self.concept_graph.add_edge(
                    knowledge.concept,
                    related_concept,
                    weight=strength,
                    relationship_type='related'
                )
                
        except Exception as e:
            logger.error(f"Failed to update knowledge graph: {e}")
    
    async def _save_to_database(self, knowledge: SemanticKnowledge) -> None:
        """Save semantic knowledge to database"""
        try:
            conn = sqlite3.connect(self.storage_path)
            cursor = conn.cursor()
            
            cursor.execute('''
                INSERT OR REPLACE INTO semantic_knowledge 
                (knowledge_id, concept, knowledge_type, content, confidence, 
                 source_memories, relationships, last_updated, validation_score, usage_count)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            ''', (
                knowledge.knowledge_id,
                knowledge.concept,
                knowledge.knowledge_type.value,
                json.dumps(knowledge.content),
                knowledge.confidence,
                json.dumps(list(knowledge.source_memories)),
                json.dumps(knowledge.relationships),
                knowledge.last_updated.isoformat(),
                knowledge.validation_score,
                knowledge.usage_count
            ))
            
            conn.commit()
            conn.close()
            
        except Exception as e:
            logger.error(f"Failed to save semantic knowledge to database: {e}")
    
    async def _load_knowledge_from_database(self, knowledge_id: str) -> None:
        """Load specific knowledge from database"""
        try:
            conn = sqlite3.connect(self.storage_path)
            cursor = conn.cursor()
            
            cursor.execute('SELECT * FROM semantic_knowledge WHERE knowledge_id = ?', (knowledge_id,))
            row = cursor.fetchone()
            conn.close()
            
            if row:
                knowledge = self._row_to_knowledge(row)
                self.knowledge_base[knowledge_id] = knowledge
                
        except Exception as e:
            logger.error(f"Failed to load knowledge from database: {e}")
    
    async def _load_relevant_knowledge(self, query: KnowledgeQuery) -> None:
        """Load relevant knowledge from database based on query"""
        try:
            conn = sqlite3.connect(self.storage_path)
            cursor = conn.cursor()
            
            # Build query for concept matching
            query_words = query.query_text.lower().split()
            concept_conditions = []
            params = []
            
            for word in query_words:
                concept_conditions.append('concept LIKE ?')
                params.append(f'%{word}%')
            
            sql_query = 'SELECT * FROM semantic_knowledge'
            if concept_conditions:
                sql_query += ' WHERE ' + ' OR '.join(concept_conditions)
            
            sql_query += ' ORDER BY confidence DESC, usage_count DESC LIMIT ?'
            params.append(query.max_results * 2)
            
            cursor.execute(sql_query, params)
            rows = cursor.fetchall()
            conn.close()
            
            # Convert rows to knowledge objects
            for row in rows:
                knowledge = self._row_to_knowledge(row)
                self.knowledge_base[knowledge.knowledge_id] = knowledge
                
        except Exception as e:
            logger.error(f"Failed to load relevant knowledge: {e}")
    
    def _row_to_knowledge(self, row: Tuple) -> SemanticKnowledge:
        """Convert database row to SemanticKnowledge object"""
        return SemanticKnowledge(
            knowledge_id=row[0],
            concept=row[1],
            knowledge_type=KnowledgeType(row[2]),
            content=json.loads(row[3]),
            confidence=row[4],
            source_memories=set(json.loads(row[5])),
            relationships=json.loads(row[6]),
            last_updated=datetime.fromisoformat(row[7]),
            validation_score=row[8],
            usage_count=row[9]
        )
    
    async def _calculate_semantic_relevance(self, knowledge: SemanticKnowledge, query: KnowledgeQuery) -> float:
        """Calculate semantic relevance score"""
        relevance_factors = []
        
        # Concept similarity
        concept_similarity = await self._calculate_concept_similarity(knowledge.concept, query.query_text)
        concept_similarity = concept_similarity if concept_similarity is not None else 0.0
        relevance_factors.append(concept_similarity)
        
        # Content similarity
        content_text = json.dumps(knowledge.content).lower()
        query_text = query.query_text.lower()
        
        content_words = set(content_text.split())
        query_words = set(query_text.split())
        word_overlap = len(content_words & query_words) / len(query_words) if query_words else 0
        relevance_factors.append(word_overlap)
        
        # Confidence factor
        confidence = knowledge.confidence if knowledge.confidence is not None else 0.0
        relevance_factors.append(confidence * 0.5)
        
        # Usage frequency (popular knowledge is more relevant)
        usage_count = knowledge.usage_count if knowledge.usage_count is not None else 0
        usage_factor = min(1.0, usage_count / 100)  # Normalize usage count
        relevance_factors.append(usage_factor * 0.3)
        
        # Calculate weighted average
        weights = [0.4, 0.3, 0.2, 0.1]
        relevance_score = sum(factor * weight for factor, weight in zip(relevance_factors, weights) if factor is not None and weight is not None)
        
        return min(1.0, max(0.0, relevance_score))
    
    async def _calculate_concept_similarity(self, concept: str, query_text: str) -> float:
        """Calculate similarity between concept and query text"""
        # Initialize embedding model if needed
        if self.embedding_model is None:
            try:
                if SentenceTransformer is not None:
                    self.embedding_model = SentenceTransformer('all-MiniLM-L6-v2')
                else:
                    raise ImportError("SentenceTransformer not available")
            except Exception as e:
                logger.warning(f"Failed to load embedding model, using simple similarity: {e}")
                # Fallback to simple word matching
                concept_words = set(concept.lower().split())
                query_words = set(query_text.lower().split())
                return len(concept_words & query_words) / len(concept_words | query_words) if concept_words | query_words else 0
        
            try:
                # Use embeddings for semantic similarity
                concept_embedding = self.embedding_model.encode([concept])
                query_embedding = self.embedding_model.encode([query_text])
                
                # Calculate cosine similarity using numpy
                from numpy.linalg import norm
                concept_vec = concept_embedding[0]
                query_vec = query_embedding[0]
                
                # Cosine similarity = dot product / (norm1 * norm2)
                similarity = np.dot(concept_vec, query_vec) / (norm(concept_vec) * norm(query_vec))
                return float(similarity)
                
            except Exception as e:
                logger.warning(f"Embedding similarity failed, using fallback: {e}")
                # Fallback to simple similarity
                concept_words = set(concept.lower().split())
                query_words = set(query_text.lower().split())
                return len(concept_words & query_words) / len(concept_words | query_words) if concept_words | query_words else 0
    
    async def _update_concept_embeddings(self, concept: str) -> None:
        """Update concept embeddings for similarity search"""
        try:
            if self.embedding_model is None and SentenceTransformer is not None:
                self.embedding_model = SentenceTransformer('all-MiniLM-L6-v2')
            
            if self.embedding_model is not None:
                embedding = self.embedding_model.encode([concept])
                self.concept_embeddings[concept] = embedding[0]
            
        except Exception as e:
            logger.warning(f"Failed to update concept embeddings: {e}")
    
    async def get_related_concepts(self, concept: str, max_depth: int = 2) -> Dict[str, float]:
        """Get concepts related to the given concept"""
        try:
            if not self.concept_graph.has_node(concept):
                return {}
            
            related_concepts = {}
            
            # Get direct neighbors
            for neighbor in self.concept_graph.neighbors(concept):
                edge_data = self.concept_graph.get_edge_data(concept, neighbor)
                weight = edge_data.get('weight', 0.5) if edge_data else 0.5
                related_concepts[neighbor] = weight
            
            # Get concepts at depth 2 if requested
            if max_depth > 1:
                for neighbor in list(related_concepts.keys()):
                    for second_neighbor in self.concept_graph.neighbors(neighbor):
                        if second_neighbor != concept and second_neighbor not in related_concepts:
                            edge_data = self.concept_graph.get_edge_data(neighbor, second_neighbor)
                            weight = edge_data.get('weight', 0.5) if edge_data else 0.5
                            # Reduce weight for indirect connections
                            related_concepts[second_neighbor] = weight * 0.5
            
            return related_concepts
            
        except Exception as e:
            logger.error(f"Failed to get related concepts: {e}")
            return {}
    
    async def get_concept_path(self, concept1: str, concept2: str) -> List[str]:
        """Find shortest path between two concepts in knowledge graph"""
        try:
            if (self.concept_graph.has_node(concept1) and 
                self.concept_graph.has_node(concept2)):
                path = nx.shortest_path(self.concept_graph, concept1, concept2)
                return path
            return []
            
        except (nx.NetworkXNoPath, nx.NodeNotFound):
            return []
        except Exception as e:
            logger.error(f"Failed to find concept path: {e}")
            return []


class KnowledgeManager:
    """
    Main knowledge management system coordinating episodic and semantic memory
    Provides unified interface for knowledge storage, retrieval, and reasoning
    """
    
    def __init__(self):
        self.episodic_memory = EpisodicMemorySystem()
        self.semantic_memory = SemanticMemorySystem()
        self.query_history = []
        self.consolidation_policy = "importance_based"  # importance_based, frequency_based, recency_based
        
    async def store_experience(
        self,
        experience_data: Dict[str, Any],
        extract_knowledge: bool = True
    ) -> Dict[str, str]:
        """Store experience and optionally extract semantic knowledge"""
        
        try:
            result = {"episodic_memory_id": "", "semantic_knowledge_ids": []}
            
            # Store episodic memory
            episodic_id = await self.episodic_memory.store(experience_data)
            result["episodic_memory_id"] = episodic_id
            
            # Extract and store semantic knowledge if requested
            if extract_knowledge and episodic_id:
                knowledge_entries = await self._extract_semantic_knowledge(experience_data, episodic_id)
                
                for knowledge_data in knowledge_entries:
                    semantic_id = await self.semantic_memory.store(knowledge_data)
                    if semantic_id:
                        result["semantic_knowledge_ids"].append(semantic_id)
            
            logger.info(f"Stored experience: episodic_id={episodic_id}, "
                       f"semantic_ids={result['semantic_knowledge_ids']}")
            
            return result
            
        except Exception as e:
            logger.error(f"Failed to store experience: {e}")
            return {"episodic_memory_id": "", "semantic_knowledge_ids": [], "error": str(e)}
    
    async def query_knowledge(
        self,
        query_text: str,
        context: Optional[Dict[str, Any]] = None,
        memory_types: Optional[List[MemoryType]] = None,
        max_results: int = 10
    ) -> KnowledgeRetrievalResult:
        """Query knowledge across episodic and semantic memory"""
        
        start_time = datetime.now()
        query_id = f"query_{start_time.isoformat()}"
        
        try:
            # Create query object
            query = KnowledgeQuery(
                query_id=query_id,
                query_text=query_text,
                context=context or {},
                memory_types=memory_types or [MemoryType.EPISODIC, MemoryType.SEMANTIC],
                max_results=max_results
            )
            
            # Retrieve from both memory systems
            episodic_results = []
            semantic_results = []
            
            if MemoryType.EPISODIC in query.memory_types:
                episodic_results = await self.episodic_memory.retrieve(query)
            
            if MemoryType.SEMANTIC in query.memory_types:
                semantic_results = await self.semantic_memory.retrieve(query)
            
            # Calculate relevance scores
            relevance_scores = {}
            
            for memory in episodic_results:
                relevance_scores[memory.memory_id] = await self._calculate_episodic_relevance(memory, query)
            
            for knowledge in semantic_results:
                relevance_scores[knowledge.knowledge_id] = await self._calculate_semantic_relevance(knowledge, query)
            
            # Calculate overall retrieval confidence
            retrieval_confidence = await self._calculate_retrieval_confidence(
                episodic_results, semantic_results, relevance_scores
            )
            
            # Create result
            processing_time = (datetime.now() - start_time).total_seconds()
            
            result = KnowledgeRetrievalResult(
                query_id=query_id,
                episodic_memories=episodic_results,
                semantic_knowledge=semantic_results,
                relevance_scores=relevance_scores,
                retrieval_confidence=retrieval_confidence,
                processing_time=processing_time,
                total_results=len(episodic_results) + len(semantic_results)
            )
            
            self.query_history.append(result)
            
            logger.info(f"Knowledge query completed: {result.total_results} results, "
                       f"confidence={retrieval_confidence:.2f}, time={processing_time:.3f}s")
            
            return result
            
        except Exception as e:
            logger.error(f"Knowledge query failed: {e}")
            return KnowledgeRetrievalResult(
                query_id=query_id,
                retrieval_confidence=0.0,
                processing_time=(datetime.now() - start_time).total_seconds()
            )
    
    async def consolidate_knowledge(
        self,
        consolidation_type: str = "auto",
        min_importance: float = 0.3
    ) -> Dict[str, Any]:
        """Consolidate knowledge by strengthening important memories and knowledge"""
        
        try:
            consolidation_results = {
                "episodic_consolidated": 0,
                "semantic_consolidated": 0,
                "new_knowledge_extracted": 0,
                "relationships_strengthened": 0
            }
            
            # Consolidate episodic memories
            important_memories = await self.episodic_memory.get_important_memories(
                threshold=min_importance
            )
            
            for memory in important_memories:
                # Increase importance score for frequently accessed memories
                if memory.retrieval_count > 5:
                    await self.episodic_memory.update(
                        memory.memory_id,
                        {"importance_score": min(1.0, memory.importance_score * 1.1)}
                    )
                    consolidation_results["episodic_consolidated"] += 1
            
            # Extract new semantic knowledge from important episodic memories
            for memory in important_memories:
                if memory.retrieval_count > 3:  # Frequently accessed
                    experience_data = {
                        "context": memory.context,
                        "events": memory.events,
                        "outcomes": memory.outcomes,
                        "importance_score": memory.importance_score
                    }
                    
                    new_knowledge = await self._extract_semantic_knowledge(
                        experience_data, memory.memory_id
                    )
                    
                    for knowledge_data in new_knowledge:
                        semantic_id = await self.semantic_memory.store(knowledge_data)
                        if semantic_id:
                            consolidation_results["new_knowledge_extracted"] += 1
            
            # Strengthen semantic knowledge relationships
            await self._strengthen_knowledge_relationships()
            consolidation_results["relationships_strengthened"] = 1
            
            # Update semantic knowledge confidence based on supporting evidence
            await self._update_knowledge_confidence()
            consolidation_results["semantic_consolidated"] = len(self.semantic_memory.knowledge_base)
            
            logger.info(f"Knowledge consolidation completed: {consolidation_results}")
            return consolidation_results
            
        except Exception as e:
            logger.error(f"Knowledge consolidation failed: {e}")
            return {"error": str(e)}
    
    async def _extract_semantic_knowledge(
        self, 
        experience_data: Dict[str, Any], 
        source_memory_id: str
    ) -> List[Dict[str, Any]]:
        """Extract semantic knowledge from episodic experience"""
        
        knowledge_entries = []
        
        try:
            # Extract factual knowledge from outcomes
            outcomes = experience_data.get("outcomes", {})
            if outcomes:
                for key, value in outcomes.items():
                    if isinstance(value, (str, int, float, bool)):
                        knowledge_entries.append({
                            "concept": key,
                            "knowledge_type": "factual",
                            "content": {"fact": value, "context": experience_data.get("context", {})},
                            "confidence": experience_data.get("importance_score", 0.5),
                            "source_memories": [source_memory_id]
                        })
            
            # Extract procedural knowledge from events
            events = experience_data.get("events", [])
            if events:
                for event in events:
                    if isinstance(event, dict) and "action" in event:
                        action = event["action"]
                        result = event.get("result", "unknown")
                        
                        knowledge_entries.append({
                            "concept": f"action_{action}",
                            "knowledge_type": "procedural",
                            "content": {
                                "action": action,
                                "result": result,
                                "context": experience_data.get("context", {})
                            },
                            "confidence": experience_data.get("importance_score", 0.5),
                            "source_memories": [source_memory_id]
                        })
            
            # Extract conceptual knowledge from context patterns
            context = experience_data.get("context", {})
            if context:
                for context_key, context_value in context.items():
                    if isinstance(context_value, str):
                        knowledge_entries.append({
                            "concept": f"context_{context_key}",
                            "knowledge_type": "conceptual",
                            "content": {
                                "attribute": context_key,
                                "value": context_value,
                                "associated_outcomes": outcomes
                            },
                            "confidence": experience_data.get("importance_score", 0.4),
                            "source_memories": [source_memory_id]
                        })
            
            return knowledge_entries
            
        except Exception as e:
            logger.error(f"Failed to extract semantic knowledge: {e}")
            return []
    
    async def _calculate_episodic_relevance(self, memory: EpisodicMemory, query: KnowledgeQuery) -> float:
        """Calculate relevance score for episodic memory"""
        # This would be implemented similarly to the existing relevance calculation
        # in the EpisodicMemorySystem
        return 0.7  # Simplified for now
    
    async def _calculate_semantic_relevance(self, knowledge: SemanticKnowledge, query: KnowledgeQuery) -> float:
        """Calculate relevance score for semantic knowledge"""
        # This would be implemented similarly to the existing relevance calculation
        # in the SemanticMemorySystem
        return 0.7  # Simplified for now
    
    async def _calculate_retrieval_confidence(
        self,
        episodic_results: List[EpisodicMemory],
        semantic_results: List[SemanticKnowledge],
        relevance_scores: Dict[str, float]
    ) -> float:
        """Calculate overall confidence in retrieval results"""
        
        if not relevance_scores:
            return 0.0
        
        # Factors affecting confidence
        result_count_factor = min(1.0, len(relevance_scores) / 5)  # More results = higher confidence
        average_relevance = sum(relevance_scores.values()) / len(relevance_scores)
        
        # Boost confidence if we have both episodic and semantic results
        diversity_factor = 1.0
        if episodic_results and semantic_results:
            diversity_factor = 1.2
        
        confidence = average_relevance * result_count_factor * diversity_factor
        return min(1.0, max(0.0, confidence))
    
    async def _strengthen_knowledge_relationships(self) -> None:
        """Strengthen relationships between frequently co-occurring concepts"""
        try:
            # Get concept co-occurrence patterns from episodic memories
            concept_cooccurrence = defaultdict(int)
            
            for memory in self.episodic_memory.memories.values():
                # Extract concepts from memory content
                memory_concepts = set()
                
                # Add concepts from context
                for key in memory.context.keys():
                    memory_concepts.add(f"context_{key}")
                
                # Add concepts from outcomes
                for key in memory.outcomes.keys():
                    memory_concepts.add(key)
                
                # Count co-occurrences
                for concept1 in memory_concepts:
                    for concept2 in memory_concepts:
                        if concept1 != concept2:
                            pair = tuple(sorted([concept1, concept2]))
                            concept_cooccurrence[pair] += 1
            
            # Strengthen relationships for frequently co-occurring concepts
            for (concept1, concept2), count in concept_cooccurrence.items():
                if count >= 3:  # Minimum co-occurrence threshold
                    strength = min(1.0, count / 10)  # Normalize strength
                    
                    # Update relationships in both concepts
                    for knowledge in self.semantic_memory.knowledge_base.values():
                        if knowledge.concept == concept1:
                            knowledge.relationships[concept2] = max(
                                knowledge.relationships.get(concept2, 0.0),
                                strength
                            )
                        elif knowledge.concept == concept2:
                            knowledge.relationships[concept1] = max(
                                knowledge.relationships.get(concept1, 0.0),
                                strength
                            )
            
        except Exception as e:
            logger.error(f"Failed to strengthen knowledge relationships: {e}")
    
    async def _update_knowledge_confidence(self) -> None:
        """Update knowledge confidence based on supporting evidence"""
        try:
            for knowledge in self.semantic_memory.knowledge_base.values():
                # More source memories = higher confidence
                source_count_factor = min(1.0, len(knowledge.source_memories) / 5)
                
                # More usage = higher confidence
                usage_factor = min(1.0, knowledge.usage_count / 20)
                
                # More relationships = higher confidence
                relationship_factor = min(1.0, len(knowledge.relationships) / 10)
                
                # Calculate new confidence
                new_confidence = (
                    knowledge.confidence * 0.5 +  # Existing confidence
                    source_count_factor * 0.2 +   # Evidence from memories
                    usage_factor * 0.2 +          # Usage frequency
                    relationship_factor * 0.1     # Network connectivity
                )
                
                knowledge.confidence = min(1.0, max(0.1, new_confidence))
                
        except Exception as e:
            logger.error(f"Failed to update knowledge confidence: {e}")
    
    def get_knowledge_statistics(self) -> Dict[str, Any]:
        """Get comprehensive knowledge management statistics"""
        
        episodic_stats = {
            "total_memories": len(self.episodic_memory.memories),
            "average_importance": sum(m.importance_score for m in self.episodic_memory.memories.values()) / len(self.episodic_memory.memories) if self.episodic_memory.memories else 0,
            "total_retrievals": sum(m.retrieval_count for m in self.episodic_memory.memories.values()),
            "temporal_index_size": len(self.episodic_memory.temporal_index)
        }
        
        semantic_stats = {
            "total_knowledge": len(self.semantic_memory.knowledge_base),
            "average_confidence": sum(k.confidence for k in self.semantic_memory.knowledge_base.values()) / len(self.semantic_memory.knowledge_base) if self.semantic_memory.knowledge_base else 0,
            "total_concepts": len(set(k.concept for k in self.semantic_memory.knowledge_base.values())),
            "knowledge_graph_nodes": self.semantic_memory.concept_graph.number_of_nodes(),
            "knowledge_graph_edges": self.semantic_memory.concept_graph.number_of_edges()
        }
        
        return {
            "episodic_memory": episodic_stats,
            "semantic_memory": semantic_stats,
            "total_queries": len(self.query_history),
            "consolidation_policy": self.consolidation_policy
        }


# Export main classes
__all__ = [
    'KnowledgeManager',
    'EpisodicMemorySystem',
    'SemanticMemorySystem',
    'EpisodicMemory',
    'SemanticKnowledge',
    'KnowledgeQuery',
    'KnowledgeRetrievalResult',
    'MemoryType',
    'KnowledgeType'
]
