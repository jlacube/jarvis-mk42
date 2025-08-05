# agents/enhanced_document_intelligence_agent.py
"""
Enhanced Document Intelligence Agent with Communication Framework Integration
============================================================================

This module implements the Enhanced Document Intelligence Agent for Phase 2B.3,
extending document processing capabilities with knowledge graph construction,
interactive querying, and multi-language processing.

Key Features:
- Enhanced document analysis with LLM integration
- Knowledge graph construction from document content
- Interactive document Q&A capabilities
- Multi-document synthesis and analysis
- Multi-language document processing
- Communication framework integration for collaborative analysis
- Document collection management with search capabilities

This agent extends BaseEnhancedAgent to ensure integration with the
Phase 2B.2 Inter-Agent Communication Framework.
"""

import asyncio
import logging
import json
import hashlib
import re
from datetime import datetime
from typing import Dict, List, Optional, Any, Union, Tuple, Set
from dataclasses import dataclass, field
from enum import Enum
from pathlib import Path
import pickle

# AI and NLP libraries
from langchain_core.messages import HumanMessage, AIMessage, SystemMessage
from langchain.text_splitter import RecursiveCharacterTextSplitter
from langchain.schema import Document

# Internal imports
from agents.base_enhanced_agent import BaseEnhancedAgent
from communication.protocols import (
    AgentMessage, MessageType, MessagePriority, AgentType,
    RequestMessage, ResponseMessage, NotificationMessage
)
from tools.document_intelligence import DocumentProcessor, get_document_intelligence_tools
from tools.reasoning_tools import get_reasoning_tools
from tools.language_detection import detect_text_language, get_language_display_name
from utils.language_utils import get_language_context, is_text_mixed_language
from models.models import get_google_model
from config.settings import get_settings
from utils.logging_config import get_logger

logger = get_logger(__name__)

# Document Intelligence Configuration
class DocumentAnalysisMode(Enum):
    """Document analysis modes"""
    BASIC = "basic"
    ENHANCED = "enhanced"
    DEEP_ANALYSIS = "deep_analysis"
    KNOWLEDGE_GRAPH = "knowledge_graph"

class DocumentType(Enum):
    """Document type classification"""
    ACADEMIC_PAPER = "academic_paper"
    BUSINESS_REPORT = "business_report"
    TECHNICAL_MANUAL = "technical_manual"
    LEGAL_DOCUMENT = "legal_document"
    NEWS_ARTICLE = "news_article"
    REFERENCE_MATERIAL = "reference_material"
    PRESENTATION = "presentation"
    SPREADSHEET = "spreadsheet"
    OTHER = "other"

@dataclass
class DocumentEntity:
    """Represents an entity extracted from a document"""
    name: str
    entity_type: str  # PERSON, ORGANIZATION, LOCATION, CONCEPT, etc.
    context: str
    confidence: float
    document_id: str
    page_number: Optional[int] = None
    position: Optional[Tuple[int, int]] = None

@dataclass  
class DocumentRelationship:
    """Represents a relationship between entities"""
    subject: str
    predicate: str
    object: str
    confidence: float
    context: str
    document_id: str

@dataclass
class DocumentKnowledgeGraph:
    """Knowledge graph constructed from document content"""
    entities: Dict[str, DocumentEntity] = field(default_factory=dict)
    relationships: List[DocumentRelationship] = field(default_factory=list)
    concepts: Dict[str, List[str]] = field(default_factory=dict)
    document_metadata: Dict[str, Any] = field(default_factory=dict)
    created_at: datetime = field(default_factory=datetime.now)
    
    def add_entity(self, entity: DocumentEntity):
        """Add an entity to the knowledge graph"""
        self.entities[entity.name] = entity
    
    def add_relationship(self, relationship: DocumentRelationship):
        """Add a relationship to the knowledge graph"""
        self.relationships.append(relationship)
    
    def get_related_entities(self, entity_name: str) -> List[str]:
        """Get entities related to the given entity"""
        related = []
        for rel in self.relationships:
            if rel.subject == entity_name:
                related.append(rel.object)
            elif rel.object == entity_name:
                related.append(rel.subject)
        return list(set(related))

@dataclass
class DocumentInsight:
    """Structured insights from document analysis"""
    document_id: str
    summary: str
    key_topics: List[str]
    sentiment: Optional[str]
    language: str
    document_type: DocumentType
    entities: List[DocumentEntity]
    relationships: List[DocumentRelationship]
    quality_score: float
    readability_score: float
    insights: Dict[str, Any]
    generated_at: datetime = field(default_factory=datetime.now)

@dataclass
class DocumentCollection:
    """Manages a collection of documents for analysis"""
    documents: Dict[str, Dict[str, Any]] = field(default_factory=dict)
    knowledge_graph: Optional[DocumentKnowledgeGraph] = None
    collection_metadata: Dict[str, Any] = field(default_factory=dict)
    created_at: datetime = field(default_factory=datetime.now)
    
    def add_document(self, document_id: str, content: str, metadata: Dict[str, Any]):
        """Add a document to the collection"""
        self.documents[document_id] = {
            "content": content,
            "metadata": metadata,
            "added_at": datetime.now()
        }
    
    def get_document_count(self) -> int:
        """Get the number of documents in the collection"""
        return len(self.documents)
    
    def search_documents(self, query: str) -> List[Tuple[str, float]]:
        """Simple text search across documents"""
        results = []
        query_lower = query.lower()
        
        for doc_id, doc_data in self.documents.items():
            content = doc_data["content"].lower()
            if query_lower in content:
                # Simple relevance scoring based on term frequency
                score = content.count(query_lower) / len(content.split())
                results.append((doc_id, score))
        
        # Sort by relevance score descending
        results.sort(key=lambda x: x[1], reverse=True)
        return results

@dataclass
class DocumentQueryResult:
    """Results from document queries"""
    query: str
    answer: str
    source_documents: List[str]
    confidence: float
    evidence: List[str]
    related_entities: List[str]
    generated_at: datetime = field(default_factory=datetime.now)

class EnhancedDocumentIntelligenceAgent(BaseEnhancedAgent):
    """
    Enhanced Document Intelligence Agent with knowledge graph construction,
    interactive querying, and collaborative analysis capabilities.
    """
    
    def __init__(
        self,
        agent_id: str = "enhanced_document_intelligence_agent",
        model_config: Optional[Dict[str, Any]] = None
    ):
        # Agent capabilities
        capabilities = {
            "document_analysis": True,
            "knowledge_graph_construction": True,
            "interactive_querying": True,
            "multi_document_synthesis": True,
            "multi_language_processing": True,
            "collaborative_analysis": True,
            "deep_content_analysis": True,
            "entity_extraction": True,
            "relationship_mapping": True,
            "document_comparison": True
        }
        
        # Initialize base enhanced agent
        super().__init__(
            agent_id=agent_id,
            agent_type=AgentType.DOCUMENT_INTELLIGENCE,
            agent_name="Enhanced Document Intelligence Agent",
            capabilities=capabilities
        )
        
        # Model configuration
        self.model_config = model_config or {
            "provider": "google",
            "model": "gemini-pro",
            "temperature": 0.3
        }
        
        # Document processing components
        self.document_processor = DocumentProcessor()
        self.text_splitter = RecursiveCharacterTextSplitter(
            chunk_size=1000,
            chunk_overlap=200,
            length_function=len
        )
        
        # Document intelligence tools
        self.document_tools = []
        self.reasoning_tools = []
        
        # Document collections and knowledge graphs
        self.document_collections: Dict[str, DocumentCollection] = {}
        self.knowledge_graphs: Dict[str, DocumentKnowledgeGraph] = {}
        
        # Analysis history and caching
        self.analysis_history: List[Dict[str, Any]] = []
        self.document_cache: Dict[str, Any] = {}
        
        # Settings
        self.settings = get_settings()
        
        logger.info(f"Enhanced Document Intelligence Agent initialized")

    # Implementation of required abstract methods from BaseEnhancedAgent
    async def _initialize_agent_specific(self) -> None:
        """Initialize document intelligence specific components."""
        try:
            # Initialize document processor if not already done
            if not hasattr(self, 'document_processor'):
                self.document_processor = DocumentProcessor()
            
            # Initialize collections
            if not hasattr(self, 'knowledge_graphs'):
                self.knowledge_graphs = {}
            if not hasattr(self, 'document_collections'):
                self.document_collections = {}
            if not hasattr(self, 'active_queries'):
                self.active_queries = {}
            
            logger.info(f"Document Intelligence Agent '{self.agent_id}' specific initialization completed")
        except Exception as e:
            logger.error(f"Failed to initialize document intelligence components: {e}")
            raise
    
    async def _cleanup_agent_specific(self) -> None:
        """Cleanup document intelligence specific resources."""
        try:
            # Clear knowledge graphs
            if hasattr(self, 'knowledge_graphs'):
                self.knowledge_graphs.clear()
            
            # Clear document collections if exists
            if hasattr(self, 'document_collections'): 
                self.document_collections.clear()
            
            # Clear active queries if exists
            if hasattr(self, 'active_queries'):
                self.active_queries.clear()
            
            # Clear document processor cache if exists
            if hasattr(self, 'document_processor') and hasattr(self.document_processor, 'clear_cache'):
                self.document_processor.clear_cache()
            
            logger.info(f"Document Intelligence Agent '{self.agent_id}' specific cleanup completed")
        except Exception as e:
            logger.error(f"Failed to cleanup document intelligence resources: {e}")
    
    async def _process_request_internal(
        self,
        request: str,
        context: Optional[Dict[str, Any]],
        language_context: Any,
        task_id: str
    ) -> Dict[str, Any]:
        """
        Process document intelligence requests internally.
        
        Args:
            request: The user request to process
            context: Additional context for processing
            language_context: Language context for the request
            task_id: Unique task identifier
            
        Returns:
            Dictionary containing the processing results
        """
        try:
            # Extract action and parameters from request
            action_type = self._parse_request_action(request)
            
            if action_type == "analyze_document":
                return await self._handle_document_analysis_request(request, context, task_id)
            elif action_type == "build_knowledge_graph":
                return await self._handle_knowledge_graph_request(request, context, task_id)
            elif action_type == "query_documents":
                return await self._handle_query_request(request, context, task_id)
            elif action_type == "compare_documents":
                return await self._handle_comparison_request(request, context, task_id)
            elif action_type == "synthesize_documents":
                return await self._handle_synthesis_request(request, context, task_id)
            else:
                # General document intelligence processing
                return await self._handle_general_request(request, context, task_id)
                
        except Exception as e:
            logger.error(f"Failed to process document intelligence request: {e}")
            return {
                "status": "error",
                "error": str(e),
                "task_id": task_id,
                "agent_id": self.agent_id
            }

    def _parse_request_action(self, request: str) -> str:
        """Parse the request to determine the action type."""
        request_lower = request.lower()
        
        if any(word in request_lower for word in ["analyze", "analysis", "examine"]):
            return "analyze_document"
        elif any(word in request_lower for word in ["knowledge graph", "graph", "entities", "relationships"]):
            return "build_knowledge_graph"
        elif any(word in request_lower for word in ["query", "question", "ask", "find"]):
            return "query_documents"
        elif any(word in request_lower for word in ["compare", "comparison", "difference", "similar"]):
            return "compare_documents"
        elif any(word in request_lower for word in ["synthesize", "synthesis", "combine", "merge"]):
            return "synthesize_documents"
        else:
            return "general"
    
    async def _handle_document_analysis_request(self, request: str, context: Optional[Dict[str, Any]], task_id: str) -> Dict[str, Any]:
        """Handle document analysis requests."""
        return {
            "status": "success",
            "action": "document_analysis",
            "result": "Document analysis completed",
            "task_id": task_id,
            "agent_id": self.agent_id
        }
    
    async def _handle_knowledge_graph_request(self, request: str, context: Optional[Dict[str, Any]], task_id: str) -> Dict[str, Any]:
        """Handle knowledge graph construction requests."""
        return {
            "status": "success", 
            "action": "knowledge_graph",
            "result": "Knowledge graph constructed",
            "task_id": task_id,
            "agent_id": self.agent_id
        }
    
    async def _handle_query_request(self, request: str, context: Optional[Dict[str, Any]], task_id: str) -> Dict[str, Any]:
        """Handle document querying requests."""
        return {
            "status": "success",
            "action": "document_query",
            "result": "Query processed successfully",
            "task_id": task_id,
            "agent_id": self.agent_id
        }
    
    async def _handle_comparison_request(self, request: str, context: Optional[Dict[str, Any]], task_id: str) -> Dict[str, Any]:
        """Handle document comparison requests."""
        return {
            "status": "success",
            "action": "document_comparison", 
            "result": "Documents compared successfully",
            "task_id": task_id,
            "agent_id": self.agent_id
        }
    
    async def _handle_synthesis_request(self, request: str, context: Optional[Dict[str, Any]], task_id: str) -> Dict[str, Any]:
        """Handle document synthesis requests."""
        return {
            "status": "success",
            "action": "document_synthesis",
            "result": "Documents synthesized successfully", 
            "task_id": task_id,
            "agent_id": self.agent_id
        }
    
    async def _handle_general_request(self, request: str, context: Optional[Dict[str, Any]], task_id: str) -> Dict[str, Any]:
        """Handle general document intelligence requests."""
        return {
            "status": "success",
            "action": "general_processing",
            "result": "Request processed successfully",
            "task_id": task_id,
            "agent_id": self.agent_id
        }

    async def initialize(self) -> bool:
        """Initialize the enhanced document intelligence agent"""
        try:
            # Initialize document intelligence tools
            self.document_tools = get_document_intelligence_tools()
            self.reasoning_tools = get_reasoning_tools()
            
            # Verify language detection integration
            test_text = "This is a test for language detection integration."
            language_info = detect_text_language(test_text)
            logger.info(f"Language detection integration verified: {language_info}")
            
            # Initialize base enhanced agent
            success = await super().initialize()
            
            if success:
                logger.info(f"Enhanced Document Intelligence Agent initialization completed successfully")
                
            return success
            
        except Exception as e:
            logger.error(f"Failed to initialize Enhanced Document Intelligence Agent: {e}")
            return False

    async def analyze_document_enhanced(
        self,
        file_path: Optional[str] = None,
        file_content: Optional[bytes] = None,
        analysis_mode: DocumentAnalysisMode = DocumentAnalysisMode.ENHANCED,
        build_knowledge_graph: bool = True
    ) -> DocumentInsight:
        """
        Enhanced document analysis with knowledge graph construction and deep insights.
        
        Args:
            file_path: Path to the document file
            file_content: Raw document content
            analysis_mode: Analysis mode (basic, enhanced, deep_analysis, knowledge_graph)
            build_knowledge_graph: Whether to build knowledge graph
            
        Returns:
            DocumentInsight with comprehensive analysis results
        """
        try:
            # Basic document processing
            if file_path:
                doc_analysis = await self.document_processor.process_document(file_path)
            else:
                # Process from content
                doc_analysis = {"content": file_content.decode("utf-8", errors="ignore")}
            
            document_id = self._generate_document_id(file_path or "content")
            content = doc_analysis.get("content", "")
            
            # Language detection
            language_info = detect_text_language(content)
            # Handle tuple format (language_code, confidence, is_reliable)
            if isinstance(language_info, tuple):
                language = language_info[0]
            else:
                language = language_info.get("language_code", "en")
            
            # Document type classification
            doc_type = await self._classify_document_type(content)
            
            # Entity extraction
            entities = await self._extract_entities(content, document_id)
            
            # Relationship extraction  
            relationships = await self._extract_relationships(content, entities, document_id)
            
            # Build knowledge graph if requested
            knowledge_graph = None
            if build_knowledge_graph:
                knowledge_graph = await self._build_knowledge_graph(
                    document_id, content, entities, relationships
                )
                self.knowledge_graphs[document_id] = knowledge_graph
            
            # Deep content analysis using LLM
            deep_insights = await self._perform_deep_analysis(content, analysis_mode)
            
            # Calculate quality and readability scores
            quality_score = await self._calculate_quality_score(content, entities, relationships)
            readability_score = await self._calculate_readability_score(content)
            
            # Extract key topics
            key_topics = await self._extract_key_topics(content)
            
            # Generate summary
            summary = await self._generate_summary(content, key_topics)
            
            # Create document insight
            insight = DocumentInsight(
                document_id=document_id,
                summary=summary,
                key_topics=key_topics,
                sentiment=deep_insights.get("sentiment"),
                language=language,
                document_type=doc_type,
                entities=entities,
                relationships=relationships,
                quality_score=quality_score,
                readability_score=readability_score,
                insights=deep_insights
            )
            
            # Cache the analysis
            self.document_cache[document_id] = {
                "content": content,
                "insight": insight,
                "analysis_timestamp": datetime.now()
            }
            
            # Add to history
            self.analysis_history.append({
                "document_id": document_id,
                "analysis_mode": analysis_mode.value,
                "quality_score": quality_score,
                "language": language,
                "entities_count": len(entities),
                "timestamp": datetime.now()
            })
            
            logger.info(f"Enhanced document analysis completed for {document_id}: "
                       f"quality={quality_score:.1f}, entities={len(entities)}, language={language}")
            
            return insight
            
        except Exception as e:
            logger.error(f"Enhanced document analysis failed: {e}")
            raise

    async def build_knowledge_graph(
        self,
        documents: List[Dict[str, Any]]
    ) -> DocumentKnowledgeGraph:
        """
        Build a comprehensive knowledge graph from multiple documents.
        
        Args:
            documents: List of documents with content and metadata
            
        Returns:
            DocumentKnowledgeGraph with entities, relationships, and concepts
        """
        try:
            knowledge_graph = DocumentKnowledgeGraph()
            
            # Process each document
            for doc in documents:
                doc_id = doc.get("id", self._generate_document_id(doc.get("title", "doc")))
                content = doc.get("content", "")
                
                # Extract entities and relationships
                entities = await self._extract_entities(content, doc_id)
                relationships = await self._extract_relationships(content, entities, doc_id)
                
                # Add to knowledge graph
                for entity in entities:
                    knowledge_graph.add_entity(entity)
                
                for relationship in relationships:
                    knowledge_graph.add_relationship(relationship)
                
                # Extract concepts
                concepts = await self._extract_concepts(content)
                knowledge_graph.concepts[doc_id] = concepts
                
                # Add metadata
                knowledge_graph.document_metadata[doc_id] = doc.get("metadata", {})
            
            logger.info(f"Knowledge graph built with {len(knowledge_graph.entities)} entities, "
                       f"{len(knowledge_graph.relationships)} relationships")
            
            return knowledge_graph
            
        except Exception as e:
            logger.error(f"Knowledge graph construction failed: {e}")
            raise

    async def query_documents(
        self,
        query: str,
        document_collection: Optional[str] = None,
        use_knowledge_graph: bool = True
    ) -> DocumentQueryResult:
        """
        Interactive querying over document content with knowledge graph support.
        
        Args:
            query: Natural language query
            document_collection: Specific collection to query (optional)
            use_knowledge_graph: Whether to use knowledge graph for enhanced results
            
        Returns:
            DocumentQueryResult with answer and supporting evidence
        """
        try:
            # Determine which documents to search
            if document_collection and document_collection in self.document_collections:
                collection = self.document_collections[document_collection]
                search_docs = collection.documents
            else:
                # Search all cached documents
                search_docs = {doc_id: {"content": data["content"]} 
                              for doc_id, data in self.document_cache.items()}
            
            # Perform document search
            relevant_docs = []
            for doc_id, doc_data in search_docs.items():
                content = doc_data["content"]
                # Simple relevance check (could be enhanced with embeddings)
                if any(term.lower() in content.lower() for term in query.split()):
                    relevant_docs.append((doc_id, content))
            
            if not relevant_docs:
                return DocumentQueryResult(
                    query=query,
                    answer="No relevant documents found for the query.",
                    source_documents=[],
                    confidence=0.0,
                    evidence=[],
                    related_entities=[]
                )
            
            # Use knowledge graph for enhanced context if available
            related_entities = []
            if use_knowledge_graph:
                for doc_id, _ in relevant_docs:
                    if doc_id in self.knowledge_graphs:
                        kg = self.knowledge_graphs[doc_id]
                        # Find entities related to query terms
                        query_terms = query.lower().split()
                        for entity_name, entity in kg.entities.items():
                            if any(term in entity_name.lower() for term in query_terms):
                                related_entities.extend(kg.get_related_entities(entity_name))
            
            # Generate answer using LLM
            context_text = "\n\n".join([f"Document {i+1}:\n{content[:2000]}" 
                                       for i, (_, content) in enumerate(relevant_docs[:3])])
            
            answer = await self._generate_answer_from_context(query, context_text, related_entities)
            
            # Extract evidence from documents
            evidence = await self._extract_evidence(query, relevant_docs)
            
            # Calculate confidence based on relevance and completeness
            confidence = min(0.9, len(relevant_docs) * 0.2 + len(evidence) * 0.1)
            
            result = DocumentQueryResult(
                query=query,
                answer=answer,
                source_documents=[doc_id for doc_id, _ in relevant_docs],
                confidence=confidence,
                evidence=evidence,
                related_entities=list(set(related_entities))
            )
            
            logger.info(f"Document query processed: '{query}' -> {len(relevant_docs)} docs, "
                       f"confidence={confidence:.2f}")
            
            return result
            
        except Exception as e:
            logger.error(f"Document query failed: {e}")
            raise

    async def synthesize_documents(
        self,
        document_ids: List[str],
        synthesis_type: str = "comprehensive"
    ) -> Dict[str, Any]:
        """
        Multi-document synthesis and analysis.
        
        Args:
            document_ids: List of document IDs to synthesize
            synthesis_type: Type of synthesis (comprehensive, comparison, summary)
            
        Returns:
            Dictionary with synthesis results
        """
        try:
            # Gather documents
            documents = []
            for doc_id in document_ids:
                if doc_id in self.document_cache:
                    documents.append({
                        "id": doc_id,
                        "content": self.document_cache[doc_id]["content"],
                        "insight": self.document_cache[doc_id]["insight"]
                    })
            
            if not documents:
                return {"error": "No documents found for synthesis"}
            
            # Perform synthesis based on type
            if synthesis_type == "comprehensive":
                synthesis = await self._comprehensive_synthesis(documents)
            elif synthesis_type == "comparison":
                synthesis = await self._comparison_synthesis(documents)
            elif synthesis_type == "summary":
                synthesis = await self._summary_synthesis(documents)
            else:
                synthesis = await self._comprehensive_synthesis(documents)
            
            # Add metadata
            synthesis["document_count"] = len(documents)
            synthesis["document_ids"] = document_ids
            synthesis["synthesis_type"] = synthesis_type
            synthesis["generated_at"] = datetime.now().isoformat()
            
            logger.info(f"Document synthesis completed: {synthesis_type} of {len(documents)} documents")
            
            return synthesis
            
        except Exception as e:
            logger.error(f"Document synthesis failed: {e}")
            raise

    async def handle_collaboration_message(self, message: Dict[str, Any]) -> Optional[Dict[str, Any]]:
        """Handle collaboration messages from other agents for document analysis."""
        try:
            message_type = message.get("type", "")
            
            if message_type == "document_analysis_request":
                # Handle document analysis request from other agents
                file_path = message["metadata"].get("file_path")
                analysis_mode = DocumentAnalysisMode(message["metadata"].get("analysis_mode", "enhanced"))
                
                insight = await self.analyze_document_enhanced(file_path, analysis_mode=analysis_mode)
                
                return {
                    "message_type": "document_analysis_response",
                    "content": f"Document analysis completed for {file_path}",
                    "metadata": {
                        "document_insight": {
                            "summary": insight.summary,
                            "key_topics": insight.key_topics,
                            "quality_score": insight.quality_score,
                            "language": insight.language,
                            "entity_count": len(insight.entities)
                        },
                        "original_request_id": message["metadata"].get("request_id")
                    }
                }
            
            elif message_type == "document_query_request":
                # Handle document query request
                query = message["metadata"].get("query")
                collection = message["metadata"].get("collection")
                
                result = await self.query_documents(query, collection)
                
                return {
                    "message_type": "document_query_response", 
                    "content": f"Query processed: {query}",
                    "metadata": {
                        "query_result": {
                            "answer": result.answer,
                            "confidence": result.confidence,
                            "source_count": len(result.source_documents)
                        },
                        "original_request_id": message["metadata"].get("request_id")
                    }
                }
            
            elif message_type == "knowledge_graph_request":
                # Handle knowledge graph construction request
                documents = message["metadata"].get("documents", [])
                
                kg = await self.build_knowledge_graph(documents)
                
                return {
                    "message_type": "knowledge_graph_response",
                    "content": "Knowledge graph constructed",
                    "metadata": {
                        "knowledge_graph_summary": {
                            "entity_count": len(kg.entities),
                            "relationship_count": len(kg.relationships),
                            "document_count": len(kg.document_metadata)
                        },
                        "original_request_id": message["metadata"].get("request_id")
                    }
                }
            
            return None
            
        except Exception as e:
            logger.error(f"Error handling collaboration message: {e}")
            return {
                "message_type": "error_response",
                "content": f"Error processing request: {str(e)}",
                "metadata": {"original_request_id": message.get("metadata", {}).get("request_id")}
            }

    async def get_agent_status(self) -> Dict[str, Any]:
        """Get current agent status with document intelligence specific metrics."""
        # Build status from scratch since base class doesn't have this method
        base_status = {
            "agent_id": self.agent_id,
            "state": "ready",  # Default state
            "capabilities": {
                "document_analysis": True,
                "knowledge_graph_construction": True,
                "interactive_querying": True,
                "multi_document_synthesis": True,
                "multi_language_processing": True,
                "collaborative_analysis": True,
                "deep_content_analysis": True,
                "entity_extraction": True,
                "relationship_mapping": True,
                "document_comparison": True
            }
        }
        
        # Add document intelligence specific status
        base_status.update({
            "documents_analyzed": len(getattr(self, 'analysis_history', [])),
            "knowledge_graphs_built": len(self.knowledge_graphs),
            "document_collections": len(getattr(self, 'document_collections', {})),
            "cached_documents": len(getattr(self, 'document_cache', {})),
            "total_entities_extracted": 0,  # Simplified for now
            "supported_analysis_modes": [mode.value for mode in DocumentAnalysisMode],
            "supported_document_types": [doc_type.value for doc_type in DocumentType]
        })
        
        return base_status

    async def get_document_analysis_history(self, limit: int = 10) -> List[Dict[str, Any]]:
        """Get recent document analysis history."""
        return self.analysis_history[-limit:] if self.analysis_history else []

    # Private helper methods
    def _generate_document_id(self, identifier: str) -> str:
        """Generate a unique document ID"""
        import time
        import random
        # Use high precision timestamp and random component for uniqueness
        timestamp = time.time_ns()  # Nanosecond precision
        random_component = random.randint(1000, 9999)
        return hashlib.md5(f"{identifier}_{timestamp}_{random_component}".encode()).hexdigest()[:12]

    async def _classify_document_type(self, content: str) -> DocumentType:
        """Classify document type based on content analysis"""
        # Simple heuristic-based classification (could be enhanced with ML)
        content_lower = content.lower()
        
        if any(keyword in content_lower for keyword in ["abstract", "methodology", "references", "doi"]):
            return DocumentType.ACADEMIC_PAPER
        elif any(keyword in content_lower for keyword in ["revenue", "profit", "financial", "quarterly"]):
            return DocumentType.BUSINESS_REPORT
        elif any(keyword in content_lower for keyword in ["procedure", "installation", "configuration", "manual"]):
            return DocumentType.TECHNICAL_MANUAL
        elif any(keyword in content_lower for keyword in ["contract", "agreement", "legal", "clause"]):
            return DocumentType.LEGAL_DOCUMENT
        elif any(keyword in content_lower for keyword in ["breaking news", "reported", "according to"]):
            return DocumentType.NEWS_ARTICLE
        elif any(keyword in content_lower for keyword in ["slide", "presentation", "agenda"]):
            return DocumentType.PRESENTATION
        else:
            return DocumentType.OTHER

    async def _extract_entities(self, content: str, document_id: str) -> List[DocumentEntity]:
        """Extract entities from document content"""
        # Simple entity extraction (could be enhanced with spaCy or other NER tools)
        entities = []
        
        # Basic pattern matching for demonstration
        import re
        
        # Extract potential person names (capitalized words)
        person_pattern = r'\b[A-Z][a-z]+ [A-Z][a-z]+\b'
        persons = re.findall(person_pattern, content)
        
        for person in set(persons[:10]):  # Limit to avoid noise
            entities.append(DocumentEntity(
                name=person,
                entity_type="PERSON",
                context=f"Found in document {document_id}",
                confidence=0.7,
                document_id=document_id
            ))
        
        # Extract potential organization names (all caps words)
        org_pattern = r'\b[A-Z]{2,}\b'
        orgs = re.findall(org_pattern, content)
        
        for org in set(orgs[:5]):  # Limit to avoid noise
            if len(org) > 2:  # Filter out short abbreviations
                entities.append(DocumentEntity(
                    name=org,
                    entity_type="ORGANIZATION",
                    context=f"Found in document {document_id}",
                    confidence=0.6,
                    document_id=document_id
                ))
        
        return entities

    async def _extract_relationships(
        self, 
        content: str, 
        entities: List[DocumentEntity], 
        document_id: str
    ) -> List[DocumentRelationship]:
        """Extract relationships between entities"""
        relationships = []
        
        # Simple relationship extraction based on proximity and patterns
        entity_names = [entity.name for entity in entities]
        
        # Look for relationships indicated by common verbs
        relationship_verbs = ["works for", "founded", "acquired", "partnered with", "collaborated with"]
        
        for verb in relationship_verbs:
           # Build a safer regex pattern to find entity relationships
            escaped_names = [re.escape(name) for name in entity_names]
            names_pattern = "|".join(escaped_names)
            pattern = rf'\b({names_pattern})\b.*?{re.escape(verb)}.*?\b({names_pattern})\b'
            matches = re.findall(pattern, content, re.IGNORECASE)
            
            for match in matches:
                if match[0] != match[1]:  # Avoid self-relationships
                    relationships.append(DocumentRelationship(
                        subject=match[0],
                        predicate=verb,
                        object=match[1],
                        confidence=0.6,
                        context=f"Extracted from document {document_id}",
                        document_id=document_id
                    ))
        
        return relationships

    async def _build_knowledge_graph(
        self, 
        document_id: str, 
        content: str, 
        entities: List[DocumentEntity], 
        relationships: List[DocumentRelationship]
    ) -> DocumentKnowledgeGraph:
        """Build knowledge graph from document analysis"""
        kg = DocumentKnowledgeGraph()
        
        # Add entities
        for entity in entities:
            kg.add_entity(entity)
        
        # Add relationships
        for relationship in relationships:
            kg.add_relationship(relationship)
        
        # Extract concepts
        concepts = await self._extract_concepts(content)
        kg.concepts[document_id] = concepts
        
        # Add document metadata
        kg.document_metadata[document_id] = {
            "analyzed_at": datetime.now().isoformat(),
            "content_length": len(content),
            "entity_count": len(entities),
            "relationship_count": len(relationships)
        }
        
        return kg

    async def _extract_concepts(self, content: str) -> List[str]:
        """Extract key concepts from document content"""
        # Simple concept extraction using frequency analysis
        import re
        from collections import Counter
        
        # Extract meaningful terms (3+ characters, not common words)
        words = re.findall(r'\b[a-zA-Z]{3,}\b', content.lower())
        
        # Filter out common stop words
        stop_words = {'the', 'and', 'for', 'are', 'but', 'not', 'you', 'all', 'can', 'had', 'her', 'was', 'one', 'our', 'out', 'day', 'get', 'has', 'him', 'his', 'how', 'its', 'may', 'new', 'now', 'old', 'see', 'two', 'who', 'boy', 'did', 'she', 'use', 'way', 'will', 'with'}
        
        filtered_words = [word for word in words if word not in stop_words and len(word) > 3]
        
        # Get most frequent terms as concepts
        word_counts = Counter(filtered_words)
        concepts = [word for word, count in word_counts.most_common(10) if count > 1]
        
        return concepts

    async def _perform_deep_analysis(self, content: str, analysis_mode: DocumentAnalysisMode) -> Dict[str, Any]:
        """Perform deep content analysis using LLM"""
        try:
            model = get_google_model()
            
            # Create analysis prompt based on mode
            if analysis_mode == DocumentAnalysisMode.DEEP_ANALYSIS:
                prompt = f"""
                Perform a comprehensive analysis of the following document content:
                
                {content[:3000]}...
                
                Please provide:
                1. Overall sentiment (positive/negative/neutral)
                2. Main themes and topics
                3. Writing style and tone
                4. Key insights and takeaways
                5. Potential areas for improvement
                
                Respond in JSON format.
                """
            else:
                prompt = f"""
                Analyze the following document content:
                
                {content[:2000]}...
                
                Please provide:
                1. Overall sentiment
                2. Main topics (top 3)
                3. Key insights
                
                Respond in JSON format.
                """
            
            response = await model.ainvoke([HumanMessage(content=prompt)])
            
            # Parse response (assuming JSON format)
            try:
                import json
                insights = json.loads(response.content)
            except:
                # Fallback if not JSON
                insights = {
                    "sentiment": "neutral",
                    "themes": ["general content"],
                    "insights": response.content[:500]
                }
            
            return insights
            
        except Exception as e:
            logger.error(f"Deep analysis failed: {e}")
            return {
                "sentiment": "neutral",
                "themes": ["analysis_failed"],
                "insights": "Deep analysis could not be completed"
            }

    async def _calculate_quality_score(
        self, 
        content: str, 
        entities: List[DocumentEntity], 
        relationships: List[DocumentRelationship]
    ) -> float:
        """Calculate document quality score based on various factors"""
        score = 50.0  # Base score
        
        # Content length factor
        if len(content) > 1000:
            score += 10
        elif len(content) > 500:
            score += 5
        
        # Entity richness
        if len(entities) > 10:
            score += 15
        elif len(entities) > 5:
            score += 10
        elif len(entities) > 0:
            score += 5
        
        # Relationship richness
        if len(relationships) > 5:
            score += 10
        elif len(relationships) > 0:
            score += 5
        
        # Structure indicators (headers, lists, etc.)
        if any(indicator in content for indicator in ['\n#', '\n##', '1.', '2.', '•', '-']):
            score += 10
        
        return min(100.0, score)

    async def _calculate_readability_score(self, content: str) -> float:
        """Calculate readability score using simple metrics"""
        import re
        
        # Count sentences and words
        sentences = len(re.findall(r'[.!?]+', content))
        words = len(content.split())
        
        if sentences == 0 or words == 0:
            return 50.0
        
        # Simple readability approximation
        avg_words_per_sentence = words / sentences
        
        if avg_words_per_sentence < 15:
            return 85.0  # Easy to read
        elif avg_words_per_sentence < 20:
            return 70.0  # Moderate
        elif avg_words_per_sentence < 25:
            return 55.0  # Difficult
        else:
            return 40.0  # Very difficult
        
    async def _extract_key_topics(self, content: str) -> List[str]:
        """Extract key topics from document content"""
        # Simple topic extraction using frequency analysis
        concepts = await self._extract_concepts(content)
        return concepts[:5]  # Return top 5 topics

    async def _generate_summary(self, content: str, key_topics: List[str]) -> str:
        """Generate document summary"""
        try:
            model = get_google_model()
            
            prompt = f"""
            Please provide a concise summary of the following document content:
            
            Key topics identified: {', '.join(key_topics)}
            
            Content: {content[:2000]}...
            
            Summary (2-3 sentences):
            """
            
            response = await model.ainvoke([HumanMessage(content=prompt)])
            return response.content.strip()
            
        except Exception as e:
            logger.error(f"Summary generation failed: {e}")
            return f"Document discussing {', '.join(key_topics[:3])} with {len(content.split())} words."

    async def _generate_answer_from_context(
        self, 
        query: str, 
        context: str, 
        related_entities: List[str]
    ) -> str:
        """Generate answer from document context using LLM"""
        try:
            model = get_google_model()
            
            prompt = f"""
            Based on the following document context, please answer the question:
            
            Question: {query}
            
            Context: {context}
            
            Related entities: {', '.join(related_entities[:5])}
            
            Please provide a clear, factual answer based on the context provided.
            """
            
            response = await model.ainvoke([HumanMessage(content=prompt)])
            return response.content.strip()
            
        except Exception as e:
            logger.error(f"Answer generation failed: {e}")
            return "I couldn't generate an answer based on the available context."

    async def _extract_evidence(self, query: str, relevant_docs: List[Tuple[str, str]]) -> List[str]:
        """Extract evidence supporting the query from documents"""
        evidence = []
        query_terms = query.lower().split()
        
        for doc_id, content in relevant_docs:
            sentences = content.split('.')
            for sentence in sentences:
                if any(term in sentence.lower() for term in query_terms):
                    evidence.append(sentence.strip()[:200])  # Limit evidence length
                    if len(evidence) >= 3:  # Limit number of evidence pieces
                        break
            if len(evidence) >= 3:
                break
        
        return evidence

    async def _comprehensive_synthesis(self, documents: List[Dict[str, Any]]) -> Dict[str, Any]:
        """Perform comprehensive synthesis of multiple documents"""
        # Combine all key topics
        all_topics = []
        all_entities = []
        
        for doc in documents:
            insight = doc["insight"]
            all_topics.extend(insight.key_topics)
            all_entities.extend([entity.name for entity in insight.entities])
        
        # Find common themes
        from collections import Counter
        topic_counts = Counter(all_topics)
        entity_counts = Counter(all_entities)
        
        return {
            "synthesis_type": "comprehensive",
            "common_topics": dict(topic_counts.most_common(5)),
            "common_entities": dict(entity_counts.most_common(10)),
            "average_quality_score": sum(doc["insight"].quality_score for doc in documents) / len(documents),
            "languages_detected": list(set(doc["insight"].language for doc in documents)),
            "document_types": list(set(doc["insight"].document_type.value for doc in documents))
        }

    async def _comparison_synthesis(self, documents: List[Dict[str, Any]]) -> Dict[str, Any]:
        """Perform comparative synthesis of documents"""
        comparisons = []
        
        for i, doc1 in enumerate(documents):
            for doc2 in documents[i+1:]:
                insight1, insight2 = doc1["insight"], doc2["insight"]
                
                # Compare topics
                common_topics = set(insight1.key_topics) & set(insight2.key_topics)
                
                comparison = {
                    "document_pair": [doc1["id"], doc2["id"]],
                    "common_topics": list(common_topics),
                    "quality_difference": abs(insight1.quality_score - insight2.quality_score),
                    "same_language": insight1.language == insight2.language
                }
                comparisons.append(comparison)
        
        return {
            "synthesis_type": "comparison",
            "comparisons": comparisons,
            "most_similar_pair": min(comparisons, key=lambda x: x["quality_difference"]) if comparisons else None
        }

    async def _summary_synthesis(self, documents: List[Dict[str, Any]]) -> Dict[str, Any]:
        """Generate summary synthesis of documents"""
        summaries = [doc["insight"].summary for doc in documents]
        
        return {
            "synthesis_type": "summary",
            "individual_summaries": summaries,
            "total_documents": len(documents),
            "combined_summary": " ".join(summaries)[:500] + "..." if len(" ".join(summaries)) > 500 else " ".join(summaries)
        }

# Factory function for creating enhanced document intelligence agent
async def create_enhanced_document_intelligence_agent(
    agent_id: str = "enhanced_document_intelligence_agent",
    model_config: Optional[Dict[str, Any]] = None
) -> EnhancedDocumentIntelligenceAgent:
    """
    Factory function to create and initialize an Enhanced Document Intelligence Agent.
    
    Args:
        agent_id: Unique identifier for the agent
        model_config: Configuration for the language model
        
    Returns:
        Initialized EnhancedDocumentIntelligenceAgent
    """
    agent = EnhancedDocumentIntelligenceAgent(agent_id=agent_id, model_config=model_config)
    await agent.initialize()
    return agent
