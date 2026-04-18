"""Skill development tracker: track conversation skills, identify growth areas, recommend practice"""

import json
from pathlib import Path
from datetime import datetime
from typing import Optional, List, Dict, Any
from dataclasses import dataclass, field
from enum import Enum

SKILL_DIR = Path.home() / ".memory-mcp" / "skill-development"
SKILL_DIR.mkdir(exist_ok=True, parents=True)


class ConversationSkill(Enum):
    """Types of conversation skills"""
    CLARITY = "clarity"  # Communicating clearly
    EMPATHY = "empathy"  # Understanding user perspective
    ADAPTATION = "adaptation"  # Adapting to user style
    DEPTH = "depth"  # Going deep on topics
    QUESTIONING = "questioning"  # Asking good questions
    REPAIR = "repair"  # Fixing misunderstandings
    PACING = "pacing"  # Managing conversation pace
    BREVITY = "brevity"  # Conciseness
    EVIDENCE = "evidence"  # Supporting claims
    SUMMARY = "summary"  # Summarizing effectively


class SkillLevel(Enum):
    """Proficiency level in skill"""
    NOVICE = "novice"  # <30% success
    DEVELOPING = "developing"  # 30-60% success
    PROFICIENT = "proficient"  # 60-80% success
    EXPERT = "expert"  # >80% success


@dataclass
class SkillInstance:
    """Instance of using a skill"""
    instance_id: str
    skill: ConversationSkill
    turn_num: int
    execution: str  # How it was executed
    outcome: str  # What happened
    success: bool
    feedback: str = ""

    def to_dict(self) -> Dict:
        """Serialize instance"""
        return {
            "instance_id": self.instance_id,
            "skill": self.skill.value,
            "success": self.success,
        }


@dataclass
class SkillProfile:
    """Agent's skill profile"""
    skill_name: ConversationSkill
    instances: List[SkillInstance] = field(default_factory=list)
    success_rate: float = 0.5
    proficiency_level: SkillLevel = SkillLevel.DEVELOPING
    last_practiced: Optional[str] = None
    growth_trajectory: List[float] = field(default_factory=list)
    recommendations: List[str] = field(default_factory=list)

    def to_dict(self) -> Dict:
        """Serialize profile"""
        return {
            "skill": self.skill_name.value,
            "level": self.proficiency_level.value,
            "success_rate": round(self.success_rate, 2),
            "instances": len(self.instances),
        }


@dataclass
class SkillDevelopmentPlan:
    """Plan for deliberate skill practice"""
    plan_id: str
    focus_skill: ConversationSkill
    current_level: SkillLevel
    target_level: SkillLevel
    practice_areas: List[str]  # What to practice
    difficulty_progression: List[str]  # Easy to hard
    success_criteria: List[str]  # How to measure success
    estimated_practice_sessions: int

    def to_dict(self) -> Dict:
        """Serialize plan"""
        return {
            "plan_id": self.plan_id,
            "focus_skill": self.focus_skill.value,
            "current_level": self.current_level.value,
            "target_level": self.target_level.value,
        }


class SkillTracker:
    """Track and develop conversation skills"""

    def __init__(self):
        self.skill_profiles: Dict[ConversationSkill, SkillProfile] = {}
        self.skill_history: List[SkillInstance] = []
        self.development_plans: Dict[str, SkillDevelopmentPlan] = {}

        # Initialize all skills
        for skill in ConversationSkill:
            self.skill_profiles[skill] = SkillProfile(skill_name=skill)

    def record_skill_use(
        self,
        skill: ConversationSkill,
        turn_num: int,
        execution: str,
        outcome: str,
        success: bool,
    ) -> SkillInstance:
        """Record instance of using a skill"""
        instance = SkillInstance(
            instance_id=f"si_{len(self.skill_history)}",
            skill=skill,
            turn_num=turn_num,
            execution=execution,
            outcome=outcome,
            success=success,
        )

        self.skill_history.append(instance)
        profile = self.skill_profiles[skill]
        profile.instances.append(instance)
        profile.last_practiced = datetime.now().isoformat()

        # Update success rate
        successes = sum(1 for i in profile.instances if i.success)
        profile.success_rate = successes / len(profile.instances) if profile.instances else 0.5

        # Update proficiency level
        if profile.success_rate > 0.8:
            profile.proficiency_level = SkillLevel.EXPERT
        elif profile.success_rate > 0.6:
            profile.proficiency_level = SkillLevel.PROFICIENT
        elif profile.success_rate > 0.3:
            profile.proficiency_level = SkillLevel.DEVELOPING
        else:
            profile.proficiency_level = SkillLevel.NOVICE

        profile.growth_trajectory.append(profile.success_rate)

        return instance

    def get_weakest_skills(self, top_n: int = 3) -> List[SkillProfile]:
        """Identify weakest skills for improvement"""
        skills = list(self.skill_profiles.values())
        skills.sort(key=lambda s: s.success_rate)
        return skills[:top_n]

    def create_development_plan(
        self,
        focus_skill: ConversationSkill,
        target_level: SkillLevel = SkillLevel.PROFICIENT,
    ) -> SkillDevelopmentPlan:
        """Create deliberate practice plan for skill"""
        current_level = self.skill_profiles[focus_skill].proficiency_level

        # Define practice areas
        practice_areas_map = {
            ConversationSkill.CLARITY: [
                "Use simpler sentences",
                "Avoid jargon",
                "State main point first",
            ],
            ConversationSkill.EMPATHY: [
                "Acknowledge user concerns",
                "Reflect feelings",
                "Validate perspective",
            ],
            ConversationSkill.ADAPTATION: [
                "Match user pace",
                "Adjust formality",
                "Use preferred style",
            ],
            ConversationSkill.DEPTH: [
                "Ask follow-up questions",
                "Explore subtopics",
                "Build on previous points",
            ],
            ConversationSkill.QUESTIONING: [
                "Ask open-ended questions",
                "Avoid leading questions",
                "Ask one question at a time",
            ],
            ConversationSkill.REPAIR: [
                "Detect misunderstandings early",
                "Clarify proactively",
                "Validate corrections",
            ],
        }

        practice_areas = practice_areas_map.get(focus_skill, ["Practice regularly"])

        plan = SkillDevelopmentPlan(
            plan_id=f"sdp_{len(self.development_plans)}",
            focus_skill=focus_skill,
            current_level=current_level,
            target_level=target_level,
            practice_areas=practice_areas,
            difficulty_progression=[
                "Simple scenarios",
                "Mixed scenarios",
                "Challenging scenarios",
            ],
            success_criteria=[
                f"Reach {target_level.value} proficiency",
                "Consistent 70%+ success rate",
                "Positive user feedback",
            ],
            estimated_practice_sessions=5 + (len(self.skill_history) // 10),
        )

        self.development_plans[plan.plan_id] = plan
        return plan

    def get_skill_report(self) -> Dict[str, Any]:
        """Get comprehensive skill report"""
        profiles = list(self.skill_profiles.values())

        by_level = {}
        for level in SkillLevel:
            by_level[level.value] = len([p for p in profiles if p.proficiency_level == level])

        avg_success = sum(p.success_rate for p in profiles) / len(profiles) if profiles else 0

        weakest = self.get_weakest_skills(3)

        return {
            "total_skills": len(profiles),
            "skills_by_level": by_level,
            "average_success_rate": round(avg_success, 2),
            "skill_instances": len(self.skill_history),
            "weakest_skills": [p.skill_name.value for p in weakest],
        }

    def get_growth_trajectory(self) -> Dict[str, List[float]]:
        """Get growth trajectory for all skills"""
        trajectories = {}
        for skill, profile in self.skill_profiles.items():
            trajectories[skill.value] = profile.growth_trajectory
        return trajectories


class SkillDevelopmentManager:
    """Manage skill development across conversations"""

    def __init__(self):
        self.trackers: Dict[str, SkillTracker] = {}

    def create_tracker(self, tracker_id: str) -> SkillTracker:
        """Create skill tracker"""
        tracker = SkillTracker()
        self.trackers[tracker_id] = tracker
        return tracker

    def get_tracker(self, tracker_id: str) -> Optional[SkillTracker]:
        """Get tracker"""
        return self.trackers.get(tracker_id)


# Global manager
skill_manager = SkillDevelopmentManager()


# MCP Tools

def create_skill_tracker(tracker_id: str) -> dict:
    """Create skill tracker"""
    tracker = skill_manager.create_tracker(tracker_id)
    return {"tracker_id": tracker_id, "created": True}


def record_skill_use(
    tracker_id: str,
    skill: str,
    turn_num: int,
    execution: str,
    outcome: str,
    success: bool,
) -> dict:
    """Record skill use"""
    tracker = skill_manager.get_tracker(tracker_id)
    if not tracker:
        return {"error": "Tracker not found"}

    try:
        skill_enum = ConversationSkill(skill)
        instance = tracker.record_skill_use(skill_enum, turn_num, execution, outcome, success)
        return instance.to_dict()
    except ValueError:
        return {"error": f"Invalid skill: {skill}"}


def get_weakest_skills(tracker_id: str, top_n: int = 3) -> dict:
    """Get weakest skills"""
    tracker = skill_manager.get_tracker(tracker_id)
    if not tracker:
        return {"error": "Tracker not found"}

    weakest = tracker.get_weakest_skills(top_n)
    return {
        "weakest_skills": [p.to_dict() for p in weakest],
    }


def create_development_plan(tracker_id: str, skill: str, target_level: str = "proficient") -> dict:
    """Create development plan"""
    tracker = skill_manager.get_tracker(tracker_id)
    if not tracker:
        return {"error": "Tracker not found"}

    try:
        skill_enum = ConversationSkill(skill)
        level_enum = SkillLevel(target_level)
        plan = tracker.create_development_plan(skill_enum, level_enum)
        return plan.to_dict()
    except ValueError as e:
        return {"error": str(e)}


def get_skill_report(tracker_id: str) -> dict:
    """Get skill report"""
    tracker = skill_manager.get_tracker(tracker_id)
    if not tracker:
        return {"error": "Tracker not found"}

    return tracker.get_skill_report()


if __name__ == "__main__":
    tracker = SkillTracker()

    # Record skill uses
    tracker.record_skill_use(
        ConversationSkill.CLARITY,
        1,
        "Used simple language",
        "User understood",
        True,
    )

    tracker.record_skill_use(
        ConversationSkill.EMPATHY,
        2,
        "Acknowledged concern",
        "User felt heard",
        True,
    )

    # Get report
    report = tracker.get_skill_report()
    print(f"Report: {json.dumps(report, indent=2)}")

    # Create plan
    plan = tracker.create_development_plan(ConversationSkill.DEPTH)
    print(f"Plan: {plan.focus_skill.value}")
