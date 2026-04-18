"""Conversation recommendation engine"""

import json
from pathlib import Path
from datetime import datetime
from typing import Optional, List, Dict, Any
from dataclasses import dataclass, field

RECOMMEND_DIR = Path.home() / ".memory-mcp" / "recommendations"
RECOMMEND_DIR.mkdir(exist_ok=True, parents=True)


@dataclass
class ConversationRecommendation:
    """Recommended conversation"""
    recommendation_id: str
    conversation_id: str
    title: str
    reason: str
    similarity_score: float
    relevance: float = 0.7
    created_at: str = ""

    def __post_init__(self):
        if not self.created_at:
            self.created_at = datetime.now().isoformat()

    def to_dict(self) -> Dict:
        return {
            "conversation_id": self.conversation_id,
            "title": self.title,
            "reason": self.reason,
            "similarity": round(self.similarity_score, 2),
        }


class RecommendationEngine:
    """Generate conversation recommendations"""

    def __init__(self):
        self.conversation_history: Dict[str, Dict] = {}
        self.user_interests: Dict[str, List[str]] = {}

    def record_conversation(
        self,
        conversation_id: str,
        user_id: str,
        topic: str,
        satisfaction: float,
    ):
        """Record conversation"""
        self.conversation_history[conversation_id] = {
            "user_id": user_id,
            "topic": topic,
            "satisfaction": satisfaction,
            "timestamp": datetime.now().isoformat(),
        }

        # Track interests
        if user_id not in self.user_interests:
            self.user_interests[user_id] = []

        self.user_interests[user_id].append(topic)

    def recommend(
        self,
        user_id: str,
        current_topic: str,
        top_k: int = 5,
    ) -> List[ConversationRecommendation]:
        """Recommend conversations"""
        recommendations = []

        # Find similar conversations
        for conv_id, conv_data in self.conversation_history.items():
            if conv_data["user_id"] != user_id:
                continue

            topic = conv_data["topic"]
            satisfaction = conv_data["satisfaction"]

            # Similarity score (simple: same words in topic)
            current_words = set(current_topic.lower().split())
            topic_words = set(topic.lower().split())
            overlap = len(current_words & topic_words)
            similarity = overlap / max(1, len(current_words | topic_words))

            if similarity > 0 or satisfaction > 0.7:
                rec = ConversationRecommendation(
                    recommendation_id=f"rec_{conv_id}",
                    conversation_id=conv_id,
                    title=f"Previous: {topic}",
                    reason="Similar to your current interest" if similarity > 0 else "You found this helpful before",
                    similarity_score=similarity,
                    relevance=similarity if similarity > 0 else satisfaction,
                )
                recommendations.append(rec)

        # Sort by relevance
        sorted_recs = sorted(
            recommendations,
            key=lambda x: x.relevance,
            reverse=True
        )[:top_k]

        return sorted_recs

    def get_recommendations(
        self,
        user_id: str,
        current_topic: str,
    ) -> Dict:
        """Get recommendations"""
        recs = self.recommend(user_id, current_topic)

        return {
            "user_id": user_id,
            "recommendations": [r.to_dict() for r in recs],
            "count": len(recs),
        }


# Global engine
recommendation_engine = RecommendationEngine()


def record_conversation(
    conversation_id: str,
    user_id: str,
    topic: str,
    satisfaction: float,
) -> dict:
    """Record conversation"""
    recommendation_engine.record_conversation(conversation_id, user_id, topic, satisfaction)
    return {"recorded": True}


def get_recommendations(user_id: str, current_topic: str) -> dict:
    """Get recommendations"""
    return recommendation_engine.get_recommendations(user_id, current_topic)
