"""Satisfaction and feedback collection for conversation quality assessment"""

import json
from pathlib import Path
from datetime import datetime
from typing import Optional, List, Dict, Any
from dataclasses import dataclass, field
from enum import Enum

FEEDBACK_DIR = Path.home() / ".memory-mcp" / "satisfaction-feedback"
FEEDBACK_DIR.mkdir(exist_ok=True, parents=True)


class FeedbackType(Enum):
    """Type of feedback signal"""
    EXPLICIT_RATING = "explicit_rating"  # User rated response (1-5 stars)
    IMPLICIT_ENGAGEMENT = "implicit_engagement"  # Inferred from behavior
    FOLLOW_UP = "follow_up"  # User asked follow-up question
    ABANDONMENT = "abandonment"  # User stopped responding
    REPHRASE_REQUEST = "rephrase_request"  # User asked to rephrase
    CONTINUATION = "continuation"  # User continued conversation


class SatisfactionLevel(Enum):
    """Overall satisfaction assessment"""
    VERY_SATISFIED = "very_satisfied"  # 4.5-5.0
    SATISFIED = "satisfied"  # 3.5-4.4
    NEUTRAL = "neutral"  # 2.5-3.4
    DISSATISFIED = "dissatisfied"  # 1.5-2.4
    VERY_DISSATISFIED = "very_dissatisfied"  # 0-1.4


@dataclass
class FeedbackSignal:
    """Single feedback signal from user behavior"""
    signal_id: str
    signal_type: FeedbackType
    turn_num: int
    explicit_score: Optional[float] = None  # 1-5 if rated explicitly
    implicit_score: float = 0.5  # Inferred 0-1 score
    evidence: str = ""  # What indicates this feedback
    timestamp: str = ""

    def __post_init__(self):
        if not self.timestamp:
            self.timestamp = datetime.now().isoformat()

    def to_dict(self) -> Dict:
        """Serialize signal"""
        return {
            "signal_id": self.signal_id,
            "type": self.signal_type.value,
            "score": self.explicit_score or round(self.implicit_score, 2),
            "turn": self.turn_num,
        }


@dataclass
class SatisfactionProfile:
    """User's satisfaction profile across conversations"""
    user_id: str
    feedback_signals: List[FeedbackSignal] = field(default_factory=list)
    overall_score: float = 0.5  # 0-5 scale
    satisfaction_level: SatisfactionLevel = SatisfactionLevel.NEUTRAL
    response_quality_score: float = 0.5  # How good responses are
    relevance_score: float = 0.5  # How relevant responses are
    clarity_score: float = 0.5  # How clear responses are
    areas_of_strength: List[str] = field(default_factory=list)
    areas_for_improvement: List[str] = field(default_factory=list)
    recommendation_likelihood: float = 0.5  # NPS-like metric
    total_conversations: int = 0
    last_updated: str = ""

    def __post_init__(self):
        if not self.last_updated:
            self.last_updated = datetime.now().isoformat()

    def to_dict(self) -> Dict:
        """Serialize profile"""
        return {
            "user_id": self.user_id,
            "overall_score": round(self.overall_score, 2),
            "satisfaction": self.satisfaction_level.value,
            "recommendation_likelihood": round(self.recommendation_likelihood, 2),
            "conversations": self.total_conversations,
        }


class SatisfactionAnalyzer:
    """Analyze satisfaction signals"""

    @staticmethod
    def infer_implicit_satisfaction(
        signal_type: FeedbackType,
        context: str = "",
    ) -> float:
        """Infer satisfaction from implicit signals"""
        signal_scores = {
            FeedbackType.FOLLOW_UP: 0.8,  # Asking follow-up = satisfied
            FeedbackType.CONTINUATION: 0.75,  # Continuing = engaged
            FeedbackType.IMPLICIT_ENGAGEMENT: 0.6,  # Active engagement = decent
            FeedbackType.REPHRASE_REQUEST: 0.4,  # Asking to rephrase = confused
            FeedbackType.ABANDONMENT: 0.1,  # Stopped = very dissatisfied
        }
        return signal_scores.get(signal_type, 0.5)

    @staticmethod
    def calculate_overall_score(
        signals: List[FeedbackSignal],
    ) -> float:
        """Calculate overall satisfaction from all signals"""
        if not signals:
            return 0.5

        total = 0
        for signal in signals:
            score = signal.explicit_score if signal.explicit_score else signal.implicit_score
            # Convert 0-1 scale to 1-5 scale if implicit
            if signal.explicit_score is None:
                score = 1 + (score * 4)  # 0-1 becomes 1-5
            total += score

        return total / len(signals)

    @staticmethod
    def determine_satisfaction_level(overall_score: float) -> SatisfactionLevel:
        """Map score to satisfaction level"""
        if overall_score >= 4.5:
            return SatisfactionLevel.VERY_SATISFIED
        elif overall_score >= 3.5:
            return SatisfactionLevel.SATISFIED
        elif overall_score >= 2.5:
            return SatisfactionLevel.NEUTRAL
        elif overall_score >= 1.5:
            return SatisfactionLevel.DISSATISFIED
        else:
            return SatisfactionLevel.VERY_DISSATISFIED


class SatisfactionCollector:
    """Collect and track satisfaction feedback"""

    def __init__(self):
        self.profiles: Dict[str, SatisfactionProfile] = {}

    def get_or_create_profile(self, user_id: str) -> SatisfactionProfile:
        """Get or create satisfaction profile"""
        if user_id not in self.profiles:
            self.profiles[user_id] = SatisfactionProfile(user_id=user_id)
        return self.profiles[user_id]

    def record_feedback_signal(
        self,
        user_id: str,
        signal_type: FeedbackType,
        turn_num: int,
        explicit_score: Optional[float] = None,
        evidence: str = "",
    ) -> FeedbackSignal:
        """Record feedback signal"""
        profile = self.get_or_create_profile(user_id)

        implicit_score = SatisfactionAnalyzer.infer_implicit_satisfaction(
            signal_type, evidence
        )

        signal = FeedbackSignal(
            signal_id=f"sig_{len(profile.feedback_signals)}",
            signal_type=signal_type,
            turn_num=turn_num,
            explicit_score=explicit_score,
            implicit_score=implicit_score,
            evidence=evidence,
        )

        profile.feedback_signals.append(signal)
        self._update_profile_scores(profile)

        return signal

    def _update_profile_scores(self, profile: SatisfactionProfile):
        """Update profile scores based on signals"""
        if not profile.feedback_signals:
            return

        # Calculate overall score
        profile.overall_score = SatisfactionAnalyzer.calculate_overall_score(
            profile.feedback_signals
        )

        # Determine satisfaction level
        profile.satisfaction_level = SatisfactionAnalyzer.determine_satisfaction_level(
            profile.overall_score
        )

        # Estimate recommendation likelihood (NPS-like)
        if profile.satisfaction_level == SatisfactionLevel.VERY_SATISFIED:
            profile.recommendation_likelihood = 0.9
        elif profile.satisfaction_level == SatisfactionLevel.SATISFIED:
            profile.recommendation_likelihood = 0.7
        elif profile.satisfaction_level == SatisfactionLevel.NEUTRAL:
            profile.recommendation_likelihood = 0.5
        elif profile.satisfaction_level == SatisfactionLevel.DISSATISFIED:
            profile.recommendation_likelihood = 0.2
        else:
            profile.recommendation_likelihood = 0.0

    def record_conversation_completion(
        self,
        user_id: str,
        conversation_success: bool,
        quality_rating: Optional[float] = None,
    ):
        """Record conversation completion and satisfaction"""
        profile = self.get_or_create_profile(user_id)
        profile.total_conversations += 1

        if quality_rating:
            signal_type = (
                FeedbackType.EXPLICIT_RATING
                if quality_rating
                else FeedbackType.IMPLICIT_ENGAGEMENT
            )
            self.record_feedback_signal(
                user_id,
                signal_type,
                turn_num=profile.total_conversations,
                explicit_score=quality_rating,
            )
        elif conversation_success:
            self.record_feedback_signal(
                user_id,
                FeedbackType.CONTINUATION,
                turn_num=profile.total_conversations,
            )

    def get_satisfaction_summary(self, user_id: str) -> Optional[Dict[str, Any]]:
        """Get satisfaction summary for user"""
        profile = self.get_or_create_profile(user_id)

        explicit_signals = [s for s in profile.feedback_signals if s.explicit_score]
        implicit_signals = [s for s in profile.feedback_signals if not s.explicit_score]

        return {
            "user_id": user_id,
            "profile": profile.to_dict(),
            "explicit_feedbacks": len(explicit_signals),
            "implicit_signals": len(implicit_signals),
            "quality_scores": {
                "response_quality": round(profile.response_quality_score, 2),
                "relevance": round(profile.relevance_score, 2),
                "clarity": round(profile.clarity_score, 2),
            },
            "recommendation_likelihood": round(profile.recommendation_likelihood, 2),
        }


class SatisfactionManager:
    """Manage satisfaction tracking across users"""

    def __init__(self):
        self.collectors: Dict[str, SatisfactionCollector] = {}

    def create_collector(self, collector_id: str) -> SatisfactionCollector:
        """Create satisfaction collector"""
        collector = SatisfactionCollector()
        self.collectors[collector_id] = collector
        return collector

    def get_collector(self, collector_id: str) -> Optional[SatisfactionCollector]:
        """Get collector"""
        return self.collectors.get(collector_id)


# Global manager
satisfaction_manager = SatisfactionManager()


# MCP Tools

def create_satisfaction_collector(collector_id: str) -> dict:
    """Create satisfaction collector"""
    collector = satisfaction_manager.create_collector(collector_id)
    return {"collector_id": collector_id, "created": True}


def record_feedback_signal(
    collector_id: str,
    user_id: str,
    signal_type: str,
    turn_num: int,
    explicit_score: Optional[float] = None,
    evidence: str = "",
) -> dict:
    """Record feedback signal"""
    collector = satisfaction_manager.get_collector(collector_id)
    if not collector:
        return {"error": "Collector not found"}

    try:
        stype = FeedbackType(signal_type)
        signal = collector.record_feedback_signal(
            user_id, stype, turn_num, explicit_score, evidence
        )
        return signal.to_dict()
    except ValueError:
        return {"error": f"Invalid signal type: {signal_type}"}


def record_conversation_completion(
    collector_id: str,
    user_id: str,
    success: bool,
    quality_rating: Optional[float] = None,
) -> dict:
    """Record conversation completion"""
    collector = satisfaction_manager.get_collector(collector_id)
    if not collector:
        return {"error": "Collector not found"}

    collector.record_conversation_completion(user_id, success, quality_rating)
    return {"recorded": True}


def get_satisfaction_summary(collector_id: str, user_id: str) -> dict:
    """Get satisfaction summary"""
    collector = satisfaction_manager.get_collector(collector_id)
    if not collector:
        return {"error": "Collector not found"}

    summary = collector.get_satisfaction_summary(user_id)
    return summary or {"error": "User not found"}


if __name__ == "__main__":
    collector = SatisfactionCollector()

    # Record signals
    collector.record_feedback_signal(
        "user_1",
        FeedbackType.EXPLICIT_RATING,
        1,
        explicit_score=4.5,
        evidence="User rated response as excellent",
    )

    collector.record_feedback_signal(
        "user_1",
        FeedbackType.FOLLOW_UP,
        2,
        evidence="User asked follow-up question",
    )

    # Record completion
    collector.record_conversation_completion("user_1", True, 4.2)

    # Get summary
    summary = collector.get_satisfaction_summary("user_1")
    print(f"Summary: {json.dumps(summary, indent=2)}")
