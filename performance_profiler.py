# Performance Optimization Framework - Phase 3A Week 1.2
"""
Week 1.2 Implementation: Performance Optimization
===============================================

This module provides comprehensive performance profiling and optimization
for the integrated JARVIS-MK42 system including:
- Memory usage profiling across all AI components
- CPU utilization analysis and balancing
- Database query optimization
- Concurrent processing improvements
"""

import asyncio
import time
import psutil
import tracemalloc
import gc
from typing import Dict, List, Any, Optional, Tuple
from dataclasses import dataclass, field
import sys
import os
from datetime import datetime
import json

# Add project root to path
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

@dataclass
class PerformanceMetrics:
    """Performance metrics for system components"""
    component_name: str
    memory_usage_mb: float = 0.0
    cpu_usage_percent: float = 0.0
    execution_time_ms: float = 0.0
    memory_peak_mb: float = 0.0
    gc_collections: int = 0
    database_queries: int = 0
    query_time_ms: float = 0.0
    additional_metrics: Dict[str, Any] = field(default_factory=dict)

@dataclass
class OptimizationSuggestion:
    """Optimization suggestion based on performance analysis"""
    category: str
    priority: str  # "HIGH", "MEDIUM", "LOW"
    component: str
    issue: str
    suggestion: str
    expected_improvement: str

class PerformanceProfiler:
    """Comprehensive performance profiling system"""
    
    def __init__(self):
        self.metrics: Dict[str, PerformanceMetrics] = {}
        self.optimization_suggestions: List[OptimizationSuggestion] = []
        self.baseline_metrics = {}
        
    async def run_comprehensive_profiling(self) -> Dict[str, Any]:
        """Run complete performance profiling suite"""
        print("🔍 Phase 3A Week 1.2: Performance Optimization")
        print("=" * 60)
        print("🚀 Starting comprehensive performance profiling...")
        
        # Initialize profiling
        tracemalloc.start()
        process = psutil.Process()
        start_time = time.time()
        
        # Profile each component
        await self._profile_ai_components()
        await self._profile_system_resources()
        await self._profile_database_operations()
        await self._profile_concurrent_operations()
        
        # Generate optimization suggestions
        self._generate_optimization_suggestions()
        
        # Create comprehensive report
        total_time = time.time() - start_time
        report = self._generate_performance_report(total_time)
        
        # Clean up
        tracemalloc.stop()
        
        return report
    
    async def _profile_ai_components(self):
        """Profile memory and CPU usage of AI components"""
        print("\n🧠 Profiling AI Components...")
        
        try:
            # Import AI components
            from ai import CognitiveArchitecture, MultiModalEngine, AdaptiveLearningSystem, KnowledgeManager
            
            components = {
                'cognitive_architecture': CognitiveArchitecture(),
                'multimodal_engine': MultiModalEngine(),
                'adaptive_learning': AdaptiveLearningSystem(), 
                'knowledge_manager': KnowledgeManager()
            }
            
            for name, component in components.items():
                await self._profile_component(name, component)
                
        except ImportError as e:
            print(f"   ⚠️ AI components not available for profiling: {e}")
    
    async def _profile_component(self, name: str, component: Any):
        """Profile individual component performance"""
        print(f"   📊 Profiling {name}...")
        
        # Start memory tracking
        gc.collect()  # Clean up before measurement
        process = psutil.Process()
        memory_before = process.memory_info().rss / 1024 / 1024  # MB
        cpu_before = process.cpu_percent()
        
        # Start detailed memory profiling
        tracemalloc_snapshot_before = tracemalloc.take_snapshot()
        
        start_time = time.time()
        
        try:
            # Exercise the component with typical operations
            if hasattr(component, 'process_with_cognitive_architecture'):
                # Cognitive Architecture
                await component.process_with_cognitive_architecture(
                    "Analyze the performance characteristics of an AI system"
                )
                
            elif hasattr(component, 'analyze_image'):
                # Multimodal Engine
                from ai.multimodal_engine import ModalityInput, ModalityType
                test_input = ModalityInput(
                    modality=ModalityType.VISION,
                    data="performance_test_data",
                    metadata={"format": "test"},
                    source="profiler"
                )
                await component.analyze_image(test_input.data)
                
            elif hasattr(component, 'process_experiences'):
                # Adaptive Learning
                from ai.adaptive_learning import Experience, ExperienceType
                test_exp = Experience(
                    experience_id="perf_test",
                    experience_type=ExperienceType.SUCCESS,
                    context={"task": "performance_test"},
                    action={"test": "profiling"},
                    outcome={"success": True},
                    reward=0.8,
                    confidence=0.9
                )
                await component.process_experiences([test_exp])
                
            elif hasattr(component, 'query_knowledge'):
                # Knowledge Manager
                from ai.knowledge_manager import MemoryType
                await component.query_knowledge(
                    query_text="performance optimization",
                    context={"domain": "system_performance"},
                    memory_types=[MemoryType.SEMANTIC],
                    max_results=5
                )
                
        except Exception as e:
            print(f"     ⚠️ Error profiling {name}: {e}")
        
        # Calculate metrics
        execution_time = (time.time() - start_time) * 1000  # ms
        memory_after = process.memory_info().rss / 1024 / 1024  # MB
        cpu_after = process.cpu_percent()
        
        # Memory peak analysis
        tracemalloc_snapshot_after = tracemalloc.take_snapshot()
        top_stats = tracemalloc_snapshot_after.compare_to(tracemalloc_snapshot_before, 'lineno')
        memory_peak = sum(stat.size_diff for stat in top_stats[:10]) / 1024 / 1024  # MB
        
        # Store metrics
        self.metrics[name] = PerformanceMetrics(
            component_name=name,
            memory_usage_mb=memory_after - memory_before,
            cpu_usage_percent=cpu_after - cpu_before,
            execution_time_ms=execution_time,
            memory_peak_mb=memory_peak,
            gc_collections=gc.get_count()[0]
        )
        
        print(f"     ✓ Memory: {self.metrics[name].memory_usage_mb:.1f}MB")
        print(f"     ✓ CPU: {self.metrics[name].cpu_usage_percent:.1f}%") 
        print(f"     ✓ Time: {self.metrics[name].execution_time_ms:.1f}ms")
    
    async def _profile_system_resources(self):
        """Profile overall system resource usage"""
        print("\n💻 Profiling System Resources...")
        
        process = psutil.Process()
        
        # System memory
        memory_info = psutil.virtual_memory()
        system_metrics = PerformanceMetrics(
            component_name="system_overall",
            memory_usage_mb=process.memory_info().rss / 1024 / 1024,
            cpu_usage_percent=process.cpu_percent(interval=1),
            additional_metrics={
                "system_memory_total_gb": memory_info.total / 1024 / 1024 / 1024,
                "system_memory_available_gb": memory_info.available / 1024 / 1024 / 1024,
                "system_memory_percent": memory_info.percent,
                "system_cpu_count": psutil.cpu_count(),
                "system_load_avg": os.getloadavg() if hasattr(os, 'getloadavg') else [0, 0, 0]
            }
        )
        
        self.metrics["system_overall"] = system_metrics
        
        print(f"   ✓ Process Memory: {system_metrics.memory_usage_mb:.1f}MB")
        print(f"   ✓ Process CPU: {system_metrics.cpu_usage_percent:.1f}%")
        print(f"   ✓ System Memory: {system_metrics.additional_metrics['system_memory_percent']:.1f}% used")
    
    async def _profile_database_operations(self):
        """Profile database query performance"""
        print("\n🗄️ Profiling Database Operations...")
        
        try:
            # Test database operations
            database_start = time.time()
            query_count = 0
            
            # Test knowledge manager database operations
            if 'knowledge_manager' in self.metrics:
                knowledge_manager = self.metrics['knowledge_manager']
                
                # Simulate multiple database queries
                from ai.knowledge_manager import KnowledgeManager
                km = KnowledgeManager()
                
                # Test episodic memory queries
                test_queries = [
                    "machine learning performance",
                    "database optimization techniques", 
                    "system profiling methods",
                    "performance metrics analysis",
                    "optimization strategies"
                ]
                
                for query in test_queries:
                    try:
                        await km.query_knowledge(query_text=query, max_results=3)
                        query_count += 1
                    except:
                        pass  # Skip failed queries for profiling
            
            database_time = (time.time() - database_start) * 1000  # ms
            
            # Store database metrics
            if query_count > 0:
                self.metrics["database_operations"] = PerformanceMetrics(
                    component_name="database_operations",
                    database_queries=query_count,
                    query_time_ms=database_time,
                    additional_metrics={
                        "avg_query_time_ms": database_time / query_count,
                        "queries_per_second": query_count / (database_time / 1000) if database_time > 0 else 0
                    }
                )
                
                print(f"   ✓ Queries executed: {query_count}")
                print(f"   ✓ Total time: {database_time:.1f}ms")
                print(f"   ✓ Avg per query: {database_time/query_count:.1f}ms")
            
        except Exception as e:
            print(f"   ⚠️ Database profiling error: {e}")
    
    async def _profile_concurrent_operations(self):
        """Profile concurrent processing performance"""
        print("\n⚡ Profiling Concurrent Operations...")
        
        try:
            # Test concurrent AI component operations
            concurrent_start = time.time()
            
            tasks = []
            
            # Create concurrent tasks for different components
            if 'cognitive_architecture' in self.metrics:
                from ai import CognitiveArchitecture
                cognitive = CognitiveArchitecture()
                tasks.append(cognitive.process_with_cognitive_architecture("Concurrent task 1"))
            
            if 'multimodal_engine' in self.metrics:
                from ai import MultiModalEngine
                from ai.multimodal_engine import ModalityInput, ModalityType
                multimodal = MultiModalEngine()
                test_input = ModalityInput(
                    modality=ModalityType.VISION,
                    data="concurrent_test",
                    metadata={"format": "test"},
                    source="profiler"
                )
                tasks.append(multimodal.analyze_image(test_input.data))
            
            # Execute tasks concurrently
            if tasks:
                results = await asyncio.gather(*tasks, return_exceptions=True)
                
                concurrent_time = (time.time() - concurrent_start) * 1000  # ms
                
                # Store concurrent metrics
                self.metrics["concurrent_operations"] = PerformanceMetrics(
                    component_name="concurrent_operations",
                    execution_time_ms=concurrent_time,
                    additional_metrics={
                        "concurrent_tasks": len(tasks),
                        "successful_tasks": len([r for r in results if not isinstance(r, Exception)]),
                        "failed_tasks": len([r for r in results if isinstance(r, Exception)]),
                        "avg_task_time_ms": concurrent_time / len(tasks) if tasks else 0
                    }
                )
                
                print(f"   ✓ Concurrent tasks: {len(tasks)}")
                print(f"   ✓ Total time: {concurrent_time:.1f}ms")
                print(f"   ✓ Successful: {self.metrics['concurrent_operations'].additional_metrics['successful_tasks']}")
            
        except Exception as e:
            print(f"   ⚠️ Concurrent profiling error: {e}")
    
    def _generate_optimization_suggestions(self):
        """Generate optimization suggestions based on profiling results"""
        print("\n💡 Generating Optimization Suggestions...")
        
        for name, metrics in self.metrics.items():
            
            # Memory optimization suggestions
            if metrics.memory_usage_mb > 100:  # >100MB
                self.optimization_suggestions.append(OptimizationSuggestion(
                    category="Memory",
                    priority="HIGH",
                    component=name,
                    issue=f"High memory usage: {metrics.memory_usage_mb:.1f}MB",
                    suggestion="Implement memory pooling, optimize data structures, add garbage collection",
                    expected_improvement="30-50% memory reduction"
                ))
            elif metrics.memory_usage_mb > 50:  # >50MB
                self.optimization_suggestions.append(OptimizationSuggestion(
                    category="Memory", 
                    priority="MEDIUM",
                    component=name,
                    issue=f"Moderate memory usage: {metrics.memory_usage_mb:.1f}MB",
                    suggestion="Review data caching strategies, optimize object lifecycle",
                    expected_improvement="15-30% memory reduction"
                ))
            
            # CPU optimization suggestions
            if metrics.cpu_usage_percent > 50:  # >50% CPU
                self.optimization_suggestions.append(OptimizationSuggestion(
                    category="CPU",
                    priority="HIGH", 
                    component=name,
                    issue=f"High CPU usage: {metrics.cpu_usage_percent:.1f}%",
                    suggestion="Implement async processing, optimize algorithms, add CPU affinity",
                    expected_improvement="20-40% CPU reduction"
                ))
            
            # Execution time optimization suggestions
            if metrics.execution_time_ms > 1000:  # >1 second
                self.optimization_suggestions.append(OptimizationSuggestion(
                    category="Performance",
                    priority="HIGH",
                    component=name,
                    issue=f"Slow execution time: {metrics.execution_time_ms:.1f}ms",
                    suggestion="Profile bottlenecks, implement caching, optimize hot code paths",
                    expected_improvement="40-60% speed improvement"
                ))
            elif metrics.execution_time_ms > 500:  # >500ms
                self.optimization_suggestions.append(OptimizationSuggestion(
                    category="Performance",
                    priority="MEDIUM",
                    component=name,
                    issue=f"Moderate execution time: {metrics.execution_time_ms:.1f}ms",
                    suggestion="Add result caching, optimize frequent operations",
                    expected_improvement="20-40% speed improvement"
                ))
        
        # Database-specific suggestions
        if "database_operations" in self.metrics:
            db_metrics = self.metrics["database_operations"]
            avg_query_time = db_metrics.additional_metrics.get("avg_query_time_ms", 0)
            
            if avg_query_time > 100:  # >100ms per query
                self.optimization_suggestions.append(OptimizationSuggestion(
                    category="Database",
                    priority="HIGH",
                    component="database_operations",
                    issue=f"Slow database queries: {avg_query_time:.1f}ms average",
                    suggestion="Add database indexes, optimize queries, implement connection pooling",
                    expected_improvement="50-70% query speed improvement"
                ))
        
        print(f"   ✓ Generated {len(self.optimization_suggestions)} optimization suggestions")
    
    def _generate_performance_report(self, total_time: float) -> Dict[str, Any]:
        """Generate comprehensive performance report"""
        report = {
            "summary": {
                "total_profiling_time": total_time,
                "components_profiled": len(self.metrics),
                "optimization_suggestions": len(self.optimization_suggestions),
                "high_priority_issues": len([s for s in self.optimization_suggestions if s.priority == "HIGH"]),
                "timestamp": datetime.now().isoformat()
            },
            "component_metrics": {},
            "optimization_suggestions": [],
            "performance_analysis": {
                "memory_hotspots": [],
                "cpu_hotspots": [],
                "performance_bottlenecks": []
            },
            "recommendations": {
                "immediate_actions": [],
                "optimization_priorities": [],
                "performance_targets": {}
            }
        }
        
        # Component metrics
        for name, metrics in self.metrics.items():
            report["component_metrics"][name] = {
                "memory_usage_mb": metrics.memory_usage_mb,
                "cpu_usage_percent": metrics.cpu_usage_percent, 
                "execution_time_ms": metrics.execution_time_ms,
                "memory_peak_mb": metrics.memory_peak_mb,
                "additional_metrics": metrics.additional_metrics
            }
        
        # Optimization suggestions
        for suggestion in self.optimization_suggestions:
            report["optimization_suggestions"].append({
                "category": suggestion.category,
                "priority": suggestion.priority,
                "component": suggestion.component,
                "issue": suggestion.issue,
                "suggestion": suggestion.suggestion,
                "expected_improvement": suggestion.expected_improvement
            })
        
        # Performance analysis
        # Memory hotspots
        memory_sorted = sorted(self.metrics.items(), key=lambda x: x[1].memory_usage_mb, reverse=True)
        report["performance_analysis"]["memory_hotspots"] = [
            {"component": name, "memory_mb": metrics.memory_usage_mb} 
            for name, metrics in memory_sorted[:3]
        ]
        
        # CPU hotspots  
        cpu_sorted = sorted(self.metrics.items(), key=lambda x: x[1].cpu_usage_percent, reverse=True)
        report["performance_analysis"]["cpu_hotspots"] = [
            {"component": name, "cpu_percent": metrics.cpu_usage_percent}
            for name, metrics in cpu_sorted[:3]
        ]
        
        # Performance bottlenecks
        time_sorted = sorted(self.metrics.items(), key=lambda x: x[1].execution_time_ms, reverse=True)
        report["performance_analysis"]["performance_bottlenecks"] = [
            {"component": name, "execution_time_ms": metrics.execution_time_ms}
            for name, metrics in time_sorted[:3]
        ]
        
        # Recommendations
        high_priority = [s for s in self.optimization_suggestions if s.priority == "HIGH"]
        report["recommendations"]["immediate_actions"] = [
            f"{s.component}: {s.suggestion}" for s in high_priority[:5]
        ]
        
        report["recommendations"]["optimization_priorities"] = [
            "Memory optimization for components using >50MB",
            "CPU optimization for components using >30% CPU", 
            "Database query optimization for >50ms queries",
            "Concurrent processing optimization",
            "Caching implementation for frequent operations"
        ]
        
        report["recommendations"]["performance_targets"] = {
            "memory_per_component_mb": 25,
            "cpu_per_component_percent": 20,
            "execution_time_ms": 200,
            "database_query_ms": 50,
            "concurrent_efficiency_percent": 80
        }
        
        return report
    
    def print_performance_report(self, report: Dict[str, Any]):
        """Print formatted performance report"""
        print(f"\n📊 PHASE 3A PERFORMANCE OPTIMIZATION REPORT")
        print("=" * 60)
        
        summary = report["summary"]
        print(f"🔍 Profiling Summary:")
        print(f"   Components Profiled: {summary['components_profiled']}")
        print(f"   Total Profiling Time: {summary['total_profiling_time']:.3f}s")
        print(f"   Optimization Suggestions: {summary['optimization_suggestions']}")
        print(f"   High Priority Issues: {summary['high_priority_issues']}")
        
        print(f"\n💾 Component Performance Metrics:")
        for name, metrics in report["component_metrics"].items():
            print(f"   📦 {name.replace('_', ' ').title()}:")
            print(f"      Memory: {metrics['memory_usage_mb']:.1f}MB")
            print(f"      CPU: {metrics['cpu_usage_percent']:.1f}%")
            print(f"      Time: {metrics['execution_time_ms']:.1f}ms")
        
        print(f"\n🔥 Performance Hotspots:")
        if report["performance_analysis"]["memory_hotspots"]:
            print(f"   Memory: {report['performance_analysis']['memory_hotspots'][0]['component']} ({report['performance_analysis']['memory_hotspots'][0]['memory_mb']:.1f}MB)")
        if report["performance_analysis"]["cpu_hotspots"]:
            print(f"   CPU: {report['performance_analysis']['cpu_hotspots'][0]['component']} ({report['performance_analysis']['cpu_hotspots'][0]['cpu_percent']:.1f}%)")
        if report["performance_analysis"]["performance_bottlenecks"]:
            print(f"   Speed: {report['performance_analysis']['performance_bottlenecks'][0]['component']} ({report['performance_analysis']['performance_bottlenecks'][0]['execution_time_ms']:.1f}ms)")
        
        print(f"\n🚨 High Priority Optimization Suggestions:")
        high_priority = [s for s in report["optimization_suggestions"] if s["priority"] == "HIGH"]
        for i, suggestion in enumerate(high_priority[:5], 1):
            print(f"   {i}. {suggestion['component']}: {suggestion['issue']}")
            print(f"      💡 {suggestion['suggestion']}")
            print(f"      📈 Expected: {suggestion['expected_improvement']}")
        
        print(f"\n🎯 Performance Targets:")
        targets = report["recommendations"]["performance_targets"]
        print(f"   Memory per component: <{targets['memory_per_component_mb']}MB")
        print(f"   CPU per component: <{targets['cpu_per_component_percent']}%")
        print(f"   Execution time: <{targets['execution_time_ms']}ms")
        print(f"   Database queries: <{targets['database_query_ms']}ms")
        
        print(f"\n📋 Next Steps:")
        for i, action in enumerate(report["recommendations"]["immediate_actions"][:3], 1):
            print(f"   {i}. {action}")

async def main():
    """Main function to run performance profiling"""
    print("🚀 Phase 3A Week 1.2: Performance Optimization")
    print("Starting comprehensive performance profiling...")
    print("=" * 60)
    
    # Create and run performance profiler
    profiler = PerformanceProfiler()
    
    # Run comprehensive profiling
    report = await profiler.run_comprehensive_profiling()
    
    # Print detailed report
    profiler.print_performance_report(report)
    
    # Save report to file
    with open("performance_profiling_report.json", "w") as f:
        json.dump(report, f, indent=2)
    
    print(f"\n💾 Performance report saved to: performance_profiling_report.json")
    
    print(f"\n🎯 Phase 3A Week 1.2 Status:")
    high_priority_count = len([s for s in report["optimization_suggestions"] if s["priority"] == "HIGH"])
    if high_priority_count == 0:
        print("✅ No high-priority performance issues - proceeding to Week 1.3")
    elif high_priority_count <= 3:
        print("⚠️ Minor performance issues identified - optimization recommended")
    else:
        print("🔴 Significant performance issues - optimization required before proceeding")

if __name__ == "__main__":
    asyncio.run(main())
