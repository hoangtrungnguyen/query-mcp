"""Intent recognition and dialogue act identification"""

import json
from pathlib import Path
from datetime import datetime
from typing import Optional, List, Dict, Any
from dataclasses import dataclass, field
from enum import Enum

INTENT_DIR = Path.home() / ".memory-mcp" / "intent-recognition"
INTENT_DIR.mkdir(exist_ok=True, parents=True)


class UserIntent(Enum):
    """Types of user intents"""
    SEEK_INFORMATION = "seek_information"
    REQUEST_ACTION = "request_action"
    EXPRESS_OPINION = "express_opinion"
    MAKE_COMPLAINT = "make_complaint"
    GET_RECOMMENDATION = "get_recommendation"
    CONFIRM_UNDERSTANDING = "confirm_understanding"
    CLARIFY = "clarify"
    NEGOTIATE = "negotiate"
    AGREE = "agree"
    DISAGREE = "disagree"


class DialogueActType(Enum):
    """Dialogue acts (from DAMSL)"""
    STATEMENT = "statement"
    YES_NO_QUESTION = "yes_no_question"
    OPEN_QUESTION = "open_question"
    COMMAND = "command"
    REQUEST_INFORMATION = "request_information"
    REQUEST_ACTION = "request_action"
    ACKNOWLEDGEMENT = "acknowledgement"
    AGREEMENT = "agreement"
    DISAGREEMENT = "disagreement"
    APOLOGY = "apology"
    THANK = "thank"


@dataclass
class IntentDetection:
    """Detected user intent"""
    detection_id: str
    text: str
    primary_intent: UserIntent
    secondary_intents: List[UserIntent] = field(default_factory=list)
    confidence: float = 0.8
    supporting_phrases: List[str] = field(default_factory=list)
    explicit: bool = True  # Is intent explicitly stated?
    created_at: str = ""

    def __post_init__(self):
        if not self.created_at:
            self.created_at = datetime.now().isoformat()

    def to_dict(self) -> Dict:
        """Serialize detection"""
        return {
            "detection_id": self.detection_id,
            "primary": self.primary_intent.value,
            "secondary": [i.value for i in self.secondary_intents],
            "confidence": round(self.confidence, 2),
            "explicit": self.explicit,
        }


@dataclass
class DialogueActDetection:
    """Detected dialogue act"""
    act_id: str
    text: str
    dialogue_act: DialogueActType
    confidence: float = 0.8
    intent_alignment: float = 0.0  # How well aligned with intent
    argument_slots: Dict[str, str] = field(default_factory=dict)  # e.g., {"wh_word": "what"}
    created_at: str = ""

    def __post_init__(self):
        if not self.created_at:
            self.created_at = datetime.now().isoformat()

    def to_dict(self) -> Dict:
        """Serialize detection"""
        return {
            "act_id": self.act_id,
            "dialogue_act": self.dialogue_act.value,
            "confidence": round(self.confidence, 2),
            "intent_alignment": round(self.intent_alignment, 2),
        }


class IntentRecognizer:
    """Recognize user intents from text"""

    INTENT_KEYWORDS = {
        UserIntent.SEEK_INFORMATION: ["what", "where", "when", "how", "why", "tell", "explain", "describe"],
        UserIntent.REQUEST_ACTION: ["can you", "please", "would you", "could you", "do"],
        UserIntent.EXPRESS_OPINION: ["think", "believe", "opinion", "seems", "appears"],
        UserIntent.MAKE_COMPLAINT: ["problem", "issue", "wrong", "broken", "complaint"],
        UserIntent.GET_RECOMMENDATION: ["recommend", "suggest", "advise", "best", "better"],
        UserIntent.CONFIRM_UNDERSTANDING: ["right", "correct", "yes", "agreed"],
        UserIntent.CLARIFY: ["clarify", "explain", "mean", "understand", "clear"],
        UserIntent.NEGOTIATE: ["instead", "how about", "what if", "alternative"],
        UserIntent.AGREE: ["yes", "sure", "ok", "agree", "good"],
        UserIntent.DISAGREE: ["no", "not", "disagree", "wrong", "don't"],
    }

    @staticmethod
    def recognize(text: str) -> IntentDetection:
        """Recognize user intent"""
        text_lower = text.lower()

        # Score each intent
        intent_scores = {}
        for intent, keywords in IntentRecognizer.INTENT_KEYWORDS.items():
            matches = sum(1 for kw in keywords if kw in text_lower)
            intent_scores[intent] = matches

        # Get primary intent
        primary_intent = max(intent_scores.items(), key=lambda x: x[1])[0]

        # Get secondary intents
        sorted_intents = sorted(intent_scores.items(), key=lambda x: x[1], reverse=True)
        secondary = [intent for intent, score in sorted_intents[1:3] if score > 0]

        # Supporting phrases
        supporting = []
        for kw in IntentRecognizer.INTENT_KEYWORDS[primary_intent]:
            if kw in text_lower:
                supporting.append(kw)

        # Confidence based on match strength
        confidence = min(
            1.0,
            (intent_scores[primary_intent] + 1) / (len(IntentRecognizer.INTENT_KEYWORDS[primary_intent]) + 1)
        )

        detection = IntentDetection(
            detection_id=f"int_{int(datetime.now().timestamp())}",
            text=text,
            primary_intent=primary_intent,
            secondary_intents=secondary,
            confidence=confidence,
            supporting_phrases=supporting,
        )

        return detection


class DialogueActClassifier:
    """Classify dialogue acts"""

    DIALOGUE_ACT_MARKERS = {
        DialogueActType.YES_NO_QUESTION: ["?", "is", "are", "do", "does"],
        DialogueActType.OPEN_QUESTION: ["what", "where", "when", "how", "why"],
        DialogueActType.COMMAND: ["must", "should", "need to", "have to"],
        DialogueActType.REQUEST_ACTION: ["can", "could", "please", "would"],
        DialogueActType.REQUEST_INFORMATION: ["tell", "explain", "describe"],
        DialogueActType.ACKNOWLEDGEMENT: ["ok", "yes", "right", "understood"],
        DialogueActType.AGREEMENT: ["agree", "correct", "absolutely"],
        DialogueActType.DISAGREEMENT: ["no", "wrong", "disagree"],
        DialogueActType.THANK: ["thank", "thanks", "appreciate"],
    }

    @staticmethod
    def classify(text: str, intent: Optional[UserIntent] = None) -> DialogueActDetection:
        """Classify dialogue act"""
        text_lower = text.lower()

        # Score each dialogue act
        act_scores = {}
        for act, markers in DialogueActClassifier.DIALOGUE_ACT_MARKERS.items():
            matches = sum(1 for marker in markers if marker in text_lower)
            act_scores[act] = matches

        # Get primary act
        primary_act = max(act_scores.items(), key=lambda x: x[1])[0]

        # Confidence
        confidence = min(
            1.0,
            (act_scores[primary_act] + 1) / (len(DialogueActClassifier.DIALOGUE_ACT_MARKERS[primary_act]) + 1)
        )

        # Alignment with intent
        intent_alignment = 0.8 if intent else 0.5

        detection = DialogueActDetection(
            act_id=f"act_{int(datetime.now().timestamp())}",
            text=text,
            dialogue_act=primary_act,
            confidence=confidence,
            intent_alignment=intent_alignment,
        )

        return detection


class IntentAnalyzer:
    """Analyze intent patterns"""

    def __init__(self):
        self.detected_intents: Dict[str, IntentDetection] = {}
        self.detected_acts: Dict[str, DialogueActDetection] = {}

    def analyze_turn(self, turn_id: str, text: str) -> Dict[str, Any]:
        """Analyze intent and dialogue act for turn"""
        # Recognize intent
        intent = IntentRecognizer.recognize(text)
        self.detected_intents[turn_id] = intent

        # Classify dialogue act
        act = DialogueActClassifier.classify(text, intent.primary_intent)
        self.detected_acts[turn_id] = act

        return {
            "turn_id": turn_id,
            "intent": intent.to_dict(),
            "dialogue_act": act.to_dict(),
            "combined_confidence": (intent.confidence + act.confidence) / 2,
        }

    def get_intent_sequence(self, turn_ids: List[str]) -> List[str]:
        """Get sequence of intents for conversation"""
        sequence = []
        for turn_id in turn_ids:
            if turn_id in self.detected_intents:
                sequence.append(self.detected_intents[turn_id].primary_intent.value)
        return sequence

    def get_dialogue_act_sequence(self, turn_ids: List[str]) -> List[str]:
        """Get sequence of dialogue acts"""
        sequence = []
        for turn_id in turn_ids:
            if turn_id in self.detected_acts:
                sequence.append(self.detected_acts[turn_id].dialogue_act.value)
        return sequence

    def analyze_intent_patterns(self) -> Dict[str, Any]:
        """Analyze patterns in detected intents"""
        intent_counts = {}
        for intent in self.detected_intents.values():
            intent_counts[intent.primary_intent.value] = intent_counts.get(intent.primary_intent.value, 0) + 1

        act_counts = {}
        for act in self.detected_acts.values():
            act_counts[act.dialogue_act.value] = act_counts.get(act.dialogue_act.value, 0) + 1

        return {
            "total_turns": len(self.detected_intents),
            "intent_distribution": intent_counts,
            "dialogue_act_distribution": act_counts,
            "avg_intent_confidence": (
                sum(i.confidence for i in self.detected_intents.values()) / len(self.detected_intents)
                if self.detected_intents else 0.0
            ),
        }


class IntentManager:
    """Manage intent recognition across conversations"""

    def __init__(self):
        self.analyzers: Dict[str, IntentAnalyzer] = {}

    def create_analyzer(self, analyzer_id: str) -> IntentAnalyzer:
        """Create intent analyzer"""
        analyzer = IntentAnalyzer()
        self.analyzers[analyzer_id] = analyzer
        return analyzer

    def get_analyzer(self, analyzer_id: str) -> Optional[IntentAnalyzer]:
        """Get analyzer"""
        return self.analyzers.get(analyzer_id)


# Global manager
intent_manager = IntentManager()


# MCP Tools

def create_intent_analyzer(analyzer_id: str) -> dict:
    """Create intent recognition analyzer"""
    analyzer = intent_manager.create_analyzer(analyzer_id)
    return {"analyzer_id": analyzer_id, "created": True}


def analyze_turn_intent(analyzer_id: str, turn_id: str, text: str) -> dict:
    """Analyze intent for turn"""
    analyzer = intent_manager.get_analyzer(analyzer_id)
    if not analyzer:
        return {"error": "Analyzer not found"}

    return analyzer.analyze_turn(turn_id, text)


def get_intent_sequence(analyzer_id: str, turn_ids: list) -> dict:
    """Get intent sequence"""
    analyzer = intent_manager.get_analyzer(analyzer_id)
    if not analyzer:
        return {"error": "Analyzer not found"}

    sequence = analyzer.get_intent_sequence(turn_ids)
    return {
        "sequence": sequence,
        "length": len(sequence),
    }


def get_intent_patterns(analyzer_id: str) -> dict:
    """Get intent patterns"""
    analyzer = intent_manager.get_analyzer(analyzer_id)
    if not analyzer:
        return {"error": "Analyzer not found"}

    return analyzer.analyze_intent_patterns()


if __name__ == "__main__":
    # Test intent recognition
    analyzer = IntentAnalyzer()

    # Analyze turns
    analyzer.analyze_turn("t1", "What is Python?")
    analyzer.analyze_turn("t2", "Can you explain how it works?")
    analyzer.analyze_turn("t3", "I disagree with that approach")
    analyzer.analyze_turn("t4", "Thanks for the help")

    # Patterns
    patterns = analyzer.analyze_intent_patterns()
    print(f"Patterns: {json.dumps(patterns, indent=2)}")

    # Sequence
    sequence = analyzer.get_intent_sequence(["t1", "t2", "t3", "t4"])
    print(f"Sequence: {sequence}")
