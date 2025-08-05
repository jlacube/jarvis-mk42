# test_ai_module.py
"""
Simple test to verify AI module imports and basic functionality
"""

import sys
import os
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

def test_imports():
    """Test that AI modules can be imported"""
    try:
        print("Testing AI module imports...")
        
        # Test cognitive models
        from ai.cognitive_models import CognitiveArchitecture, SystemOneThinking, SystemTwoThinking
        print("✓ Cognitive models imported successfully")
        
        # Test multimodal engine
        from ai.multimodal_engine import MultiModalEngine, VisionProcessor, AudioProcessor
        print("✓ Multimodal engine imported successfully")
        
        # Test adaptive learning
        from ai.adaptive_learning import AdaptiveLearningSystem, ExperienceReplay
        print("✓ Adaptive learning imported successfully")
        
        # Test knowledge manager
        from ai.knowledge_manager import KnowledgeManager, EpisodicMemorySystem
        print("✓ Knowledge manager imported successfully")
        
        # Test main AI module
        from ai import CognitiveArchitecture as MainCogArch
        print("✓ Main AI module imported successfully")
        
        return True
        
    except ImportError as e:
        print(f"✗ Import failed: {e}")
        return False
    except Exception as e:
        print(f"✗ Unexpected error: {e}")
        return False

def test_basic_functionality():
    """Test basic functionality of AI components"""
    try:
        print("\nTesting basic functionality...")
        
        # Test cognitive architecture
        from ai.cognitive_models import CognitiveArchitecture
        cognitive_arch = CognitiveArchitecture()
        print("✓ Cognitive architecture created")
        
        # Test multimodal engine
        from ai.multimodal_engine import MultiModalEngine
        multimodal_engine = MultiModalEngine()
        print("✓ Multimodal engine created")
        
        # Test adaptive learning
        from ai.adaptive_learning import AdaptiveLearningSystem
        adaptive_learning = AdaptiveLearningSystem()
        print("✓ Adaptive learning system created")
        
        # Test knowledge manager  
        from ai.knowledge_manager import KnowledgeManager
        knowledge_manager = KnowledgeManager()
        print("✓ Knowledge manager created")
        
        return True
        
    except Exception as e:
        print(f"✗ Functionality test failed: {e}")
        return False

if __name__ == "__main__":
    print("=== AI Module Test ===")
    
    imports_ok = test_imports()
    if imports_ok:
        functionality_ok = test_basic_functionality()
        
        if functionality_ok:
            print(f"\n🎉 All tests passed! AI module is ready for Phase 2B.4")
        else:
            print(f"\n⚠️  Imports work but functionality tests failed")
    else:
        print(f"\n❌ Import tests failed - check dependencies")
    
    print("\nNote: Some advanced features may require additional dependencies:")
    print("- sentence-transformers (for semantic embeddings)")
    print("- faiss-cpu (for vector similarity search)")
    print("- networkx (for knowledge graphs)")
    print("- scikit-learn (for ML utilities)")
    print("\nInstall with: pip install sentence-transformers faiss-cpu networkx scikit-learn")
