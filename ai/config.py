# ai/config.py
"""
Configuration for Advanced AI Module
====================================

Simple configuration for AI module components.
"""

import os
from typing import Dict, Any


class AIConfig:
    """Configuration class for AI module"""
    
    def __init__(self):
        # Cognitive Models Configuration
        self.cognitive_models = {
            "system_one_threshold": 0.1,
            "system_two_threshold": 0.3,
            "meta_cognitive_enabled": True,
            "confidence_threshold": 0.5
        }
        
        # Multi-modal Engine Configuration
        self.multimodal = {
            "vision_quality": "balanced",
            "audio_quality": "balanced", 
            "cross_modal_enabled": True,
            "embedding_model": "all-MiniLM-L6-v2"
        }
        
        # Adaptive Learning Configuration
        self.adaptive_learning = {
            "experience_buffer_size": 10000,
            "replay_batch_size": 32,
            "learning_rate": 0.1,
            "consolidation_threshold": 0.8
        }
        
        # Knowledge Management Configuration
        self.knowledge_management = {
            "episodic_memory_limit": 50000,
            "semantic_memory_limit": 100000,
            "consolidation_interval": 3600,  # seconds
            "importance_threshold": 0.3
        }
        
        # Database paths
        self.database_paths = {
            "episodic_memory": "episodic_memory.db",
            "semantic_memory": "semantic_memory.db",
            "personalization": "personalization.db"
        }
        
        # Logging configuration
        self.logging = {
            "level": os.getenv("AI_LOG_LEVEL", "INFO"),
            "format": "%(asctime)s - %(name)s - %(levelname)s - %(message)s"
        }
    
    def get(self, key: str, default: Any = None) -> Any:
        """Get configuration value"""
        keys = key.split('.')
        value = self
        
        for k in keys:
            if hasattr(value, k):
                value = getattr(value, k)
            elif isinstance(value, dict) and k in value:
                value = value[k]
            else:
                return default
        
        return value
    
    def update(self, updates: Dict[str, Any]) -> None:
        """Update configuration values"""
        for key, value in updates.items():
            keys = key.split('.')
            target = self
            
            for k in keys[:-1]:
                if hasattr(target, k):
                    target = getattr(target, k)
                elif isinstance(target, dict):
                    if k not in target:
                        target[k] = {}
                    target = target[k]
            
            final_key = keys[-1]
            if hasattr(target, final_key):
                setattr(target, final_key, value)
            elif isinstance(target, dict):
                target[final_key] = value


# Global configuration instance
_config = AIConfig()


def get_settings() -> AIConfig:
    """Get the global AI configuration"""
    return _config


def update_settings(updates: Dict[str, Any]) -> None:
    """Update global AI configuration"""
    _config.update(updates)
