"""Conversation flow validation and quality checks"""

import json
from pathlib import Path
from datetime import datetime
from typing import Optional, List, Dict, Any
from enum import Enum
from dataclasses import dataclass

VALIDATIONS_DIR = Path.home() / ".memory-mcp" / "validations"
VALIDATIONS_DIR.mkdir(exist_ok=True, parents=True)


class ValidationLevel(Enum):
    """Validation scope levels"""
    RESPONSE = "response"  # Single message
    CONVERSATION = "conversation"  # Multi-turn coherence
    SESSION = "session"  # Complete session task completion


class IssueType(Enum):
    """Types of issues detected"""
    HALLUCINATION = "hallucination"
    LOOP = "loop"
    CONTEXT_LOSS = "context_loss"
    INCONSISTENCY = "inconsistency"
    FACTUAL_ERROR = "factual_error"
    INCOHERENCE = "incoherence"


@dataclass
class ValidationIssue:
    """Detected validation issue"""
    issue_type: IssueType
    severity: float  # 0.0-1.0
    message: str
    location: Dict  # {"turn": N, "speaker": agent_id}
    suggestion: Optional[str] = None
    confidence: float = 0.8

    def to_dict(self) -> Dict:
        """Serialize issue"""
        return {
            "type": self.issue_type.value,
            "severity": self.severity,
            "message": self.message,
            "location": self.location,
            "suggestion": self.suggestion,
            "confidence": self.confidence,
        }


class ContextTracker:
    """Track context across conversation"""

    def __init__(self):
        self.facts: Dict[str, Any] = {}  # Known facts
        self.entity_mentions: Dict[str, int] = {}  # Entity reference counts
        self.contradictions: List[Dict] = []

    def add_fact(self, key: str, value: Any, turn: int):
        """Add fact to context"""
        if key in self.facts:
            if self.facts[key]["value"] != value:
                self.contradictions.append({
                    "key": key,
                    "original": self.facts[key],
                    "new": value,
                    "turn": turn,
                })
        self.facts[key] = {"value": value, "turn": turn}

    def add_entity_mention(self, entity: str):
        """Track entity mentions"""
        self.entity_mentions[entity] = self.entity_mentions.get(entity, 0) + 1

    def check_consistency(self) -> List[ValidationIssue]:
        """Check for contradictions"""
        issues = []
        for contradiction in self.contradictions:
            issues.append(
                ValidationIssue(
                    issue_type=IssueType.INCONSISTENCY,
                    severity=0.8,
                    message=f"Fact '{contradiction['key']}' changed from {contradiction['original']['value']} to {contradiction['new']['value']}",
                    location={"turn": contradiction["turn"]},
                    confidence=0.95,
                )
            )
        return issues


class LoopDetector:
    """Detect repetitive loops in conversation"""

    def __init__(self, threshold: int = 3):
        self.threshold = threshold
        self.message_hashes: List[str] = []
        self.agent_turns: Dict[str, int] = {}

    def add_message(self, content: str, agent_id: str):
        """Add message and check for loops"""
        msg_hash = hash(content[:50])  # Simple hash
        self.message_hashes.append(msg_hash)
        self.agent_turns[agent_id] = self.agent_turns.get(agent_id, 0) + 1

    def detect_repetition(self) -> Optional[ValidationIssue]:
        """Detect if same message repeated N times"""
        if len(self.message_hashes) < self.threshold:
            return None

        recent = self.message_hashes[-self.threshold :]
        if len(set(recent)) == 1:  # All same hash
            return ValidationIssue(
                issue_type=IssueType.LOOP,
                severity=0.9,
                message=f"Message repeated {self.threshold} times - possible infinite loop",
                location={"turn": len(self.message_hashes)},
                suggestion="Break loop by requesting clarification or escalating",
                confidence=0.7,
            )

        return None

    def detect_inefficiency(self, total_turns: int) -> Optional[ValidationIssue]:
        """Detect inefficient conversation (too many turns for task)"""
        if total_turns > 20:
            return ValidationIssue(
                issue_type=IssueType.LOOP,
                severity=0.6,
                message=f"Conversation length {total_turns} suggests inefficiency",
                location={"turn": total_turns},
                suggestion="Consider summarizing and refocusing",
                confidence=0.6,
            )

        return None


class CoherenceChecker:
    """Check conversation coherence"""

    @staticmethod
    def check_context_retention(
        messages: List[Dict],
        context_window: int = 5,
    ) -> Optional[ValidationIssue]:
        """Check if agent forgets earlier context"""
        if len(messages) < context_window:
            return None

        # Simple heuristic: check if references to early context diminish
        early_entities = set()
        late_messages = messages[-context_window:]

        for msg in messages[: len(messages) - context_window]:
            # Extract entity-like strings
            words = msg.get("content", "").split()
            early_entities.update(w for w in words if len(w) > 3)

        late_text = " ".join(m.get("content", "") for m in late_messages)
        referenced = sum(1 for e in early_entities if e in late_text)

        if referenced < len(early_entities) * 0.3:
            return ValidationIssue(
                issue_type=IssueType.CONTEXT_LOSS,
                severity=0.7,
                message="Agent appears to have lost track of earlier context",
                location={"turn": len(messages)},
                suggestion="Reinject context or summarize earlier discussion",
                confidence=0.6,
            )

        return None

    @staticmethod
    def check_tone_consistency(messages: List[Dict]) -> Optional[ValidationIssue]:
        """Check if agent tone remains consistent"""
        if len(messages) < 2:
            return None

        # Simple heuristic: check for abrupt shifts in formality/tone
        early_tone = messages[0].get("content", "").lower()
        late_tone = messages[-1].get("content", "").lower()

        formal_early = sum(1 for word in ["please", "kindly", "regards"] if word in early_tone)
        formal_late = sum(1 for word in ["please", "kindly", "regards"] if word in late_tone)

        if formal_early > 0 and formal_late == 0:
            return ValidationIssue(
                issue_type=IssueType.INCOHERENCE,
                severity=0.5,
                message="Tone shifted from formal to informal",
                location={"turn": len(messages)},
                confidence=0.5,
            )

        return None


class FactualValidator:
    """Validate factual grounding"""

    def __init__(self):
        self.known_facts: Dict[str, str] = {}

    def add_ground_truth(self, fact: str, value: str):
        """Add ground truth fact"""
        self.known_facts[fact] = value

    def validate_response(self, response: str) -> Optional[ValidationIssue]:
        """Check if response is grounded in facts"""
        issues = []

        # Simple heuristic: check for unsupported claims
        suspicious_phrases = ["always", "never", "definitely", "proven", "everyone knows"]

        for phrase in suspicious_phrases:
            if phrase in response.lower():
                issues.append(
                    ValidationIssue(
                        issue_type=IssueType.FACTUAL_ERROR,
                        severity=0.6,
                        message=f"Unqualified claim detected: '{phrase}'",
                        location={},
                        suggestion="Add evidence or qualify with 'may', 'likely', 'in some cases'",
                        confidence=0.5,
                    )
                )

        return issues[0] if issues else None


class FlowValidator:
    """Complete flow validation system"""

    def __init__(self):
        self.context_tracker = ContextTracker()
        self.loop_detector = LoopDetector()
        self.coherence_checker = CoherenceChecker()
        self.factual_validator = FactualValidator()
        self.issues: List[ValidationIssue] = []

    def validate_conversation(
        self,
        messages: List[Dict],
        level: ValidationLevel = ValidationLevel.CONVERSATION,
    ) -> Dict[str, Any]:
        """Validate entire conversation"""
        self.issues = []

        # Add messages to detectors
        for turn, msg in enumerate(messages):
            content = msg.get("content", "")
            agent_id = msg.get("speaker_id", "unknown")

            self.loop_detector.add_message(content, agent_id)

            # Check factual grounding
            factual_issue = self.factual_validator.validate_response(content)
            if factual_issue:
                self.issues.append(factual_issue)

        # Multi-level checks
        if level in [ValidationLevel.CONVERSATION, ValidationLevel.SESSION]:
            # Check context retention
            context_issue = self.coherence_checker.check_context_retention(messages)
            if context_issue:
                self.issues.append(context_issue)

            # Check tone consistency
            tone_issue = self.coherence_checker.check_tone_consistency(messages)
            if tone_issue:
                self.issues.append(tone_issue)

            # Check for loops
            loop_issue = self.loop_detector.detect_repetition()
            if loop_issue:
                self.issues.append(loop_issue)

            # Check efficiency
            efficiency_issue = self.loop_detector.detect_inefficiency(len(messages))
            if efficiency_issue:
                self.issues.append(efficiency_issue)

            # Check context consistency
            consistency_issues = self.context_tracker.check_consistency()
            self.issues.extend(consistency_issues)

        # Calculate overall quality score
        quality_score = self._calculate_quality_score()

        return {
            "valid": len(self.issues) == 0,
            "quality_score": quality_score,
            "issue_count": len(self.issues),
            "issues": [issue.to_dict() for issue in self.issues],
            "recommendations": self._generate_recommendations(),
        }

    def _calculate_quality_score(self) -> float:
        """Calculate conversation quality (0.0-1.0)"""
        if not self.issues:
            return 1.0

        severity_sum = sum(issue.severity * issue.confidence for issue in self.issues)
        return max(0.0, 1.0 - (severity_sum / len(self.issues)))

    def _generate_recommendations(self) -> List[str]:
        """Generate improvement recommendations"""
        recommendations = []

        for issue in self.issues:
            if issue.suggestion:
                recommendations.append(issue.suggestion)

        return recommendations[:5]  # Top 5 recommendations

    def save_validation_report(self, validation_id: str, report: Dict) -> str:
        """Save validation report"""
        filepath = VALIDATIONS_DIR / f"{validation_id}.json"
        with open(filepath, "w") as f:
            json.dump(report, f, indent=2, default=str)
        return str(filepath)


# Global validator instance
validator = FlowValidator()


# MCP Tools (add to memory_server.py)

def validate_conversation(
    messages: list,
    level: str = "conversation",
) -> dict:
    """Validate conversation flow and quality"""
    validation_level = ValidationLevel(level)
    return validator.validate_conversation(messages, validation_level)


def validate_and_save(
    validation_id: str,
    messages: list,
    level: str = "conversation",
) -> dict:
    """Validate conversation and save report"""
    report = validator.validate_conversation(messages, ValidationLevel(level))
    filepath = validator.save_validation_report(validation_id, report)
    report["report_path"] = filepath
    return report


def check_context_loss(messages: list) -> dict:
    """Check if conversation lost earlier context"""
    issue = CoherenceChecker.check_context_retention(messages)
    if issue:
        return {"detected": True, "issue": issue.to_dict()}
    return {"detected": False}


def detect_conversation_loops(messages: list) -> dict:
    """Detect repetitive loops in conversation"""
    detector = LoopDetector()
    for msg in messages:
        detector.add_message(msg.get("content", ""), msg.get("speaker_id", ""))

    repetition = detector.detect_repetition()
    efficiency = detector.detect_inefficiency(len(messages))

    return {
        "repetition_detected": repetition is not None,
        "efficiency_issues": efficiency is not None,
        "issues": [i.to_dict() for i in [repetition, efficiency] if i],
    }


def validate_factual_grounding(message: str) -> dict:
    """Check if message is factually grounded"""
    issue = validator.factual_validator.validate_response(message)
    return {
        "grounded": issue is None,
        "issue": issue.to_dict() if issue else None,
    }


if __name__ == "__main__":
    # Test validation
    test_messages = [
        {
            "speaker_id": "agent_1",
            "content": "The sky is definitely always blue",
            "turn": 0,
        },
        {
            "speaker_id": "user",
            "content": "What about at night?",
            "turn": 1,
        },
        {
            "speaker_id": "agent_1",
            "content": "At night it's black. Everyone knows the sky is always blue.",
            "turn": 2,
        },
    ]

    report = validator.validate_conversation(test_messages, ValidationLevel.CONVERSATION)
    print(json.dumps(report, indent=2))
