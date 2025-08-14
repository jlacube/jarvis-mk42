"""
Comprehensive Tests for Language Utils Module

This test suite provides complete coverage for the utils.language_utils module,
testing all language processing utilities, data structures, and edge cases.
"""

import pytest
from unittest.mock import patch, Mock
from typing import Dict, List, Any

# Import the module under test
from utils.language_utils import (
    LanguageFamily,
    LanguageContext,
    LANGUAGE_FAMILIES,
    RTL_LANGUAGES,
    LANGUAGE_SCRIPTS,
    get_language_context,
    is_text_mixed_language,
    normalize_text_for_language,
    split_text_by_sentences,
    get_word_count,
    estimate_reading_time,
    is_formal_language_context,
    prepare_text_for_translation,
    validate_language_consistency
)


class TestLanguageFamily:
    """Test LanguageFamily enum"""
    
    def test_language_family_values(self):
        """Test LanguageFamily enum values"""
        assert LanguageFamily.GERMANIC.value == "germanic"
        assert LanguageFamily.ROMANCE.value == "romance"
        assert LanguageFamily.SLAVIC.value == "slavic"
        assert LanguageFamily.SINO_TIBETAN.value == "sino_tibetan"
        assert LanguageFamily.AFROASIATIC.value == "afroasiatic"
        assert LanguageFamily.INDO_ARYAN.value == "indo_aryan"
        assert LanguageFamily.JAPONIC.value == "japonic"
        assert LanguageFamily.KOREANIC.value == "koreanic"
        assert LanguageFamily.OTHER.value == "other"
    
    def test_language_family_count(self):
        """Test that all expected language families are present"""
        families = list(LanguageFamily)
        assert len(families) == 9


class TestLanguageContext:
    """Test LanguageContext dataclass"""
    
    def test_language_context_creation(self):
        """Test LanguageContext creation"""
        context = LanguageContext(
            language_code="en",
            language_name="English",
            confidence=0.95,
            is_reliable=True,
            family=LanguageFamily.GERMANIC,
            direction="ltr",
            script="latin"
        )
        
        assert context.language_code == "en"
        assert context.language_name == "English"
        assert context.confidence == 0.95
        assert context.is_reliable is True
        assert context.family == LanguageFamily.GERMANIC
        assert context.direction == "ltr"
        assert context.script == "latin"
    
    def test_language_context_attributes(self):
        """Test LanguageContext attribute access"""
        context = LanguageContext("es", "Spanish", 0.9, True, LanguageFamily.ROMANCE, "ltr", "latin")
        
        # Test all attributes are accessible
        assert hasattr(context, 'language_code')
        assert hasattr(context, 'language_name')
        assert hasattr(context, 'confidence')
        assert hasattr(context, 'is_reliable')
        assert hasattr(context, 'family')
        assert hasattr(context, 'direction')
        assert hasattr(context, 'script')


class TestLanguageMappings:
    """Test language mapping dictionaries"""
    
    def test_language_families_mapping(self):
        """Test LANGUAGE_FAMILIES mapping"""
        # Test Germanic languages
        assert LANGUAGE_FAMILIES['en'] == LanguageFamily.GERMANIC
        assert LANGUAGE_FAMILIES['de'] == LanguageFamily.GERMANIC
        assert LANGUAGE_FAMILIES['nl'] == LanguageFamily.GERMANIC
        
        # Test Romance languages
        assert LANGUAGE_FAMILIES['es'] == LanguageFamily.ROMANCE
        assert LANGUAGE_FAMILIES['fr'] == LanguageFamily.ROMANCE
        assert LANGUAGE_FAMILIES['it'] == LanguageFamily.ROMANCE
        
        # Test Slavic languages
        assert LANGUAGE_FAMILIES['ru'] == LanguageFamily.SLAVIC
        assert LANGUAGE_FAMILIES['pl'] == LanguageFamily.SLAVIC
        
        # Test special languages
        assert LANGUAGE_FAMILIES['ja'] == LanguageFamily.JAPONIC
        assert LANGUAGE_FAMILIES['ko'] == LanguageFamily.KOREANIC
    
    def test_rtl_languages_set(self):
        """Test RTL_LANGUAGES set"""
        assert 'ar' in RTL_LANGUAGES
        assert 'he' in RTL_LANGUAGES
        assert 'fa' in RTL_LANGUAGES
        assert 'ur' in RTL_LANGUAGES
        assert 'en' not in RTL_LANGUAGES
        assert 'es' not in RTL_LANGUAGES
    
    def test_language_scripts_mapping(self):
        """Test LANGUAGE_SCRIPTS mapping"""
        # Test Latin scripts
        assert LANGUAGE_SCRIPTS['en'] == 'latin'
        assert LANGUAGE_SCRIPTS['es'] == 'latin'
        assert LANGUAGE_SCRIPTS['fr'] == 'latin'
        
        # Test other scripts
        assert LANGUAGE_SCRIPTS['ru'] == 'cyrillic'
        assert LANGUAGE_SCRIPTS['ar'] == 'arabic'
        assert LANGUAGE_SCRIPTS['zh-cn'] == 'chinese'
        assert LANGUAGE_SCRIPTS['ja'] == 'japanese'
        assert LANGUAGE_SCRIPTS['ko'] == 'korean'


class TestGetLanguageContext:
    """Test get_language_context function"""
    
    @patch('utils.language_utils.detect_text_language')
    @patch('utils.language_utils.get_language_display_name')
    def test_get_language_context_english(self, mock_display_name, mock_detect):
        """Test get_language_context for English text"""
        mock_detect.return_value = ('en', 0.95, True)
        mock_display_name.return_value = 'English'
        
        result = get_language_context("Hello world")
        
        assert isinstance(result, LanguageContext)
        assert result.language_code == 'en'
        assert result.language_name == 'English'
        assert result.confidence == 0.95
        assert result.is_reliable is True
        assert result.family == LanguageFamily.GERMANIC
        assert result.direction == 'ltr'
        assert result.script == 'latin'
    
    @patch('utils.language_utils.detect_text_language')
    @patch('utils.language_utils.get_language_display_name')
    def test_get_language_context_arabic(self, mock_display_name, mock_detect):
        """Test get_language_context for Arabic text"""
        mock_detect.return_value = ('ar', 0.9, True)
        mock_display_name.return_value = 'Arabic'
        
        result = get_language_context("مرحبا بالعالم")
        
        assert result.language_code == 'ar'
        assert result.language_name == 'Arabic'
        assert result.family == LanguageFamily.AFROASIATIC
        assert result.direction == 'rtl'
        assert result.script == 'arabic'
    
    @patch('utils.language_utils.detect_text_language')
    @patch('utils.language_utils.get_language_display_name')
    def test_get_language_context_unknown_language(self, mock_display_name, mock_detect):
        """Test get_language_context for unknown language"""
        mock_detect.return_value = ('unknown', 0.3, False)
        mock_display_name.return_value = 'Unknown'
        
        result = get_language_context("xyz abc 123")
        
        assert result.language_code == 'unknown'
        assert result.family == LanguageFamily.OTHER
        assert result.direction == 'ltr'  # Default
        assert result.script == 'latin'   # Default


class TestIsTextMixedLanguage:
    """Test is_text_mixed_language function"""
    
    def test_empty_text(self):
        """Test is_text_mixed_language with empty text"""
        assert is_text_mixed_language("") is False
        assert is_text_mixed_language("   ") is False
        assert is_text_mixed_language(None) is False
    
    def test_short_text(self):
        """Test is_text_mixed_language with short text"""
        assert is_text_mixed_language("Hello") is False
    
    @patch('utils.language_utils._detect_multiple_languages')
    def test_mixed_language_detected(self, mock_detect_multiple):
        """Test mixed language detection"""
        # Mock multiple language detection
        mock_detection = Mock()
        mock_detection.all_languages = [
            Mock(confidence=0.6),
            Mock(confidence=0.5)
        ]
        mock_detect_multiple.return_value = mock_detection
        
        result = is_text_mixed_language("Hello world and Hola mundo", threshold=0.3)
        assert result is True
    
    @patch('utils.language_utils._detect_multiple_languages')
    def test_single_language_detected(self, mock_detect_multiple):
        """Test single language detection"""
        mock_detection = Mock()
        mock_detection.all_languages = [
            Mock(confidence=0.9),
            Mock(confidence=0.1)
        ]
        mock_detect_multiple.return_value = mock_detection
        
        result = is_text_mixed_language("Hello world this is English", threshold=0.3)
        assert result is False
    
    @patch('utils.language_utils._detect_multiple_languages')
    def test_detection_error_handling(self, mock_detect_multiple):
        """Test error handling in mixed language detection"""
        mock_detect_multiple.side_effect = Exception("Detection error")
        
        result = is_text_mixed_language("Some text that causes error")
        assert result is False


class TestNormalizeTextForLanguage:
    """Test normalize_text_for_language function"""
    
    def test_empty_text(self):
        """Test normalization with empty text"""
        assert normalize_text_for_language("", "en") == ""
        assert normalize_text_for_language(None, "en") is None
    
    def test_basic_normalization(self):
        """Test basic text normalization"""
        text = "  Hello   world  "
        result = normalize_text_for_language(text, "en")
        assert result == "Hello world"
    
    def test_arabic_normalization(self):
        """Test Arabic text normalization"""
        # Arabic text with diacritics
        text = "مَرْحَبًا"
        result = normalize_text_for_language(text, "ar")
        # Should remove diacritics
        assert "َ" not in result
        assert "ْ" not in result
        assert "ً" not in result
    
    def test_chinese_normalization(self):
        """Test Chinese text normalization"""
        text = "你好，世界！"
        result = normalize_text_for_language(text, "zh-cn")
        assert "," in result  # Chinese comma normalized to ASCII
        assert "." in result  # Chinese period normalized to ASCII
    
    def test_japanese_normalization(self):
        """Test Japanese text normalization"""
        text = "こんにちは、世界。"
        result = normalize_text_for_language(text, "ja")
        assert "," in result
        assert "." in result
    
    def test_whitespace_normalization(self):
        """Test whitespace normalization for all languages"""
        text = "Hello\u00A0\u00A0world\t\t\ntest"
        result = normalize_text_for_language(text, "en")
        assert "\u00A0" not in result  # Non-breaking space removed
        assert result == "Hello world test"


class TestSplitTextBySentences:
    """Test split_text_by_sentences function"""
    
    def test_empty_text(self):
        """Test sentence splitting with empty text"""
        assert split_text_by_sentences("", "en") == []
        assert split_text_by_sentences(None, "en") == []
    
    def test_english_sentences(self):
        """Test English sentence splitting"""
        text = "Hello world. How are you? I am fine!"
        result = split_text_by_sentences(text, "en")
        assert len(result) == 3
        assert "Hello world" in result[0]
        assert "How are you" in result[1]
        assert "I am fine" in result[2]
    
    def test_chinese_sentences(self):
        """Test Chinese sentence splitting"""
        text = "你好。世界！怎么样？"
        result = split_text_by_sentences(text, "zh-cn")
        assert len(result) == 3
    
    def test_japanese_sentences(self):
        """Test Japanese sentence splitting"""
        text = "こんにちは。世界！元気？"
        result = split_text_by_sentences(text, "ja")
        assert len(result) == 3
    
    def test_arabic_sentences(self):
        """Test Arabic sentence splitting"""
        text = "مرحبا. كيف حالك؟ أنا بخير."
        result = split_text_by_sentences(text, "ar")
        assert len(result) == 3


class TestGetWordCount:
    """Test get_word_count function"""
    
    def test_empty_text(self):
        """Test word count with empty text"""
        assert get_word_count("", "en") == 0
        assert get_word_count(None, "en") == 0
    
    def test_english_word_count(self):
        """Test English word count"""
        text = "Hello world how are you"
        result = get_word_count(text, "en")
        assert result == 5
    
    def test_chinese_character_count(self):
        """Test Chinese character count"""
        text = "你好世界"
        result = get_word_count(text, "zh-cn")
        assert result == 4  # Character count for Chinese
    
    def test_japanese_character_count(self):
        """Test Japanese character count"""
        text = "こんにちは"
        result = get_word_count(text, "ja")
        assert result == 5  # Character count for Japanese
    
    def test_korean_word_count(self):
        """Test Korean word count"""
        text = "안녕하세요 세계"
        result = get_word_count(text, "ko")
        assert result == 2  # Space-based count for Korean


class TestEstimateReadingTime:
    """Test estimate_reading_time function"""
    
    def test_empty_text(self):
        """Test reading time estimation with empty text"""
        assert estimate_reading_time("", "en") == 0
        assert estimate_reading_time(None, "en") == 0
    
    def test_english_reading_time(self):
        """Test English reading time estimation"""
        # 200 words at 200 wpm = 1 minute
        text = " ".join(["word"] * 200)
        result = estimate_reading_time(text, "en")
        assert result == 1
    
    def test_chinese_reading_time(self):
        """Test Chinese reading time estimation"""
        # 250 characters at 250 cpm = 1 minute
        text = "你" * 250
        result = estimate_reading_time(text, "zh-cn")
        assert result == 1
    
    def test_minimum_reading_time(self):
        """Test minimum reading time is 1 minute"""
        text = "short"
        result = estimate_reading_time(text, "en")
        assert result == 1  # Minimum is 1 minute
    
    def test_unknown_language_default(self):
        """Test default reading speed for unknown languages"""
        text = " ".join(["word"] * 180)  # Default 180 wpm
        result = estimate_reading_time(text, "unknown")
        assert result == 1


class TestIsFormalLanguageContext:
    """Test is_formal_language_context function"""
    
    def test_empty_text(self):
        """Test formal language detection with empty text"""
        assert is_formal_language_context("", "en") is False
        assert is_formal_language_context(None, "en") is False
    
    def test_english_formal_text(self):
        """Test English formal language detection"""
        text = "Dear Sir, please kindly consider this request. Respectfully yours."
        result = is_formal_language_context(text, "en")
        assert result is True
    
    def test_english_informal_text(self):
        """Test English informal language detection"""
        text = "Hey there! How's it going? Talk to you later."
        result = is_formal_language_context(text, "en")
        assert result is False
    
    def test_spanish_formal_text(self):
        """Test Spanish formal language detection"""
        text = "Estimado señor, por favor considere usted esta solicitud."
        result = is_formal_language_context(text, "es")
        assert result is True
    
    def test_unknown_language_indicators(self):
        """Test formal detection with unknown language"""
        text = "Some formal text"
        result = is_formal_language_context(text, "unknown")
        assert result is False  # No indicators for unknown language


class TestPrepareTextForTranslation:
    """Test prepare_text_for_translation function"""
    
    def test_empty_text(self):
        """Test translation preparation with empty text"""
        result = prepare_text_for_translation("", "en", "es")
        
        assert result["prepared_text"] == ""
        assert result["source_context"] is None
        assert result["target_context"] is None
        assert result["translation_notes"] == []
    
    @patch('utils.language_utils.get_language_context')
    @patch('utils.language_utils.get_language_display_name')
    @patch('utils.language_utils.normalize_text_for_language')
    @patch('utils.language_utils.is_formal_language_context')
    def test_basic_translation_preparation(self, mock_formal, mock_normalize, mock_display, mock_context):
        """Test basic translation preparation"""
        # Mock dependencies
        mock_context.return_value = LanguageContext(
            "en", "English", 0.95, True, LanguageFamily.GERMANIC, "ltr", "latin"
        )
        mock_display.return_value = "Spanish"
        mock_normalize.return_value = "Hello world"
        mock_formal.return_value = False
        
        result = prepare_text_for_translation("Hello world", "en", "es")
        
        assert result["prepared_text"] == "Hello world"
        assert result["source_context"] is not None
        assert result["target_context"] is not None
        assert result["target_context"].language_code == "es"
        assert result["estimated_complexity"] in ["low", "medium", "high"]
    
    @patch('utils.language_utils.get_language_context')
    @patch('utils.language_utils.get_language_display_name')
    @patch('utils.language_utils.normalize_text_for_language')
    @patch('utils.language_utils.is_formal_language_context')
    def test_direction_change_notes(self, mock_formal, mock_normalize, mock_display, mock_context):
        """Test translation notes for direction changes"""
        # English to Arabic (LTR to RTL)
        mock_context.return_value = LanguageContext(
            "en", "English", 0.95, True, LanguageFamily.GERMANIC, "ltr", "latin"
        )
        mock_display.return_value = "Arabic"
        mock_normalize.return_value = "Hello world"
        mock_formal.return_value = False
        
        result = prepare_text_for_translation("Hello world", "en", "ar")
        
        notes = result["translation_notes"]
        assert any("direction change" in note.lower() for note in notes)
        assert any("script change" in note.lower() for note in notes)
    
    @patch('utils.language_utils.get_language_context')
    @patch('utils.language_utils.get_language_display_name')
    @patch('utils.language_utils.normalize_text_for_language')
    @patch('utils.language_utils.is_formal_language_context')
    def test_formal_context_notes(self, mock_formal, mock_normalize, mock_display, mock_context):
        """Test translation notes for formal context"""
        mock_context.return_value = LanguageContext(
            "en", "English", 0.95, True, LanguageFamily.GERMANIC, "ltr", "latin"
        )
        mock_display.return_value = "Spanish"
        mock_normalize.return_value = "Dear Sir"
        mock_formal.return_value = True  # Formal context detected
        
        result = prepare_text_for_translation("Dear Sir", "en", "es")
        
        notes = result["translation_notes"]
        assert any("formal" in note.lower() for note in notes)


class TestValidateLanguageConsistency:
    """Test validate_language_consistency function"""
    
    def test_empty_texts(self):
        """Test validation with empty text list"""
        result = validate_language_consistency([], "en")
        
        assert result["is_consistent"] is True
        assert result["consistency_score"] == 1.0
        assert result["inconsistent_texts"] == []
        assert result["detected_languages"] == {}
    
    @patch('utils.language_utils.detect_text_language')
    def test_consistent_texts(self, mock_detect):
        """Test validation with consistent language texts"""
        mock_detect.return_value = ("en", 0.95, True)
        
        texts = ["Hello world", "How are you", "I am fine"]
        result = validate_language_consistency(texts, "en")
        
        assert result["is_consistent"] is True
        assert result["consistency_score"] == 1.0
        assert len(result["inconsistent_texts"]) == 0
        assert result["detected_languages"]["en"] == 3
    
    @patch('utils.language_utils.detect_text_language')
    def test_inconsistent_texts(self, mock_detect):
        """Test validation with inconsistent language texts"""
        # Mock different languages for different texts
        def mock_detect_side_effect(text):
            if "Hello" in text:
                return ("en", 0.95, True)
            elif "Hola" in text:
                return ("es", 0.90, True)
            else:
                return ("en", 0.95, True)
        
        mock_detect.side_effect = mock_detect_side_effect
        
        texts = ["Hello world", "Hola mundo", "How are you"]
        result = validate_language_consistency(texts, "en")
        
        assert result["is_consistent"] is False
        assert result["consistency_score"] < 1.0
        assert len(result["inconsistent_texts"]) > 0
        assert result["detected_languages"]["en"] == 2
        assert result["detected_languages"]["es"] == 1
    
    def test_empty_and_whitespace_texts(self):
        """Test validation ignoring empty and whitespace-only texts"""
        with patch('utils.language_utils.detect_text_language') as mock_detect:
            mock_detect.return_value = ("en", 0.95, True)
            
            texts = ["Hello world", "", "   ", "How are you"]
            result = validate_language_consistency(texts, "en")
            
            # Should only analyze 2 non-empty texts
            assert result["total_texts_analyzed"] == 2
            assert result["is_consistent"] is True


# Integration tests
class TestLanguageUtilsIntegration:
    """Integration tests for language utils functions"""
    
    @patch('utils.language_utils.detect_text_language')
    @patch('utils.language_utils.get_language_display_name')
    def test_end_to_end_language_processing(self, mock_display, mock_detect):
        """Test end-to-end language processing workflow"""
        mock_detect.return_value = ("en", 0.95, True)
        mock_display.return_value = "English"
        
        text = "Hello world. How are you today? I hope you are doing well!"
        
        # Get language context
        context = get_language_context(text)
        assert context.language_code == "en"
        
        # Normalize text
        normalized = normalize_text_for_language(text, context.language_code)
        assert normalized.strip() == text.strip()
        
        # Split into sentences
        sentences = split_text_by_sentences(text, context.language_code)
        assert len(sentences) == 3
        
        # Get word count
        word_count = get_word_count(text, context.language_code)
        assert word_count > 0
        
        # Estimate reading time
        reading_time = estimate_reading_time(text, context.language_code)
        assert reading_time >= 1
        
        # Check formality
        is_formal = is_formal_language_context(text, context.language_code)
        assert isinstance(is_formal, bool)


if __name__ == "__main__":
    pytest.main([__file__, "-v", "--tb=short"])
