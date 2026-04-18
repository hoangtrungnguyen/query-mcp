"""Conversation summarization and abstraction"""

import json
from pathlib import Path
from datetime import datetime
from typing import Optional, List, Dict, Any
from dataclasses import dataclass, field
from enum import Enum

SUMMARY_DIR = Path.home() / ".memory-mcp" / "summarization"
SUMMARY_DIR.mkdir(exist_ok=True, parents=True)


class AbstractionLevel(Enum):
    """Levels of abstraction"""
    DETAILED = "detailed"  # Full transcript
    SUMMARY = "summary"  # Key points
    ABSTRACT = "abstract"  # Core decisions
    EXECUTIVE = "executive"  # One-liner summary


@dataclass
class ConversationSummary:
    """Summary at specific abstraction level"""
    summary_id: str
    level: AbstractionLevel
    content: str
    key_points: List[str] = field(default_factory=list)
    decisions_made: List[str] = field(default_factory=list)
    questions_asked: List[str] = field(default_factory=list)
    compression_ratio: float = 1.0
    created_at: str = ""

    def __post_init__(self):
        if not self.created_at:
            self.created_at = datetime.now().isoformat()

    def to_dict(self) -> Dict:
        return {
            "level": self.level.value,
            "key_points": len(self.key_points),
            "decisions": len(self.decisions_made),
            "compression": round(self.compression_ratio, 2),
        }


class SummarizationEngine:
    """Create conversation summaries"""

    def __init__(self):
        self.summaries: Dict[str, List[ConversationSummary]] = {}

    def summarize_conversation(
        self,
        conversation_id: str,
        turns: List[Dict[str, str]],
    ) -> Dict[str, Any]:
        """Create summaries at multiple levels"""
        summaries = []

        # Extract key information
        key_points = []
        decisions = []
        questions = []

        for turn in turns:
            user_input = turn.get("user_input", "").lower()
            if any(q in user_input for q in ["?", "what", "how", "why"]):
                questions.append(user_input[:100])
            if any(d in user_input for d in ["decide", "choose", "agree"]):
                decisions.append(user_input[:100])

        # Detailed summary
        detailed_content = "\n".join(
            f"User: {t.get('user_input', '')}\nAssistant: {t.get('response', '')}"
            for t in turns
        )
        detailed = ConversationSummary(
            summary_id=f"summ_detailed_{conversation_id}",
            level=AbstractionLevel.DETAILED,
            content=detailed_content,
            key_points=key_points,
            decisions_made=decisions,
            questions_asked=questions,
            compression_ratio=1.0,
        )
        summaries.append(detailed)

        # Summary level
        summary_content = f"Conversation had {len(turns)} turns. Key points: {', '.join(key_points[:3])}"
        summary = ConversationSummary(
            summary_id=f"summ_summary_{conversation_id}",
            level=AbstractionLevel.SUMMARY,
            content=summary_content,
            key_points=key_points,
            decisions_made=decisions,
            compression_ratio=0.3,
        )
        summaries.append(summary)

        # Abstract level
        abstract_content = f"Conversation focused on {len(key_points)} key topics with {len(decisions)} decisions made."
        abstract = ConversationSummary(
            summary_id=f"summ_abstract_{conversation_id}",
            level=AbstractionLevel.ABSTRACT,
            content=abstract_content,
            decisions_made=decisions,
            compression_ratio=0.1,
        )
        summaries.append(abstract)

        # Executive level
        executive = ConversationSummary(
            summary_id=f"summ_exec_{conversation_id}",
            level=AbstractionLevel.EXECUTIVE,
            content=f"Discussion resolved {len(decisions)} decisions.",
            decisions_made=decisions,
            compression_ratio=0.05,
        )
        summaries.append(executive)

        self.summaries[conversation_id] = summaries

        return {
            "conversation_id": conversation_id,
            "summaries": [s.to_dict() for s in summaries],
            "turns_analyzed": len(turns),
        }

    def get_summary(
        self,
        conversation_id: str,
        level: str = "summary",
    ) -> Optional[ConversationSummary]:
        """Get summary at specific level"""
        summaries = self.summaries.get(conversation_id, [])
        for s in summaries:
            if s.level.value == level:
                return s
        return None


# Global engine
summarization_engine = SummarizationEngine()


def summarize_conversation(
    conversation_id: str,
    turns: list,
) -> dict:
    """Summarize conversation"""
    return summarization_engine.summarize_conversation(conversation_id, turns)


def get_summary(conversation_id: str, level: str = "summary") -> dict:
    """Get summary at level"""
    summary = summarization_engine.get_summary(conversation_id, level)
    return summary.to_dict() if summary else {"error": "Summary not found"}
