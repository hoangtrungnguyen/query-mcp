"""Multilingual conversation support and cultural awareness"""

import json
from pathlib import Path
from datetime import datetime
from typing import Optional, List, Dict, Any, Tuple
from dataclasses import dataclass, field
from enum import Enum

MULTILINGUAL_DIR = Path.home() / ".memory-mcp" / "multilingual"
MULTILINGUAL_DIR.mkdir(exist_ok=True, parents=True)


class Language(Enum):
    """Supported languages"""
    ENGLISH = "en"
    SPANISH = "es"
    FRENCH = "fr"
    GERMAN = "de"
    CHINESE = "zh"
    JAPANESE = "ja"
    KOREAN = "ko"
    PORTUGUESE = "pt"
    RUSSIAN = "ru"
    ARABIC = "ar"


class CulturalContext(Enum):
    """Cultural communication contexts"""
    FORMAL = "formal"  # Business, official
    INFORMAL = "informal"  # Casual, friends
    ACADEMIC = "academic"  # Educational
    TECHNICAL = "technical"  # Professional/technical
    CREATIVE = "creative"  # Artistic, expressive


@dataclass
class LanguageDetection:
    """Language detection result"""
    detection_id: str
    text: str
    detected_language: Language
    confidence: float  # 0-1
    alternative_languages: List[Tuple[Language, float]] = field(default_factory=list)
    detected_at: str = ""

    def __post_init__(self):
        if not self.detected_at:
            self.detected_at = datetime.now().isoformat()

    def to_dict(self) -> Dict:
        """Serialize detection"""
        return {
            "detection_id": self.detection_id,
            "detected_language": self.detected_language.value,
            "confidence": self.confidence,
            "alternatives": len(self.alternative_languages),
        }


@dataclass
class Translation:
    """Translation result"""
    translation_id: str
    source_text: str
    source_language: Language
    target_language: Language
    translated_text: str
    confidence: float  # 0-1
    back_translation: Optional[str] = None  # For quality check
    quality_score: float = 0.8
    created_at: str = ""

    def __post_init__(self):
        if not self.created_at:
            self.created_at = datetime.now().isoformat()

    def to_dict(self) -> Dict:
        """Serialize translation"""
        return {
            "translation_id": self.translation_id,
            "source": self.source_language.value,
            "target": self.target_language.value,
            "confidence": self.confidence,
            "quality": self.quality_score,
        }


@dataclass
class CulturalAdaptation:
    """Culturally adapted response"""
    adaptation_id: str
    original_response: str
    adapted_response: str
    target_language: Language
    target_culture: str
    adaptations_made: List[str]  # What was changed
    formality_level: CulturalContext
    cultural_sensitivity_score: float  # 0-1
    created_at: str = ""

    def __post_init__(self):
        if not self.created_at:
            self.created_at = datetime.now().isoformat()

    def to_dict(self) -> Dict:
        """Serialize adaptation"""
        return {
            "adaptation_id": self.adaptation_id,
            "target_language": self.target_language.value,
            "target_culture": self.target_culture,
            "formality": self.formality_level.value,
            "sensitivity_score": self.cultural_sensitivity_score,
            "adaptations": len(self.adaptations_made),
        }


@dataclass
class MultilingualConversation:
    """Conversation spanning multiple languages"""
    conversation_id: str
    primary_language: Language
    languages_used: List[Language] = field(default_factory=list)
    messages: List[Dict[str, Any]] = field(default_factory=list)
    detected_cultures: List[str] = field(default_factory=list)
    code_switching_detected: bool = False
    created_at: str = ""

    def __post_init__(self):
        if not self.created_at:
            self.created_at = datetime.now().isoformat()
        if self.primary_language not in self.languages_used:
            self.languages_used.append(self.primary_language)

    def add_message(
        self,
        text: str,
        language: Language,
        role: str = "user",
        cultural_context: Optional[str] = None,
    ):
        """Add message to conversation"""
        if language not in self.languages_used:
            self.languages_used.append(language)

        self.messages.append({
            "text": text,
            "language": language.value,
            "role": role,
            "culture": cultural_context,
            "timestamp": datetime.now().isoformat(),
        })

    def to_dict(self) -> Dict:
        """Serialize conversation"""
        return {
            "conversation_id": self.conversation_id,
            "primary_language": self.primary_language.value,
            "languages_used": [l.value for l in self.languages_used],
            "message_count": len(self.messages),
            "cultures": len(self.detected_cultures),
            "code_switching": self.code_switching_detected,
        }


class LanguageDetector:
    """Detect language of text"""

    @staticmethod
    def detect(text: str) -> LanguageDetection:
        """Detect language"""
        # Simulated detection using character/word heuristics
        language_markers = {
            Language.ENGLISH: ["the", "and", "is", "to"],
            Language.SPANISH: ["el", "la", "de", "que"],
            Language.FRENCH: ["le", "la", "de", "et"],
            Language.GERMAN: ["der", "die", "und", "zu"],
            Language.CHINESE: ["的", "一", "是", "在"],
            Language.JAPANESE: ["の", "を", "に", "は"],
            Language.KOREAN: ["의", "을", "이", "를"],
        }

        text_lower = text.lower()
        scores = {}

        for language, markers in language_markers.items():
            matches = sum(1 for marker in markers if marker in text_lower)
            scores[language] = matches / len(markers)

        if not scores:
            detected = Language.ENGLISH
            confidence = 0.5
        else:
            detected = max(scores.items(), key=lambda x: x[1])[0]
            confidence = min(1.0, scores[detected])

        detection = LanguageDetection(
            detection_id=f"det_{int(datetime.now().timestamp())}",
            text=text,
            detected_language=detected,
            confidence=confidence,
            alternative_languages=[
                (lang, score) for lang, score in sorted(
                    scores.items(),
                    key=lambda x: x[1],
                    reverse=True
                )[1:3]
            ],
        )

        return detection


class Translator:
    """Translate between languages"""

    @staticmethod
    def translate(
        text: str,
        source_language: Language,
        target_language: Language,
    ) -> Translation:
        """Translate text"""
        # Simulated translation using simple word mapping
        translation_map = {
            (Language.ENGLISH, Language.SPANISH): {
                "hello": "hola",
                "thank you": "gracias",
                "goodbye": "adiós",
                "yes": "sí",
                "no": "no",
            },
            (Language.ENGLISH, Language.FRENCH): {
                "hello": "bonjour",
                "thank you": "merci",
                "goodbye": "au revoir",
                "yes": "oui",
                "no": "non",
            },
        }

        key = (source_language, target_language)
        mapping = translation_map.get(key, {})

        translated = text
        for src, tgt in mapping.items():
            translated = translated.lower().replace(src.lower(), tgt)

        if translated == text.lower():
            # No translation found, use source
            translated = text
            confidence = 0.3
        else:
            confidence = 0.9

        translation = Translation(
            translation_id=f"trans_{int(datetime.now().timestamp())}",
            source_text=text,
            source_language=source_language,
            target_language=target_language,
            translated_text=translated,
            confidence=confidence,
            quality_score=confidence,
        )

        return translation

    @staticmethod
    def back_translate(
        translated_text: str,
        source_language: Language,
        target_language: Language,
    ) -> str:
        """Back-translate for quality check"""
        reverse_trans = Translator.translate(
            translated_text,
            target_language,
            source_language,
        )
        return reverse_trans.translated_text


class CulturalAdapter:
    """Adapt responses for cultural context"""

    CULTURAL_RULES = {
        "ja": {
            "formal": ["です", "ます"],  # Polite endings
            "informal": ["だ", "よ"],  # Casual endings
        },
        "ar": {
            "formal": ["في سياق رسمي"],  # In formal context
            "informal": ["بشكل عادي"],  # Casually
        },
    }

    @staticmethod
    def adapt(
        response: str,
        target_language: Language,
        target_culture: str,
        formality: CulturalContext,
    ) -> CulturalAdaptation:
        """Adapt response for cultural context"""
        adaptations = []

        adapted_response = response

        # Apply formality adjustments
        if formality == CulturalContext.FORMAL:
            adapted_response = adapted_response.replace("thanks", "thank you")
            adapted_response = adapted_response.replace("hi", "hello")
            adaptations.append("formal_pronouns")

        elif formality == CulturalContext.INFORMAL:
            adapted_response = adapted_response.replace("thank you", "thanks")
            adapted_response = adapted_response.replace("hello", "hi")
            adaptations.append("casual_pronouns")

        # Language-specific adaptations
        if target_language == Language.JAPANESE:
            adaptations.append("japanese_honorifics")
        elif target_language == Language.CHINESE:
            adaptations.append("chinese_formality_markers")
        elif target_language == Language.ARABIC:
            adaptations.append("arabic_formality_level")

        # Cultural sensitivity
        sensitivity_score = 0.8
        if formality == CulturalContext.FORMAL:
            sensitivity_score = 0.9

        adaptation = CulturalAdaptation(
            adaptation_id=f"adapt_{int(datetime.now().timestamp())}",
            original_response=response,
            adapted_response=adapted_response,
            target_language=target_language,
            target_culture=target_culture,
            adaptations_made=adaptations,
            formality_level=formality,
            cultural_sensitivity_score=sensitivity_score,
        )

        return adaptation


class CodeSwitchDetector:
    """Detect code-switching (mixing languages)"""

    @staticmethod
    def detect_switching(text: str) -> Tuple[bool, List[Language]]:
        """Detect if text switches between languages"""
        sentences = text.split(".")
        detected_languages = set()

        for sentence in sentences:
            if sentence.strip():
                detection = LanguageDetector.detect(sentence)
                if detection.confidence > 0.6:
                    detected_languages.add(detection.detected_language)

        code_switching = len(detected_languages) > 1
        return code_switching, list(detected_languages)


class MultilingualManager:
    """Manage multilingual conversations"""

    def __init__(self):
        self.conversations: Dict[str, MultilingualConversation] = {}
        self.translations: Dict[str, Translation] = {}
        self.detections: Dict[str, LanguageDetection] = {}

    def create_conversation(
        self,
        conversation_id: str,
        primary_language: Language,
    ) -> MultilingualConversation:
        """Create multilingual conversation"""
        conv = MultilingualConversation(
            conversation_id=conversation_id,
            primary_language=primary_language,
        )
        self.conversations[conversation_id] = conv
        return conv

    def detect_language(self, text: str) -> LanguageDetection:
        """Detect text language"""
        detection = LanguageDetector.detect(text)
        self.detections[detection.detection_id] = detection
        return detection

    def translate_text(
        self,
        text: str,
        source_language: Language,
        target_language: Language,
    ) -> Translation:
        """Translate text"""
        translation = Translator.translate(text, source_language, target_language)
        self.translations[translation.translation_id] = translation
        return translation

    def add_message(
        self,
        conversation_id: str,
        text: str,
        language: Language,
        role: str = "user",
    ) -> bool:
        """Add message to conversation"""
        if conversation_id not in self.conversations:
            return False

        conv = self.conversations[conversation_id]

        # Detect code-switching
        code_switching, langs = CodeSwitchDetector.detect_switching(text)
        if code_switching:
            conv.code_switching_detected = True

        conv.add_message(text, language, role)
        return True

    def get_multilingual_summary(self, conversation_id: str) -> Optional[Dict]:
        """Get conversation summary"""
        if conversation_id not in self.conversations:
            return None

        conv = self.conversations[conversation_id]

        return {
            "conversation_id": conversation_id,
            "primary_language": conv.primary_language.value,
            "languages_used": [l.value for l in conv.languages_used],
            "message_count": len(conv.messages),
            "code_switching": conv.code_switching_detected,
            "detected_cultures": conv.detected_cultures,
        }


# Global manager
multilingual_manager = MultilingualManager()


# MCP Tools

def detect_text_language(text: str) -> dict:
    """Detect language of text"""
    detection = multilingual_manager.detect_language(text)
    return detection.to_dict()


def translate_text(
    text: str,
    source_language: str,
    target_language: str,
) -> dict:
    """Translate text"""
    translation = multilingual_manager.translate_text(
        text,
        Language(source_language),
        Language(target_language),
    )
    return translation.to_dict()


def create_multilingual_conversation(conversation_id: str, primary_language: str) -> dict:
    """Create multilingual conversation"""
    conv = multilingual_manager.create_conversation(
        conversation_id,
        Language(primary_language),
    )
    return conv.to_dict()


def add_conversation_message(
    conversation_id: str,
    text: str,
    language: str,
    role: str = "user",
) -> dict:
    """Add message to conversation"""
    success = multilingual_manager.add_message(
        conversation_id,
        text,
        Language(language),
        role,
    )
    return {"added": success, "conversation_id": conversation_id}


def adapt_for_culture(
    response: str,
    target_language: str,
    target_culture: str,
    formality: str = "formal",
) -> dict:
    """Adapt response for cultural context"""
    adaptation = CulturalAdapter.adapt(
        response,
        Language(target_language),
        target_culture,
        CulturalContext(formality),
    )
    return adaptation.to_dict()


def get_conversation_summary(conversation_id: str) -> dict:
    """Get conversation summary"""
    summary = multilingual_manager.get_multilingual_summary(conversation_id)
    return summary or {"error": "Conversation not found"}


if __name__ == "__main__":
    # Test multilingual
    manager = MultilingualManager()

    # Detect language
    detection = manager.detect_language("Bonjour, comment allez-vous?")
    print(f"Detected: {detection.detected_language.value}")

    # Translate
    translation = manager.translate_text(
        "Hello",
        Language.ENGLISH,
        Language.SPANISH,
    )
    print(f"Translation: {translation.translated_text}")

    # Create conversation
    conv = manager.create_conversation("conv_1", Language.ENGLISH)
    manager.add_message("conv_1", "Hello", Language.ENGLISH, "user")
    manager.add_message("conv_1", "Hola", Language.SPANISH, "assistant")

    # Summary
    summary = manager.get_multilingual_summary("conv_1")
    print(f"Summary: {json.dumps(summary, indent=2)}")

    # Cultural adaptation
    adaptation = CulturalAdapter.adapt(
        "Thanks for your help",
        Language.JAPANESE,
        "japan",
        CulturalContext.FORMAL,
    )
    print(f"Adapted: {adaptation.adapted_response}")
