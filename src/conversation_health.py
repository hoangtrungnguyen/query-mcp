"""Conversation health monitoring: detect stalls, dead ends, and conversation quality degradation"""

import json
from pathlib import Path
from datetime import datetime
from typing import Optional, List, Dict, Any
from dataclasses import dataclass, field
from enum import Enum

HEALTH_DIR = Path.home() / ".memory-mcp" / "conversation-health"
HEALTH_DIR.mkdir(exist_ok=True, parents=True)


class HealthStatus(Enum):
    """Overall conversation health"""
    HEALTHY = "healthy"  # Progressing well
    WARNING = "warning"  # Some degradation
    CRITICAL = "critical"  # Severe issues
    STALLED = "stalled"  # No progress
    DEAD_END = "dead_end"  # Can't continue productively


class HealthIssue(Enum):
    """Specific health problems"""
    REPETITIVE = "repetitive"  # Repeating same points
    SHALLOW = "shallow"  # Not going deep
    UNRESOLVED = "unresolved"  # Open issues not closed
    DIVERGENT = "divergent"  # Conversation scattered
    UNRESPONSIVE = "unresponsive"  # User engagement dropped
    CIRCULAR = "circular"  # Going in circles


@dataclass
class TurnMetrics:
    """Metrics for a single turn"""
    turn_num: int
    response_length: int
    unique_words: int
    questions_asked: int
    topics_introduced: int
    topics_referenced: int  # References to previous topics
    sentiment_polarity: float  # -1 to 1

    def to_dict(self) -> Dict:
        """Serialize metrics"""
        return {
            "turn": self.turn_num,
            "response_length": self.response_length,
            "unique_words": self.unique_words,
            "questions": self.questions_asked,
        }


@dataclass
class ConversationHealthState:
    """Health state of conversation"""
    conversation_id: str
    current_status: HealthStatus = HealthStatus.HEALTHY
    issues: List[HealthIssue] = field(default_factory=list)
    turn_metrics: List[TurnMetrics] = field(default_factory=list)
    depth_score: float = 0.5  # 0-1, how deep we're going
    engagement_trend: float = 0.0  # Trend in engagement (-1 to 1)
    topic_coherence: float = 0.8  # 0-1, how on-topic
    stall_turns: int = 0  # Turns without progress
    last_topic_shift: int = 0
    last_resolution: int = 0

    def to_dict(self) -> Dict:
        """Serialize state"""
        return {
            "conversation_id": self.conversation_id,
            "status": self.current_status.value,
            "depth_score": round(self.depth_score, 2),
            "coherence": round(self.topic_coherence, 2),
            "issues": [i.value for i in self.issues],
        }


class HealthAnalyzer:
    """Analyze conversation health metrics"""

    @staticmethod
    def calculate_metrics(
        response: str,
        turn_num: int,
    ) -> TurnMetrics:
        """Calculate metrics for a response"""
        words = response.split()
        unique_words = len(set(w.lower() for w in words))
        questions = response.count("?")

        # Simple topic counting (rough)
        sentences = response.split(".")
        topics = len(sentences)

        # Simple sentiment (rough heuristic)
        positive_words = ["good", "great", "excellent", "nice", "great"]
        negative_words = ["bad", "poor", "terrible", "awful"]
        sentiment = 0.5
        if any(w in response.lower() for w in positive_words):
            sentiment = 0.7
        if any(w in response.lower() for w in negative_words):
            sentiment = 0.3

        return TurnMetrics(
            turn_num=turn_num,
            response_length=len(response),
            unique_words=unique_words,
            questions_asked=questions,
            topics_introduced=topics,
            topics_referenced=0,
            sentiment_polarity=sentiment,
        )

    @staticmethod
    def detect_repetition(
        recent_turns: List[TurnMetrics],
    ) -> float:
        """Detect repetitive pattern (0-1, higher = more repetitive)"""
        if len(recent_turns) < 3:
            return 0.0

        # Check unique word variety
        lengths = [t.response_length for t in recent_turns[-3:]]
        avg_length = sum(lengths) / len(lengths) if lengths else 0

        # Low variety + low engagement = repetition
        unique_counts = [t.unique_words for t in recent_turns[-3:]]
        avg_unique = sum(unique_counts) / len(unique_counts) if unique_counts else 0

        if avg_length > 0:
            uniqueness_ratio = avg_unique / (avg_length / 4)  # ~4 chars per word
            return 1 - min(1.0, uniqueness_ratio)

        return 0.0

    @staticmethod
    def detect_shallow_depth(
        recent_turns: List[TurnMetrics],
    ) -> float:
        """Detect if conversation is staying shallow (0-1)"""
        if not recent_turns:
            return 0.5

        # Questions asked indicate depth of inquiry
        total_questions = sum(t.questions_asked for t in recent_turns[-5:])
        avg_response_length = sum(t.response_length for t in recent_turns[-5:]) / 5

        if avg_response_length < 100:  # Very short responses
            return 0.8
        if total_questions == 0:  # No questions = not exploring
            return 0.6

        return 0.2


class ConversationHealthMonitor:
    """Monitor conversation health across turns"""

    def __init__(self):
        self.states: Dict[str, ConversationHealthState] = {}
        self.history: Dict[str, List[HealthStatus]] = {}

    def create_health_state(self, conversation_id: str) -> ConversationHealthState:
        """Create health state for conversation"""
        state = ConversationHealthState(conversation_id=conversation_id)
        self.states[conversation_id] = state
        self.history[conversation_id] = [state.current_status]
        return state

    def update_health(
        self,
        conversation_id: str,
        response: str,
        turn_num: int,
    ) -> ConversationHealthState:
        """Update health based on new response"""
        if conversation_id not in self.states:
            self.create_health_state(conversation_id)

        state = self.states[conversation_id]

        # Calculate metrics
        metrics = HealthAnalyzer.calculate_metrics(response, turn_num)
        state.turn_metrics.append(metrics)

        # Detect issues
        new_issues = []

        repetition = HealthAnalyzer.detect_repetition(state.turn_metrics[-5:])
        if repetition > 0.6:
            new_issues.append(HealthIssue.REPETITIVE)

        shallowness = HealthAnalyzer.detect_shallow_depth(state.turn_metrics[-5:])
        if shallowness > 0.6:
            new_issues.append(HealthIssue.SHALLOW)

        # Track stalls
        if metrics.response_length < 50:
            state.stall_turns += 1
        else:
            state.stall_turns = 0

        if state.stall_turns > 3:
            new_issues.append(HealthIssue.UNRESPONSIVE)

        # Determine overall status
        if len(new_issues) >= 3:
            state.current_status = HealthStatus.CRITICAL
        elif len(new_issues) >= 2:
            state.current_status = HealthStatus.WARNING
        elif state.stall_turns > 2:
            state.current_status = HealthStatus.STALLED
        else:
            state.current_status = HealthStatus.HEALTHY

        state.issues = new_issues
        self.history[conversation_id].append(state.current_status)

        return state

    def diagnose_dead_end(
        self,
        conversation_id: str,
        reason: str = "",
    ) -> Optional[Dict[str, Any]]:
        """Diagnose if conversation has reached dead end"""
        if conversation_id not in self.states:
            return None

        state = self.states[conversation_id]

        # Criteria for dead end
        criteria = []
        if state.stall_turns > 2:
            criteria.append("repeated_short_responses")
        if HealthIssue.REPETITIVE in state.issues:
            criteria.append("high_repetition")
        if HealthIssue.CIRCULAR in state.issues:
            criteria.append("circular_reasoning")

        if len(criteria) >= 2:
            state.current_status = HealthStatus.DEAD_END
            return {
                "conversation_id": conversation_id,
                "dead_end": True,
                "criteria": criteria,
                "recommendation": "Consider pivoting topic or ending conversation",
            }

        return {
            "conversation_id": conversation_id,
            "dead_end": False,
            "criteria": [],
        }

    def get_health_report(self, conversation_id: str) -> Optional[Dict[str, Any]]:
        """Get full health report"""
        if conversation_id not in self.states:
            return None

        state = self.states[conversation_id]
        status_counts = {}
        for status in self.history[conversation_id]:
            status_counts[status.value] = status_counts.get(status.value, 0) + 1

        return {
            "conversation_id": conversation_id,
            "current_status": state.current_status.value,
            "issues": [i.value for i in state.issues],
            "turns_tracked": len(state.turn_metrics),
            "stall_turns": state.stall_turns,
            "status_history": status_counts,
        }


class HealthManager:
    """Manage conversation health across multiple conversations"""

    def __init__(self):
        self.monitors: Dict[str, ConversationHealthMonitor] = {}

    def create_monitor(self, monitor_id: str) -> ConversationHealthMonitor:
        """Create health monitor"""
        monitor = ConversationHealthMonitor()
        self.monitors[monitor_id] = monitor
        return monitor

    def get_monitor(self, monitor_id: str) -> Optional[ConversationHealthMonitor]:
        """Get monitor"""
        return self.monitors.get(monitor_id)


# Global manager
health_manager = HealthManager()


# MCP Tools

def create_health_monitor(monitor_id: str) -> dict:
    """Create health monitor"""
    monitor = health_manager.create_monitor(monitor_id)
    return {"monitor_id": monitor_id, "created": True}


def create_conversation_health(monitor_id: str, conversation_id: str) -> dict:
    """Create health state for conversation"""
    monitor = health_manager.get_monitor(monitor_id)
    if not monitor:
        return {"error": "Monitor not found"}

    state = monitor.create_health_state(conversation_id)
    return state.to_dict()


def update_conversation_health(
    monitor_id: str,
    conversation_id: str,
    response: str,
    turn_num: int,
) -> dict:
    """Update conversation health"""
    monitor = health_manager.get_monitor(monitor_id)
    if not monitor:
        return {"error": "Monitor not found"}

    state = monitor.update_health(conversation_id, response, turn_num)
    return state.to_dict()


def diagnose_dead_end(monitor_id: str, conversation_id: str, reason: str = "") -> dict:
    """Diagnose dead end"""
    monitor = health_manager.get_monitor(monitor_id)
    if not monitor:
        return {"error": "Monitor not found"}

    result = monitor.diagnose_dead_end(conversation_id, reason)
    return result or {"error": "Conversation not found"}


def get_health_report(monitor_id: str, conversation_id: str) -> dict:
    """Get health report"""
    monitor = health_manager.get_monitor(monitor_id)
    if not monitor:
        return {"error": "Monitor not found"}

    report = monitor.get_health_report(conversation_id)
    return report or {"error": "Conversation not found"}


if __name__ == "__main__":
    monitor = ConversationHealthMonitor()

    # Create state
    monitor.create_health_state("conv_1")

    # Update with responses
    monitor.update_health("conv_1", "This is a response. Let me explain more.", 1)
    monitor.update_health("conv_1", "Continuing...", 2)
    monitor.update_health("conv_1", "Hi", 3)
    monitor.update_health("conv_1", "Ok", 4)

    # Get report
    report = monitor.get_health_report("conv_1")
    print(f"Report: {json.dumps(report, indent=2)}")

    # Check for dead end
    result = monitor.diagnose_dead_end("conv_1")
    print(f"Dead end: {result}")
