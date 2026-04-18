"""Human-in-the-loop feedback and iterative refinement"""

import json
from pathlib import Path
from datetime import datetime
from typing import Optional, List, Dict, Any
from dataclasses import dataclass, field
from enum import Enum

FEEDBACK_DIR = Path.home() / ".memory-mcp" / "human-feedback"
FEEDBACK_DIR.mkdir(exist_ok=True, parents=True)


class FeedbackType(Enum):
    """Types of feedback"""
    LIKE = "like"  # Approval
    DISLIKE = "dislike"  # Disapproval
    CORRECTION = "correction"  # Incorrect response
    CLARIFICATION = "clarification"  # Need clearer explanation
    INCOMPLETE = "incomplete"  # Missing information
    IRRELEVANT = "irrelevant"  # Off-topic
    UNSAFE = "unsafe"  # Inappropriate/harmful
    EXCELLENT = "excellent"  # Exemplary


class FeedbackImpact(Enum):
    """Impact level of feedback"""
    MINOR = 0.1
    MODERATE = 0.5
    MAJOR = 0.8
    CRITICAL = 1.0


@dataclass
class HumanFeedback:
    """User feedback on agent response"""
    feedback_id: str
    response_id: str
    user_id: str
    feedback_type: FeedbackType
    rating: int  # 1-5 stars
    comment: Optional[str] = None
    suggested_correction: Optional[str] = None
    impact: FeedbackImpact = FeedbackImpact.MODERATE
    helpful: Optional[bool] = None  # Was the feedback useful?
    created_at: str = ""

    def __post_init__(self):
        if not self.created_at:
            self.created_at = datetime.now().isoformat()

    def to_dict(self) -> Dict:
        """Serialize feedback"""
        return {
            "feedback_id": self.feedback_id,
            "response_id": self.response_id,
            "type": self.feedback_type.value,
            "rating": self.rating,
            "has_comment": self.comment is not None,
            "impact": self.impact.name,
            "created_at": self.created_at,
        }


@dataclass
class FeedbackRound:
    """Single feedback round (query, response, feedback)"""
    round_id: str
    query: str
    original_response: str
    feedback_list: List[HumanFeedback] = field(default_factory=list)
    refined_responses: List[str] = field(default_factory=list)
    consensus_feedback: Optional[str] = None
    created_at: str = ""

    def __post_init__(self):
        if not self.created_at:
            self.created_at = datetime.now().isoformat()

    def to_dict(self) -> Dict:
        """Serialize round"""
        return {
            "round_id": self.round_id,
            "query": self.query[:100],
            "feedback_count": len(self.feedback_list),
            "refined_count": len(self.refined_responses),
            "consensus": self.consensus_feedback is not None,
        }


@dataclass
class LearningSignal:
    """Signal extracted from feedback"""
    signal_id: str
    feedback_id: str
    signal_type: str  # "pattern", "rule", "boundary", "weight"
    description: str
    confidence: float  # 0-1
    applies_to: List[str] = field(default_factory=list)  # Query patterns this applies to
    created_at: str = ""

    def __post_init__(self):
        if not self.created_at:
            self.created_at = datetime.now().isoformat()

    def to_dict(self) -> Dict:
        """Serialize signal"""
        return {
            "signal_id": self.signal_id,
            "type": self.signal_type,
            "confidence": self.confidence,
            "applies_to_queries": len(self.applies_to),
        }


class FeedbackAnalyzer:
    """Analyze feedback patterns"""

    @staticmethod
    def aggregate_feedback(feedback_list: List[HumanFeedback]) -> Dict[str, Any]:
        """Aggregate multiple feedback items"""
        if not feedback_list:
            return {}

        type_counts = {}
        total_rating = 0
        corrections = []

        for fb in feedback_list:
            type_counts[fb.feedback_type.value] = type_counts.get(fb.feedback_type.value, 0) + 1
            total_rating += fb.rating

            if fb.suggested_correction:
                corrections.append(fb.suggested_correction)

        avg_rating = total_rating / len(feedback_list)
        most_common_type = max(type_counts.items(), key=lambda x: x[1])[0] if type_counts else None

        return {
            "feedback_count": len(feedback_list),
            "avg_rating": avg_rating,
            "most_common_type": most_common_type,
            "type_distribution": type_counts,
            "corrections_suggested": len(corrections),
            "consensus_rating": "positive" if avg_rating >= 3.5 else "needs_improvement",
        }

    @staticmethod
    def identify_issues(feedback_list: List[HumanFeedback]) -> List[str]:
        """Identify issues from feedback"""
        issues = []

        # Count negative feedback
        negative = [
            f for f in feedback_list
            if f.feedback_type in [
                FeedbackType.DISLIKE,
                FeedbackType.CORRECTION,
                FeedbackType.INCOMPLETE,
                FeedbackType.UNSAFE,
            ]
        ]

        if len(negative) > len(feedback_list) * 0.5:  # >50% negative
            issues.append("High rate of negative feedback")

        # Check for safety concerns
        unsafe = [f for f in feedback_list if f.feedback_type == FeedbackType.UNSAFE]
        if unsafe:
            issues.append("Safety concern flagged")

        # Check for consistency
        ratings = [f.rating for f in feedback_list]
        if ratings and max(ratings) - min(ratings) >= 4:  # Wide variance
            issues.append("Inconsistent response quality")

        return issues

    @staticmethod
    def extract_rules(feedback_list: List[HumanFeedback]) -> List[str]:
        """Extract behavioral rules from feedback"""
        rules = []

        corrections = [
            f.suggested_correction for f in feedback_list
            if f.suggested_correction
        ]

        if len(corrections) > 2:
            rules.append("Apply suggested corrections to similar queries")

        incompletes = [
            f for f in feedback_list
            if f.feedback_type == FeedbackType.INCOMPLETE
        ]

        if len(incompletes) > 1:
            rules.append("Provide more comprehensive responses")

        return rules


class RefinementEngine:
    """Refine agent behavior based on feedback"""

    def __init__(self):
        self.feedback_rounds: Dict[str, FeedbackRound] = {}
        self.learning_signals: Dict[str, LearningSignal] = {}
        self.analyzer = FeedbackAnalyzer()

    def create_feedback_round(
        self,
        round_id: str,
        query: str,
        response: str,
    ) -> FeedbackRound:
        """Create new feedback round"""
        round_obj = FeedbackRound(
            round_id=round_id,
            query=query,
            original_response=response,
        )
        self.feedback_rounds[round_id] = round_obj
        return round_obj

    def add_feedback(
        self,
        round_id: str,
        feedback_id: str,
        user_id: str,
        feedback_type: FeedbackType,
        rating: int,
        comment: Optional[str] = None,
        correction: Optional[str] = None,
    ) -> Optional[HumanFeedback]:
        """Add feedback to round"""
        if round_id not in self.feedback_rounds:
            return None

        feedback = HumanFeedback(
            feedback_id=feedback_id,
            response_id=f"resp_{round_id}",
            user_id=user_id,
            feedback_type=feedback_type,
            rating=rating,
            comment=comment,
            suggested_correction=correction,
        )

        self.feedback_rounds[round_id].feedback_list.append(feedback)
        return feedback

    def extract_learning_signals(self, round_id: str) -> List[LearningSignal]:
        """Extract learning signals from feedback"""
        if round_id not in self.feedback_rounds:
            return []

        round_obj = self.feedback_rounds[round_id]
        signals = []

        # Extract from rules
        rules = self.analyzer.extract_rules(round_obj.feedback_list)
        for i, rule in enumerate(rules):
            signal = LearningSignal(
                signal_id=f"sig_{round_id}_{i}",
                feedback_id=f"fb_{round_id}",
                signal_type="rule",
                description=rule,
                confidence=0.7,
                applies_to=[round_obj.query],
            )
            self.learning_signals[signal.signal_id] = signal
            signals.append(signal)

        # Extract from corrections
        corrections = [
            f for f in round_obj.feedback_list
            if f.suggested_correction
        ]

        if corrections:
            signal = LearningSignal(
                signal_id=f"sig_correction_{round_id}",
                feedback_id=f"fb_{round_id}",
                signal_type="correction_pattern",
                description=f"Common correction pattern: {corrections[0].suggested_correction[:50]}",
                confidence=min(1.0, len(corrections) * 0.3),
                applies_to=[round_obj.query],
            )
            self.learning_signals[signal.signal_id] = signal
            signals.append(signal)

        return signals

    def generate_refined_response(
        self,
        round_id: str,
    ) -> Optional[str]:
        """Generate refined response based on feedback"""
        if round_id not in self.feedback_rounds:
            return None

        round_obj = self.feedback_rounds[round_id]
        feedback_agg = self.analyzer.aggregate_feedback(round_obj.feedback_list)

        # If there are corrections, synthesize them
        corrections = [
            f.suggested_correction for f in round_obj.feedback_list
            if f.suggested_correction
        ]

        if corrections:
            # Use first correction as basis, incorporate others
            refined = corrections[0]
            if len(corrections) > 1:
                refined += f" (incorporating {len(corrections)-1} alternative suggestions)"
            round_obj.refined_responses.append(refined)
            return refined

        # If overall positive, no major refinement needed
        if feedback_agg.get("consensus_rating") == "positive":
            refined = round_obj.original_response
            round_obj.refined_responses.append(refined)
            return refined

        # If needs improvement, create placeholder
        refined = f"[Refined based on feedback] {round_obj.original_response}"
        round_obj.refined_responses.append(refined)
        return refined

    def get_feedback_summary(self, round_id: str) -> Optional[Dict[str, Any]]:
        """Get comprehensive feedback summary"""
        if round_id not in self.feedback_rounds:
            return None

        round_obj = self.feedback_rounds[round_id]
        agg = self.analyzer.aggregate_feedback(round_obj.feedback_list)
        issues = self.analyzer.identify_issues(round_obj.feedback_list)

        return {
            "round_id": round_id,
            "query": round_obj.query[:100],
            "feedback_count": agg.get("feedback_count", 0),
            "avg_rating": agg.get("avg_rating", 0),
            "consensus": agg.get("consensus_rating", "unknown"),
            "issues_identified": issues,
            "refinements_available": len(round_obj.refined_responses),
        }

    def get_all_feedback_data(self) -> Dict[str, Any]:
        """Get all feedback and learning data"""
        total_feedback = sum(
            len(r.feedback_list) for r in self.feedback_rounds.values()
        )
        avg_rating = (
            sum(
                f.rating for r in self.feedback_rounds.values()
                for f in r.feedback_list
            ) / total_feedback
            if total_feedback > 0 else 0.0
        )

        return {
            "total_rounds": len(self.feedback_rounds),
            "total_feedback_items": total_feedback,
            "avg_rating": avg_rating,
            "learning_signals": len(self.learning_signals),
            "refinements_made": sum(
                len(r.refined_responses)
                for r in self.feedback_rounds.values()
            ),
        }


class HumanFeedbackManager:
    """Manage human feedback systems"""

    def __init__(self):
        self.engines: Dict[str, RefinementEngine] = {}

    def create_engine(self, engine_id: str) -> RefinementEngine:
        """Create feedback engine"""
        engine = RefinementEngine()
        self.engines[engine_id] = engine
        return engine

    def get_engine(self, engine_id: str) -> Optional[RefinementEngine]:
        """Get feedback engine"""
        return self.engines.get(engine_id)


# Global manager
feedback_manager = HumanFeedbackManager()


# MCP Tools

def create_feedback_engine(engine_id: str) -> dict:
    """Create human feedback engine"""
    engine = feedback_manager.create_engine(engine_id)
    return {"engine_id": engine_id, "created": True}


def create_feedback_round(
    engine_id: str,
    round_id: str,
    query: str,
    response: str,
) -> dict:
    """Create feedback round"""
    engine = feedback_manager.get_engine(engine_id)
    if not engine:
        return {"error": "Engine not found"}

    round_obj = engine.create_feedback_round(round_id, query, response)
    return round_obj.to_dict()


def submit_feedback(
    engine_id: str,
    round_id: str,
    feedback_id: str,
    user_id: str,
    feedback_type: str,
    rating: int,
    comment: str = None,
    correction: str = None,
) -> dict:
    """Submit human feedback"""
    engine = feedback_manager.get_engine(engine_id)
    if not engine:
        return {"error": "Engine not found"}

    feedback = engine.add_feedback(
        round_id,
        feedback_id,
        user_id,
        FeedbackType(feedback_type),
        rating,
        comment,
        correction,
    )

    return feedback.to_dict() if feedback else {"error": "Round not found"}


def extract_learning_signals(engine_id: str, round_id: str) -> dict:
    """Extract learning signals from feedback"""
    engine = feedback_manager.get_engine(engine_id)
    if not engine:
        return {"error": "Engine not found"}

    signals = engine.extract_learning_signals(round_id)
    return {
        "round_id": round_id,
        "signals": [s.to_dict() for s in signals],
        "count": len(signals),
    }


def get_refined_response(engine_id: str, round_id: str) -> dict:
    """Get refined response from feedback"""
    engine = feedback_manager.get_engine(engine_id)
    if not engine:
        return {"error": "Engine not found"}

    refined = engine.generate_refined_response(round_id)
    return {
        "round_id": round_id,
        "refined_response": refined or "No refinement available",
    }


def get_feedback_summary(engine_id: str, round_id: str) -> dict:
    """Get feedback summary"""
    engine = feedback_manager.get_engine(engine_id)
    if not engine:
        return {"error": "Engine not found"}

    summary = engine.get_feedback_summary(round_id)
    return summary or {"error": "Round not found"}


def get_all_feedback_data(engine_id: str) -> dict:
    """Get all feedback data"""
    engine = feedback_manager.get_engine(engine_id)
    if not engine:
        return {"error": "Engine not found"}

    return engine.get_all_feedback_data()


if __name__ == "__main__":
    # Test human feedback
    manager = HumanFeedbackManager()
    engine = manager.create_engine("engine_1")

    # Create feedback round
    round_obj = engine.create_feedback_round(
        "round_1",
        "What is Python?",
        "Python is a programming language.",
    )
    print(f"Round: {round_obj.round_id}")

    # Add multiple feedback items
    engine.add_feedback(
        "round_1",
        "fb_1",
        "user_1",
        FeedbackType.LIKE,
        5,
        comment="Good answer",
    )
    engine.add_feedback(
        "round_1",
        "fb_2",
        "user_2",
        FeedbackType.INCOMPLETE,
        3,
        comment="Need more details",
        correction="Python is a high-level, interpreted programming language known for simplicity.",
    )

    # Extract signals
    signals = engine.extract_learning_signals("round_1")
    print(f"Signals: {len(signals)}")

    # Generate refined response
    refined = engine.generate_refined_response("round_1")
    print(f"Refined: {refined}")

    # Feedback summary
    summary = engine.get_feedback_summary("round_1")
    print(f"Summary: {json.dumps(summary, indent=2)}")

    # All feedback data
    all_data = engine.get_all_feedback_data()
    print(f"All data: {json.dumps(all_data, indent=2)}")
