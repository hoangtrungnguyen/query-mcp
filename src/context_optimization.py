"""Context window optimization and efficient token management"""

import json
from pathlib import Path
from datetime import datetime
from typing import Optional, List, Dict, Any
from dataclasses import dataclass, field
from enum import Enum

CONTEXT_DIR = Path.home() / ".memory-mcp" / "context-optimization"
CONTEXT_DIR.mkdir(exist_ok=True, parents=True)


class SummarizationLevel(Enum):
    """Levels of summarization"""
    NONE = 0  # Full context
    LIGHT = 1  # Minimal compression
    MODERATE = 2  # Balanced compression
    AGGRESSIVE = 3  # Maximum compression
    EXTREME = 4  # Extreme summarization


class ContextImportance(Enum):
    """Importance of context segment"""
    CRITICAL = 1.0  # Must preserve
    HIGH = 0.75
    MEDIUM = 0.5
    LOW = 0.25
    TRIVIAL = 0.0


@dataclass
class ContextSegment:
    """Single unit of conversation context"""
    segment_id: str
    content: str
    token_count: int
    importance: ContextImportance
    type: str  # "user_query", "assistant_response", "tool_output", "meta"
    created_at: str = ""
    last_accessed: str = ""
    access_count: int = 0

    def __post_init__(self):
        if not self.created_at:
            self.created_at = datetime.now().isoformat()
        if not self.last_accessed:
            self.last_accessed = self.created_at

    def to_dict(self) -> Dict:
        """Serialize segment"""
        return {
            "segment_id": self.segment_id,
            "tokens": self.token_count,
            "importance": self.importance.name,
            "type": self.type,
            "accesses": self.access_count,
        }


@dataclass
class ContextSummary:
    """Compressed context representation"""
    summary_id: str
    original_segments: List[str]  # segment IDs
    summary_text: str
    original_tokens: int
    summary_tokens: int
    compression_ratio: float
    preserved_importance: float  # % of important info preserved
    summarization_level: SummarizationLevel
    created_at: str = ""

    def __post_init__(self):
        if not self.created_at:
            self.created_at = datetime.now().isoformat()

    def get_compression_savings(self) -> int:
        """Calculate token savings"""
        return self.original_tokens - self.summary_tokens

    def to_dict(self) -> Dict:
        """Serialize summary"""
        return {
            "summary_id": self.summary_id,
            "original_tokens": self.original_tokens,
            "summary_tokens": self.summary_tokens,
            "compression_ratio": round(self.compression_ratio, 2),
            "savings": self.get_compression_savings(),
            "importance_preserved": round(self.preserved_importance, 2),
        }


@dataclass
class ContextWindowState:
    """Current state of context window"""
    window_id: str
    max_tokens: int
    current_tokens: int
    segments: List[ContextSegment] = field(default_factory=list)
    archived_summaries: List[ContextSummary] = field(default_factory=list)
    total_tokens_saved: int = 0
    created_at: str = ""

    def __post_init__(self):
        if not self.created_at:
            self.created_at = datetime.now().isoformat()

    def get_available_capacity(self) -> int:
        """Get remaining capacity"""
        return max(0, self.max_tokens - self.current_tokens)

    def get_compression_needed(self) -> int:
        """Get tokens needed to free up"""
        if self.current_tokens <= self.max_tokens:
            return 0
        return self.current_tokens - self.max_tokens

    def to_dict(self) -> Dict:
        """Serialize state"""
        return {
            "window_id": self.window_id,
            "capacity": self.max_tokens,
            "current_usage": self.current_tokens,
            "available": self.get_available_capacity(),
            "segments": len(self.segments),
            "summaries": len(self.archived_summaries),
            "tokens_saved": self.total_tokens_saved,
        }


class ContextSelector:
    """Select which context to keep/compress"""

    @staticmethod
    def calculate_segment_score(segment: ContextSegment) -> float:
        """Calculate importance score for segment"""
        # Base score from importance
        score = segment.importance.value

        # Boost for recent access
        recency_bonus = 0.1 if segment.access_count > 0 else 0

        # Boost for critical types
        type_bonus = 0.2 if segment.type in ["user_query", "meta"] else 0

        return min(1.0, score + recency_bonus + type_bonus)

    @staticmethod
    def select_segments_to_keep(
        segments: List[ContextSegment],
        target_tokens: int,
    ) -> tuple[List[ContextSegment], List[ContextSegment]]:
        """Select segments to keep vs compress"""
        # Score each segment
        scored = [
            (seg, ContextSelector.calculate_segment_score(seg))
            for seg in segments
        ]

        # Sort by score (keep high-scoring)
        scored.sort(key=lambda x: x[1], reverse=True)

        keep = []
        compress = []
        current_tokens = 0

        for seg, score in scored:
            if current_tokens + seg.token_count <= target_tokens:
                keep.append(seg)
                current_tokens += seg.token_count
            else:
                compress.append(seg)

        return keep, compress


class ContextCompressor:
    """Compress context segments"""

    @staticmethod
    def compress_segment(
        segment: ContextSegment,
        level: SummarizationLevel = SummarizationLevel.MODERATE,
    ) -> str:
        """Compress single segment"""
        text = segment.content

        if level == SummarizationLevel.NONE:
            return text

        elif level == SummarizationLevel.LIGHT:
            # Keep first sentences
            sentences = text.split(".")
            return ". ".join(sentences[:max(1, len(sentences) // 2)]) + "."

        elif level == SummarizationLevel.MODERATE:
            # Keep key points only
            words = text.split()
            important_words = [w for w in words if len(w) > 3]
            return " ".join(important_words[:len(important_words) // 2])

        elif level == SummarizationLevel.AGGRESSIVE:
            # Extreme compression
            words = [w for w in text.split() if len(w) > 4]
            return " ".join(words[:max(2, len(words) // 3)])

        else:  # EXTREME
            # One sentence summary
            sentences = text.split(".")
            return sentences[0] if sentences else "[compressed]"

    @staticmethod
    def estimate_compressed_tokens(original_tokens: int, level: SummarizationLevel) -> int:
        """Estimate tokens after compression"""
        ratios = {
            SummarizationLevel.NONE: 1.0,
            SummarizationLevel.LIGHT: 0.7,
            SummarizationLevel.MODERATE: 0.4,
            SummarizationLevel.AGGRESSIVE: 0.2,
            SummarizationLevel.EXTREME: 0.05,
        }

        return int(original_tokens * ratios[level])


class ContextWindowManager:
    """Manage context window optimization"""

    def __init__(self, max_tokens: int = 4000):
        self.windows: Dict[str, ContextWindowState] = {}
        self.max_tokens = max_tokens

    def create_window(self, window_id: str) -> ContextWindowState:
        """Create context window"""
        window = ContextWindowState(
            window_id=window_id,
            max_tokens=self.max_tokens,
            current_tokens=0,
        )
        self.windows[window_id] = window
        return window

    def add_segment(
        self,
        window_id: str,
        segment_id: str,
        content: str,
        token_count: int,
        importance: ContextImportance,
        segment_type: str,
    ) -> Optional[ContextSegment]:
        """Add segment to window"""
        if window_id not in self.windows:
            return None

        segment = ContextSegment(
            segment_id=segment_id,
            content=content,
            token_count=token_count,
            importance=importance,
            type=segment_type,
        )

        window = self.windows[window_id]
        window.segments.append(segment)
        window.current_tokens += token_count

        return segment

    def compress_window(
        self,
        window_id: str,
        target_tokens: Optional[int] = None,
        summarization_level: SummarizationLevel = SummarizationLevel.MODERATE,
    ) -> Optional[Dict[str, Any]]:
        """Compress context window"""
        if window_id not in self.windows:
            return None

        window = self.windows[window_id]
        target = target_tokens or window.get_available_capacity() * 2

        # Select which segments to keep
        keep, compress = ContextSelector.select_segments_to_keep(
            window.segments,
            target,
        )

        # Compress selected segments
        compressed_texts = [
            ContextCompressor.compress_segment(seg, summarization_level)
            for seg in compress
        ]
        compressed_content = " ".join(compressed_texts)

        # Create summary
        original_tokens = sum(s.token_count for s in compress)
        summary_tokens = ContextCompressor.estimate_compressed_tokens(
            original_tokens,
            summarization_level,
        )

        summary = ContextSummary(
            summary_id=f"summ_{window_id}",
            original_segments=[s.segment_id for s in compress],
            summary_text=compressed_content,
            original_tokens=original_tokens,
            summary_tokens=summary_tokens,
            compression_ratio=summary_tokens / max(1, original_tokens),
            preserved_importance=(
                sum(s.importance.value for s in keep) /
                max(1, sum(s.importance.value for s in window.segments))
            ),
            summarization_level=summarization_level,
        )

        # Update window
        window.segments = keep
        window.archived_summaries.append(summary)
        window.current_tokens = sum(s.token_count for s in keep)
        window.total_tokens_saved += summary.get_compression_savings()

        return {
            "window_id": window_id,
            "kept_segments": len(keep),
            "compressed_segments": len(compress),
            "tokens_freed": summary.get_compression_savings(),
            "new_usage": window.current_tokens,
        }

    def get_window_status(self, window_id: str) -> Optional[Dict]:
        """Get window status"""
        if window_id not in self.windows:
            return None

        window = self.windows[window_id]
        return {
            "window_id": window_id,
            "capacity": window.max_tokens,
            "current_usage": window.current_tokens,
            "available": window.get_available_capacity(),
            "compression_needed": window.get_compression_needed(),
            "segments": len(window.segments),
            "summaries": len(window.archived_summaries),
            "health": (
                "healthy" if window.get_available_capacity() > 0
                else "exceeded"
            ),
        }

    def optimize_for_next_turn(self, window_id: str, incoming_tokens: int) -> Dict[str, Any]:
        """Optimize window to accommodate incoming tokens"""
        if window_id not in self.windows:
            return {"error": "Window not found"}

        window = self.windows[window_id]
        needed = window.current_tokens + incoming_tokens - window.max_tokens

        if needed <= 0:
            return {
                "optimization_needed": False,
                "available_capacity": window.get_available_capacity(),
            }

        # Need to free up space
        target_tokens = window.max_tokens - incoming_tokens - 100  # Leave 100 token buffer

        result = self.compress_window(
            window_id,
            target_tokens,
            SummarizationLevel.MODERATE,
        )

        return {
            "optimization_needed": True,
            "tokens_to_free": needed,
            "compression_result": result,
            "new_available": window.get_available_capacity(),
        }


class ContextManager:
    """Manage multiple context windows"""

    def __init__(self):
        self.window_managers: Dict[str, ContextWindowManager] = {}

    def create_manager(self, manager_id: str, max_tokens: int = 4000) -> ContextWindowManager:
        """Create context manager"""
        manager = ContextWindowManager(max_tokens)
        self.window_managers[manager_id] = manager
        return manager

    def get_manager(self, manager_id: str) -> Optional[ContextWindowManager]:
        """Get manager"""
        return self.window_managers.get(manager_id)


# Global manager
context_manager = ContextManager()


# MCP Tools

def create_context_manager(manager_id: str, max_tokens: int = 4000) -> dict:
    """Create context manager"""
    manager = context_manager.create_manager(manager_id, max_tokens)
    return {"manager_id": manager_id, "max_tokens": max_tokens, "created": True}


def create_context_window(manager_id: str, window_id: str) -> dict:
    """Create context window"""
    manager = context_manager.get_manager(manager_id)
    if not manager:
        return {"error": "Manager not found"}

    window = manager.create_window(window_id)
    return window.to_dict()


def add_context_segment(
    manager_id: str,
    window_id: str,
    segment_id: str,
    content: str,
    token_count: int,
    importance: str,
    segment_type: str,
) -> dict:
    """Add context segment"""
    manager = context_manager.get_manager(manager_id)
    if not manager:
        return {"error": "Manager not found"}

    segment = manager.add_segment(
        window_id,
        segment_id,
        content,
        token_count,
        ContextImportance[importance],
        segment_type,
    )
    return segment.to_dict() if segment else {"error": "Window not found"}


def compress_context_window(manager_id: str, window_id: str) -> dict:
    """Compress context window"""
    manager = context_manager.get_manager(manager_id)
    if not manager:
        return {"error": "Manager not found"}

    result = manager.compress_window(window_id)
    return result or {"error": "Window not found"}


def get_window_status(manager_id: str, window_id: str) -> dict:
    """Get window status"""
    manager = context_manager.get_manager(manager_id)
    if not manager:
        return {"error": "Manager not found"}

    status = manager.get_window_status(window_id)
    return status or {"error": "Window not found"}


def optimize_for_incoming_tokens(
    manager_id: str,
    window_id: str,
    incoming_tokens: int,
) -> dict:
    """Optimize window for incoming tokens"""
    manager = context_manager.get_manager(manager_id)
    if not manager:
        return {"error": "Manager not found"}

    return manager.optimize_for_next_turn(window_id, incoming_tokens)


if __name__ == "__main__":
    # Test context optimization
    manager = ContextWindowManager(max_tokens=1000)
    window = manager.create_window("win_1")

    # Add segments
    manager.add_segment(
        "win_1",
        "seg_1",
        "This is a critical user query about Python programming",
        50,
        ContextImportance.CRITICAL,
        "user_query",
    )
    manager.add_segment(
        "win_1",
        "seg_2",
        "The assistant provided a comprehensive response about decorators and closures",
        150,
        ContextImportance.HIGH,
        "assistant_response",
    )
    manager.add_segment(
        "win_1",
        "seg_3",
        "Some verbose tool output that might not be as important",
        300,
        ContextImportance.LOW,
        "tool_output",
    )

    # Check status
    status = manager.get_window_status("win_1")
    print(f"Status: {json.dumps(status, indent=2)}")

    # Compress
    result = manager.compress_window("win_1", target_tokens=400)
    print(f"Compression: {json.dumps(result, indent=2)}")

    # New status
    status = manager.get_window_status("win_1")
    print(f"After compression: {json.dumps(status, indent=2)}")
