"""Conversation goal introspection and debugging"""

import json
from pathlib import Path
from datetime import datetime
from typing import Optional, List, Dict, Any
from dataclasses import dataclass, field
from enum import Enum

INTROSPECT_DIR = Path.home() / ".memory-mcp" / "goal-introspection"
INTROSPECT_DIR.mkdir(exist_ok=True, parents=True)


class GoalStatus(Enum):
    """Status of conversation goal"""
    PENDING = "pending"
    IN_PROGRESS = "in_progress"
    ACHIEVED = "achieved"
    FAILED = "failed"
    ABANDONED = "abandoned"


class BlockingIssue(Enum):
    """What's blocking goal achievement"""
    MISSING_INFORMATION = "missing_information"
    USER_DISAGREEMENT = "user_disagreement"
    TECHNICAL_LIMITATION = "technical_limitation"
    CONTEXT_MISMATCH = "context_mismatch"
    ASSUMPTION_VIOLATION = "assumption_violation"
    RESOURCE_CONSTRAINT = "resource_constraint"


@dataclass
class AssumptionTrack:
    """Assumption made during conversation"""
    assumption_id: str
    statement: str  # What was assumed
    confidence: float  # How confident (0-1)
    turn_introduced: int
    violated: bool = False
    violation_turn: Optional[int] = None
    violation_evidence: str = ""

    def to_dict(self) -> Dict:
        """Serialize assumption"""
        return {
            "assumption_id": self.assumption_id,
            "statement": self.statement[:100],
            "confidence": round(self.confidence, 2),
            "violated": self.violated,
        }


@dataclass
class DecisionPoint:
    """Key decision in conversation"""
    decision_id: str
    turn_num: int
    description: str  # What was decided
    options_considered: List[str] = field(default_factory=list)
    option_chosen: str = ""
    reasoning: str = ""
    confidence: float = 0.7
    reversible: bool = True  # Can be undone

    def to_dict(self) -> Dict:
        """Serialize decision"""
        return {
            "decision_id": self.decision_id,
            "turn": self.turn_num,
            "description": self.description[:100],
            "confidence": round(self.confidence, 2),
            "reversible": self.reversible,
        }


@dataclass
class GoalPath:
    """Path taken to achieve (or fail to achieve) goal"""
    path_id: str
    goal: str
    status: GoalStatus
    assumptions: List[AssumptionTrack] = field(default_factory=list)
    decisions: List[DecisionPoint] = field(default_factory=list)
    turn_start: int = 0
    turn_end: Optional[int] = None
    blocking_issues: List[BlockingIssue] = field(default_factory=list)
    recovery_suggestions: List[str] = field(default_factory=list)

    def to_dict(self) -> Dict:
        """Serialize path"""
        return {
            "path_id": self.path_id,
            "goal": self.goal[:100],
            "status": self.status.value,
            "assumptions": len(self.assumptions),
            "decisions": len(self.decisions),
            "blocking_issues": [i.value for i in self.blocking_issues],
        }


class AssumptionValidator:
    """Validate assumptions against evidence"""

    @staticmethod
    def check_assumption_violation(
        assumption: AssumptionTrack,
        current_turn: int,
        new_evidence: str,
    ) -> bool:
        """Check if assumption is violated by new evidence"""
        # Simple heuristic: if evidence contradicts assumption
        assumption_lower = assumption.statement.lower()
        evidence_lower = new_evidence.lower()

        contradictions = ["but", "however", "actually", "not", "don't", "doesn't"]
        if any(c in evidence_lower for c in contradictions):
            # Check if contradiction relates to assumption
            assumption_words = set(assumption_lower.split())
            evidence_words = set(evidence_lower.split())
            overlap = len(assumption_words & evidence_words)

            return overlap > 0 and "not" in evidence_lower

        return False


class GoalIntrospectionEngine:
    """Analyze goal achievement and diagnose failures"""

    def __init__(self):
        self.goal_paths: Dict[str, GoalPath] = {}

    def track_goal(
        self,
        path_id: str,
        goal: str,
        turn_num: int,
    ) -> GoalPath:
        """Start tracking goal"""
        path = GoalPath(
            path_id=path_id,
            goal=goal,
            status=GoalStatus.IN_PROGRESS,
            turn_start=turn_num,
        )
        self.goal_paths[path_id] = path
        return path

    def record_assumption(
        self,
        path_id: str,
        assumption: str,
        confidence: float,
        turn_num: int,
    ):
        """Record assumption made during conversation"""
        if path_id not in self.goal_paths:
            return

        path = self.goal_paths[path_id]
        track = AssumptionTrack(
            assumption_id=f"ass_{len(path.assumptions)}",
            statement=assumption,
            confidence=confidence,
            turn_introduced=turn_num,
        )
        path.assumptions.append(track)

    def record_decision(
        self,
        path_id: str,
        description: str,
        options: List[str],
        chosen: str,
        reasoning: str,
        turn_num: int,
    ):
        """Record decision point"""
        if path_id not in self.goal_paths:
            return

        path = self.goal_paths[path_id]
        decision = DecisionPoint(
            decision_id=f"dec_{len(path.decisions)}",
            turn_num=turn_num,
            description=description,
            options_considered=options,
            option_chosen=chosen,
            reasoning=reasoning,
        )
        path.decisions.append(decision)

    def check_assumption_violation(
        self,
        path_id: str,
        new_evidence: str,
        turn_num: int,
    ) -> List[AssumptionTrack]:
        """Check if any assumptions are violated"""
        if path_id not in self.goal_paths:
            return []

        path = self.goal_paths[path_id]
        violated = []

        for assumption in path.assumptions:
            if AssumptionValidator.check_assumption_violation(
                assumption,
                turn_num,
                new_evidence,
            ):
                assumption.violated = True
                assumption.violation_turn = turn_num
                assumption.violation_evidence = new_evidence
                violated.append(assumption)
                path.blocking_issues.append(BlockingIssue.ASSUMPTION_VIOLATION)

        return violated

    def mark_goal_failed(
        self,
        path_id: str,
        blocking_issue: BlockingIssue,
        final_turn: int,
    ) -> Dict[str, Any]:
        """Mark goal as failed and diagnose"""
        if path_id not in self.goal_paths:
            return {"error": "Path not found"}

        path = self.goal_paths[path_id]
        path.status = GoalStatus.FAILED
        path.turn_end = final_turn

        if blocking_issue not in path.blocking_issues:
            path.blocking_issues.append(blocking_issue)

        # Generate recovery suggestions
        path.recovery_suggestions = self._generate_recovery_suggestions(path)

        return self._generate_diagnosis(path)

    def mark_goal_achieved(
        self,
        path_id: str,
        final_turn: int,
    ) -> Dict[str, Any]:
        """Mark goal as achieved"""
        if path_id not in self.goal_paths:
            return {"error": "Path not found"}

        path = self.goal_paths[path_id]
        path.status = GoalStatus.ACHIEVED
        path.turn_end = final_turn

        return {
            "goal": path.goal,
            "status": GoalStatus.ACHIEVED.value,
            "turns_taken": final_turn - path.turn_start,
            "assumptions": len(path.assumptions),
            "decisions": len(path.decisions),
        }

    def _generate_recovery_suggestions(self, path: GoalPath) -> List[str]:
        """Generate suggestions to recover from failure"""
        suggestions = []

        # Check for violated assumptions
        violated = [a for a in path.assumptions if a.violated]
        if violated:
            suggestions.append(f"Revise assumptions: {len(violated)} were violated")

        # Check for risky decisions
        risky = [d for d in path.decisions if d.confidence < 0.6]
        if risky:
            suggestions.append(f"Reconsider {len(risky)} low-confidence decisions")

        # Check for missing information
        if BlockingIssue.MISSING_INFORMATION in path.blocking_issues:
            suggestions.append("Gather more information before proceeding")

        # Check for user disagreement
        if BlockingIssue.USER_DISAGREEMENT in path.blocking_issues:
            suggestions.append("Align with user on approach or goals")

        return suggestions[:3]  # Return top 3

    def _generate_diagnosis(self, path: GoalPath) -> Dict[str, Any]:
        """Generate diagnostic report"""
        return {
            "goal": path.goal,
            "status": path.status.value,
            "duration_turns": path.turn_end - path.turn_start if path.turn_end else 0,
            "blocking_issues": [i.value for i in path.blocking_issues],
            "violated_assumptions": len([a for a in path.assumptions if a.violated]),
            "low_confidence_decisions": len([d for d in path.decisions if d.confidence < 0.6]),
            "recovery_suggestions": path.recovery_suggestions,
        }

    def get_goal_introspection(self, path_id: str) -> Optional[Dict]:
        """Get full introspection report"""
        path = self.goal_paths.get(path_id)
        if not path:
            return None

        return {
            "goal": path.goal,
            "status": path.status.value,
            "path": path.to_dict(),
            "assumptions": [a.to_dict() for a in path.assumptions],
            "decisions": [d.to_dict() for d in path.decisions],
            "issues": [i.value for i in path.blocking_issues],
            "suggestions": path.recovery_suggestions,
        }


class IntrospectionManager:
    """Manage introspection across conversations"""

    def __init__(self):
        self.engines: Dict[str, GoalIntrospectionEngine] = {}

    def create_engine(self, engine_id: str) -> GoalIntrospectionEngine:
        """Create introspection engine"""
        engine = GoalIntrospectionEngine()
        self.engines[engine_id] = engine
        return engine

    def get_engine(self, engine_id: str) -> Optional[GoalIntrospectionEngine]:
        """Get engine"""
        return self.engines.get(engine_id)


# Global manager
introspection_manager = IntrospectionManager()


# MCP Tools

def create_introspection_engine(engine_id: str) -> dict:
    """Create introspection engine"""
    engine = introspection_manager.create_engine(engine_id)
    return {"engine_id": engine_id, "created": True}


def track_goal(engine_id: str, path_id: str, goal: str, turn_num: int) -> dict:
    """Start tracking goal"""
    engine = introspection_manager.get_engine(engine_id)
    if not engine:
        return {"error": "Engine not found"}

    path = engine.track_goal(path_id, goal, turn_num)
    return path.to_dict()


def record_assumption(
    engine_id: str,
    path_id: str,
    assumption: str,
    confidence: float,
    turn_num: int,
) -> dict:
    """Record assumption"""
    engine = introspection_manager.get_engine(engine_id)
    if not engine:
        return {"error": "Engine not found"}

    engine.record_assumption(path_id, assumption, confidence, turn_num)
    return {"recorded": True}


def check_assumptions(engine_id: str, path_id: str, evidence: str, turn_num: int) -> dict:
    """Check assumption violations"""
    engine = introspection_manager.get_engine(engine_id)
    if not engine:
        return {"error": "Engine not found"}

    violated = engine.check_assumption_violation(path_id, evidence, turn_num)
    return {
        "violations": len(violated),
        "details": [a.to_dict() for a in violated],
    }


def mark_goal_failed(engine_id: str, path_id: str, blocking_issue: str, turn_num: int) -> dict:
    """Mark goal as failed"""
    engine = introspection_manager.get_engine(engine_id)
    if not engine:
        return {"error": "Engine not found"}

    try:
        issue = BlockingIssue(blocking_issue)
        return engine.mark_goal_failed(path_id, issue, turn_num)
    except ValueError:
        return {"error": f"Invalid blocking issue: {blocking_issue}"}


def get_goal_introspection(engine_id: str, path_id: str) -> dict:
    """Get goal introspection report"""
    engine = introspection_manager.get_engine(engine_id)
    if not engine:
        return {"error": "Engine not found"}

    report = engine.get_goal_introspection(path_id)
    return report or {"error": "Path not found"}


if __name__ == "__main__":
    engine = GoalIntrospectionEngine()

    path = engine.track_goal("path_1", "Understand machine learning", 1)
    print(f"Path: {json.dumps(path.to_dict(), indent=2)}")

    engine.record_assumption("path_1", "User has math background", 0.6, 2)
    engine.record_decision("path_1", "Explain with math", ["math", "intuitive"], "math", "User seemed ready", 2)

    violated = engine.check_assumption_violation("path_1", "Actually I don't know calculus", 5)
    print(f"Violated: {len(violated)}")

    diagnosis = engine.mark_goal_failed("path_1", BlockingIssue.ASSUMPTION_VIOLATION, 10)
    print(f"Diagnosis: {json.dumps(diagnosis, indent=2)}")
