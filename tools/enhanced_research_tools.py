"""
Enhanced Research Tools for Advanced Research Agent

This module provides sophisticated research tools that extend beyond basic search capabilities.
It includes fact verification, source credibility assessment, multi-language research,
domain-specific strategies, and research quality metrics.

The tools integrate with the language detection system and communication framework
to provide comprehensive research capabilities for the enhanced research agent.
"""

import asyncio
import logging
from datetime import datetime, timedelta
from typing import Dict, List, Optional, Tuple, Any
from dataclasses import dataclass
import re
import statistics
from urllib.parse import urlparse

import requests
from langchain_core.tools import tool
from bs4 import BeautifulSoup
import dateutil.parser

from tools.language_detection import detect_language_with_confidence, detect_multiple_languages
from tools.research_tools import (
    google_search_tool, 
    advanced_research_tool, 
    webpage_research_tool,
    validate_query,
    validate_url
)
from config.settings import get_settings
from utils.exceptions import JarvisValidationError, JarvisAPIError, JarvisToolError
from utils.logging_config import get_logger

# Initialize logger and settings
logger = get_logger(__name__)
settings = get_settings()

@dataclass
class SourceCredibility:
    """Represents the credibility assessment of a research source"""
    url: str
    domain: str
    authority_score: float  # 0.0 to 1.0
    recency_score: float   # 0.0 to 1.0
    consistency_score: float  # 0.0 to 1.0
    overall_score: float   # 0.0 to 1.0
    reasoning: str
    language: str
    detected_bias: Optional[str] = None

@dataclass
class FactVerificationResult:
    """Represents the result of fact verification"""
    claim: str
    verification_status: str  # "VERIFIED", "DISPUTED", "UNVERIFIED", "FALSE"
    confidence: float  # 0.0 to 1.0
    supporting_sources: List[SourceCredibility]
    contradicting_sources: List[SourceCredibility]
    verification_reasoning: str
    languages_checked: List[str]

@dataclass
class ResearchQualityMetrics:
    """Metrics for assessing research quality"""
    source_diversity: float  # 0.0 to 1.0
    credibility_average: float  # 0.0 to 1.0
    recency_average: float  # 0.0 to 1.0
    language_coverage: int  # Number of languages
    fact_verification_rate: float  # 0.0 to 1.0
    depth_score: float  # 0.0 to 1.0
    overall_quality: float  # 0.0 to 1.0

# Domain-specific trusted sources
TRUSTED_DOMAINS = {
    "academic": [
        "scholar.google.com", "pubmed.ncbi.nlm.nih.gov", "arxiv.org", 
        "jstor.org", "springer.com", "elsevier.com", "nature.com",
        "science.org", "pnas.org", "ieee.org"
    ],
    "news": [
        "reuters.com", "ap.org", "bbc.com", "npr.org", "pbs.org",
        "theguardian.com", "wsj.com", "nytimes.com", "washingtonpost.com"
    ],
    "technical": [
        "stackoverflow.com", "github.com", "developer.mozilla.org",
        "docs.python.org", "kubernetes.io", "docker.com", "microsoft.com"
    ],
    "business": [
        "bloomberg.com", "fortune.com", "forbes.com", "businessinsider.com",
        "hbr.org", "mckinsey.com", "pwc.com", "deloitte.com"
    ],
    "government": [
        "gov", "edu", "who.int", "un.org", "worldbank.org", 
        "imf.org", "oecd.org", "fda.gov", "cdc.gov"
    ]
}

def get_domain_authority_score(domain: str, research_domain: str = "general") -> float:
    """Calculate domain authority score based on trusted sources"""
    # Check if domain is in trusted sources for specific research domain
    if research_domain in TRUSTED_DOMAINS:
        if domain in TRUSTED_DOMAINS[research_domain]:
            return 0.9
    
    # Check if domain is in any trusted category
    for category_domains in TRUSTED_DOMAINS.values():
        if domain in category_domains:
            return 0.8
    
    # Check for edu/gov domains
    if domain.endswith('.edu') or domain.endswith('.gov'):
        return 0.85
    
    # Check for org domains
    if domain.endswith('.org'):
        return 0.7
    
    # Default score for other domains
    return 0.5

def calculate_recency_score(published_date: Optional[str]) -> float:
    """Calculate recency score based on publication date"""
    if not published_date:
        return 0.5  # Default for unknown dates
    
    try:
        pub_date = dateutil.parser.parse(published_date)
        now = datetime.now(pub_date.tzinfo) if pub_date.tzinfo else datetime.now()
        days_old = (now - pub_date).days
        
        # More recent is better
        if days_old <= 30:
            return 1.0
        elif days_old <= 90:
            return 0.9
        elif days_old <= 365:
            return 0.7
        elif days_old <= 365 * 2:
            return 0.5
        else:
            return 0.3
    except:
        return 0.5

@tool
async def assess_source_credibility(
    url: str, 
    content: str = "", 
    research_domain: str = "general"
) -> Dict[str, Any]:
    """
    Assess the credibility of a research source based on multiple factors.
    
    Args:
        url: The URL of the source to assess
        content: Optional content from the source for analysis
        research_domain: The domain of research (academic, news, technical, business, government)
        
    Returns:
        Dict containing credibility assessment with scores and reasoning
        
    Raises:
        JarvisValidationError: If URL is invalid
        JarvisToolError: If assessment fails
    """
    try:
        # Validate inputs
        url = validate_url(url)
        parsed_url = urlparse(url)
        domain = parsed_url.netloc.lower().replace('www.', '')
        
        logger.info(f"Assessing credibility for domain: {domain}")
        
        # Calculate authority score
        authority_score = get_domain_authority_score(domain, research_domain)
        
        # Calculate recency score (try to extract date from content or URL)
        recency_score = 0.5  # Default
        if content:
            # Look for publication dates in content
            date_patterns = [
                r'published[:\s]+([0-9]{1,2}[/-][0-9]{1,2}[/-][0-9]{2,4})',
                r'([0-9]{4}-[0-9]{2}-[0-9]{2})',
                r'(\w+\s+[0-9]{1,2},\s+[0-9]{4})'
            ]
            for pattern in date_patterns:
                match = re.search(pattern, content, re.IGNORECASE)
                if match:
                    recency_score = calculate_recency_score(match.group(1))
                    break
        
        # Calculate consistency score (placeholder for now)
        consistency_score = 0.8  # Would require cross-referencing multiple sources
        
        # Detect language
        language = "unknown"
        if content:
            try:
                lang_result = await detect_language_with_confidence.ainvoke({"text": content[:1000]})
                language = lang_result.get("language", "unknown")
            except:
                pass
        
        # Calculate overall score
        overall_score = (authority_score * 0.4 + recency_score * 0.3 + consistency_score * 0.3)
        
        # Generate reasoning
        reasoning_parts = []
        if authority_score >= 0.8:
            reasoning_parts.append("High authority domain")
        elif authority_score >= 0.6:
            reasoning_parts.append("Moderate authority domain")
        else:
            reasoning_parts.append("Lower authority domain")
            
        if recency_score >= 0.8:
            reasoning_parts.append("recent publication")
        elif recency_score >= 0.6:
            reasoning_parts.append("moderately recent")
        else:
            reasoning_parts.append("older publication")
            
        reasoning = f"Assessment based on: {', '.join(reasoning_parts)}"
        
        # Create credibility result
        credibility = SourceCredibility(
            url=url,
            domain=domain,
            authority_score=authority_score,
            recency_score=recency_score,
            consistency_score=consistency_score,
            overall_score=overall_score,
            reasoning=reasoning,
            language=language
        )
        
        logger.info(f"Credibility assessment completed for {domain}: {overall_score:.2f}")
        
        return {
            "url": credibility.url,
            "domain": credibility.domain,
            "authority_score": credibility.authority_score,
            "recency_score": credibility.recency_score,
            "consistency_score": credibility.consistency_score,
            "overall_score": credibility.overall_score,
            "reasoning": credibility.reasoning,
            "language": credibility.language,
            "detected_bias": credibility.detected_bias
        }
        
    except JarvisValidationError:
        raise
    except Exception as e:
        logger.error(f"Source credibility assessment failed: {e}")
        raise JarvisToolError(f"Source credibility assessment failed: {e}")

@tool
async def verify_fact_claim(
    claim: str, 
    max_sources: int = 5,
    languages: Optional[List[str]] = None
) -> Dict[str, Any]:
    """
    Verify a factual claim by cross-referencing multiple sources.
    
    Args:
        claim: The claim to verify
        max_sources: Maximum number of sources to check
        languages: List of languages to search in (defaults to English)
        
    Returns:
        Dict containing verification result with supporting/contradicting evidence
        
    Raises:
        JarvisValidationError: If claim is invalid
        JarvisToolError: If verification fails
    """
    try:
        # Validate inputs
        claim = validate_query(claim)
        if languages is None:
            languages = ["english"]
        
        logger.info(f"Verifying claim: {claim[:100]}...")
        
        # Perform multi-language searches
        supporting_sources = []
        contradicting_sources = []
        
        for language in languages:
            # Create language-specific search query
            if language != "english":
                search_query = f"{claim} (in {language})"
            else:
                search_query = claim
            
            # Search for information
            try:
                search_results = await google_search_tool.ainvoke({
                    "query": search_query,
                    "max_results": max_sources
                })
                
                # Analyze search results
                organic_results = search_results.get("organic", [])
                
                for result in organic_results[:max_sources]:
                    url = result.get("link", "")
                    if not url:
                        continue
                    
                    # Get page content
                    try:
                        content = await webpage_research_tool.ainvoke({"url": url})
                        
                        # Assess source credibility
                        credibility_result = await assess_source_credibility.ainvoke({
                            "url": url,
                            "content": content,
                            "research_domain": "general"
                        })
                        
                        credibility = SourceCredibility(
                            url=url,
                            domain=credibility_result["domain"],
                            authority_score=credibility_result["authority_score"],
                            recency_score=credibility_result["recency_score"],
                            consistency_score=credibility_result["consistency_score"],
                            overall_score=credibility_result["overall_score"],
                            reasoning=credibility_result["reasoning"],
                            language=credibility_result["language"]
                        )
                        
                        # Simple claim verification (would be enhanced with NLP)
                        content_lower = content.lower()
                        claim_lower = claim.lower()
                        
                        # Basic keyword matching (would be enhanced with semantic analysis)
                        claim_keywords = claim_lower.split()
                        matches = sum(1 for keyword in claim_keywords if keyword in content_lower)
                        
                        if matches >= len(claim_keywords) * 0.6:  # 60% keyword match
                            if credibility.overall_score >= 0.6:
                                supporting_sources.append(credibility)
                        
                    except Exception as e:
                        logger.warning(f"Failed to process result {url}: {e}")
                        continue
                        
            except Exception as e:
                logger.warning(f"Search failed for language {language}: {e}")
                continue
        
        # Determine verification status
        if len(supporting_sources) >= 2:
            verification_status = "VERIFIED"
            confidence = min(0.9, 0.6 + len(supporting_sources) * 0.1)
        elif len(supporting_sources) == 1:
            verification_status = "PARTIALLY_VERIFIED"
            confidence = 0.6
        elif len(contradicting_sources) >= 2:
            verification_status = "DISPUTED"
            confidence = 0.7
        else:
            verification_status = "UNVERIFIED"
            confidence = 0.3
            
        verification_reasoning = f"Found {len(supporting_sources)} supporting sources and {len(contradicting_sources)} contradicting sources across {len(languages)} languages"
        
        # Create verification result
        result = FactVerificationResult(
            claim=claim,
            verification_status=verification_status,
            confidence=confidence,
            supporting_sources=supporting_sources,
            contradicting_sources=contradicting_sources,
            verification_reasoning=verification_reasoning,
            languages_checked=languages
        )
        
        logger.info(f"Fact verification completed: {verification_status} with confidence {confidence:.2f}")
        
        return {
            "claim": result.claim,
            "verification_status": result.verification_status,
            "confidence": result.confidence,
            "supporting_sources": [
                {
                    "url": src.url,
                    "domain": src.domain,
                    "overall_score": src.overall_score,
                    "reasoning": src.reasoning
                } for src in result.supporting_sources
            ],
            "contradicting_sources": [
                {
                    "url": src.url,
                    "domain": src.domain,
                    "overall_score": src.overall_score,
                    "reasoning": src.reasoning
                } for src in result.contradicting_sources
            ],
            "verification_reasoning": result.verification_reasoning,
            "languages_checked": result.languages_checked
        }
        
    except JarvisValidationError:
        raise
    except Exception as e:
        logger.error(f"Fact verification failed: {e}")
        raise JarvisToolError(f"Fact verification failed: {e}")

@tool
async def domain_specific_research(
    query: str,
    domain: str = "general",
    max_results: int = 10,
    include_languages: Optional[List[str]] = None
) -> Dict[str, Any]:
    """
    Perform domain-specific research with specialized strategies.
    
    Args:
        query: The research query
        domain: Research domain (academic, technical, business, news, government)
        max_results: Maximum number of results
        include_languages: Languages to include in research
        
    Returns:
        Dict containing domain-specific research results with quality metrics
        
    Raises:
        JarvisValidationError: If inputs are invalid
        JarvisToolError: If research fails
    """
    try:
        # Validate inputs
        query = validate_query(query)
        if include_languages is None:
            include_languages = ["english"]
        
        logger.info(f"Performing domain-specific research for '{domain}': {query[:100]}...")
        
        # Domain-specific search strategies
        search_queries = []
        
        if domain == "academic":
            search_queries = [
                f"{query} site:scholar.google.com",
                f"{query} site:pubmed.ncbi.nlm.nih.gov",
                f"{query} site:arxiv.org",
                f"{query} peer reviewed",
                f"{query} research study"
            ]
        elif domain == "technical":
            search_queries = [
                f"{query} site:stackoverflow.com",
                f"{query} site:github.com",
                f"{query} documentation",
                f"{query} API reference",
                f"{query} technical guide"
            ]
        elif domain == "business":
            search_queries = [
                f"{query} site:bloomberg.com",
                f"{query} site:forbes.com",
                f"{query} market analysis",
                f"{query} business report",
                f"{query} industry trends"
            ]
        elif domain == "news":
            search_queries = [
                f"{query} site:reuters.com",
                f"{query} site:ap.org",
                f"{query} site:bbc.com",
                f"{query} breaking news",
                f"{query} latest news"
            ]
        else:  # general
            search_queries = [query]
        
        # Collect results from all search strategies
        all_results = []
        credibility_scores = []
        
        for search_query in search_queries[:3]:  # Limit to top 3 strategies
            try:
                # Perform search
                if domain in ["academic", "technical"]:
                    # Use advanced research for technical/academic domains
                    result_text = await advanced_research_tool.ainvoke({
                        "query": search_query,
                        "max_results": max_results // len(search_queries)
                    })
                else:
                    # Use Google search for other domains
                    search_results = await google_search_tool.ainvoke({
                        "query": search_query,
                        "max_results": max_results // len(search_queries)
                    })
                    result_text = str(search_results)
                
                # Assess language and quality
                try:
                    lang_result = await detect_language_with_confidence.ainvoke({"text": result_text[:1000]})
                    detected_language = lang_result.get("language", "unknown")
                except:
                    detected_language = "unknown"
                
                # Simple quality assessment based on domain relevance
                domain_keywords = {
                    "academic": ["study", "research", "paper", "journal", "analysis"],
                    "technical": ["documentation", "API", "code", "implementation", "guide"],
                    "business": ["market", "revenue", "profit", "strategy", "analysis"],
                    "news": ["reported", "breaking", "latest", "update", "announced"]
                }
                
                quality_score = 0.5  # Default
                if domain in domain_keywords:
                    keywords = domain_keywords[domain]
                    matches = sum(1 for keyword in keywords if keyword.lower() in result_text.lower())
                    quality_score = min(1.0, 0.5 + (matches / len(keywords)) * 0.5)
                
                credibility_scores.append(quality_score)
                
                all_results.append({
                    "search_strategy": search_query,
                    "content": result_text,
                    "language": detected_language,
                    "quality_score": quality_score,
                    "domain_relevance": domain
                })
                
            except Exception as e:
                logger.warning(f"Search strategy '{search_query}' failed: {e}")
                continue
        
        # Calculate research quality metrics
        if credibility_scores:
            metrics = ResearchQualityMetrics(
                source_diversity=len(all_results) / max(len(search_queries), 1),
                credibility_average=statistics.mean(credibility_scores),
                recency_average=0.7,  # Placeholder
                language_coverage=len(set(r["language"] for r in all_results)),
                fact_verification_rate=0.0,  # Would be calculated with fact checking
                depth_score=len(all_results) / max_results,
                overall_quality=statistics.mean(credibility_scores) * 0.7 + 
                              (len(all_results) / max_results) * 0.3
            )
        else:
            metrics = ResearchQualityMetrics(
                source_diversity=0.0,
                credibility_average=0.0,
                recency_average=0.0,
                language_coverage=0,
                fact_verification_rate=0.0,
                depth_score=0.0,
                overall_quality=0.0
            )
        
        logger.info(f"Domain research completed with quality score: {metrics.overall_quality:.2f}")
        
        return {
            "query": query,
            "domain": domain,
            "results": all_results,
            "quality_metrics": {
                "source_diversity": metrics.source_diversity,
                "credibility_average": metrics.credibility_average,
                "recency_average": metrics.recency_average,
                "language_coverage": metrics.language_coverage,
                "fact_verification_rate": metrics.fact_verification_rate,
                "depth_score": metrics.depth_score,
                "overall_quality": metrics.overall_quality
            },
            "languages_covered": list(set(r["language"] for r in all_results)),
            "total_results": len(all_results)
        }
        
    except JarvisValidationError:
        raise
    except Exception as e:
        logger.error(f"Domain-specific research failed: {e}")
        raise JarvisToolError(f"Domain-specific research failed: {e}")

@tool
async def multi_language_research(
    query: str,
    target_languages: Optional[List[str]] = None,
    max_results_per_language: int = 5
) -> Dict[str, Any]:
    """
    Conduct research across multiple languages for comprehensive coverage.
    
    Args:
        query: The research query
        target_languages: List of languages to research in
        max_results_per_language: Maximum results per language
        
    Returns:
        Dict containing multi-language research results
        
    Raises:
        JarvisValidationError: If inputs are invalid
        JarvisToolError: If research fails
    """
    try:
        # Validate inputs
        query = validate_query(query)
        if target_languages is None:
            target_languages = ["english", "spanish", "french", "german", "chinese"]
        
        logger.info(f"Performing multi-language research in {len(target_languages)} languages")
        
        # Research results by language
        language_results = {}
        
        for language in target_languages:
            try:
                # Create language-specific query
                if language == "english":
                    search_query = query
                else:
                    search_query = f"{query} language:{language}"
                
                # Perform search
                search_results = await google_search_tool.ainvoke({
                    "query": search_query,
                    "max_results": max_results_per_language
                })
                
                # Process results
                organic_results = search_results.get("organic", [])
                processed_results = []
                
                for result in organic_results:
                    url = result.get("link", "")
                    snippet = result.get("snippet", "")
                    
                    if url and snippet:
                        # Detect actual language of snippet
                        try:
                            lang_result = await detect_language_with_confidence.ainvoke({"text": snippet})
                            detected_lang = lang_result.get("language", "unknown")
                            confidence = lang_result.get("confidence", 0.0)
                        except:
                            detected_lang = "unknown"
                            confidence = 0.0
                        
                        processed_results.append({
                            "url": url,
                            "snippet": snippet,
                            "detected_language": detected_lang,
                            "language_confidence": confidence,
                            "title": result.get("title", "")
                        })
                
                language_results[language] = {
                    "target_language": language,
                    "results": processed_results,
                    "result_count": len(processed_results)
                }
                
                logger.info(f"Found {len(processed_results)} results for {language}")
                
            except Exception as e:
                logger.warning(f"Research in {language} failed: {e}")
                language_results[language] = {
                    "target_language": language,
                    "results": [],
                    "result_count": 0,
                    "error": str(e)
                }
        
        # Calculate coverage metrics
        total_results = sum(lr["result_count"] for lr in language_results.values())
        successful_languages = sum(1 for lr in language_results.values() if lr["result_count"] > 0)
        
        logger.info(f"Multi-language research completed: {total_results} results across {successful_languages} languages")
        
        return {
            "query": query,
            "target_languages": target_languages,
            "language_results": language_results,
            "summary": {
                "total_results": total_results,
                "successful_languages": successful_languages,
                "coverage_rate": successful_languages / len(target_languages),
                "average_results_per_language": total_results / len(target_languages) if target_languages else 0
            }
        }
        
    except JarvisValidationError:
        raise
    except Exception as e:
        logger.error(f"Multi-language research failed: {e}")
        raise JarvisToolError(f"Multi-language research failed: {e}")

@tool
async def real_time_information_research(
    query: str,
    time_range: str = "24h",
    max_results: int = 10
) -> Dict[str, Any]:
    """
    Research focused on real-time and recent information.
    
    Args:
        query: The research query
        time_range: Time range for results (24h, 7d, 30d, 1y)
        max_results: Maximum number of results
        
    Returns:
        Dict containing real-time research results
        
    Raises:
        JarvisValidationError: If inputs are invalid
        JarvisToolError: If research fails
    """
    try:
        # Validate inputs
        query = validate_query(query)
        
        logger.info(f"Performing real-time research for: {query[:100]}...")
        
        # Create time-sensitive search queries
        time_queries = [
            f"{query} {time_range}",
            f"{query} recent",
            f"{query} latest",
            f"{query} breaking",
            f"{query} update",
            f"{query} news"
        ]
        
        recent_results = []
        
        for time_query in time_queries[:3]:  # Limit to top 3 time-sensitive queries
            try:
                # Use advanced research for real-time information
                result_text = await advanced_research_tool.ainvoke({
                    "query": time_query,
                    "max_results": max_results // 3
                })
                
                # Calculate recency score based on content
                recency_indicators = ["today", "yesterday", "this week", "breaking", "update", "latest"]
                recency_score = sum(1 for indicator in recency_indicators 
                                  if indicator in result_text.lower()) / len(recency_indicators)
                
                recent_results.append({
                    "query": time_query,
                    "content": result_text,
                    "recency_score": recency_score,
                    "timestamp": datetime.now().isoformat()
                })
                
            except Exception as e:
                logger.warning(f"Real-time search '{time_query}' failed: {e}")
                continue
        
        # Sort by recency score
        recent_results.sort(key=lambda x: x["recency_score"], reverse=True)
        
        # Calculate overall recency metrics
        if recent_results:
            avg_recency = statistics.mean(r["recency_score"] for r in recent_results)
            freshness_score = min(1.0, avg_recency * 2)  # Scale to 0-1
        else:
            avg_recency = 0.0
            freshness_score = 0.0
        
        logger.info(f"Real-time research completed with freshness score: {freshness_score:.2f}")
        
        return {
            "query": query,
            "time_range": time_range,
            "results": recent_results,
            "metrics": {
                "total_results": len(recent_results),
                "average_recency_score": avg_recency,
                "freshness_score": freshness_score,
                "search_timestamp": datetime.now().isoformat()
            }
        }
        
    except JarvisValidationError:
        raise
    except Exception as e:
        logger.error(f"Real-time research failed: {e}")
        raise JarvisToolError(f"Real-time research failed: {e}")

def get_enhanced_research_tools() -> List:
    """
    Returns a list of enhanced research tool functions.
    
    These tools provide advanced research capabilities including:
    - Source credibility assessment
    - Fact verification across multiple sources
    - Domain-specific research strategies
    - Multi-language research capabilities
    - Real-time information focus
    """
    return [
        assess_source_credibility,
        verify_fact_claim,
        domain_specific_research,
        multi_language_research,
        real_time_information_research
    ]
