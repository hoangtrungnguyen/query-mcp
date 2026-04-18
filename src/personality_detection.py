"""User personality detection and adaptation"""

import json
from pathlib import Path
from datetime import datetime
from typing import Optional, List, Dict, Any
from dataclasses import dataclass, field
from enum import Enum

PERSONALITY_DIR = Path.home() / ".memory-mcp" / "personality-detection"
PERSONALITY_DIR.mkdir(exist_ok=True, parents=True)


class Trait(Enum):
    """Big Five personality traits"""
    OPENNESS = "openness"  # Curiosity, creativity
    CONSCIENTIOUSNESS = "conscientiousness"  # Organization, discipline
    EXTRAVERSION = "extraversion"  # Sociability, assertiveness
    AGREEABLENESS = "agreeableness"  # Cooperation, empathy
    NEUROTICISM = "neuroticism"  # Stress sensitivity, anxiety


@dataclass
class PersonalityScore:
    """Score on personality trait"""
    trait: Trait
    score: float  # -1 to 1 (low to high)
    confidence: float  # How confident
    evidence: List[str] = field(default_factory=list)  # Supporting evidence

    def to_dict(self) -> Dict:
        """Serialize score"""
        return {
            "trait": self.trait.value,
            "score": round(self.score, 2),
            "confidence": round(self.confidence, 2),
        }


@dataclass
class CommunicationStyle:
    """Detected communication style"""
    style_id: str
    formality: float  # 0=very casual, 1=very formal
    verbosity: float  # 0=very brief, 1=very detailed
    directness: float  # 0=indirect/hints, 1=direct/explicit
    humor_preference: float  # 0=serious, 1=humorous
    expertise_level: str  # novice, intermediate, expert

    def to_dict(self) -> Dict:
        """Serialize style"""
        return {
            "style_id": self.style_id,
            "formality": round(self.formality, 2),
            "verbosity": round(self.verbosity, 2),
            "directness": round(self.directness, 2),
        }


@dataclass
class UserPersonality:
    """Detected user personality profile"""
    user_id: str
    trait_scores: Dict[Trait, PersonalityScore] = field(default_factory=dict)
    communication_style: Optional[CommunicationStyle] = None
    learning_style: str = "unknown"  # visual, auditory, kinesthetic, mixed
    risk_tolerance: float = 0.5  # 0=risk-averse, 1=risk-seeking
    pace_preference: str = "normal"  # slow, normal, fast
    confidence: float = 0.5  # Overall confidence in profile
    created_at: str = ""

    def __post_init__(self):
        if not self.created_at:
            self.created_at = datetime.now().isoformat()

    def to_dict(self) -> Dict:
        """Serialize profile"""
        return {
            "user_id": self.user_id,
            "traits": len(self.trait_scores),
            "overall_confidence": round(self.confidence, 2),
            "pace": self.pace_preference,
        }


class PersonalityDetector:
    """Detect personality from dialogue patterns"""

    # Linguistic markers for personality traits
    TRAIT_MARKERS = {
        Trait.OPENNESS: ["imagine", "explore", "why", "curious", "novel", "interesting"],
        Trait.CONSCIENTIOUSNESS: ["plan", "organize", "schedule", "deadline", "careful", "detail"],
        Trait.EXTRAVERSION: ["talk", "share", "communicate", "network", "social", "enthusiast"],
        Trait.AGREEABLENESS: ["help", "support", "care", "empathy", "cooperate", "kindly"],
        Trait.NEUROTICISM: ["worry", "anxious", "stress", "concerned", "fear", "uncertain"],
    }

    @staticmethod
    def detect_from_text(text: str) -> Dict[Trait, PersonalityScore]:
        """Detect personality traits from text"""
        scores = {}
        text_lower = text.lower()

        for trait, markers in PersonalityDetector.TRAIT_MARKERS.items():
            matches = sum(1 for marker in markers if marker in text_lower)
            score = (matches / len(markers)) * 2 - 1  # Normalize to -1 to 1

            personality_score = PersonalityScore(
                trait=trait,
                score=min(1.0, max(-1.0, score)),
                confidence=0.5 + (matches * 0.1),
                evidence=markers,
            )
            scores[trait] = personality_score

        return scores

    @staticmethod
    def analyze_communication_style(
        dialogue: List[Dict[str, str]],
    ) -> CommunicationStyle:
        """Analyze communication style from dialogue"""
        if not dialogue:
            return CommunicationStyle(
                style_id="default",
                formality=0.5,
                verbosity=0.5,
                directness=0.5,
                humor_preference=0.5,
                expertise_level="intermediate",
            )

        # Analyze formality
        formal_words = ["therefore", "nevertheless", "furthermore", "however"]
        formal_count = sum(1 for turn in dialogue for word in formal_words if word in turn.get("text", "").lower())
        formality = min(1.0, formal_count / len(dialogue))

        # Analyze verbosity
        avg_length = sum(len(t.get("text", "").split()) for t in dialogue) / len(dialogue)
        verbosity = min(1.0, avg_length / 100)

        # Analyze directness
        imperative_count = sum(1 for turn in dialogue if turn.get("text", "").rstrip().endswith("?"))
        directness = min(1.0, (len(dialogue) - imperative_count) / len(dialogue))

        # Analyze humor
        humor_markers = ["haha", "lol", "joke", "funny", ";)", ":)"]
        humor_count = sum(1 for turn in dialogue for marker in humor_markers if marker in turn.get("text", "").lower())
        humor = min(1.0, humor_count / max(1, len(dialogue)))

        return CommunicationStyle(
            style_id=f"style_{int(datetime.now().timestamp())}",
            formality=formality,
            verbosity=verbosity,
            directness=directness,
            humor_preference=humor,
            expertise_level="intermediate",
        )

    @staticmethod
    def detect_pace_preference(
        turn_intervals: List[float],
    ) -> str:
        """Detect pace preference from response times"""
        if not turn_intervals:
            return "normal"

        avg_interval = sum(turn_intervals) / len(turn_intervals)

        if avg_interval < 5.0:  # < 5 seconds
            return "fast"
        elif avg_interval > 30.0:  # > 30 seconds
            return "slow"
        else:
            return "normal"


class PersonalityAnalyzer:
    """Analyze personality and provide adaptation strategies"""

    def __init__(self):
        self.profiles: Dict[str, UserPersonality] = {}
        self.dialogues: Dict[str, List[Dict[str, str]]] = {}

    def analyze_user(
        self,
        user_id: str,
        dialogue_samples: List[Dict[str, str]],
    ) -> UserPersonality:
        """Analyze user personality from dialogue samples"""
        combined_text = " ".join([turn.get("text", "") for turn in dialogue_samples])

        # Detect traits
        trait_scores = PersonalityDetector.detect_from_text(combined_text)

        # Analyze communication style
        style = PersonalityDetector.analyze_communication_style(dialogue_samples)

        # Detect pace preference
        turn_intervals = [1.0] * len(dialogue_samples)  # Placeholder
        pace = PersonalityDetector.detect_pace_preference(turn_intervals)

        # Average confidence
        avg_confidence = sum(s.confidence for s in trait_scores.values()) / len(trait_scores)

        profile = UserPersonality(
            user_id=user_id,
            trait_scores=trait_scores,
            communication_style=style,
            pace_preference=pace,
            confidence=avg_confidence,
        )

        self.profiles[user_id] = profile
        self.dialogues[user_id] = dialogue_samples

        return profile

    def get_adaptation_suggestions(self, user_id: str) -> Dict[str, Any]:
        """Get communication adaptation suggestions"""
        profile = self.profiles.get(user_id)
        if not profile:
            return {}

        suggestions = {}

        # Adapt formality
        if profile.communication_style:
            formality = profile.communication_style.formality
            if formality > 0.7:
                suggestions["formality"] = "Maintain formal tone"
            elif formality < 0.3:
                suggestions["formality"] = "Use casual, conversational tone"
            else:
                suggestions["formality"] = "Use neutral, professional tone"

        # Adapt verbosity
        if profile.communication_style:
            verbosity = profile.communication_style.verbosity
            if verbosity > 0.7:
                suggestions["verbosity"] = "Provide detailed explanations"
            elif verbosity < 0.3:
                suggestions["verbosity"] = "Keep responses concise"
            else:
                suggestions["verbosity"] = "Balance brevity and detail"

        # Adapt directness
        if profile.communication_style:
            directness = profile.communication_style.directness
            if directness > 0.7:
                suggestions["directness"] = "Be direct and explicit"
            else:
                suggestions["directness"] = "Use diplomatic language"

        # Pace
        suggestions["pace"] = f"Adjust pace to {profile.pace_preference}"

        return suggestions

    def get_personality_summary(self, user_id: str) -> Optional[Dict[str, Any]]:
        """Get personality summary"""
        profile = self.profiles.get(user_id)
        if not profile:
            return None

        trait_summary = {
            t.value: s.to_dict() for t, s in profile.trait_scores.items()
        }

        return {
            "user_id": user_id,
            "traits": trait_summary,
            "communication_style": profile.communication_style.to_dict() if profile.communication_style else None,
            "pace": profile.pace_preference,
            "overall_confidence": round(profile.confidence, 2),
            "adaptation_suggestions": self.get_adaptation_suggestions(user_id),
        }


class PersonalityManager:
    """Manage personality detection across users"""

    def __init__(self):
        self.analyzers: Dict[str, PersonalityAnalyzer] = {}

    def create_analyzer(self, analyzer_id: str) -> PersonalityAnalyzer:
        """Create analyzer"""
        analyzer = PersonalityAnalyzer()
        self.analyzers[analyzer_id] = analyzer
        return analyzer

    def get_analyzer(self, analyzer_id: str) -> Optional[PersonalityAnalyzer]:
        """Get analyzer"""
        return self.analyzers.get(analyzer_id)


# Global manager
personality_manager = PersonalityManager()


# MCP Tools

def create_personality_analyzer(analyzer_id: str) -> dict:
    """Create personality analyzer"""
    analyzer = personality_manager.create_analyzer(analyzer_id)
    return {"analyzer_id": analyzer_id, "created": True}


def analyze_user_personality(
    analyzer_id: str,
    user_id: str,
    dialogue_samples: list,
) -> dict:
    """Analyze user personality"""
    analyzer = personality_manager.get_analyzer(analyzer_id)
    if not analyzer:
        return {"error": "Analyzer not found"}

    profile = analyzer.analyze_user(user_id, dialogue_samples)
    return profile.to_dict()


def get_personality_profile(analyzer_id: str, user_id: str) -> dict:
    """Get personality profile"""
    analyzer = personality_manager.get_analyzer(analyzer_id)
    if not analyzer:
        return {"error": "Analyzer not found"}

    summary = analyzer.get_personality_summary(user_id)
    return summary or {"error": "User not analyzed"}


if __name__ == "__main__":
    analyzer = PersonalityAnalyzer()

    dialogue = [
        {"text": "I'm curious about machine learning, can you explain how neural networks work?"},
        {"text": "That's interesting! I'd like to explore more about the math behind it."},
        {"text": "Thank you for explaining that so clearly!"},
    ]

    profile = analyzer.analyze_user("user_1", dialogue)
    print(f"Profile: {json.dumps(profile.to_dict(), indent=2)}")

    summary = analyzer.get_personality_summary("user_1")
    print(f"Summary: {json.dumps(summary, indent=2)}")
