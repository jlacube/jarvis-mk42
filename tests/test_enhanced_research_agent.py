"""
Tests for Enhanced Research Agent

This module contains comprehensive tests for the Enhanced Research Agent,
including tests for all research strategies, tools, and integration with
the communication framework and language detection system.
"""

import pytest
import pytest_asyncio
import asyncio
from unittest.mock import Mock, patch, AsyncMock
from datetime import datetime
from typing import Dict, List, Any
import sys
import os

# Add the project root to Python path
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from agents.enhanced_research_agent import EnhancedResearchAgent, create_enhanced_research_agent
from agents.base_enhanced_agent import AgentState
from utils.research_strategies import (
    ResearchContext,
    ResearchResult,
    ResearchPriority,
    DeepResearchStrategy,
    FactVerificationStrategy,
    DomainExpertiseStrategy,
    RealTimeResearchStrategy,
    select_optimal_strategy
)
from tools.enhanced_research_tools import (
    assess_source_credibility,
    verify_fact_claim,
    domain_specific_research,
    multi_language_research,
    real_time_information_research
)

class TestEnhancedResearchAgent:
    """Test class for Enhanced Research Agent"""
    
    @pytest_asyncio.fixture
    async def agent(self):
        """Create test agent instance"""
        agent = EnhancedResearchAgent(
            agent_id="test_research_agent",
            model_config={"provider": "openai", "model": "gpt-4", "temperature": 0.3}
        )
        await agent.initialize()
        return agent
    
    @pytest.mark.asyncio
    async def test_agent_initialization(self, agent):
        """Test agent initialization"""
        assert agent.agent_id == "test_research_agent"
        assert agent.agent_name == "Enhanced Research Agent"
        assert agent.agent_type.value == "research"
        assert agent.state == AgentState.READY
        assert len(agent.research_strategies) > 0
        assert len(agent.research_tools) > 0
        assert len(agent.capabilities.supported_languages) > 0
        assert len(agent.specialized_domains) > 0
    
    @pytest.mark.asyncio
    async def test_basic_research_conduct(self, agent):
        """Test basic research functionality"""
        with patch('tools.research_tools.google_search_tool') as mock_search:
            # Mock search results
            mock_search.ainvoke = AsyncMock(return_value={
                "organic": [
                    {
                        "title": "Test Result",
                        "snippet": "This is a test search result",
                        "link": "https://example.com/test"
                    }
                ]
            })
            
            with patch('tools.language_detection.detect_language_with_confidence') as mock_lang:
                mock_lang.ainvoke = AsyncMock(return_value={"language": "english", "confidence": 0.99})
                
                # Conduct basic research
                result = await agent.conduct_research(
                    query="test research query",
                    domain="general",
                    priority="medium",
                    max_depth=1,
                    max_breadth=3
                )
                
                assert result["success"] is True
                assert "query" in result
                assert "research_id" in result
                assert "strategy_used" in result
                assert "quality_metrics" in result
                assert result["query"] == "test research query"
    
    @pytest.mark.asyncio
    async def test_domain_specific_research(self, agent):
        """Test domain-specific research"""
        with patch('tools.enhanced_research_tools.domain_specific_research') as mock_domain:
            mock_domain.ainvoke = AsyncMock(return_value={
                "results": [{"content": "Academic research result", "quality_score": 0.8}],
                "quality_metrics": {"overall_quality": 0.8},
                "languages_covered": ["english"],
                "total_results": 1
            })
            
            with patch('tools.language_detection.detect_language_with_confidence') as mock_lang:
                mock_lang.ainvoke = AsyncMock(return_value={"language": "english", "confidence": 0.99})
                
                result = await agent.conduct_research(
                    query="machine learning algorithms",
                    domain="academic",
                    priority="high",
                    max_depth=2,
                    max_breadth=5
                )
                
                assert result["success"] is True
                assert result["context"]["domain"] == "academic"
                assert "academic" in str(result).lower() or result["strategy_used"] in ["Domain Expertise", "Deep Research"]
    
    @pytest.mark.asyncio
    async def test_multi_language_research(self, agent):
        """Test multi-language research capabilities"""
        with patch('tools.enhanced_research_tools.multi_language_research') as mock_multilang:
            mock_multilang.ainvoke = AsyncMock(return_value={
                "language_results": {
                    "english": {"results": [{"snippet": "English result"}], "result_count": 1},
                    "spanish": {"results": [{"snippet": "Spanish result"}], "result_count": 1}
                },
                "summary": {"total_results": 2, "successful_languages": 2}
            })
            
            with patch('tools.research_tools.google_search_tool') as mock_search:
                mock_search.ainvoke = AsyncMock(return_value={
                    "organic": [{"title": "Test", "snippet": "Test", "link": "https://example.com"}]
                })
                
                with patch('tools.language_detection.detect_language_with_confidence') as mock_lang:
                    mock_lang.ainvoke = AsyncMock(return_value={"language": "english", "confidence": 0.99})
                    
                    result = await agent.conduct_research(
                        query="inteligencia artificial",
                        languages=["english", "spanish"],
                        priority="medium"
                    )
                    
                    assert result["success"] is True
                    assert "english" in result["quality_metrics"]["languages_covered"] or "spanish" in result["quality_metrics"]["languages_covered"]
    
    @pytest.mark.asyncio
    async def test_fact_verification(self, agent):
        """Test fact verification functionality"""
        with patch('tools.enhanced_research_tools.verify_fact_claim') as mock_verify:
            mock_verify.ainvoke = AsyncMock(return_value={
                "claim": "The Earth is round",
                "verification_status": "VERIFIED",
                "confidence": 0.95,
                "supporting_sources": [
                    {"url": "https://nasa.gov", "overall_score": 0.9}
                ],
                "contradicting_sources": [],
                "verification_reasoning": "Multiple credible sources support this claim",
                "languages_checked": ["english"]
            })
            
            result = await agent.verify_fact("The Earth is round")
            
            assert result["verification_status"] == "VERIFIED"
            assert result["confidence"] == 0.95
            assert len(result["supporting_sources"]) > 0
    
    @pytest.mark.asyncio
    async def test_source_credibility_assessment(self, agent):
        """Test source credibility assessment"""
        with patch('tools.enhanced_research_tools.assess_source_credibility') as mock_assess:
            mock_assess.ainvoke = AsyncMock(return_value={
                "url": "https://nasa.gov/test",
                "domain": "nasa.gov",
                "authority_score": 0.9,
                "recency_score": 0.8,
                "consistency_score": 0.8,
                "overall_score": 0.85,
                "reasoning": "High authority government domain with recent content",
                "language": "english"
            })
            
            result = await agent.assess_source_credibility("https://nasa.gov/test", "science")
            
            assert result["overall_score"] == 0.85
            assert result["domain"] == "nasa.gov"
            assert result["authority_score"] == 0.9
    
    @pytest.mark.asyncio
    async def test_real_time_research(self, agent):
        """Test real-time research functionality"""
        with patch('tools.enhanced_research_tools.real_time_information_research') as mock_realtime:
            mock_realtime.ainvoke = AsyncMock(return_value={
                "results": [
                    {"content": "Breaking: Latest AI developments", "recency_score": 0.9}
                ],
                "metrics": {
                    "total_results": 1,
                    "freshness_score": 0.9,
                    "search_timestamp": datetime.now().isoformat()
                }
            })
            
            with patch('tools.language_detection.detect_language_with_confidence') as mock_lang:
                mock_lang.ainvoke = AsyncMock(return_value={"language": "english", "confidence": 0.99})
                
                result = await agent.conduct_research(
                    query="latest AI developments breaking news",
                    time_sensitivity="real_time",
                    max_depth=1
                )
                
                assert result["success"] is True
                assert result["context"]["time_sensitivity"] == "real_time"
    
    @pytest.mark.asyncio
    async def test_research_history(self, agent):
        """Test research history tracking"""
        # Perform multiple research operations
        with patch('tools.research_tools.google_search_tool') as mock_search:
            mock_search.ainvoke = AsyncMock(return_value={
                "organic": [{"title": "Test", "snippet": "Test", "link": "https://example.com"}]
            })
            
            with patch('tools.language_detection.detect_language_with_confidence') as mock_lang:
                mock_lang.ainvoke = AsyncMock(return_value={"language": "english", "confidence": 0.99})
                
                # Conduct multiple research operations
                await agent.conduct_research("query 1", max_depth=1)
                await agent.conduct_research("query 2", max_depth=1)
                
                history = await agent.get_research_history()
                
                assert len(history) == 2
                assert all("query" in item for item in history)
                assert all("quality_score" in item for item in history)
    
    @pytest.mark.asyncio
    async def test_agent_status(self, agent):
        """Test agent status reporting"""
        status = await agent.get_agent_status()
        
        assert "research_strategies_available" in status
        assert "research_tools_available" in status
        assert "total_research_conducted" in status
        assert "supported_domains" in status
        assert "supported_languages" in status
        assert status["research_strategies_available"] > 0
        assert status["research_tools_available"] > 0
    
    @pytest.mark.asyncio
    async def test_collaboration_message_handling(self, agent):
        """Test collaboration message handling"""
        # Test research request message
        research_request = {
            "message_type": "research_request",
            "sender_id": "test_agent",
            "content": "Research AI trends",
            "metadata": {"query": "AI trends 2024", "domain": "technology"}
        }
        
        with patch('tools.research_tools.google_search_tool') as mock_search:
            mock_search.ainvoke = AsyncMock(return_value={
                "organic": [{"title": "AI trends", "snippet": "Latest AI trends", "link": "https://example.com"}]
            })
            
            with patch('tools.language_detection.detect_language_with_confidence') as mock_lang:
                mock_lang.ainvoke = AsyncMock(return_value={"language": "english", "confidence": 0.99})
                
                response = await agent.handle_collaboration_message(research_request)
                
                assert response is not None
                assert response["message_type"] == "research_response"
                assert "research_result" in response["metadata"]
        
        # Test fact check request message
        fact_check_request = {
            "message_type": "fact_check_request",
            "sender_id": "test_agent",
            "content": "Check this fact",
            "metadata": {"claim": "Python is a programming language"}
        }
        
        with patch('tools.enhanced_research_tools.verify_fact_claim') as mock_verify:
            mock_verify.ainvoke = AsyncMock(return_value={
                "verification_status": "VERIFIED",
                "confidence": 0.95,
                "supporting_sources": [],
                "contradicting_sources": [],
                "verification_reasoning": "Well known fact",
                "languages_checked": ["english"]
            })
            
            response = await agent.handle_collaboration_message(fact_check_request)
            
            assert response is not None
            assert response["message_type"] == "fact_check_response"
            assert "verification_result" in response["metadata"]

class TestResearchStrategies:
    """Test class for research strategies"""
    
    @pytest.fixture
    def research_context(self):
        """Create test research context"""
        return ResearchContext(
            query="test query",
            domain="general",
            priority=ResearchPriority.MEDIUM,
            languages=["english"],
            verification_required=True,
            max_depth=2,
            max_breadth=5
        )
    
    def test_strategy_selection(self, research_context):
        """Test strategy selection logic"""
        # Test fact verification priority
        research_context.verification_required = True
        research_context.query = "verify this fact"
        strategy = select_optimal_strategy(research_context)
        assert isinstance(strategy, FactVerificationStrategy)
        
        # Test real-time priority (reset verification_required)
        research_context.verification_required = False
        research_context.time_sensitivity = "real_time"
        research_context.query = "latest breaking news"
        strategy = select_optimal_strategy(research_context)
        assert isinstance(strategy, RealTimeResearchStrategy)
        
        # Test domain expertise priority
        research_context.domain = "academic"
        research_context.time_sensitivity = "normal"
        research_context.verification_required = False
        strategy = select_optimal_strategy(research_context)
        assert isinstance(strategy, DomainExpertiseStrategy)
    
    def test_deep_research_strategy_applicability(self, research_context):
        """Test deep research strategy applicability"""
        strategy = DeepResearchStrategy()
        
        # Should be applicable for high priority
        research_context.priority = ResearchPriority.HIGH
        assert strategy.is_applicable(research_context)
        
        # Should be applicable for academic domain
        research_context.priority = ResearchPriority.MEDIUM
        research_context.domain = "academic"
        assert strategy.is_applicable(research_context)
        
        # Should be applicable for high depth
        research_context.domain = "general"
        research_context.max_depth = 3
        assert strategy.is_applicable(research_context)
    
    def test_fact_verification_strategy_applicability(self, research_context):
        """Test fact verification strategy applicability"""
        strategy = FactVerificationStrategy()
        
        # Should be applicable when verification required
        research_context.verification_required = True
        assert strategy.is_applicable(research_context)
        
        # Should be applicable for critical priority
        research_context.verification_required = False
        research_context.priority = ResearchPriority.CRITICAL
        assert strategy.is_applicable(research_context)
        
        # Should be applicable for verification queries
        research_context.priority = ResearchPriority.MEDIUM
        research_context.query = "is this fact true?"
        assert strategy.is_applicable(research_context)
    
    def test_domain_expertise_strategy_applicability(self, research_context):
        """Test domain expertise strategy applicability"""
        strategy = DomainExpertiseStrategy()
        
        # Should be applicable for specialized domains
        research_context.domain = "academic"
        assert strategy.is_applicable(research_context)
        
        research_context.domain = "technical"
        assert strategy.is_applicable(research_context)
        
        # Should not be applicable for general domain
        research_context.domain = "general"
        assert not strategy.is_applicable(research_context)
    
    def test_realtime_research_strategy_applicability(self, research_context):
        """Test real-time research strategy applicability"""
        strategy = RealTimeResearchStrategy()
        
        # Should be applicable for real-time sensitivity
        research_context.time_sensitivity = "real_time"
        assert strategy.is_applicable(research_context)
        
        # Should be applicable for recent sensitivity
        research_context.time_sensitivity = "recent"
        assert strategy.is_applicable(research_context)
        
        # Should be applicable for time-sensitive queries
        research_context.time_sensitivity = "normal"
        research_context.query = "latest breaking news"
        assert strategy.is_applicable(research_context)

class TestEnhancedResearchTools:
    """Test class for enhanced research tools"""
    
    @pytest.mark.asyncio
    async def test_assess_source_credibility_tool(self):
        """Test source credibility assessment tool"""
        with patch('requests.get') as mock_get:
            mock_response = Mock()
            mock_response.status_code = 200
            mock_response.content = b"<html><body>Test content</body></html>"
            mock_get.return_value = mock_response
            
            # Test with government domain
            result = await assess_source_credibility.ainvoke({
                "url": "https://nasa.gov/test",
                "content": "NASA research on space exploration",
                "research_domain": "science"
            })
            
            assert "overall_score" in result
            assert "authority_score" in result
            assert "reasoning" in result
            assert result["domain"] == "nasa.gov"
            assert result["overall_score"] > 0.5  # Government domain should have good score
    
    @pytest.mark.asyncio
    async def test_domain_specific_research_tool(self):
        """Test domain-specific research tool"""
        with patch('tools.research_tools.advanced_research_tool') as mock_advanced:
            mock_advanced.ainvoke = AsyncMock(return_value="Advanced research result for academic query")
            
            with patch('tools.language_detection.detect_language_with_confidence') as mock_lang:
                mock_lang.ainvoke = AsyncMock(return_value={"language": "english", "confidence": 0.99})
                
                result = await domain_specific_research.ainvoke({
                    "query": "machine learning research",
                    "domain": "academic",
                    "max_results": 5,
                    "include_languages": ["english"]
                })
                
                assert "results" in result
                assert "quality_metrics" in result
                assert "languages_covered" in result
                assert result["domain"] == "academic"
    
    @pytest.mark.asyncio
    async def test_multi_language_research_tool(self):
        """Test multi-language research tool"""
        with patch('tools.research_tools.google_search_tool') as mock_search:
            mock_search.ainvoke = AsyncMock(return_value={
                "organic": [
                    {"title": "Test", "snippet": "Test content", "link": "https://example.com"}
                ]
            })
            
            with patch('tools.language_detection.detect_language_with_confidence') as mock_lang:
                mock_lang.ainvoke = AsyncMock(return_value={"language": "english", "confidence": 0.99})
                
                result = await multi_language_research.ainvoke({
                    "query": "artificial intelligence",
                    "target_languages": ["english", "spanish"],
                    "max_results_per_language": 3
                })
                
                assert "language_results" in result
                assert "summary" in result
                assert len(result["target_languages"]) == 2
    
    @pytest.mark.asyncio
    async def test_real_time_information_research_tool(self):
        """Test real-time information research tool"""
        with patch('tools.research_tools.advanced_research_tool') as mock_advanced:
            mock_advanced.ainvoke = AsyncMock(return_value="Breaking news: Latest AI developments today")
            
            result = await real_time_information_research.ainvoke({
                "query": "AI developments",
                "time_range": "24h",
                "max_results": 5
            })
            
            assert "results" in result
            assert "metrics" in result
            assert result["time_range"] == "24h"
            assert "freshness_score" in result["metrics"]

class TestIntegration:
    """Integration tests for the complete enhanced research system"""
    
    @pytest.mark.asyncio
    async def test_end_to_end_research_workflow(self):
        """Test complete end-to-end research workflow"""
        # Create agent
        agent = await create_enhanced_research_agent("test_integration_agent")
        
        with patch('tools.research_tools.google_search_tool') as mock_search:
            mock_search.ainvoke = AsyncMock(return_value={
                "organic": [
                    {
                        "title": "Comprehensive AI Research",
                        "snippet": "Detailed analysis of artificial intelligence trends",
                        "link": "https://example.com/ai-research"
                    }
                ]
            })
            
            with patch('tools.language_detection.detect_language_with_confidence') as mock_lang:
                mock_lang.ainvoke = AsyncMock(return_value={"language": "english", "confidence": 0.99})
                
                with patch('tools.research_tools.fetch_url_content') as mock_fetch:
                    mock_fetch.return_value = "Comprehensive AI research content about trends and implications in technology."
                    
                    with patch('tools.enhanced_research_tools.assess_source_credibility') as mock_credibility:
                        mock_credibility.ainvoke = AsyncMock(return_value={
                            "url": "https://example.com/ai-research",
                            "domain": "example.com",
                            "authority_score": 0.8,
                            "recency_score": 0.7,
                            "consistency_score": 0.8,
                            "overall_score": 0.75,
                            "reasoning": "Credible source with good content",
                            "language": "english"
                        })
                        
                        # Perform comprehensive research
                        result = await agent.conduct_research(
                            query="artificial intelligence trends and implications",
                            domain="technology",
                            priority="high",
                            languages=["english"],
                            verification_required=True,
                            max_depth=2,
                            max_breadth=5
                        )
                        
                        # Verify comprehensive result structure
                        assert result["success"] is True
                        assert "research_id" in result
                        assert "strategy_used" in result
                        assert "context" in result
                        assert "results" in result
                        assert "quality_metrics" in result
                        assert "quality_assessment" in result
                        
                        # Verify quality metrics
                        quality_metrics = result["quality_metrics"]
                        assert "overall_quality_score" in quality_metrics
                        assert "confidence" in quality_metrics
                        assert "verification_status" in quality_metrics
                        assert "sources_analyzed" in quality_metrics
                        assert "languages_covered" in quality_metrics
                        
                        # Verify context preservation
                        context = result["context"]
                        assert context["domain"] == "technology"
                        assert context["priority"] == "high"
                        assert context["verification_required"] is True
        
        # Test research history
        history = await agent.get_research_history()
        assert len(history) == 1
        assert history[0]["query"] == "artificial intelligence trends and implications"
        
        # Test agent status
        status = await agent.get_agent_status()
        assert status["total_research_conducted"] == 1
        assert status["active_research"] is False

# Run tests with proper error handling
if __name__ == "__main__":
    print("Running Enhanced Research Agent Tests...")
    
    # Run basic agent tests
    async def run_basic_tests():
        agent = EnhancedResearchAgent("test_agent")
        await agent.initialize()
        
        print(f"✓ Agent initialized successfully")
        print(f"✓ Strategies available: {len(agent.research_strategies)}")
        print(f"✓ Tools available: {len(agent.research_tools)}")
        print(f"✓ Languages supported: {len(agent.capabilities.supported_languages)}")
        print(f"✓ Domains supported: {len(agent.specialized_domains)}")
        
        status = await agent.get_agent_status()
        print(f"✓ Agent status: {status['state']}")
        
        return True
    
    # Run the basic tests
    try:
        result = asyncio.run(run_basic_tests())
        if result:
            print("✅ All basic tests passed!")
        else:
            print("❌ Some tests failed!")
    except Exception as e:
        print(f"❌ Test execution failed: {e}")
