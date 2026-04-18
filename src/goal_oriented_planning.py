"""Goal-oriented conversation planning and execution"""

import json
from pathlib import Path
from datetime import datetime
from typing import Optional, List, Dict, Any
from dataclasses import dataclass, field
from enum import Enum

GOAL_DIR = Path.home() / ".memory-mcp" / "goal-planning"
GOAL_DIR.mkdir(exist_ok=True, parents=True)


class GoalType(Enum):
    """Types of conversation goals"""
    INFORMATION_GATHERING = "information_gathering"
    PROBLEM_SOLVING = "problem_solving"
    DECISION_MAKING = "decision_making"
    LEARNING = "learning"
    NEGOTIATION = "negotiation"


class ProgressStatus(Enum):
    """Progress toward goal"""
    NOT_STARTED = "not_started"
    IN_PROGRESS = "in_progress"
    PARTIALLY_COMPLETE = "partially_complete"
    COMPLETE = "complete"
    ABANDONED = "abandoned"


@dataclass
class ConversationGoal:
    """Goal for conversation"""
    goal_id: str
    title: str
    goal_type: GoalType
    description: str
    success_criteria: List[str]
    priority: int = 1
    estimated_turns: int = 5
    current_progress: float = 0.0
    status: ProgressStatus = ProgressStatus.NOT_STARTED

    def to_dict(self) -> Dict:
        return {
            "goal_id": self.goal_id,
            "title": self.title,
            "type": self.goal_type.value,
            "priority": self.priority,
            "progress": round(self.current_progress, 2),
            "status": self.status.value,
        }


@dataclass
class ConversationPlan:
    """Plan for achieving conversation goals"""
    plan_id: str
    goals: List[ConversationGoal] = field(default_factory=list)
    current_step: int = 0
    total_steps: int = 0
    completion_percentage: float = 0.0
    turns_used: int = 0
    created_at: str = ""

    def __post_init__(self):
        if not self.created_at:
            self.created_at = datetime.now().isoformat()

    def to_dict(self) -> Dict:
        return {
            "plan_id": self.plan_id,
            "goals": len(self.goals),
            "completion": round(self.completion_percentage, 2),
            "turns_used": self.turns_used,
        }


class PlanningEngine:
    """Plan conversations toward goals"""

    def __init__(self):
        self.plans: Dict[str, ConversationPlan] = {}
        self.turn_count = 0

    def create_plan(
        self,
        plan_id: str,
        goals: List[ConversationGoal],
    ) -> ConversationPlan:
        """Create conversation plan"""
        plan = ConversationPlan(plan_id=plan_id, goals=goals)
        plan.total_steps = sum(g.estimated_turns for g in goals)
        self.plans[plan_id] = plan
        return plan

    def progress_toward_goal(
        self,
        plan_id: str,
        goal_id: str,
        progress_increment: float,
    ) -> Optional[ConversationGoal]:
        """Update progress on goal"""
        if plan_id not in self.plans:
            return None

        plan = self.plans[plan_id]
        goal = next((g for g in plan.goals if g.goal_id == goal_id), None)

        if goal:
            goal.current_progress = min(1.0, goal.current_progress + progress_increment)
            if goal.current_progress >= 1.0:
                goal.status = ProgressStatus.COMPLETE
            else:
                goal.status = ProgressStatus.IN_PROGRESS

            # Update plan progress
            avg_progress = sum(g.current_progress for g in plan.goals) / len(plan.goals)
            plan.completion_percentage = avg_progress
            plan.turns_used += 1

        return goal

    def get_next_action(
        self,
        plan_id: str,
    ) -> Optional[str]:
        """Get recommended next action"""
        if plan_id not in self.plans:
            return None

        plan = self.plans[plan_id]

        # Find first incomplete goal
        incomplete = next(
            (g for g in plan.goals if g.status != ProgressStatus.COMPLETE),
            None,
        )

        if incomplete:
            return f"Focus on: {incomplete.title}"

        return "All goals achieved!"

    def get_plan_status(self, plan_id: str) -> Optional[Dict]:
        """Get plan status"""
        if plan_id not in self.plans:
            return None

        plan = self.plans[plan_id]
        completed_goals = sum(1 for g in plan.goals if g.status == ProgressStatus.COMPLETE)

        return {
            "plan_id": plan_id,
            "goals_completed": completed_goals,
            "total_goals": len(plan.goals),
            "completion_percentage": round(plan.completion_percentage * 100, 1),
            "turns_used": plan.turns_used,
            "efficiency": (
                plan.completion_percentage / max(1, plan.turns_used / plan.total_steps)
                if plan.total_steps > 0 else 0.0
            ),
        }


# Global engine
planning_engine = PlanningEngine()


def create_conversation_plan(plan_id: str, goals: list) -> dict:
    """Create conversation plan"""
    goal_objects = [
        ConversationGoal(
            goal_id=g.get("goal_id", f"g_{i}"),
            title=g.get("title", ""),
            goal_type=GoalType(g.get("type", "information_gathering")),
            description=g.get("description", ""),
            success_criteria=g.get("criteria", []),
            priority=g.get("priority", 1),
        )
        for i, g in enumerate(goals)
    ]

    plan = planning_engine.create_plan(plan_id, goal_objects)
    return plan.to_dict()


def progress_toward_goal(
    plan_id: str,
    goal_id: str,
    progress: float,
) -> dict:
    """Update goal progress"""
    goal = planning_engine.progress_toward_goal(plan_id, goal_id, progress)
    return goal.to_dict() if goal else {"error": "Goal not found"}


def get_next_action(plan_id: str) -> dict:
    """Get next action"""
    action = planning_engine.get_next_action(plan_id)
    return {"action": action} if action else {"error": "Plan not found"}


def get_plan_status(plan_id: str) -> dict:
    """Get plan status"""
    status = planning_engine.get_plan_status(plan_id)
    return status or {"error": "Plan not found"}
