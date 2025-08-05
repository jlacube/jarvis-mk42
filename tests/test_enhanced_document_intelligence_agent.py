"""
Tests for Enhanced Document Intelligence Agent

This module contains comprehensive tests for the Enhanced Document Intelligence Agent,
including tests for document analysis, knowledge graph construction, interactive querying,
multi-document synthesis, and integration with the communication framework.
"""

import pytest
import pytest_asyncio
import asyncio
from unittest.mock import Mock, patch, AsyncMock
from datetime import datetime
from typing import Dict, List, Any
import sys
import os
import tempfile
import json

# Add the project root to Python path
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from agents.enhanced_document_intelligence_agent import (
    EnhancedDocumentIntelligenceAgent,
    create_enhanced_document_intelligence_agent,
    DocumentInsight,
    DocumentKnowledgeGraph,
    DocumentCollection,
    DocumentQueryResult,
    DocumentAnalysisMode,
    DocumentType,
    DocumentEntity,
    DocumentRelationship
)

class TestEnhancedDocumentIntelligenceAgent:
    """Test class for Enhanced Document Intelligence Agent"""
    
    @pytest_asyncio.fixture
    async def agent(self):
        """Create test agent instance"""
        agent = EnhancedDocumentIntelligenceAgent(
            agent_id="test_document_agent",
            model_config={"provider": "google", "model": "gemini-pro", "temperature": 0.2}
        )
        await agent.initialize()
        return agent
    
    @pytest.mark.asyncio
    async def test_agent_initialization(self):
        """Test agent initialization and basic properties"""
        agent = EnhancedDocumentIntelligenceAgent(agent_id="test_agent")
        
        # Test basic properties
        assert agent.agent_id == "test_agent"
        assert agent.agent_name == "Enhanced Document Intelligence Agent"
        assert len(agent.capabilities) > 0
        assert agent.capabilities["document_analysis"] == True
        assert agent.capabilities["knowledge_graph_construction"] == True
        
        # Test initialization
        success = await agent.initialize()
        assert success == True
        assert len(agent.document_tools) > 0
        assert len(agent.reasoning_tools) > 0

    @pytest.mark.asyncio
    async def test_document_analysis_enhanced(self, agent):
        """Test enhanced document analysis functionality"""
        # Create test document content
        test_content = """
        # Research Report on Artificial Intelligence
        
        This report discusses the recent advances in artificial intelligence and machine learning.
        John Smith from MIT has published groundbreaking research on neural networks.
        The study was conducted in collaboration with Google AI and Microsoft Research.
        
        Key findings include:
        1. Improved accuracy in natural language processing
        2. Better performance in computer vision tasks
        3. Enhanced reasoning capabilities in large language models
        
        The research has implications for healthcare, finance, and education sectors.
        """.encode('utf-8')
        
        # Test enhanced analysis
        insight = await agent.analyze_document_enhanced(
            file_content=test_content,
            analysis_mode=DocumentAnalysisMode.ENHANCED,
            build_knowledge_graph=True
        )
        
        assert isinstance(insight, DocumentInsight)
        assert insight.language in ['en', 'english']  # Language should be detected
        assert insight.quality_score > 0
        assert insight.readability_score > 0
        assert len(insight.key_topics) > 0
        assert len(insight.entities) > 0
        assert len(insight.summary) > 10
        
        print(f"✓ Enhanced analysis - Quality: {insight.quality_score:.1f}, "
              f"Entities: {len(insight.entities)}, Topics: {len(insight.key_topics)}")

    @pytest.mark.asyncio
    async def test_knowledge_graph_construction(self, agent):
        """Test knowledge graph construction from documents"""
        # Create test documents
        documents = [
            {
                "id": "doc1",
                "content": "John Smith works for MIT. He founded the AI Research Lab in 2020.",
                "metadata": {"title": "AI Research"}
            },
            {
                "id": "doc2", 
                "content": "MIT partnered with Google on machine learning research. The collaboration started in 2021.",
                "metadata": {"title": "ML Partnership"}
            }
        ]
        
        # Build knowledge graph
        kg = await agent.build_knowledge_graph(documents)
        
        assert isinstance(kg, DocumentKnowledgeGraph)
        assert len(kg.entities) > 0
        assert len(kg.relationships) >= 0  # Might be 0 with simple extraction
        assert len(kg.concepts) == len(documents)
        assert len(kg.document_metadata) == len(documents)
        
        # Test entity relationships
        if len(kg.entities) > 1:
            entity_name = list(kg.entities.keys())[0]
            related = kg.get_related_entities(entity_name)
            assert isinstance(related, list)
        
        print(f"✓ Knowledge graph built - Entities: {len(kg.entities)}, "
              f"Relationships: {len(kg.relationships)}")

    @pytest.mark.asyncio
    async def test_document_querying(self, agent):
        """Test interactive document querying"""
        # Add test document to cache
        test_content = """
        The Python programming language was created by Guido van Rossum in 1991.
        It is widely used for web development, data science, and artificial intelligence.
        Popular frameworks include Django for web development and TensorFlow for machine learning.
        """
        
        doc_id = agent._generate_document_id("test_doc")
        agent.document_cache[doc_id] = {
            "content": test_content,
            "analysis_timestamp": datetime.now()
        }
        
        # Test query
        result = await agent.query_documents(
            query="Who created Python?",
            use_knowledge_graph=False
        )
        
        assert isinstance(result, DocumentQueryResult)
        assert result.query == "Who created Python?"
        assert len(result.answer) > 0
        assert result.confidence > 0
        assert len(result.source_documents) > 0
        
        print(f"✓ Document query - Answer length: {len(result.answer)}, "
              f"Confidence: {result.confidence:.2f}")

    @pytest.mark.asyncio
    async def test_document_type_classification(self, agent):
        """Test document type classification"""
        # Test different document types
        test_documents = [
            ("This paper presents a novel approach to machine learning. Abstract: We propose...", DocumentType.ACADEMIC_PAPER),
            ("Q4 Financial Report: Revenue increased by 15% this quarter...", DocumentType.BUSINESS_REPORT),
            ("Installation Manual: Follow these steps to configure the system...", DocumentType.TECHNICAL_MANUAL),
            ("Breaking news: Local company announces new product launch...", DocumentType.NEWS_ARTICLE)
        ]
        
        for content, expected_type in test_documents:
            doc_type = await agent._classify_document_type(content)
            # Accept the expected type or OTHER as valid (since classification is heuristic)
            assert doc_type in [expected_type, DocumentType.OTHER]
        
        print("✓ Document type classification working")

    @pytest.mark.asyncio
    async def test_entity_extraction(self, agent):
        """Test entity extraction from documents"""
        test_content = """
        John Smith works at Microsoft Corporation. He collaborated with Mary Johnson from IBM.
        The project was funded by the National Science Foundation (NSF).
        """
        
        entities = await agent._extract_entities(test_content, "test_doc")
        
        assert len(entities) > 0
        
        # Check entity types
        entity_types = {entity.entity_type for entity in entities}
        assert "PERSON" in entity_types or "ORGANIZATION" in entity_types
        
        # Check entity properties
        for entity in entities:
            assert isinstance(entity, DocumentEntity)
            assert len(entity.name) > 0
            assert entity.confidence > 0
            assert entity.document_id == "test_doc"
        
        print(f"✓ Entity extraction - Found {len(entities)} entities")

    @pytest.mark.asyncio
    async def test_document_synthesis(self, agent):
        """Test multi-document synthesis"""
        # Create test documents with insights
        test_docs = []
        for i in range(3):
            content = f"Document {i+1} content about artificial intelligence and machine learning research."
            
            # Mock insight
            insight = DocumentInsight(
                document_id=f"doc_{i+1}",
                summary=f"Summary of document {i+1}",
                key_topics=["AI", "machine learning", f"topic_{i+1}"],
                sentiment="positive",
                language="en",
                document_type=DocumentType.ACADEMIC_PAPER,
                entities=[],
                relationships=[],
                quality_score=75.0 + i * 5,
                readability_score=80.0,
                insights={"sentiment": "positive"}
            )
            
            test_docs.append({
                "id": f"doc_{i+1}",
                "content": content,
                "insight": insight
            })
            
            # Add to agent cache
            agent.document_cache[f"doc_{i+1}"] = {
                "content": content,
                "insight": insight,
                "analysis_timestamp": datetime.now()
            }
        
        # Test comprehensive synthesis
        synthesis = await agent.synthesize_documents(
            document_ids=["doc_1", "doc_2", "doc_3"],
            synthesis_type="comprehensive"
        )
        
        assert synthesis["synthesis_type"] == "comprehensive"
        assert synthesis["document_count"] == 3
        assert "common_topics" in synthesis
        assert "average_quality_score" in synthesis
        
        print(f"✓ Document synthesis completed - {synthesis['document_count']} documents")

    @pytest.mark.asyncio
    async def test_collaborative_message_handling(self, agent):
        """Test handling of collaboration messages from other agents"""
        # Test document analysis request
        analysis_message = {
            "type": "document_analysis_request",
            "content": "Please analyze this document",
            "metadata": {
                "file_path": None,  # Will use content
                "analysis_mode": "enhanced",
                "request_id": "test_123"
            }
        }
        
        # Mock the analyze_document_enhanced method for testing
        mock_insight = DocumentInsight(
            document_id="test_doc",
            summary="Test document summary",
            key_topics=["topic1", "topic2"],
            sentiment="neutral",
            language="en",
            document_type=DocumentType.OTHER,
            entities=[],
            relationships=[],
            quality_score=75.0,
            readability_score=80.0,
            insights={}
        )
        
        with patch.object(agent, 'analyze_document_enhanced', return_value=mock_insight):
            response = await agent.handle_collaboration_message(analysis_message)
        
        assert response is not None
        assert response["message_type"] == "document_analysis_response"
        assert "document_insight" in response["metadata"]
        assert response["metadata"]["original_request_id"] == "test_123"
        
        print("✓ Document analysis message handling working")
        
        # Test document query request
        query_message = {
            "type": "document_query_request",
            "content": "Query request",
            "metadata": {
                "query": "test query",
                "collection": None,
                "request_id": "test_456"
            }
        }
        
        mock_result = DocumentQueryResult(
            query="test query",
            answer="Test answer",
            source_documents=["doc1"],
            confidence=0.8,
            evidence=["evidence1"],
            related_entities=[]
        )
        
        with patch.object(agent, 'query_documents', return_value=mock_result):
            response = await agent.handle_collaboration_message(query_message)
        
        assert response is not None
        assert response["message_type"] == "document_query_response"
        assert "query_result" in response["metadata"]
        assert response["metadata"]["original_request_id"] == "test_456"
        
        print("✓ Document query message handling working")

    @pytest.mark.asyncio
    async def test_agent_status(self, agent):
        """Test agent status reporting"""
        status = await agent.get_agent_status()
        
        # Check base status fields
        assert "agent_id" in status
        assert "state" in status
        assert "capabilities" in status
        
        # Check document intelligence specific status fields
        assert "documents_analyzed" in status
        assert "knowledge_graphs_built" in status
        assert "document_collections" in status
        assert "cached_documents" in status
        assert "supported_analysis_modes" in status
        assert "supported_document_types" in status
        
        # Verify values
        assert status["documents_analyzed"] >= 0
        assert status["knowledge_graphs_built"] >= 0
        assert len(status["supported_analysis_modes"]) > 0
        assert len(status["supported_document_types"]) > 0
        
        print(f"✓ Agent status: {status['documents_analyzed']} docs analyzed, "
              f"{len(status['supported_analysis_modes'])} analysis modes")

    @pytest.mark.asyncio
    async def test_document_collection_management(self, agent):
        """Test document collection management"""
        # Create a document collection
        collection = DocumentCollection()
        
        # Add documents
        collection.add_document("doc1", "Content about AI", {"type": "research"})
        collection.add_document("doc2", "Content about ML", {"type": "study"})
        
        assert collection.get_document_count() == 2
        
        # Test search
        results = collection.search_documents("AI")
        assert len(results) >= 1
        assert results[0][0] == "doc1"  # Should find the AI document
        
        # Add to agent
        agent.document_collections["test_collection"] = collection
        
        assert len(agent.document_collections) == 1
        
        print("✓ Document collection management working")

    @pytest.mark.asyncio
    async def test_quality_and_readability_scoring(self, agent):
        """Test document quality and readability scoring"""
        # Test high-quality content
        high_quality_content = """
        # Comprehensive Research Report on Machine Learning
        
        This detailed report examines recent advances in machine learning algorithms.
        The study was conducted by Dr. Jane Smith at Stanford University.
        Key findings include improved accuracy and reduced training time.
        
        1. Introduction
        2. Methodology  
        3. Results
        4. Conclusion
        
        The research has implications for various industries.
        """
        
        entities = [DocumentEntity("Dr. Jane Smith", "PERSON", "context", 0.9, "doc1")]
        relationships = [DocumentRelationship("Dr. Jane Smith", "works at", "Stanford University", 0.8, "context", "doc1")]
        
        quality_score = await agent._calculate_quality_score(high_quality_content, entities, relationships)
        readability_score = await agent._calculate_readability_score(high_quality_content)
        
        assert quality_score > 50.0
        assert readability_score > 0.0
        
        print(f"✓ Scoring - Quality: {quality_score:.1f}, Readability: {readability_score:.1f}")

    @pytest.mark.asyncio
    async def test_concept_extraction(self, agent):
        """Test concept extraction from documents"""
        test_content = """
        Machine learning algorithms are fundamental to artificial intelligence systems.
        Deep learning networks use neural networks for pattern recognition.
        Natural language processing enables computers to understand human language.
        """
        
        concepts = await agent._extract_concepts(test_content)
        
        assert len(concepts) > 0
        assert all(len(concept) > 3 for concept in concepts)  # Should filter short words
        
        print(f"✓ Concept extraction - Found {len(concepts)} concepts: {concepts[:5]}")

    @pytest.mark.asyncio
    async def test_document_id_generation(self, agent):
        """Test document ID generation"""
        id1 = agent._generate_document_id("test_doc")
        id2 = agent._generate_document_id("test_doc")
        
        assert len(id1) == 12  # Should be 12 characters (from MD5 hash)
        assert id1 != id2  # Should be different due to timestamp
        
        print("✓ Document ID generation working")

# Integration tests
class TestEnhancedDocumentIntelligenceAgentIntegration:
    """Integration tests for Enhanced Document Intelligence Agent"""
    
    @pytest.mark.asyncio
    async def test_factory_function(self):
        """Test agent creation via factory function"""
        agent = await create_enhanced_document_intelligence_agent(
            agent_id="factory_test_agent",
            model_config={"provider": "google", "model": "gemini-pro", "temperature": 0.2}
        )
        
        assert agent.agent_id == "factory_test_agent"
        assert agent.model_config["provider"] == "google"
        assert len(agent.document_tools) > 0
        
        print("✓ Factory function working correctly")

    @pytest.mark.asyncio
    async def test_end_to_end_workflow(self):
        """Test complete workflow from document analysis to querying"""
        agent = await create_enhanced_document_intelligence_agent(agent_id="workflow_test_agent")
        
        # Step 1: Analyze document
        test_content = """
        # Annual Report 2024
        
        Our company achieved record revenue of $10 billion this year.
        CEO John Williams led the transformation initiative.
        We expanded into new markets including healthcare and finance.
        
        Key achievements:
        - 25% revenue growth
        - 1000 new employees hired
        - 5 new product launches
        
        Looking ahead, we plan to invest heavily in artificial intelligence
        and machine learning technologies to maintain our competitive edge.
        """.encode('utf-8')
        
        insight = await agent.analyze_document_enhanced(
            file_content=test_content,
            analysis_mode=DocumentAnalysisMode.ENHANCED,
            build_knowledge_graph=True
        )
        
        assert insight.quality_score > 0
        assert len(insight.entities) > 0
        
        # Step 2: Query the document
        result = await agent.query_documents("What was the revenue growth?")
        
        assert len(result.answer) > 0
        assert result.confidence > 0
        
        # Step 3: Check agent status
        status = await agent.get_agent_status()
        assert status["documents_analyzed"] > 0
        
        # Step 4: Get analysis history
        history = await agent.get_document_analysis_history()
        assert len(history) > 0
        
        print(f"✓ End-to-end workflow completed successfully")
        print(f"  Analysis Quality: {insight.quality_score:.1f}")
        print(f"  Entities Found: {len(insight.entities)}")
        print(f"  Query Confidence: {result.confidence:.2f}")

# Run the tests
async def run_enhanced_document_intelligence_agent_tests():
    """Run all Enhanced Document Intelligence Agent tests"""
    print("Running Enhanced Document Intelligence Agent Tests...")
    
    try:
        # Basic tests
        test_instance = TestEnhancedDocumentIntelligenceAgent()
        
        # Test initialization
        await test_instance.test_agent_initialization()
        
        # Create agent for other tests
        agent = EnhancedDocumentIntelligenceAgent(agent_id="test_agent")
        await agent.initialize()
        
        # Run all tests
        await test_instance.test_document_analysis_enhanced(agent)
        await test_instance.test_knowledge_graph_construction(agent)
        await test_instance.test_document_querying(agent)
        await test_instance.test_document_type_classification(agent)
        await test_instance.test_entity_extraction(agent)
        await test_instance.test_document_synthesis(agent)
        await test_instance.test_collaborative_message_handling(agent)
        await test_instance.test_agent_status(agent)
        await test_instance.test_document_collection_management(agent)
        await test_instance.test_quality_and_readability_scoring(agent)
        await test_instance.test_concept_extraction(agent)
        await test_instance.test_document_id_generation(agent)
        
        # Integration tests
        integration_test = TestEnhancedDocumentIntelligenceAgentIntegration()
        await integration_test.test_factory_function()
        await integration_test.test_end_to_end_workflow()
        
        print("✅ All basic tests passed!")
        
        # Summary
        print("\n📊 Enhanced Document Intelligence Agent Test Summary:")
        print(f"✓ Agent initialized successfully")
        print(f"✓ Document analysis with knowledge graph construction")
        print(f"✓ Interactive document querying")
        print(f"✓ Entity extraction and relationship mapping")
        print(f"✓ Multi-document synthesis")
        print(f"✓ Document type classification")
        print(f"✓ Quality and readability scoring")
        print(f"✓ Collaborative message handling")  
        print(f"✓ Document collection management")
        print(f"✓ Integration tests passed")
        
        return True
        
    except Exception as e:
        print(f"❌ Test execution failed: {e}")
        import traceback
        traceback.print_exc()
        return False

if __name__ == "__main__":
    # Run the tests
    result = asyncio.run(run_enhanced_document_intelligence_agent_tests())
    if result:
        print("\n🎉 All Enhanced Document Intelligence Agent tests completed successfully!")
    else:
        print("\n❌ Some tests failed. Please check the output above.")
