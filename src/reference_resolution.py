"""Reference resolution and anaphora handling"""

import json
from pathlib import Path
from datetime import datetime
from typing import Optional, List, Dict, Any
from dataclasses import dataclass, field
from enum import Enum

REF_DIR = Path.home() / ".memory-mcp" / "reference-resolution"
REF_DIR.mkdir(exist_ok=True, parents=True)


class ReferenceType(Enum):
    """Types of references"""
    PRONOUN = "pronoun"
    DEFINITE_DESCRIPTION = "definite_description"
    DEMONSTRATIVE = "demonstrative"
    ELLIPSIS = "ellipsis"
    PROPER_NOUN = "proper_noun"


class PronounType(Enum):
    """Pronoun categories"""
    PERSONAL = "personal"  # he, she, it, they
    POSSESSIVE = "possessive"  # his, her, its, their
    REFLEXIVE = "reflexive"  # himself, herself, itself
    DEMONSTRATIVE_PRON = "demonstrative_pronoun"  # this, that


@dataclass
class ReferenceCandidate:
    """Possible referent for a reference"""
    entity_id: str
    entity_text: str
    entity_type: str
    distance: int  # Sentences since introduction
    frequency: int  # How many times mentioned
    gender_match: bool = True
    number_match: bool = True
    likelihood: float = 0.5  # P(entity is referent)

    def to_dict(self) -> Dict:
        """Serialize candidate"""
        return {
            "entity_id": self.entity_id,
            "entity_text": self.entity_text,
            "likelihood": round(self.likelihood, 2),
            "distance": self.distance,
        }


@dataclass
class ResolvedReference:
    """Reference with identified referent"""
    reference_id: str
    reference_type: ReferenceType
    reference_text: str
    identified_referent: str  # entity_id
    confidence: float
    candidates: List[ReferenceCandidate] = field(default_factory=list)
    created_at: str = ""

    def __post_init__(self):
        if not self.created_at:
            self.created_at = datetime.now().isoformat()

    def to_dict(self) -> Dict:
        """Serialize resolution"""
        return {
            "reference_id": self.reference_id,
            "type": self.reference_type.value,
            "text": self.reference_text,
            "referent": self.identified_referent,
            "confidence": round(self.confidence, 2),
        }


@dataclass
class EntityMention:
    """Entity mention in discourse"""
    entity_id: str
    text: str
    entity_type: str
    turn: int
    position: int  # Word position
    gender: Optional[str] = None
    number: str = "singular"  # singular, plural
    animacy: str = "animate"  # animate, inanimate


@dataclass
class ReferenceChain:
    """Chain of references to same entity"""
    chain_id: str
    entity_id: str
    mentions: List[EntityMention] = field(default_factory=list)
    coherence: float = 0.8

    def to_dict(self) -> Dict:
        """Serialize chain"""
        return {
            "chain_id": self.chain_id,
            "entity_id": self.entity_id,
            "mention_count": len(self.mentions),
            "coherence": round(self.coherence, 2),
        }


class ReferenceResolver:
    """Resolve references to entities"""

    PRONOUNS = {
        PronounType.PERSONAL: ["he", "she", "it", "they", "him", "her", "them"],
        PronounType.POSSESSIVE: ["his", "her", "its", "their"],
        PronounType.REFLEXIVE: ["himself", "herself", "itself", "themselves"],
        PronounType.DEMONSTRATIVE_PRON: ["this", "that", "these", "those"],
    }

    DEFINITE_DETERMINERS = ["the"]

    @staticmethod
    def resolve_reference(
        reference_text: str,
        current_turn: int,
        previous_entities: Dict[str, EntityMention],
        dialogue_history: List[str],
    ) -> ResolvedReference:
        """Resolve a reference"""
        reference_text_lower = reference_text.lower()
        reference_type = ReferenceResolver._classify_reference(reference_text_lower)

        candidates = []

        # Pronoun resolution
        if reference_type == ReferenceType.PRONOUN:
            candidates = ReferenceResolver._find_pronoun_antecedents(
                reference_text_lower,
                previous_entities,
                current_turn,
            )

        # Definite description resolution
        elif reference_type == ReferenceType.DEFINITE_DESCRIPTION:
            candidates = ReferenceResolver._find_description_antecedents(
                reference_text_lower,
                previous_entities,
            )

        # Demonstrative resolution
        elif reference_type == ReferenceType.DEMONSTRATIVE:
            candidates = ReferenceResolver._find_demonstrative_antecedents(
                reference_text_lower,
                previous_entities,
                current_turn,
            )

        # Select best candidate
        best_candidate = None
        best_likelihood = 0.0
        if candidates:
            best_candidate = max(candidates, key=lambda c: c.likelihood)
            best_likelihood = best_candidate.likelihood

        resolution = ResolvedReference(
            reference_id=f"ref_{int(datetime.now().timestamp())}",
            reference_type=reference_type,
            reference_text=reference_text,
            identified_referent=best_candidate.entity_id if best_candidate else "unknown",
            confidence=best_likelihood,
            candidates=candidates,
        )

        return resolution

    @staticmethod
    def _classify_reference(text: str) -> ReferenceType:
        """Classify reference type"""
        for pron_type, pronouns in ReferenceResolver.PRONOUNS.items():
            if text in pronouns:
                return ReferenceType.PRONOUN

        if text.startswith("the "):
            return ReferenceType.DEFINITE_DESCRIPTION

        if text in ["this", "that", "these", "those"]:
            return ReferenceType.DEMONSTRATIVE

        return ReferenceType.PROPER_NOUN

    @staticmethod
    def _find_pronoun_antecedents(
        pronoun: str,
        entities: Dict[str, EntityMention],
        current_turn: int,
    ) -> List[ReferenceCandidate]:
        """Find candidates for pronoun"""
        candidates = []

        # Determine pronoun properties
        is_plural = pronoun in ["they", "them", "their", "themselves"]
        is_singular = not is_plural

        for entity_id, mention in entities.items():
            match_number = (
                (mention.number == "plural" and is_plural) or
                (mention.number == "singular" and is_singular)
            )

            if not match_number:
                continue

            distance = current_turn - mention.turn
            likelihood = 1.0 / (1.0 + distance * 0.1)  # Decay with distance

            candidate = ReferenceCandidate(
                entity_id=entity_id,
                entity_text=mention.text,
                entity_type=mention.entity_type,
                distance=distance,
                frequency=1,
                number_match=match_number,
                likelihood=likelihood,
            )
            candidates.append(candidate)

        return sorted(candidates, key=lambda c: c.likelihood, reverse=True)

    @staticmethod
    def _find_description_antecedents(
        description: str,
        entities: Dict[str, EntityMention],
    ) -> List[ReferenceCandidate]:
        """Find candidates for definite description"""
        candidates = []

        # Remove "the"
        desc_words = description.replace("the ", "").split()

        for entity_id, mention in entities.items():
            match_count = sum(1 for word in desc_words if word in mention.text.lower())

            if match_count > 0:
                likelihood = match_count / len(desc_words)

                candidate = ReferenceCandidate(
                    entity_id=entity_id,
                    entity_text=mention.text,
                    entity_type=mention.entity_type,
                    distance=0,
                    frequency=1,
                    likelihood=likelihood,
                )
                candidates.append(candidate)

        return sorted(candidates, key=lambda c: c.likelihood, reverse=True)

    @staticmethod
    def _find_demonstrative_antecedents(
        demonstrative: str,
        entities: Dict[str, EntityMention],
        current_turn: int,
    ) -> List[ReferenceCandidate]:
        """Find candidates for demonstrative"""
        candidates = []

        is_distal = demonstrative in ["that", "those"]
        is_proximal = demonstrative in ["this", "these"]

        for entity_id, mention in entities.items():
            distance = current_turn - mention.turn
            if is_proximal and distance > 1:
                continue
            if is_distal and distance <= 1:
                continue

            likelihood = 0.8 if distance <= 1 else 0.5

            candidate = ReferenceCandidate(
                entity_id=entity_id,
                entity_text=mention.text,
                entity_type=mention.entity_type,
                distance=distance,
                frequency=1,
                likelihood=likelihood,
            )
            candidates.append(candidate)

        return sorted(candidates, key=lambda c: c.likelihood, reverse=True)


class ReferenceTracker:
    """Track reference chains across turns"""

    def __init__(self):
        self.chains: Dict[str, ReferenceChain] = {}
        self.entity_mentions: Dict[str, EntityMention] = {}
        self.resolutions: Dict[str, ResolvedReference] = {}

    def add_mention(self, mention: EntityMention):
        """Add entity mention"""
        self.entity_mentions[mention.entity_id] = mention

    def add_resolution(self, resolution: ResolvedReference):
        """Record reference resolution"""
        self.resolutions[resolution.reference_id] = resolution

        # Update or create chain
        referent_id = resolution.identified_referent
        if referent_id not in self.chains:
            self.chains[referent_id] = ReferenceChain(
                chain_id=f"chain_{referent_id}",
                entity_id=referent_id,
            )

    def get_chain(self, entity_id: str) -> Optional[ReferenceChain]:
        """Get reference chain for entity"""
        return self.chains.get(entity_id)

    def get_chains_summary(self) -> Dict[str, Any]:
        """Get summary of reference chains"""
        return {
            "total_chains": len(self.chains),
            "total_resolutions": len(self.resolutions),
            "chains": [c.to_dict() for c in self.chains.values()],
        }


class ReferenceManager:
    """Manage reference resolution across conversations"""

    def __init__(self):
        self.trackers: Dict[str, ReferenceTracker] = {}

    def create_tracker(self, tracker_id: str) -> ReferenceTracker:
        """Create reference tracker"""
        tracker = ReferenceTracker()
        self.trackers[tracker_id] = tracker
        return tracker

    def get_tracker(self, tracker_id: str) -> Optional[ReferenceTracker]:
        """Get tracker"""
        return self.trackers.get(tracker_id)


# Global manager
reference_manager = ReferenceManager()


# MCP Tools

def create_reference_tracker(tracker_id: str) -> dict:
    """Create reference resolution tracker"""
    tracker = reference_manager.create_tracker(tracker_id)
    return {"tracker_id": tracker_id, "created": True}


def resolve_reference(
    tracker_id: str,
    reference_text: str,
    current_turn: int,
    entities: dict,
) -> dict:
    """Resolve reference"""
    tracker = reference_manager.get_tracker(tracker_id)
    if not tracker:
        return {"error": "Tracker not found"}

    # Convert entities dict to EntityMention objects
    entity_mentions = {}
    for eid, edata in entities.items():
        entity_mentions[eid] = EntityMention(
            entity_id=eid,
            text=edata.get("text", ""),
            entity_type=edata.get("type", ""),
            turn=edata.get("turn", 0),
            position=edata.get("position", 0),
        )

    resolution = ReferenceResolver.resolve_reference(
        reference_text,
        current_turn,
        entity_mentions,
        [],
    )
    tracker.add_resolution(resolution)

    return resolution.to_dict()


def get_reference_chains(tracker_id: str) -> dict:
    """Get reference chains"""
    tracker = reference_manager.get_tracker(tracker_id)
    if not tracker:
        return {"error": "Tracker not found"}

    return tracker.get_chains_summary()


if __name__ == "__main__":
    tracker = ReferenceTracker()

    # Add mentions
    mentions = {
        "ent_john": EntityMention(
            entity_id="ent_john",
            text="John",
            entity_type="person",
            turn=1,
            position=0,
            gender="male",
        ),
        "ent_mary": EntityMention(
            entity_id="ent_mary",
            text="Mary",
            entity_type="person",
            turn=1,
            position=5,
            gender="female",
        ),
    }

    for mention in mentions.values():
        tracker.add_mention(mention)

    # Resolve pronouns
    resolution = ReferenceResolver.resolve_reference(
        "he",
        2,
        mentions,
        [],
    )
    tracker.add_resolution(resolution)

    print(f"Resolution: {json.dumps(resolution.to_dict(), indent=2)}")
    print(f"Chains: {json.dumps(tracker.get_chains_summary(), indent=2)}")
