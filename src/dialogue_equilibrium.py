"""Dialogue equilibrium management and dynamic rebalancing"""

import json
from pathlib import Path
from datetime import datetime
from typing import Optional, List, Dict, Any
from dataclasses import dataclass, field
from enum import Enum

EQUILIBRIUM_DIR = Path.home() / ".memory-mcp" / "dialogue-equilibrium"
EQUILIBRIUM_DIR.mkdir(exist_ok=True, parents=True)


class DialgueDimension(Enum):
    """Dimensions of dialogue balance"""
    FORMALITY = "formality"  # 0=casual, 1=formal
    PACE = "pace"  # 0=slow, 1=fast
    DIRECTNESS = "directness"  # 0=indirect, 1=direct
    ENGAGEMENT = "engagement"  # 0=passive, 1=active
    EXPLANATION_DEPTH = "explanation_depth"  # 0=brief, 1=detailed
    HUMOR = "humor"  # 0=serious, 1=humorous


class EquilibriumStatus(Enum):
    """Status of dialogue equilibrium"""
    BALANCED = "balanced"  # Agent and user aligned
    DRIFT_AGENT_FORMAL = "drift_agent_formal"  # Agent too formal
    DRIFT_AGENT_CASUAL = "drift_agent_casual"  # Agent too casual
    DRIFT_USER = "drift_user"  # User shifted preferences
    OSCILLATION = "oscillation"  # Values fluctuating
    CONVERGING = "converging"  # Getting closer


@dataclass
class DimensionMeasure:
    """Measurement on dialogue dimension"""
    dimension: DialgueDimension
    agent_value: float  # 0-1, agent's current value
    user_preference: float  # 0-1, what user prefers
    observed_response: str  # User's signal about balance
    confidence: float = 0.7

    def to_dict(self) -> Dict:
        """Serialize measure"""
        return {
            "dimension": self.dimension.value,
            "agent": round(self.agent_value, 2),
            "user_pref": round(self.user_preference, 2),
            "diff": round(abs(self.agent_value - self.user_preference), 2),
        }


@dataclass
class EquilibriumSnapshot:
    """Snapshot of dialogue equilibrium"""
    snapshot_id: str
    turn_num: int
    dimensions: Dict[DialgueDimension, DimensionMeasure] = field(default_factory=dict)
    overall_distance: float = 0.0  # 0-1, how far from equilibrium
    status: EquilibriumStatus = EquilibriumStatus.BALANCED
    timestamp: str = ""

    def __post_init__(self):
        if not self.timestamp:
            self.timestamp = datetime.now().isoformat()

    def to_dict(self) -> Dict:
        """Serialize snapshot"""
        return {
            "snapshot_id": self.snapshot_id,
            "turn": self.turn_num,
            "status": self.status.value,
            "distance": round(self.overall_distance, 2),
        }


@dataclass
class Rebalance:
    """Rebalancing action taken"""
    rebalance_id: str
    dimension: DialgueDimension
    change: float  # How much to shift (-1 to 1)
    reason: str
    turn_num: int
    effectiveness: float = 0.0  # How well it worked (0-1)

    def to_dict(self) -> Dict:
        """Serialize rebalance"""
        return {
            "rebalance_id": self.rebalance_id,
            "dimension": self.dimension.value,
            "change": round(self.change, 2),
            "effectiveness": round(self.effectiveness, 2),
        }


class EquilibriumDetector:
    """Detect dialogue equilibrium and drift"""

    @staticmethod
    def detect_user_preference_shift(
        recent_responses: List[str],
    ) -> Dict[DialgueDimension, float]:
        """Detect user's shifting preferences from recent responses"""
        preferences = {}

        # Simple heuristic analysis
        combined = " ".join(recent_responses).lower()

        # Formality signals
        formal_words = ["furthermore", "nonetheless", "therefore"]
        casual_words = ["yeah", "cool", "awesome"]
        formality = 0.6  # Default
        if any(w in combined for w in formal_words):
            formality = 0.8
        if any(w in combined for w in casual_words):
            formality = 0.3
        preferences[DialgueDimension.FORMALITY] = formality

        # Pace signals
        fast_words = ["quickly", "summary", "brief"]
        slow_words = ["detailed", "explain", "elaborate"]
        pace = 0.5  # Default
        if any(w in combined for w in fast_words):
            pace = 0.8
        if any(w in combined for w in slow_words):
            pace = 0.2
        preferences[DialgueDimension.PACE] = pace

        # Directness signals
        if "?" in combined:
            preferences[DialgueDimension.DIRECTNESS] = 0.3
        else:
            preferences[DialgueDimension.DIRECTNESS] = 0.7

        # Engagement
        engagement_words = ["interesting", "tell me more", "more"]
        preferences[DialgueDimension.ENGAGEMENT] = (
            0.8 if any(w in combined for w in engagement_words) else 0.5
        )

        return preferences

    @staticmethod
    def calculate_distance(
        agent_values: Dict[DialgueDimension, float],
        user_preferences: Dict[DialgueDimension, float],
    ) -> float:
        """Calculate overall distance from equilibrium"""
        if not agent_values or not user_preferences:
            return 0.5

        total_diff = sum(
            abs(agent_values.get(dim, 0.5) - user_preferences.get(dim, 0.5))
            for dim in DialgueDimension
        )
        avg_diff = total_diff / len(DialgueDimension)
        return min(1.0, avg_diff)

    @staticmethod
    def detect_status(
        distance: float,
        previous_distance: Optional[float] = None,
    ) -> EquilibriumStatus:
        """Detect equilibrium status"""
        if distance < 0.2:
            return EquilibriumStatus.BALANCED
        elif distance > 0.5:
            return EquilibriumStatus.DRIFT_USER
        elif previous_distance and abs(distance - previous_distance) > 0.1:
            if distance > previous_distance:
                return EquilibriumStatus.OSCILLATION
            else:
                return EquilibriumStatus.CONVERGING
        else:
            return EquilibriumStatus.BALANCED


class EquilibriumManager:
    """Manage dialogue equilibrium"""

    def __init__(self):
        self.snapshots: List[EquilibriumSnapshot] = []
        self.rebalances: List[Rebalance] = []
        self.current_agent_values: Dict[DialgueDimension, float] = {
            dim: 0.5 for dim in DialgueDimension
        }

    def measure_equilibrium(
        self,
        turn_num: int,
        agent_values: Dict[DialgueDimension, float],
        user_responses: List[str],
    ) -> EquilibriumSnapshot:
        """Measure current equilibrium"""
        # Detect user preferences
        user_prefs = EquilibriumDetector.detect_user_preference_shift(user_responses)

        # Build dimension measures
        dimensions = {}
        for dim in DialgueDimension:
            measure = DimensionMeasure(
                dimension=dim,
                agent_value=agent_values.get(dim, 0.5),
                user_preference=user_prefs.get(dim, 0.5),
                observed_response=" ".join(user_responses[-1:]) if user_responses else "",
            )
            dimensions[dim] = measure

        # Calculate distance
        distance = EquilibriumDetector.calculate_distance(agent_values, user_prefs)

        # Detect status
        previous_distance = self.snapshots[-1].overall_distance if self.snapshots else None
        status = EquilibriumDetector.detect_status(distance, previous_distance)

        snapshot = EquilibriumSnapshot(
            snapshot_id=f"snap_{len(self.snapshots)}",
            turn_num=turn_num,
            dimensions=dimensions,
            overall_distance=distance,
            status=status,
        )

        self.snapshots.append(snapshot)
        self.current_agent_values = agent_values.copy()

        return snapshot

    def recommend_rebalance(self, snapshot: EquilibriumSnapshot) -> List[Rebalance]:
        """Recommend rebalancing actions"""
        rebalances = []

        for dimension, measure in snapshot.dimensions.items():
            diff = measure.agent_value - measure.user_preference

            # If difference > 0.3, recommend rebalance
            if abs(diff) > 0.3:
                change = -diff * 0.5  # Move halfway toward user preference
                reason = (
                    f"User prefers {'higher' if diff > 0 else 'lower'} "
                    f"{dimension.value}"
                )

                rebalance = Rebalance(
                    rebalance_id=f"rebal_{len(rebalances)}",
                    dimension=dimension,
                    change=change,
                    reason=reason,
                    turn_num=len(self.snapshots),
                )
                rebalances.append(rebalance)

        return rebalances

    def apply_rebalance(
        self,
        rebalance: Rebalance,
    ) -> Dict[str, float]:
        """Apply rebalancing and return new values"""
        new_values = self.current_agent_values.copy()

        current = new_values.get(rebalance.dimension, 0.5)
        new_values[rebalance.dimension] = max(0.0, min(1.0, current + rebalance.change))

        self.rebalances.append(rebalance)

        return new_values

    def get_equilibrium_report(self) -> Dict[str, Any]:
        """Get full equilibrium report"""
        if not self.snapshots:
            return {"error": "No measurements yet"}

        latest = self.snapshots[-1]
        recent = self.snapshots[-5:] if len(self.snapshots) > 5 else self.snapshots

        trend = "improving" if recent[-1].overall_distance < recent[0].overall_distance else "degrading"

        return {
            "latest_status": latest.status.value,
            "current_distance": round(latest.overall_distance, 2),
            "trend": trend,
            "snapshots": len(self.snapshots),
            "rebalances_applied": len(self.rebalances),
            "dimensions": {
                d.value: m.to_dict() for d, m in latest.dimensions.items()
            },
        }


class EquilibriumCoordinator:
    """Coordinate equilibrium across conversations"""

    def __init__(self):
        self.managers: Dict[str, EquilibriumManager] = {}

    def create_manager(self, manager_id: str) -> EquilibriumManager:
        """Create manager"""
        manager = EquilibriumManager()
        self.managers[manager_id] = manager
        return manager

    def get_manager(self, manager_id: str) -> Optional[EquilibriumManager]:
        """Get manager"""
        return self.managers.get(manager_id)


# Global coordinator
equilibrium_coordinator = EquilibriumCoordinator()


# MCP Tools

def create_equilibrium_manager(manager_id: str) -> dict:
    """Create equilibrium manager"""
    manager = equilibrium_coordinator.create_manager(manager_id)
    return {"manager_id": manager_id, "created": True}


def measure_equilibrium(
    manager_id: str,
    turn_num: int,
    agent_values: dict,
    user_responses: list,
) -> dict:
    """Measure equilibrium"""
    manager = equilibrium_coordinator.get_manager(manager_id)
    if not manager:
        return {"error": "Manager not found"}

    # Convert dimension names to enum
    agent_vals = {}
    for k, v in agent_values.items():
        try:
            agent_vals[DialgueDimension(k)] = v
        except ValueError:
            pass

    snapshot = manager.measure_equilibrium(turn_num, agent_vals, user_responses)
    return snapshot.to_dict()


def recommend_rebalance(manager_id: str) -> dict:
    """Get rebalancing recommendations"""
    manager = equilibrium_coordinator.get_manager(manager_id)
    if not manager:
        return {"error": "Manager not found"}

    if not manager.snapshots:
        return {"error": "No measurements yet"}

    latest = manager.snapshots[-1]
    rebalances = manager.recommend_rebalance(latest)

    return {
        "recommended": len(rebalances) > 0,
        "rebalances": [r.to_dict() for r in rebalances],
    }


def get_equilibrium_report(manager_id: str) -> dict:
    """Get equilibrium report"""
    manager = equilibrium_coordinator.get_manager(manager_id)
    if not manager:
        return {"error": "Manager not found"}

    return manager.get_equilibrium_report()


if __name__ == "__main__":
    manager = EquilibriumManager()

    # Measure equilibrium
    agent_vals = {DialgueDimension.FORMALITY: 0.8, DialgueDimension.PACE: 0.6}
    snap = manager.measure_equilibrium(1, agent_vals, ["That's too formal"])

    print(f"Snapshot: {json.dumps(snap.to_dict(), indent=2)}")

    # Recommend rebalance
    rebalances = manager.recommend_rebalance(snap)
    print(f"Rebalances: {len(rebalances)}")

    # Get report
    report = manager.get_equilibrium_report()
    print(f"Report: {json.dumps(report, indent=2)}")
