# ai/__init__.py
"""
Advanced AI Integration Module for Jarvis-MK42
==============================================

This module provides advanced AI capabilities including:
- Cognitive models and reasoning architectures
- Multi-modal processing and understanding
- Adaptive learning and personalization
- Knowledge management and memory systems
- Advanced orchestration and coordination

Phase 2B.4: Advanced AI Integration
"""

try:
    from .cognitive_models import (
        CognitiveArchitecture,
        SystemOneThinking,
        SystemTwoThinking,
        MetaCognition,
        CausalReasoning,
        ChainOfThought,
        TreeOfThought
    )

    from .multimodal_engine import (
        MultiModalEngine,
        VisionProcessor,
        AudioProcessor,
        CrossModalProcessor
    )

    from .adaptive_learning import (
        AdaptiveLearningSystem,
        ExperienceReplay,
        PersonalizationEngine,
        IncrementalLearning
    )

    from .knowledge_manager import (
        KnowledgeManager,
        EpisodicMemorySystem,
        SemanticMemorySystem
    )

    __all__ = [
        # Cognitive Models
        'CognitiveArchitecture',
        'SystemOneThinking',
        'SystemTwoThinking', 
        'MetaCognition',
        'CausalReasoning',
        'ChainOfThought',
        'TreeOfThought',
        
        # Multi-Modal Engine
        'MultiModalEngine',
        'VisionProcessor',
        'AudioProcessor',
        'CrossModalProcessor',
        
        # Adaptive Learning
        'AdaptiveLearningSystem',
        'ExperienceReplay',
        'PersonalizationEngine',
        'IncrementalLearning',
        
        # Knowledge Management
        'KnowledgeManager',
        'EpisodicMemorySystem',
        'SemanticMemorySystem'
    ]

except ImportError as e:
    # Handle missing dependencies gracefully
    import warnings
    warnings.warn(f"Some AI module dependencies are missing: {e}. "
                  f"Please install required packages: pip install numpy networkx sentence-transformers faiss-cpu scikit-learn")
    
    # Provide minimal fallback exports
    __all__ = []
