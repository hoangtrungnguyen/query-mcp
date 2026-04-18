"""Conversation personalization through user profiling and adaptive response generation"""

import json
from pathlib import Path
from datetime import datetime
from typing import Optional, List, Dict, Any
from dataclasses import dataclass, field
from enum import Enum
from collections import defaultdict

PERSONALIZATION_DIR = Path.home() / ".memory-mcp" / "personalization"
PERSONALIZATION_DIR.mkdir(exist_ok=True, parents=True)


class CommunicationStyle(Enum):
    """User communication preferences"""
    FORMAL = "formal"  # Formal, professional
    CASUAL = "casual"  # Relaxed, conversational
    TECHNICAL = "technical"  # Detailed, jargon-heavy
    SIMPLE = "simple"  # Plain language
    BALANCED = "balanced"  # Mix of styles


class PacePreference(Enum):
    """Conversation pace"""
    SLOW = "slow"  # Detailed, step-by-step
    MODERATE = "moderate"  # Balanced
    FAST = "fast"  # Quick, concise


class DetailLevel(Enum):
    """Desired level of detail"""
    MINIMAL = "minimal"  # Bare essentials
    BRIEF = "brief"  # Concise but complete
    STANDARD = "standard"  # Normal detail
    COMPREHENSIVE = "comprehensive"  # Extensive detail


@dataclass
class UserPreferences:
    """Learned user preferences"""
    user_id: str
    communication_style: CommunicationStyle = CommunicationStyle.BALANCED
    pace: PacePreference = PacePreference.MODERATE
    detail_level: DetailLevel = DetailLevel.STANDARD
    topics_of_interest: List[str] = field(default_factory=list)
    disliked_topics: List[str] = field(default_factory=list)
    preferred_tools: List[str] = field(default_factory=list)
    language: str = "en"
    timezone: str = "UTC"
    follow_up_preference: bool = True
    examples_preferred: bool = True
    citations_preferred: bool = True
    confidence: float = 0.5  # How confident are we in these preferences?

    def to_dict(self) -> Dict:
        """Serialize preferences"""
        return {
            "user_id": self.user_id,
            "communication_style": self.communication_style.value,
            "pace": self.pace.value,
            "detail_level": self.detail_level.value,
            "topics_of_interest": self.topics_of_interest,
            "disliked_topics": self.disliked_topics,
            "preferred_tools": self.preferred_tools,
            "language": self.language,
            "timezone": self.timezone,
            "follow_up_preference": self.follow_up_preference,
            "examples_preferred": self.examples_preferred,
            "citations_preferred": self.citations_preferred,
            "confidence": self.confidence,
        }


@dataclass
class UserProfile:
    """Complete user profile for personalization"""
    user_id: str
    preferences: UserPreferences
    interaction_history: List[str] = field(default_factory=list)
    conversation_count: int = 0
    total_tokens_used: int = 0
    creation_date: str = ""
    last_interaction: str = ""
    metadata: Dict[str, Any] = field(default_factory=dict)

    def __post_init__(self):
        if not self.creation_date:
            self.creation_date = datetime.now().isoformat()

    def to_dict(self) -> Dict:
        """Serialize profile"""
        return {
            "user_id": self.user_id,
            "preferences": self.preferences.to_dict(),
            "interaction_history": self.interaction_history[-50:],  # Last 50
            "conversation_count": self.conversation_count,
            "total_tokens_used": self.total_tokens_used,
            "creation_date": self.creation_date,
            "last_interaction": self.last_interaction,
            "metadata": self.metadata,
        }


class UserProfileLearner:
    """Learn user preferences from interaction patterns"""

    @staticmethod
    def learn_communication_style(interaction_history: List[Dict]) -> CommunicationStyle:
        """Infer communication style from messages"""
        if not interaction_history:
            return CommunicationStyle.BALANCED

        # Simple heuristics
        avg_length = sum(len(m.get("content", "").split()) for m in interaction_history) / len(
            interaction_history
        )

        formal_markers = ["formally", "regards", "hereby", "respectfully"]
        technical_markers = ["algorithm", "API", "parameter", "implementation"]
        casual_markers = ["lol", "btw", "gonna", "awesome"]

        content = " ".join(m.get("content", "") for m in interaction_history).lower()

        if any(m in content for m in formal_markers):
            return CommunicationStyle.FORMAL
        elif any(m in content for m in technical_markers):
            return CommunicationStyle.TECHNICAL
        elif any(m in content for m in casual_markers):
            return CommunicationStyle.CASUAL
        elif avg_length < 20:
            return CommunicationStyle.SIMPLE

        return CommunicationStyle.BALANCED

    @staticmethod
    def learn_pace_preference(interaction_history: List[Dict]) -> PacePreference:
        """Infer conversation pace preference"""
        if not interaction_history:
            return PacePreference.MODERATE

        # Check response lengths
        response_lengths = [
            len(m.get("content", "").split())
            for m in interaction_history
            if m.get("speaker_id") == "agent"
        ]

        if not response_lengths:
            return PacePreference.MODERATE

        avg_response_length = sum(response_lengths) / len(response_lengths)

        if avg_response_length < 20:
            return PacePreference.FAST
        elif avg_response_length > 100:
            return PacePreference.SLOW

        return PacePreference.MODERATE

    @staticmethod
    def learn_detail_level(interaction_history: List[Dict]) -> DetailLevel:
        """Infer desired detail level"""
        if not interaction_history:
            return DetailLevel.STANDARD

        # Check for follow-up questions requesting more detail
        user_messages = [m for m in interaction_history if m.get("speaker_id") == "user"]
        detail_requests = sum(
            1
            for m in user_messages
            if any(
                word in m.get("content", "").lower()
                for word in ["more", "explain", "detail", "why", "how"]
            )
        )

        if detail_requests > len(user_messages) * 0.5:
            return DetailLevel.COMPREHENSIVE

        return DetailLevel.STANDARD

    @staticmethod
    def learn_topics(interaction_history: List[Dict]) -> Tuple[List[str], List[str]]:
        """Extract topics of interest and disliked"""
        interested = []
        disliked = []

        for msg in interaction_history:
            content = msg.get("content", "").lower()
            # Simple keyword matching
            if "interested" in content or "like" in content or "love" in content:
                # Extract keywords after
                interested.extend(content.split()[: 5])
            elif "dislike" in content or "hate" in content or "avoid" in content:
                disliked.extend(content.split()[: 5])

        return interested, disliked


class PersonalizationEngine:
    """Engine for personalizing conversations"""

    def __init__(self):
        self.user_profiles: Dict[str, UserProfile] = {}
        self.learner = UserProfileLearner()

    def create_user_profile(self, user_id: str) -> UserProfile:
        """Create new user profile"""
        preferences = UserPreferences(user_id=user_id)
        profile = UserProfile(
            user_id=user_id,
            preferences=preferences,
        )
        self.user_profiles[user_id] = profile
        return profile

    def get_or_create_profile(self, user_id: str) -> UserProfile:
        """Get existing profile or create new"""
        if user_id not in self.user_profiles:
            return self.create_user_profile(user_id)
        return self.user_profiles[user_id]

    def update_profile_from_history(
        self,
        user_id: str,
        interaction_history: List[Dict],
    ) -> UserProfile:
        """Update profile based on interaction history"""
        profile = self.get_or_create_profile(user_id)

        # Learn preferences
        profile.preferences.communication_style = self.learner.learn_communication_style(
            interaction_history
        )
        profile.preferences.pace = self.learner.learn_pace_preference(interaction_history)
        profile.preferences.detail_level = self.learner.learn_detail_level(
            interaction_history
        )

        topics_interested, topics_disliked = self.learner.learn_topics(interaction_history)
        profile.preferences.topics_of_interest = topics_interested
        profile.preferences.disliked_topics = topics_disliked

        profile.interaction_history = [m.get("content", "") for m in interaction_history[-50:]]
        profile.conversation_count += 1
        profile.last_interaction = datetime.now().isoformat()

        # Increase confidence with more interactions
        profile.preferences.confidence = min(0.95, 0.5 + profile.conversation_count * 0.05)

        return profile

    def generate_personalized_prompt(
        self,
        user_id: str,
        base_prompt: str,
        context: Optional[Dict] = None,
    ) -> str:
        """Generate personalized version of prompt"""
        profile = self.get_or_create_profile(user_id)
        prefs = profile.preferences

        # Build personalization directives
        directives = []

        # Style directive
        if prefs.communication_style == CommunicationStyle.FORMAL:
            directives.append("Use formal, professional language.")
        elif prefs.communication_style == CommunicationStyle.CASUAL:
            directives.append("Use casual, conversational tone.")
        elif prefs.communication_style == CommunicationStyle.TECHNICAL:
            directives.append("Use technical language and jargon where appropriate.")
        elif prefs.communication_style == CommunicationStyle.SIMPLE:
            directives.append("Use plain, simple language.")

        # Pace directive
        if prefs.pace == PacePreference.FAST:
            directives.append("Keep responses concise and to the point.")
        elif prefs.pace == PacePreference.SLOW:
            directives.append("Provide detailed, step-by-step explanations.")

        # Detail directive
        if prefs.detail_level == DetailLevel.MINIMAL:
            directives.append("Provide only essential information.")
        elif prefs.detail_level == DetailLevel.COMPREHENSIVE:
            directives.append("Provide comprehensive details and examples.")

        # Examples
        if prefs.examples_preferred:
            directives.append("Include concrete examples.")

        # Citations
        if prefs.citations_preferred:
            directives.append("Include citations and sources where relevant.")

        # Combine
        personalized = base_prompt
        if directives:
            personalized += f"\n\nPersonalization: {' '.join(directives)}"

        return personalized

    def adapt_response(
        self,
        user_id: str,
        response: str,
    ) -> str:
        """Adapt response to user preferences"""
        profile = self.get_or_create_profile(user_id)
        prefs = profile.preferences

        # Apply post-processing based on preferences
        words = response.split()

        # Trim for fast pace
        if prefs.pace == PacePreference.FAST and len(words) > 200:
            response = " ".join(words[:150]) + "..."

        return response

    def get_user_context(self, user_id: str) -> Dict[str, Any]:
        """Get personalization context for user"""
        profile = self.get_or_create_profile(user_id)

        return {
            "user_id": user_id,
            "preferences": profile.preferences.to_dict(),
            "interaction_count": profile.conversation_count,
            "preferred_style": profile.preferences.communication_style.value,
            "preferred_pace": profile.preferences.pace.value,
            "detail_level": profile.preferences.detail_level.value,
        }

    def save_profile(self, user_id: str) -> str:
        """Save user profile to disk"""
        if user_id not in self.user_profiles:
            return ""

        profile = self.user_profiles[user_id]
        filepath = PERSONALIZATION_DIR / f"{user_id}_profile.json"

        with open(filepath, "w") as f:
            json.dump(profile.to_dict(), f, indent=2)

        return str(filepath)


# Global engine
personalization_engine = PersonalizationEngine()


# MCP Tools (add to memory_server.py)

def create_user_profile(user_id: str) -> dict:
    """Create personalization profile for user"""
    profile = personalization_engine.create_user_profile(user_id)
    return {"user_id": user_id, "created": True}


def update_user_preferences(
    user_id: str,
    interaction_history: list,
) -> dict:
    """Update preferences from interaction history"""
    profile = personalization_engine.update_profile_from_history(user_id, interaction_history)
    return profile.preferences.to_dict()


def get_personalized_prompt(
    user_id: str,
    base_prompt: str,
) -> dict:
    """Generate personalized prompt for user"""
    personalized = personalization_engine.generate_personalized_prompt(user_id, base_prompt)
    return {"original": base_prompt, "personalized": personalized}


def adapt_response_for_user(user_id: str, response: str) -> dict:
    """Adapt response to user preferences"""
    adapted = personalization_engine.adapt_response(user_id, response)
    return {"original_length": len(response.split()), "adapted_length": len(adapted.split())}


def get_user_personalization_context(user_id: str) -> dict:
    """Get personalization context for user"""
    return personalization_engine.get_user_context(user_id)


if __name__ == "__main__":
    # Test personalization
    engine = PersonalizationEngine()

    # Create profile
    profile = engine.create_user_profile("user_1")
    print(f"Profile created for user_1")

    # Update from history
    history = [
        {"speaker_id": "user", "content": "Can you explain this in detail?"},
        {"speaker_id": "agent", "content": "Here's a detailed explanation..."},
    ]
    updated = engine.update_profile_from_history("user_1", history)
    print(f"Updated profile: {updated.preferences.detail_level.value}")

    # Generate personalized prompt
    personalized = engine.generate_personalized_prompt(
        "user_1",
        "Explain machine learning",
    )
    print(f"Personalized prompt:\n{personalized}")

    # Get context
    context = engine.get_user_context("user_1")
    print(f"Context: {json.dumps(context, indent=2)}")
