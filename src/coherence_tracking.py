"""Multi-turn coherence tracking and discourse analysis"""

import json
from pathlib import Path
from datetime import datetime
from typing import Optional, List, Dict, Any
from dataclasses import dataclass, field
from enum import Enum

COHERENCE_DIR = Path.home() / ".memory-mcp" / "coherence-tracking"
COHERENCE_DIR.mkdir(exist_ok=True, parents=True)


class CoherenceLink(Enum):
    """Types of coherence links between discourse segments"""
    ENTITY_CHAIN = "entity_chain"  # Same entity mentioned
    TEMPORAL = "temporal"  # Temporal ordering
    CAUSAL = "causal"  # Cause-effect
    RHETORICAL = "rhetorical"  # Elaboration, contrast, etc.
    TOPIC_CONTINUATION = "topic_continuation"  # Same topic
    ELLIPSIS = "ellipsis"  # Omitted elements


@dataclass
class EntityChain:
    """Chain of mentions of same entity"""
    chain_id: str
    entity_id: str
    entity_text: str
    mentions: List[int] = field(default_factory=list)  # Turn indices
    pronouns: List[str] = field(default_factory=list)  # Pronouns used
    frequency: int = 0
    continuity: float = 0.8  # How continuous (penalties for gaps)

    def to_dict(self) -> Dict:
        """Serialize chain"""
        return {
            "chain_id": self.chain_id,
            "entity_id": self.entity_id,
            "mentions": len(self.mentions),
            "continuity": round(self.continuity, 2),
        }


@dataclass
class TemporalOrdering:
    """Temporal relationships between events"""
    ordering_id: str
    event1: str  # Turn reference
    event2: str  # Turn reference
    relation: str  # BEFORE, AFTER, DURING, SIMULTANEOUS
    explicitness: float  # How explicit (0-1)

    def to_dict(self) -> Dict:
        """Serialize ordering"""
        return {
            "ordering_id": self.ordering_id,
            "relation": self.relation,
            "explicitness": round(self.explicitness, 2),
        }


@dataclass
class TopicContinuity:
    """Topic maintenance across turns"""
    continuity_id: str
    topic: str
    start_turn: int
    end_turn: int
    mentions: int  # How many times mentioned
    consistency: float  # How consistent discussion
    coherence: float  # How coherent discussion

    def to_dict(self) -> Dict:
        """Serialize continuity"""
        return {
            "continuity_id": self.continuity_id,
            "topic": self.topic,
            "span": f"{self.start_turn}-{self.end_turn}",
            "consistency": round(self.consistency, 2),
            "coherence": round(self.coherence, 2),
        }


@dataclass
class DiscourseSegment:
    """Single turn or utterance in discourse"""
    segment_id: str
    turn_num: int
    text: str
    speaker: str  # user or assistant
    entities: List[str] = field(default_factory=list)  # Entity IDs mentioned
    topics: List[str] = field(default_factory=list)  # Topics discussed
    events: List[str] = field(default_factory=list)  # Events mentioned
    outgoing_links: List[CoherenceLink] = field(default_factory=list)  # Links to previous

    def to_dict(self) -> Dict:
        """Serialize segment"""
        return {
            "segment_id": self.segment_id,
            "turn": self.turn_num,
            "speaker": self.speaker,
            "entities": len(self.entities),
            "topics": len(self.topics),
        }


class CoherenceAnalyzer:
    """Analyze coherence across turns"""

    @staticmethod
    def analyze_entity_chains(
        segments: List[DiscourseSegment],
    ) -> List[EntityChain]:
        """Analyze entity chains across discourse"""
        entity_mentions: Dict[str, List[int]] = {}
        chains = []

        for segment in segments:
            for entity in segment.entities:
                if entity not in entity_mentions:
                    entity_mentions[entity] = []
                entity_mentions[entity].append(segment.turn_num)

        # Create chains
        for entity_id, mentions in entity_mentions.items():
            if len(mentions) > 0:
                gaps = [mentions[i+1] - mentions[i] for i in range(len(mentions)-1)]
                avg_gap = sum(gaps) / len(gaps) if gaps else 0

                # Penalty for gaps
                continuity = 1.0 - min(0.5, avg_gap * 0.1)

                chain = EntityChain(
                    chain_id=f"chain_{entity_id}",
                    entity_id=entity_id,
                    entity_text=f"entity_{entity_id}",
                    mentions=mentions,
                    frequency=len(mentions),
                    continuity=max(0.0, continuity),
                )
                chains.append(chain)

        return chains

    @staticmethod
    def analyze_temporal_ordering(
        segments: List[DiscourseSegment],
    ) -> List[TemporalOrdering]:
        """Analyze temporal ordering of events"""
        orderings = []

        for i in range(len(segments) - 1):
            curr = segments[i]
            next_seg = segments[i + 1]

            if curr.events and next_seg.events:
                for evt1 in curr.events:
                    for evt2 in next_seg.events:
                        ordering = TemporalOrdering(
                            ordering_id=f"order_{i}_{i+1}",
                            event1=f"turn_{curr.turn_num}",
                            event2=f"turn_{next_seg.turn_num}",
                            relation="BEFORE",
                            explicitness=0.7,
                        )
                        orderings.append(ordering)
                        break

        return orderings

    @staticmethod
    def analyze_topic_continuity(
        segments: List[DiscourseSegment],
    ) -> List[TopicContinuity]:
        """Analyze topic continuity across turns"""
        topic_spans: Dict[str, List[int]] = {}

        for segment in segments:
            for topic in segment.topics:
                if topic not in topic_spans:
                    topic_spans[topic] = []
                topic_spans[topic].append(segment.turn_num)

        continuities = []
        for topic, turns in topic_spans.items():
            if turns:
                start = min(turns)
                end = max(turns)
                span = end - start + 1

                consistency = 1.0 - (len(set(range(start, end + 1)) - set(turns)) / span)
                coherence = consistency * 0.9  # Slightly lower than consistency

                cont = TopicContinuity(
                    continuity_id=f"cont_{topic}",
                    topic=topic,
                    start_turn=start,
                    end_turn=end,
                    mentions=len(turns),
                    consistency=max(0.0, consistency),
                    coherence=max(0.0, coherence),
                )
                continuities.append(cont)

        return continuities


class CoherenceTracker:
    """Track coherence across conversation"""

    def __init__(self):
        self.segments: Dict[int, DiscourseSegment] = {}
        self.entity_chains: List[EntityChain] = []
        self.temporal_orderings: List[TemporalOrdering] = []
        self.topic_continuities: List[TopicContinuity] = []
        self.overall_coherence: float = 0.8

    def add_segment(
        self,
        turn_num: int,
        text: str,
        speaker: str,
        entities: List[str] = None,
        topics: List[str] = None,
        events: List[str] = None,
    ) -> Dict[str, Any]:
        """Add discourse segment and analyze coherence"""
        segment = DiscourseSegment(
            segment_id=f"seg_{turn_num}",
            turn_num=turn_num,
            text=text,
            speaker=speaker,
            entities=entities or [],
            topics=topics or [],
            events=events or [],
        )
        self.segments[turn_num] = segment

        # Recompute coherence
        all_segments = list(self.segments.values())

        self.entity_chains = CoherenceAnalyzer.analyze_entity_chains(all_segments)
        self.temporal_orderings = CoherenceAnalyzer.analyze_temporal_ordering(all_segments)
        self.topic_continuities = CoherenceAnalyzer.analyze_topic_continuity(all_segments)

        # Compute overall coherence
        coherence_scores = []
        if self.entity_chains:
            coherence_scores.extend([c.continuity for c in self.entity_chains])
        if self.topic_continuities:
            coherence_scores.extend([c.coherence for c in self.topic_continuities])

        self.overall_coherence = (
            sum(coherence_scores) / len(coherence_scores)
            if coherence_scores else 0.8
        )

        return {
            "segment_id": segment.segment_id,
            "turn": turn_num,
            "overall_coherence": round(self.overall_coherence, 2),
            "entity_chains": len(self.entity_chains),
            "topic_continuities": len(self.topic_continuities),
        }

    def get_coherence_report(self) -> Dict[str, Any]:
        """Get detailed coherence report"""
        return {
            "overall_coherence": round(self.overall_coherence, 2),
            "total_segments": len(self.segments),
            "entity_chains": [c.to_dict() for c in self.entity_chains],
            "temporal_orderings": len(self.temporal_orderings),
            "topic_continuities": [t.to_dict() for t in self.topic_continuities],
            "coherence_assessment": (
                "excellent" if self.overall_coherence > 0.85 else
                "good" if self.overall_coherence > 0.7 else
                "fair" if self.overall_coherence > 0.5 else
                "poor"
            ),
        }


class CoherenceManager:
    """Manage coherence tracking across conversations"""

    def __init__(self):
        self.trackers: Dict[str, CoherenceTracker] = {}

    def create_tracker(self, tracker_id: str) -> CoherenceTracker:
        """Create coherence tracker"""
        tracker = CoherenceTracker()
        self.trackers[tracker_id] = tracker
        return tracker

    def get_tracker(self, tracker_id: str) -> Optional[CoherenceTracker]:
        """Get tracker"""
        return self.trackers.get(tracker_id)


# Global manager
coherence_manager = CoherenceManager()


# MCP Tools

def create_coherence_tracker(tracker_id: str) -> dict:
    """Create coherence tracker"""
    tracker = coherence_manager.create_tracker(tracker_id)
    return {"tracker_id": tracker_id, "created": True}


def add_segment(
    tracker_id: str,
    turn_num: int,
    text: str,
    speaker: str,
    entities: list = None,
    topics: list = None,
) -> dict:
    """Add discourse segment"""
    tracker = coherence_manager.get_tracker(tracker_id)
    if not tracker:
        return {"error": "Tracker not found"}

    return tracker.add_segment(turn_num, text, speaker, entities, topics)


def get_coherence_report(tracker_id: str) -> dict:
    """Get coherence report"""
    tracker = coherence_manager.get_tracker(tracker_id)
    if not tracker:
        return {"error": "Tracker not found"}

    return tracker.get_coherence_report()


if __name__ == "__main__":
    tracker = CoherenceTracker()

    # Add segments
    tracker.add_segment(
        1,
        "John is a software engineer.",
        "user",
        entities=["ent_john"],
        topics=["profession"],
    )
    tracker.add_segment(
        2,
        "He works on machine learning projects.",
        "assistant",
        entities=["ent_john"],
        topics=["profession", "machine_learning"],
    )
    tracker.add_segment(
        3,
        "What does he focus on?",
        "user",
        entities=["ent_john"],
        topics=["machine_learning"],
    )

    report = tracker.get_coherence_report()
    print(f"Report: {json.dumps(report, indent=2)}")
