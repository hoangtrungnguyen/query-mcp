"""Conversation summarization: extractive and abstractive summaries at milestones"""

import json
from pathlib import Path
from datetime import datetime
from typing import Optional, List, Dict, Any
from dataclasses import dataclass, field
from enum import Enum

SUMMARY_DIR = Path.home() / ".memory-mcp" / "conversation-summarizer"
SUMMARY_DIR.mkdir(exist_ok=True, parents=True)


class SummaryType(Enum):
    """Type of summary"""
    EXTRACTIVE = "extractive"  # Key sentences from conversation
    ABSTRACTIVE = "abstractive"  # Synthesized summary
    MILESTONE = "milestone"  # Summary at decision points
    FINAL = "final"  # End-of-conversation summary


class SummaryFocus(Enum):
    """What to focus summary on"""
    DECISIONS = "decisions"  # Key decisions made
    QUESTIONS_ANSWERS = "questions_answers"  # Q&A pairs
    GOALS = "goals"  # Goals and progress
    LEARNING = "learning"  # What was learned
    ACTIONS = "actions"  # Action items


@dataclass
class SummarySegment:
    """Segment of conversation to include in summary"""
    segment_id: str
    start_turn: int
    end_turn: int
    key_points: List[str]
    importance: float  # 0-1, how important to preserve
    topic: str

    def to_dict(self) -> Dict:
        """Serialize segment"""
        return {
            "segment_id": self.segment_id,
            "turns": f"{self.start_turn}-{self.end_turn}",
            "importance": round(self.importance, 2),
            "topic": self.topic,
        }


@dataclass
class ConversationSummary:
    """Summary of conversation"""
    summary_id: str
    conversation_id: str
    summary_type: SummaryType
    focus: SummaryFocus
    segments: List[SummarySegment] = field(default_factory=list)
    summary_text: str = ""
    key_decisions: List[str] = field(default_factory=list)
    unresolved_questions: List[str] = field(default_factory=list)
    action_items: List[str] = field(default_factory=list)
    compression_ratio: float = 1.0  # Original / compressed
    created_at: str = ""

    def __post_init__(self):
        if not self.created_at:
            self.created_at = datetime.now().isoformat()

    def to_dict(self) -> Dict:
        """Serialize summary"""
        return {
            "summary_id": self.summary_id,
            "type": self.summary_type.value,
            "focus": self.focus.value,
            "segments": len(self.segments),
            "decisions": len(self.key_decisions),
            "compression": round(self.compression_ratio, 2),
        }


class SummaryBuilder:
    """Build conversation summaries"""

    @staticmethod
    def extract_key_sentences(
        conversation_turns: List[str],
        num_sentences: int = 5,
    ) -> List[str]:
        """Extract most important sentences (extractive)"""
        if not conversation_turns:
            return []

        # Simple heuristic: sentences with more words (more substantive)
        all_sentences = []
        for turn_idx, turn in enumerate(conversation_turns):
            sentences = turn.split(".")
            for sent in sentences:
                if len(sent.split()) > 5:  # Filter out very short sentences
                    all_sentences.append((sent.strip(), turn_idx))

        # Sort by length (proxy for importance)
        all_sentences.sort(key=lambda x: len(x[0].split()), reverse=True)

        # Return top N, maintaining original order
        selected = sorted(all_sentences[:num_sentences], key=lambda x: x[1])
        return [s[0] for s in selected if s[0]]

    @staticmethod
    def identify_decisions(
        conversation_turns: List[str],
    ) -> List[str]:
        """Identify key decisions made"""
        decisions = []
        decision_words = ["decided", "chose", "selected", "agreed", "concluded", "determined"]

        for turn in conversation_turns:
            turn_lower = turn.lower()
            if any(word in turn_lower for word in decision_words):
                decisions.append(turn[:100])

        return decisions

    @staticmethod
    def identify_action_items(
        conversation_turns: List[str],
    ) -> List[str]:
        """Identify action items and next steps"""
        actions = []
        action_words = ["will", "going to", "next", "should", "need to", "todo"]

        for turn in conversation_turns:
            turn_lower = turn.lower()
            if any(word in turn_lower for word in action_words):
                actions.append(turn[:100])

        return actions

    @staticmethod
    def segment_conversation(
        conversation_turns: List[str],
        segment_size: int = 5,
    ) -> List[SummarySegment]:
        """Segment conversation into topics"""
        segments = []

        for i in range(0, len(conversation_turns), segment_size):
            segment_turns = conversation_turns[i : i + segment_size]
            start_turn = i + 1
            end_turn = i + len(segment_turns)

            # Estimate importance based on length and key words
            total_length = sum(len(t) for t in segment_turns)
            importance = min(1.0, total_length / 500)  # ~500 chars = high importance

            # Simple topic identification
            combined = " ".join(segment_turns).lower()
            topic = "general"
            if "python" in combined:
                topic = "python"
            elif "function" in combined or "method" in combined:
                topic = "functions"
            elif "error" in combined or "bug" in combined:
                topic = "debugging"

            segment = SummarySegment(
                segment_id=f"seg_{len(segments)}",
                start_turn=start_turn,
                end_turn=end_turn,
                key_points=[sentence[:50] for sentence in segment_turns[:2]],
                importance=importance,
                topic=topic,
            )
            segments.append(segment)

        return segments


class ConversationSummarizer:
    """Summarize conversations"""

    def __init__(self):
        self.summaries: Dict[str, ConversationSummary] = {}

    def summarize_conversation(
        self,
        conversation_id: str,
        conversation_turns: List[str],
        summary_type: SummaryType = SummaryType.EXTRACTIVE,
        focus: SummaryFocus = SummaryFocus.DECISIONS,
    ) -> ConversationSummary:
        """Create summary of conversation"""
        segments = SummaryBuilder.segment_conversation(conversation_turns)

        key_sentences = SummaryBuilder.extract_key_sentences(conversation_turns)
        summary_text = " ".join(key_sentences)

        key_decisions = SummaryBuilder.identify_decisions(conversation_turns)
        action_items = SummaryBuilder.identify_action_items(conversation_turns)

        # Estimate compression ratio
        original_length = sum(len(t) for t in conversation_turns)
        compressed_length = len(summary_text)
        compression_ratio = original_length / compressed_length if compressed_length > 0 else 1.0

        summary = ConversationSummary(
            summary_id=f"sum_{len(self.summaries)}",
            conversation_id=conversation_id,
            summary_type=summary_type,
            focus=focus,
            segments=segments,
            summary_text=summary_text,
            key_decisions=key_decisions,
            action_items=action_items,
            compression_ratio=compression_ratio,
        )

        self.summaries[summary.summary_id] = summary
        return summary

    def summarize_milestone(
        self,
        conversation_id: str,
        conversation_turns: List[str],
        milestone_turn: int,
    ) -> ConversationSummary:
        """Create summary at specific milestone turn"""
        turns_up_to_milestone = conversation_turns[:milestone_turn]
        return self.summarize_conversation(
            conversation_id,
            turns_up_to_milestone,
            summary_type=SummaryType.MILESTONE,
            focus=SummaryFocus.GOALS,
        )

    def get_summary_report(self, summary_id: str) -> Optional[Dict[str, Any]]:
        """Get full summary report"""
        if summary_id not in self.summaries:
            return None

        summary = self.summaries[summary_id]
        return {
            "summary_id": summary_id,
            "type": summary.summary_type.value,
            "text": summary.summary_text,
            "key_decisions": summary.key_decisions,
            "action_items": summary.action_items,
            "segments": [s.to_dict() for s in summary.segments],
            "compression_ratio": round(summary.compression_ratio, 2),
        }


class SummarizerManager:
    """Manage conversation summarization"""

    def __init__(self):
        self.summarizers: Dict[str, ConversationSummarizer] = {}

    def create_summarizer(self, summarizer_id: str) -> ConversationSummarizer:
        """Create summarizer"""
        summarizer = ConversationSummarizer()
        self.summarizers[summarizer_id] = summarizer
        return summarizer

    def get_summarizer(self, summarizer_id: str) -> Optional[ConversationSummarizer]:
        """Get summarizer"""
        return self.summarizers.get(summarizer_id)


# Global manager
summarizer_manager = SummarizerManager()


# MCP Tools

def create_summarizer(summarizer_id: str) -> dict:
    """Create conversation summarizer"""
    summarizer = summarizer_manager.create_summarizer(summarizer_id)
    return {"summarizer_id": summarizer_id, "created": True}


def summarize_conversation(
    summarizer_id: str,
    conversation_id: str,
    conversation_turns: list,
    summary_type: str = "extractive",
    focus: str = "decisions",
) -> dict:
    """Summarize conversation"""
    summarizer = summarizer_manager.get_summarizer(summarizer_id)
    if not summarizer:
        return {"error": "Summarizer not found"}

    try:
        stype = SummaryType(summary_type)
        sfocus = SummaryFocus(focus)
        summary = summarizer.summarize_conversation(conversation_id, conversation_turns, stype, sfocus)
        return summary.to_dict()
    except ValueError as e:
        return {"error": str(e)}


def summarize_milestone(
    summarizer_id: str,
    conversation_id: str,
    conversation_turns: list,
    milestone_turn: int,
) -> dict:
    """Summarize at milestone"""
    summarizer = summarizer_manager.get_summarizer(summarizer_id)
    if not summarizer:
        return {"error": "Summarizer not found"}

    summary = summarizer.summarize_milestone(conversation_id, conversation_turns, milestone_turn)
    return summary.to_dict()


def get_summary_report(summarizer_id: str, summary_id: str) -> dict:
    """Get summary report"""
    summarizer = summarizer_manager.get_summarizer(summarizer_id)
    if not summarizer:
        return {"error": "Summarizer not found"}

    report = summarizer.get_summary_report(summary_id)
    return report or {"error": "Summary not found"}


if __name__ == "__main__":
    summarizer = ConversationSummarizer()

    turns = [
        "I want to learn Python",
        "Let me start with variables and data types",
        "Variables store values",
        "We decided to focus on functions next",
        "I will practice exercises",
    ]

    summary = summarizer.summarize_conversation("conv_1", turns)
    print(f"Summary: {summary.summary_text}")
    print(f"Decisions: {summary.key_decisions}")
    print(f"Actions: {summary.action_items}")
