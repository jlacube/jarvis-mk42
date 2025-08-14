"""
Comprehensive Tests for Language Utils Module (Mocked Dependencies)

This test suite provides complete coverage for the utils.language_utils module,
testing all language processing utilities with mocked dependencies to avoid
configuration issues.
"""

import pytest
from unittest.mock import patch, Mock, MagicMock
from typing import Dict, List, Any
import sys
import os

# Add project root to path
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))


class TestLanguageUtilsConstants:
    """Test constants and mappings without imports"""
    
    def test_language_family_enum_exists(self):
        """Test that we can import LanguageFamily enum"""
        # Mock the problematic dependencies first
        with patch.dict('sys.modules', {
            'config.settings': MagicMock(),
            'utils.logging_config': MagicMock(),
            'tools.language_detection': MagicMock()
        }):
            from utils.language_utils import LanguageFamily
            
            # Test enum values
            assert LanguageFamily.GERMANIC.value == "germanic"
            assert LanguageFamily.ROMANCE.value == "romance"
            assert LanguageFamily.SLAVIC.value == "slavic"
            assert LanguageFamily.SINO_TIBETAN.value == "sino_tibetan"
            assert LanguageFamily.AFROASIATIC.value == "afroasiatic"
            assert LanguageFamily.INDO_ARYAN.value == "indo_aryan"
            assert LanguageFamily.JAPONIC.value == "japonic"
            assert LanguageFamily.KOREANIC.value == "koreanic"
            assert LanguageFamily.OTHER.value == "other"
    
    def test_language_context_dataclass(self):
        """Test LanguageContext dataclass creation"""
        with patch.dict('sys.modules', {
            'config.settings': MagicMock(),
            'utils.logging_config': MagicMock(),
            'tools.language_detection': MagicMock()
        }):
            from utils.language_utils import LanguageContext, LanguageFamily
            
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
    
    def test_language_mappings(self):
        """Test language mapping dictionaries"""
        with patch.dict('sys.modules', {
            'config.settings': MagicMock(),
            'utils.logging_config': MagicMock(),
            'tools.language_detection': MagicMock()
        }):
            from utils.language_utils import (
                LANGUAGE_FAMILIES, RTL_LANGUAGES, LANGUAGE_SCRIPTS, LanguageFamily
            )
            
            # Test Germanic languages
            assert LANGUAGE_FAMILIES['en'] == LanguageFamily.GERMANIC
            assert LANGUAGE_FAMILIES['de'] == LanguageFamily.GERMANIC
            
            # Test Romance languages
            assert LANGUAGE_FAMILIES['es'] == LanguageFamily.ROMANCE
            assert LANGUAGE_FAMILIES['fr'] == LanguageFamily.ROMANCE
            
            # Test RTL languages
            assert 'ar' in RTL_LANGUAGES
            assert 'he' in RTL_LANGUAGES
            assert 'en' not in RTL_LANGUAGES
            
            # Test scripts
            assert LANGUAGE_SCRIPTS['en'] == 'latin'
            assert LANGUAGE_SCRIPTS['ar'] == 'arabic'
            assert LANGUAGE_SCRIPTS['zh-cn'] == 'chinese'


class TestLanguageUtilsFunctions:
    """Test language utility functions with mocked dependencies"""
    
    def test_get_language_context(self):
        """Test get_language_context function"""
        with patch.dict('sys.modules', {
            'config.settings': MagicMock(),
            'utils.logging_config': MagicMock(),
            'tools.language_detection': MagicMock()
        }):
            # Mock the language detection functions
            mock_detect = MagicMock(return_value=('en', 0.95, True))
            mock_display = MagicMock(return_value='English')
            
            with patch('utils.language_utils.detect_text_language', mock_detect):
                with patch('utils.language_utils.get_language_display_name', mock_display):
                    from utils.language_utils import get_language_context, LanguageFamily
                    
                    result = get_language_context("Hello world")
                    
                    assert result.language_code == 'en'
                    assert result.language_name == 'English'
                    assert result.confidence == 0.95
                    assert result.is_reliable is True
                    assert result.family == LanguageFamily.GERMANIC
                    assert result.direction == 'ltr'
                    assert result.script == 'latin'
    
    def test_get_language_context_arabic(self):
        """Test get_language_context for RTL language"""
        with patch.dict('sys.modules', {
            'config.settings': MagicMock(),
            'utils.logging_config': MagicMock(),
            'tools.language_detection': MagicMock()
        }):
            mock_detect = MagicMock(return_value=('ar', 0.9, True))
            mock_display = MagicMock(return_value='Arabic')
            
            with patch('utils.language_utils.detect_text_language', mock_detect):
                with patch('utils.language_utils.get_language_display_name', mock_display):
                    from utils.language_utils import get_language_context, LanguageFamily
                    
                    result = get_language_context("مرحبا")
                    
                    assert result.language_code == 'ar'
                    assert result.family == LanguageFamily.AFROASIATIC
                    assert result.direction == 'rtl'
                    assert result.script == 'arabic'
    
    def test_get_language_context_unknown(self):
        """Test get_language_context for unknown language"""
        with patch.dict('sys.modules', {
            'config.settings': MagicMock(),
            'utils.logging_config': MagicMock(),
            'tools.language_detection': MagicMock()
        }):
            mock_detect = MagicMock(return_value=('unknown', 0.3, False))
            mock_display = MagicMock(return_value='Unknown')
            
            with patch('utils.language_utils.detect_text_language', mock_detect):
                with patch('utils.language_utils.get_language_display_name', mock_display):
                    from utils.language_utils import get_language_context, LanguageFamily
                    
                    result = get_language_context("xyz abc")
                    
                    assert result.language_code == 'unknown'
                    assert result.family == LanguageFamily.OTHER
                    assert result.direction == 'ltr'  # Default
                    assert result.script == 'latin'   # Default
    
    def test_is_text_mixed_language_empty(self):
        """Test is_text_mixed_language with empty text"""
        with patch.dict('sys.modules', {
            'config.settings': MagicMock(),
            'utils.logging_config': MagicMock(),
            'tools.language_detection': MagicMock()
        }):
            from utils.language_utils import is_text_mixed_language
            
            assert is_text_mixed_language("") is False
            assert is_text_mixed_language("   ") is False
            assert is_text_mixed_language(None) is False
    
    def test_is_text_mixed_language_short(self):
        """Test is_text_mixed_language with short text"""
        with patch.dict('sys.modules', {
            'config.settings': MagicMock(),
            'utils.logging_config': MagicMock(),
            'tools.language_detection': MagicMock()
        }):
            from utils.language_utils import is_text_mixed_language
            
            assert is_text_mixed_language("Hello") is False
    
    def test_is_text_mixed_language_detected(self):
        """Test mixed language detection"""
        with patch.dict('sys.modules', {
            'config.settings': MagicMock(),
            'utils.logging_config': MagicMock(),
            'tools.language_detection': MagicMock()
        }):
            # Mock the _detect_multiple_languages function
            mock_detection = Mock()
            mock_detection.all_languages = [
                Mock(confidence=0.6),
                Mock(confidence=0.5)
            ]
            
            with patch('tools.language_detection._detect_multiple_languages', return_value=mock_detection):
                from utils.language_utils import is_text_mixed_language
                
                result = is_text_mixed_language("Hello world and Hola mundo", threshold=0.3)
                assert result is True
    
    def test_is_text_mixed_language_single(self):
        """Test single language detection"""
        with patch.dict('sys.modules', {
            'config.settings': MagicMock(),
            'utils.logging_config': MagicMock(),
            'tools.language_detection': MagicMock()
        }):
            mock_detection = Mock()
            mock_detection.all_languages = [
                Mock(confidence=0.9),
                Mock(confidence=0.1)
            ]
            
            with patch('tools.language_detection._detect_multiple_languages', return_value=mock_detection):
                from utils.language_utils import is_text_mixed_language
                
                result = is_text_mixed_language("Hello world this is English", threshold=0.3)
                assert result is False
    
    def test_is_text_mixed_language_single_language_detected(self):
        """Test mixed language detection with only one language detected"""
        with patch.dict('sys.modules', {
            'config.settings': MagicMock(),
            'utils.logging_config': MagicMock(),
            'tools.language_detection': MagicMock()
        }):
            mock_detection = Mock()
            mock_detection.all_languages = [
                Mock(confidence=0.9)  # Only one language detected
            ]
            
            with patch('tools.language_detection._detect_multiple_languages', return_value=mock_detection):
                from utils.language_utils import is_text_mixed_language
                
                result = is_text_mixed_language("Hello world this is English")
                assert result is False
    
    def test_normalize_text_for_language_indic(self):
        """Test Indic languages text normalization"""
        with patch.dict('sys.modules', {
            'config.settings': MagicMock(),
            'utils.logging_config': MagicMock(),
            'tools.language_detection': MagicMock()
        }):
            from utils.language_utils import normalize_text_for_language
            
            # Test Hindi text with potential diacritics
            text = "नमस्ते दुनिया"
            result = normalize_text_for_language(text, "hi")
            assert isinstance(result, str)
            assert result.strip() == text.strip()  # Basic normalization
            
            # Test Bengali
            text = "হ্যালো পৃথিবী"
            result = normalize_text_for_language(text, "bn")
            assert isinstance(result, str)
            
            # Test other Indic languages
            for lang in ['gu', 'pa', 'mr', 'ne']:
                result = normalize_text_for_language("test text", lang)
                assert isinstance(result, str)
    
    def test_normalize_text_for_language_empty(self):
        """Test normalization with empty text"""
        with patch.dict('sys.modules', {
            'config.settings': MagicMock(),
            'utils.logging_config': MagicMock(),
            'tools.language_detection': MagicMock()
        }):
            from utils.language_utils import normalize_text_for_language
            
            assert normalize_text_for_language("", "en") == ""
            assert normalize_text_for_language(None, "en") is None
    
    def test_normalize_text_for_language_basic(self):
        """Test basic text normalization"""
        with patch.dict('sys.modules', {
            'config.settings': MagicMock(),
            'utils.logging_config': MagicMock(),
            'tools.language_detection': MagicMock()
        }):
            from utils.language_utils import normalize_text_for_language
            
            text = "  Hello   world  "
            result = normalize_text_for_language(text, "en")
            assert result == "Hello world"
    
    def test_normalize_text_for_language_arabic(self):
        """Test Arabic text normalization (diacritics removal)"""
        with patch.dict('sys.modules', {
            'config.settings': MagicMock(),
            'utils.logging_config': MagicMock(),
            'tools.language_detection': MagicMock()
        }):
            from utils.language_utils import normalize_text_for_language
            
            # Arabic text with diacritics
            text = "مَرْحَبًا"
            result = normalize_text_for_language(text, "ar")
            # Should remove diacritics
            assert "َ" not in result
            assert "ْ" not in result
            assert "ً" not in result
    
    def test_normalize_text_for_language_chinese(self):
        """Test Chinese text normalization"""
        with patch.dict('sys.modules', {
            'config.settings': MagicMock(),
            'utils.logging_config': MagicMock(),
            'tools.language_detection': MagicMock()
        }):
            from utils.language_utils import normalize_text_for_language
            
            text = "你好，世界！"
            result = normalize_text_for_language(text, "zh-cn")
            assert "," in result  # Chinese comma normalized to ASCII
            assert "!" in result  # Chinese exclamation normalized to ASCII
    
    def test_normalize_text_for_language_japanese(self):
        """Test Japanese text normalization"""
        with patch.dict('sys.modules', {
            'config.settings': MagicMock(),
            'utils.logging_config': MagicMock(),
            'tools.language_detection': MagicMock()
        }):
            from utils.language_utils import normalize_text_for_language
            
            text = "こんにちは、世界。"
            result = normalize_text_for_language(text, "ja")
            assert "," in result
            assert "." in result
    
    def test_normalize_text_whitespace(self):
        """Test whitespace normalization"""
        with patch.dict('sys.modules', {
            'config.settings': MagicMock(),
            'utils.logging_config': MagicMock(),
            'tools.language_detection': MagicMock()
        }):
            from utils.language_utils import normalize_text_for_language
            
            text = "Hello\u00A0\u00A0world\t\t\ntest"
            result = normalize_text_for_language(text, "en")
            assert "\u00A0" not in result  # Non-breaking space removed
            assert result == "Hello world test"
    
    def test_split_text_by_sentences_empty(self):
        """Test sentence splitting with empty text"""
        with patch.dict('sys.modules', {
            'config.settings': MagicMock(),
            'utils.logging_config': MagicMock(),
            'tools.language_detection': MagicMock()
        }):
            from utils.language_utils import split_text_by_sentences
            
            assert split_text_by_sentences("", "en") == []
            assert split_text_by_sentences(None, "en") == []
    
    def test_split_text_by_sentences_english(self):
        """Test English sentence splitting"""
        with patch.dict('sys.modules', {
            'config.settings': MagicMock(),
            'utils.logging_config': MagicMock(),
            'tools.language_detection': MagicMock()
        }):
            from utils.language_utils import split_text_by_sentences
            
            text = "Hello world. How are you? I am fine!"
            result = split_text_by_sentences(text, "en")
            assert len(result) == 3
            assert "Hello world" in result[0]
    
    def test_split_text_by_sentences_chinese(self):
        """Test Chinese sentence splitting"""
        with patch.dict('sys.modules', {
            'config.settings': MagicMock(),
            'utils.logging_config': MagicMock(),
            'tools.language_detection': MagicMock()
        }):
            from utils.language_utils import split_text_by_sentences
            
            text = "你好。世界！怎么样？"
            result = split_text_by_sentences(text, "zh-cn")
            assert len(result) == 3
    
    def test_split_text_by_sentences_japanese(self):
        """Test Japanese sentence splitting"""
        with patch.dict('sys.modules', {
            'config.settings': MagicMock(),
            'utils.logging_config': MagicMock(),
            'tools.language_detection': MagicMock()
        }):
            from utils.language_utils import split_text_by_sentences
            
            text = "こんにちは。世界！元気？"
            result = split_text_by_sentences(text, "ja")
            assert len(result) == 3
    
    def test_split_text_by_sentences_arabic(self):
        """Test Arabic sentence splitting"""
        with patch.dict('sys.modules', {
            'config.settings': MagicMock(),
            'utils.logging_config': MagicMock(),
            'tools.language_detection': MagicMock()
        }):
            from utils.language_utils import split_text_by_sentences
            
            text = "مرحبا. كيف حالك؟ أنا بخير."
            result = split_text_by_sentences(text, "ar")
            assert len(result) == 3
    
    def test_get_word_count_empty(self):
        """Test word count with empty text"""
        with patch.dict('sys.modules', {
            'config.settings': MagicMock(),
            'utils.logging_config': MagicMock(),
            'tools.language_detection': MagicMock()
        }):
            from utils.language_utils import get_word_count
            
            assert get_word_count("", "en") == 0
            assert get_word_count(None, "en") == 0
    
    def test_get_word_count_english(self):
        """Test English word count"""
        with patch.dict('sys.modules', {
            'config.settings': MagicMock(),
            'utils.logging_config': MagicMock(),
            'tools.language_detection': MagicMock()
        }):
            with patch('utils.language_utils.normalize_text_for_language', return_value="Hello world how are you"):
                from utils.language_utils import get_word_count
                
                result = get_word_count("Hello world how are you", "en")
                assert result == 5
    
    def test_get_word_count_chinese(self):
        """Test Chinese character count"""
        with patch.dict('sys.modules', {
            'config.settings': MagicMock(),
            'utils.logging_config': MagicMock(),
            'tools.language_detection': MagicMock()
        }):
            with patch('utils.language_utils.normalize_text_for_language', return_value="你好世界"):
                from utils.language_utils import get_word_count
                
                result = get_word_count("你好世界", "zh-cn")
                assert result == 4  # Character count for Chinese
    
    def test_get_word_count_japanese(self):
        """Test Japanese character count"""
        with patch.dict('sys.modules', {
            'config.settings': MagicMock(),
            'utils.logging_config': MagicMock(),
            'tools.language_detection': MagicMock()
        }):
            with patch('utils.language_utils.normalize_text_for_language', return_value="こんにちは"):
                from utils.language_utils import get_word_count
                
                result = get_word_count("こんにちは", "ja")
                assert result == 5  # Character count for Japanese
    
    def test_get_word_count_korean(self):
        """Test Korean word count"""
        with patch.dict('sys.modules', {
            'config.settings': MagicMock(),
            'utils.logging_config': MagicMock(),
            'tools.language_detection': MagicMock()
        }):
            with patch('utils.language_utils.normalize_text_for_language', return_value="안녕하세요 세계"):
                from utils.language_utils import get_word_count
                
                result = get_word_count("안녕하세요 세계", "ko")
                assert result == 2  # Space-based count for Korean
    
    def test_estimate_reading_time_empty(self):
        """Test reading time estimation with empty text"""
        with patch.dict('sys.modules', {
            'config.settings': MagicMock(),
            'utils.logging_config': MagicMock(),
            'tools.language_detection': MagicMock()
        }):
            from utils.language_utils import estimate_reading_time
            
            assert estimate_reading_time("", "en") == 0
            assert estimate_reading_time(None, "en") == 0
    
    def test_estimate_reading_time_english(self):
        """Test English reading time estimation"""
        with patch.dict('sys.modules', {
            'config.settings': MagicMock(),
            'utils.logging_config': MagicMock(),
            'tools.language_detection': MagicMock()
        }):
            with patch('utils.language_utils.get_word_count', return_value=200):
                from utils.language_utils import estimate_reading_time
                
                result = estimate_reading_time("dummy text", "en")
                assert result == 1  # 200 words at 200 wpm = 1 minute
    
    def test_estimate_reading_time_minimum(self):
        """Test minimum reading time is 1 minute"""
        with patch.dict('sys.modules', {
            'config.settings': MagicMock(),
            'utils.logging_config': MagicMock(),
            'tools.language_detection': MagicMock()
        }):
            with patch('utils.language_utils.get_word_count', return_value=5):
                from utils.language_utils import estimate_reading_time
                
                result = estimate_reading_time("short", "en")
                assert result == 1  # Minimum is 1 minute
    
    def test_estimate_reading_time_unknown_language(self):
        """Test default reading speed for unknown languages"""
        with patch.dict('sys.modules', {
            'config.settings': MagicMock(),
            'utils.logging_config': MagicMock(),
            'tools.language_detection': MagicMock()
        }):
            with patch('utils.language_utils.get_word_count', return_value=180):
                from utils.language_utils import estimate_reading_time
                
                result = estimate_reading_time("dummy text", "unknown")
                assert result == 1  # 180 words at default 180 wpm = 1 minute
    
    def test_is_formal_language_context_empty(self):
        """Test formal language detection with empty text"""
        with patch.dict('sys.modules', {
            'config.settings': MagicMock(),
            'utils.logging_config': MagicMock(),
            'tools.language_detection': MagicMock()
        }):
            from utils.language_utils import is_formal_language_context
            
            assert is_formal_language_context("", "en") is False
            assert is_formal_language_context(None, "en") is False
    
    def test_is_formal_language_context_english_formal(self):
        """Test English formal language detection"""
        with patch.dict('sys.modules', {
            'config.settings': MagicMock(),
            'utils.logging_config': MagicMock(),
            'tools.language_detection': MagicMock()
        }):
            from utils.language_utils import is_formal_language_context
            
            text = "Dear Sir, please kindly consider this request. Respectfully yours."
            result = is_formal_language_context(text, "en")
            assert result is True
    
    def test_is_formal_language_context_english_informal(self):
        """Test English informal language detection"""
        with patch.dict('sys.modules', {
            'config.settings': MagicMock(),
            'utils.logging_config': MagicMock(),
            'tools.language_detection': MagicMock()
        }):
            from utils.language_utils import is_formal_language_context
            
            text = "Hey there! How's it going? Talk to you later."
            result = is_formal_language_context(text, "en")
            assert result is False
    
    def test_is_formal_language_context_spanish(self):
        """Test Spanish formal language detection"""
        with patch.dict('sys.modules', {
            'config.settings': MagicMock(),
            'utils.logging_config': MagicMock(),
            'tools.language_detection': MagicMock()
        }):
            from utils.language_utils import is_formal_language_context
            
            text = "Estimado señor, por favor considere usted esta solicitud."
            result = is_formal_language_context(text, "es")
            assert result is True
    
    def test_is_formal_language_context_unknown(self):
        """Test formal detection with unknown language"""
        with patch.dict('sys.modules', {
            'config.settings': MagicMock(),
            'utils.logging_config': MagicMock(),
            'tools.language_detection': MagicMock()
        }):
            from utils.language_utils import is_formal_language_context
            
            text = "Some formal text"
            result = is_formal_language_context(text, "unknown")
            assert result is False  # No indicators for unknown language
    
    def test_prepare_text_for_translation_empty(self):
        """Test translation preparation with empty text"""
        with patch.dict('sys.modules', {
            'config.settings': MagicMock(),
            'utils.logging_config': MagicMock(),
            'tools.language_detection': MagicMock()
        }):
            from utils.language_utils import prepare_text_for_translation
            
            result = prepare_text_for_translation("", "en", "es")
            
            assert result["prepared_text"] == ""
            assert result["source_context"] is None
            assert result["target_context"] is None
            assert result["translation_notes"] == []
    
    def test_prepare_text_for_translation_basic(self):
        """Test basic translation preparation"""
        with patch.dict('sys.modules', {
            'config.settings': MagicMock(),
            'utils.logging_config': MagicMock(),
            'tools.language_detection': MagicMock()
        }):
            # Mock dependencies
            mock_context = Mock()
            mock_context.direction = "ltr"
            mock_context.script = "latin"
            mock_context.family = Mock()
            mock_context.family.value = "germanic"
            
            with patch('utils.language_utils.get_language_context', return_value=mock_context):
                with patch('utils.language_utils.get_language_display_name', return_value="Spanish"):
                    with patch('utils.language_utils.normalize_text_for_language', return_value="Hello world"):
                        with patch('utils.language_utils.is_formal_language_context', return_value=False):
                            from utils.language_utils import prepare_text_for_translation
                            
                            result = prepare_text_for_translation("Hello world", "en", "es")
                            
                            assert result["prepared_text"] == "Hello world"
                            assert result["source_context"] is not None
                            assert result["target_context"] is not None
                            assert result["estimated_complexity"] in ["low", "medium", "high"]
    
    def test_prepare_text_for_translation_direction_change(self):
        """Test translation notes for direction changes"""
        with patch.dict('sys.modules', {
            'config.settings': MagicMock(),
            'utils.logging_config': MagicMock(),
            'tools.language_detection': MagicMock()
        }):
            # Mock English context (LTR)
            mock_source_context = Mock()
            mock_source_context.direction = "ltr"
            mock_source_context.script = "latin"
            mock_source_context.family = Mock()
            mock_source_context.family.value = "germanic"
            
            with patch('utils.language_utils.get_language_context', return_value=mock_source_context):
                with patch('utils.language_utils.get_language_display_name', return_value="Arabic"):
                    with patch('utils.language_utils.normalize_text_for_language', return_value="Hello world"):
                        with patch('utils.language_utils.is_formal_language_context', return_value=False):
                            from utils.language_utils import prepare_text_for_translation
                            
                            result = prepare_text_for_translation("Hello world", "en", "ar")
                            
                            notes = result["translation_notes"]
                            assert any("direction change" in note.lower() for note in notes)
                            assert any("script change" in note.lower() for note in notes)
    
    def test_prepare_text_for_translation_formal(self):
        """Test translation notes for formal context"""
        with patch.dict('sys.modules', {
            'config.settings': MagicMock(),
            'utils.logging_config': MagicMock(),
            'tools.language_detection': MagicMock()
        }):
            mock_context = Mock()
            mock_context.direction = "ltr"
            mock_context.script = "latin"
            mock_context.family = Mock()
            mock_context.family.value = "germanic"
            
            with patch('utils.language_utils.get_language_context', return_value=mock_context):
                with patch('utils.language_utils.get_language_display_name', return_value="Spanish"):
                    with patch('utils.language_utils.normalize_text_for_language', return_value="Dear Sir"):
                        with patch('utils.language_utils.is_formal_language_context', return_value=True):
                            from utils.language_utils import prepare_text_for_translation
                            
                            result = prepare_text_for_translation("Dear Sir", "en", "es")
                            
                            notes = result["translation_notes"]
                            assert any("formal" in note.lower() for note in notes)
    
    def test_validate_language_consistency_empty(self):
        """Test validation with empty text list"""
        with patch.dict('sys.modules', {
            'config.settings': MagicMock(),
            'utils.logging_config': MagicMock(),
            'tools.language_detection': MagicMock()
        }):
            from utils.language_utils import validate_language_consistency
            
            result = validate_language_consistency([], "en")
            
            assert result["is_consistent"] is True
            assert result["consistency_score"] == 1.0
            assert result["inconsistent_texts"] == []
            assert result["detected_languages"] == {}
    
    def test_validate_language_consistency_consistent(self):
        """Test validation with consistent language texts"""
        with patch.dict('sys.modules', {
            'config.settings': MagicMock(),
            'utils.logging_config': MagicMock(),
            'tools.language_detection': MagicMock()
        }):
            with patch('utils.language_utils.detect_text_language', return_value=("en", 0.95, True)):
                from utils.language_utils import validate_language_consistency
                
                texts = ["Hello world", "How are you", "I am fine"]
                result = validate_language_consistency(texts, "en")
                
                assert result["is_consistent"] is True
                assert result["consistency_score"] == 1.0
                assert len(result["inconsistent_texts"]) == 0
                assert result["detected_languages"]["en"] == 3
    
    def test_validate_language_consistency_inconsistent(self):
        """Test validation with inconsistent language texts"""
        with patch.dict('sys.modules', {
            'config.settings': MagicMock(),
            'utils.logging_config': MagicMock(),
            'tools.language_detection': MagicMock()
        }):
            def mock_detect_side_effect(text):
                if "Hello" in text:
                    return ("en", 0.95, True)
                elif "Hola" in text:
                    return ("es", 0.90, True)
                else:
                    return ("en", 0.95, True)
            
            with patch('utils.language_utils.detect_text_language', side_effect=mock_detect_side_effect):
                from utils.language_utils import validate_language_consistency
                
                texts = ["Hello world", "Hola mundo", "How are you"]
                result = validate_language_consistency(texts, "en")
                
                assert result["is_consistent"] is False
                assert result["consistency_score"] < 1.0
                assert len(result["inconsistent_texts"]) > 0
    
    def test_validate_language_consistency_empty_texts(self):
        """Test validation ignoring empty and whitespace-only texts"""
        with patch.dict('sys.modules', {
            'config.settings': MagicMock(),
            'utils.logging_config': MagicMock(),
            'tools.language_detection': MagicMock()
        }):
            with patch('utils.language_utils.detect_text_language', return_value=("en", 0.95, True)):
                from utils.language_utils import validate_language_consistency
                
                texts = ["Hello world", "", "   ", "How are you"]
                result = validate_language_consistency(texts, "en")
                
                # Should only analyze 2 non-empty texts
                assert result["total_texts_analyzed"] == 2
                assert result["is_consistent"] is True
    
    def test_is_text_mixed_language_single_language_detected(self):
        """Test mixed language detection with only one language detected"""
        with patch.dict('sys.modules', {
            'config.settings': MagicMock(),
            'utils.logging_config': MagicMock(),
            'tools.language_detection': MagicMock()
        }):
            mock_detection = Mock()
            mock_detection.all_languages = [
                Mock(confidence=0.9)  # Only one language detected
            ]
            
            with patch('tools.language_detection._detect_multiple_languages', return_value=mock_detection):
                from utils.language_utils import is_text_mixed_language
                
                result = is_text_mixed_language("Hello world this is English")
                assert result is False
    
    def test_normalize_text_for_language_indic(self):
        """Test Indic languages text normalization"""
        with patch.dict('sys.modules', {
            'config.settings': MagicMock(),
            'utils.logging_config': MagicMock(),
            'tools.language_detection': MagicMock()
        }):
            from utils.language_utils import normalize_text_for_language
            
            # Test Hindi text with potential diacritics
            text = "नमस्ते दुनिया"
            result = normalize_text_for_language(text, "hi")
            assert isinstance(result, str)
            assert result.strip() == text.strip()  # Basic normalization
            
            # Test Bengali
            text = "হ্যালো পৃথিবী"
            result = normalize_text_for_language(text, "bn")
            assert isinstance(result, str)
            
            # Test other Indic languages
            for lang in ['gu', 'pa', 'mr', 'ne']:
                result = normalize_text_for_language("test text", lang)
                assert isinstance(result, str)


if __name__ == "__main__":
    pytest.main([__file__, "-v", "--tb=short"])


class TestLanguageUtilsExceptionPaths:
    """Additional tests for exception paths"""
    
    def test_mixed_language_detection_exception_logging(self):
        """Test that exception logging path is covered"""
        with patch.dict('sys.modules', {
            'config.settings': MagicMock(),
            'utils.logging_config': MagicMock(),
            'tools.language_detection': MagicMock()
        }):
            # Mock the logger to ensure we can track the warning call
            mock_logger = MagicMock()
            
            with patch('utils.language_utils.logger', mock_logger):
                with patch('tools.language_detection._detect_multiple_languages', side_effect=RuntimeError("Runtime error")):
                    from utils.language_utils import is_text_mixed_language
                    
                    # Use text long enough to pass the length check
                    result = is_text_mixed_language("This is definitely a long enough text to trigger the mixed language detection path in the function")
                    
                    assert result is False
                    # Verify that the logger warning was called
                    mock_logger.warning.assert_called_once()
