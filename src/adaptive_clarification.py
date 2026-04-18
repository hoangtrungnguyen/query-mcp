"""Adaptive clarification learning and personalization"""

import json
from pathlib import Path
from datetime import datetime
from typing import Optional, List, Dict, Any
from dataclasses import dataclass, field
from enum import Enum

CLARIFY_DIR = Path.home() / ".memory-mcp" / "adaptive-clarification"
CLARIFY_DIR.mkdir(exist_ok=True, parents=True)


class ClarificationStyle(Enum):
    """Style of clarification question"""
    DIRECTIVE = "directive"  # Direct: "What do you mean by X?"
    SUGGESTIVE = "suggestive"  # Hints: "Did you mean X or Y?"
    EXPLORATORY = "exploratory"  # Open: "Tell me more about X"
    EXAMPLE_BASED = "example_based"  # Examples: "Like when you..."
    CONFIRMATION = "confirmation"  # Confirm: "So you're saying..."


@dataclass
class ClarificationAttempt:
    """Single clarification question asked"""
    attempt_id: str
    question: str
    style: ClarificationStyle
    topic: str
    turn_num: int
    user_understood: bool = False  # Did user understand what was being clarified?
    answer_given: Optional[str] = None
    clarity_improvement: float = 0.5  # 0-1, how much it improved clarity
    timestamp: str = ""

    def __post_init__(self):
        if not self.timestamp:
            self.timestamp = datetime.now().isoformat()

    def to_dict(self) -> Dict:
        """Serialize attempt"""
        return {
            "attempt_id": self.attempt_id,
            "style": self.style.value,
            "understood": self.user_understood,
            "improvement": round(self.clarity_improvement, 2),
        }


@dataclass
class StylePreference:
    """User preference for clarification style"""
    style: ClarificationStyle
    success_rate: float  # % of questions understood
    confidence: float  # How confident in preference (based on sample size)
    sample_size: int  # Number of observations
    user_feedback: List[str] = field(default_factory=list)

    def to_dict(self) -> Dict:
        """Serialize preference"""
        return {
            "style": self.style.value,
            "success_rate": round(self.success_rate, 2),
            "confidence": round(self.confidence, 2),
        }


@dataclass
class AdaptiveProfile:
    """User's adaptive clarification profile"""
    user_id: str
    style_preferences: Dict[ClarificationStyle, StylePreference] = field(default_factory=dict)
    preferred_style: Optional[ClarificationStyle] = None
    avoid_styles: List[ClarificationStyle] = field(default_factory=list)
    topic_strategies: Dict[str, ClarificationStyle] = field(default_factory=dict)  # Per-topic strategies
    attempts_history: List[ClarificationAttempt] = field(default_factory=list)
    last_updated: str = ""

    def __post_init__(self):
        if not self.last_updated:
            self.last_updated = datetime.now().isoformat()

    def to_dict(self) -> Dict:
        """Serialize profile"""
        return {
            "user_id": self.user_id,
            "preferred_style": self.preferred_style.value if self.preferred_style else None,
            "attempts": len(self.attempts_history),
            "topics_tracked": len(self.topic_strategies),
        }


class AdaptiveClarificationEngine:
    """Learn and adapt clarification strategies"""

    def __init__(self):
        self.profiles: Dict[str, AdaptiveProfile] = {}
        self.style_effectiveness: Dict[ClarificationStyle, List[float]] = {
            style: [] for style in ClarificationStyle
        }

    def get_or_create_profile(self, user_id: str) -> AdaptiveProfile:
        """Get user profile, create if doesn't exist"""
        if user_id not in self.profiles:
            profile = AdaptiveProfile(user_id=user_id)
            # Initialize style preferences
            for style in ClarificationStyle:
                profile.style_preferences[style] = StylePreference(
                    style=style,
                    success_rate=0.5,
                    confidence=0.0,
                    sample_size=0,
                )
            self.profiles[user_id] = profile

        return self.profiles[user_id]

    def record_attempt(
        self,
        user_id: str,
        question: str,
        style: ClarificationStyle,
        topic: str,
        turn_num: int,
    ) -> ClarificationAttempt:
        """Record clarification attempt"""
        profile = self.get_or_create_profile(user_id)

        attempt = ClarificationAttempt(
            attempt_id=f"att_{len(profile.attempts_history)}",
            question=question,
            style=style,
            topic=topic,
            turn_num=turn_num,
        )

        profile.attempts_history.append(attempt)
        return attempt

    def record_outcome(
        self,
        user_id: str,
        attempt_id: str,
        understood: bool,
        clarity_improvement: float,
        answer: str = "",
    ):
        """Record outcome of clarification attempt"""
        profile = self.get_or_create_profile(user_id)

        # Find attempt
        attempt = None
        for att in profile.attempts_history:
            if att.attempt_id == attempt_id:
                attempt = att
                break

        if not attempt:
            return

        attempt.user_understood = understood
        attempt.clarity_improvement = clarity_improvement
        attempt.answer_given = answer

        # Update style effectiveness
        style = attempt.style
        self.style_effectiveness[style].append(1.0 if understood else 0.0)

        # Update style preference
        pref = profile.style_preferences[style]
        if pref.sample_size == 0:
            pref.success_rate = 1.0 if understood else 0.0
            pref.sample_size = 1
        else:
            total_success = pref.success_rate * pref.sample_size
            total_success += 1.0 if understood else 0.0
            pref.sample_size += 1
            pref.success_rate = total_success / pref.sample_size

        # Confidence grows with sample size (sqrt function for diminishing returns)
        pref.confidence = min(1.0, (pref.sample_size / 10) ** 0.5)

        # Update preferred style if this is now best
        best_style = max(
            profile.style_preferences.values(),
            key=lambda p: p.success_rate if p.sample_size > 0 else 0,
        )
        if best_style.success_rate > 0.6 and best_style.confidence > 0.3:
            profile.preferred_style = best_style.style

        # Track avoid styles (success rate < 0.4, confidence > 0.3)
        profile.avoid_styles = [
            s for s, p in profile.style_preferences.items()
            if p.success_rate < 0.4 and p.confidence > 0.3
        ]

    def get_recommended_style(
        self,
        user_id: str,
        topic: str = None,
    ) -> ClarificationStyle:
        """Get recommended clarification style for user"""
        profile = self.get_or_create_profile(user_id)

        # Check topic-specific strategy
        if topic and topic in profile.topic_strategies:
            return profile.topic_strategies[topic]

        # Use preferred style if exists and confident
        if (
            profile.preferred_style
            and profile.style_preferences[profile.preferred_style].confidence > 0.3
        ):
            return profile.preferred_style

        # Find best style avoiding poor ones
        candidates = [
            s for s in ClarificationStyle
            if s not in profile.avoid_styles
        ]

        if candidates:
            return max(
                candidates,
                key=lambda s: profile.style_preferences[s].success_rate,
            )

        # Fallback
        return ClarificationStyle.DIRECTIVE

    def record_topic_strategy(
        self,
        user_id: str,
        topic: str,
        effective_style: ClarificationStyle,
    ):
        """Record which style works best for topic"""
        profile = self.get_or_create_profile(user_id)
        profile.topic_strategies[topic] = effective_style

    def get_profile_summary(self, user_id: str) -> Optional[Dict]:
        """Get user's clarification profile"""
        profile = self.get_or_create_profile(user_id)

        return {
            "user_id": user_id,
            "profile": profile.to_dict(),
            "style_preferences": {
                s.value: p.to_dict()
                for s, p in profile.style_preferences.items()
            },
            "preferred_style": profile.preferred_style.value if profile.preferred_style else None,
            "avoid_styles": [s.value for s in profile.avoid_styles],
            "topic_strategies": profile.topic_strategies,
        }


class ClarificationLearner:
    """Learn clarification strategies across users"""

    def __init__(self):
        self.engines: Dict[str, AdaptiveClarificationEngine] = {}

    def create_engine(self, engine_id: str) -> AdaptiveClarificationEngine:
        """Create engine"""
        engine = AdaptiveClarificationEngine()
        self.engines[engine_id] = engine
        return engine

    def get_engine(self, engine_id: str) -> Optional[AdaptiveClarificationEngine]:
        """Get engine"""
        return self.engines.get(engine_id)


# Global learner
clarification_learner = ClarificationLearner()


# MCP Tools

def create_clarification_engine(engine_id: str) -> dict:
    """Create clarification engine"""
    engine = clarification_learner.create_engine(engine_id)
    return {"engine_id": engine_id, "created": True}


def record_clarification_attempt(
    engine_id: str,
    user_id: str,
    question: str,
    style: str,
    topic: str,
    turn_num: int,
) -> dict:
    """Record clarification attempt"""
    engine = clarification_learner.get_engine(engine_id)
    if not engine:
        return {"error": "Engine not found"}

    try:
        style_enum = ClarificationStyle(style)
        attempt = engine.record_attempt(user_id, question, style_enum, topic, turn_num)
        return attempt.to_dict()
    except ValueError:
        return {"error": f"Invalid style: {style}"}


def record_clarification_outcome(
    engine_id: str,
    user_id: str,
    attempt_id: str,
    understood: bool,
    clarity_improvement: float,
) -> dict:
    """Record outcome"""
    engine = clarification_learner.get_engine(engine_id)
    if not engine:
        return {"error": "Engine not found"}

    engine.record_outcome(user_id, attempt_id, understood, clarity_improvement)
    return {"recorded": True}


def get_recommended_style(
    engine_id: str,
    user_id: str,
    topic: str = None,
) -> dict:
    """Get recommended style"""
    engine = clarification_learner.get_engine(engine_id)
    if not engine:
        return {"error": "Engine not found"}

    style = engine.get_recommended_style(user_id, topic)
    return {"recommended_style": style.value}


def get_user_profile(engine_id: str, user_id: str) -> dict:
    """Get user profile"""
    engine = clarification_learner.get_engine(engine_id)
    if not engine:
        return {"error": "Engine not found"}

    summary = engine.get_profile_summary(user_id)
    return summary or {"error": "User not found"}


if __name__ == "__main__":
    engine = AdaptiveClarificationEngine()

    # Record attempts
    att1 = engine.record_attempt("user_1", "What do you mean?", ClarificationStyle.DIRECTIVE, "topic_1", 1)
    engine.record_outcome("user_1", att1.attempt_id, True, 0.8)

    att2 = engine.record_attempt("user_1", "For example...", ClarificationStyle.EXAMPLE_BASED, "topic_1", 2)
    engine.record_outcome("user_1", att2.attempt_id, True, 0.9)

    # Get recommended
    recommended = engine.get_recommended_style("user_1", "topic_1")
    print(f"Recommended: {recommended}")

    # Get profile
    profile = engine.get_profile_summary("user_1")
    print(f"Profile: {json.dumps(profile, indent=2)}")
