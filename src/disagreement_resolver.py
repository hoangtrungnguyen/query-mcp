"""Disagreement resolution: explore divergent views, find common ground, handle irresolvable differences"""

import json
from pathlib import Path
from datetime import datetime
from typing import Optional, List, Dict, Any
from dataclasses import dataclass, field
from enum import Enum

DISAGREEMENT_DIR = Path.home() / ".memory-mcp" / "disagreement-resolver"
DISAGREEMENT_DIR.mkdir(exist_ok=True, parents=True)


class DisagreementType(Enum):
    """Type of disagreement"""
    FACTUAL = "factual"  # Different facts/information
    VALUE = "value"  # Different values or priorities
    APPROACH = "approach"  # Different methods to same goal
    PRIORITY = "priority"  # Different importance ranking
    INTERPRETATION = "interpretation"  # Different meaning of facts
    FEASIBILITY = "feasibility"  # Different judgment on what's possible


class ResolutionPath(Enum):
    """How disagreement could be resolved"""
    CONVERGENCE = "convergence"  # Find common ground, agree on solution
    COMPROMISE = "compromise"  # Both sides give ground
    DEFER = "defer"  # Agree to revisit later with more info
    ACCEPT_DIVERGENCE = "accept_divergence"  # Agree to disagree, maintain respect
    ESCALATE = "escalate"  # Need third party or expert


@dataclass
class Position:
    """One party's position in disagreement"""
    position_id: str
    holder: str  # "user" or "agent"
    statement: str  # What they claim/believe
    evidence: List[str]  # Supporting evidence/reasoning
    confidence: float  # How confident (0-1)
    values_implicit: List[str]  # Underlying values
    concerns: List[str]  # Why they care about this

    def to_dict(self) -> Dict:
        """Serialize position"""
        return {
            "position_id": self.position_id,
            "holder": self.holder,
            "statement": self.statement[:100],
            "confidence": round(self.confidence, 2),
            "evidence_points": len(self.evidence),
        }


@dataclass
class DisagreementInstance:
    """Specific disagreement in conversation"""
    disagreement_id: str
    disagreement_type: DisagreementType
    topic: str
    turn_detected: int
    positions: List[Position] = field(default_factory=list)
    common_ground: List[str] = field(default_factory=list)
    suggested_resolutions: List[ResolutionPath] = field(default_factory=list)
    resolved: bool = False
    resolution_path: Optional[ResolutionPath] = None
    resolution_text: str = ""

    def to_dict(self) -> Dict:
        """Serialize disagreement"""
        return {
            "disagreement_id": self.disagreement_id,
            "type": self.disagreement_type.value,
            "topic": self.topic,
            "resolved": self.resolved,
            "common_ground": len(self.common_ground),
        }


class DisagreementAnalyzer:
    """Analyze disagreements"""

    @staticmethod
    def detect_disagreement_signal(
        agent_statement: str,
        user_statement: str,
    ) -> bool:
        """Detect if user is disagreeing with agent"""
        disagreement_words = [
            "no", "not", "disagree", "wrong", "incorrect", "actually",
            "but", "however", "though", "instead", "rather", "opposite"
        ]

        user_lower = user_statement.lower()
        agent_lower = agent_statement.lower()

        # Check for explicit disagreement markers
        has_disagreement = any(word in user_lower for word in disagreement_words)

        # Check if user contradicts agent's key words
        agent_words = set(agent_lower.split())
        user_words = set(user_lower.split())

        # Low overlap + disagreement word = likely disagreement
        overlap = len(agent_words & user_words)
        total = max(len(agent_words), len(user_words))
        similarity = overlap / total if total > 0 else 0

        return has_disagreement and similarity < 0.6

    @staticmethod
    def extract_evidence(statement: str) -> List[str]:
        """Extract evidence points from statement"""
        # Simple: split on "because", "since", "for example"
        evidence = []

        if "because" in statement.lower():
            parts = statement.lower().split("because")
            if len(parts) > 1:
                evidence.append(parts[1][:100])

        if "example" in statement.lower():
            evidence.append("User provided example(s)")

        if "data" in statement.lower() or "study" in statement.lower():
            evidence.append("User referenced research/data")

        return evidence if evidence else ["User asserts this position"]


class DisagreementResolver:
    """Resolve disagreements productively"""

    def __init__(self):
        self.disagreements: Dict[str, DisagreementInstance] = {}

    def record_disagreement(
        self,
        topic: str,
        agent_statement: str,
        user_statement: str,
        disagreement_type: DisagreementType,
        turn_num: int,
    ) -> DisagreementInstance:
        """Record disagreement between agent and user"""
        # Build positions
        agent_position = Position(
            position_id="pos_agent",
            holder="agent",
            statement=agent_statement,
            evidence=DisagreementAnalyzer.extract_evidence(agent_statement),
            confidence=0.7,
            values_implicit=["efficiency", "clarity"],
            concerns=[],
        )

        user_position = Position(
            position_id="pos_user",
            holder="user",
            statement=user_statement,
            evidence=DisagreementAnalyzer.extract_evidence(user_statement),
            confidence=0.6,
            values_implicit=[],
            concerns=["not addressed by agent"],
        )

        disagreement = DisagreementInstance(
            disagreement_id=f"dis_{len(self.disagreements)}",
            disagreement_type=disagreement_type,
            topic=topic,
            turn_detected=turn_num,
            positions=[agent_position, user_position],
        )

        self.disagreements[disagreement.disagreement_id] = disagreement
        return disagreement

    def find_common_ground(self, disagreement_id: str) -> List[str]:
        """Find areas of agreement in disagreement"""
        if disagreement_id not in self.disagreements:
            return []

        disagreement = self.disagreements[disagreement_id]
        if len(disagreement.positions) < 2:
            return []

        pos1_words = set(disagreement.positions[0].statement.lower().split())
        pos2_words = set(disagreement.positions[1].statement.lower().split())

        # Common words that aren't pure agreement
        common = pos1_words & pos2_words
        stop_words = {"the", "a", "an", "and", "or", "is", "it", "to", "for"}
        common = {w for w in common if w not in stop_words and len(w) > 3}

        common_ground = [f"Both mention: {w}" for w in list(common)[:3]]

        # Suggest explicit common ground
        if not common_ground:
            common_ground = ["Both seeking to understand the issue"]

        disagreement.common_ground = common_ground
        return common_ground

    def suggest_resolution_paths(self, disagreement_id: str) -> List[ResolutionPath]:
        """Suggest how to resolve disagreement"""
        if disagreement_id not in self.disagreements:
            return []

        disagreement = self.disagreements[disagreement_id]

        suggestions = []

        # Factual disagreements: find more information
        if disagreement.disagreement_type == DisagreementType.FACTUAL:
            suggestions.append(ResolutionPath.DEFER)
            suggestions.append(ResolutionPath.CONVERGENCE)

        # Value disagreements: find compromise or accept divergence
        elif disagreement.disagreement_type == DisagreementType.VALUE:
            suggestions.append(ResolutionPath.ACCEPT_DIVERGENCE)
            suggestions.append(ResolutionPath.COMPROMISE)

        # Approach disagreements: find best approach
        elif disagreement.disagreement_type == DisagreementType.APPROACH:
            suggestions.append(ResolutionPath.CONVERGENCE)
            suggestions.append(ResolutionPath.COMPROMISE)

        # Priority disagreements: compromise or defer
        elif disagreement.disagreement_type == DisagreementType.PRIORITY:
            suggestions.append(ResolutionPath.COMPROMISE)
            suggestions.append(ResolutionPath.ACCEPT_DIVERGENCE)

        else:
            suggestions.append(ResolutionPath.DEFER)

        disagreement.suggested_resolutions = suggestions
        return suggestions

    def resolve_disagreement(
        self,
        disagreement_id: str,
        resolution_path: ResolutionPath,
        resolution_text: str,
    ):
        """Mark disagreement as resolved"""
        if disagreement_id not in self.disagreements:
            return

        disagreement = self.disagreements[disagreement_id]
        disagreement.resolved = True
        disagreement.resolution_path = resolution_path
        disagreement.resolution_text = resolution_text

    def get_disagreement_report(self, disagreement_id: str) -> Optional[Dict[str, Any]]:
        """Get full disagreement analysis report"""
        if disagreement_id not in self.disagreements:
            return None

        d = self.disagreements[disagreement_id]
        return {
            "disagreement_id": disagreement_id,
            "type": d.disagreement_type.value,
            "topic": d.topic,
            "positions": [p.to_dict() for p in d.positions],
            "common_ground": d.common_ground,
            "suggested_resolutions": [r.value for r in d.suggested_resolutions],
            "resolved": d.resolved,
            "resolution_path": d.resolution_path.value if d.resolution_path else None,
        }


class DisagreementManager:
    """Manage disagreement resolution across conversations"""

    def __init__(self):
        self.resolvers: Dict[str, DisagreementResolver] = {}

    def create_resolver(self, resolver_id: str) -> DisagreementResolver:
        """Create resolver"""
        resolver = DisagreementResolver()
        self.resolvers[resolver_id] = resolver
        return resolver

    def get_resolver(self, resolver_id: str) -> Optional[DisagreementResolver]:
        """Get resolver"""
        return self.resolvers.get(resolver_id)


# Global manager
disagreement_manager = DisagreementManager()


# MCP Tools

def create_disagreement_resolver(resolver_id: str) -> dict:
    """Create disagreement resolver"""
    resolver = disagreement_manager.create_resolver(resolver_id)
    return {"resolver_id": resolver_id, "created": True}


def record_disagreement(
    resolver_id: str,
    topic: str,
    agent_statement: str,
    user_statement: str,
    disagreement_type: str,
    turn_num: int,
) -> dict:
    """Record disagreement"""
    resolver = disagreement_manager.get_resolver(resolver_id)
    if not resolver:
        return {"error": "Resolver not found"}

    try:
        dtype = DisagreementType(disagreement_type)
        disagreement = resolver.record_disagreement(
            topic, agent_statement, user_statement, dtype, turn_num
        )
        return disagreement.to_dict()
    except ValueError:
        return {"error": f"Invalid disagreement type: {disagreement_type}"}


def find_common_ground(resolver_id: str, disagreement_id: str) -> dict:
    """Find common ground"""
    resolver = disagreement_manager.get_resolver(resolver_id)
    if not resolver:
        return {"error": "Resolver not found"}

    common = resolver.find_common_ground(disagreement_id)
    return {"common_ground": common}


def suggest_resolution_paths(resolver_id: str, disagreement_id: str) -> dict:
    """Suggest resolution paths"""
    resolver = disagreement_manager.get_resolver(resolver_id)
    if not resolver:
        return {"error": "Resolver not found"}

    paths = resolver.suggest_resolution_paths(disagreement_id)
    return {"suggested_paths": [p.value for p in paths]}


def resolve_disagreement(
    resolver_id: str,
    disagreement_id: str,
    resolution_path: str,
    resolution_text: str,
) -> dict:
    """Resolve disagreement"""
    resolver = disagreement_manager.get_resolver(resolver_id)
    if not resolver:
        return {"error": "Resolver not found"}

    try:
        rpath = ResolutionPath(resolution_path)
        resolver.resolve_disagreement(disagreement_id, rpath, resolution_text)
        return {"resolved": True}
    except ValueError:
        return {"error": f"Invalid resolution path: {resolution_path}"}


def get_disagreement_report(resolver_id: str, disagreement_id: str) -> dict:
    """Get disagreement report"""
    resolver = disagreement_manager.get_resolver(resolver_id)
    if not resolver:
        return {"error": "Resolver not found"}

    report = resolver.get_disagreement_report(disagreement_id)
    return report or {"error": "Disagreement not found"}


if __name__ == "__main__":
    resolver = DisagreementResolver()

    d = resolver.record_disagreement(
        "Python difficulty",
        "Python is beginner-friendly",
        "Actually Python is really complex",
        DisagreementType.INTERPRETATION,
        5,
    )

    common = resolver.find_common_ground(d.disagreement_id)
    print(f"Common: {common}")

    paths = resolver.suggest_resolution_paths(d.disagreement_id)
    print(f"Paths: {[p.value for p in paths]}")
