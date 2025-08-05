#!/usr/bin/env python3
"""
Enhanced Document Intelligence Agent Demo
=========================================

Demonstrates the capabilities of the newly implemented Enhanced Document Intelligence Agent
including knowledge graph construction, document analysis, and interactive querying.
"""

import asyncio
import json
from agents.enhanced_document_intelligence_agent import (
    EnhancedDocumentIntelligenceAgent,
    DocumentAnalysisMode,
    create_enhanced_document_intelligence_agent
)

async def demo_document_analysis():
    """Demonstrate document analysis capabilities"""
    print("🚀 Enhanced Document Intelligence Agent Demo")
    print("=" * 50)
    
    # Create agent
    agent = await create_enhanced_document_intelligence_agent(
        agent_id="demo_agent"
    )
    
    # Sample document content
    sample_document = """
    # Research Report: Artificial Intelligence in Healthcare
    
    This comprehensive report examines the transformative impact of AI in healthcare.
    Dr. Sarah Johnson from MIT collaborated with researchers at Stanford University
    to develop new machine learning algorithms for medical diagnosis.
    
    Key findings include:
    - 95% accuracy in cancer detection using deep learning
    - 40% reduction in diagnostic time
    - Enhanced treatment personalization through AI analysis
    
    The research was funded by the National Institutes of Health (NIH)
    and published in the Journal of Medical AI Research.
    """.encode('utf-8')
    
    print("📄 Analyzing sample document...")
    
    # Perform enhanced document analysis
    try:
        insight = await agent.analyze_document_enhanced(
            file_content=sample_document,
            analysis_mode=DocumentAnalysisMode.ENHANCED,
            build_knowledge_graph=True
        )
        
        print(f"✅ Document Analysis Complete!")
        print(f"   - Document Type: {insight.document_type}")
        print(f"   - Language: {insight.language}")
        print(f"   - Entities Found: {len(insight.entities)}")
        print(f"   - Relationships: {len(insight.relationships)}")
        print(f"   - Quality Score: {insight.quality_score:.2f}")
        
        # Display some entities
        print("\n🔍 Extracted Entities:")
        for entity in insight.entities[:5]:  # Show first 5
            print(f"   - {entity.name} ({entity.entity_type}) - Confidence: {entity.confidence:.2f}")
        
        # Display relationships
        print("\n🔗 Discovered Relationships:")
        for rel in insight.relationships[:3]:  # Show first 3
            print(f"   - {rel.subject} → {rel.predicate} → {rel.object}")
        
    except Exception as e:
        print(f"❌ Analysis failed: {e}")
    
    print("\n🔍 Testing Knowledge Graph Construction...")
    
    # Test knowledge graph construction
    test_documents = [
        {
            "id": "doc1", 
            "content": "Dr. Johnson works at MIT and specializes in AI research.",
            "metadata": {"title": "Researcher Profile"}
        },
        {
            "id": "doc2",
            "content": "MIT partnered with Stanford on healthcare AI project.",
            "metadata": {"title": "Partnership News"}
        }
    ]
    
    try:
        kg = await agent.build_knowledge_graph(test_documents)
        print(f"✅ Knowledge Graph Built!")
        print(f"   - Entities: {len(kg.entities)}")
        print(f"   - Relationships: {len(kg.relationships)}")
        
        # Show some entities from knowledge graph
        print("\n📊 Knowledge Graph Entities:")
        for entity_name, entity in list(kg.entities.items())[:3]:
            print(f"   - {entity_name} ({entity.entity_type})")
            
    except Exception as e:
        print(f"❌ Knowledge graph construction failed: {e}")
    
    print("\n🤖 Testing Interactive Querying...")
    
    # Test document querying
    try:
        query_result = await agent.query_documents(
            query="What is Dr. Johnson's research focus?",
            document_ids=["doc1", "doc2"]
        )
        
        print(f"✅ Query Processed!")
        print(f"   - Answer: {query_result.answer}")
        print(f"   - Confidence: {query_result.confidence:.2f}")
        
    except Exception as e:
        print(f"❌ Querying failed: {e}")
    
    print("\n📈 Agent Status:")
    try:
        status = await agent.get_agent_status()
        print(f"   - Agent ID: {status['agent_id']}")
        print(f"   - State: {status['state']}")
        print(f"   - Documents Analyzed: {status['documents_analyzed']}")
        print(f"   - Knowledge Graphs: {status['knowledge_graphs_built']}")
        
    except Exception as e:
        print(f"❌ Status check failed: {e}")
    
    print("\n🎉 Demo Complete! Enhanced Document Intelligence Agent is operational.")
    print("Ready for Phase 2B.4 - Advanced AI Integration!")

if __name__ == "__main__":
    asyncio.run(demo_document_analysis())
