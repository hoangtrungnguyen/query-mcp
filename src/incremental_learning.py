"""Incremental learning and continuous adaptation"""

import json
from pathlib import Path
from datetime import datetime
from typing import Optional, List, Dict, Any
from dataclasses import dataclass, field

LEARNING_DIR = Path.home() / ".memory-mcp" / "incremental-learning"
LEARNING_DIR.mkdir(exist_ok=True, parents=True)


@dataclass
class LearningSignal:
    """Signal from user feedback for learning"""
    signal_id: str
    interaction_id: str
    signal_type: str  # "positive", "negative", "correction"
    magnitude: float  # 0-1
    pattern: str  # What pattern to learn
    created_at: str = ""

    def __post_init__(self):
        if not self.created_at:
            self.created_at = datetime.now().isoformat()

    def to_dict(self) -> Dict:
        return {
            "signal_type": self.signal_type,
            "magnitude": round(self.magnitude, 2),
            "pattern": self.pattern,
        }


@dataclass
class LearnedPattern:
    """Pattern learned from interactions"""
    pattern_id: str
    pattern_description: str
    confidence: float
    times_reinforced: int = 0
    first_learned: str = ""
    last_reinforced: str = ""

    def __post_init__(self):
        if not self.first_learned:
            self.first_learned = datetime.now().isoformat()
        if not self.last_reinforced:
            self.last_reinforced = self.first_learned

    def reinforce(self, confidence_boost: float = 0.1):
        """Reinforce pattern through positive feedback"""
        self.confidence = min(1.0, self.confidence + confidence_boost)
        self.times_reinforced += 1
        self.last_reinforced = datetime.now().isoformat()

    def to_dict(self) -> Dict:
        return {
            "pattern": self.pattern_description,
            "confidence": round(self.confidence, 2),
            "reinforcements": self.times_reinforced,
        }


class IncrementalLearner:
    """Learn incrementally from interactions"""

    def __init__(self):
        self.learning_signals: List[LearningSignal] = []
        self.learned_patterns: Dict[str, LearnedPattern] = {}
        self.interaction_count = 0

    def record_signal(
        self,
        interaction_id: str,
        signal_type: str,
        magnitude: float,
        pattern: str,
    ) -> LearningSignal:
        """Record learning signal"""
        signal = LearningSignal(
            signal_id=f"sig_{len(self.learning_signals)}",
            interaction_id=interaction_id,
            signal_type=signal_type,
            magnitude=magnitude,
            pattern=pattern,
        )
        self.learning_signals.append(signal)
        self.interaction_count += 1

        # Update or create pattern
        if pattern not in self.learned_patterns:
            self.learned_patterns[pattern] = LearnedPattern(
                pattern_id=f"pat_{len(self.learned_patterns)}",
                pattern_description=pattern,
                confidence=magnitude,
            )
        else:
            pattern_obj = self.learned_patterns[pattern]
            if signal_type == "positive":
                pattern_obj.reinforce(magnitude * 0.1)
            elif signal_type == "negative":
                pattern_obj.confidence = max(0.0, pattern_obj.confidence - (magnitude * 0.1))

        return signal

    def get_learned_patterns(self) -> List[LearnedPattern]:
        """Get patterns learned so far"""
        return sorted(
            self.learned_patterns.values(),
            key=lambda x: x.confidence,
            reverse=True
        )

    def get_learning_progress(self) -> Dict:
        """Get learning progress metrics"""
        high_confidence = sum(
            1 for p in self.learned_patterns.values()
            if p.confidence > 0.7
        )

        return {
            "interactions": self.interaction_count,
            "patterns_learned": len(self.learned_patterns),
            "high_confidence_patterns": high_confidence,
            "avg_confidence": (
                sum(p.confidence for p in self.learned_patterns.values()) / len(self.learned_patterns)
                if self.learned_patterns else 0.0
            ),
        }


# Global learner
incremental_learner = IncrementalLearner()


def record_learning_signal(
    interaction_id: str,
    signal_type: str,
    magnitude: float,
    pattern: str,
) -> dict:
    """Record learning signal"""
    signal = incremental_learner.record_signal(interaction_id, signal_type, magnitude, pattern)
    return signal.to_dict()


def get_learned_patterns() -> dict:
    """Get learned patterns"""
    patterns = incremental_learner.get_learned_patterns()
    return {
        "patterns": [p.to_dict() for p in patterns],
        "count": len(patterns),
    }


def get_learning_progress() -> dict:
    """Get learning progress"""
    return incremental_learner.get_learning_progress()
