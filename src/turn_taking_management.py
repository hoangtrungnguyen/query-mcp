"""Turn-taking management and conversation protocol"""

import json
from pathlib import Path
from datetime import datetime, timedelta
from typing import Optional, List, Dict, Any
from dataclasses import dataclass, field
from enum import Enum

TURN_DIR = Path.home() / ".memory-mcp" / "turn-taking"
TURN_DIR.mkdir(exist_ok=True, parents=True)


class TurnState(Enum):
    """States of turn-taking"""
    FLOOR_AVAILABLE = "floor_available"
    USER_SPEAKING = "user_speaking"
    ASSISTANT_SPEAKING = "assistant_speaking"
    SIMULTANEOUS = "simultaneous"  # Overlap
    PAUSE = "pause"


class TransitionType(Enum):
    """Turn transition types"""
    SMOOTH = "smooth"  # Natural transition
    OVERLAP = "overlap"  # Speaker overlap
    INTERRUPTION = "interruption"  # Interrupted
    HOLD = "hold"  # Held floor across turns


@dataclass
class TurnBoundary:
    """Point where turn exchange can occur"""
    boundary_id: str
    position: int  # Turn number
    is_valid: bool  # Can transition here
    confidence: float  # P(valid boundary)
    cues: List[str] = field(default_factory=list)  # Linguistic cues (e.g., "falling intonation", "question mark")

    def to_dict(self) -> Dict:
        """Serialize boundary"""
        return {
            "boundary_id": self.boundary_id,
            "position": self.position,
            "is_valid": self.is_valid,
            "confidence": round(self.confidence, 2),
        }


@dataclass
class FloorControl:
    """Who currently has floor"""
    holder: str  # "user" or "assistant"
    acquired_at: str
    duration: float  # Seconds held
    turn_duration: Optional[float] = None  # Seconds for this turn

    def to_dict(self) -> Dict:
        """Serialize control"""
        return {
            "holder": self.holder,
            "duration": round(self.duration, 1),
            "turn_duration": round(self.turn_duration, 1) if self.turn_duration else None,
        }


@dataclass
class TurnTakingRule:
    """Convention for turn exchange"""
    rule_id: str
    rule_name: str
    description: str
    conditions: List[str]  # When rule applies
    action: str  # What happens
    enforced: bool = True

    def to_dict(self) -> Dict:
        """Serialize rule"""
        return {
            "rule_id": self.rule_id,
            "rule_name": self.rule_name,
            "enforced": self.enforced,
        }


@dataclass
class TurnTransition:
    """Transition between turns"""
    transition_id: str
    from_speaker: str
    to_speaker: str
    transition_type: TransitionType
    boundary_used: int  # Turn boundary position
    latency: float = 0.0  # Milliseconds to response
    smooth: bool = True

    def to_dict(self) -> Dict:
        """Serialize transition"""
        return {
            "transition_id": self.transition_id,
            "from": self.from_speaker,
            "to": self.to_speaker,
            "type": self.transition_type.value,
            "smooth": self.smooth,
        }


class TurnBoundaryDetector:
    """Detect valid turn boundaries"""

    # Cues that indicate turn completion
    END_CUES = {
        "syntactic": ["question mark", "period", "exclamation"],
        "prosodic": ["falling intonation", "pitch drop", "volume decrease"],
        "lexical": ["well", "so", "anyway", "right"],
    }

    @staticmethod
    def detect_boundaries(text: str, turn_num: int) -> List[TurnBoundary]:
        """Detect possible turn boundaries in text"""
        boundaries = []

        sentences = text.split(".")
        for i, sentence in enumerate(sentences):
            if not sentence.strip():
                continue

            confidence = 0.5
            cues = []

            # Check for syntactic cues
            if sentence.strip().endswith("?"):
                confidence += 0.3
                cues.append("question_mark")
            elif sentence.strip().endswith("!"):
                confidence += 0.1
                cues.append("exclamation")

            # Check for end markers
            words = sentence.lower().split()
            if words and words[-1] in ["right", "so", "anyway", "well"]:
                confidence += 0.2
                cues.append("discourse_marker")

            confidence = min(1.0, confidence)

            boundary = TurnBoundary(
                boundary_id=f"bound_{turn_num}_{i}",
                position=turn_num,
                is_valid=confidence > 0.6,
                confidence=confidence,
                cues=cues,
            )
            boundaries.append(boundary)

        return boundaries


class OverlapHandler:
    """Handle overlapping speech/input"""

    @staticmethod
    def detect_overlap(
        user_start: float,
        assistant_end: float,
        current_time: float,
    ) -> bool:
        """Detect if overlap is occurring"""
        return user_start < assistant_end and current_time > user_start

    @staticmethod
    def resolve_overlap(
        floor_holder: str,
        interrupting_speaker: str,
        priority: Dict[str, int],
    ) -> str:
        """Resolve overlap by granting floor"""
        if priority.get(interrupting_speaker, 0) > priority.get(floor_holder, 0):
            return interrupting_speaker
        return floor_holder


class TurnTakingManager:
    """Manage turn-taking in conversation"""

    def __init__(self):
        self.current_state = TurnState.FLOOR_AVAILABLE
        self.floor_control: Optional[FloorControl] = None
        self.turn_history: List[TurnTransition] = []
        self.boundaries_detected: List[TurnBoundary] = []
        self.rules: Dict[str, TurnTakingRule] = {}
        self._setup_default_rules()

    def _setup_default_rules(self):
        """Set up default turn-taking rules"""
        rules = [
            TurnTakingRule(
                rule_id="rule_1",
                rule_name="question_response",
                description="Question initiates response turn",
                conditions=["speaker produces question"],
                action="listener must respond",
            ),
            TurnTakingRule(
                rule_id="rule_2",
                rule_name="floor_hold_limit",
                description="Floor held max 120 seconds",
                conditions=["floor_control.duration > 120"],
                action="force transition",
            ),
            TurnTakingRule(
                rule_id="rule_3",
                rule_name="overlap_priority",
                description="Higher priority speaker takes floor on overlap",
                conditions=["simultaneous_speech"],
                action="grant floor to higher priority",
            ),
        ]
        for rule in rules:
            self.rules[rule.rule_id] = rule

    def process_user_input(self, user_text: str, timestamp: float) -> Dict[str, Any]:
        """Process user input and manage turns"""
        turn_num = len(self.turn_history) + 1

        # Detect boundaries
        boundaries = TurnBoundaryDetector.detect_boundaries(user_text, turn_num)
        self.boundaries_detected.extend(boundaries)

        # Check for smooth transition
        previous_held = self.floor_control
        transition_type = TransitionType.SMOOTH

        # Update floor control
        self.floor_control = FloorControl(
            holder="user",
            acquired_at=datetime.now().isoformat(),
            duration=0.0,
        )
        self.current_state = TurnState.USER_SPEAKING

        # Create transition record
        from_speaker = previous_held.holder if previous_held else "none"
        transition = TurnTransition(
            transition_id=f"trans_{turn_num}",
            from_speaker=from_speaker,
            to_speaker="user",
            transition_type=transition_type,
            boundary_used=turn_num - 1,
            smooth=True,
        )
        self.turn_history.append(transition)

        return {
            "turn": turn_num,
            "current_state": self.current_state.value,
            "current_holder": self.floor_control.holder,
            "boundaries_detected": len(boundaries),
            "valid_boundaries": sum(1 for b in boundaries if b.is_valid),
        }

    def process_assistant_response(self, response_text: str, latency: float = 0.0) -> Dict[str, Any]:
        """Process assistant response"""
        turn_num = len(self.turn_history)

        # Detect boundaries in response
        boundaries = TurnBoundaryDetector.detect_boundaries(response_text, turn_num)
        self.boundaries_detected.extend(boundaries)

        # Update floor
        previous_held = self.floor_control
        self.floor_control = FloorControl(
            holder="assistant",
            acquired_at=datetime.now().isoformat(),
            duration=0.0,
            turn_duration=latency,
        )
        self.current_state = TurnState.ASSISTANT_SPEAKING

        # Create transition record
        transition = TurnTransition(
            transition_id=f"trans_{turn_num}",
            from_speaker=previous_held.holder if previous_held else "none",
            to_speaker="assistant",
            transition_type=TransitionType.SMOOTH,
            boundary_used=turn_num - 1,
            latency=latency,
        )
        self.turn_history.append(transition)

        return {
            "turn": turn_num,
            "current_state": self.current_state.value,
            "current_holder": self.floor_control.holder,
            "response_latency": round(latency, 2),
        }

    def get_next_speaker(self) -> str:
        """Get who should speak next"""
        if not self.floor_control:
            return "user"

        if self.floor_control.holder == "user":
            return "assistant"
        else:
            return "user"

    def get_turn_summary(self) -> Dict[str, Any]:
        """Get turn-taking summary"""
        user_turns = sum(1 for t in self.turn_history if t.to_speaker == "user")
        assistant_turns = sum(1 for t in self.turn_history if t.to_speaker == "assistant")

        overlaps = sum(1 for t in self.turn_history if t.transition_type == TransitionType.OVERLAP)
        interruptions = sum(1 for t in self.turn_history if t.transition_type == TransitionType.INTERRUPTION)

        return {
            "total_turns": len(self.turn_history),
            "user_turns": user_turns,
            "assistant_turns": assistant_turns,
            "overlaps": overlaps,
            "interruptions": interruptions,
            "current_holder": self.floor_control.holder if self.floor_control else None,
            "rules_active": len([r for r in self.rules.values() if r.enforced]),
        }


class TurnTakingCoordinator:
    """Coordinate turn-taking across conversations"""

    def __init__(self):
        self.managers: Dict[str, TurnTakingManager] = {}

    def create_manager(self, manager_id: str) -> TurnTakingManager:
        """Create turn-taking manager"""
        manager = TurnTakingManager()
        self.managers[manager_id] = manager
        return manager

    def get_manager(self, manager_id: str) -> Optional[TurnTakingManager]:
        """Get manager"""
        return self.managers.get(manager_id)


# Global coordinator
turn_coordinator = TurnTakingCoordinator()


# MCP Tools

def create_turn_manager(manager_id: str) -> dict:
    """Create turn-taking manager"""
    manager = turn_coordinator.create_manager(manager_id)
    return {"manager_id": manager_id, "created": True}


def process_user_turn(manager_id: str, user_text: str) -> dict:
    """Process user turn"""
    manager = turn_coordinator.get_manager(manager_id)
    if not manager:
        return {"error": "Manager not found"}

    return manager.process_user_input(user_text, datetime.now().timestamp())


def process_assistant_turn(manager_id: str, response_text: str, latency: float = 0.0) -> dict:
    """Process assistant turn"""
    manager = turn_coordinator.get_manager(manager_id)
    if not manager:
        return {"error": "Manager not found"}

    return manager.process_assistant_response(response_text, latency)


def get_next_speaker(manager_id: str) -> dict:
    """Get next speaker"""
    manager = turn_coordinator.get_manager(manager_id)
    if not manager:
        return {"error": "Manager not found"}

    return {"next_speaker": manager.get_next_speaker()}


def get_turn_summary(manager_id: str) -> dict:
    """Get turn summary"""
    manager = turn_coordinator.get_manager(manager_id)
    if not manager:
        return {"error": "Manager not found"}

    return manager.get_turn_summary()


if __name__ == "__main__":
    manager = TurnTakingManager()

    # Simulate turns
    manager.process_user_input("What is machine learning?", 0.0)
    manager.process_assistant_response(
        "Machine learning is a field of AI. It enables systems to learn from data.",
        500.0
    )
    manager.process_user_input("Can you give an example?", 1.0)

    summary = manager.get_turn_summary()
    print(f"Summary: {json.dumps(summary, indent=2)}")

    next_speaker = manager.get_next_speaker()
    print(f"Next speaker: {next_speaker}")
