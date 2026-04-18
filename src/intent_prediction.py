"""Proactive intent prediction: forecast user's next questions and prepare context"""

import json
from pathlib import Path
from datetime import datetime
from typing import Optional, List, Dict, Any
from dataclasses import dataclass, field
from enum import Enum

INTENT_DIR = Path.home() / ".memory-mcp" / "intent-prediction"
INTENT_DIR.mkdir(exist_ok=True, parents=True)


class IntentType(Enum):
    """Category of predicted intent"""
    CLARIFICATION = "clarification"  # User wants clarification
    ELABORATION = "elaboration"  # User wants more detail
    EXAMPLE = "example"  # User wants an example
    COMPARISON = "comparison"  # User wants comparison with alternatives
    APPLICATION = "application"  # User wants to apply knowledge
    VERIFICATION = "verification"  # User wants to verify understanding
    NEXT_TOPIC = "next_topic"  # User wants to move to new topic
    DISAGREE = "disagree"  # User may disagree


class PredictionConfidence(Enum):
    """Confidence in prediction"""
    VERY_HIGH = "very_high"  # >0.8
    HIGH = "high"  # 0.6-0.8
    MODERATE = "moderate"  # 0.4-0.6
    LOW = "low"  # 0.2-0.4
    VERY_LOW = "very_low"  # <0.2


@dataclass
class IntentSignal:
    """Signal indicating user intent"""
    signal_type: str  # "questioning", "engagement_level", "topic_interest"
    value: str  # Observed signal
    strength: float  # 0-1, how strong this signal is
    turn_num: int

    def to_dict(self) -> Dict:
        """Serialize signal"""
        return {
            "signal_type": self.signal_type,
            "strength": round(self.strength, 2),
        }


@dataclass
class PredictedIntent:
    """Predicted user intent"""
    prediction_id: str
    primary_intent: IntentType
    secondary_intents: List[IntentType]
    confidence: float  # 0-1
    supporting_signals: List[IntentSignal] = field(default_factory=list)
    suggested_actions: List[str] = field(default_factory=list)
    predicted_turn: int = 0
    actual_intent: Optional[IntentType] = None
    correct: bool = False

    def to_dict(self) -> Dict:
        """Serialize prediction"""
        return {
            "prediction_id": self.prediction_id,
            "primary_intent": self.primary_intent.value,
            "confidence": round(self.confidence, 2),
            "correct": self.correct,
        }


@dataclass
class IntentPattern:
    """Learned pattern of user intents"""
    pattern_id: str
    prior_topic: str
    common_next_intents: Dict[IntentType, float]  # Intent -> frequency
    frequent_questions: List[str]
    sample_size: int

    def to_dict(self) -> Dict:
        """Serialize pattern"""
        return {
            "pattern_id": self.pattern_id,
            "prior_topic": self.prior_topic,
            "sample_size": self.sample_size,
        }


class IntentDetector:
    """Detect user intent signals"""

    @staticmethod
    def detect_clarification_intent(response: str, turn_num: int) -> IntentSignal:
        """Detect if user wants clarification"""
        clarification_words = ["what", "how", "why", "explain", "mean", "confused"]
        signal_strength = (
            sum(1 for w in clarification_words if w in response.lower()) / len(clarification_words)
        )

        return IntentSignal(
            signal_type="clarification_request",
            value=response[:50],
            strength=signal_strength,
            turn_num=turn_num,
        )

    @staticmethod
    def detect_elaboration_intent(response: str, turn_num: int) -> IntentSignal:
        """Detect if user wants more detail"""
        elaboration_words = ["more", "detail", "deeper", "elaborate", "tell me more", "further"]
        signal_strength = (
            sum(1 for w in elaboration_words if w in response.lower())
            / len(elaboration_words)
        )

        return IntentSignal(
            signal_type="elaboration_request",
            value=response[:50],
            strength=signal_strength,
            turn_num=turn_num,
        )

    @staticmethod
    def detect_example_intent(response: str, turn_num: int) -> IntentSignal:
        """Detect if user wants examples"""
        example_words = ["example", "instance", "like", "show", "demonstrate", "concrete"]
        signal_strength = (
            sum(1 for w in example_words if w in response.lower()) / len(example_words)
        )

        return IntentSignal(
            signal_type="example_request",
            value=response[:50],
            strength=signal_strength,
            turn_num=turn_num,
        )


class IntentPredictor:
    """Predict user intents from conversation patterns"""

    def __init__(self):
        self.predictions: Dict[str, PredictedIntent] = {}
        self.patterns: Dict[str, IntentPattern] = {}
        self.signal_history: List[IntentSignal] = []

    def predict_next_intent(
        self,
        conversation_history: List[str],
        current_topic: str,
        turn_num: int,
    ) -> PredictedIntent:
        """Predict user's likely next intent"""
        signals = []

        # Analyze recent responses for intent signals
        if conversation_history:
            recent = conversation_history[-1]

            signals.append(IntentDetector.detect_clarification_intent(recent, turn_num))
            signals.append(IntentDetector.detect_elaboration_intent(recent, turn_num))
            signals.append(IntentDetector.detect_example_intent(recent, turn_num))

        self.signal_history.extend(signals)

        # Determine primary intent based on strongest signal
        strongest_signal = max(signals, key=lambda s: s.strength)

        signal_to_intent = {
            "clarification_request": IntentType.CLARIFICATION,
            "elaboration_request": IntentType.ELABORATION,
            "example_request": IntentType.EXAMPLE,
        }

        primary_intent = signal_to_intent.get(strongest_signal.signal_type, IntentType.ELABORATION)

        # Secondary intents
        secondary_intents = [
            signal_to_intent.get(s.signal_type, IntentType.ELABORATION)
            for s in signals
            if s.strength > 0.2 and signal_to_intent.get(s.signal_type) != primary_intent
        ]

        # Calculate confidence
        confidence = strongest_signal.strength

        # Generate suggested actions
        suggested_actions = self._suggest_actions(primary_intent)

        prediction = PredictedIntent(
            prediction_id=f"pred_{len(self.predictions)}",
            primary_intent=primary_intent,
            secondary_intents=secondary_intents,
            confidence=confidence,
            supporting_signals=signals,
            suggested_actions=suggested_actions,
            predicted_turn=turn_num,
        )

        self.predictions[prediction.prediction_id] = prediction
        return prediction

    @staticmethod
    def _suggest_actions(intent: IntentType) -> List[str]:
        """Suggest actions based on predicted intent"""
        suggestions = {
            IntentType.CLARIFICATION: [
                "Prepare brief, direct explanation",
                "Use simpler language",
                "Focus on key definition",
            ],
            IntentType.ELABORATION: [
                "Prepare detailed explanation",
                "Add supporting context",
                "Go deeper into subtopics",
            ],
            IntentType.EXAMPLE: [
                "Prepare concrete examples",
                "Use relatable scenarios",
                "Show real-world application",
            ],
            IntentType.COMPARISON: [
                "Prepare comparison matrix",
                "Highlight pros/cons",
                "Compare with alternatives",
            ],
            IntentType.APPLICATION: [
                "Prepare practical steps",
                "Provide templates",
                "Give actionable advice",
            ],
            IntentType.VERIFICATION: [
                "Prepare confirmation statements",
                "Use checkpoints",
                "Verify understanding",
            ],
        }
        return suggestions.get(intent, ["Prepare flexible response"])

    def record_prediction_outcome(
        self,
        prediction_id: str,
        actual_intent: IntentType,
    ):
        """Record actual intent for prediction accuracy"""
        if prediction_id not in self.predictions:
            return

        prediction = self.predictions[prediction_id]
        prediction.actual_intent = actual_intent
        prediction.correct = actual_intent == prediction.primary_intent

    def get_prediction_accuracy(self) -> Dict[str, Any]:
        """Get prediction accuracy metrics"""
        correct = sum(1 for p in self.predictions.values() if p.correct)
        total = len(self.predictions)

        if total == 0:
            return {"accuracy": 0, "predictions": 0}

        return {
            "accuracy": round(correct / total, 2),
            "predictions": total,
            "correct": correct,
            "signals_tracked": len(self.signal_history),
        }


class PredictionManager:
    """Manage intent prediction across conversations"""

    def __init__(self):
        self.predictors: Dict[str, IntentPredictor] = {}

    def create_predictor(self, predictor_id: str) -> IntentPredictor:
        """Create intent predictor"""
        predictor = IntentPredictor()
        self.predictors[predictor_id] = predictor
        return predictor

    def get_predictor(self, predictor_id: str) -> Optional[IntentPredictor]:
        """Get predictor"""
        return self.predictors.get(predictor_id)


# Global manager
prediction_manager = PredictionManager()


# MCP Tools

def create_intent_predictor(predictor_id: str) -> dict:
    """Create intent predictor"""
    predictor = prediction_manager.create_predictor(predictor_id)
    return {"predictor_id": predictor_id, "created": True}


def predict_next_intent(
    predictor_id: str,
    conversation_history: list,
    current_topic: str,
    turn_num: int,
) -> dict:
    """Predict next user intent"""
    predictor = prediction_manager.get_predictor(predictor_id)
    if not predictor:
        return {"error": "Predictor not found"}

    prediction = predictor.predict_next_intent(
        conversation_history, current_topic, turn_num
    )
    return {
        "prediction_id": prediction.prediction_id,
        "primary_intent": prediction.primary_intent.value,
        "confidence": round(prediction.confidence, 2),
        "suggested_actions": prediction.suggested_actions,
    }


def record_prediction_outcome(
    predictor_id: str,
    prediction_id: str,
    actual_intent: str,
) -> dict:
    """Record prediction outcome"""
    predictor = prediction_manager.get_predictor(predictor_id)
    if not predictor:
        return {"error": "Predictor not found"}

    try:
        intent = IntentType(actual_intent)
        predictor.record_prediction_outcome(prediction_id, intent)
        return {"recorded": True}
    except ValueError:
        return {"error": f"Invalid intent type: {actual_intent}"}


def get_prediction_accuracy(predictor_id: str) -> dict:
    """Get prediction accuracy"""
    predictor = prediction_manager.get_predictor(predictor_id)
    if not predictor:
        return {"error": "Predictor not found"}

    return predictor.get_prediction_accuracy()


if __name__ == "__main__":
    predictor = IntentPredictor()

    # Predict intent
    prediction = predictor.predict_next_intent(
        ["Can you explain more about this?", "I want more details"],
        "Python basics",
        3,
    )

    print(f"Predicted: {prediction.primary_intent.value}")
    print(f"Confidence: {prediction.confidence}")
    print(f"Actions: {prediction.suggested_actions}")

    # Record outcome
    predictor.record_prediction_outcome(prediction.prediction_id, IntentType.ELABORATION)

    # Get accuracy
    accuracy = predictor.get_prediction_accuracy()
    print(f"Accuracy: {accuracy}")
