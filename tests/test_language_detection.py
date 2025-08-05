# tests/test_language_detection.py
"""
Test Suite for Language Detection Tools (Phase 2B.3)
===================================================

This test suite validates the language detection capabilities including:
- Basic language detection for common languages
- Confidence scoring and reliability assessment
- Multi-language detection for mixed content
- Integration with enhanced agents
- Edge cases and error handling
"""

import pytest
import asyncio
from unittest.mock import patch, MagicMock

# Import language detection components
from tools.language_detection import (
    detect_language, detect_language_with_confidence, detect_multiple_languages,
    get_supported_languages, detect_text_language, is_language_supported,
    get_language_display_name, _detect_single_language, _detect_multiple_languages
)

from utils.language_utils import (
    get_language_context, is_text_mixed_language, normalize_text_for_language,
    split_text_by_sentences, get_word_count, estimate_reading_time,
    is_formal_language_context, prepare_text_for_translation,
    validate_language_consistency
)


class TestLanguageDetection:
    """Test basic language detection functionality."""
    
    def test_detect_english(self):
        """Test detection of English text."""
        # Use longer, more clearly English text
        result = detect_language.invoke({"text": "This is a comprehensive English sentence with multiple common English words."})
        assert result == "en"
    
    def test_detect_spanish(self):
        """Test detection of Spanish text."""
        result = detect_language.invoke({"text": "Esta es una oración completa en español con múltiples palabras comunes."})
        assert result == "es"
    
    def test_detect_french(self):
        """Test detection of French text."""
        result = detect_language.invoke({"text": "Ceci est une phrase complète en français avec plusieurs mots courants."})
        assert result == "fr"
    
    def test_detect_german(self):
        """Test detection of German text."""
        result = detect_language.invoke({"text": "Dies ist ein vollständiger deutscher Satz mit mehreren häufigen Wörtern."})
        assert result == "de"
    
    def test_detect_chinese(self):
        """Test detection of Chinese text."""
        result = detect_language.invoke({"text": "这是一个完整的中文句子，包含多个常见的中文词汇。"})
        assert result in ["zh-cn", "zh-tw"]  # Could be either simplified or traditional
    
    def test_detect_empty_text(self):
        """Test detection with empty text."""
        result = detect_language.invoke({"text": ""})
        assert result == "en"  # Should default to English
    
    def test_detect_short_text(self):
        """Test detection with very short text."""
        # Very short text can be unreliable, so we just check it returns a valid language code
        result = detect_language.invoke({"text": "Hello there"})
        assert isinstance(result, str)
        assert len(result) >= 2  # Should be a valid language code
    
    def test_detect_language_with_confidence_english(self):
        """Test detailed detection with confidence for English."""
        result = detect_language_with_confidence.invoke({"text": "This is a comprehensive English sentence with multiple words."})
        
        assert isinstance(result, dict)
        assert result["language_code"] == "en"
        assert result["language_name"] == "English"
        assert result["confidence"] > 0.5
        assert result["is_reliable"] is True
        assert result["text_length"] > 0
    
    def test_detect_language_with_confidence_spanish(self):
        """Test detailed detection with confidence for Spanish."""
        result = detect_language_with_confidence.invoke({"text": "Esta es una oración completa en español con múltiples palabras."})
        
        assert result["language_code"] == "es"
        assert result["language_name"] == "Spanish"
        assert result["confidence"] > 0.7
        assert result["is_reliable"] is True
    
    def test_detect_multiple_languages_english(self):
        """Test multiple language detection for English text."""
        result = detect_multiple_languages.invoke({"text": "This is a clear English sentence."})
        
        assert isinstance(result, dict)
        assert "primary_language" in result
        assert "all_languages" in result
        assert result["primary_language"]["language_code"] == "en"
        assert len(result["all_languages"]) >= 1
        assert result["detection_method"] == "probabilistic"
    
    def test_detect_multiple_languages_mixed(self):
        """Test multiple language detection for potentially mixed content."""
        result = detect_multiple_languages.invoke({"text": "Hello mundo, comment ça va?"})
        
        assert "primary_language" in result
        assert "all_languages" in result
        assert len(result["all_languages"]) >= 1
        # Should detect multiple possible languages
    
    def test_get_supported_languages(self):
        """Test getting list of supported languages."""
        result = get_supported_languages.invoke({})
        
        assert isinstance(result, dict)
        assert "language_codes" in result
        assert "language_names" in result
        assert "total_count" in result
        assert len(result["language_codes"]) > 20  # Should support many languages
        assert "en" in result["language_codes"]
        assert "English" in result["language_names"]
    
    def test_detect_text_language_helper(self):
        """Test the helper function for other modules."""
        lang_code, confidence, is_reliable = detect_text_language("This is English text.")
        
        assert lang_code == "en"
        assert isinstance(confidence, float)
        assert isinstance(is_reliable, bool)
        assert 0.0 <= confidence <= 1.0
    
    def test_is_language_supported(self):
        """Test checking if languages are supported."""
        assert is_language_supported("en") is True
        assert is_language_supported("es") is True
        assert is_language_supported("zz") is False  # Invalid language code
    
    def test_get_language_display_name(self):
        """Test getting display names for language codes."""
        assert get_language_display_name("en") == "English"
        assert get_language_display_name("es") == "Spanish"
        assert get_language_display_name("fr") == "French"
        assert get_language_display_name("invalid") == "INVALID"


class TestLanguageUtils:
    """Test language utility functions."""
    
    def test_get_language_context_english(self):
        """Test getting language context for English text."""
        context = get_language_context("This is an English sentence.")
        
        assert context.language_code == "en"
        assert context.language_name == "English"
        assert context.direction == "ltr"
        assert context.script == "latin"
        assert context.confidence > 0.5
    
    def test_get_language_context_arabic(self):
        """Test getting language context for Arabic text."""
        context = get_language_context("هذه جملة باللغة العربية")
        
        assert context.language_code == "ar"
        assert context.direction == "rtl"
        assert context.script == "arabic"
    
    def test_normalize_text_for_language_english(self):
        """Test text normalization for English."""
        text = "  Hello   world  \n\n  "
        normalized = normalize_text_for_language(text, "en")
        
        assert normalized == "Hello world"
    
    def test_normalize_text_for_language_chinese(self):
        """Test text normalization for Chinese."""
        text = "你好，世界！"
        normalized = normalize_text_for_language(text, "zh-cn")
        
        # Should normalize Chinese punctuation
        assert "," in normalized or "，" in normalized
    
    def test_split_text_by_sentences_english(self):
        """Test sentence splitting for English."""
        text = "First sentence. Second sentence! Third sentence?"
        sentences = split_text_by_sentences(text, "en")
        
        assert len(sentences) == 3
        assert "First sentence" in sentences[0]
    
    def test_split_text_by_sentences_chinese(self):
        """Test sentence splitting for Chinese."""
        text = "第一句话。第二句话！第三句话？"
        sentences = split_text_by_sentences(text, "zh-cn")
        
        assert len(sentences) >= 2  # Should split on Chinese punctuation
    
    def test_get_word_count_english(self):
        """Test word count for English."""
        text = "This is a simple test sentence."
        count = get_word_count(text, "en")
        
        assert count == 6
    
    def test_get_word_count_chinese(self):
        """Test word count for Chinese (character-based)."""
        text = "这是一个测试句子"
        count = get_word_count(text, "zh-cn")
        
        assert count > 0  # Chinese counts characters
    
    def test_estimate_reading_time(self):
        """Test reading time estimation."""
        text = "This is a sample text for reading time estimation. " * 20
        time = estimate_reading_time(text, "en")
        
        assert time >= 1  # Should take at least 1 minute
        assert isinstance(time, int)
    
    def test_is_formal_language_context_english(self):
        """Test formal language detection for English."""
        formal_text = "Dear Sir or Madam, I would like to respectfully request your assistance."
        informal_text = "Hey, can you help me out?"
        
        assert is_formal_language_context(formal_text, "en") is True
        assert is_formal_language_context(informal_text, "en") is False
    
    def test_prepare_text_for_translation(self):
        """Test text preparation for translation."""
        result = prepare_text_for_translation("Hello world", "en", "es")
        
        assert isinstance(result, dict)
        assert "prepared_text" in result
        assert "source_context" in result
        assert "target_context" in result
        assert "translation_notes" in result
        assert result["source_context"].language_code == "en"
        assert result["target_context"].language_code == "es"
    
    def test_validate_language_consistency(self):
        """Test language consistency validation."""
        texts = [
            "This is English text.",
            "This is also English text.",
            "And this is English too."
        ]
        
        result = validate_language_consistency(texts, "en")
        
        assert isinstance(result, dict)
        assert result["is_consistent"] is True
        assert result["consistency_score"] == 1.0
        assert result["expected_language"] == "en"
    
    def test_validate_language_consistency_mixed(self):
        """Test language consistency validation with mixed languages."""
        texts = [
            "This is English text.",
            "Esto es texto en español.",
            "This is English again."
        ]
        
        result = validate_language_consistency(texts, "en")
        
        assert result["is_consistent"] is False
        assert result["consistency_score"] < 1.0
        assert len(result["inconsistent_texts"]) > 0


class TestLanguageDetectionIntegration:
    """Test integration of language detection with other components."""
    
    @pytest.mark.asyncio
    async def test_language_detection_tools_registration(self):
        """Test that language detection tools are properly registered."""
        from tools.language_detection import get_language_detection_tools
        
        tools = get_language_detection_tools()
        
        assert len(tools) == 4  # Should have 4 language detection tools
        tool_names = [tool.name for tool in tools]
        
        assert "detect_language" in tool_names
        assert "detect_language_with_confidence" in tool_names
        assert "detect_multiple_languages" in tool_names
        assert "get_supported_languages" in tool_names
    
    def test_language_detection_error_handling(self):
        """Test error handling in language detection."""
        # Test with empty string input (None is not valid for tools)
        result = detect_language.invoke({"text": ""})
        assert result == "en"  # Should default to English
        
        # Test with very unusual text
        result = detect_language.invoke({"text": "12345 !@#$%"})
        assert isinstance(result, str)  # Should return some language code
    
    def test_language_utils_edge_cases(self):
        """Test edge cases in language utilities."""
        # Empty text
        context = get_language_context("")
        assert context.language_code == "en"  # Should default to English
        
        # Very short text
        context = get_language_context("Hi")
        assert isinstance(context.confidence, float)
        
        # Mixed language detection
        is_mixed = is_text_mixed_language("Hello mundo", threshold=0.3)
        assert isinstance(is_mixed, bool)


class TestLanguageDetectionPerformance:
    """Test performance characteristics of language detection."""
    
    def test_detection_speed(self):
        """Test that language detection is reasonably fast."""
        import time
        
        text = "This is a reasonably long English sentence to test detection speed."
        
        start_time = time.time()
        for _ in range(10):  # Run detection 10 times
            detect_language(text)
        end_time = time.time()
        
        avg_time = (end_time - start_time) / 10
        assert avg_time < 0.1  # Should be under 100ms per detection
    
    def test_confidence_accuracy(self):
        """Test that confidence scores are meaningful."""
        # Clear English text should have high confidence
        result = detect_language_with_confidence(
            "This is a very clear and unambiguous English sentence with many words."
        )
        assert result["confidence"] > 0.8
        assert result["is_reliable"] is True
        
        # Very short text should have lower confidence
        result = detect_language_with_confidence("OK")
        # Confidence might be lower for very short text
        assert 0.0 <= result["confidence"] <= 1.0


if __name__ == "__main__":
    # Run the tests
    pytest.main([__file__, "-v", "--tb=short"])
