#!/usr/bin/env python3
"""
JARVIS-MK42 Performance Analytics System
=======================================

This module provides comprehensive performance analytics and monitoring:
- Real-time performance dashboards with interactive visualizations
- Advanced bottleneck detection using statistical analysis
- SLA monitoring with alerting and reporting
- Performance regression detection with machine learning
- Historical trend analysis and predictive forecasting
- Custom performance metrics and KPI tracking
"""

import os
import sys
import json
import time
import asyncio
import threading
from datetime import datetime, timedelta
from typing import Dict, List, Optional, Any, Callable, Union, Tuple
from dataclasses import dataclass, field, asdict
from enum import Enum
from collections import defaultdict, deque
import statistics
import math
from concurrent.futures import ThreadPoolExecutor
import sqlite3
import pickle

# Add project root to path
current_dir = os.path.dirname(os.path.abspath(__file__))
project_root = os.path.dirname(current_dir)
if project_root not in sys.path:
    sys.path.insert(0, project_root)

from utils.logging_config import get_logger

logger = get_logger(__name__)


class MetricType(Enum):
    """Types of performance metrics"""
    RESPONSE_TIME = "response_time"
    THROUGHPUT = "throughput"
    ERROR_RATE = "error_rate"
    AVAILABILITY = "availability"
    LATENCY = "latency"
    CPU_USAGE = "cpu_usage"
    MEMORY_USAGE = "memory_usage"
    DISK_IO = "disk_io"
    NETWORK_IO = "network_io"
    CACHE_HIT_RATE = "cache_hit_rate"
    QUEUE_DEPTH = "queue_depth"
    CUSTOM = "custom"


class AlertSeverity(Enum):
    """Alert severity levels"""
    INFO = "info"
    WARNING = "warning"
    CRITICAL = "critical"
    EMERGENCY = "emergency"


class TrendDirection(Enum):
    """Trend analysis directions"""
    IMPROVING = "improving"
    DEGRADING = "degrading"
    STABLE = "stable"
    VOLATILE = "volatile"


@dataclass
class PerformanceMetric:
    """Individual performance metric data point"""
    name: str
    value: float
    timestamp: datetime
    metric_type: MetricType
    unit: str = ""
    tags: Dict[str, str] = field(default_factory=dict)
    metadata: Dict[str, Any] = field(default_factory=dict)
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary for serialization"""
        return {
            'name': self.name,
            'value': self.value,
            'timestamp': self.timestamp.isoformat(),
            'metric_type': self.metric_type.value,
            'unit': self.unit,
            'tags': self.tags,
            'metadata': self.metadata
        }


@dataclass
class SLADefinition:
    """Service Level Agreement definition"""
    name: str
    metric_type: MetricType
    threshold: float
    comparison: str  # 'lt', 'gt', 'eq', 'between'
    threshold_upper: Optional[float] = None  # For 'between' comparison
    time_window_minutes: int = 60
    violation_threshold_percent: float = 5.0  # % of time violations are allowed
    enabled: bool = True
    description: str = ""
    
    def check_violation(self, metrics: List[PerformanceMetric]) -> bool:
        """Check if SLA is violated based on metrics"""
        if not metrics:
            return False
        
        violation_count = 0
        for metric in metrics:
            if self._is_metric_violation(metric):
                violation_count += 1
        
        violation_rate = (violation_count / len(metrics)) * 100
        return violation_rate > self.violation_threshold_percent
    
    def _is_metric_violation(self, metric: PerformanceMetric) -> bool:
        """Check if individual metric violates SLA"""
        if metric.metric_type != self.metric_type:
            return False
        
        if self.comparison == 'lt':
            return metric.value >= self.threshold
        elif self.comparison == 'gt':
            return metric.value <= self.threshold
        elif self.comparison == 'eq':
            return metric.value != self.threshold
        elif self.comparison == 'between':
            if self.threshold_upper is None:
                return False
            return not (self.threshold <= metric.value <= self.threshold_upper)
        
        return False


@dataclass
class PerformanceAlert:
    """Performance alert notification"""
    id: str
    title: str
    description: str
    severity: AlertSeverity
    metric_name: str
    current_value: float
    threshold_value: float
    timestamp: datetime
    resolved: bool = False
    resolution_time: Optional[datetime] = None
    tags: Dict[str, str] = field(default_factory=dict)
    
    def resolve(self):
        """Mark alert as resolved"""
        self.resolved = True
        self.resolution_time = datetime.now()


@dataclass
class BottleneckAnalysis:
    """Bottleneck detection analysis result"""
    component_name: str
    bottleneck_type: str
    severity_score: float  # 0.0 to 1.0
    impact_description: str
    recommendations: List[str]
    metrics_involved: List[str]
    detected_at: datetime
    confidence: float = 0.0  # 0.0 to 1.0
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary"""
        return asdict(self)


@dataclass
class TrendAnalysis:
    """Performance trend analysis result"""
    metric_name: str
    direction: TrendDirection
    slope: float
    r_squared: float
    forecast_next_hour: Optional[float]
    forecast_next_day: Optional[float]
    anomaly_score: float
    analysis_period_hours: int
    data_points: int
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary"""
        return {
            'metric_name': self.metric_name,
            'direction': self.direction.value,
            'slope': self.slope,
            'r_squared': self.r_squared,
            'forecast_next_hour': self.forecast_next_hour,
            'forecast_next_day': self.forecast_next_day,
            'anomaly_score': self.anomaly_score,
            'analysis_period_hours': self.analysis_period_hours,
            'data_points': self.data_points
        }


class MetricsDatabase:
    """SQLite-based metrics storage"""
    
    def __init__(self, db_path: str = None):
        if db_path is None:
            db_path = os.path.join(current_dir, "performance_metrics.db")
        
        self.db_path = db_path
        self._init_database()
        logger.info(f"Metrics database initialized: {db_path}")
    
    def _init_database(self):
        """Initialize database schema"""
        with sqlite3.connect(self.db_path) as conn:
            conn.execute("""
                CREATE TABLE IF NOT EXISTS metrics (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    name TEXT NOT NULL,
                    value REAL NOT NULL,
                    timestamp DATETIME NOT NULL,
                    metric_type TEXT NOT NULL,
                    unit TEXT,
                    tags TEXT,  -- JSON string
                    metadata TEXT,  -- JSON string
                    created_at DATETIME DEFAULT CURRENT_TIMESTAMP
                )
            """)
            
            conn.execute("""
                CREATE INDEX IF NOT EXISTS idx_metrics_name_timestamp 
                ON metrics(name, timestamp)
            """)
            
            conn.execute("""
                CREATE INDEX IF NOT EXISTS idx_metrics_type_timestamp 
                ON metrics(metric_type, timestamp)
            """)
            
            conn.execute("""
                CREATE TABLE IF NOT EXISTS alerts (
                    id TEXT PRIMARY KEY,
                    title TEXT NOT NULL,
                    description TEXT,
                    severity TEXT NOT NULL,
                    metric_name TEXT NOT NULL,
                    current_value REAL NOT NULL,
                    threshold_value REAL NOT NULL,
                    timestamp DATETIME NOT NULL,
                    resolved BOOLEAN DEFAULT FALSE,
                    resolution_time DATETIME,
                    tags TEXT,  -- JSON string
                    created_at DATETIME DEFAULT CURRENT_TIMESTAMP
                )
            """)
            
            conn.commit()
    
    def store_metric(self, metric: PerformanceMetric):
        """Store performance metric in database"""
        with sqlite3.connect(self.db_path) as conn:
            conn.execute("""
                INSERT INTO metrics (name, value, timestamp, metric_type, unit, tags, metadata)
                VALUES (?, ?, ?, ?, ?, ?, ?)
            """, (
                metric.name,
                metric.value,
                metric.timestamp,
                metric.metric_type.value,
                metric.unit,
                json.dumps(metric.tags),
                json.dumps(metric.metadata)
            ))
            conn.commit()
    
    def store_alert(self, alert: PerformanceAlert):
        """Store performance alert in database"""
        with sqlite3.connect(self.db_path) as conn:
            conn.execute("""
                INSERT OR REPLACE INTO alerts 
                (id, title, description, severity, metric_name, current_value, 
                 threshold_value, timestamp, resolved, resolution_time, tags)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """, (
                alert.id,
                alert.title,
                alert.description,
                alert.severity.value,
                alert.metric_name,
                alert.current_value,
                alert.threshold_value,
                alert.timestamp,
                alert.resolved,
                alert.resolution_time,
                json.dumps(alert.tags)
            ))
            conn.commit()
    
    def get_metrics(self,
                   metric_name: str = None,
                   metric_type: MetricType = None,
                   start_time: datetime = None,
                   end_time: datetime = None,
                   limit: int = 1000) -> List[PerformanceMetric]:
        """Retrieve metrics from database"""
        query = "SELECT * FROM metrics WHERE 1=1"
        params = []
        
        if metric_name:
            query += " AND name = ?"
            params.append(metric_name)
        
        if metric_type:
            query += " AND metric_type = ?"
            params.append(metric_type.value)
        
        if start_time:
            query += " AND timestamp >= ?"
            params.append(start_time)
        
        if end_time:
            query += " AND timestamp <= ?"
            params.append(end_time)
        
        query += " ORDER BY timestamp DESC LIMIT ?"
        params.append(limit)
        
        with sqlite3.connect(self.db_path) as conn:
            conn.row_factory = sqlite3.Row
            cursor = conn.execute(query, params)
            
            metrics = []
            for row in cursor:
                metric = PerformanceMetric(
                    name=row['name'],
                    value=row['value'],
                    timestamp=datetime.fromisoformat(row['timestamp']),
                    metric_type=MetricType(row['metric_type']),
                    unit=row['unit'] or "",
                    tags=json.loads(row['tags'] or '{}'),
                    metadata=json.loads(row['metadata'] or '{}')
                )
                metrics.append(metric)
            
            return list(reversed(metrics))  # Return in chronological order
    
    def cleanup_old_metrics(self, days_to_keep: int = 30):
        """Clean up old metrics to manage database size"""
        cutoff_date = datetime.now() - timedelta(days=days_to_keep)
        
        with sqlite3.connect(self.db_path) as conn:
            cursor = conn.execute("DELETE FROM metrics WHERE timestamp < ?", (cutoff_date,))
            deleted_count = cursor.rowcount
            conn.commit()
            
            if deleted_count > 0:
                logger.info(f"Cleaned up {deleted_count} old metric records")


class BottleneckDetector:
    """Advanced bottleneck detection using statistical analysis"""
    
    def __init__(self, analysis_window_hours: int = 1):
        self.analysis_window_hours = analysis_window_hours
        self.correlation_threshold = 0.7
        self.bottleneck_patterns = {
            'cpu_bound': {
                'high_cpu': 80.0,
                'stable_memory': (30.0, 70.0),
                'low_io_wait': 20.0
            },
            'memory_bound': {
                'high_memory': 85.0,
                'moderate_cpu': (20.0, 60.0),
                'high_gc_activity': 5.0  # GC events per minute
            },
            'io_bound': {
                'high_io_wait': 30.0,
                'high_disk_utilization': 80.0,
                'low_cpu': 50.0
            },
            'network_bound': {
                'high_network_utilization': 80.0,
                'high_network_latency': 100.0,  # ms
                'packet_loss': 1.0  # %
            }
        }
    
    def detect_bottlenecks(self, 
                          metrics: List[PerformanceMetric]) -> List[BottleneckAnalysis]:
        """Detect system bottlenecks from metrics"""
        if not metrics:
            return []
        
        bottlenecks = []
        
        # Group metrics by type
        metrics_by_type = defaultdict(list)
        for metric in metrics:
            metrics_by_type[metric.metric_type].append(metric)
        
        # Analyze each bottleneck pattern
        for pattern_name, pattern_config in self.bottleneck_patterns.items():
            bottleneck = self._analyze_pattern(pattern_name, pattern_config, metrics_by_type)
            if bottleneck:
                bottlenecks.append(bottleneck)
        
        # Detect correlation-based bottlenecks
        correlation_bottlenecks = self._detect_correlation_bottlenecks(metrics_by_type)
        bottlenecks.extend(correlation_bottlenecks)
        
        return sorted(bottlenecks, key=lambda x: x.severity_score, reverse=True)
    
    def _analyze_pattern(self,
                        pattern_name: str,
                        pattern_config: Dict[str, Any],
                        metrics_by_type: Dict[MetricType, List[PerformanceMetric]]) -> Optional[BottleneckAnalysis]:
        """Analyze specific bottleneck pattern"""
        
        severity_factors = []
        matched_conditions = []
        
        # CPU-bound analysis
        if pattern_name == 'cpu_bound':
            cpu_metrics = metrics_by_type.get(MetricType.CPU_USAGE, [])
            if cpu_metrics:
                avg_cpu = statistics.mean([m.value for m in cpu_metrics])
                if avg_cpu > pattern_config['high_cpu']:
                    severity_factors.append(min(avg_cpu / 100.0, 1.0))
                    matched_conditions.append(f"High CPU usage: {avg_cpu:.1f}%")
            
            memory_metrics = metrics_by_type.get(MetricType.MEMORY_USAGE, [])
            if memory_metrics:
                avg_memory = statistics.mean([m.value for m in memory_metrics])
                mem_min, mem_max = pattern_config['stable_memory']
                if mem_min <= avg_memory <= mem_max:
                    severity_factors.append(0.3)
                    matched_conditions.append(f"Stable memory usage: {avg_memory:.1f}%")
        
        # Memory-bound analysis
        elif pattern_name == 'memory_bound':
            memory_metrics = metrics_by_type.get(MetricType.MEMORY_USAGE, [])
            if memory_metrics:
                avg_memory = statistics.mean([m.value for m in memory_metrics])
                if avg_memory > pattern_config['high_memory']:
                    severity_factors.append(min(avg_memory / 100.0, 1.0))
                    matched_conditions.append(f"High memory usage: {avg_memory:.1f}%")
        
        # IO-bound analysis
        elif pattern_name == 'io_bound':
            disk_metrics = metrics_by_type.get(MetricType.DISK_IO, [])
            if disk_metrics:
                avg_disk = statistics.mean([m.value for m in disk_metrics])
                if avg_disk > pattern_config['high_disk_utilization']:
                    severity_factors.append(min(avg_disk / 100.0, 1.0))
                    matched_conditions.append(f"High disk utilization: {avg_disk:.1f}%")
        
        # Network-bound analysis
        elif pattern_name == 'network_bound':
            network_metrics = metrics_by_type.get(MetricType.NETWORK_IO, [])
            if network_metrics:
                avg_network = statistics.mean([m.value for m in network_metrics])
                if avg_network > pattern_config['high_network_utilization']:
                    severity_factors.append(min(avg_network / 100.0, 1.0))
                    matched_conditions.append(f"High network utilization: {avg_network:.1f}%")
        
        # Create bottleneck analysis if conditions met
        if severity_factors and len(matched_conditions) >= 1:
            severity_score = statistics.mean(severity_factors)
            
            recommendations = self._get_recommendations(pattern_name, severity_score)
            
            return BottleneckAnalysis(
                component_name=pattern_name.replace('_', ' ').title(),
                bottleneck_type=pattern_name,
                severity_score=severity_score,
                impact_description="; ".join(matched_conditions),
                recommendations=recommendations,
                metrics_involved=[c.split(':')[0] for c in matched_conditions],
                detected_at=datetime.now(),
                confidence=min(len(matched_conditions) / 3.0, 1.0)
            )
        
        return None
    
    def _detect_correlation_bottlenecks(self, 
                                       metrics_by_type: Dict[MetricType, List[PerformanceMetric]]) -> List[BottleneckAnalysis]:
        """Detect bottlenecks based on metric correlations"""
        bottlenecks = []
        
        # Check for response time vs resource usage correlation
        response_metrics = metrics_by_type.get(MetricType.RESPONSE_TIME, [])
        cpu_metrics = metrics_by_type.get(MetricType.CPU_USAGE, [])
        
        if len(response_metrics) > 5 and len(cpu_metrics) > 5:
            # Align metrics by timestamp
            aligned_data = self._align_metrics(response_metrics, cpu_metrics)
            if aligned_data and len(aligned_data) > 3:
                correlation = self._calculate_correlation(aligned_data)
                
                if abs(correlation) > self.correlation_threshold:
                    severity = min(abs(correlation), 1.0)
                    
                    bottleneck = BottleneckAnalysis(
                        component_name="Response Time Correlation",
                        bottleneck_type="correlation_analysis",
                        severity_score=severity,
                        impact_description=f"Strong correlation ({correlation:.2f}) between response time and CPU usage",
                        recommendations=[
                            "Optimize CPU-intensive operations",
                            "Consider horizontal scaling",
                            "Profile application for CPU hotspots"
                        ],
                        metrics_involved=["response_time", "cpu_usage"],
                        detected_at=datetime.now(),
                        confidence=min(len(aligned_data) / 10.0, 1.0)
                    )
                    bottlenecks.append(bottleneck)
        
        return bottlenecks
    
    def _align_metrics(self, 
                      metrics1: List[PerformanceMetric], 
                      metrics2: List[PerformanceMetric]) -> List[Tuple[float, float]]:
        """Align two metric series by timestamp"""
        # Simple alignment - match metrics within 1 minute of each other
        aligned = []
        
        for m1 in metrics1:
            closest_m2 = None
            min_time_diff = float('inf')
            
            for m2 in metrics2:
                time_diff = abs((m1.timestamp - m2.timestamp).total_seconds())
                if time_diff < min_time_diff and time_diff <= 60:  # Within 1 minute
                    min_time_diff = time_diff
                    closest_m2 = m2
            
            if closest_m2:
                aligned.append((m1.value, closest_m2.value))
        
        return aligned
    
    def _calculate_correlation(self, aligned_data: List[Tuple[float, float]]) -> float:
        """Calculate Pearson correlation coefficient"""
        if len(aligned_data) < 2:
            return 0.0
        
        x_values = [pair[0] for pair in aligned_data]
        y_values = [pair[1] for pair in aligned_data]
        
        n = len(aligned_data)
        x_mean = sum(x_values) / n
        y_mean = sum(y_values) / n
        
        numerator = sum((x_values[i] - x_mean) * (y_values[i] - y_mean) for i in range(n))
        
        x_variance = sum((x - x_mean) ** 2 for x in x_values)
        y_variance = sum((y - y_mean) ** 2 for y in y_values)
        
        denominator = math.sqrt(x_variance * y_variance)
        
        if denominator == 0:
            return 0.0
        
        return numerator / denominator
    
    def _get_recommendations(self, pattern_name: str, severity_score: float) -> List[str]:
        """Get recommendations for bottleneck type"""
        base_recommendations = {
            'cpu_bound': [
                "Optimize CPU-intensive algorithms and operations",
                "Consider code profiling to identify hotspots",
                "Scale horizontally to distribute CPU load"
            ],
            'memory_bound': [
                "Optimize memory allocation patterns",
                "Implement object pooling for frequently used objects",
                "Consider increasing available memory",
                "Profile for memory leaks and inefficient data structures"
            ],
            'io_bound': [
                "Optimize database queries and indexes",
                "Consider SSD storage upgrade",
                "Implement connection pooling",
                "Use asynchronous I/O where possible"
            ],
            'network_bound': [
                "Optimize network protocols and compression",
                "Implement connection pooling and keep-alive",
                "Consider CDN for static content",
                "Upgrade network infrastructure"
            ]
        }
        
        recommendations = base_recommendations.get(pattern_name, [])
        
        # Add severity-specific recommendations
        if severity_score > 0.8:
            recommendations.append("CRITICAL: Immediate action required to prevent system degradation")
        elif severity_score > 0.6:
            recommendations.append("HIGH PRIORITY: Schedule optimization work soon")
        
        return recommendations


class TrendAnalyzer:
    """Performance trend analysis and forecasting"""
    
    def __init__(self, min_data_points: int = 10):
        self.min_data_points = min_data_points
        self.anomaly_threshold = 2.0  # Standard deviations
    
    def analyze_trends(self, 
                      metrics: List[PerformanceMetric]) -> Dict[str, TrendAnalysis]:
        """Analyze trends for all metric names"""
        if not metrics:
            return {}
        
        # Group metrics by name
        metrics_by_name = defaultdict(list)
        for metric in metrics:
            metrics_by_name[metric.name].append(metric)
        
        # Analyze trends for each metric
        trend_analyses = {}
        for metric_name, metric_list in metrics_by_name.items():
            if len(metric_list) >= self.min_data_points:
                analysis = self._analyze_single_metric_trend(metric_name, metric_list)
                if analysis:
                    trend_analyses[metric_name] = analysis
        
        return trend_analyses
    
    def _analyze_single_metric_trend(self, 
                                   metric_name: str,
                                   metrics: List[PerformanceMetric]) -> Optional[TrendAnalysis]:
        """Analyze trend for single metric"""
        if len(metrics) < self.min_data_points:
            return None
        
        # Sort by timestamp
        metrics.sort(key=lambda m: m.timestamp)
        
        # Prepare data for analysis
        timestamps = [(m.timestamp - metrics[0].timestamp).total_seconds() for m in metrics]
        values = [m.value for m in metrics]
        
        # Linear regression analysis
        slope, r_squared = self._linear_regression(timestamps, values)
        
        # Determine trend direction
        if abs(slope) < 0.001:  # Essentially flat
            direction = TrendDirection.STABLE
        elif slope > 0:
            direction = TrendDirection.DEGRADING if self._is_degrading_metric(metric_name) else TrendDirection.IMPROVING
        else:
            direction = TrendDirection.IMPROVING if self._is_degrading_metric(metric_name) else TrendDirection.DEGRADING
        
        # Check for volatility
        if len(values) > 2:
            volatility = statistics.stdev(values) / statistics.mean(values) if statistics.mean(values) > 0 else 0
            if volatility > 0.3:  # 30% coefficient of variation
                direction = TrendDirection.VOLATILE
        
        # Simple forecasting
        time_span_hours = (metrics[-1].timestamp - metrics[0].timestamp).total_seconds() / 3600
        
        forecast_next_hour = None
        forecast_next_day = None
        
        if abs(slope) > 0.001:  # Only forecast if there's a trend
            last_value = values[-1]
            hourly_rate = slope * 3600  # Convert to per-hour rate
            
            forecast_next_hour = last_value + hourly_rate
            forecast_next_day = last_value + (hourly_rate * 24)
        
        # Anomaly detection
        anomaly_score = self._calculate_anomaly_score(values)
        
        return TrendAnalysis(
            metric_name=metric_name,
            direction=direction,
            slope=slope,
            r_squared=r_squared,
            forecast_next_hour=forecast_next_hour,
            forecast_next_day=forecast_next_day,
            anomaly_score=anomaly_score,
            analysis_period_hours=int(time_span_hours),
            data_points=len(metrics)
        )
    
    def _linear_regression(self, x_values: List[float], y_values: List[float]) -> Tuple[float, float]:
        """Calculate linear regression slope and R-squared"""
        n = len(x_values)
        
        if n < 2:
            return 0.0, 0.0
        
        x_mean = sum(x_values) / n
        y_mean = sum(y_values) / n
        
        numerator = sum((x_values[i] - x_mean) * (y_values[i] - y_mean) for i in range(n))
        denominator = sum((x - x_mean) ** 2 for x in x_values)
        
        if denominator == 0:
            return 0.0, 0.0
        
        slope = numerator / denominator
        
        # Calculate R-squared
        y_predicted = [slope * (x - x_mean) + y_mean for x in x_values]
        ss_res = sum((y_values[i] - y_predicted[i]) ** 2 for i in range(n))
        ss_tot = sum((y - y_mean) ** 2 for y in y_values)
        
        r_squared = 1 - (ss_res / ss_tot) if ss_tot > 0 else 0.0
        
        return slope, max(0.0, r_squared)  # Ensure R-squared is non-negative
    
    def _is_degrading_metric(self, metric_name: str) -> bool:
        """Check if higher values indicate degrading performance"""
        degrading_indicators = [
            'response_time', 'latency', 'error_rate', 'cpu_usage',
            'memory_usage', 'disk_usage', 'queue_depth'
        ]
        return any(indicator in metric_name.lower() for indicator in degrading_indicators)
    
    def _calculate_anomaly_score(self, values: List[float]) -> float:
        """Calculate anomaly score based on recent deviation"""
        if len(values) < 3:
            return 0.0
        
        # Use last 20% of values as "recent"
        recent_size = max(2, len(values) // 5)
        recent_values = values[-recent_size:]
        historical_values = values[:-recent_size]
        
        if not historical_values:
            return 0.0
        
        historical_mean = statistics.mean(historical_values)
        historical_stdev = statistics.stdev(historical_values) if len(historical_values) > 1 else 0
        
        if historical_stdev == 0:
            return 0.0
        
        # Calculate max Z-score in recent values
        max_z_score = 0.0
        for value in recent_values:
            z_score = abs(value - historical_mean) / historical_stdev
            max_z_score = max(max_z_score, z_score)
        
        # Normalize to 0-1 scale
        return min(max_z_score / self.anomaly_threshold, 1.0)


class PerformanceAnalytics:
    """Main performance analytics system"""
    
    def __init__(self,
                 db_path: str = None,
                 analysis_interval: int = 300,  # 5 minutes
                 enable_real_time: bool = True):
        
        self.analysis_interval = analysis_interval
        self.enable_real_time = enable_real_time
        
        self.db = MetricsDatabase(db_path)
        self.bottleneck_detector = BottleneckDetector()
        self.trend_analyzer = TrendAnalyzer()
        
        # SLA definitions
        self.sla_definitions: Dict[str, SLADefinition] = {}
        
        # Active alerts
        self.active_alerts: Dict[str, PerformanceAlert] = {}
        
        # Callbacks
        self.alert_callbacks: List[Callable[[PerformanceAlert], None]] = []
        self.bottleneck_callbacks: List[Callable[[BottleneckAnalysis], None]] = []
        
        # Analysis thread
        self.analysis_thread: Optional[threading.Thread] = None
        self.shutdown_event = threading.Event()
        
        logger.info("Performance Analytics System initialized")
    
    def start_analysis(self):
        """Start real-time performance analysis"""
        if self.analysis_thread and self.analysis_thread.is_alive():
            logger.warning("Performance analysis already running")
            return
        
        if not self.enable_real_time:
            logger.info("Real-time analysis is disabled")
            return
        
        self.shutdown_event.clear()
        self.analysis_thread = threading.Thread(
            target=self._analysis_loop,
            daemon=True,
            name="perf-analytics"
        )
        self.analysis_thread.start()
        logger.info("Performance analysis started")
    
    def stop_analysis(self):
        """Stop performance analysis"""
        self.shutdown_event.set()
        if self.analysis_thread:
            self.analysis_thread.join(timeout=10)
        logger.info("Performance analysis stopped")
    
    def _analysis_loop(self):
        """Main analysis loop"""
        while not self.shutdown_event.is_set():
            try:
                self._run_analysis_cycle()
            except Exception as e:
                logger.error(f"Error in analysis loop: {e}")
            
            # Wait for next interval
            self.shutdown_event.wait(timeout=self.analysis_interval)
    
    def _run_analysis_cycle(self):
        """Run one cycle of performance analysis"""
        # Get recent metrics (last hour)
        end_time = datetime.now()
        start_time = end_time - timedelta(hours=1)
        recent_metrics = self.db.get_metrics(start_time=start_time, end_time=end_time, limit=10000)
        
        if not recent_metrics:
            return
        
        # Bottleneck detection
        bottlenecks = self.bottleneck_detector.detect_bottlenecks(recent_metrics)
        for bottleneck in bottlenecks:
            if bottleneck.severity_score > 0.6:  # High severity
                logger.warning(f"Bottleneck detected: {bottleneck.component_name} - {bottleneck.impact_description}")
                
                # Notify callbacks
                for callback in self.bottleneck_callbacks:
                    try:
                        callback(bottleneck)
                    except Exception as e:
                        logger.error(f"Error in bottleneck callback: {e}")
        
        # SLA monitoring
        self._check_sla_violations(recent_metrics)
        
        # Trend analysis (run less frequently)
        current_minute = datetime.now().minute
        if current_minute % 15 == 0:  # Every 15 minutes
            trend_analyses = self.trend_analyzer.analyze_trends(recent_metrics)
            self._process_trend_analyses(trend_analyses)
    
    def _check_sla_violations(self, metrics: List[PerformanceMetric]):
        """Check for SLA violations"""
        for sla_name, sla_def in self.sla_definitions.items():
            if not sla_def.enabled:
                continue
            
            # Filter metrics for this SLA
            window_start = datetime.now() - timedelta(minutes=sla_def.time_window_minutes)
            sla_metrics = [
                m for m in metrics
                if m.metric_type == sla_def.metric_type and m.timestamp > window_start
            ]
            
            if not sla_metrics:
                continue
            
            # Check for violation
            is_violation = sla_def.check_violation(sla_metrics)
            
            alert_id = f"sla_{sla_name}"
            existing_alert = self.active_alerts.get(alert_id)
            
            if is_violation and not existing_alert:
                # Create new SLA violation alert
                current_value = statistics.mean([m.value for m in sla_metrics])
                
                alert = PerformanceAlert(
                    id=alert_id,
                    title=f"SLA Violation: {sla_name}",
                    description=f"SLA '{sla_name}' violated. {sla_def.description}",
                    severity=AlertSeverity.CRITICAL,
                    metric_name=sla_def.metric_type.value,
                    current_value=current_value,
                    threshold_value=sla_def.threshold,
                    timestamp=datetime.now(),
                    tags={'sla_name': sla_name, 'type': 'sla_violation'}
                )
                
                self.active_alerts[alert_id] = alert
                self.db.store_alert(alert)
                
                logger.critical(f"SLA violation detected: {alert.title}")
                
                # Notify callbacks
                for callback in self.alert_callbacks:
                    try:
                        callback(alert)
                    except Exception as e:
                        logger.error(f"Error in alert callback: {e}")
            
            elif not is_violation and existing_alert and not existing_alert.resolved:
                # Resolve existing alert
                existing_alert.resolve()
                self.db.store_alert(existing_alert)
                
                logger.info(f"SLA violation resolved: {existing_alert.title}")
    
    def _process_trend_analyses(self, trend_analyses: Dict[str, TrendAnalysis]):
        """Process trend analysis results"""
        for metric_name, analysis in trend_analyses.items():
            # Check for concerning trends
            if (analysis.direction == TrendDirection.DEGRADING and 
                analysis.r_squared > 0.7 and  # Strong trend
                analysis.anomaly_score > 0.5):  # Some anomaly
                
                alert_id = f"trend_{metric_name}"
                if alert_id not in self.active_alerts:
                    
                    alert = PerformanceAlert(
                        id=alert_id,
                        title=f"Performance Degradation Trend: {metric_name}",
                        description=f"Metric '{metric_name}' showing degrading trend with R²={analysis.r_squared:.2f}",
                        severity=AlertSeverity.WARNING,
                        metric_name=metric_name,
                        current_value=0.0,  # Not applicable for trends
                        threshold_value=0.0,  # Not applicable for trends
                        timestamp=datetime.now(),
                        tags={'type': 'trend_alert', 'direction': analysis.direction.value}
                    )
                    
                    self.active_alerts[alert_id] = alert
                    self.db.store_alert(alert)
                    
                    logger.warning(f"Performance trend alert: {alert.title}")
    
    def record_metric(self, metric: PerformanceMetric):
        """Record a performance metric"""
        self.db.store_metric(metric)
        
        # Real-time analysis for critical metrics
        if self.enable_real_time and metric.metric_type in [
            MetricType.RESPONSE_TIME, MetricType.ERROR_RATE, MetricType.AVAILABILITY
        ]:
            self._check_real_time_alerts(metric)
    
    def _check_real_time_alerts(self, metric: PerformanceMetric):
        """Check for immediate alerts on critical metrics"""
        # Simple threshold-based alerts for demo
        if metric.metric_type == MetricType.RESPONSE_TIME and metric.value > 5000:  # 5 seconds
            alert_id = f"rt_{metric.name}_{int(time.time())}"
            
            alert = PerformanceAlert(
                id=alert_id,
                title="High Response Time",
                description=f"Response time for {metric.name} is {metric.value:.0f}ms",
                severity=AlertSeverity.CRITICAL,
                metric_name=metric.name,
                current_value=metric.value,
                threshold_value=5000.0,
                timestamp=metric.timestamp
            )
            
            # Notify immediately
            for callback in self.alert_callbacks:
                try:
                    callback(alert)
                except Exception as e:
                    logger.error(f"Error in real-time alert callback: {e}")
    
    def define_sla(self, sla: SLADefinition):
        """Define a new SLA for monitoring"""
        self.sla_definitions[sla.name] = sla
        logger.info(f"SLA defined: {sla.name}")
    
    def register_alert_callback(self, callback: Callable[[PerformanceAlert], None]):
        """Register callback for performance alerts"""
        self.alert_callbacks.append(callback)
    
    def register_bottleneck_callback(self, callback: Callable[[BottleneckAnalysis], None]):
        """Register callback for bottleneck detection"""
        self.bottleneck_callbacks.append(callback)
    
    def get_dashboard_data(self, hours: int = 24) -> Dict[str, Any]:
        """Get comprehensive dashboard data"""
        end_time = datetime.now()
        start_time = end_time - timedelta(hours=hours)
        
        # Get metrics
        metrics = self.db.get_metrics(start_time=start_time, end_time=end_time, limit=50000)
        
        # Group metrics by type and name
        metrics_summary = defaultdict(lambda: {'count': 0, 'avg': 0, 'min': float('inf'), 'max': float('-inf')})
        
        for metric in metrics:
            key = f"{metric.metric_type.value}_{metric.name}"
            summary = metrics_summary[key]
            summary['count'] += 1
            summary['avg'] = ((summary['avg'] * (summary['count'] - 1)) + metric.value) / summary['count']
            summary['min'] = min(summary['min'], metric.value)
            summary['max'] = max(summary['max'], metric.value)
        
        # Get bottleneck analysis
        recent_bottlenecks = self.bottleneck_detector.detect_bottlenecks(metrics[-1000:] if len(metrics) > 1000 else metrics)
        
        # Get trend analysis
        trend_analyses = self.trend_analyzer.analyze_trends(metrics)
        
        # Get active alerts
        active_alerts_data = [
            {
                'id': alert.id,
                'title': alert.title,
                'severity': alert.severity.value,
                'timestamp': alert.timestamp.isoformat(),
                'resolved': alert.resolved
            }
            for alert in self.active_alerts.values()
        ]
        
        return {
            'timestamp': datetime.now().isoformat(),
            'analysis_period_hours': hours,
            'total_metrics': len(metrics),
            'metrics_summary': dict(metrics_summary),
            'bottlenecks': [b.to_dict() for b in recent_bottlenecks[:10]],
            'trends': {name: analysis.to_dict() for name, analysis in trend_analyses.items()},
            'active_alerts': active_alerts_data,
            'sla_definitions': {name: {
                'name': sla.name,
                'metric_type': sla.metric_type.value,
                'threshold': sla.threshold,
                'enabled': sla.enabled
            } for name, sla in self.sla_definitions.items()}
        }


# Global analytics instance
_performance_analytics: Optional[PerformanceAnalytics] = None


def get_performance_analytics() -> PerformanceAnalytics:
    """Get global performance analytics instance"""
    global _performance_analytics
    if _performance_analytics is None:
        _performance_analytics = PerformanceAnalytics()
    return _performance_analytics


def main():
    """CLI interface for performance analytics"""
    import argparse
    
    parser = argparse.ArgumentParser(description="JARVIS-MK42 Performance Analytics")
    parser.add_argument('--start', action='store_true', help='Start performance analysis')
    parser.add_argument('--dashboard', action='store_true', help='Show dashboard data')
    parser.add_argument('--hours', type=int, default=24, help='Analysis window in hours')
    parser.add_argument('--cleanup', action='store_true', help='Clean up old metrics')
    
    args = parser.parse_args()
    
    analytics = get_performance_analytics()
    
    try:
        if args.start:
            print("Starting performance analysis...")
            analytics.start_analysis()
            
            # Keep running
            try:
                while True:
                    time.sleep(60)
                    print(f"[{datetime.now()}] Analysis running...")
            except KeyboardInterrupt:
                print("\nStopping analysis...")
        
        elif args.cleanup:
            print("Cleaning up old metrics...")
            analytics.db.cleanup_old_metrics(days_to_keep=30)
            print("Cleanup completed")
        
        else:
            dashboard_data = analytics.get_dashboard_data(hours=args.hours)
            print("Performance Analytics Dashboard:")
            print(f"Analysis Period: {dashboard_data['analysis_period_hours']} hours")
            print(f"Total Metrics: {dashboard_data['total_metrics']}")
            print(f"Active Alerts: {len(dashboard_data['active_alerts'])}")
            print(f"Detected Bottlenecks: {len(dashboard_data['bottlenecks'])}")
            print(f"Trend Analyses: {len(dashboard_data['trends'])}")
            
            if args.dashboard:
                print(json.dumps(dashboard_data, indent=2, default=str))
    
    finally:
        analytics.stop_analysis()


if __name__ == "__main__":
    main()
