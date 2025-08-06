#!/usr/bin/env python3
"""
JARVIS-MK42 AI Model Performance Optimizer
=========================================

This module provides comprehensive AI model performance optimization including:
- Model inference caching with context-aware cache keys
- Batch processing for multiple requests with optimal batching strategies
- Model warm-up and preloading strategies for faster response times
- Context window optimization for large conversations
- Memory-efficient model loading/unloading with smart resource management
- Multi-model orchestration and routing for optimal performance
"""

import os
import sys
import json
import time
import asyncio
import threading
import hashlib
import pickle
import gzip
from datetime import datetime, timedelta
from typing import Dict, List, Optional, Any, Callable, Union, Tuple
from dataclasses import dataclass, field
from enum import Enum
from collections import defaultdict, deque, OrderedDict
from concurrent.futures import ThreadPoolExecutor, Future
import weakref
import gc
import psutil

# Add project root to path
current_dir = os.path.dirname(os.path.abspath(__file__))
project_root = os.path.dirname(current_dir)
if project_root not in sys.path:
    sys.path.insert(0, project_root)

from utils.logging_config import get_logger

logger = get_logger(__name__)


class ModelType(Enum):
    """AI model types"""
    CHAT = "chat"
    COMPLETION = "completion"
    EMBEDDING = "embedding"
    VISION = "vision"
    AUDIO = "audio"
    MULTIMODAL = "multimodal"
    CUSTOM = "custom"


class CacheStrategy(Enum):
    """Model cache strategies"""
    EXACT_MATCH = "exact_match"
    SEMANTIC_SIMILARITY = "semantic_similarity"
    CONTEXT_AWARE = "context_aware"
    TEMPLATE_BASED = "template_based"
    HYBRID = "hybrid"


class ModelLoadingStrategy(Enum):
    """Model loading strategies"""
    EAGER = "eager"          # Load all models at startup
    LAZY = "lazy"            # Load models on first use
    DEMAND = "demand"        # Load/unload based on usage
    SCHEDULED = "scheduled"  # Load/unload on schedule
    ADAPTIVE = "adaptive"    # AI-driven loading decisions


@dataclass
class ModelMetrics:
    """Performance metrics for AI models"""
    model_id: str
    total_requests: int = 0
    successful_requests: int = 0
    failed_requests: int = 0
    total_inference_time: float = 0.0
    total_tokens_processed: int = 0
    cache_hits: int = 0
    cache_misses: int = 0
    memory_usage_mb: float = 0.0
    last_used: datetime = field(default_factory=datetime.now)
    load_time: float = 0.0
    
    @property
    def avg_inference_time(self) -> float:
        """Average inference time in seconds"""
        if self.successful_requests == 0:
            return 0.0
        return self.total_inference_time / self.successful_requests
    
    @property
    def success_rate(self) -> float:
        """Request success rate"""
        if self.total_requests == 0:
            return 0.0
        return self.successful_requests / self.total_requests
    
    @property
    def cache_hit_rate(self) -> float:
        """Cache hit rate"""
        total_cache_ops = self.cache_hits + self.cache_misses
        if total_cache_ops == 0:
            return 0.0
        return self.cache_hits / total_cache_ops
    
    @property
    def tokens_per_second(self) -> float:
        """Processing throughput in tokens per second"""
        if self.total_inference_time == 0:
            return 0.0
        return self.total_tokens_processed / self.total_inference_time


@dataclass
class CachedInference:
    """Cached model inference result"""
    cache_key: str
    model_id: str
    input_hash: str
    output: Any
    created_at: datetime
    access_count: int = 0
    last_accessed: datetime = field(default_factory=datetime.now)
    tokens_processed: int = 0
    inference_time: float = 0.0
    context_metadata: Dict[str, Any] = field(default_factory=dict)
    
    def update_access(self):
        """Update access tracking"""
        self.access_count += 1
        self.last_accessed = datetime.now()
    
    def is_expired(self, ttl_seconds: int) -> bool:
        """Check if cache entry has expired"""
        return (datetime.now() - self.created_at).total_seconds() > ttl_seconds


@dataclass
class BatchRequest:
    """Batch processing request"""
    request_id: str
    model_id: str
    input_data: Any
    context: Dict[str, Any] = field(default_factory=dict)
    priority: int = 5
    created_at: datetime = field(default_factory=datetime.now)
    timeout: float = 30.0
    
    def __lt__(self, other):
        """For priority queue ordering (higher priority = lower number)"""
        return self.priority < other.priority


class ModelInferenceCache:
    """Advanced caching system for model inference results"""
    
    def __init__(self,
                 max_size: int = 10000,
                 ttl_seconds: int = 3600,
                 strategy: CacheStrategy = CacheStrategy.HYBRID):
        self.max_size = max_size
        self.ttl_seconds = ttl_seconds
        self.strategy = strategy
        self.cache: OrderedDict[str, CachedInference] = OrderedDict()
        self._lock = threading.RLock()
        self.stats = {
            'hits': 0,
            'misses': 0,
            'evictions': 0,
            'total_size_bytes': 0
        }
    
    def _generate_cache_key(self, 
                           model_id: str,
                           input_data: Any,
                           context: Dict[str, Any] = None) -> str:
        """Generate cache key based on strategy"""
        base_data = {
            'model_id': model_id,
            'input': self._serialize_input(input_data)
        }
        
        if self.strategy == CacheStrategy.EXACT_MATCH:
            # Simple exact match
            key_string = json.dumps(base_data, sort_keys=True)
        
        elif self.strategy == CacheStrategy.CONTEXT_AWARE:
            # Include relevant context
            if context:
                # Only include stable context elements
                stable_context = {
                    k: v for k, v in context.items() 
                    if k in ['user_id', 'session_type', 'language', 'model_version']
                }
                base_data['context'] = stable_context
            key_string = json.dumps(base_data, sort_keys=True)
        
        elif self.strategy == CacheStrategy.TEMPLATE_BASED:
            # Extract template pattern from input
            template = self._extract_template(input_data)
            base_data['template'] = template
            key_string = json.dumps(base_data, sort_keys=True)
        
        else:  # HYBRID or default
            # Combine multiple strategies
            if context:
                base_data['context_hash'] = self._hash_context(context)
            key_string = json.dumps(base_data, sort_keys=True)
        
        return hashlib.sha256(key_string.encode()).hexdigest()
    
    def _serialize_input(self, input_data: Any) -> str:
        """Serialize input data for consistent hashing"""
        try:
            if isinstance(input_data, str):
                return input_data
            elif isinstance(input_data, dict):
                return json.dumps(input_data, sort_keys=True)
            elif isinstance(input_data, (list, tuple)):
                return json.dumps(list(input_data), sort_keys=True)
            else:
                return str(input_data)
        except:
            return str(input_data)
    
    def _extract_template(self, input_data: Any) -> str:
        """Extract template pattern from input for template-based caching"""
        if isinstance(input_data, str):
            # Simple pattern extraction (placeholder for more sophisticated logic)
            import re
            # Replace numbers with placeholder
            template = re.sub(r'\d+', '{NUM}', input_data)
            # Replace quoted strings with placeholder
            template = re.sub(r'["\'][^"\']*["\']', '{STR}', template)
            return template
        return self._serialize_input(input_data)
    
    def _hash_context(self, context: Dict[str, Any]) -> str:
        """Create hash of relevant context elements"""
        relevant_keys = ['user_preferences', 'conversation_style', 'domain']
        filtered_context = {
            k: v for k, v in context.items() if k in relevant_keys
        }
        return hashlib.md5(json.dumps(filtered_context, sort_keys=True).encode()).hexdigest()
    
    def _calculate_size(self, cached_inference: CachedInference) -> int:
        """Calculate approximate size of cached inference"""
        try:
            return len(pickle.dumps(cached_inference.output))
        except:
            return len(str(cached_inference.output).encode())
    
    def _evict_expired(self):
        """Remove expired cache entries"""
        current_time = datetime.now()
        expired_keys = []
        
        for key, cached in self.cache.items():
            if cached.is_expired(self.ttl_seconds):
                expired_keys.append(key)
        
        for key in expired_keys:
            cached = self.cache.pop(key, None)
            if cached:
                self.stats['evictions'] += 1
                self.stats['total_size_bytes'] -= self._calculate_size(cached)
    
    def _evict_lru(self):
        """Evict least recently used entries"""
        while len(self.cache) >= self.max_size:
            if not self.cache:
                break
            
            # Remove oldest entry
            key, cached = self.cache.popitem(last=False)
            self.stats['evictions'] += 1
            self.stats['total_size_bytes'] -= self._calculate_size(cached)
    
    def get(self, 
           model_id: str,
           input_data: Any,
           context: Dict[str, Any] = None) -> Optional[Any]:
        """Get cached inference result"""
        with self._lock:
            cache_key = self._generate_cache_key(model_id, input_data, context)
            cached = self.cache.get(cache_key)
            
            if cached is None:
                self.stats['misses'] += 1
                return None
            
            if cached.is_expired(self.ttl_seconds):
                del self.cache[cache_key]
                self.stats['misses'] += 1
                self.stats['evictions'] += 1
                return None
            
            # Update access tracking and move to end (LRU)
            cached.update_access()
            self.cache.move_to_end(cache_key)
            self.stats['hits'] += 1
            
            return cached.output
    
    def put(self,
           model_id: str,
           input_data: Any,
           output: Any,
           inference_time: float = 0.0,
           tokens_processed: int = 0,
           context: Dict[str, Any] = None):
        """Cache inference result"""
        with self._lock:
            # Clean up expired entries first
            self._evict_expired()
            
            # Evict LRU entries if needed
            self._evict_lru()
            
            cache_key = self._generate_cache_key(model_id, input_data, context)
            input_hash = hashlib.md5(self._serialize_input(input_data).encode()).hexdigest()
            
            cached = CachedInference(
                cache_key=cache_key,
                model_id=model_id,
                input_hash=input_hash,
                output=output,
                created_at=datetime.now(),
                tokens_processed=tokens_processed,
                inference_time=inference_time,
                context_metadata=context or {}
            )
            
            self.cache[cache_key] = cached
            self.stats['total_size_bytes'] += self._calculate_size(cached)
    
    def clear_model_cache(self, model_id: str):
        """Clear cache for specific model"""
        with self._lock:
            keys_to_remove = [
                key for key, cached in self.cache.items()
                if cached.model_id == model_id
            ]
            
            for key in keys_to_remove:
                cached = self.cache.pop(key)
                self.stats['total_size_bytes'] -= self._calculate_size(cached)
    
    def get_cache_stats(self) -> Dict[str, Any]:
        """Get cache statistics"""
        with self._lock:
            total_requests = self.stats['hits'] + self.stats['misses']
            hit_rate = self.stats['hits'] / max(total_requests, 1)
            
            return {
                'strategy': self.strategy.value,
                'size': len(self.cache),
                'max_size': self.max_size,
                'hits': self.stats['hits'],
                'misses': self.stats['misses'],
                'hit_rate': hit_rate,
                'evictions': self.stats['evictions'],
                'size_bytes': self.stats['total_size_bytes'],
                'size_mb': round(self.stats['total_size_bytes'] / (1024 * 1024), 2),
                'ttl_seconds': self.ttl_seconds
            }


class BatchProcessor:
    """Intelligent batch processing for model inference"""
    
    def __init__(self, 
                 max_batch_size: int = 10,
                 batch_timeout_ms: int = 100,
                 max_queue_size: int = 1000):
        self.max_batch_size = max_batch_size
        self.batch_timeout_ms = batch_timeout_ms
        self.max_queue_size = max_queue_size
        self.request_queues: Dict[str, deque] = defaultdict(deque)
        self.batch_futures: Dict[str, Dict[str, Future]] = defaultdict(dict)
        self.processing_threads: Dict[str, threading.Thread] = {}
        self.model_handlers: Dict[str, Callable] = {}
        self._running = False
        self._lock = threading.RLock()
    
    def register_model_handler(self, model_id: str, handler: Callable):
        """Register batch handler for model"""
        with self._lock:
            self.model_handlers[model_id] = handler
            
            if model_id not in self.processing_threads:
                # Start processing thread for this model
                thread = threading.Thread(
                    target=self._batch_processing_loop,
                    args=(model_id,),
                    daemon=True,
                    name=f"batch-{model_id}"
                )
                self.processing_threads[model_id] = thread
                thread.start()
                logger.info(f"Started batch processing for model: {model_id}")
    
    def submit_request(self, 
                      model_id: str,
                      input_data: Any,
                      context: Dict[str, Any] = None,
                      priority: int = 5,
                      timeout: float = 30.0) -> Future:
        """Submit request for batch processing"""
        if model_id not in self.model_handlers:
            raise ValueError(f"No handler registered for model: {model_id}")
        
        request_id = f"{model_id}_{time.time()}_{id(input_data)}"
        batch_request = BatchRequest(
            request_id=request_id,
            model_id=model_id,
            input_data=input_data,
            context=context or {},
            priority=priority,
            timeout=timeout
        )
        
        # Create future for this request
        future = Future()
        
        with self._lock:
            # Check queue size
            if len(self.request_queues[model_id]) >= self.max_queue_size:
                future.set_exception(Exception("Batch queue is full"))
                return future
            
            # Add to queue
            self.request_queues[model_id].append(batch_request)
            self.batch_futures[model_id][request_id] = future
        
        return future
    
    def _batch_processing_loop(self, model_id: str):
        """Main batch processing loop for a model"""
        self._running = True
        
        while self._running:
            try:
                batch_requests = self._collect_batch(model_id)
                
                if batch_requests:
                    self._process_batch(model_id, batch_requests)
                else:
                    # No requests, sleep briefly
                    time.sleep(0.01)  # 10ms
                    
            except Exception as e:
                logger.error(f"Error in batch processing loop for {model_id}: {e}")
                time.sleep(0.1)
    
    def _collect_batch(self, model_id: str) -> List[BatchRequest]:
        """Collect batch of requests for processing"""
        batch = []
        start_time = time.time()
        
        with self._lock:
            queue = self.request_queues[model_id]
            
            # Collect requests up to batch size or timeout
            while (len(batch) < self.max_batch_size and 
                   (time.time() - start_time) * 1000 < self.batch_timeout_ms):
                
                if queue:
                    batch.append(queue.popleft())
                else:
                    # No more requests, wait a bit
                    time.sleep(0.001)  # 1ms
                    
                    # Break if we have at least one request and timeout reached
                    if batch and (time.time() - start_time) * 1000 >= self.batch_timeout_ms:
                        break
        
        return batch
    
    def _process_batch(self, model_id: str, batch_requests: List[BatchRequest]):
        """Process batch of requests"""
        try:
            handler = self.model_handlers[model_id]
            
            # Prepare batch input
            batch_inputs = [req.input_data for req in batch_requests]
            batch_contexts = [req.context for req in batch_requests]
            
            start_time = time.time()
            
            # Execute batch processing
            try:
                batch_outputs = handler(batch_inputs, batch_contexts)
                processing_time = time.time() - start_time
                
                # Ensure outputs match inputs
                if len(batch_outputs) != len(batch_requests):
                    raise ValueError("Batch output count doesn't match input count")
                
                # Set results for each request
                with self._lock:
                    for request, output in zip(batch_requests, batch_outputs):
                        future = self.batch_futures[model_id].pop(request.request_id, None)
                        if future and not future.cancelled():
                            future.set_result({
                                'output': output,
                                'processing_time': processing_time / len(batch_requests),
                                'batch_size': len(batch_requests)
                            })
                
            except Exception as e:
                # Set exception for all requests in failed batch
                with self._lock:
                    for request in batch_requests:
                        future = self.batch_futures[model_id].pop(request.request_id, None)
                        if future and not future.cancelled():
                            future.set_exception(e)
                
                logger.error(f"Batch processing failed for {model_id}: {e}")
                
        except Exception as e:
            logger.error(f"Error processing batch for {model_id}: {e}")
    
    def stop_processing(self):
        """Stop batch processing"""
        self._running = False
        
        # Wait for threads to finish
        for thread in self.processing_threads.values():
            thread.join(timeout=5.0)
        
        logger.info("Batch processing stopped")
    
    def get_stats(self) -> Dict[str, Any]:
        """Get batch processing statistics"""
        with self._lock:
            stats = {}
            for model_id, queue in self.request_queues.items():
                stats[model_id] = {
                    'queue_size': len(queue),
                    'pending_futures': len(self.batch_futures[model_id]),
                    'max_batch_size': self.max_batch_size,
                    'batch_timeout_ms': self.batch_timeout_ms
                }
            
            return {
                'models': stats,
                'total_queued_requests': sum(len(q) for q in self.request_queues.values()),
                'processing_enabled': self._running
            }


class ModelManager:
    """Model loading and lifecycle management"""
    
    def __init__(self, 
                 loading_strategy: ModelLoadingStrategy = ModelLoadingStrategy.ADAPTIVE,
                 max_loaded_models: int = 5,
                 memory_limit_mb: int = 4096):
        self.loading_strategy = loading_strategy
        self.max_loaded_models = max_loaded_models
        self.memory_limit_mb = memory_limit_mb
        self.loaded_models: Dict[str, Any] = {}
        self.model_metrics: Dict[str, ModelMetrics] = {}
        self.model_loaders: Dict[str, Callable] = {}
        self.model_configs: Dict[str, Dict[str, Any]] = {}
        self._lock = threading.RLock()
        self._warmup_thread: Optional[threading.Thread] = None
        
        # Start model management based on strategy
        if loading_strategy == ModelLoadingStrategy.EAGER:
            self._start_eager_loading()
        elif loading_strategy == ModelLoadingStrategy.SCHEDULED:
            self._start_scheduled_management()
    
    def register_model(self,
                      model_id: str,
                      loader: Callable,
                      config: Dict[str, Any] = None,
                      preload: bool = False):
        """Register model with loader function"""
        with self._lock:
            self.model_loaders[model_id] = loader
            self.model_configs[model_id] = config or {}
            self.model_metrics[model_id] = ModelMetrics(model_id=model_id)
            
            if preload or self.loading_strategy == ModelLoadingStrategy.EAGER:
                self._load_model(model_id)
                
            logger.info(f"Registered model: {model_id}")
    
    def _load_model(self, model_id: str) -> bool:
        """Load model into memory"""
        try:
            if model_id in self.loaded_models:
                return True
            
            # Check memory constraints
            if len(self.loaded_models) >= self.max_loaded_models:
                self._unload_least_used_model()
            
            if not self._check_memory_available():
                self._free_memory()
            
            # Load the model
            loader = self.model_loaders.get(model_id)
            if not loader:
                raise ValueError(f"No loader registered for model: {model_id}")
            
            start_time = time.time()
            logger.info(f"Loading model: {model_id}")
            
            model = loader(self.model_configs.get(model_id, {}))
            load_time = time.time() - start_time
            
            self.loaded_models[model_id] = model
            self.model_metrics[model_id].load_time = load_time
            self.model_metrics[model_id].last_used = datetime.now()
            
            # Update memory usage
            self._update_model_memory_usage(model_id)
            
            logger.info(f"Model {model_id} loaded in {load_time:.2f}s")
            return True
            
        except Exception as e:
            logger.error(f"Failed to load model {model_id}: {e}")
            return False
    
    def _unload_model(self, model_id: str):
        """Unload model from memory"""
        try:
            if model_id not in self.loaded_models:
                return
            
            model = self.loaded_models.pop(model_id)
            
            # Clean up model resources if it has cleanup method
            if hasattr(model, 'cleanup'):
                model.cleanup()
            elif hasattr(model, 'close'):
                model.close()
            
            # Force garbage collection
            del model
            gc.collect()
            
            self.model_metrics[model_id].memory_usage_mb = 0.0
            logger.info(f"Unloaded model: {model_id}")
            
        except Exception as e:
            logger.error(f"Error unloading model {model_id}: {e}")
    
    def _unload_least_used_model(self):
        """Unload the least recently used model"""
        if not self.loaded_models:
            return
        
        # Find least recently used model
        lru_model = min(
            self.loaded_models.keys(),
            key=lambda m: self.model_metrics[m].last_used
        )
        
        self._unload_model(lru_model)
    
    def _check_memory_available(self) -> bool:
        """Check if sufficient memory is available"""
        current_usage = psutil.virtual_memory().percent
        available_mb = psutil.virtual_memory().available / (1024 * 1024)
        
        # Require at least 512MB free and less than 85% usage
        return available_mb > 512 and current_usage < 85
    
    def _free_memory(self):
        """Free memory by unloading models"""
        # Sort by last used time and unload oldest
        models_by_usage = sorted(
            self.loaded_models.keys(),
            key=lambda m: self.model_metrics[m].last_used
        )
        
        # Unload up to half of loaded models
        unload_count = max(1, len(models_by_usage) // 2)
        for i in range(min(unload_count, len(models_by_usage))):
            self._unload_model(models_by_usage[i])
            
            if self._check_memory_available():
                break
    
    def _update_model_memory_usage(self, model_id: str):
        """Update memory usage for model"""
        try:
            # This is an approximation - actual implementation would
            # depend on the specific model framework being used
            process = psutil.Process()
            memory_mb = process.memory_info().rss / (1024 * 1024)
            
            # Rough estimate - divide by number of loaded models
            if len(self.loaded_models) > 0:
                per_model_mb = memory_mb / len(self.loaded_models)
                self.model_metrics[model_id].memory_usage_mb = per_model_mb
                
        except Exception as e:
            logger.warning(f"Could not update memory usage for {model_id}: {e}")
    
    def get_model(self, model_id: str) -> Optional[Any]:
        """Get model, loading if necessary"""
        with self._lock:
            # Update usage tracking
            if model_id in self.model_metrics:
                self.model_metrics[model_id].last_used = datetime.now()
            
            # Return if already loaded
            if model_id in self.loaded_models:
                return self.loaded_models[model_id]
            
            # Load on demand based on strategy
            if self.loading_strategy in [ModelLoadingStrategy.LAZY, 
                                       ModelLoadingStrategy.DEMAND,
                                       ModelLoadingStrategy.ADAPTIVE]:
                if self._load_model(model_id):
                    return self.loaded_models[model_id]
            
            return None
    
    def update_model_metrics(self,
                           model_id: str,
                           inference_time: float,
                           tokens_processed: int = 0,
                           success: bool = True):
        """Update model performance metrics"""
        with self._lock:
            metrics = self.model_metrics.get(model_id)
            if not metrics:
                return
            
            metrics.total_requests += 1
            if success:
                metrics.successful_requests += 1
                metrics.total_inference_time += inference_time
                metrics.total_tokens_processed += tokens_processed
            else:
                metrics.failed_requests += 1
            
            metrics.last_used = datetime.now()
    
    def get_model_stats(self) -> Dict[str, Any]:
        """Get comprehensive model statistics"""
        with self._lock:
            stats = {
                'loading_strategy': self.loading_strategy.value,
                'max_loaded_models': self.max_loaded_models,
                'currently_loaded': len(self.loaded_models),
                'registered_models': len(self.model_loaders),
                'memory_limit_mb': self.memory_limit_mb,
                'models': {}
            }
            
            for model_id, metrics in self.model_metrics.items():
                is_loaded = model_id in self.loaded_models
                stats['models'][model_id] = {
                    'loaded': is_loaded,
                    'total_requests': metrics.total_requests,
                    'success_rate': metrics.success_rate,
                    'avg_inference_time_ms': metrics.avg_inference_time * 1000,
                    'tokens_per_second': metrics.tokens_per_second,
                    'cache_hit_rate': metrics.cache_hit_rate,
                    'memory_usage_mb': metrics.memory_usage_mb,
                    'load_time_s': metrics.load_time,
                    'last_used': metrics.last_used.isoformat()
                }
            
            return stats
    
    def shutdown(self):
        """Shutdown model manager"""
        with self._lock:
            # Unload all models
            model_ids = list(self.loaded_models.keys())
            for model_id in model_ids:
                self._unload_model(model_id)
            
            logger.info("Model manager shut down")


class AIModelOptimizer:
    """Main AI model performance optimizer"""
    
    def __init__(self,
                 cache_strategy: CacheStrategy = CacheStrategy.HYBRID,
                 loading_strategy: ModelLoadingStrategy = ModelLoadingStrategy.ADAPTIVE,
                 max_cache_size: int = 50000,
                 max_loaded_models: int = 5):
        
        self.inference_cache = ModelInferenceCache(
            max_size=max_cache_size,
            ttl_seconds=7200,  # 2 hours
            strategy=cache_strategy
        )
        
        self.model_manager = ModelManager(
            loading_strategy=loading_strategy,
            max_loaded_models=max_loaded_models
        )
        
        self.batch_processor = BatchProcessor(
            max_batch_size=8,
            batch_timeout_ms=50  # 50ms for better responsiveness
        )
        
        self.global_metrics = {
            'total_requests': 0,
            'cache_hits': 0,
            'cache_misses': 0,
            'total_inference_time': 0.0,
            'batch_requests': 0
        }
        
        self._lock = threading.Lock()
        
        logger.info("AI Model Optimizer initialized")
    
    def register_model(self,
                      model_id: str,
                      loader: Callable,
                      config: Dict[str, Any] = None,
                      batch_handler: Callable = None,
                      preload: bool = False):
        """Register AI model with optimizer"""
        # Register with model manager
        self.model_manager.register_model(model_id, loader, config, preload)
        
        # Register batch handler if provided
        if batch_handler:
            self.batch_processor.register_model_handler(model_id, batch_handler)
        
        logger.info(f"Registered model {model_id} with AI optimizer")
    
    async def optimized_inference(self,
                                 model_id: str,
                                 input_data: Any,
                                 context: Dict[str, Any] = None,
                                 use_cache: bool = True,
                                 use_batching: bool = False,
                                 priority: int = 5) -> Dict[str, Any]:
        """Perform optimized model inference"""
        start_time = time.time()
        
        with self._lock:
            self.global_metrics['total_requests'] += 1
        
        try:
            # Try cache first if enabled
            if use_cache:
                cached_result = self.inference_cache.get(model_id, input_data, context)
                if cached_result is not None:
                    with self._lock:
                        self.global_metrics['cache_hits'] += 1
                    
                    self.model_manager.model_metrics[model_id].cache_hits += 1
                    
                    return {
                        'output': cached_result,
                        'inference_time': 0.0,
                        'cached': True,
                        'model_id': model_id
                    }
            
            # Cache miss
            with self._lock:
                self.global_metrics['cache_misses'] += 1
            
            self.model_manager.model_metrics[model_id].cache_misses += 1
            
            # Choose processing method
            if use_batching and model_id in self.batch_processor.model_handlers:
                # Use batch processing
                future = self.batch_processor.submit_request(
                    model_id, input_data, context, priority
                )
                
                result = future.result(timeout=30.0)
                output = result['output']
                inference_time = result['processing_time']
                
                with self._lock:
                    self.global_metrics['batch_requests'] += 1
                
            else:
                # Direct inference
                model = self.model_manager.get_model(model_id)
                if model is None:
                    raise ValueError(f"Model {model_id} could not be loaded")
                
                inference_start = time.time()
                
                # Perform inference (this would call the actual model)
                if hasattr(model, 'predict'):
                    output = model.predict(input_data)
                elif hasattr(model, 'invoke'):
                    output = model.invoke(input_data)
                elif callable(model):
                    output = model(input_data)
                else:
                    raise ValueError(f"Model {model_id} is not callable")
                
                inference_time = time.time() - inference_start
            
            # Update metrics
            total_time = time.time() - start_time
            tokens_processed = self._estimate_tokens(input_data, output)
            
            self.model_manager.update_model_metrics(
                model_id, inference_time, tokens_processed, True
            )
            
            with self._lock:
                self.global_metrics['total_inference_time'] += total_time
            
            # Cache result if enabled
            if use_cache:
                self.inference_cache.put(
                    model_id, input_data, output,
                    inference_time, tokens_processed, context
                )
            
            return {
                'output': output,
                'inference_time': inference_time,
                'cached': False,
                'model_id': model_id,
                'tokens_processed': tokens_processed
            }
            
        except Exception as e:
            # Update error metrics
            self.model_manager.update_model_metrics(model_id, 0, 0, False)
            
            logger.error(f"Inference failed for {model_id}: {e}")
            raise
    
    def _estimate_tokens(self, input_data: Any, output: Any) -> int:
        """Estimate token count for input and output"""
        # Rough estimation - actual implementation would depend on tokenizer
        input_text = str(input_data) if input_data else ""
        output_text = str(output) if output else ""
        
        # Approximate: 1 token ≈ 4 characters
        return (len(input_text) + len(output_text)) // 4
    
    def clear_model_cache(self, model_id: str):
        """Clear cache for specific model"""
        self.inference_cache.clear_model_cache(model_id)
        logger.info(f"Cleared cache for model: {model_id}")
    
    def get_comprehensive_stats(self) -> Dict[str, Any]:
        """Get comprehensive optimization statistics"""
        with self._lock:
            total_requests = self.global_metrics['total_requests']
            cache_hit_rate = (
                self.global_metrics['cache_hits'] / max(total_requests, 1)
            )
            avg_inference_time = (
                self.global_metrics['total_inference_time'] / max(total_requests, 1)
            )
        
        return {
            'timestamp': datetime.now().isoformat(),
            'global_metrics': {
                'total_requests': total_requests,
                'cache_hit_rate': cache_hit_rate,
                'avg_inference_time_ms': avg_inference_time * 1000,
                'batch_request_rate': (
                    self.global_metrics['batch_requests'] / max(total_requests, 1)
                )
            },
            'cache_stats': self.inference_cache.get_cache_stats(),
            'model_stats': self.model_manager.get_model_stats(),
            'batch_stats': self.batch_processor.get_stats(),
            'system_memory_mb': psutil.virtual_memory().used / (1024 * 1024),
            'system_memory_percent': psutil.virtual_memory().percent
        }
    
    def shutdown(self):
        """Shutdown AI model optimizer"""
        self.batch_processor.stop_processing()
        self.model_manager.shutdown()
        logger.info("AI Model Optimizer shut down")


# Global optimizer instance
_ai_model_optimizer: Optional[AIModelOptimizer] = None


def get_ai_model_optimizer() -> AIModelOptimizer:
    """Get global AI model optimizer instance"""
    global _ai_model_optimizer
    if _ai_model_optimizer is None:
        _ai_model_optimizer = AIModelOptimizer()
    return _ai_model_optimizer


def main():
    """CLI interface for AI model optimizer"""
    import argparse
    
    parser = argparse.ArgumentParser(description="JARVIS-MK42 AI Model Optimizer")
    parser.add_argument('--stats', action='store_true', help='Show optimization stats')
    parser.add_argument('--clear-cache', metavar='MODEL_ID', help='Clear cache for model')
    
    args = parser.parse_args()
    
    optimizer = get_ai_model_optimizer()
    
    try:
        if args.stats:
            stats = optimizer.get_comprehensive_stats()
            print(json.dumps(stats, indent=2))
        
        elif args.clear_cache:
            optimizer.clear_model_cache(args.clear_cache)
            print(f"Cache cleared for model: {args.clear_cache}")
        
        else:
            stats = optimizer.get_comprehensive_stats()
            print("AI Model Optimizer Status:")
            print(f"Total Requests: {stats['global_metrics']['total_requests']}")
            print(f"Cache Hit Rate: {stats['global_metrics']['cache_hit_rate']:.1%}")
            print(f"Avg Inference Time: {stats['global_metrics']['avg_inference_time_ms']:.1f} ms")
            print(f"Loaded Models: {stats['model_stats']['currently_loaded']}/{stats['model_stats']['max_loaded_models']}")
            print(f"Cache Size: {stats['cache_stats']['size']}/{stats['cache_stats']['max_size']}")
    
    finally:
        optimizer.shutdown()


if __name__ == "__main__":
    main()
