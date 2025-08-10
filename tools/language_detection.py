# tools/language_detection.py
"""
Language Detection Tool for Multi-Language Support
=================================================

This module provides language detection capabilities using the langdetect library,
which is a port of Google's language-detection library to Python. It supports
detection of 50+ languages with confidence scoring.

Key Features:
- Automatic language detection from text
- Confidence scoring for language predictions
- Support for 50+ languages
- Multiple detection modes (single language vs. probability distribution)
- Robust error handling for edge cases

Usage:
- detect_language(text): Returns the most likely language code
- detect_languages_with_confidence(text): Returns all probable languages with scores
- get_supported_languages(): Returns list of supported language codes
"""

import logging
from typing import List, Dict, Optional, Tuple, Any
from dataclasses import dataclass

from langchain_core.tools import tool
from langdetect import detect, detect_langs, DetectorFactory
from langdetect.lang_detect_exception import LangDetectException

from utils.logging_config import get_logger

logger = get_logger(__name__)

# Set seed for consistent results (important for testing and reproducibility)
DetectorFactory.seed = 0


@dataclass
class LanguageDetection:
    """Result of language detection with confidence score."""
    language_code: str
    language_name: str
    confidence: float
    is_reliable: bool  # True if confidence is above reliability threshold


@dataclass 
class MultiLanguageDetection:
    """Result of multi-language detection with all probable languages."""
    primary_language: LanguageDetection
    all_languages: List[LanguageDetection]
    text_length: int
    detection_method: str


# Language code to name mapping for common languages
LANGUAGE_NAMES = {
    'af': 'Afrikaans', 'ar': 'Arabic', 'bg': 'Bulgarian', 'bn': 'Bengali',
    'ca': 'Catalan', 'cs': 'Czech', 'cy': 'Welsh', 'da': 'Danish',
    'de': 'German', 'el': 'Greek', 'en': 'English', 'es': 'Spanish',
    'et': 'Estonian', 'fa': 'Persian', 'fi': 'Finnish', 'fr': 'French',
    'gu': 'Gujarati', 'he': 'Hebrew', 'hi': 'Hindi', 'hr': 'Croatian',
    'hu': 'Hungarian', 'id': 'Indonesian', 'it': 'Italian', 'ja': 'Japanese',
    'kn': 'Kannada', 'ko': 'Korean', 'lt': 'Lithuanian', 'lv': 'Latvian',
    'mk': 'Macedonian', 'ml': 'Malayalam', 'mr': 'Marathi', 'ne': 'Nepali',
    'nl': 'Dutch', 'no': 'Norwegian', 'pa': 'Punjabi', 'pl': 'Polish',
    'pt': 'Portuguese', 'ro': 'Romanian', 'ru': 'Russian', 'sk': 'Slovak',
    'sl': 'Slovenian', 'so': 'Somali', 'sq': 'Albanian', 'sv': 'Swedish',
    'sw': 'Swahili', 'ta': 'Tamil', 'te': 'Telugu', 'th': 'Thai',
    'tl': 'Tagalog', 'tr': 'Turkish', 'uk': 'Ukrainian', 'ur': 'Urdu',
    'vi': 'Vietnamese', 'zh-cn': 'Chinese (Simplified)', 'zh-tw': 'Chinese (Traditional)'
}

# Reliability thresholds
RELIABILITY_THRESHOLD = 0.7  # Confidence above this is considered reliable
MIN_TEXT_LENGTH = 3  # Minimum text length for reliable detection


def get_language_name(language_code: str) -> str:
    """Get human-readable language name from language code."""
    return LANGUAGE_NAMES.get(language_code, language_code.upper())


def is_detection_reliable(text: str, confidence: float) -> bool:
    """
    Determine if language detection is reliable based on text length and confidence.
    
    Args:
        text: The input text
        confidence: Detection confidence score
        
    Returns:
        bool: True if detection is considered reliable
    """
    # Very short text is unreliable regardless of confidence
    if len(text.strip()) < MIN_TEXT_LENGTH:
        return False
    
    # For longer text, use confidence threshold
    if len(text.strip()) > 20:
        return confidence >= RELIABILITY_THRESHOLD
    
    # For medium text, require higher confidence
    return confidence >= 0.85


def _detect_single_language(text: str) -> LanguageDetection:
    """
    Detect the primary language of text.
    
    Args:
        text: Input text to analyze
        
    Returns:
        LanguageDetection: Primary language with confidence
        
    Raises:
        LangDetectException: If detection fails
    """
    try:
        # Get single language detection
        lang_code = detect(text)
        
        # Get detailed probabilities to extract confidence
        lang_probs = detect_langs(text)
        primary_prob = next((prob for prob in lang_probs if prob.lang == lang_code), None)
        
        confidence = primary_prob.prob if primary_prob else 0.5
        
        return LanguageDetection(
            language_code=lang_code,
            language_name=get_language_name(lang_code),
            confidence=confidence,
            is_reliable=is_detection_reliable(text, confidence)
        )
        
    except LangDetectException as e:
        logger.warning(f"Language detection failed: {e}")
        # Default to English with low confidence
        return LanguageDetection(
            language_code='en',
            language_name='English',
            confidence=0.1, 
            is_reliable=False
        )


def _detect_multiple_languages(text: str) -> MultiLanguageDetection:
    """
    Detect all probable languages with confidence scores.
    
    Args:
        text: Input text to analyze
        
    Returns:
        MultiLanguageDetection: All probable languages with details
    """
    try:
        lang_probs = detect_langs(text)
        
        all_detections = []
        for prob in lang_probs:
            detection = LanguageDetection(
                language_code=prob.lang,
                language_name=get_language_name(prob.lang),
                confidence=prob.prob,
                is_reliable=is_detection_reliable(text, prob.prob)
            )
            all_detections.append(detection)
        
        # Primary language is the first (highest confidence)
        primary = all_detections[0] if all_detections else LanguageDetection(
            language_code='en', language_name='English', confidence=0.1, is_reliable=False
        )
        
        return MultiLanguageDetection(
            primary_language=primary,
            all_languages=all_detections,
            text_length=len(text.strip()),
            detection_method='probabilistic'
        )
        
    except LangDetectException as e:
        logger.warning(f"Multi-language detection failed: {e}")
        # Default to English with low confidence
        default_detection = LanguageDetection(
            language_code='en', language_name='English', confidence=0.1, is_reliable=False
        )
        return MultiLanguageDetection(
            primary_language=default_detection,
            all_languages=[default_detection],
            text_length=len(text.strip()),
            detection_method='fallback'
        )


@tool
def detect_language(text: str) -> str:
    """
    Detect the primary language of the given text.
    
    This tool uses Google's language detection algorithm to identify the most
    likely language of the input text. It returns the ISO 639-1 language code
    (e.g., 'en' for English, 'es' for Spanish, 'fr' for French).
    
    Args:
        text (str): The text to analyze for language detection
        
    Returns:
        str: The ISO 639-1 language code of the detected language
        
    Example:
        detect_language("Hello, how are you?") -> "en"
        detect_language("Bonjour, comment allez-vous?") -> "fr"
        detect_language("Hola, ¿cómo estás?") -> "es"
    """
    if not text or not text.strip():
        logger.warning("Empty text provided for language detection")
        return "en"  # Default to English
    
    try:
        detection = _detect_single_language(text)
        
        logger.info(f"Language detected: {detection.language_name} ({detection.language_code}) "
                   f"with confidence {detection.confidence:.2f}, reliable: {detection.is_reliable}")
        
        return detection.language_code
        
    except Exception as e:
        logger.error(f"Unexpected error in language detection: {e}")
        return "en"  # Fallback to English


@tool
def detect_language_with_confidence(text: str) -> Dict[str, Any]:
    """
    Detect the primary language with detailed confidence information.
    
    This tool provides more detailed language detection results including
    confidence scores, reliability assessment, and language names.
    
    Args:
        text (str): The text to analyze for language detection
        
    Returns:
        Dict[str, Any]: Dictionary containing:
            - language_code: ISO 639-1 language code
            - language_name: Human-readable language name  
            - confidence: Confidence score (0.0 to 1.0)
            - is_reliable: Whether the detection is reliable
            - text_length: Length of analyzed text
            
    Example:
        detect_language_with_confidence("Hello world") -> {
            "language_code": "en",
            "language_name": "English", 
            "confidence": 0.95,
            "is_reliable": True,
            "text_length": 11
        }
    """
    if not text or not text.strip():
        logger.warning("Empty text provided for detailed language detection")
        return {
            "language_code": "en",
            "language_name": "English",
            "confidence": 0.1,
            "is_reliable": False,
            "text_length": 0
        }
    
    try:
        detection = _detect_single_language(text)
        
        result = {
            "language_code": detection.language_code,
            "language_name": detection.language_name,
            "confidence": detection.confidence,
            "is_reliable": detection.is_reliable,
            "text_length": len(text.strip())
        }
        
        logger.info(f"Detailed language detection: {result}")
        return result
        
    except Exception as e:
        logger.error(f"Unexpected error in detailed language detection: {e}")
        return {
            "language_code": "en",
            "language_name": "English",
            "confidence": 0.1,
            "is_reliable": False,
            "text_length": len(text.strip()) if text else 0
        }


@tool
def detect_multiple_languages(text: str) -> Dict[str, Any]:
    """
    Detect all probable languages with confidence scores.
    
    This tool returns all languages that the detection algorithm considers
    possible for the given text, ranked by confidence. Useful for texts
    that might contain multiple languages or ambiguous content.
    
    Args:
        text (str): The text to analyze for language detection
        
    Returns:
        Dict[str, Any]: Dictionary containing:
            - primary_language: Most likely language with details
            - all_languages: List of all probable languages
            - text_length: Length of analyzed text
            - detection_method: Method used for detection
            
    Example:
        detect_multiple_languages("Hello mundo") -> {
            "primary_language": {"language_code": "en", "confidence": 0.6, ...},
            "all_languages": [
                {"language_code": "en", "confidence": 0.6, ...},
                {"language_code": "es", "confidence": 0.4, ...}
            ],
            "text_length": 11,
            "detection_method": "probabilistic"
        }
    """
    if not text or not text.strip():
        logger.warning("Empty text provided for multi-language detection")
        default_detection = {
            "language_code": "en",
            "language_name": "English", 
            "confidence": 0.1,
            "is_reliable": False
        }
        return {
            "primary_language": default_detection,
            "all_languages": [default_detection],
            "text_length": 0,
            "detection_method": "fallback"
        }
    
    try:
        detection = _detect_multiple_languages(text)
        
        result = {
            "primary_language": {
                "language_code": detection.primary_language.language_code,
                "language_name": detection.primary_language.language_name,
                "confidence": detection.primary_language.confidence,
                "is_reliable": detection.primary_language.is_reliable
            },
            "all_languages": [
                {
                    "language_code": lang.language_code,
                    "language_name": lang.language_name,
                    "confidence": lang.confidence,
                    "is_reliable": lang.is_reliable
                }
                for lang in detection.all_languages
            ],
            "text_length": detection.text_length,
            "detection_method": detection.detection_method
        }
        
        logger.info(f"Multi-language detection found {len(detection.all_languages)} possible languages, "
                   f"primary: {detection.primary_language.language_name}")
        return result
        
    except Exception as e:
        logger.error(f"Unexpected error in multi-language detection: {e}")
        default_detection = {
            "language_code": "en",
            "language_name": "English",
            "confidence": 0.1, 
            "is_reliable": False
        }
        return {
            "primary_language": default_detection,
            "all_languages": [default_detection],
            "text_length": len(text.strip()) if text else 0,
            "detection_method": "error_fallback"
        }


@tool 
def get_supported_languages() -> Dict[str, List[str]]:
    """
    Get list of all supported languages for detection.
    
    Returns the complete list of languages supported by the detection
    algorithm along with their ISO 639-1 codes and human-readable names.
    
    Returns:
        Dict[str, List[str]]: Dictionary containing:
            - language_codes: List of ISO 639-1 language codes
            - language_names: List of human-readable language names
            - total_count: Total number of supported languages
            
    Example:
        get_supported_languages() -> {
            "language_codes": ["en", "es", "fr", "de", ...],
            "language_names": ["English", "Spanish", "French", "German", ...],
            "total_count": 55
        }
    """
    try:
        codes = list(LANGUAGE_NAMES.keys())
        names = list(LANGUAGE_NAMES.values())
        
        result = {
            "language_codes": codes,
            "language_names": names,
            "total_count": len(codes),
            "supported_formats": ["text", "short_phrases", "sentences", "paragraphs"],
            "reliability_threshold": RELIABILITY_THRESHOLD,
            "min_text_length": MIN_TEXT_LENGTH
        }
        
        logger.info(f"Returning {len(codes)} supported languages")
        return result
        
    except Exception as e:
        logger.error(f"Error getting supported languages: {e}")
        return {
            "language_codes": ["en"],
            "language_names": ["English"],
            "total_count": 1,
            "error": str(e)
        }


# Helper functions for use by other modules (not tools)
def detect_text_language(text: str) -> Tuple[str, float, bool]:
    """
    Helper function for other modules to detect language.
    
    Args:
        text: Text to analyze
        
    Returns:
        Tuple[str, float, bool]: (language_code, confidence, is_reliable)
    """
    if not text or not text.strip():
        return "en", 0.1, False
    
    try:
        detection = _detect_single_language(text)
        return detection.language_code, detection.confidence, detection.is_reliable
    except Exception:
        return "en", 0.1, False


def is_language_supported(language_code: str) -> bool:
    """
    Check if a language code is supported.
    
    Args:
        language_code: ISO 639-1 language code
        
    Returns:
        bool: True if language is supported
    """
    return language_code.lower() in LANGUAGE_NAMES


def get_language_display_name(language_code: str) -> str:
    """
    Get display name for a language code.
    
    Args:
        language_code: ISO 639-1 language code
        
    Returns:
        str: Human-readable language name
    """
    return get_language_name(language_code.lower())


def get_language_detection_tools():
    """
    Get all language detection tools for the tool registry.
    
    Returns:
        List[BaseTool]: List of language detection tools
    """
    return [
        detect_language,
        detect_language_with_confidence,
        detect_multiple_languages,
        get_supported_languages
    ]
