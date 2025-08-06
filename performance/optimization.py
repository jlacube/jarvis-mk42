#!/usr/bin/env python3
"""
JARVIS-MK42 Performance Optimization Engine
==========================================

This module provides comprehensive performance optimization capabilities including:
- Request/response optimization and intelligent caching
- Memory management and garbage collection optimization
- CPU usage optimization for AI model inference
- Query optimization and database performance tuning
- API endpoint performance monitoring and tuning
- Resource usage optimization and bottleneck detection
"""

import os
import sys
import gc
import time
import json
import threading
import asyncio
import psutil
import functools
import hashlib
from datetime import datetime, timedelta
from typing import Dict, List, Optional, Any, Tuple, Callable, Union
from dataclasses import dataclass, field
from enum import Enum
from pathlib import Path
from collections import defaultdict, OrderedDict
from concurrent.futures import ThreadPoolExecutor, as_completed
import weakref
import pickle
import gzip
from contextlib import contextmanager

# Add project root to path
current_dir = os.path.dirname(os.path.abspath(__file__))
project_root = os.path.dirname(current_dir)
if project_root not in sys.path:
    sys.path.insert(0, project_root)

from utils.logging_config import get_logger

logger = get_logger(__name__)


class CacheStrategy(Enum):
    """Cache strategy types"""
    LRU = "lru"          # Least Recently Used
    LFU = "lfu"          # Least Frequently Used  
    TTL = "ttl"          # Time To Live
    FIFO = "fifo"        # First In, First Out
    ADAPTIVE = "adaptive" # Adaptive based on usage patterns


class OptimizationLevel(Enum):
    """Performance optimization levels"""
    MINIMAL = "minimal"       # Basic optimizations only
    STANDARD = "standard"     # Standard production optimizations
    AGGRESSIVE = "aggressive" # Maximum performance optimizations
    ADAPTIVE = "adaptive"     # AI-driven adaptive optimization


@dataclass
class CacheEntry:
    """Cache entry with metadata"""
    key: str
    value: Any
    created_at: datetime
    last_accessed: datetime
    access_count: int
    size_bytes: int
    ttl_seconds: Optional[int] = None
    compression_enabled: bool = False
    
    def is_expired(self) -> bool:
        """Check if cache entry has expired"""
        if self.ttl_seconds is None:
            return False
        return datetime.now() - self.created_at > timedelta(seconds=self.ttl_seconds)
    
    def get_age_seconds(self) -> float:
        """Get age of cache entry in seconds"""
        return (datetime.now() - self.created_at).total_seconds()
    
    def update_access(self):
        """Update access statistics"""
        self.last_accessed = datetime.now()
        self.access_count += 1


@dataclass
class PerformanceMetrics:
    """Performance metrics tracking"""
    request_count: int = 0
    total_response_time: float = 0.0
    cache_hits: int = 0
    cache_misses: int = 0
    memory_usage_mb: float = 0.0
    cpu_usage_percent: float = 0.0
    avg_response_time_ms: float = 0.0
    cache_hit_rate: float = 0.0
    throughput_rps: float = 0.0
    optimization_score: float = 0.0
    
    def calculate_derived_metrics(self):
        """Calculate derived performance metrics"""
        if self.request_count > 0:
            self.avg_response_time_ms = (self.total_response_time / self.request_count) * 1000
            self.throughput_rps = self.request_count / max(self.total_response_time, 0.001)
        
        total_cache_operations = self.cache_hits + self.cache_misses
        if total_cache_operations > 0:
            self.cache_hit_rate = self.cache_hits / total_cache_operations
        
        # Calculate optimization score (0-100)
        score = 0
        if self.avg_response_time_ms < 100:
            score += 30
        elif self.avg_response_time_ms < 500:
            score += 20
        elif self.avg_response_time_ms < 1000:
            score += 10
        
        if self.cache_hit_rate > 0.8:
            score += 25
        elif self.cache_hit_rate > 0.6:
            score += 15
        elif self.cache_hit_rate > 0.4:
            score += 5
        
        if self.cpu_usage_percent < 20:
            score += 20
        elif self.cpu_usage_percent < 50:
            score += 15
        elif self.cpu_usage_percent < 80:
            score += 10
        
        if self.memory_usage_mb < 100:
            score += 15
        elif self.memory_usage_mb < 500:
            score += 10
        elif self.memory_usage_mb < 1000:
            score += 5
        
        if self.throughput_rps > 100:
            score += 10
        elif self.throughput_rps > 50:
            score += 5
        
        self.optimization_score = min(100, score)


class IntelligentCache:
    """Intelligent caching system with multiple strategies"""
    
    def __init__(self, 
                 max_size: int = 1000,
                 default_ttl: Optional[int] = None,
                 strategy: CacheStrategy = CacheStrategy.ADAPTIVE,
                 compression_threshold: int = 1024):
        self.max_size = max_size
        self.default_ttl = default_ttl
        self.strategy = strategy
        self.compression_threshold = compression_threshold
        self.cache: OrderedDict[str, CacheEntry] = OrderedDict()
        self._lock = threading.RLock()
        self._stats = {
            'hits': 0,
            'misses': 0,
            'evictions': 0,
            'size_bytes': 0
        }
    
    def _calculate_entry_size(self, value: Any) -> int:
        """Calculate approximate size of cache entry"""
        try:
            return len(pickle.dumps(value))
        except:
            return sys.getsizeof(value)
    
    def _compress_value(self, value: Any) -> bytes:
        """Compress large values"""
        serialized = pickle.dumps(value)
        if len(serialized) > self.compression_threshold:
            return gzip.compress(serialized)
        return serialized
    
    def _decompress_value(self, data: bytes, compressed: bool) -> Any:
        """Decompress cached values"""
        if compressed:
            data = gzip.decompress(data)
        return pickle.loads(data)
    
    def _should_evict(self) -> bool:
        """Determine if eviction is needed"""
        return len(self.cache) >= self.max_size
    
    def _select_eviction_candidate(self) -> Optional[str]:
        """Select cache entry for eviction based on strategy"""
        if not self.cache:
            return None
        
        if self.strategy == CacheStrategy.LRU:
            # Least recently used
            return min(self.cache.keys(), key=lambda k: self.cache[k].last_accessed)
        
        elif self.strategy == CacheStrategy.LFU:
            # Least frequently used
            return min(self.cache.keys(), key=lambda k: self.cache[k].access_count)
        
        elif self.strategy == CacheStrategy.TTL:
            # Expired entries first, then oldest
            expired = [k for k, v in self.cache.items() if v.is_expired()]
            if expired:
                return expired[0]
            return min(self.cache.keys(), key=lambda k: self.cache[k].created_at)
        
        elif self.strategy == CacheStrategy.FIFO:
            # First in, first out
            return next(iter(self.cache))
        
        else:  # ADAPTIVE
            # Intelligent selection based on access patterns and age
            now = datetime.now()
            candidates = []
            
            for key, entry in self.cache.items():
                age = (now - entry.created_at).total_seconds()
                recency = (now - entry.last_accessed).total_seconds()
                frequency = entry.access_count
                
                # Score: lower is more likely to be evicted
                score = (age * 0.3) + (recency * 0.4) - (frequency * 0.3)
                candidates.append((key, score))
            
            # Return candidate with highest eviction score
            return max(candidates, key=lambda x: x[1])[0]
    
    def get(self, key: str) -> Optional[Any]:
        """Get value from cache"""
        with self._lock:
            entry = self.cache.get(key)
            if entry is None:
                self._stats['misses'] += 1
                return None
            
            if entry.is_expired():
                del self.cache[key]
                self._stats['size_bytes'] -= entry.size_bytes
                self._stats['misses'] += 1
                return None
            
            entry.update_access()
            # Move to end for LRU
            self.cache.move_to_end(key)
            self._stats['hits'] += 1
            
            if entry.compression_enabled:
                return self._decompress_value(entry.value, True)
            return entry.value
    
    def put(self, key: str, value: Any, ttl: Optional[int] = None) -> bool:
        """Put value in cache"""
        with self._lock:
            # Calculate size
            size_bytes = self._calculate_entry_size(value)
            
            # Handle compression
            compressed = size_bytes > self.compression_threshold
            if compressed:
                cached_value = self._compress_value(value)
            else:
                cached_value = value
            
            # Evict if necessary
            while self._should_evict():
                evict_key = self._select_eviction_candidate()
                if evict_key:
                    evicted = self.cache.pop(evict_key)
                    self._stats['size_bytes'] -= evicted.size_bytes
                    self._stats['evictions'] += 1
                else:
                    break
            
            # Create cache entry
            entry = CacheEntry(
                key=key,
                value=cached_value,
                created_at=datetime.now(),
                last_accessed=datetime.now(),
                access_count=1,
                size_bytes=size_bytes,
                ttl_seconds=ttl or self.default_ttl,
                compression_enabled=compressed
            )
            
            self.cache[key] = entry
            self._stats['size_bytes'] += size_bytes
            return True
    
    def clear(self):
        """Clear all cache entries"""
        with self._lock:
            self.cache.clear()
            self._stats = {'hits': 0, 'misses': 0, 'evictions': 0, 'size_bytes': 0}
    
    def get_stats(self) -> Dict[str, Any]:
        """Get cache statistics"""
        with self._lock:
            total_requests = self._stats['hits'] + self._stats['misses']
            hit_rate = self._stats['hits'] / max(total_requests, 1)
            
            return {
                'size': len(self.cache),
                'max_size': self.max_size,
                'hits': self._stats['hits'],
                'misses': self._stats['misses'],
                'hit_rate': hit_rate,
                'evictions': self._stats['evictions'],
                'size_bytes': self._stats['size_bytes'],
                'size_mb': round(self._stats['size_bytes'] / (1024 * 1024), 2),
                'strategy': self.strategy.value
            }


class MemoryOptimizer:
    """Memory optimization and garbage collection manager"""
    
    def __init__(self):
        self.gc_threshold = (700, 10, 10)  # More aggressive than default
        self.memory_limit_mb = 1024  # 1GB default limit
        self.cleanup_interval = 300  # 5 minutes
        self._weak_refs: List[weakref.ref] = []
        self._cleanup_callbacks: List[Callable] = []
        self._running = False
        self._thread: Optional[threading.Thread] = None
    
    def configure_gc(self, 
                    threshold: Tuple[int, int, int] = None,
                    enable_stats: bool = True):
        """Configure garbage collection settings"""
        if threshold:
            gc.set_threshold(*threshold)
            self.gc_threshold = threshold
        
        if enable_stats:
            gc.set_debug(gc.DEBUG_STATS)
        
        # Force immediate collection
        collected = gc.collect()
        logger.info(f"Memory optimizer configured. Collected {collected} objects.")
    
    def add_cleanup_callback(self, callback: Callable):
        """Add cleanup callback for custom resource management"""
        self._cleanup_callbacks.append(callback)
    
    def register_weak_ref(self, obj: Any, callback: Optional[Callable] = None):
        """Register object for weak reference tracking"""
        weak_ref = weakref.ref(obj, callback)
        self._weak_refs.append(weak_ref)
        return weak_ref
    
    def force_cleanup(self) -> Dict[str, Any]:
        """Force immediate memory cleanup"""
        start_memory = self.get_memory_usage()
        
        # Run custom cleanup callbacks
        for callback in self._cleanup_callbacks:
            try:
                callback()
            except Exception as e:
                logger.warning(f"Cleanup callback failed: {e}")
        
        # Clean up dead weak references
        self._weak_refs = [ref for ref in self._weak_refs if ref() is not None]
        
        # Force garbage collection
        collected = gc.collect()
        
        # Clear unreachable cycles
        gc.collect()
        gc.collect()  # Run twice for better cleanup
        
        end_memory = self.get_memory_usage()
        freed_mb = start_memory - end_memory
        
        return {
            'objects_collected': collected,
            'memory_before_mb': start_memory,
            'memory_after_mb': end_memory,
            'memory_freed_mb': freed_mb,
            'weak_refs_active': len([ref for ref in self._weak_refs if ref() is not None])
        }
    
    def get_memory_usage(self) -> float:
        """Get current memory usage in MB"""
        process = psutil.Process()
        return process.memory_info().rss / (1024 * 1024)
    
    def check_memory_pressure(self) -> bool:
        """Check if system is under memory pressure"""
        current_mb = self.get_memory_usage()
        return current_mb > self.memory_limit_mb
    
    def start_monitoring(self):
        """Start memory monitoring thread"""
        if self._running:
            return
        
        self._running = True
        self._thread = threading.Thread(target=self._monitoring_loop, daemon=True)
        self._thread.start()
        logger.info("Memory optimizer monitoring started")
    
    def stop_monitoring(self):
        """Stop memory monitoring"""
        self._running = False
        if self._thread:
            self._thread.join()
        logger.info("Memory optimizer monitoring stopped")
    
    def _monitoring_loop(self):
        """Memory monitoring loop"""
        while self._running:
            try:
                if self.check_memory_pressure():
                    logger.warning("Memory pressure detected, performing cleanup")
                    result = self.force_cleanup()
                    logger.info(f"Memory cleanup completed: freed {result['memory_freed_mb']:.2f} MB")
                
                time.sleep(self.cleanup_interval)
                
            except Exception as e:
                logger.error(f"Error in memory monitoring: {e}")
                time.sleep(60)  # Wait a minute before retrying


class RequestOptimizer:
    """Request/response optimization with intelligent caching"""
    
    def __init__(self, cache_size: int = 10000):
        self.request_cache = IntelligentCache(
            max_size=cache_size,
            default_ttl=3600,  # 1 hour default
            strategy=CacheStrategy.ADAPTIVE
        )
        self.response_compressor = self._setup_compression()
        self.metrics = PerformanceMetrics()
        self._lock = threading.Lock()
    
    def _setup_compression(self) -> Dict[str, Any]:
        """Setup response compression"""
        return {
            'enabled': True,
            'threshold_bytes': 1024,
            'level': 6  # Good balance of speed/compression
        }
    
    def _generate_cache_key(self, 
                          request_data: Any, 
                          user_context: Dict[str, Any] = None) -> str:
        """Generate cache key for request"""
        key_data = {
            'request': str(request_data),
            'user': user_context.get('user_name', 'anonymous') if user_context else 'anonymous'
        }
        
        key_string = json.dumps(key_data, sort_keys=True)
        return hashlib.md5(key_string.encode()).hexdigest()
    
    def optimize_request(self, func: Callable) -> Callable:
        """Decorator for request optimization"""
        @functools.wraps(func)
        async def async_wrapper(*args, **kwargs):
            start_time = time.time()
            
            # Generate cache key
            cache_key = self._generate_cache_key((args, kwargs))
            
            # Try cache first
            cached_result = self.request_cache.get(cache_key)
            if cached_result is not None:
                with self._lock:
                    self.metrics.cache_hits += 1
                    self.metrics.request_count += 1
                    response_time = time.time() - start_time
                    self.metrics.total_response_time += response_time
                
                return cached_result
            
            # Execute function
            try:
                if asyncio.iscoroutinefunction(func):
                    result = await func(*args, **kwargs)
                else:
                    result = func(*args, **kwargs)
                
                # Cache successful result
                self.request_cache.put(cache_key, result)
                
                with self._lock:
                    self.metrics.cache_misses += 1
                    
            except Exception as e:
                # Don't cache errors, but still track metrics
                with self._lock:
                    self.metrics.cache_misses += 1
                raise
            
            finally:
                with self._lock:
                    self.metrics.request_count += 1
                    response_time = time.time() - start_time
                    self.metrics.total_response_time += response_time
            
            return result
        
        @functools.wraps(func)
        def sync_wrapper(*args, **kwargs):
            start_time = time.time()
            
            # Generate cache key
            cache_key = self._generate_cache_key((args, kwargs))
            
            # Try cache first
            cached_result = self.request_cache.get(cache_key)
            if cached_result is not None:
                with self._lock:
                    self.metrics.cache_hits += 1
                    self.metrics.request_count += 1
                    response_time = time.time() - start_time
                    self.metrics.total_response_time += response_time
                
                return cached_result
            
            # Execute function
            try:
                result = func(*args, **kwargs)
                
                # Cache successful result
                self.request_cache.put(cache_key, result)
                
                with self._lock:
                    self.metrics.cache_misses += 1
                    
            except Exception as e:
                with self._lock:
                    self.metrics.cache_misses += 1
                raise
            
            finally:
                with self._lock:
                    self.metrics.request_count += 1
                    response_time = time.time() - start_time
                    self.metrics.total_response_time += response_time
            
            return result
        
        return async_wrapper if asyncio.iscoroutinefunction(func) else sync_wrapper
    
    def get_performance_metrics(self) -> Dict[str, Any]:
        """Get current performance metrics"""
        with self._lock:
            self.metrics.memory_usage_mb = psutil.Process().memory_info().rss / (1024 * 1024)
            self.metrics.cpu_usage_percent = psutil.cpu_percent(interval=0.1)
            self.metrics.calculate_derived_metrics()
            
            return {
                'requests': {
                    'total': self.metrics.request_count,
                    'avg_response_time_ms': self.metrics.avg_response_time_ms,
                    'throughput_rps': self.metrics.throughput_rps
                },
                'cache': {
                    'hits': self.metrics.cache_hits,
                    'misses': self.metrics.cache_misses,
                    'hit_rate': self.metrics.cache_hit_rate,
                    **self.request_cache.get_stats()
                },
                'system': {
                    'memory_usage_mb': self.metrics.memory_usage_mb,
                    'cpu_usage_percent': self.metrics.cpu_usage_percent
                },
                'performance': {
                    'optimization_score': self.metrics.optimization_score
                }
            }


class PerformanceOptimizer:
    """Main performance optimization engine"""
    
    def __init__(self, 
                 optimization_level: OptimizationLevel = OptimizationLevel.STANDARD,
                 cache_size: int = 10000,
                 memory_limit_mb: int = 1024):
        self.optimization_level = optimization_level
        self.request_optimizer = RequestOptimizer(cache_size)
        self.memory_optimizer = MemoryOptimizer()
        self.memory_optimizer.memory_limit_mb = memory_limit_mb
        
        # Configuration based on optimization level
        self._configure_for_level()
        
        # Start monitoring
        self.memory_optimizer.start_monitoring()
        
        logger.info(f"Performance optimizer initialized with {optimization_level.value} level")
    
    def _configure_for_level(self):
        """Configure optimizations based on level"""
        if self.optimization_level == OptimizationLevel.MINIMAL:
            # Basic settings
            self.memory_optimizer.cleanup_interval = 600  # 10 minutes
            self.request_optimizer.request_cache.default_ttl = 1800  # 30 minutes
        
        elif self.optimization_level == OptimizationLevel.STANDARD:
            # Production settings (current defaults)
            pass
        
        elif self.optimization_level == OptimizationLevel.AGGRESSIVE:
            # Maximum performance
            self.memory_optimizer.configure_gc((500, 5, 5))
            self.memory_optimizer.cleanup_interval = 120  # 2 minutes
            self.request_optimizer.request_cache.max_size = 50000
            self.request_optimizer.request_cache.strategy = CacheStrategy.LFU
        
        else:  # ADAPTIVE
            # AI-driven adaptive (placeholder for future ML-based optimization)
            self.memory_optimizer.configure_gc((600, 8, 8))
            self.request_optimizer.request_cache.strategy = CacheStrategy.ADAPTIVE
    
    def optimize_function(self, func: Callable) -> Callable:
        """Decorator to optimize any function"""
        return self.request_optimizer.optimize_request(func)
    
    @contextmanager
    def performance_monitoring(self, operation_name: str = "operation"):
        """Context manager for performance monitoring"""
        start_time = time.time()
        start_memory = self.memory_optimizer.get_memory_usage()
        
        try:
            yield
        finally:
            end_time = time.time()
            end_memory = self.memory_optimizer.get_memory_usage()
            
            duration = end_time - start_time
            memory_delta = end_memory - start_memory
            
            logger.info(f"Performance: {operation_name} took {duration:.3f}s, "
                       f"memory delta: {memory_delta:.2f}MB")
    
    def get_comprehensive_metrics(self) -> Dict[str, Any]:
        """Get comprehensive performance metrics"""
        request_metrics = self.request_optimizer.get_performance_metrics()
        memory_usage = self.memory_optimizer.get_memory_usage()
        memory_pressure = self.memory_optimizer.check_memory_pressure()
        
        return {
            'timestamp': datetime.now().isoformat(),
            'optimization_level': self.optimization_level.value,
            'performance_score': request_metrics['performance']['optimization_score'],
            'requests': request_metrics['requests'],
            'cache': request_metrics['cache'],
            'system': {
                **request_metrics['system'],
                'memory_pressure': memory_pressure,
                'gc_stats': {
                    'collections': gc.get_stats(),
                    'threshold': gc.get_threshold()
                }
            }
        }
    
    def force_optimization(self) -> Dict[str, Any]:
        """Force immediate optimization across all systems"""
        logger.info("Forcing comprehensive performance optimization")
        
        # Memory cleanup
        memory_result = self.memory_optimizer.force_cleanup()
        
        # Cache optimization (clear old entries)
        cache_stats_before = self.request_optimizer.request_cache.get_stats()
        
        # Remove expired cache entries
        with self.request_optimizer.request_cache._lock:
            expired_keys = [
                key for key, entry in self.request_optimizer.request_cache.cache.items()
                if entry.is_expired()
            ]
            for key in expired_keys:
                del self.request_optimizer.request_cache.cache[key]
        
        cache_stats_after = self.request_optimizer.request_cache.get_stats()
        
        return {
            'memory_optimization': memory_result,
            'cache_optimization': {
                'expired_entries_removed': len(expired_keys) if 'expired_keys' in locals() else 0,
                'cache_size_before': cache_stats_before['size'],
                'cache_size_after': cache_stats_after['size']
            },
            'overall_score': self.get_comprehensive_metrics()['performance_score']
        }
    
    def shutdown(self):
        """Shutdown performance optimizer"""
        self.memory_optimizer.stop_monitoring()
        logger.info("Performance optimizer shut down")


# Global performance optimizer instance
_performance_optimizer: Optional[PerformanceOptimizer] = None


def get_performance_optimizer() -> PerformanceOptimizer:
    """Get global performance optimizer instance"""
    global _performance_optimizer
    if _performance_optimizer is None:
        _performance_optimizer = PerformanceOptimizer()
    return _performance_optimizer


def optimize_performance(func: Callable) -> Callable:
    """Decorator for automatic performance optimization"""
    return get_performance_optimizer().optimize_function(func)


def main():
    """CLI interface for performance optimizer"""
    import argparse
    
    parser = argparse.ArgumentParser(description="JARVIS-MK42 Performance Optimizer")
    parser.add_argument('--metrics', action='store_true', help='Show performance metrics')
    parser.add_argument('--optimize', action='store_true', help='Force optimization')
    parser.add_argument('--level', choices=['minimal', 'standard', 'aggressive', 'adaptive'],
                       default='standard', help='Optimization level')
    
    args = parser.parse_args()
    
    # Create optimizer with specified level
    optimizer = PerformanceOptimizer(OptimizationLevel(args.level))
    
    try:
        if args.metrics:
            metrics = optimizer.get_comprehensive_metrics()
            print(json.dumps(metrics, indent=2))
        
        elif args.optimize:
            result = optimizer.force_optimization()
            print("Optimization completed:")
            print(json.dumps(result, indent=2))
        
        else:
            print("Performance Optimizer Status:")
            metrics = optimizer.get_comprehensive_metrics()
            print(f"Optimization Level: {metrics['optimization_level']}")
            print(f"Performance Score: {metrics['performance_score']:.1f}/100")
            print(f"Memory Usage: {metrics['system']['memory_usage_mb']:.1f} MB")
            print(f"Cache Hit Rate: {metrics['cache']['hit_rate']:.1%}")
            print(f"Avg Response Time: {metrics['requests']['avg_response_time_ms']:.1f} ms")
    
    finally:
        optimizer.shutdown()


if __name__ == "__main__":
    main()
