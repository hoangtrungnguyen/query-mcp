"""Long-term memory consolidation and pattern persistence across conversations"""

import json
from pathlib import Path
from datetime import datetime
from typing import Optional, List, Dict, Any
from dataclasses import dataclass, field
from enum import Enum

MEMORY_DIR = Path.home() / ".memory-mcp" / "memory-consolidation"
MEMORY_DIR.mkdir(exist_ok=True, parents=True)


class PatternType(Enum):
    """Type of conversation pattern"""
    SOLUTION = "solution"  # Successful approach to a problem
    FAILURE = "failure"  # What didn't work
    SEQUENCE = "sequence"  # Effective sequence of steps
    CLARIFICATION = "clarification"  # Good clarification for this topic
    ADAPTATION = "adaptation"  # Effective style adaptation


class PatternRelevance(Enum):
    """How relevant pattern is to new context"""
    EXACT = "exact"  # Directly matches current situation
    ANALOGOUS = "analogous"  # Similar structure, different domain
    PARTIAL = "partial"  # Some elements apply
    DISTANT = "distant"  # Tangentially related


@dataclass
class ConversationPattern:
    """Reusable pattern from past conversation"""
    pattern_id: str
    pattern_type: PatternType
    topic: str  # What conversation was about
    context_tags: List[str]  # Searchable metadata (user_type, domain, etc)
    description: str  # What pattern is
    execution_steps: List[str]  # How to apply it
    success_rate: float  # % of times it worked (0-1)
    sample_size: int  # Number of observations
    learned_at: str = ""
    last_used: Optional[str] = None
    effectiveness_evidence: List[str] = field(default_factory=list)

    def __post_init__(self):
        if not self.learned_at:
            self.learned_at = datetime.now().isoformat()

    def to_dict(self) -> Dict:
        """Serialize pattern"""
        return {
            "pattern_id": self.pattern_id,
            "type": self.pattern_type.value,
            "topic": self.topic,
            "success_rate": round(self.success_rate, 2),
            "sample_size": self.sample_size,
        }


@dataclass
class PatternMatch:
    """Match between new situation and stored pattern"""
    pattern_id: str
    relevance: PatternRelevance
    confidence: float  # 0-1, how confident in match
    explanation: str
    suggested_steps: List[str]

    def to_dict(self) -> Dict:
        """Serialize match"""
        return {
            "pattern_id": self.pattern_id,
            "relevance": self.relevance.value,
            "confidence": round(self.confidence, 2),
        }


@dataclass
class MemoryNarrative:
    """Narrative summary of successful conversation"""
    narrative_id: str
    conversation_id: str
    goal: str
    outcome: str  # What was achieved
    key_moments: List[str]  # Important turning points
    extracted_patterns: List[str]  # Pattern IDs extracted from this conversation
    duration_turns: int
    user_satisfaction: float  # 0-1 if known
    created_at: str = ""

    def __post_init__(self):
        if not self.created_at:
            self.created_at = datetime.now().isoformat()

    def to_dict(self) -> Dict:
        """Serialize narrative"""
        return {
            "narrative_id": self.narrative_id,
            "goal": self.goal,
            "outcome": self.outcome,
            "patterns_extracted": len(self.extracted_patterns),
            "satisfaction": round(self.user_satisfaction, 2) if self.user_satisfaction else None,
        }


class PatternMatcher:
    """Match current situations to stored patterns"""

    @staticmethod
    def calculate_relevance(
        pattern: ConversationPattern,
        current_tags: List[str],
    ) -> PatternRelevance:
        """Calculate how relevant pattern is to current situation"""
        if not pattern.context_tags:
            return PatternRelevance.PARTIAL

        pattern_set = set(pattern.context_tags)
        current_set = set(current_tags)

        overlap = len(pattern_set & current_set)
        total = len(pattern_set | current_set)

        if total == 0:
            return PatternRelevance.PARTIAL

        overlap_ratio = overlap / total

        if overlap_ratio >= 0.8:
            return PatternRelevance.EXACT
        elif overlap_ratio >= 0.5:
            return PatternRelevance.ANALOGOUS
        elif overlap_ratio >= 0.3:
            return PatternRelevance.PARTIAL
        else:
            return PatternRelevance.DISTANT

    @staticmethod
    def calculate_match_confidence(
        pattern: ConversationPattern,
        relevance: PatternRelevance,
        success_rate: float,
    ) -> float:
        """Calculate confidence in pattern match"""
        relevance_scores = {
            PatternRelevance.EXACT: 1.0,
            PatternRelevance.ANALOGOUS: 0.7,
            PatternRelevance.PARTIAL: 0.4,
            PatternRelevance.DISTANT: 0.2,
        }

        relevance_score = relevance_scores[relevance]

        # Increase confidence with larger sample size
        sample_confidence = min(1.0, (pattern.sample_size / 10) ** 0.5)

        return relevance_score * success_rate * sample_confidence


class MemoryConsolidator:
    """Consolidate and manage learned patterns"""

    def __init__(self):
        self.patterns: Dict[str, ConversationPattern] = {}
        self.narratives: Dict[str, MemoryNarrative] = {}

    def record_conversation_success(
        self,
        conversation_id: str,
        goal: str,
        outcome: str,
        key_moments: List[str],
        user_satisfaction: float = 0.5,
    ) -> MemoryNarrative:
        """Record successful conversation as narrative"""
        narrative = MemoryNarrative(
            narrative_id=f"narr_{len(self.narratives)}",
            conversation_id=conversation_id,
            goal=goal,
            outcome=outcome,
            key_moments=key_moments,
            extracted_patterns=[],
            duration_turns=len(key_moments),
            user_satisfaction=user_satisfaction,
        )
        self.narratives[narrative.narrative_id] = narrative
        return narrative

    def extract_pattern(
        self,
        narrative_id: str,
        pattern_type: PatternType,
        topic: str,
        context_tags: List[str],
        description: str,
        execution_steps: List[str],
        initial_effectiveness: float = 0.8,
    ) -> ConversationPattern:
        """Extract reusable pattern from narrative"""
        pattern = ConversationPattern(
            pattern_id=f"pat_{len(self.patterns)}",
            pattern_type=pattern_type,
            topic=topic,
            context_tags=context_tags,
            description=description,
            execution_steps=execution_steps,
            success_rate=initial_effectiveness,
            sample_size=1,
        )

        self.patterns[pattern.pattern_id] = pattern

        if narrative_id in self.narratives:
            self.narratives[narrative_id].extracted_patterns.append(pattern.pattern_id)

        return pattern

    def find_relevant_patterns(
        self,
        topic: str,
        context_tags: List[str],
        min_confidence: float = 0.5,
    ) -> List[PatternMatch]:
        """Find patterns relevant to current situation"""
        matches = []

        for pattern in self.patterns.values():
            # Filter by topic
            if pattern.topic.lower() not in topic.lower() and topic.lower() not in pattern.topic.lower():
                continue

            relevance = PatternMatcher.calculate_relevance(pattern, context_tags)
            confidence = PatternMatcher.calculate_match_confidence(
                pattern,
                relevance,
                pattern.success_rate,
            )

            if confidence >= min_confidence:
                match = PatternMatch(
                    pattern_id=pattern.pattern_id,
                    relevance=relevance,
                    confidence=confidence,
                    explanation=pattern.description,
                    suggested_steps=pattern.execution_steps,
                )
                matches.append(match)

        # Sort by confidence
        matches.sort(key=lambda m: m.confidence, reverse=True)
        return matches

    def record_pattern_use(
        self,
        pattern_id: str,
        succeeded: bool,
    ):
        """Record outcome of using a pattern"""
        if pattern_id not in self.patterns:
            return

        pattern = self.patterns[pattern_id]
        pattern.last_used = datetime.now().isoformat()

        # Update success rate
        old_success = pattern.success_rate * pattern.sample_size
        old_success += 1.0 if succeeded else 0.0
        pattern.sample_size += 1
        pattern.success_rate = old_success / pattern.sample_size

    def get_pattern_library_summary(self) -> Dict[str, Any]:
        """Get summary of learned patterns"""
        if not self.patterns:
            return {"patterns": 0, "narratives": 0}

        by_type = {}
        for pattern in self.patterns.values():
            ptype = pattern.pattern_type.value
            if ptype not in by_type:
                by_type[ptype] = 0
            by_type[ptype] += 1

        high_confidence = [p for p in self.patterns.values() if p.success_rate > 0.7]

        return {
            "total_patterns": len(self.patterns),
            "total_narratives": len(self.narratives),
            "patterns_by_type": by_type,
            "high_confidence_patterns": len(high_confidence),
            "avg_success_rate": round(
                sum(p.success_rate for p in self.patterns.values()) / len(self.patterns), 2
            ) if self.patterns else 0,
        }


class ConsolidationManager:
    """Manage memory consolidation across conversations"""

    def __init__(self):
        self.consolidators: Dict[str, MemoryConsolidator] = {}

    def create_consolidator(self, consolidator_id: str) -> MemoryConsolidator:
        """Create consolidator"""
        consolidator = MemoryConsolidator()
        self.consolidators[consolidator_id] = consolidator
        return consolidator

    def get_consolidator(self, consolidator_id: str) -> Optional[MemoryConsolidator]:
        """Get consolidator"""
        return self.consolidators.get(consolidator_id)


# Global manager
consolidation_manager = ConsolidationManager()


# MCP Tools

def create_consolidator(consolidator_id: str) -> dict:
    """Create memory consolidator"""
    consolidator = consolidation_manager.create_consolidator(consolidator_id)
    return {"consolidator_id": consolidator_id, "created": True}


def record_conversation_success(
    consolidator_id: str,
    conversation_id: str,
    goal: str,
    outcome: str,
    key_moments: list,
    satisfaction: float = 0.5,
) -> dict:
    """Record successful conversation"""
    consolidator = consolidation_manager.get_consolidator(consolidator_id)
    if not consolidator:
        return {"error": "Consolidator not found"}

    narrative = consolidator.record_conversation_success(
        conversation_id, goal, outcome, key_moments, satisfaction
    )
    return narrative.to_dict()


def extract_pattern(
    consolidator_id: str,
    narrative_id: str,
    pattern_type: str,
    topic: str,
    context_tags: list,
    description: str,
    execution_steps: list,
    effectiveness: float = 0.8,
) -> dict:
    """Extract pattern from narrative"""
    consolidator = consolidation_manager.get_consolidator(consolidator_id)
    if not consolidator:
        return {"error": "Consolidator not found"}

    try:
        ptype = PatternType(pattern_type)
        pattern = consolidator.extract_pattern(
            narrative_id, ptype, topic, context_tags, description, execution_steps, effectiveness
        )
        return pattern.to_dict()
    except ValueError:
        return {"error": f"Invalid pattern type: {pattern_type}"}


def find_relevant_patterns(
    consolidator_id: str,
    topic: str,
    context_tags: list,
    min_confidence: float = 0.5,
) -> dict:
    """Find relevant patterns"""
    consolidator = consolidation_manager.get_consolidator(consolidator_id)
    if not consolidator:
        return {"error": "Consolidator not found"}

    matches = consolidator.find_relevant_patterns(topic, context_tags, min_confidence)
    return {
        "matches": len(matches),
        "patterns": [m.to_dict() for m in matches],
    }


def record_pattern_use(consolidator_id: str, pattern_id: str, succeeded: bool) -> dict:
    """Record pattern use outcome"""
    consolidator = consolidation_manager.get_consolidator(consolidator_id)
    if not consolidator:
        return {"error": "Consolidator not found"}

    consolidator.record_pattern_use(pattern_id, succeeded)
    return {"recorded": True}


def get_library_summary(consolidator_id: str) -> dict:
    """Get pattern library summary"""
    consolidator = consolidation_manager.get_consolidator(consolidator_id)
    if not consolidator:
        return {"error": "Consolidator not found"}

    return consolidator.get_pattern_library_summary()


if __name__ == "__main__":
    consolidator = MemoryConsolidator()

    # Record narrative
    narrative = consolidator.record_conversation_success(
        "conv_1",
        "Explain machine learning",
        "User understood concepts",
        ["Started with intuition", "Moved to math", "Provided examples"],
        0.9,
    )

    # Extract pattern
    pattern = consolidator.extract_pattern(
        narrative.narrative_id,
        PatternType.SEQUENCE,
        "explanation",
        ["technical", "visual", "patient_user"],
        "Start intuitive then formalize",
        ["Intuition first", "Then formalize", "Validate understanding"],
        0.85,
    )

    # Find patterns
    matches = consolidator.find_relevant_patterns(
        "explanation",
        ["technical", "visual"],
    )

    print(f"Matches: {len(matches)}")
    print(f"Summary: {consolidator.get_pattern_library_summary()}")
