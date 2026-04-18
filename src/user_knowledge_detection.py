"""User knowledge level detection and adaptation"""

import json
from pathlib import Path
from datetime import datetime
from typing import Optional, List, Dict, Any
from dataclasses import dataclass, field
from enum import Enum

KNOWLEDGE_DIR = Path.home() / ".memory-mcp" / "user-knowledge"
KNOWLEDGE_DIR.mkdir(exist_ok=True, parents=True)


class KnowledgeLevel(Enum):
    """User expertise levels"""
    NOVICE = 1
    BEGINNER = 2
    INTERMEDIATE = 3
    ADVANCED = 4
    EXPERT = 5


@dataclass
class KnowledgeProfile:
    """User's knowledge profile"""
    user_id: str
    current_level: KnowledgeLevel
    domain: str
    confidence: float = 0.6
    explanation_depth: float = 0.5  # 0=simple, 1=detailed
    vocabulary_level: float = 0.5  # 0=basic, 1=technical
    turn_count: int = 0
    created_at: str = ""

    def __post_init__(self):
        if not self.created_at:
            self.created_at = datetime.now().isoformat()

    def to_dict(self) -> Dict:
        return {
            "user_id": self.user_id,
            "level": self.current_level.name,
            "domain": self.domain,
            "confidence": round(self.confidence, 2),
        }


class KnowledgeDetector:
    """Detect user knowledge level"""

    NOVICE_INDICATORS = ["what is", "explain", "basics", "beginner", "how do"]
    EXPERT_INDICATORS = ["optimize", "architecture", "framework", "implement", "design"]

    @staticmethod
    def assess_knowledge_level(
        user_inputs: List[str],
    ) -> KnowledgeLevel:
        """Assess user knowledge level from interactions"""
        if not user_inputs:
            return KnowledgeLevel.BEGINNER

        expert_score = 0
        novice_score = 0

        for user_input in user_inputs:
            text_lower = user_input.lower()
            expert_score += sum(1 for ind in KnowledgeDetector.EXPERT_INDICATORS if ind in text_lower)
            novice_score += sum(1 for ind in KnowledgeDetector.NOVICE_INDICATORS if ind in text_lower)

        if expert_score > novice_score:
            return KnowledgeLevel.ADVANCED if expert_score > 3 else KnowledgeLevel.INTERMEDIATE
        elif novice_score > expert_score:
            return KnowledgeLevel.NOVICE if novice_score > 3 else KnowledgeLevel.BEGINNER

        return KnowledgeLevel.INTERMEDIATE


class AdaptationEngine:
    """Adapt explanations based on knowledge level"""

    @staticmethod
    def adapt_explanation(
        explanation: str,
        target_level: KnowledgeLevel,
    ) -> str:
        """Adapt explanation for knowledge level"""
        if target_level == KnowledgeLevel.NOVICE:
            return f"Simply put: {explanation[:50]}..."

        elif target_level == KnowledgeLevel.BEGINNER:
            return f"Here's the basics: {explanation}"

        elif target_level == KnowledgeLevel.INTERMEDIATE:
            return f"Key points: {explanation}"

        elif target_level == KnowledgeLevel.ADVANCED:
            return f"Technical details: {explanation}"

        else:  # EXPERT
            return f"Advanced concepts: {explanation}"

    @staticmethod
    def get_vocabulary_level(
        target_level: KnowledgeLevel,
    ) -> float:
        """Get vocabulary level for explanation"""
        return (target_level.value - 1) / 4.0


class KnowledgeManager:
    """Manage user knowledge profiles"""

    def __init__(self):
        self.profiles: Dict[str, KnowledgeProfile] = {}

    def create_profile(
        self,
        user_id: str,
        domain: str,
    ) -> KnowledgeProfile:
        """Create knowledge profile"""
        profile = KnowledgeProfile(
            user_id=user_id,
            current_level=KnowledgeLevel.BEGINNER,
            domain=domain,
        )
        self.profiles[user_id] = profile
        return profile

    def update_knowledge_level(
        self,
        user_id: str,
        user_inputs: List[str],
    ) -> Optional[KnowledgeProfile]:
        """Update knowledge level based on interactions"""
        if user_id not in self.profiles:
            return None

        profile = self.profiles[user_id]
        level = KnowledgeDetector.assess_knowledge_level(user_inputs)
        profile.current_level = level
        profile.turn_count += len(user_inputs)
        profile.confidence = min(1.0, profile.confidence + 0.1)

        return profile

    def get_adapted_response(
        self,
        user_id: str,
        response: str,
    ) -> str:
        """Get response adapted to user knowledge level"""
        if user_id not in self.profiles:
            return response

        profile = self.profiles[user_id]
        return AdaptationEngine.adapt_explanation(response, profile.current_level)


# Global manager
knowledge_manager = KnowledgeManager()


def create_knowledge_profile(user_id: str, domain: str) -> dict:
    """Create knowledge profile"""
    profile = knowledge_manager.create_profile(user_id, domain)
    return profile.to_dict()


def update_knowledge_level(user_id: str, user_inputs: list) -> dict:
    """Update knowledge level"""
    profile = knowledge_manager.update_knowledge_level(user_id, user_inputs)
    return profile.to_dict() if profile else {"error": "Profile not found"}


def get_adapted_response(user_id: str, response: str) -> dict:
    """Get adapted response"""
    adapted = knowledge_manager.get_adapted_response(user_id, response)
    return {"adapted_response": adapted}
