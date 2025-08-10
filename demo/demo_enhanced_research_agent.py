"""
Enhanced Research Agent Demo

This demo showcases the advanced capabilities of the Enhanced Research Agent,
including deep research, fact verification, multi-language research, domain
expertise, and real-time information gathering.

The demo integrates with Phase 2B.2 communication framework and Phase 2B.3
language detection to demonstrate the complete enhanced agent system.
"""

import asyncio
import logging
from datetime import datetime
from typing import Dict, List, Any
import json
import sys
import os

# Add the project root to Python path
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from agents.enhanced_research_agent import create_enhanced_research_agent
from utils.research_strategies import ResearchPriority
from utils.logging_config import get_logger

# Initialize logger
logger = get_logger(__name__)
logging.basicConfig(level=logging.INFO)

class EnhancedResearchAgentDemo:
    """Demo class for Enhanced Research Agent capabilities"""
    
    def __init__(self):
        self.agent = None
        self.demo_results = []
    
    async def initialize(self):
        """Initialize the demo environment"""
        print("🚀 Initializing Enhanced Research Agent Demo...")
        print("=" * 60)
        
        try:
            # Create enhanced research agent
            self.agent = await create_enhanced_research_agent(
                agent_id="demo_enhanced_research_agent",
                model_config={
                    "provider": "openai",
                    "model": "gpt-4",
                    "temperature": 0.3
                }
            )
            
            print(f"✅ Enhanced Research Agent initialized successfully!")
            print(f"   Agent ID: {self.agent.agent_id}")
            print(f"   Agent Name: {self.agent.agent_name}")
            print(f"   Agent Type: {self.agent.agent_type}")
            
            # Get agent status
            status = await self.agent.get_agent_status()
            print(f"   Status: {status['state']}")
            print(f"   Strategies Available: {status['research_strategies_available']}")
            print(f"   Tools Available: {status['research_tools_available']}")
            print(f"   Supported Languages: {len(status['supported_languages'])}")
            print(f"   Supported Domains: {len(status['supported_domains'])}")
            print()
            
            return True
            
        except Exception as e:
            print(f"❌ Initialization failed: {e}")
            logger.error(f"Demo initialization failed: {e}")
            return False
    
    async def demo_basic_research(self):
        """Demonstrate basic enhanced research capabilities"""
        print("📊 Demo 1: Basic Enhanced Research")
        print("-" * 40)
        
        try:
            query = "What are the latest developments in artificial intelligence in 2024?"
            
            print(f"🔍 Research Query: {query}")
            print("⏳ Conducting research...")
            
            # Conduct basic research
            result = await self.agent.conduct_research(
                query=query,
                domain="technology",
                priority="medium",
                max_depth=2,
                max_breadth=5
            )
            
            # Display results
            print(f"✅ Research completed successfully!")
            print(f"   Research ID: {result['research_id']}")
            print(f"   Strategy Used: {result['strategy_used']}")
            print(f"   Quality Score: {result['quality_metrics']['overall_quality_score']:.2f}")
            print(f"   Confidence: {result['quality_metrics']['confidence']:.2f}")
            print(f"   Verification Status: {result['quality_metrics']['verification_status']}")
            print(f"   Sources Analyzed: {result['quality_metrics']['sources_analyzed']}")
            print(f"   Languages Covered: {result['quality_metrics']['languages_covered']}")
            print(f"   Execution Time: {result['quality_metrics']['execution_time']:.2f}s")
            
            # Show quality assessment
            quality_assessment = result['quality_assessment']
            print(f"   Overall Assessment: {quality_assessment['overall_assessment']:.2f}")
            print(f"   Meets Threshold: {quality_assessment['meets_threshold']}")
            
            if result['recommendations']:
                print("   Recommendations:")
                for rec in result['recommendations']:
                    print(f"     • {rec}")
            
            self.demo_results.append({
                "demo": "Basic Research",
                "success": result['success'],
                "quality_score": result['quality_metrics']['overall_quality_score'],
                "execution_time": result['quality_metrics']['execution_time']
            })
            
            print()
            return True
            
        except Exception as e:
            print(f"❌ Basic research demo failed: {e}")
            logger.error(f"Basic research demo failed: {e}")
            return False
    
    async def demo_fact_verification(self):
        """Demonstrate fact verification capabilities"""
        print("🔍 Demo 2: Fact Verification")
        print("-" * 40)
        
        try:
            # Test multiple claims
            test_claims = [
                "The Earth orbits around the Sun",
                "Python is a programming language created by Guido van Rossum",
                "The Great Wall of China is visible from space with the naked eye"
            ]
            
            verification_results = []
            
            for claim in test_claims:
                print(f"🔬 Verifying claim: {claim}")
                print("⏳ Checking sources...")
                
                try:
                    result = await self.agent.verify_fact(
                        claim=claim,
                        max_sources=5,
                        languages=["english"]
                    )
                    
                    verification_results.append(result)
                    
                    print(f"   Status: {result['verification_status']}")
                    print(f"   Confidence: {result['confidence']:.2f}")
                    print(f"   Supporting Sources: {len(result['supporting_sources'])}")
                    print(f"   Contradicting Sources: {len(result['contradicting_sources'])}")
                    print(f"   Languages Checked: {result['languages_checked']}")
                    print()
                    
                except Exception as e:
                    print(f"   ❌ Verification failed: {e}")
                    print()
            
            # Summary
            if verification_results:
                verified_count = sum(1 for r in verification_results if r['verification_status'] == 'VERIFIED')
                avg_confidence = sum(r['confidence'] for r in verification_results) / len(verification_results)
                
                print(f"📊 Verification Summary:")
                print(f"   Claims Tested: {len(test_claims)}")
                print(f"   Successfully Verified: {verified_count}")
                print(f"   Average Confidence: {avg_confidence:.2f}")
                
                self.demo_results.append({
                    "demo": "Fact Verification",
                    "success": len(verification_results) > 0,
                    "verification_rate": verified_count / len(test_claims),
                    "average_confidence": avg_confidence
                })
            
            print()
            return True
            
        except Exception as e:
            print(f"❌ Fact verification demo failed: {e}")
            logger.error(f"Fact verification demo failed: {e}")
            return False
    
    async def demo_domain_expertise(self):
        """Demonstrate domain-specific research capabilities"""
        print("🎓 Demo 3: Domain Expertise Research")
        print("-" * 40)
        
        try:
            # Test different domains
            domain_queries = [
                ("academic", "machine learning algorithms for natural language processing"),
                ("technical", "best practices for microservices architecture"),
                ("business", "market trends in renewable energy sector"),
                ("news", "latest developments in space exploration")
            ]
            
            domain_results = []
            
            for domain, query in domain_queries:
                print(f"🏛️  Domain: {domain.upper()}")
                print(f"🔍 Query: {query}")
                print("⏳ Conducting domain-specific research...")
                
                try:
                    result = await self.agent.conduct_research(
                        query=query,
                        domain=domain,
                        priority="high",
                        max_depth=2,
                        max_breadth=3
                    )
                    
                    domain_results.append({
                        "domain": domain,
                        "result": result
                    })
                    
                    print(f"   ✅ Strategy: {result['strategy_used']}")
                    print(f"   📊 Quality Score: {result['quality_metrics']['overall_quality_score']:.2f}")
                    print(f"   🎯 Confidence: {result['quality_metrics']['confidence']:.2f}")
                    print(f"   📚 Sources: {result['quality_metrics']['sources_analyzed']}")
                    print()
                    
                except Exception as e:
                    print(f"   ❌ Domain research failed: {e}")
                    print()
            
            # Summary
            if domain_results:
                avg_quality = sum(r['result']['quality_metrics']['overall_quality_score'] for r in domain_results) / len(domain_results)
                successful_domains = sum(1 for r in domain_results if r['result']['success'])
                
                print(f"📊 Domain Expertise Summary:")
                print(f"   Domains Tested: {len(domain_queries)}")
                print(f"   Successful Researches: {successful_domains}")
                print(f"   Average Quality Score: {avg_quality:.2f}")
                
                self.demo_results.append({
                    "demo": "Domain Expertise",
                    "success": successful_domains > 0,
                    "domains_tested": len(domain_queries),
                    "success_rate": successful_domains / len(domain_queries),
                    "average_quality": avg_quality
                })
            
            print()
            return True
            
        except Exception as e:
            print(f"❌ Domain expertise demo failed: {e}")
            logger.error(f"Domain expertise demo failed: {e}")
            return False
    
    async def demo_multi_language_research(self):
        """Demonstrate multi-language research capabilities"""
        print("🌍 Demo 4: Multi-Language Research")
        print("-" * 40)
        
        try:
            # Test multi-language queries
            multilang_queries = [
                {
                    "query": "artificial intelligence",
                    "languages": ["english", "spanish", "french"],
                    "description": "AI research in multiple languages"
                },
                {
                    "query": "climate change solutions",
                    "languages": ["english", "german", "chinese"],
                    "description": "Climate solutions globally"
                }
            ]
            
            multilang_results = []
            
            for query_info in multilang_queries:
                query = query_info["query"]
                languages = query_info["languages"]
                description = query_info["description"]
                
                print(f"🔍 Query: {query} ({description})")
                print(f"🌐 Languages: {', '.join(languages)}")
                print("⏳ Conducting multi-language research...")
                
                try:
                    result = await self.agent.conduct_research(
                        query=query,
                        languages=languages,
                        priority="medium",
                        max_depth=1,
                        max_breadth=4
                    )
                    
                    multilang_results.append(result)
                    
                    languages_found = result['quality_metrics']['languages_covered']
                    coverage_rate = len(languages_found) / len(languages)
                    
                    print(f"   ✅ Languages Found: {languages_found}")
                    print(f"   📊 Coverage Rate: {coverage_rate:.2f}")
                    print(f"   🎯 Quality Score: {result['quality_metrics']['overall_quality_score']:.2f}")
                    print(f"   📚 Sources: {result['quality_metrics']['sources_analyzed']}")
                    print()
                    
                except Exception as e:
                    print(f"   ❌ Multi-language research failed: {e}")
                    print()
            
            # Summary
            if multilang_results:
                total_languages_requested = sum(len(q["languages"]) for q in multilang_queries)
                total_languages_found = sum(len(r['quality_metrics']['languages_covered']) for r in multilang_results)
                overall_coverage = total_languages_found / total_languages_requested if total_languages_requested > 0 else 0
                
                print(f"📊 Multi-Language Summary:")
                print(f"   Queries Tested: {len(multilang_queries)}")
                print(f"   Languages Requested: {total_languages_requested}")
                print(f"   Languages Found: {total_languages_found}")
                print(f"   Overall Coverage Rate: {overall_coverage:.2f}")
                
                self.demo_results.append({
                    "demo": "Multi-Language Research",
                    "success": len(multilang_results) > 0,
                    "coverage_rate": overall_coverage,
                    "languages_found": total_languages_found
                })
            
            print()
            return True
            
        except Exception as e:
            print(f"❌ Multi-language research demo failed: {e}")
            logger.error(f"Multi-language research demo failed: {e}")
            return False
    
    async def demo_real_time_research(self):
        """Demonstrate real-time research capabilities"""
        print("⚡ Demo 5: Real-Time Research")
        print("-" * 40)
        
        try:
            # Test real-time queries
            realtime_queries = [
                "latest news in artificial intelligence today",
                "breaking developments in renewable energy",
                "current stock market trends"
            ]
            
            realtime_results = []
            
            for query in realtime_queries:
                print(f"📡 Real-time Query: {query}")
                print("⏳ Gathering fresh information...")
                
                try:
                    result = await self.agent.conduct_research(
                        query=query,
                        time_sensitivity="real_time",
                        priority="high",
                        max_depth=1,
                        max_breadth=5
                    )
                    
                    realtime_results.append(result)
                    
                    print(f"   ⚡ Strategy: {result['strategy_used']}")
                    print(f"   🕒 Time Sensitivity: {result['context']['time_sensitivity']}")
                    print(f"   📊 Quality Score: {result['quality_metrics']['overall_quality_score']:.2f}")
                    print(f"   🎯 Confidence: {result['quality_metrics']['confidence']:.2f}")
                    print(f"   ⏱️  Execution Time: {result['quality_metrics']['execution_time']:.2f}s")
                    print()
                    
                except Exception as e:
                    print(f"   ❌ Real-time research failed: {e}")
                    print()
            
            # Summary
            if realtime_results:
                avg_execution_time = sum(r['quality_metrics']['execution_time'] for r in realtime_results) / len(realtime_results)
                realtime_strategies = sum(1 for r in realtime_results if "Real" in r['strategy_used'])
                
                print(f"📊 Real-Time Summary:")
                print(f"   Queries Tested: {len(realtime_queries)}")
                print(f"   Successful Researches: {len(realtime_results)}")
                print(f"   Real-Time Strategies Used: {realtime_strategies}")
                print(f"   Average Execution Time: {avg_execution_time:.2f}s")
                
                self.demo_results.append({
                    "demo": "Real-Time Research",
                    "success": len(realtime_results) > 0,
                    "realtime_strategy_rate": realtime_strategies / len(realtime_results) if realtime_results else 0,
                    "average_execution_time": avg_execution_time
                })
            
            print()
            return True
            
        except Exception as e:
            print(f"❌ Real-time research demo failed: {e}")
            logger.error(f"Real-time research demo failed: {e}")
            return False
    
    async def demo_source_credibility(self):
        """Demonstrate source credibility assessment"""
        print("🏆 Demo 6: Source Credibility Assessment")
        print("-" * 40)
        
        try:
            # Test various sources
            test_sources = [
                ("https://nasa.gov/example", "government/science"),
                ("https://bbc.com/news/example", "news"),
                ("https://stackoverflow.com/questions/example", "technical"),
                ("https://harvard.edu/research/example", "academic"),
                ("https://random-blog.com/post", "general")
            ]
            
            credibility_results = []
            
            for url, expected_domain in test_sources:
                print(f"🔗 Assessing: {url}")
                print(f"📂 Expected Domain: {expected_domain}")
                
                try:
                    result = await self.agent.assess_source_credibility(url, expected_domain.split('/')[0])
                    
                    credibility_results.append(result)
                    
                    print(f"   🏅 Overall Score: {result['overall_score']:.2f}")
                    print(f"   🔰 Authority Score: {result['authority_score']:.2f}")
                    print(f"   📅 Recency Score: {result['recency_score']:.2f}")
                    print(f"   💭 Reasoning: {result['reasoning']}")
                    print()
                    
                except Exception as e:
                    print(f"   ❌ Credibility assessment failed: {e}")
                    print()
            
            # Summary
            if credibility_results:
                avg_credibility = sum(r['overall_score'] for r in credibility_results) / len(credibility_results)
                high_credibility_count = sum(1 for r in credibility_results if r['overall_score'] >= 0.7)
                
                print(f"📊 Credibility Assessment Summary:")
                print(f"   Sources Assessed: {len(test_sources)}")
                print(f"   Successfully Assessed: {len(credibility_results)}")
                print(f"   Average Credibility Score: {avg_credibility:.2f}")
                print(f"   High Credibility Sources: {high_credibility_count}")
                
                self.demo_results.append({
                    "demo": "Source Credibility",
                    "success": len(credibility_results) > 0,
                    "average_credibility": avg_credibility,
                    "high_credibility_rate": high_credibility_count / len(credibility_results) if credibility_results else 0
                })
            
            print()
            return True
            
        except Exception as e:
            print(f"❌ Source credibility demo failed: {e}")
            logger.error(f"Source credibility demo failed: {e}")
            return False
    
    async def demo_research_history_and_metrics(self):
        """Demonstrate research history and metrics tracking"""
        print("📈 Demo 7: Research History & Metrics")
        print("-" * 40)
        
        try:
            # Get research history
            history = await self.agent.get_research_history()
            
            print(f"📚 Research History:")
            print(f"   Total Research Sessions: {len(history)}")
            
            if history:
                # Show recent research
                for i, research in enumerate(history[-3:], 1):  # Show last 3
                    print(f"   {i}. Query: {research['query'][:50]}...")
                    print(f"      Strategy: {research['strategy_name']}")
                    print(f"      Quality: {research['quality_score']:.2f}")
                    print(f"      Success: {research['success']}")
                    print()
                
                # Calculate metrics
                successful_research = sum(1 for r in history if r['success'])
                avg_quality = sum(r['quality_score'] for r in history) / len(history)
                avg_execution_time = sum(r['execution_time'] for r in history) / len(history)
                
                print(f"📊 Performance Metrics:")
                print(f"   Success Rate: {successful_research / len(history):.2f}")
                print(f"   Average Quality Score: {avg_quality:.2f}")
                print(f"   Average Execution Time: {avg_execution_time:.2f}s")
            
            # Get comprehensive agent status
            status = await self.agent.get_agent_status()
            
            print(f"🤖 Agent Status:")
            print(f"   State: {status['state']}")
            print(f"   Total Requests: {status.get('total_requests', 0)}")
            print(f"   Successful Requests: {status.get('successful_requests', 0)}")
            print(f"   Failed Requests: {status.get('failed_requests', 0)}")
            print(f"   Recent Research Quality: {status['recent_research_quality']:.2f}")
            
            self.demo_results.append({
                "demo": "History & Metrics",
                "success": True,
                "total_research": len(history),
                "success_rate": successful_research / len(history) if history else 0,
                "average_quality": avg_quality if history else 0
            })
            
            print()
            return True
            
        except Exception as e:
            print(f"❌ History and metrics demo failed: {e}")
            logger.error(f"History and metrics demo failed: {e}")
            return False
    
    async def display_final_summary(self):
        """Display final demo summary"""
        print("🏆 ENHANCED RESEARCH AGENT DEMO SUMMARY")
        print("=" * 60)
        
        if not self.demo_results:
            print("❌ No demo results to display")
            return
        
        successful_demos = sum(1 for result in self.demo_results if result['success'])
        total_demos = len(self.demo_results)
        
        print(f"📊 Overall Results:")
        print(f"   Total Demos: {total_demos}")
        print(f"   Successful Demos: {successful_demos}")
        print(f"   Success Rate: {successful_demos / total_demos:.2f}")
        print()
        
        print(f"📋 Demo Results:")
        for i, result in enumerate(self.demo_results, 1):
            status = "✅" if result['success'] else "❌"
            print(f"   {i}. {status} {result['demo']}")
            
            # Show specific metrics for each demo
            if result['demo'] == "Basic Research" and 'quality_score' in result:
                print(f"      Quality Score: {result['quality_score']:.2f}")
            elif result['demo'] == "Fact Verification" and 'verification_rate' in result:
                print(f"      Verification Rate: {result['verification_rate']:.2f}")
            elif result['demo'] == "Domain Expertise" and 'success_rate' in result:
                print(f"      Domain Success Rate: {result['success_rate']:.2f}")
            elif result['demo'] == "Multi-Language Research" and 'coverage_rate' in result:
                print(f"      Language Coverage: {result['coverage_rate']:.2f}")
            elif result['demo'] == "Source Credibility" and 'average_credibility' in result:
                print(f"      Avg Credibility: {result['average_credibility']:.2f}")
        
        print()
        
        if successful_demos == total_demos:
            print("🎉 ALL DEMOS COMPLETED SUCCESSFULLY!")
            print("✨ Enhanced Research Agent is fully operational with advanced capabilities:")
            print("   • Deep multi-level research")
            print("   • Fact verification and claim validation")
            print("   • Domain-specific expertise")
            print("   • Multi-language research capabilities")
            print("   • Real-time information gathering")
            print("   • Source credibility assessment")
            print("   • Comprehensive quality metrics")
            print("   • Research history tracking")
        else:
            print(f"⚠️  {total_demos - successful_demos} demo(s) encountered issues")
            print("🔧 Check logs for detailed error information")
        
        print()
        print("🚀 Enhanced Research Agent Demo Complete!")
        print("=" * 60)

async def main():
    """Main demo execution function"""
    demo = EnhancedResearchAgentDemo()
    
    try:
        # Initialize demo
        if not await demo.initialize():
            print("❌ Demo initialization failed. Exiting.")
            return
        
        # Run all demos
        demos_to_run = [
            demo.demo_basic_research,
            demo.demo_fact_verification,
            demo.demo_domain_expertise,
            demo.demo_multi_language_research,
            demo.demo_real_time_research,
            demo.demo_source_credibility,
            demo.demo_research_history_and_metrics
        ]
        
        print("🎬 Starting Enhanced Research Agent Capability Demos...")
        print("=" * 60)
        print()
        
        for demo_func in demos_to_run:
            try:
                await demo_func()
                await asyncio.sleep(1)  # Brief pause between demos
            except Exception as e:
                print(f"❌ Demo function {demo_func.__name__} failed: {e}")
                logger.error(f"Demo function {demo_func.__name__} failed: {e}")
        
        # Display final summary
        await demo.display_final_summary()
        
    except Exception as e:
        print(f"❌ Demo execution failed: {e}")
        logger.error(f"Demo execution failed: {e}")

if __name__ == "__main__":
    print("🌟 Enhanced Research Agent Demo Starting...")
    print("=" * 60)
    print()
    
    try:
        asyncio.run(main())
    except KeyboardInterrupt:
        print("\n🛑 Demo interrupted by user")
    except Exception as e:
        print(f"\n❌ Demo failed with error: {e}")
        logger.error(f"Demo failed: {e}")
    
    print("\n👋 Demo session ended.")
