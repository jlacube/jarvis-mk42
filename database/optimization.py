#!/usr/bin/env python3
"""
JARVIS-MK42 Database Optimization Module
=======================================

This module provides comprehensive database optimization capabilities including:
- Query performance analysis and optimization
- Index management and recommendations
- Connection pooling and optimization
- Database statistics collection and analysis
- Query caching mechanisms
- Performance monitoring and alerting
- Database health assessment and tuning
"""

import os
import sys
import json
import time
import sqlite3
import threading
import statistics
from datetime import datetime, timedelta
from typing import Dict, List, Optional, Any, Tuple, Union
from dataclasses import dataclass, field
from enum import Enum
from collections import defaultdict, deque
from contextlib import contextmanager
from pathlib import Path

# Add project root to path
current_dir = os.path.dirname(os.path.abspath(__file__))
project_root = os.path.dirname(current_dir)
if project_root not in sys.path:
    sys.path.insert(0, project_root)

from utils.logging_config import get_logger

logger = get_logger(__name__)

try:
    import sqlite3
    HAS_SQLITE = True
except ImportError:
    HAS_SQLITE = False
    logger.warning("sqlite3 not available - database optimization disabled")


class QueryType(Enum):
    """Types of database queries"""
    SELECT = "SELECT"
    INSERT = "INSERT"
    UPDATE = "UPDATE"
    DELETE = "DELETE"
    CREATE = "CREATE"
    DROP = "DROP"
    ALTER = "ALTER"
    PRAGMA = "PRAGMA"
    UNKNOWN = "UNKNOWN"


class OptimizationLevel(Enum):
    """Database optimization levels"""
    BASIC = "basic"
    STANDARD = "standard"
    AGGRESSIVE = "aggressive"
    CUSTOM = "custom"


@dataclass
class QueryMetrics:
    """Metrics for a database query"""
    query_id: str
    sql: str
    query_type: QueryType
    execution_time: float
    rows_affected: int
    rows_examined: int
    timestamp: datetime
    parameters: Dict[str, Any] = field(default_factory=dict)
    error: Optional[str] = None
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary"""
        return {
            'query_id': self.query_id,
            'sql': self.sql,
            'query_type': self.query_type.value,
            'execution_time': self.execution_time,
            'rows_affected': self.rows_affected,
            'rows_examined': self.rows_examined,
            'timestamp': self.timestamp.isoformat(),
            'parameters': self.parameters,
            'error': self.error
        }


@dataclass
class IndexRecommendation:
    """Database index recommendation"""
    table_name: str
    columns: List[str]
    index_type: str
    estimated_benefit: float
    reason: str
    sql_statement: str
    priority: int = 1  # 1=high, 2=medium, 3=low
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary"""
        return {
            'table_name': self.table_name,
            'columns': self.columns,
            'index_type': self.index_type,
            'estimated_benefit': self.estimated_benefit,
            'reason': self.reason,
            'sql_statement': self.sql_statement,
            'priority': self.priority
        }


@dataclass
class DatabaseStats:
    """Database statistics and health metrics"""
    database_path: str
    total_size_bytes: int
    table_count: int
    index_count: int
    page_size: int
    page_count: int
    free_pages: int
    fragmentation_percent: float
    last_vacuum: Optional[datetime]
    last_analyze: Optional[datetime]
    connections_active: int
    query_cache_hit_rate: float
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary"""
        return {
            'database_path': self.database_path,
            'total_size_bytes': self.total_size_bytes,
            'total_size_mb': round(self.total_size_bytes / (1024 * 1024), 2),
            'table_count': self.table_count,
            'index_count': self.index_count,
            'page_size': self.page_size,
            'page_count': self.page_count,
            'free_pages': self.free_pages,
            'fragmentation_percent': self.fragmentation_percent,
            'last_vacuum': self.last_vacuum.isoformat() if self.last_vacuum else None,
            'last_analyze': self.last_analyze.isoformat() if self.last_analyze else None,
            'connections_active': self.connections_active,
            'query_cache_hit_rate': self.query_cache_hit_rate
        }


class ConnectionPool:
    """Simple SQLite connection pool for better performance"""
    
    def __init__(self, database_path: str, max_connections: int = 10):
        self.database_path = database_path
        self.max_connections = max_connections
        self.available_connections = deque()
        self.active_connections = set()
        self.lock = threading.RLock()
        self.total_created = 0
        
    def _create_connection(self) -> sqlite3.Connection:
        """Create a new database connection"""
        conn = sqlite3.connect(
            self.database_path,
            timeout=30.0,
            check_same_thread=False,
            isolation_level=None  # Autocommit mode
        )
        
        # Enable optimizations
        conn.execute("PRAGMA journal_mode=WAL")
        conn.execute("PRAGMA synchronous=NORMAL")
        conn.execute("PRAGMA cache_size=-64000")  # 64MB cache
        conn.execute("PRAGMA temp_store=MEMORY")
        conn.execute("PRAGMA mmap_size=268435456")  # 256MB mmap
        
        self.total_created += 1
        return conn
    
    @contextmanager
    def get_connection(self):
        """Get a connection from the pool"""
        conn = None
        
        try:
            with self.lock:
                if self.available_connections:
                    conn = self.available_connections.popleft()
                elif len(self.active_connections) < self.max_connections:
                    conn = self._create_connection()
                else:
                    # Wait for a connection to become available
                    pass
            
            if conn is None:
                # Create temporary connection if pool is full
                conn = self._create_connection()
            
            with self.lock:
                self.active_connections.add(conn)
            
            yield conn
            
        finally:
            if conn:
                with self.lock:
                    self.active_connections.discard(conn)
                    if len(self.available_connections) < self.max_connections // 2:
                        self.available_connections.append(conn)
                    else:
                        conn.close()
    
    def close_all(self):
        """Close all connections in the pool"""
        with self.lock:
            # Close available connections
            while self.available_connections:
                conn = self.available_connections.popleft()
                conn.close()
            
            # Close active connections (they'll be removed when returned)
            for conn in list(self.active_connections):
                try:
                    conn.close()
                except:
                    pass
            self.active_connections.clear()


class QueryCache:
    """Simple query result cache for frequently executed queries"""
    
    def __init__(self, max_size: int = 1000, ttl_seconds: int = 300):
        self.max_size = max_size
        self.ttl_seconds = ttl_seconds
        self.cache: Dict[str, Tuple[Any, datetime]] = {}
        self.lock = threading.RLock()
        self.hits = 0
        self.misses = 0
    
    def _generate_key(self, sql: str, parameters: Tuple = ()) -> str:
        """Generate cache key for query"""
        return f"{hash(sql)}:{hash(parameters)}"
    
    def get(self, sql: str, parameters: Tuple = ()) -> Optional[Any]:
        """Get cached result for query"""
        key = self._generate_key(sql, parameters)
        
        with self.lock:
            if key in self.cache:
                result, timestamp = self.cache[key]
                
                # Check if cache entry is still valid
                if datetime.utcnow() - timestamp < timedelta(seconds=self.ttl_seconds):
                    self.hits += 1
                    return result
                else:
                    # Remove expired entry
                    del self.cache[key]
        
        self.misses += 1
        return None
    
    def put(self, sql: str, result: Any, parameters: Tuple = ()):
        """Cache query result"""
        key = self._generate_key(sql, parameters)
        
        with self.lock:
            # Remove oldest entries if cache is full
            if len(self.cache) >= self.max_size:
                # Remove entries that are more than half TTL old
                cutoff_time = datetime.utcnow() - timedelta(seconds=self.ttl_seconds // 2)
                expired_keys = [
                    k for k, (_, ts) in self.cache.items()
                    if ts < cutoff_time
                ]
                for k in expired_keys[:len(expired_keys)//2]:
                    del self.cache[k]
            
            self.cache[key] = (result, datetime.utcnow())
    
    def clear(self):
        """Clear the cache"""
        with self.lock:
            self.cache.clear()
            self.hits = 0
            self.misses = 0
    
    def get_hit_rate(self) -> float:
        """Get cache hit rate"""
        total = self.hits + self.misses
        return self.hits / total if total > 0 else 0.0


class DatabaseOptimizer:
    """
    Main database optimization system.
    
    Provides comprehensive database optimization including query analysis,
    index management, connection pooling, and performance monitoring.
    """
    
    def __init__(self, database_path: str = "jarvis.db"):
        self.database_path = database_path
        self.connection_pool = ConnectionPool(database_path)
        self.query_cache = QueryCache()
        self.query_history: deque = deque(maxlen=10000)
        self.optimization_level = OptimizationLevel.STANDARD
        self.stats_cache = {}
        self.stats_cache_time = None
        self.lock = threading.RLock()
        
        # Initialize optimization
        self._initialize_database()
        logger.info("Database optimizer initialized for %s", database_path)
    
    def _initialize_database(self):
        """Initialize database with optimizations"""
        if not HAS_SQLITE:
            logger.warning("SQLite not available - skipping database initialization")
            return
        
        try:
            with self.connection_pool.get_connection() as conn:
                # Enable Write-Ahead Logging for better concurrency
                conn.execute("PRAGMA journal_mode=WAL")
                
                # Set synchronous to NORMAL for better performance
                conn.execute("PRAGMA synchronous=NORMAL")
                
                # Increase cache size
                conn.execute("PRAGMA cache_size=-64000")  # 64MB
                
                # Store temporary tables in memory
                conn.execute("PRAGMA temp_store=MEMORY")
                
                # Enable memory-mapped I/O
                conn.execute("PRAGMA mmap_size=268435456")  # 256MB
                
                # Enable query planner optimization
                conn.execute("PRAGMA optimize")
                
                logger.info("Database initialization completed with optimizations")
                
        except Exception as e:
            logger.error("Error initializing database: %s", e)
    
    def analyze_query_performance(self, sql: str, parameters: Tuple = ()) -> Dict[str, Any]:
        """
        Analyze query performance and execution plan.
        
        Args:
            sql: SQL query to analyze
            parameters: Query parameters
            
        Returns:
            Dictionary with performance analysis results
        """
        try:
            analysis = {
                'sql': sql,
                'parameters': parameters,
                'query_type': self._detect_query_type(sql),
                'execution_plan': None,
                'execution_time': 0,
                'rows_affected': 0,
                'optimization_suggestions': []
            }
            
            with self.connection_pool.get_connection() as conn:
                # Get query execution plan
                try:
                    explain_sql = f"EXPLAIN QUERY PLAN {sql}"
                    plan_cursor = conn.execute(explain_sql, parameters)
                    execution_plan = plan_cursor.fetchall()
                    analysis['execution_plan'] = [
                        {
                            'id': row[0],
                            'parent': row[1],
                            'notused': row[2],
                            'detail': row[3]
                        } for row in execution_plan
                    ]
                except Exception as e:
                    logger.warning("Could not get execution plan: %s", e)
                
                # Time the actual query execution
                start_time = time.time()
                
                if analysis['query_type'] == QueryType.SELECT:
                    cursor = conn.execute(sql, parameters)
                    rows = cursor.fetchall()
                    analysis['rows_affected'] = len(rows)
                else:
                    cursor = conn.execute(sql, parameters)
                    analysis['rows_affected'] = cursor.rowcount
                
                analysis['execution_time'] = time.time() - start_time
                
                # Generate optimization suggestions
                analysis['optimization_suggestions'] = self._generate_optimization_suggestions(
                    sql, analysis['execution_plan']
                )
            
            # Store query metrics
            query_metrics = QueryMetrics(
                query_id=f"query_{int(time.time() * 1000)}",
                sql=sql,
                query_type=analysis['query_type'],
                execution_time=analysis['execution_time'],
                rows_affected=analysis['rows_affected'],
                rows_examined=analysis['rows_affected'],  # Approximation
                timestamp=datetime.utcnow(),
                parameters=dict(enumerate(parameters))
            )
            
            with self.lock:
                self.query_history.append(query_metrics)
            
            logger.debug(
                "Query analysis complete: %s (%.2fms)",
                analysis['query_type'].value,
                analysis['execution_time'] * 1000
            )
            
            return analysis
            
        except Exception as e:
            logger.error("Error analyzing query performance: %s", e)
            return {
                'sql': sql,
                'error': str(e),
                'execution_time': 0,
                'optimization_suggestions': []
            }
    
    def _detect_query_type(self, sql: str) -> QueryType:
        """Detect the type of SQL query"""
        sql_upper = sql.strip().upper()
        
        if sql_upper.startswith('SELECT'):
            return QueryType.SELECT
        elif sql_upper.startswith('INSERT'):
            return QueryType.INSERT
        elif sql_upper.startswith('UPDATE'):
            return QueryType.UPDATE
        elif sql_upper.startswith('DELETE'):
            return QueryType.DELETE
        elif sql_upper.startswith('CREATE'):
            return QueryType.CREATE
        elif sql_upper.startswith('DROP'):
            return QueryType.DROP
        elif sql_upper.startswith('ALTER'):
            return QueryType.ALTER
        elif sql_upper.startswith('PRAGMA'):
            return QueryType.PRAGMA
        else:
            return QueryType.UNKNOWN
    
    def _generate_optimization_suggestions(self, sql: str, execution_plan: List[Dict]) -> List[str]:
        """Generate optimization suggestions based on query and execution plan"""
        suggestions = []
        
        if not execution_plan:
            return suggestions
        
        # Check for table scans
        for step in execution_plan:
            detail = step.get('detail', '').upper()
            if 'SCAN TABLE' in detail:
                table_name = detail.split('SCAN TABLE')[1].strip().split()[0]
                suggestions.append(f"Consider adding an index on table '{table_name}' to avoid table scan")
        
        # Check for missing indexes on WHERE clauses
        sql_upper = sql.upper()
        if 'WHERE' in sql_upper:
            # Simple heuristic: suggest indexes for WHERE conditions
            where_clause = sql_upper.split('WHERE')[1].split('ORDER BY')[0].split('GROUP BY')[0]
            if '=' in where_clause:
                suggestions.append("Consider adding indexes on columns used in WHERE conditions")
        
        # Check for ORDER BY without index
        if 'ORDER BY' in sql_upper:
            suggestions.append("Consider adding an index on ORDER BY columns for better sorting performance")
        
        # Check for complex joins
        if 'JOIN' in sql_upper:
            join_count = sql_upper.count('JOIN')
            if join_count > 2:
                suggestions.append("Complex joins detected - consider query restructuring or adding composite indexes")
        
        return suggestions
    
    def get_index_recommendations(self) -> List[IndexRecommendation]:
        """
        Generate index recommendations based on query history.
        
        Returns:
            List of index recommendations
        """
        recommendations = []
        
        try:
            with self.connection_pool.get_connection() as conn:
                # Get all tables
                cursor = conn.execute("SELECT name FROM sqlite_master WHERE type='table'")
                tables = [row[0] for row in cursor.fetchall()]
                
                # Get existing indexes
                existing_indexes = set()
                for table in tables:
                    cursor = conn.execute(f"PRAGMA index_list('{table}')")
                    for index_info in cursor.fetchall():
                        index_name = index_info[1]
                        existing_indexes.add(index_name)
                
                # Analyze query patterns to suggest indexes
                query_patterns = self._analyze_query_patterns()
                
                for pattern in query_patterns:
                    table_name = pattern.get('table')
                    columns = pattern.get('columns', [])
                    frequency = pattern.get('frequency', 0)
                    
                    if table_name and columns and frequency > 5:  # Minimum frequency threshold
                        index_name = f"idx_{table_name}_{'_'.join(columns)}"
                        
                        if index_name not in existing_indexes:
                            recommendation = IndexRecommendation(
                                table_name=table_name,
                                columns=columns,
                                index_type="BTREE",
                                estimated_benefit=min(frequency / 10.0, 5.0),  # Scale benefit
                                reason=f"Frequently queried columns (used {frequency} times)",
                                sql_statement=f"CREATE INDEX {index_name} ON {table_name} ({', '.join(columns)})",
                                priority=1 if frequency > 20 else 2 if frequency > 10 else 3
                            )
                            recommendations.append(recommendation)
            
            # Sort recommendations by priority and estimated benefit
            recommendations.sort(key=lambda x: (x.priority, -x.estimated_benefit))
            
            logger.info("Generated %d index recommendations", len(recommendations))
            return recommendations
            
        except Exception as e:
            logger.error("Error generating index recommendations: %s", e)
            return []
    
    def _analyze_query_patterns(self) -> List[Dict[str, Any]]:
        """Analyze query history for common patterns"""
        patterns = defaultdict(int)
        
        with self.lock:
            for query_metric in self.query_history:
                if query_metric.query_type == QueryType.SELECT:
                    # Simple pattern extraction (could be more sophisticated)
                    sql = query_metric.sql.upper()
                    
                    # Extract table names
                    if 'FROM' in sql:
                        from_part = sql.split('FROM')[1].split('WHERE')[0].split('ORDER BY')[0]
                        table_name = from_part.strip().split()[0]
                        
                        # Extract WHERE columns
                        if 'WHERE' in sql:
                            where_part = sql.split('WHERE')[1].split('ORDER BY')[0].split('GROUP BY')[0]
                            # Simple column extraction (basic implementation)
                            columns = []
                            for token in where_part.split():
                                if '=' in token or 'LIKE' in token or 'IN' in token:
                                    col = token.split('=')[0].split('LIKE')[0].split('IN')[0].strip()
                                    if col.isalpha():
                                        columns.append(col.lower())
                            
                            if columns:
                                pattern_key = f"{table_name}:{':'.join(sorted(columns))}"
                                patterns[pattern_key] += 1
        
        # Convert to list of dictionaries
        result = []
        for pattern_key, frequency in patterns.items():
            parts = pattern_key.split(':')
            if len(parts) >= 2:
                result.append({
                    'table': parts[0],
                    'columns': parts[1].split(':') if len(parts) > 1 else [],
                    'frequency': frequency
                })
        
        return result
    
    def get_database_statistics(self, force_refresh: bool = False) -> DatabaseStats:
        """
        Get comprehensive database statistics.
        
        Args:
            force_refresh: Force refresh of cached statistics
            
        Returns:
            Database statistics object
        """
        # Check cache first
        if not force_refresh and self.stats_cache_time:
            if datetime.utcnow() - self.stats_cache_time < timedelta(minutes=5):
                return DatabaseStats(**self.stats_cache)
        
        try:
            with self.connection_pool.get_connection() as conn:
                stats_data = {
                    'database_path': self.database_path,
                    'total_size_bytes': 0,
                    'table_count': 0,
                    'index_count': 0,
                    'page_size': 4096,
                    'page_count': 0,
                    'free_pages': 0,
                    'fragmentation_percent': 0.0,
                    'last_vacuum': None,
                    'last_analyze': None,
                    'connections_active': len(self.connection_pool.active_connections),
                    'query_cache_hit_rate': self.query_cache.get_hit_rate()
                }
                
                # Get file size
                if os.path.exists(self.database_path):
                    stats_data['total_size_bytes'] = os.path.getsize(self.database_path)
                
                # Get page information
                cursor = conn.execute("PRAGMA page_size")
                stats_data['page_size'] = cursor.fetchone()[0]
                
                cursor = conn.execute("PRAGMA page_count")
                stats_data['page_count'] = cursor.fetchone()[0]
                
                cursor = conn.execute("PRAGMA freelist_count")
                stats_data['free_pages'] = cursor.fetchone()[0]
                
                # Calculate fragmentation
                if stats_data['page_count'] > 0:
                    stats_data['fragmentation_percent'] = (
                        stats_data['free_pages'] / stats_data['page_count']
                    ) * 100
                
                # Count tables and indexes
                cursor = conn.execute("SELECT COUNT(*) FROM sqlite_master WHERE type='table'")
                stats_data['table_count'] = cursor.fetchone()[0]
                
                cursor = conn.execute("SELECT COUNT(*) FROM sqlite_master WHERE type='index'")
                stats_data['index_count'] = cursor.fetchone()[0]
                
                # Check for recent maintenance operations (SQLite doesn't track this directly)
                # We'll use file modification time as a proxy
                if os.path.exists(self.database_path):
                    mod_time = datetime.fromtimestamp(os.path.getmtime(self.database_path))
                    # If modified recently, assume maintenance was performed
                    if datetime.now() - mod_time < timedelta(hours=24):
                        stats_data['last_vacuum'] = mod_time
                        stats_data['last_analyze'] = mod_time
                
                # Cache the results
                self.stats_cache = stats_data
                self.stats_cache_time = datetime.utcnow()
                
                return DatabaseStats(**stats_data)
                
        except Exception as e:
            logger.error("Error getting database statistics: %s", e)
            # Return default stats on error
            return DatabaseStats(
                database_path=self.database_path,
                total_size_bytes=0,
                table_count=0,
                index_count=0,
                page_size=4096,
                page_count=0,
                free_pages=0,
                fragmentation_percent=0.0,
                last_vacuum=None,
                last_analyze=None,
                connections_active=0,
                query_cache_hit_rate=0.0
            )
    
    def optimize_database(self, level: OptimizationLevel = OptimizationLevel.STANDARD) -> Dict[str, Any]:
        """
        Perform database optimization operations.
        
        Args:
            level: Optimization level to apply
            
        Returns:
            Dictionary with optimization results
        """
        self.optimization_level = level
        results = {
            'optimization_level': level.value,
            'operations_performed': [],
            'before_stats': self.get_database_statistics().to_dict(),
            'after_stats': None,
            'improvements': {},
            'errors': []
        }
        
        try:
            with self.connection_pool.get_connection() as conn:
                # VACUUM operation to defragment and compact database
                if level in [OptimizationLevel.STANDARD, OptimizationLevel.AGGRESSIVE]:
                    try:
                        logger.info("Performing VACUUM operation...")
                        conn.execute("VACUUM")
                        results['operations_performed'].append('VACUUM')
                        logger.info("VACUUM operation completed")
                    except Exception as e:
                        error_msg = f"VACUUM failed: {e}"
                        results['errors'].append(error_msg)
                        logger.error(error_msg)
                
                # ANALYZE operation to update query planner statistics
                try:
                    logger.info("Performing ANALYZE operation...")
                    conn.execute("ANALYZE")
                    results['operations_performed'].append('ANALYZE')
                    logger.info("ANALYZE operation completed")
                except Exception as e:
                    error_msg = f"ANALYZE failed: {e}"
                    results['errors'].append(error_msg)
                    logger.error(error_msg)
                
                # Optimize pragma settings based on level
                if level == OptimizationLevel.AGGRESSIVE:
                    try:
                        # More aggressive cache size
                        conn.execute("PRAGMA cache_size=-128000")  # 128MB
                        results['operations_performed'].append('Increased cache size')
                        
                        # Enable more aggressive synchronous mode
                        conn.execute("PRAGMA synchronous=NORMAL")
                        results['operations_performed'].append('Optimized synchronous mode')
                        
                    except Exception as e:
                        error_msg = f"Aggressive optimization failed: {e}"
                        results['errors'].append(error_msg)
                        logger.error(error_msg)
                
                # Run query planner optimization
                try:
                    conn.execute("PRAGMA optimize")
                    results['operations_performed'].append('Query planner optimization')
                except Exception as e:
                    error_msg = f"Query planner optimization failed: {e}"
                    results['errors'].append(error_msg)
                    logger.error(error_msg)
            
            # Clear query cache to see fresh performance
            self.query_cache.clear()
            
            # Get after-optimization statistics
            results['after_stats'] = self.get_database_statistics(force_refresh=True).to_dict()
            
            # Calculate improvements
            before = results['before_stats']
            after = results['after_stats']
            
            results['improvements'] = {
                'size_reduction_bytes': before['total_size_bytes'] - after['total_size_bytes'],
                'fragmentation_reduction': before['fragmentation_percent'] - after['fragmentation_percent'],
                'operations_count': len(results['operations_performed']),
                'errors_count': len(results['errors'])
            }
            
            logger.info(
                "Database optimization completed: %d operations, %d errors",
                len(results['operations_performed']),
                len(results['errors'])
            )
            
            return results
            
        except Exception as e:
            error_msg = f"Database optimization failed: {e}"
            results['errors'].append(error_msg)
            logger.error(error_msg)
            return results
    
    def execute_with_monitoring(self, sql: str, parameters: Tuple = ()) -> Any:
        """
        Execute SQL with performance monitoring and caching.
        
        Args:
            sql: SQL query to execute
            parameters: Query parameters
            
        Returns:
            Query results
        """
        # Check cache first for SELECT queries
        query_type = self._detect_query_type(sql)
        if query_type == QueryType.SELECT:
            cached_result = self.query_cache.get(sql, parameters)
            if cached_result is not None:
                return cached_result
        
        try:
            with self.connection_pool.get_connection() as conn:
                start_time = time.time()
                
                cursor = conn.execute(sql, parameters)
                
                if query_type == QueryType.SELECT:
                    result = cursor.fetchall()
                    # Cache SELECT results
                    self.query_cache.put(sql, result, parameters)
                else:
                    result = cursor.rowcount
                
                execution_time = time.time() - start_time
                
                # Record metrics
                query_metrics = QueryMetrics(
                    query_id=f"query_{int(time.time() * 1000)}",
                    sql=sql,
                    query_type=query_type,
                    execution_time=execution_time,
                    rows_affected=len(result) if isinstance(result, list) else result,
                    rows_examined=len(result) if isinstance(result, list) else result,
                    timestamp=datetime.utcnow(),
                    parameters=dict(enumerate(parameters))
                )
                
                with self.lock:
                    self.query_history.append(query_metrics)
                
                return result
                
        except Exception as e:
            logger.error("Error executing monitored query: %s", e)
            raise
    
    def get_performance_report(self, hours: int = 24) -> Dict[str, Any]:
        """
        Generate comprehensive performance report.
        
        Args:
            hours: Number of hours to include in the report
            
        Returns:
            Performance report dictionary
        """
        since = datetime.utcnow() - timedelta(hours=hours)
        
        with self.lock:
            # Filter queries within time range
            recent_queries = [
                q for q in self.query_history
                if q.timestamp >= since
            ]
        
        if not recent_queries:
            return {
                'period_hours': hours,
                'total_queries': 0,
                'message': 'No queries in the specified time range'
            }
        
        # Calculate statistics
        execution_times = [q.execution_time for q in recent_queries]
        query_types = defaultdict(int)
        slow_queries = []
        
        for query in recent_queries:
            query_types[query.query_type.value] += 1
            
            # Identify slow queries (> 100ms)
            if query.execution_time > 0.1:
                slow_queries.append(query)
        
        # Sort slow queries by execution time
        slow_queries.sort(key=lambda x: x.execution_time, reverse=True)
        
        report = {
            'period_hours': hours,
            'period_start': since.isoformat(),
            'period_end': datetime.utcnow().isoformat(),
            'total_queries': len(recent_queries),
            'query_types': dict(query_types),
            'performance_metrics': {
                'avg_execution_time': statistics.mean(execution_times),
                'median_execution_time': statistics.median(execution_times),
                'min_execution_time': min(execution_times),
                'max_execution_time': max(execution_times),
                'slow_query_count': len(slow_queries),
                'slow_query_threshold': 0.1
            },
            'top_slow_queries': [
                {
                    'sql': q.sql,
                    'execution_time': q.execution_time,
                    'timestamp': q.timestamp.isoformat(),
                    'query_type': q.query_type.value
                }
                for q in slow_queries[:10]
            ],
            'cache_performance': {
                'hit_rate': self.query_cache.get_hit_rate(),
                'total_hits': self.query_cache.hits,
                'total_misses': self.query_cache.misses,
                'cache_size': len(self.query_cache.cache)
            },
            'database_stats': self.get_database_statistics().to_dict(),
            'index_recommendations': [r.to_dict() for r in self.get_index_recommendations()[:5]]
        }
        
        return report
    
    def close(self):
        """Close the database optimizer and clean up resources"""
        try:
            self.connection_pool.close_all()
            self.query_cache.clear()
            logger.info("Database optimizer closed")
        except Exception as e:
            logger.error("Error closing database optimizer: %s", e)


# Global optimizer instance
_db_optimizer = None

def get_database_optimizer(database_path: str = "jarvis.db") -> DatabaseOptimizer:
    """Get or create the global database optimizer instance"""
    global _db_optimizer
    if _db_optimizer is None:
        _db_optimizer = DatabaseOptimizer(database_path)
    return _db_optimizer


def main():
    """Command line interface for database optimization"""
    import argparse
    
    parser = argparse.ArgumentParser(description="JARVIS-MK42 Database Optimization")
    parser.add_argument('--database', default='jarvis.db', help='Database file path')
    parser.add_argument('--optimize', action='store_true', help='Perform database optimization')
    parser.add_argument('--level', choices=['basic', 'standard', 'aggressive'], 
                       default='standard', help='Optimization level')
    parser.add_argument('--stats', action='store_true', help='Show database statistics')
    parser.add_argument('--report', type=int, default=24, help='Generate performance report for N hours')
    parser.add_argument('--indexes', action='store_true', help='Show index recommendations')
    parser.add_argument('--analyze', help='Analyze specific SQL query')
    
    args = parser.parse_args()
    
    optimizer = get_database_optimizer(args.database)
    
    try:
        if args.optimize:
            level = OptimizationLevel(args.level)
            print(f"Optimizing database with level: {level.value}")
            result = optimizer.optimize_database(level)
            print(json.dumps(result, indent=2))
        
        elif args.stats:
            stats = optimizer.get_database_statistics(force_refresh=True)
            print(json.dumps(stats.to_dict(), indent=2))
        
        elif args.report:
            report = optimizer.get_performance_report(args.report)
            print(json.dumps(report, indent=2))
        
        elif args.indexes:
            recommendations = optimizer.get_index_recommendations()
            print(f"Index Recommendations ({len(recommendations)}):")
            for rec in recommendations:
                print(f"  Priority {rec.priority}: {rec.sql_statement}")
                print(f"    Reason: {rec.reason}")
                print(f"    Benefit: {rec.estimated_benefit:.2f}")
                print()
        
        elif args.analyze:
            analysis = optimizer.analyze_query_performance(args.analyze)
            print(json.dumps(analysis, indent=2, default=str))
        
        else:
            print("JARVIS-MK42 Database Optimization System")
            print("Use --help for available options")
    
    finally:
        optimizer.close()


if __name__ == "__main__":
    main()
