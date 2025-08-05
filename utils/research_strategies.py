"""
Research Strategies for Enhanced Research Agent

This module provides various research strategies that can be applied
to different types of research queries and domains. Each strategy
implements specific approaches for gathering, analyzing, and validating
information based on the research context.

The strategies integrate with enhanced research tools and communication
framework to provide sophisticated research workflows.
"""

import asyncio
import logging
from abc import ABC, abstractmethod
from typing import Dict, List, Optional, Any, Tuple
from dataclasses import dataclass
from enum import Enum

from tools.enhanced_research_tools import (
    assess_source_credibility,
    verify_fact_claim,
    domain_specific_research,
    multi_language_research,
    real_time_information_research
)
from tools.research_tools import (
    google_search_tool,
    advanced_research_tool,
    webpage_research_tool
)
from tools.language_detection import detect_language_with_confidence
from utils.exceptions import JarvisValidationError, JarvisToolError
from utils.logging_config import get_logger

# Initialize logger
logger = get_logger(__name__)

class ResearchPriority(Enum):
    """Priority levels for research strategies"""
    LOW = 1
    MEDIUM = 2
    HIGH = 3
    CRITICAL = 4

@dataclass
class ResearchContext:
    """Context information for research strategies"""
    query: str
    domain: str = "general"
    priority: ResearchPriority = ResearchPriority.MEDIUM
    languages: List[str] = None
    time_sensitivity: str = "normal"  # "real_time", "recent", "normal", "historical"
    verification_required: bool = True
    max_depth: int = 2
    max_breadth: int = 5
    quality_threshold: float = 0.6

@dataclass
class ResearchResult:
    """Result from research strategy execution"""
    strategy_name: str
    query: str
    success: bool
    results: List[Dict[str, Any]]
    quality_score: float
    confidence: float
    verification_status: str
    sources_analyzed: int
    languages_covered: List[str]
    execution_time: float
    errors: List[str] = None
    recommendations: List[str] = None

class ResearchStrategy(ABC):
    """Abstract base class for research strategies"""
    
    def __init__(self, name: str, description: str):
        self.name = name
        self.description = description
        
    @abstractmethod
    async def execute(self, context: ResearchContext) -> ResearchResult:
        """Execute the research strategy"""
        pass
    
    @abstractmethod
    def is_applicable(self, context: ResearchContext) -> bool:
        """Check if this strategy is applicable to the given context"""
        pass
    
    async def validate_context(self, context: ResearchContext) -> None:
        """Validate the research context"""
        if not context.query or not context.query.strip():
            raise JarvisValidationError("Research query cannot be empty")
        
        if context.max_depth < 1 or context.max_depth > 5:
            raise JarvisValidationError("Research depth must be between 1 and 5")
        
        if context.max_breadth < 1 or context.max_breadth > 20:
            raise JarvisValidationError("Research breadth must be between 1 and 20")

class DeepResearchStrategy(ResearchStrategy):
    """
    Multi-level recursive research strategy inspired by GPT Researcher.
    Implements deep, comprehensive research with multiple levels of investigation.
    """
    
    def __init__(self):
        super().__init__(
            "Deep Research",
            "Multi-level recursive research for comprehensive topic investigation"
        )
    
    def is_applicable(self, context: ResearchContext) -> bool:
        """Deep research is applicable for high priority, complex queries"""
        return (
            context.priority in [ResearchPriority.HIGH, ResearchPriority.CRITICAL] or
            context.max_depth > 2 or
            context.domain in ["academic", "technical", "business"]
        )
    
    async def execute(self, context: ResearchContext) -> ResearchResult:
        """Execute deep research strategy"""
        start_time = asyncio.get_event_loop().time()
        
        try:
            await self.validate_context(context)
            
            logger.info(f"Starting deep research for: {context.query[:100]}...")
            
            all_results = []
            quality_scores = []
            languages_covered = set()
            sources_analyzed = 0
            errors = []
            
            # Level 1: Initial broad research
            level1_results = await self._perform_research_level(
                context.query, 
                context, 
                level=1,
                breadth=context.max_breadth
            )
            
            all_results.extend(level1_results["results"])
            quality_scores.append(level1_results["quality_score"])
            languages_covered.update(level1_results["languages"])
            sources_analyzed += level1_results["sources_count"]
            
            # Generate follow-up questions for deeper research
            follow_up_queries = await self._generate_follow_up_queries(
                context.query,
                level1_results["results"]
            )
            
            # Level 2+: Deep dive research
            for level in range(2, context.max_depth + 1):
                if not follow_up_queries:
                    break
                
                level_results = []
                for query in follow_up_queries[:context.max_breadth // 2]:  # Reduce breadth at deeper levels
                    try:
                        deep_result = await self._perform_research_level(
                            query,
                            context,
                            level=level,
                            breadth=max(2, context.max_breadth // level)
                        )
                        level_results.extend(deep_result["results"])
                        quality_scores.append(deep_result["quality_score"])
                        languages_covered.update(deep_result["languages"])
                        sources_analyzed += deep_result["sources_count"]
                        
                    except Exception as e:
                        error_msg = f"Level {level} research failed for '{query}': {e}"
                        errors.append(error_msg)
                        logger.warning(error_msg)
                
                all_results.extend(level_results)
                
                # Generate next level questions
                if level < context.max_depth:
                    follow_up_queries = await self._generate_follow_up_queries(
                        context.query,
                        level_results
                    )
            
            # Calculate overall metrics
            overall_quality = sum(quality_scores) / len(quality_scores) if quality_scores else 0.0
            confidence = min(0.95, 0.5 + (len(all_results) / (context.max_breadth * context.max_depth)) * 0.45)
            
            # Determine verification status
            if context.verification_required and len(all_results) >= 3:
                verification_status = "VERIFIED"
            elif len(all_results) >= 2:
                verification_status = "PARTIALLY_VERIFIED"
            else:
                verification_status = "UNVERIFIED"
            
            execution_time = asyncio.get_event_loop().time() - start_time
            
            logger.info(f"Deep research completed: {len(all_results)} results, quality {overall_quality:.2f}")
            
            return ResearchResult(
                strategy_name=self.name,
                query=context.query,
                success=len(all_results) > 0,
                results=all_results,
                quality_score=overall_quality,
                confidence=confidence,
                verification_status=verification_status,
                sources_analyzed=sources_analyzed,
                languages_covered=list(languages_covered),
                execution_time=execution_time,
                errors=errors,
                recommendations=[
                    "Consider fact verification for critical claims",
                    "Cross-reference with domain-specific sources",
                    "Validate information across multiple languages"
                ]
            )
            
        except Exception as e:
            execution_time = asyncio.get_event_loop().time() - start_time
            logger.error(f"Deep research strategy failed: {e}")
            
            return ResearchResult(
                strategy_name=self.name,
                query=context.query,
                success=False,
                results=[],
                quality_score=0.0,
                confidence=0.0,
                verification_status="FAILED",
                sources_analyzed=0,
                languages_covered=[],
                execution_time=execution_time,
                errors=[str(e)]
            )
    
    async def _perform_research_level(
        self, 
        query: str, 
        context: ResearchContext, 
        level: int, 
        breadth: int
    ) -> Dict[str, Any]:
        """Perform research at a specific level"""
        
        results = []
        quality_scores = []
        languages = set()
        sources_count = 0
        
        # Use different research tools based on level and domain
        if level == 1:
            # Broad initial research
            try:
                # Use domain-specific research
                domain_result = await domain_specific_research.ainvoke({
                    "query": query,
                    "domain": context.domain,
                    "max_results": breadth,
                    "include_languages": context.languages
                })
                
                results.extend(domain_result["results"])
                quality_scores.append(domain_result["quality_metrics"]["overall_quality"])
                languages.update(domain_result["languages_covered"])
                sources_count += domain_result["total_results"]
                
            except Exception as e:
                logger.warning(f"Domain-specific research failed: {e}")
        
        else:
            # Deeper, more targeted research
            try:
                # Use advanced research tool for depth
                advanced_result = await advanced_research_tool.ainvoke({
                    "query": query,
                    "max_results": breadth
                })
                
                results.append({
                    "content": advanced_result,
                    "source": "advanced_research",
                    "level": level,
                    "query": query
                })
                
                # Detect language
                try:
                    lang_result = await detect_language_with_confidence.ainvoke({
                        "text": advanced_result[:1000]
                    })
                    languages.add(lang_result.get("language", "unknown"))
                except:
                    languages.add("unknown")
                
                quality_scores.append(0.7)  # Default quality for advanced research
                sources_count += 1
                
            except Exception as e:
                logger.warning(f"Advanced research failed: {e}")
        
        avg_quality = sum(quality_scores) / len(quality_scores) if quality_scores else 0.0
        
        return {
            "results": results,
            "quality_score": avg_quality,
            "languages": languages,
            "sources_count": sources_count
        }
    
    async def _generate_follow_up_queries(
        self, 
        original_query: str, 
        previous_results: List[Dict[str, Any]]
    ) -> List[str]:
        """Generate follow-up questions for deeper research"""
        
        # Simple keyword-based follow-up generation
        # In a real implementation, this would use LLM to generate intelligent follow-ups
        
        follow_ups = []
        
        # Extract key terms from results
        key_terms = set()
        for result in previous_results:
            content = result.get("content", "")
            if content:
                # Simple keyword extraction (would be enhanced with NLP)
                words = content.lower().split()
                important_words = [w for w in words if len(w) > 5 and w.isalpha()]
                key_terms.update(important_words[:10])  # Top 10 keywords
        
        # Generate follow-up queries
        query_templates = [
            f"{original_query} implications",
            f"{original_query} challenges",
            f"{original_query} future trends",
            f"{original_query} case studies",
            f"{original_query} alternatives"
        ]
        
        # Add key-term based queries
        for term in list(key_terms)[:3]:  # Top 3 key terms
            query_templates.append(f"{original_query} {term}")
        
        return query_templates[:5]  # Return top 5 follow-up queries

class FactVerificationStrategy(ResearchStrategy):
    """
    Strategy focused on fact verification and claim validation.
    Cross-validates information across multiple sources and languages.
    """
    
    def __init__(self):
        super().__init__(
            "Fact Verification",
            "Cross-validation of claims across multiple sources and languages"
        )
    
    def is_applicable(self, context: ResearchContext) -> bool:
        """Fact verification is applicable when verification is explicitly required"""
        return (
            context.verification_required or
            context.priority == ResearchPriority.CRITICAL or
            "verify" in context.query.lower() or
            "fact" in context.query.lower() or
            "true" in context.query.lower() or
            "false" in context.query.lower()
        )
    
    async def execute(self, context: ResearchContext) -> ResearchResult:
        """Execute fact verification strategy"""
        start_time = asyncio.get_event_loop().time()
        
        try:
            await self.validate_context(context)
            
            logger.info(f"Starting fact verification for: {context.query[:100]}...")
            
            # Extract claims from query
            claims = await self._extract_claims(context.query)
            
            all_results = []
            verification_results = []
            languages_covered = set()
            sources_analyzed = 0
            errors = []
            
            # Verify each claim
            for claim in claims:
                try:
                    verification_result = await verify_fact_claim.ainvoke({
                        "claim": claim,
                        "max_sources": context.max_breadth,
                        "languages": context.languages
                    })
                    
                    verification_results.append(verification_result)
                    all_results.append({
                        "type": "fact_verification",
                        "claim": claim,
                        "verification": verification_result
                    })
                    
                    languages_covered.update(verification_result["languages_checked"])
                    sources_analyzed += len(verification_result["supporting_sources"]) + len(verification_result["contradicting_sources"])
                    
                except Exception as e:
                    error_msg = f"Fact verification failed for claim '{claim}': {e}"
                    errors.append(error_msg)
                    logger.warning(error_msg)
            
            # Calculate overall verification status
            if verification_results:
                verified_count = sum(1 for vr in verification_results if vr["verification_status"] == "VERIFIED")
                disputed_count = sum(1 for vr in verification_results if vr["verification_status"] == "DISPUTED")
                
                if verified_count == len(verification_results):
                    overall_verification = "FULLY_VERIFIED"
                    confidence = min(0.95, sum(vr["confidence"] for vr in verification_results) / len(verification_results))
                elif disputed_count > 0:
                    overall_verification = "DISPUTED"
                    confidence = 0.5
                elif verified_count > len(verification_results) / 2:
                    overall_verification = "MOSTLY_VERIFIED"
                    confidence = 0.7
                else:
                    overall_verification = "UNVERIFIED"
                    confidence = 0.3
            else:
                overall_verification = "NO_CLAIMS_FOUND"
                confidence = 0.1
            
            quality_score = confidence  # Quality aligns with confidence for fact verification
            
            execution_time = asyncio.get_event_loop().time() - start_time
            
            logger.info(f"Fact verification completed: {overall_verification} with confidence {confidence:.2f}")
            
            return ResearchResult(
                strategy_name=self.name,
                query=context.query,
                success=len(verification_results) > 0,
                results=all_results,
                quality_score=quality_score,
                confidence=confidence,
                verification_status=overall_verification,
                sources_analyzed=sources_analyzed,
                languages_covered=list(languages_covered),
                execution_time=execution_time,
                errors=errors,
                recommendations=[
                    "Cross-reference disputed claims with additional sources",
                    "Consider temporal context for time-sensitive claims",
                    "Verify claims in multiple languages for global perspective"
                ]
            )
            
        except Exception as e:
            execution_time = asyncio.get_event_loop().time() - start_time
            logger.error(f"Fact verification strategy failed: {e}")
            
            return ResearchResult(
                strategy_name=self.name,
                query=context.query,
                success=False,
                results=[],
                quality_score=0.0,
                confidence=0.0,
                verification_status="FAILED",
                sources_analyzed=0,
                languages_covered=[],
                execution_time=execution_time,
                errors=[str(e)]
            )
    
    async def _extract_claims(self, query: str) -> List[str]:
        """Extract verifiable claims from the query"""
        # Simple claim extraction (would be enhanced with NLP)
        
        # Look for statement patterns
        claim_patterns = [
            query  # The entire query as a claim
        ]
        
        # Split on common separators
        if " and " in query:
            claim_patterns.extend(query.split(" and "))
        if ". " in query:
            claim_patterns.extend(query.split(". "))
        if "? " in query:
            claim_patterns.extend(query.split("? "))
        
        # Clean up claims
        claims = []
        for claim in claim_patterns:
            claim = claim.strip()
            if claim and len(claim) > 10:  # Filter out very short claims
                claims.append(claim)
        
        return claims[:3]  # Limit to top 3 claims

class DomainExpertiseStrategy(ResearchStrategy):
    """
    Strategy that adapts research approach based on domain expertise.
    Uses specialized knowledge and sources for different fields.
    """
    
    def __init__(self):
        super().__init__(
            "Domain Expertise",
            "Specialized research approach adapted to specific domains"
        )
    
    def is_applicable(self, context: ResearchContext) -> bool:
        """Domain expertise is applicable for specialized domains"""
        return context.domain != "general"
    
    async def execute(self, context: ResearchContext) -> ResearchResult:
        """Execute domain expertise strategy"""
        start_time = asyncio.get_event_loop().time()
        
        try:
            await self.validate_context(context)
            
            logger.info(f"Starting domain expertise research for '{context.domain}': {context.query[:100]}...")
            
            # Perform domain-specific research
            domain_result = await domain_specific_research.ainvoke({
                "query": context.query,
                "domain": context.domain,
                "max_results": context.max_breadth * 2,  # More results for specialized domains
                "include_languages": context.languages
            })
            
            all_results = domain_result["results"]
            quality_score = domain_result["quality_metrics"]["overall_quality"]
            languages_covered = domain_result["languages_covered"]
            sources_analyzed = domain_result["total_results"]
            
            # Domain-specific enhancements
            if context.domain == "academic":
                # Enhance with citation analysis
                enhanced_results = await self._enhance_academic_research(all_results, context)
                all_results.extend(enhanced_results)
                
            elif context.domain == "technical":
                # Enhance with implementation examples
                enhanced_results = await self._enhance_technical_research(all_results, context)
                all_results.extend(enhanced_results)
                
            elif context.domain == "business":
                # Enhance with market analysis
                enhanced_results = await self._enhance_business_research(all_results, context)
                all_results.extend(enhanced_results)
            
            # Calculate confidence based on domain-specific factors
            confidence = min(0.9, quality_score + (len(all_results) / (context.max_breadth * 2)) * 0.2)
            
            verification_status = "DOMAIN_VERIFIED" if quality_score >= context.quality_threshold else "PARTIALLY_VERIFIED"
            
            execution_time = asyncio.get_event_loop().time() - start_time
            
            logger.info(f"Domain research completed: {len(all_results)} results, quality {quality_score:.2f}")
            
            return ResearchResult(
                strategy_name=self.name,
                query=context.query,
                success=len(all_results) > 0,
                results=all_results,
                quality_score=quality_score,
                confidence=confidence,
                verification_status=verification_status,
                sources_analyzed=sources_analyzed,
                languages_covered=languages_covered,
                execution_time=execution_time,
                recommendations=[
                    f"Results specialized for {context.domain} domain",
                    "Consider consulting domain experts for validation",
                    "Cross-reference with latest domain-specific publications"
                ]
            )
            
        except Exception as e:
            execution_time = asyncio.get_event_loop().time() - start_time
            logger.error(f"Domain expertise strategy failed: {e}")
            
            return ResearchResult(
                strategy_name=self.name,
                query=context.query,
                success=False,
                results=[],
                quality_score=0.0,
                confidence=0.0,
                verification_status="FAILED",
                sources_analyzed=0,
                languages_covered=[],
                execution_time=execution_time,
                errors=[str(e)]
            )
    
    async def _enhance_academic_research(self, results: List[Dict], context: ResearchContext) -> List[Dict]:
        """Enhance research with academic-specific information"""
        enhanced = []
        
        # Look for citation patterns, peer review status, etc.
        for result in results[:3]:  # Enhance top 3 results
            content = result.get("content", "")
            if "citation" in content.lower() or "peer review" in content.lower():
                enhanced.append({
                    "type": "academic_enhancement",
                    "original_result": result,
                    "enhancement": "Academic source with citation/peer review indicators"
                })
        
        return enhanced
    
    async def _enhance_technical_research(self, results: List[Dict], context: ResearchContext) -> List[Dict]:
        """Enhance research with technical-specific information"""
        enhanced = []
        
        # Look for code examples, documentation, API references
        for result in results[:3]:
            content = result.get("content", "")
            if any(keyword in content.lower() for keyword in ["code", "api", "documentation", "example"]):
                enhanced.append({
                    "type": "technical_enhancement",
                    "original_result": result,
                    "enhancement": "Technical source with implementation details"
                })
        
        return enhanced
    
    async def _enhance_business_research(self, results: List[Dict], context: ResearchContext) -> List[Dict]:
        """Enhance research with business-specific information"""
        enhanced = []
        
        # Look for financial data, market analysis, industry reports
        for result in results[:3]:
            content = result.get("content", "")
            if any(keyword in content.lower() for keyword in ["market", "revenue", "analysis", "industry"]):
                enhanced.append({
                    "type": "business_enhancement",
                    "original_result": result,
                    "enhancement": "Business source with market/financial insights"
                })
        
        return enhanced

class RealTimeResearchStrategy(ResearchStrategy):
    """
    Strategy focused on real-time and current information.
    Prioritizes fresh information and trending topics.
    """
    
    def __init__(self):
        super().__init__(
            "Real-Time Research",
            "Research focused on current and real-time information"
        )
    
    def is_applicable(self, context: ResearchContext) -> bool:
        """Real-time research is applicable for time-sensitive queries"""
        return (
            context.time_sensitivity in ["real_time", "recent"] or
            any(keyword in context.query.lower() for keyword in [
                "latest", "recent", "current", "today", "breaking", "news", "update"
            ])
        )
    
    async def execute(self, context: ResearchContext) -> ResearchResult:
        """Execute real-time research strategy"""
        start_time = asyncio.get_event_loop().time()
        
        try:
            await self.validate_context(context)
            
            logger.info(f"Starting real-time research for: {context.query[:100]}...")
            
            # Determine time range based on context
            time_range = "24h" if context.time_sensitivity == "real_time" else "7d"
            
            # Perform real-time research
            realtime_result = await real_time_information_research.ainvoke({
                "query": context.query,
                "time_range": time_range,
                "max_results": context.max_breadth
            })
            
            all_results = realtime_result["results"]
            freshness_score = realtime_result["metrics"]["freshness_score"]
            sources_analyzed = realtime_result["metrics"]["total_results"]
            
            # Multi-language real-time research if specified
            languages_covered = []
            if context.languages and len(context.languages) > 1:
                try:
                    multilang_result = await multi_language_research.ainvoke({
                        "query": context.query,
                        "target_languages": context.languages,
                        "max_results_per_language": max(2, context.max_breadth // len(context.languages))
                    })
                    
                    # Add multi-language results
                    for lang, lang_results in multilang_result["language_results"].items():
                        if lang_results["result_count"] > 0:
                            all_results.append({
                                "type": "multilingual_realtime",
                                "language": lang,
                                "results": lang_results["results"]
                            })
                            languages_covered.append(lang)
                            sources_analyzed += lang_results["result_count"]
                    
                except Exception as e:
                    logger.warning(f"Multi-language real-time research failed: {e}")
            
            # Quality score based on freshness and source diversity
            quality_score = min(0.9, freshness_score * 0.7 + (len(all_results) / context.max_breadth) * 0.3)
            confidence = min(0.85, freshness_score * 0.8 + 0.2)  # Real-time has inherent uncertainty
            
            verification_status = "REAL_TIME_CURRENT" if freshness_score >= 0.7 else "MODERATELY_CURRENT"
            
            execution_time = asyncio.get_event_loop().time() - start_time
            
            logger.info(f"Real-time research completed: freshness {freshness_score:.2f}, quality {quality_score:.2f}")
            
            return ResearchResult(
                strategy_name=self.name,
                query=context.query,
                success=len(all_results) > 0,
                results=all_results,
                quality_score=quality_score,
                confidence=confidence,
                verification_status=verification_status,
                sources_analyzed=sources_analyzed,
                languages_covered=languages_covered,
                execution_time=execution_time,
                recommendations=[
                    "Information is time-sensitive and may change rapidly",
                    "Consider verifying breaking news from multiple sources",
                    "Monitor for updates to ensure continued accuracy"
                ]
            )
            
        except Exception as e:
            execution_time = asyncio.get_event_loop().time() - start_time
            logger.error(f"Real-time research strategy failed: {e}")
            
            return ResearchResult(
                strategy_name=self.name,
                query=context.query,
                success=False,
                results=[],
                quality_score=0.0,
                confidence=0.0,
                verification_status="FAILED",
                sources_analyzed=0,
                languages_covered=[],
                execution_time=execution_time,
                errors=[str(e)]
            )

def get_research_strategies() -> List[ResearchStrategy]:
    """Returns a list of available research strategies"""
    return [
        DeepResearchStrategy(),
        FactVerificationStrategy(),
        DomainExpertiseStrategy(),
        RealTimeResearchStrategy()
    ]

def select_optimal_strategy(context: ResearchContext) -> ResearchStrategy:
    """Select the most appropriate research strategy for the given context"""
    strategies = get_research_strategies()
    
    # Find applicable strategies
    applicable_strategies = [s for s in strategies if s.is_applicable(context)]
    
    if not applicable_strategies:
        # Default to deep research for complex cases
        return DeepResearchStrategy()
    
    # Priority-based selection
    if context.verification_required:
        fact_strategy = [s for s in applicable_strategies if isinstance(s, FactVerificationStrategy)]
        if fact_strategy:
            return fact_strategy[0]
    
    if context.time_sensitivity in ["real_time", "recent"]:
        realtime_strategy = [s for s in applicable_strategies if isinstance(s, RealTimeResearchStrategy)]
        if realtime_strategy:
            return realtime_strategy[0]
    
    if context.domain != "general":
        domain_strategy = [s for s in applicable_strategies if isinstance(s, DomainExpertiseStrategy)]
        if domain_strategy:
            return domain_strategy[0]
    
    # Default to first applicable strategy or deep research
    return applicable_strategies[0] if applicable_strategies else DeepResearchStrategy()
