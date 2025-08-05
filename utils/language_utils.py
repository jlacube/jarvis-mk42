# utils/language_utils.py
"""
Language Processing Utilities
============================

This module provides common language processing utilities for multi-language support
in the Jarvis-MK42 system. It includes functions for language detection, text processing,
and language-aware operations.

Features:
- Language detection integration
- Text preprocessing for multi-language content  
- Language-aware string operations
- Locale and culture support
- Translation preparation utilities
"""

import re
import logging
from typing import Dict, List, Optional, Tuple, Any
from dataclasses import dataclass
from enum import Enum

from tools.language_detection import detect_text_language, is_language_supported, get_language_display_name
from utils.logging_config import get_logger

logger = get_logger(__name__)


class LanguageFamily(Enum):
    """Major language families for processing optimization."""
    GERMANIC = "germanic"      # English, German, Dutch, Swedish, etc.
    ROMANCE = "romance"        # Spanish, French, Italian, Portuguese, etc.
    SLAVIC = "slavic"         # Russian, Polish, Czech, Ukrainian, etc.
    SINO_TIBETAN = "sino_tibetan"  # Chinese, Tibetan, etc.
    AFROASIATIC = "afroasiatic"    # Arabic, Hebrew, etc.
    INDO_ARYAN = "indo_aryan"      # Hindi, Bengali, Urdu, etc.
    JAPONIC = "japonic"            # Japanese
    KOREANIC = "koreanic"          # Korean
    OTHER = "other"


@dataclass
class LanguageContext:
    """Context information for language-aware processing."""
    language_code: str
    language_name: str
    confidence: float
    is_reliable: bool
    family: LanguageFamily
    direction: str  # 'ltr' or 'rtl'
    script: str     # 'latin', 'cyrillic', 'arabic', 'chinese', etc.


# Language family mappings
LANGUAGE_FAMILIES = {
    'en': LanguageFamily.GERMANIC, 'de': LanguageFamily.GERMANIC, 'nl': LanguageFamily.GERMANIC,
    'sv': LanguageFamily.GERMANIC, 'da': LanguageFamily.GERMANIC, 'no': LanguageFamily.GERMANIC,
    
    'es': LanguageFamily.ROMANCE, 'fr': LanguageFamily.ROMANCE, 'it': LanguageFamily.ROMANCE,
    'pt': LanguageFamily.ROMANCE, 'ro': LanguageFamily.ROMANCE, 'ca': LanguageFamily.ROMANCE,
    
    'ru': LanguageFamily.SLAVIC, 'pl': LanguageFamily.SLAVIC, 'cs': LanguageFamily.SLAVIC,
    'sk': LanguageFamily.SLAVIC, 'uk': LanguageFamily.SLAVIC, 'bg': LanguageFamily.SLAVIC,
    'hr': LanguageFamily.SLAVIC, 'sl': LanguageFamily.SLAVIC, 'mk': LanguageFamily.SLAVIC,
    
    'zh-cn': LanguageFamily.SINO_TIBETAN, 'zh-tw': LanguageFamily.SINO_TIBETAN,
    
    'ar': LanguageFamily.AFROASIATIC, 'he': LanguageFamily.AFROASIATIC,
    
    'hi': LanguageFamily.INDO_ARYAN, 'bn': LanguageFamily.INDO_ARYAN, 'ur': LanguageFamily.INDO_ARYAN,
    'gu': LanguageFamily.INDO_ARYAN, 'pa': LanguageFamily.INDO_ARYAN, 'mr': LanguageFamily.INDO_ARYAN,
    'ne': LanguageFamily.INDO_ARYAN,
    
    'ja': LanguageFamily.JAPONIC,
    'ko': LanguageFamily.KOREANIC,
}

# Text direction mappings
RTL_LANGUAGES = {'ar', 'he', 'fa', 'ur'}  # Right-to-left languages

# Script mappings
LANGUAGE_SCRIPTS = {
    'en': 'latin', 'es': 'latin', 'fr': 'latin', 'de': 'latin', 'it': 'latin', 'pt': 'latin',
    'nl': 'latin', 'sv': 'latin', 'da': 'latin', 'no': 'latin', 'fi': 'latin', 'et': 'latin',
    'lv': 'latin', 'lt': 'latin', 'pl': 'latin', 'cs': 'latin', 'sk': 'latin', 'sl': 'latin',
    'hr': 'latin', 'hu': 'latin', 'ro': 'latin', 'ca': 'latin', 'tl': 'latin', 'sw': 'latin',
    'so': 'latin', 'sq': 'latin', 'af': 'latin', 'cy': 'latin', 'id': 'latin', 'ms': 'latin',
    'tr': 'latin', 'vi': 'latin',
    
    'ru': 'cyrillic', 'bg': 'cyrillic', 'uk': 'cyrillic', 'mk': 'cyrillic',
    
    'ar': 'arabic', 'fa': 'arabic', 'ur': 'arabic',
    'he': 'hebrew',
    
    'zh-cn': 'chinese', 'zh-tw': 'chinese',
    'ja': 'japanese',
    'ko': 'korean',
    'th': 'thai',
    
    'hi': 'devanagari', 'ne': 'devanagari', 'mr': 'devanagari',
    'bn': 'bengali',
    'gu': 'gujarati',
    'pa': 'gurmukhi',
    'ta': 'tamil',
    'te': 'telugu',
    'kn': 'kannada',
    'ml': 'malayalam',
    'el': 'greek',
}


def get_language_context(text: str) -> LanguageContext:
    """
    Get comprehensive language context for text.
    
    Args:
        text: Text to analyze
        
    Returns:  
        LanguageContext: Complete language context information
    """
    lang_code, confidence, is_reliable = detect_text_language(text)
    
    family = LANGUAGE_FAMILIES.get(lang_code, LanguageFamily.OTHER)
    direction = 'rtl' if lang_code in RTL_LANGUAGES else 'ltr'
    script = LANGUAGE_SCRIPTS.get(lang_code, 'latin')
    
    return LanguageContext(
        language_code=lang_code,
        language_name=get_language_display_name(lang_code),
        confidence=confidence,
        is_reliable=is_reliable,
        family=family,
        direction=direction,
        script=script
    )


def is_text_mixed_language(text: str, threshold: float = 0.3) -> bool:
    """
    Detect if text contains mixed languages.
    
    Args:
        text: Text to analyze
        threshold: Minimum confidence difference to consider mixed
        
    Returns:
        bool: True if text appears to contain multiple languages
    """
    if not text or len(text.strip()) < 20:
        return False
    
    try:
        from tools.language_detection import _detect_multiple_languages
        detection = _detect_multiple_languages(text)
        
        # If top two languages have similar confidence, consider it mixed
        if len(detection.all_languages) >= 2:
            top_conf = detection.all_languages[0].confidence
            second_conf = detection.all_languages[1].confidence
            return (top_conf - second_conf) < threshold
            
        return False
        
    except Exception as e:
        logger.warning(f"Error detecting mixed language: {e}")
        return False


def normalize_text_for_language(text: str, language_code: str) -> str:
    """
    Normalize text according to language-specific rules.
    
    Args:
        text: Text to normalize
        language_code: ISO 639-1 language code
        
    Returns:
        str: Normalized text
    """
    if not text:
        return text
    
    normalized = text.strip()
    
    # Language-specific normalization
    if language_code in ['ar', 'fa', 'ur']:  # Arabic script languages
        # Remove Arabic diacritics for better processing
        normalized = re.sub(r'[\u064B-\u065F\u0670\u06D6-\u06ED]', '', normalized)
        
    elif language_code in ['zh-cn', 'zh-tw']:  # Chinese
        # Normalize Chinese punctuation
        normalized = normalized.replace('，', ',').replace('。', '.')
        normalized = normalized.replace('！', '!').replace('？', '?')
        
    elif language_code == 'ja':  # Japanese  
        # Normalize Japanese punctuation
        normalized = normalized.replace('、', ',').replace('。', '.')
        
    elif language_code in ['hi', 'bn', 'gu', 'pa', 'mr', 'ne']:  # Indic languages
        # Remove Indic diacritics if present
        normalized = re.sub(r'[\u0900-\u097F\u0980-\u09FF\u0A80-\u0AFF\u0B00-\u0B7F\u0C80-\u0CFF][\u093C\u09BC\u0ABC\u0B3C\u0CBC]?', lambda m: m.group(0)[0], normalized)
    
    # Common normalizations for all languages
    normalized = re.sub(r'\s+', ' ', normalized)  # Normalize whitespace
    normalized = normalized.replace('\u00A0', ' ')  # Replace non-breaking space
    
    return normalized


def split_text_by_sentences(text: str, language_code: str) -> List[str]:
    """
    Split text into sentences using language-aware rules.
    
    Args:
        text: Text to split
        language_code: ISO 639-1 language code
        
    Returns:
        List[str]: List of sentences
    """
    if not text:
        return []
    
    sentences = []
    
    # Language-specific sentence splitting
    if language_code in ['zh-cn', 'zh-tw']:  # Chinese
        # Chinese uses different punctuation
        sentences = re.split(r'[。！？；]', text)
        
    elif language_code == 'ja':  # Japanese
        # Japanese sentence endings
        sentences = re.split(r'[。！？]', text)
        
    elif language_code in ['ar', 'fa', 'ur']:  # Arabic script
        # Arabic punctuation
        sentences = re.split(r'[\.！？。؟]', text)
        
    else:  # Most European languages
        # Standard sentence splitting
        sentences = re.split(r'[.!?]+\s+', text)
    
    # Clean and filter sentences
    sentences = [s.strip() for s in sentences if s.strip()]
    
    return sentences


def get_word_count(text: str, language_code: str) -> int:
    """
    Get word count using language-appropriate tokenization.
    
    Args:
        text: Text to count words in
        language_code: ISO 639-1 language code
        
    Returns:
        int: Word count
    """
    if not text:
        return 0
    
    normalized = normalize_text_for_language(text, language_code)
    
    if language_code in ['zh-cn', 'zh-tw']:  # Chinese
        # Chinese doesn't use spaces between words
        # Count characters instead (rough approximation)
        return len(re.sub(r'\s+', '', normalized))
        
    elif language_code == 'ja':  # Japanese
        # Japanese mix of character types
        # Count non-space characters as rough word count
        return len(re.sub(r'\s+', '', normalized))
        
    elif language_code == 'ko':  # Korean
        # Korean has spaces but complex morphology
        return len(normalized.split())
        
    else:  # Most other languages
        # Standard space-based word counting
        return len(normalized.split())


def estimate_reading_time(text: str, language_code: str) -> int:
    """
    Estimate reading time in minutes for given language.
    
    Args:
        text: Text to estimate reading time for
        language_code: ISO 639-1 language code
        
    Returns:
        int: Estimated reading time in minutes
    """
    if not text:
        return 0
    
    word_count = get_word_count(text, language_code)
    
    # Language-specific reading speeds (words per minute)
    reading_speeds = {
        'en': 200, 'es': 180, 'fr': 160, 'de': 150, 'it': 170, 'pt': 175,
        'ru': 140, 'pl': 130, 'cs': 125, 'sk': 125, 'uk': 140,
        'zh-cn': 250, 'zh-tw': 250,  # Characters per minute for Chinese
        'ja': 300,  # Characters per minute for Japanese
        'ko': 180,
        'ar': 120, 'he': 130, 'fa': 120, 'ur': 120,
        'hi': 130, 'bn': 125, 'ta': 120, 'te': 115,
    }
    
    speed = reading_speeds.get(language_code, 180)  # Default speed
    
    # Calculate reading time in minutes
    reading_time = max(1, round(word_count / speed))
    
    return reading_time


def is_formal_language_context(text: str, language_code: str) -> bool:
    """
    Detect if text uses formal language register.
    
    Args:
        text: Text to analyze
        language_code: ISO 639-1 language code
        
    Returns:
        bool: True if text appears formal
    """
    if not text:
        return False
    
    # Language-specific formal indicators
    formal_indicators = {
        'en': ['sir', 'madam', 'please', 'kindly', 'respectfully', 'sincerely'],
        'es': ['señor', 'señora', 'usted', 'por favor', 'atentamente'],
        'fr': ['monsieur', 'madame', 'vous', 's\'il vous plaît', 'cordialement'],
        'de': ['sie', 'herr', 'frau', 'bitte', 'mit freundlichen grüßen'],
        'it': ['signore', 'signora', 'lei', 'per favore', 'cordialmente'],
        'pt': ['senhor', 'senhora', 'por favor', 'atenciosamente'],
        'ru': ['вы', 'господин', 'госпожа', 'пожалуйста', 'с уважением'],
        'ja': ['です', 'ます', 'さん', '様', 'お願いします'],
        'ko': ['습니다', '님', '씨', '부탁드립니다'],
        'zh-cn': ['您', '先生', '女士', '请', '谢谢'],
        'ar': ['سيد', 'سيدة', 'من فضلك', 'شكرا'],
    }
    
    indicators = formal_indicators.get(language_code, [])
    text_lower = text.lower()
    
    # Count formal indicators
    formal_count = sum(1 for indicator in indicators if indicator in text_lower)
    
    # Consider formal if multiple indicators present
    return formal_count >= 2


def prepare_text_for_translation(text: str, source_lang: str, target_lang: str) -> Dict[str, Any]:
    """
    Prepare text for translation with context information.
    
    Args:
        text: Text to prepare for translation
        source_lang: Source language code
        target_lang: Target language code
        
    Returns:
        Dict[str, Any]: Translation context and prepared text
    """
    if not text:
        return {
            "prepared_text": "",
            "source_context": None,
            "target_context": None,
            "translation_notes": []
        }
    
    # Get language contexts
    source_context = get_language_context(text)
    
    # Create target context (without text analysis)
    target_family = LANGUAGE_FAMILIES.get(target_lang, LanguageFamily.OTHER)
    target_direction = 'rtl' if target_lang in RTL_LANGUAGES else 'ltr'
    target_script = LANGUAGE_SCRIPTS.get(target_lang, 'latin')
    
    target_context = LanguageContext(
        language_code=target_lang,
        language_name=get_language_display_name(target_lang),
        confidence=1.0,
        is_reliable=True,
        family=target_family,
        direction=target_direction,
        script=target_script
    )
    
    # Prepare text
    prepared_text = normalize_text_for_language(text, source_lang)
    
    # Generate translation notes
    notes = []
    
    if source_context.direction != target_context.direction:
        notes.append(f"Text direction change: {source_context.direction} → {target_context.direction}")
    
    if source_context.script != target_context.script:
        notes.append(f"Script change: {source_context.script} → {target_context.script}")
    
    if source_context.family != target_context.family:
        notes.append(f"Language family change: {source_context.family.value} → {target_context.family.value}")
    
    if is_formal_language_context(text, source_lang):
        notes.append("Formal register detected - maintain formality in translation")
    
    return {
        "prepared_text": prepared_text,
        "source_context": source_context,
        "target_context": target_context,
        "translation_notes": notes,
        "estimated_complexity": "high" if len(notes) > 2 else "medium" if notes else "low"
    }


def validate_language_consistency(texts: List[str], expected_language: str) -> Dict[str, Any]:
    """
    Validate that a list of texts are in the expected language.
    
    Args:
        texts: List of texts to validate
        expected_language: Expected ISO 639-1 language code
        
    Returns:
        Dict[str, Any]: Validation results
    """
    if not texts:
        return {
            "is_consistent": True,
            "consistency_score": 1.0,
            "inconsistent_texts": [],
            "detected_languages": {}
        }
    
    inconsistent_texts = []
    language_counts = {}
    
    for i, text in enumerate(texts):
        if not text or not text.strip():
            continue
            
        detected_lang, confidence, is_reliable = detect_text_language(text)
        
        # Count detected languages
        if detected_lang in language_counts:
            language_counts[detected_lang] += 1
        else:
            language_counts[detected_lang] = 1
        
        # Check if inconsistent with expected language
        if detected_lang != expected_language and is_reliable:
            inconsistent_texts.append({
                "index": i,
                "text": text[:50] + "..." if len(text) > 50 else text,
                "detected_language": detected_lang,
                "confidence": confidence
            })
    
    # Calculate consistency score
    total_texts = len([t for t in texts if t and t.strip()])
    expected_count = language_counts.get(expected_language, 0)
    consistency_score = expected_count / total_texts if total_texts > 0 else 1.0
    
    return {
        "is_consistent": len(inconsistent_texts) == 0,
        "consistency_score": consistency_score,
        "inconsistent_texts": inconsistent_texts,
        "detected_languages": language_counts,
        "total_texts_analyzed": total_texts,
        "expected_language": expected_language
    }
