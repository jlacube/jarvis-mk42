"""
Enhanced Research Agent for Advanced Research Capabilities

This agent extends the BaseEnhancedAgent to provide sophisticated research capabilities
including fact verification, domain expertise, multi-language research, and real-time
information gathering. It integrates with the communication framework from Phase 2B.2
and language detection from Phase 2B.3.

The agent implements multiple research strategies and workflows to provide comprehensive,
high-quality research results with verification and quality assessment.
"""

import asyncio
import logging
from typing import Dict, List, Optional, Any, Tuple
from datetime import datetime
import json

from agents.base_enhanced_agent import BaseEnhancedAgent, AgentCapabilities, AgentMetrics, AgentState
from communication.protocols import AgentType
from utils.research_strategies import (
    ResearchStrategy,
    ResearchContext,
    ResearchResult,
    ResearchPriority,
    get_research_strategies,
    select_optimal_strategy
)
from tools.enhanced_research_tools import get_enhanced_research_tools
from tools.research_tools import get_research_tools
from tools.language_detection import detect_language_with_confidence, detect_multiple_languages
from models.models import get_openai_model, get_google_model
from utils.exceptions import JarvisValidationError, JarvisToolError
from utils.logging_config import get_logger

# Initialize logger
logger = get_logger(__name__)

class EnhancedResearchAgent(BaseEnhancedAgent):
    """
    Enhanced Research Agent with advanced research capabilities.
    
    Features:
    - Multi-strategy research approach (Deep, Fact Verification, Domain Expertise, Real-time)
    - Multi-language research capabilities
    - Source credibility assessment
    - Fact verification and claim validation
    - Domain-specific research strategies
    - Real-time information focus
    - Quality metrics and assessment
    - Communication framework integration
    """
    
    def __init__(
        self,
        agent_id: str = "enhanced_research_agent",
        name: str = "Enhanced Research Agent",
        model_config: Dict[str, Any] = None,
        communication_config: Dict[str, Any] = None
    ):
        # Import necessary enums for capabilities
        from communication.context_manager import ContextScope
        from communication.conflict_resolver import ResolutionStrategy
        from agents.base_enhanced_agent import CommunicationMode
        
        # Define capabilities
        capabilities = AgentCapabilities(
            primary_functions=[
                "web_search", "fact_verification", "domain_research", 
                "multi_language_research", "real_time_research", "source_credibility_assessment"
            ],
            supported_languages=["english", "spanish", "french", "german", "chinese", "japanese", "arabic", "russian", "portuguese", "italian"],
            communication_modes=[CommunicationMode.STANDALONE, CommunicationMode.COLLABORATIVE, CommunicationMode.RESPONDING],
            conflict_resolution_strategies=[ResolutionStrategy.MAJORITY_VOTE, ResolutionStrategy.EXPERT_OVERRIDE, ResolutionStrategy.MERGE_COMPATIBLE],
            context_scopes=[ContextScope.TASK, ContextScope.CONVERSATION, ContextScope.GLOBAL],
            max_concurrent_tasks=3,
            supports_streaming=True,
            requires_context=True
        )
        
        # Initialize base agent
        super().__init__(
            agent_id=agent_id,
            agent_type=AgentType.RESEARCH,
            agent_name=name,
            capabilities=capabilities,
            message_bus=None,  # Will be set up during initialization if needed
            context_manager=None,  # Will be set up during initialization if needed
            conflict_resolver=None  # Will be set up during initialization if needed
        )
        
        # Store configuration for later use
        self.model_config = model_config or {"provider": "openai", "model": "gpt-4", "temperature": 0.3}
        self.communication_config = communication_config
        
        # Initialize communication manager reference (set during base class initialization)
        self.communication_manager = None
        
        # Initialize research-specific components
        self.specialized_domains = ["academic", "technical", "business", "news", "government", "science", "medicine", "law", "finance"]
        self.research_strategies = get_research_strategies()
        self.research_tools = get_research_tools() + get_enhanced_research_tools()
        self.tool_registry = {}  # Initialize tool registry for tracking tools
        self.research_history: List[ResearchResult] = []
        self.active_research_context: Optional[ResearchContext] = None
        
        logger.info(f"Enhanced Research Agent initialized with {len(self.research_strategies)} strategies and {len(self.research_tools)} tools")
    
    async def initialize(self) -> bool:
        """Initialize the enhanced research agent"""
        try:
            # Initialize base agent
            await super().initialize()
            
            # Initialize research-specific tools in tool registry
            for tool in self.research_tools:
                self.tool_registry[tool.name] = tool
            
            # Test language detection integration
            try:
                test_result = await detect_language_with_confidence.ainvoke({"text": "This is a test."})
                logger.info(f"Language detection integration verified: {test_result}")
            except Exception as e:
                logger.warning(f"Language detection integration issue: {e}")
            
            # Update agent state
            self.state = AgentState.READY
            self.metrics.last_activity = datetime.now()
            
            logger.info("Enhanced Research Agent initialization completed successfully")
            return True
            
        except Exception as e:
            logger.error(f"Enhanced Research Agent initialization failed: {e}")
            self.state = AgentState.ERROR
            return False
    
    async def conduct_research(
        self,
        query: str,
        domain: str = "general",
        priority: str = "medium",
        languages: List[str] = None,
        time_sensitivity: str = "normal",
        verification_required: bool = True,
        max_depth: int = 2,
        max_breadth: int = 5,
        quality_threshold: float = 0.6
    ) -> Dict[str, Any]:
        """
        Conduct comprehensive research using optimal strategy selection.
        
        Args:
            query: The research query
            domain: Research domain (academic, technical, business, news, government, etc.)
            priority: Research priority (low, medium, high, critical)
            languages: List of languages to include in research
            time_sensitivity: Time sensitivity (real_time, recent, normal, historical)
            verification_required: Whether fact verification is required
            max_depth: Maximum research depth (1-5)
            max_breadth: Maximum breadth per level (1-20)
            quality_threshold: Minimum quality threshold (0.0-1.0)
            
        Returns:
            Dict containing comprehensive research results with quality metrics
        """
        start_time = datetime.now()
        
        try:
            # Validate inputs
            if not query or not query.strip():
                raise JarvisValidationError("Research query cannot be empty")
            
            # Map priority string to enum
            priority_map = {
                "low": ResearchPriority.LOW,
                "medium": ResearchPriority.MEDIUM,
                "high": ResearchPriority.HIGH,
                "critical": ResearchPriority.CRITICAL
            }
            priority_enum = priority_map.get(priority.lower(), ResearchPriority.MEDIUM)
            
            # Set default languages if not specified
            if languages is None:
                # Detect query language and include related languages
                try:
                    lang_result = await detect_language_with_confidence.ainvoke({"text": query})
                    detected_lang = lang_result.get("language", "english")
                    
                    # Add related languages for better coverage
                    language_families = {
                        "english": ["english", "spanish", "french"],
                        "spanish": ["spanish", "english", "portuguese"],
                        "french": ["french", "english", "spanish"],
                        "german": ["german", "english", "french"],
                        "chinese": ["chinese", "english", "japanese"],
                        "japanese": ["japanese", "chinese", "english"],
                        "arabic": ["arabic", "english", "french"],
                        "russian": ["russian", "english", "german"]
                    }
                    
                    languages = language_families.get(detected_lang, ["english", detected_lang])
                    
                except Exception as e:
                    logger.warning(f"Language detection failed, using default: {e}")
                    languages = ["english"]
            
            logger.info(f"Starting enhanced research for query: {query[:100]}...")
            logger.info(f"Domain: {domain}, Priority: {priority}, Languages: {languages}")
            
            # Create research context
            context = ResearchContext(
                query=query,
                domain=domain,
                priority=priority_enum,
                languages=languages,
                time_sensitivity=time_sensitivity,
                verification_required=verification_required,
                max_depth=max_depth,
                max_breadth=max_breadth,
                quality_threshold=quality_threshold
            )
            
            self.active_research_context = context
            
            # Select optimal research strategy
            strategy = select_optimal_strategy(context)
            logger.info(f"Selected research strategy: {strategy.name}")
            
            # Send collaboration message about research start
            if self.communication_manager:
                await self.communication_manager.send_message(
                    sender_id=self.agent_id,
                    content=f"Starting enhanced research: {query[:100]}...",
                    message_type="research_start",
                    metadata={
                        "strategy": strategy.name,
                        "domain": domain,
                        "languages": languages
                    }
                )
            
            # Execute research strategy
            research_result = await strategy.execute(context)
            
            # Store research result
            self.research_history.append(research_result)
            
            # Update agent metrics
            self.metrics.total_requests += 1
            if research_result.success:
                self.metrics.successful_requests += 1
            else:
                self.metrics.failed_requests += 1
            
            self.metrics.average_response_time = (
                (self.metrics.average_response_time * (self.metrics.total_requests - 1) + 
                 research_result.execution_time) / self.metrics.total_requests
            )
            
            # Calculate comprehensive research quality
            quality_assessment = await self._assess_research_quality(research_result, context)
            
            # Prepare comprehensive result
            comprehensive_result = {
                "query": query,
                "research_id": f"research_{int(start_time.timestamp())}",
                "strategy_used": strategy.name,
                "context": {
                    "domain": domain,
                    "priority": priority,
                    "languages": languages,
                    "time_sensitivity": time_sensitivity,
                    "verification_required": verification_required
                },
                "results": research_result.results,
                "quality_metrics": {
                    "overall_quality_score": research_result.quality_score,
                    "confidence": research_result.confidence,
                    "verification_status": research_result.verification_status,
                    "sources_analyzed": research_result.sources_analyzed,
                    "languages_covered": research_result.languages_covered,
                    "execution_time": research_result.execution_time
                },
                "quality_assessment": quality_assessment,
                "recommendations": research_result.recommendations or [],
                "success": research_result.success,
                "timestamp": start_time.isoformat(),
                "agent_info": {
                    "agent_id": self.agent_id,
                    "agent_name": self.agent_name,
                    "version": "enhanced_v1.0"
                }
            }
            
            # Add errors if any
            if research_result.errors:
                comprehensive_result["errors"] = research_result.errors
            
            # Send collaboration message about research completion
            if self.communication_manager:
                await self.communication_manager.send_message(
                    sender_id=self.agent_id,
                    content=f"Research completed with quality score: {research_result.quality_score:.2f}",
                    message_type="research_complete",
                    metadata={
                        "research_id": comprehensive_result["research_id"],
                        "quality_score": research_result.quality_score,
                        "verification_status": research_result.verification_status,
                        "sources_analyzed": research_result.sources_analyzed
                    }
                )
            
            # Update state
            self.metrics.last_activity = datetime.now()
            self.metrics.messages_processed += 1
            
            logger.info(f"Enhanced research completed successfully: quality {research_result.quality_score:.2f}, confidence {research_result.confidence:.2f}")
            
            return comprehensive_result
            
        except Exception as e:
            logger.error(f"Enhanced research failed: {e}")
            
            # Update error metrics
            self.metrics.failed_requests += 1
            self.metrics.total_requests += 1
            
            # Send error message to collaboration framework
            if self.communication_manager:
                await self.communication_manager.send_message(
                    sender_id=self.agent_id,
                    content=f"Research failed: {str(e)}",
                    message_type="research_error",
                    metadata={"error": str(e), "query": query}
                )
            
            raise JarvisToolError(f"Enhanced research failed: {e}")
        
        finally:
            self.active_research_context = None
    
    async def verify_fact(
        self,
        claim: str,
        max_sources: int = 5,
        languages: List[str] = None
    ) -> Dict[str, Any]:
        """
        Verify a specific fact or claim.
        
        Args:
            claim: The claim to verify
            max_sources: Maximum number of sources to check
            languages: Languages to verify in
            
        Returns:
            Dict containing verification results
        """
        try:
            from tools.enhanced_research_tools import verify_fact_claim
            
            if languages is None:
                languages = ["english"]
            
            logger.info(f"Verifying fact: {claim[:100]}...")
            
            result = await verify_fact_claim.ainvoke({
                "claim": claim,
                "max_sources": max_sources,
                "languages": languages
            })
            
            # Send collaboration message about fact verification
            if self.communication_manager:
                await self.communication_manager.send_message(
                    sender_id=self.agent_id,
                    content=f"Fact verified: {result['verification_status']} with {result['confidence']:.2f} confidence",
                    message_type="fact_verification",
                    metadata={
                        "claim": claim,
                        "status": result["verification_status"],
                        "confidence": result["confidence"]
                    }
                )
            
            logger.info(f"Fact verification completed: {result['verification_status']}")
            return result
            
        except Exception as e:
            logger.error(f"Fact verification failed: {e}")
            raise JarvisToolError(f"Fact verification failed: {e}")
    
    async def assess_source_credibility(
        self,
        url: str,
        domain: str = "general"
    ) -> Dict[str, Any]:
        """
        Assess the credibility of a source.
        
        Args:
            url: URL to assess
            domain: Research domain for context
            
        Returns:
            Dict containing credibility assessment
        """
        try:
            from tools.enhanced_research_tools import assess_source_credibility
            
            logger.info(f"Assessing source credibility: {url}")
            
            result = await assess_source_credibility.ainvoke({
                "url": url,
                "research_domain": domain
            })
            
            logger.info(f"Source credibility assessed: {result['overall_score']:.2f}")
            return result
            
        except Exception as e:
            logger.error(f"Source credibility assessment failed: {e}")
            raise JarvisToolError(f"Source credibility assessment failed: {e}")
    
    async def get_research_history(self, limit: int = 10) -> List[Dict[str, Any]]:
        """
        Get recent research history.
        
        Args:
            limit: Maximum number of results to return
            
        Returns:
            List of recent research results
        """
        try:
            recent_history = self.research_history[-limit:] if self.research_history else []
            
            return [
                {
                    "strategy_name": result.strategy_name,
                    "query": result.query,
                    "success": result.success,
                    "quality_score": result.quality_score,
                    "confidence": result.confidence,
                    "verification_status": result.verification_status,
                    "sources_analyzed": result.sources_analyzed,
                    "languages_covered": result.languages_covered,
                    "execution_time": result.execution_time
                }
                for result in recent_history
            ]
            
        except Exception as e:
            logger.error(f"Failed to get research history: {e}")
            return []
    
    async def get_agent_status(self) -> Dict[str, Any]:
        """Get comprehensive agent status including research-specific metrics"""
        base_status = self.get_status()
        
        # Add research-specific status
        research_status = {
            "research_strategies_available": len(self.research_strategies),
            "research_tools_available": len(self.research_tools),
            "total_research_conducted": len(self.research_history),
            "active_research": self.active_research_context is not None,
            "recent_research_quality": (
                sum(r.quality_score for r in self.research_history[-10:]) / 
                min(10, len(self.research_history))
            ) if self.research_history else 0.0,
            "supported_domains": self.specialized_domains,
            "supported_languages": self.capabilities.supported_languages
        }
        
        base_status.update(research_status)
        return base_status
    
    async def _assess_research_quality(
        self,
        research_result: ResearchResult,
        context: ResearchContext
    ) -> Dict[str, Any]:
        """Assess the quality of research results"""
        
        quality_factors = {
            "strategy_appropriate": 1.0 if research_result.success else 0.0,
            "source_diversity": min(1.0, research_result.sources_analyzed / context.max_breadth),
            "language_coverage": min(1.0, len(research_result.languages_covered) / len(context.languages or ["english"])),
            "verification_confidence": research_result.confidence,
            "execution_efficiency": min(1.0, 30.0 / max(research_result.execution_time, 1.0))  # Prefer faster execution
        }
        
        # Calculate weighted quality assessment
        weights = {
            "strategy_appropriate": 0.3,
            "source_diversity": 0.2,
            "language_coverage": 0.2,
            "verification_confidence": 0.2,
            "execution_efficiency": 0.1
        }
        
        overall_assessment = sum(
            quality_factors[factor] * weights[factor] 
            for factor in quality_factors
        )
        
        # Generate quality recommendations
        recommendations = []
        if quality_factors["source_diversity"] < 0.7:
            recommendations.append("Consider increasing source diversity")
        if quality_factors["language_coverage"] < 0.8 and len(context.languages or []) > 1:
            recommendations.append("Improve multi-language coverage")
        if quality_factors["verification_confidence"] < 0.7:
            recommendations.append("Enhance fact verification with additional sources")
        
        return {
            "overall_assessment": overall_assessment,
            "quality_factors": quality_factors,
            "recommendations": recommendations,
            "meets_threshold": overall_assessment >= context.quality_threshold
        }

    async def handle_collaboration_message(self, message: Dict[str, Any]) -> Optional[Dict[str, Any]]:
        """Handle collaboration messages from other agents"""
        try:
            message_type = message.get("message_type", "")
            content = message.get("content", "")
            sender_id = message.get("sender_id", "")
            metadata = message.get("metadata", {})
            
            logger.info(f"Received collaboration message from {sender_id}: {message_type}")
            
            if message_type == "research_request":
                # Handle research request from another agent
                query = metadata.get("query", content)
                domain = metadata.get("domain", "general")
                priority = metadata.get("priority", "medium")
                
                if query:
                    research_result = await self.conduct_research(
                        query=query,
                        domain=domain,
                        priority=priority
                    )
                    
                    return {
                        "message_type": "research_response",
                        "content": f"Research completed for: {query[:100]}...",
                        "metadata": {
                            "research_result": research_result,
                            "original_request_id": metadata.get("request_id")
                        }
                    }
            
            elif message_type == "fact_check_request":
                # Handle fact checking request
                claim = metadata.get("claim", content)
                
                if claim:
                    verification_result = await self.verify_fact(claim)
                    
                    return {
                        "message_type": "fact_check_response",
                        "content": f"Fact check: {verification_result['verification_status']}",
                        "metadata": {
                            "verification_result": verification_result,
                            "original_request_id": metadata.get("request_id")
                        }
                    }
            
            elif message_type == "source_verification_request":
                # Handle source credibility check request
                url = metadata.get("url", "")
                domain = metadata.get("domain", "general")
                
                if url:
                    credibility_result = await self.assess_source_credibility(url, domain)
                    
                    return {
                        "message_type": "source_verification_response",
                        "content": f"Source credibility: {credibility_result['overall_score']:.2f}",
                        "metadata": {
                            "credibility_result": credibility_result,
                            "original_request_id": metadata.get("request_id")
                        }
                    }
        
        except Exception as e:
            logger.error(f"Failed to handle collaboration message: {e}")
            return {
                "message_type": "error_response",
                "content": f"Failed to process request: {str(e)}",
                "metadata": {"error": str(e)}
            }
        
        return None
    
    # Abstract method implementations required by BaseEnhancedAgent
    async def _initialize_agent_specific(self) -> None:
        """Initialize research agent specific components."""
        # Initialize any research-specific resources here
        # For now, just log initialization
        logger.info(f"Enhanced Research Agent {self.agent_id} initialized successfully")
    
    async def _cleanup_agent_specific(self) -> None:
        """Cleanup research agent specific resources."""
        # Cleanup any research-specific resources here
        # For now, just log cleanup
        logger.info(f"Enhanced Research Agent {self.agent_id} cleaned up successfully")
    
    async def _process_request_internal(
        self,
        request: str,
        context: Optional[Dict[str, Any]],
        language_context: Any,
        task_id: str
    ) -> Dict[str, Any]:
        """Process research request internally using appropriate strategy."""
        try:
            # Use the main conduct_research method with the internal request
            research_result = await self.conduct_research(
                query=request,
                context=context or {},
                max_depth=3,
                language=getattr(language_context, 'language', 'english') if language_context else 'english'
            )
            
            return {
                'success': True,
                'task_id': task_id,
                'result': research_result,
                'agent_id': self.agent_id,
                'timestamp': datetime.now().isoformat()
            }
        except Exception as e:
            logger.error(f"Error in _process_request_internal: {e}")
            return {
                'success': False,
                'task_id': task_id,
                'error': str(e),
                'agent_id': self.agent_id,
                'timestamp': datetime.now().isoformat()
            }

async def create_enhanced_research_agent(
    agent_id: str = "enhanced_research_agent",
    model_config: Dict[str, Any] = None,
    communication_config: Dict[str, Any] = None
) -> EnhancedResearchAgent:
    """
    Factory function to create and initialize an Enhanced Research Agent.
    
    Args:
        agent_id: Unique identifier for the agent
        model_config: Model configuration settings
        communication_config: Communication framework configuration
        
    Returns:
        Initialized EnhancedResearchAgent instance
    """
    agent = EnhancedResearchAgent(
        agent_id=agent_id,
        model_config=model_config,
        communication_config=communication_config
    )
    
    await agent.initialize()
    return agent
