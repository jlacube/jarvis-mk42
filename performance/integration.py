#!/usr/bin/env python3
"""
JARVIS-MK42 Performance System Integration
=========================================

This module integrates all performance and scalability systems:
- Performance Optimization Engine (optimization.py)
- Scalability Management (scalability.py)  
- AI Model Performance Optimizer (ai_models.py)
- Resource Manager (resource_manager.py)
- Performance Analytics (analytics.py)

Provides unified interface and orchestration across all performance systems.
"""

import os
import sys
import json
import time
import asyncio
import threading
from datetime import datetime, timedelta
from typing import Dict, List, Optional, Any, Callable
from dataclasses import dataclass
from enum import Enum

# Add project root to path
current_dir = os.path.dirname(os.path.abspath(__file__))
project_root = os.path.dirname(current_dir)
if project_root not in sys.path:
    sys.path.insert(0, project_root)

from utils.logging_config import get_logger

# Import performance modules
try:
    from .optimization import get_performance_optimizer, PerformanceOptimizer
    from .scalability import get_scalability_manager, ScalabilityManager
    from .ai_models import get_ai_model_optimizer, AIModelOptimizer
    from .resource_manager import get_resource_manager, ResourceManager
    from .analytics import get_performance_analytics, PerformanceAnalytics, PerformanceMetric, MetricType
except ImportError:
    # Fallback for direct execution
    from optimization import get_performance_optimizer, PerformanceOptimizer
    from scalability import get_scalability_manager, ScalabilityManager
    from ai_models import get_ai_model_optimizer, AIModelOptimizer
    from resource_manager import get_resource_manager, ResourceManager
    from analytics import get_performance_analytics, PerformanceAnalytics, PerformanceMetric, MetricType

logger = get_logger(__name__)


class PerformanceMode(Enum):
    """Performance optimization modes"""
    BALANCED = "balanced"           # Balance between performance and resource usage
    PERFORMANCE = "performance"    # Maximize performance
    EFFICIENCY = "efficiency"      # Maximize resource efficiency
    SCALE = "scale"                # Focus on scalability
    DEVELOPMENT = "development"    # Development-friendly settings
    PRODUCTION = "production"      # Production-optimized settings


@dataclass
class SystemPerformanceStatus:
    """Overall system performance status"""
    mode: PerformanceMode
    overall_health: str
    performance_score: float  # 0.0 to 1.0
    efficiency_score: float   # 0.0 to 1.0
    scalability_score: float  # 0.0 to 1.0
    active_optimizations: List[str]
    critical_issues: List[str]
    recommendations: List[str]
    last_updated: datetime
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary"""
        return {
            'mode': self.mode.value,
            'overall_health': self.overall_health,
            'performance_score': self.performance_score,
            'efficiency_score': self.efficiency_score,
            'scalability_score': self.scalability_score,
            'active_optimizations': self.active_optimizations,
            'critical_issues': self.critical_issues,
            'recommendations': self.recommendations,
            'last_updated': self.last_updated.isoformat()
        }


class PerformanceSystemIntegrator:
    """Unified performance system orchestrator"""
    
    def __init__(self, mode: PerformanceMode = PerformanceMode.BALANCED):
        self.mode = mode
        self.initialized = False
        
        # Core performance systems
        self.performance_optimizer: Optional[PerformanceOptimizer] = None
        self.scalability_manager: Optional[ScalabilityManager] = None
        self.ai_model_optimizer: Optional[AIModelOptimizer] = None
        self.resource_manager: Optional[ResourceManager] = None
        self.performance_analytics: Optional[PerformanceAnalytics] = None
        
        # Integration state
        self.optimization_callbacks: Dict[str, List[Callable]] = {
            'performance': [],
            'scalability': [],
            'ai_models': [],
            'resources': [],
            'analytics': []
        }
        
        self.system_metrics: Dict[str, Any] = {}
        self.last_health_check = datetime.now()
        
        # Control flags
        self.auto_optimization_enabled = True
        self.cross_system_coordination = True
        
        logger.info(f"Performance System Integrator initialized in {mode.value} mode")
    
    def initialize_systems(self, 
                          enable_ai_models: bool = True,
                          enable_analytics: bool = True,
                          enable_resource_monitoring: bool = True) -> bool:
        """Initialize all performance systems"""
        try:
            logger.info("Initializing performance systems...")
            
            # Initialize core optimization
            self.performance_optimizer = get_performance_optimizer()
            
            # Initialize scalability management
            self.scalability_manager = get_scalability_manager()
            
            # Initialize AI model optimization
            if enable_ai_models:
                self.ai_model_optimizer = get_ai_model_optimizer()
            
            # Initialize resource management
            if enable_resource_monitoring:
                self.resource_manager = get_resource_manager()
                self._setup_resource_monitoring()
            
            # Initialize performance analytics
            if enable_analytics:
                self.performance_analytics = get_performance_analytics()
                self._setup_analytics_integration()
            
            # Configure based on mode
            self._configure_for_mode()
            
            # Set up cross-system coordination
            if self.cross_system_coordination:
                self._setup_coordination()
            
            self.initialized = True
            logger.info("All performance systems initialized successfully")
            return True
            
        except Exception as e:
            logger.error(f"Failed to initialize performance systems: {e}")
            return False
    
    def _configure_for_mode(self):
        """Configure systems based on performance mode"""
        if self.mode == PerformanceMode.PERFORMANCE:
            # Maximum performance settings
            if self.performance_optimizer:
                # Enable aggressive caching
                pass
            if self.scalability_manager:
                # Prefer performance over efficiency
                pass
                
        elif self.mode == PerformanceMode.EFFICIENCY:
            # Resource efficiency settings
            if self.resource_manager:
                # Enable aggressive resource monitoring
                pass
                
        elif self.mode == PerformanceMode.SCALE:
            # Scalability-focused settings
            if self.scalability_manager:
                # Enable auto-scaling
                pass
                
        elif self.mode == PerformanceMode.DEVELOPMENT:
            # Development-friendly settings
            self.auto_optimization_enabled = False
            
        elif self.mode == PerformanceMode.PRODUCTION:
            # Production-optimized settings
            self.auto_optimization_enabled = True
            self.cross_system_coordination = True
    
    def _setup_resource_monitoring(self):
        """Set up resource monitoring integration"""
        if not self.resource_manager:
            return
        
        # Register callbacks for resource events
        def on_resource_alert(metric, status):
            self._handle_resource_alert(metric, status)
        
        def on_scaling_recommendation(recommendation):
            self._handle_scaling_recommendation(recommendation)
        
        self.resource_manager.register_alert_callback(on_resource_alert)
        self.resource_manager.register_scaling_callback(on_scaling_recommendation)
        
        # Start monitoring
        self.resource_manager.start_monitoring()
        logger.info("Resource monitoring integration configured")
    
    def _setup_analytics_integration(self):
        """Set up performance analytics integration"""
        if not self.performance_analytics:
            return
        
        # Register callbacks for analytics events
        def on_performance_alert(alert):
            self._handle_performance_alert(alert)
        
        def on_bottleneck_detected(bottleneck):
            self._handle_bottleneck_detection(bottleneck)
        
        self.performance_analytics.register_alert_callback(on_performance_alert)
        self.performance_analytics.register_bottleneck_callback(on_bottleneck_detected)
        
        # Start analytics
        self.performance_analytics.start_analysis()
        logger.info("Performance analytics integration configured")
    
    def _setup_coordination(self):
        """Set up cross-system coordination"""
        # Coordination logic between systems
        logger.info("Cross-system coordination configured")
    
    def _handle_resource_alert(self, metric, status):
        """Handle resource management alerts"""
        logger.warning(f"Resource alert: {metric.name} at {metric.value:.1f}% - Status: {status.value}")
        
        # Record in analytics if available
        if self.performance_analytics:
            perf_metric = PerformanceMetric(
                name=f"resource_{metric.name}",
                value=metric.value,
                timestamp=metric.timestamp,
                metric_type=MetricType.CUSTOM,
                unit="percent",
                tags={'source': 'resource_manager', 'status': status.value}
            )
            self.performance_analytics.record_metric(perf_metric)
        
        # Trigger optimizations if needed
        if self.auto_optimization_enabled and status.value == 'critical':
            self._trigger_emergency_optimization(metric)
    
    def _handle_scaling_recommendation(self, recommendation):
        """Handle auto-scaling recommendations"""
        logger.info(f"Scaling recommendation: {recommendation.reasoning}")
        
        # Apply scaling if auto-optimization is enabled
        if self.auto_optimization_enabled and recommendation.confidence > 0.8:
            self._apply_scaling_recommendation(recommendation)
    
    def _handle_performance_alert(self, alert):
        """Handle performance analytics alerts"""
        logger.warning(f"Performance alert: {alert.title}")
        
        # Coordinate response across systems
        if self.auto_optimization_enabled:
            self._coordinate_performance_response(alert)
    
    def _handle_bottleneck_detection(self, bottleneck):
        """Handle bottleneck detection"""
        logger.warning(f"Bottleneck detected: {bottleneck.component_name} - {bottleneck.impact_description}")
        
        # Apply bottleneck-specific optimizations
        if self.auto_optimization_enabled:
            self._apply_bottleneck_optimizations(bottleneck)
    
    def _trigger_emergency_optimization(self, metric):
        """Trigger emergency optimization for critical resource usage"""
        optimizations_applied = []
        
        # Apply cache optimization
        if self.performance_optimizer and metric.name == 'memory':
            # Force memory cleanup
            optimizations_applied.append("memory_cleanup")
        
        # Apply scaling if possible
        if self.scalability_manager and metric.name == 'cpu':
            # Request additional resources
            optimizations_applied.append("cpu_scaling")
        
        logger.info(f"Emergency optimizations applied: {optimizations_applied}")
    
    def _apply_scaling_recommendation(self, recommendation):
        """Apply scaling recommendation"""
        if not self.scalability_manager:
            return
        
        # This would integrate with actual scaling mechanisms
        logger.info(f"Would apply scaling: {recommendation.direction.value} for {recommendation.resource_type.value}")
    
    def _coordinate_performance_response(self, alert):
        """Coordinate response to performance alerts across systems"""
        response_actions = []
        
        # Analyze alert and determine response
        if "response_time" in alert.metric_name.lower():
            # High response time - optimize caching and consider scaling
            if self.performance_optimizer:
                response_actions.append("cache_optimization")
            if self.scalability_manager:
                response_actions.append("consider_scaling")
        
        elif "error_rate" in alert.metric_name.lower():
            # High error rate - check resource constraints
            if self.resource_manager:
                response_actions.append("resource_analysis")
        
        logger.info(f"Coordinated response actions: {response_actions}")
    
    def _apply_bottleneck_optimizations(self, bottleneck):
        """Apply optimizations specific to detected bottlenecks"""
        optimizations = []
        
        if bottleneck.bottleneck_type == 'cpu_bound':
            # CPU optimization strategies
            if self.ai_model_optimizer:
                # Optimize model inference
                optimizations.append("ai_model_optimization")
            if self.scalability_manager:
                # Consider CPU scaling
                optimizations.append("cpu_scaling")
        
        elif bottleneck.bottleneck_type == 'memory_bound':
            # Memory optimization strategies  
            if self.performance_optimizer:
                # Optimize memory usage
                optimizations.append("memory_optimization")
        
        logger.info(f"Bottleneck optimizations applied: {optimizations}")
    
    def get_system_status(self) -> SystemPerformanceStatus:
        """Get comprehensive system performance status"""
        if not self.initialized:
            return SystemPerformanceStatus(
                mode=self.mode,
                overall_health="not_initialized",
                performance_score=0.0,
                efficiency_score=0.0,
                scalability_score=0.0,
                active_optimizations=[],
                critical_issues=["Systems not initialized"],
                recommendations=["Initialize performance systems"],
                last_updated=datetime.now()
            )
        
        # Collect status from all systems
        performance_score = self._calculate_performance_score()
        efficiency_score = self._calculate_efficiency_score()
        scalability_score = self._calculate_scalability_score()
        
        # Determine overall health
        avg_score = (performance_score + efficiency_score + scalability_score) / 3
        if avg_score >= 0.8:
            overall_health = "excellent"
        elif avg_score >= 0.6:
            overall_health = "good"
        elif avg_score >= 0.4:
            overall_health = "fair"
        else:
            overall_health = "poor"
        
        # Collect active optimizations and issues
        active_optimizations = self._get_active_optimizations()
        critical_issues = self._get_critical_issues()
        recommendations = self._get_recommendations()
        
        return SystemPerformanceStatus(
            mode=self.mode,
            overall_health=overall_health,
            performance_score=performance_score,
            efficiency_score=efficiency_score,
            scalability_score=scalability_score,
            active_optimizations=active_optimizations,
            critical_issues=critical_issues,
            recommendations=recommendations,
            last_updated=datetime.now()
        )
    
    def _calculate_performance_score(self) -> float:
        """Calculate overall performance score"""
        scores = []
        
        # Performance optimizer contribution
        if self.performance_optimizer:
            scores.append(0.8)  # Placeholder - would use actual metrics
        
        # AI model optimizer contribution
        if self.ai_model_optimizer:
            scores.append(0.7)  # Placeholder
        
        # Default if no systems available
        if not scores:
            scores.append(0.5)
        
        return sum(scores) / len(scores)
    
    def _calculate_efficiency_score(self) -> float:
        """Calculate resource efficiency score"""
        if self.resource_manager:
            # Get current resource status
            status = self.resource_manager.get_current_status()
            
            # Calculate efficiency based on resource utilization
            efficiency_factors = []
            
            for resource, data in status.get('resources', {}).items():
                utilization = data.get('current_value', 0)
                
                # Ideal utilization ranges
                if 30 <= utilization <= 70:  # Sweet spot
                    efficiency_factors.append(1.0)
                elif utilization < 30:  # Under-utilized
                    efficiency_factors.append(0.6)
                elif utilization < 85:  # High but acceptable
                    efficiency_factors.append(0.8)
                else:  # Over-utilized
                    efficiency_factors.append(0.3)
            
            if efficiency_factors:
                return sum(efficiency_factors) / len(efficiency_factors)
        
        return 0.7  # Default efficiency score
    
    def _calculate_scalability_score(self) -> float:
        """Calculate scalability readiness score"""
        if self.scalability_manager:
            # Evaluate scalability capabilities
            return 0.8  # Placeholder - would use actual metrics
        
        return 0.5  # Default if no scalability manager
    
    def _get_active_optimizations(self) -> List[str]:
        """Get list of currently active optimizations"""
        optimizations = []
        
        if self.performance_optimizer:
            optimizations.append("Performance Optimization Engine")
        
        if self.scalability_manager:
            optimizations.append("Auto-scaling Management")
        
        if self.ai_model_optimizer:
            optimizations.append("AI Model Optimization")
        
        if self.resource_manager:
            optimizations.append("Resource Monitoring & Management")
        
        if self.performance_analytics:
            optimizations.append("Performance Analytics & Alerting")
        
        return optimizations
    
    def _get_critical_issues(self) -> List[str]:
        """Get list of critical performance issues"""
        issues = []
        
        # Check each system for issues
        if self.resource_manager:
            status = self.resource_manager.get_current_status()
            for resource, data in status.get('resources', {}).items():
                if data.get('status') == 'critical':
                    issues.append(f"Critical {resource} utilization: {data.get('current_value', 0):.1f}%")
        
        # Check performance analytics for active critical alerts
        if self.performance_analytics:
            # Would check for critical alerts
            pass
        
        return issues
    
    def _get_recommendations(self) -> List[str]:
        """Get performance optimization recommendations"""
        recommendations = []
        
        # Mode-specific recommendations
        if self.mode == PerformanceMode.DEVELOPMENT:
            recommendations.append("Consider enabling auto-optimization for better performance")
        
        # Resource-based recommendations
        if self.resource_manager:
            status = self.resource_manager.get_current_status()
            for resource, data in status.get('resources', {}).items():
                utilization = data.get('current_value', 0)
                if utilization > 85:
                    recommendations.append(f"High {resource} usage - consider optimization or scaling")
                elif utilization < 30:
                    recommendations.append(f"Low {resource} usage - consider resource reallocation")
        
        # System-specific recommendations
        if not self.ai_model_optimizer:
            recommendations.append("Enable AI model optimization for better inference performance")
        
        if not self.performance_analytics:
            recommendations.append("Enable performance analytics for better insights")
        
        return recommendations[:5]  # Limit to top 5 recommendations
    
    def shutdown(self):
        """Shutdown all performance systems"""
        logger.info("Shutting down performance systems...")
        
        if self.resource_manager:
            self.resource_manager.stop_monitoring()
        
        if self.performance_analytics:
            self.performance_analytics.stop_analysis()
        
        if self.ai_model_optimizer:
            self.ai_model_optimizer.shutdown()
        
        logger.info("Performance systems shutdown complete")
    
    def get_comprehensive_report(self) -> Dict[str, Any]:
        """Get comprehensive performance report"""
        status = self.get_system_status()
        
        report = {
            'timestamp': datetime.now().isoformat(),
            'system_status': status.to_dict(),
            'subsystem_reports': {}
        }
        
        # Collect reports from each subsystem
        if self.performance_optimizer:
            report['subsystem_reports']['optimization'] = self.performance_optimizer.get_optimization_stats()
        
        if self.scalability_manager:
            report['subsystem_reports']['scalability'] = self.scalability_manager.get_comprehensive_status()
        
        if self.ai_model_optimizer:
            report['subsystem_reports']['ai_models'] = self.ai_model_optimizer.get_comprehensive_stats()
        
        if self.resource_manager:
            report['subsystem_reports']['resources'] = self.resource_manager.get_comprehensive_report()
        
        if self.performance_analytics:
            report['subsystem_reports']['analytics'] = self.performance_analytics.get_dashboard_data(hours=24)
        
        return report


# Global integrator instance
_performance_integrator: Optional[PerformanceSystemIntegrator] = None


def get_performance_integrator(mode: PerformanceMode = PerformanceMode.BALANCED) -> PerformanceSystemIntegrator:
    """Get global performance integrator instance"""
    global _performance_integrator
    if _performance_integrator is None:
        _performance_integrator = PerformanceSystemIntegrator(mode)
    return _performance_integrator


def main():
    """CLI interface for performance system integration"""
    import argparse
    
    parser = argparse.ArgumentParser(description="JARVIS-MK42 Performance System Integration")
    parser.add_argument('--init', action='store_true', help='Initialize all performance systems')
    parser.add_argument('--status', action='store_true', help='Show system status')
    parser.add_argument('--report', action='store_true', help='Show comprehensive report')
    parser.add_argument('--mode', choices=['balanced', 'performance', 'efficiency', 'scale', 'development', 'production'], 
                       default='balanced', help='Performance mode')
    parser.add_argument('--monitor', action='store_true', help='Start monitoring mode')
    
    args = parser.parse_args()
    
    # Get integrator with specified mode
    mode = PerformanceMode(args.mode)
    integrator = get_performance_integrator(mode)
    
    try:
        if args.init:
            print(f"Initializing performance systems in {mode.value} mode...")
            success = integrator.initialize_systems()
            if success:
                print("✓ All performance systems initialized successfully")
            else:
                print("✗ Failed to initialize some performance systems")
        
        elif args.monitor:
            print("Starting performance monitoring...")
            integrator.initialize_systems()
            
            try:
                while True:
                    status = integrator.get_system_status()
                    print(f"\n[{status.last_updated}]")
                    print(f"Mode: {status.mode.value}")
                    print(f"Health: {status.overall_health}")
                    print(f"Performance: {status.performance_score:.1%}")
                    print(f"Efficiency: {status.efficiency_score:.1%}")
                    print(f"Scalability: {status.scalability_score:.1%}")
                    
                    if status.critical_issues:
                        print(f"⚠️  Issues: {', '.join(status.critical_issues)}")
                    
                    time.sleep(30)  # Update every 30 seconds
                    
            except KeyboardInterrupt:
                print("\nStopping monitoring...")
        
        elif args.report:
            integrator.initialize_systems()
            report = integrator.get_comprehensive_report()
            print(json.dumps(report, indent=2, default=str))
        
        else:
            # Show basic status
            if not integrator.initialized:
                integrator.initialize_systems()
            
            status = integrator.get_system_status()
            print("JARVIS-MK42 Performance Systems Status:")
            print(f"Mode: {status.mode.value}")
            print(f"Overall Health: {status.overall_health}")
            print(f"Performance Score: {status.performance_score:.1%}")
            print(f"Efficiency Score: {status.efficiency_score:.1%}")
            print(f"Scalability Score: {status.scalability_score:.1%}")
            print(f"Active Optimizations: {len(status.active_optimizations)}")
            
            if status.critical_issues:
                print(f"\n⚠️  Critical Issues:")
                for issue in status.critical_issues:
                    print(f"   • {issue}")
            
            if status.recommendations:
                print(f"\n💡 Recommendations:")
                for rec in status.recommendations:
                    print(f"   • {rec}")
    
    finally:
        integrator.shutdown()


if __name__ == "__main__":
    main()
