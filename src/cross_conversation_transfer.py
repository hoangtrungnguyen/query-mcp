"""Cross-conversation learning: transfer insights from similar conversations"""

import json
from pathlib import Path
from datetime import datetime
from typing import Optional, List, Dict, Any
from dataclasses import dataclass, field
from enum import Enum

TRANSFER_DIR = Path.home() / ".memory-mcp" / "cross-conversation-transfer"
TRANSFER_DIR.mkdir(exist_ok=True, parents=True)


class TransferType(Enum):
    """Type of cross-conversation transfer"""
    EXACT_MATCH = "exact_match"  # Same problem, same user type
    DOMAIN_ANALOGY = "domain_analogy"  # Similar domain, different specifics
    METHODOLOGICAL = "methodological"  # Same approach works in different contexts
    FAILURE_AVOIDANCE = "failure_avoidance"  # Learn what failed elsewhere
    PATTERN_GENERALIZATION = "pattern_generalization"  # General pattern applicable


@dataclass
class ConversationSignature:
    """Unique signature of a conversation for matching"""
    signature_id: str
    conversation_id: str
    goal: str
    topics: List[str]
    user_type: str  # "technical", "beginner", "expert", etc.
    conversation_length: int
    success: bool
    key_techniques_used: List[str]

    def to_dict(self) -> Dict:
        """Serialize signature"""
        return {
            "signature_id": self.signature_id,
            "conversation_id": self.conversation_id,
            "goal": self.goal,
            "topics": self.topics,
            "user_type": self.user_type,
            "success": self.success,
        }


@dataclass
class ConversationMatch:
    """Match between current and past conversation"""
    match_id: str
    source_conversation: str
    similarity_score: float  # 0-1
    transfer_type: TransferType
    applicable_techniques: List[str]
    likely_challenges: List[str]
    recommended_actions: List[str]

    def to_dict(self) -> Dict:
        """Serialize match"""
        return {
            "match_id": self.match_id,
            "source_conversation": self.source_conversation,
            "similarity": round(self.similarity_score, 2),
            "transfer_type": self.transfer_type.value,
            "techniques": len(self.applicable_techniques),
        }


@dataclass
class TransferLearning:
    """Learned insight transferred from one conversation to another"""
    learning_id: str
    source_conversation: str
    target_conversation: str
    insight: str  # What was learned
    technique: str  # Technique/approach
    success_in_source: bool
    applied_in_target: bool = False
    effectiveness_in_target: float = 0.5

    def to_dict(self) -> Dict:
        """Serialize learning"""
        return {
            "learning_id": self.learning_id,
            "source": self.source_conversation,
            "target": self.target_conversation,
            "technique": self.technique,
            "source_success": self.success_in_source,
        }


class SimilarityCalculator:
    """Calculate conversation similarity for matching"""

    @staticmethod
    def calculate_topic_overlap(topics1: List[str], topics2: List[str]) -> float:
        """Calculate topic similarity"""
        if not topics1 or not topics2:
            return 0.0

        set1 = set(topics1)
        set2 = set(topics2)

        intersection = len(set1 & set2)
        union = len(set1 | set2)

        return intersection / union if union > 0 else 0.0

    @staticmethod
    def calculate_goal_similarity(goal1: str, goal2: str) -> float:
        """Calculate goal similarity using word overlap"""
        words1 = set(goal1.lower().split())
        words2 = set(goal2.lower().split())

        overlap = len(words1 & words2)
        total = max(len(words1), len(words2))

        return overlap / total if total > 0 else 0.0

    @staticmethod
    def calculate_overall_similarity(
        sig1: ConversationSignature,
        sig2: ConversationSignature,
    ) -> float:
        """Calculate overall conversation similarity"""
        goal_sim = SimilarityCalculator.calculate_goal_similarity(sig1.goal, sig2.goal)
        topic_sim = SimilarityCalculator.calculate_topic_overlap(sig1.topics, sig2.topics)
        user_type_match = 1.0 if sig1.user_type == sig2.user_type else 0.3

        # Weighted average
        overall = (goal_sim * 0.4) + (topic_sim * 0.4) + (user_type_match * 0.2)
        return overall


class TransferLearner:
    """Learn and apply transfer learning across conversations"""

    def __init__(self):
        self.conversation_signatures: Dict[str, ConversationSignature] = {}
        self.matches: Dict[str, ConversationMatch] = {}
        self.learned_transfers: Dict[str, TransferLearning] = {}

    def register_conversation(
        self,
        conversation_id: str,
        goal: str,
        topics: List[str],
        user_type: str,
        conversation_length: int,
        success: bool,
        techniques: List[str],
    ) -> ConversationSignature:
        """Register completed conversation for future matching"""
        signature = ConversationSignature(
            signature_id=f"sig_{len(self.conversation_signatures)}",
            conversation_id=conversation_id,
            goal=goal,
            topics=topics,
            user_type=user_type,
            conversation_length=conversation_length,
            success=success,
            key_techniques_used=techniques,
        )

        self.conversation_signatures[signature.signature_id] = signature
        return signature

    def find_similar_conversations(
        self,
        current_goal: str,
        current_topics: List[str],
        current_user_type: str,
        min_similarity: float = 0.5,
    ) -> List[ConversationMatch]:
        """Find similar past conversations"""
        matches = []

        for sig in self.conversation_signatures.values():
            similarity = SimilarityCalculator.calculate_overall_similarity(
                ConversationSignature(
                    signature_id="current",
                    conversation_id="current",
                    goal=current_goal,
                    topics=current_topics,
                    user_type=current_user_type,
                    conversation_length=0,
                    success=False,
                    key_techniques_used=[],
                ),
                sig,
            )

            if similarity >= min_similarity:
                # Determine transfer type
                transfer_type = self._determine_transfer_type(similarity)

                match = ConversationMatch(
                    match_id=f"match_{len(matches)}",
                    source_conversation=sig.conversation_id,
                    similarity_score=similarity,
                    transfer_type=transfer_type,
                    applicable_techniques=sig.key_techniques_used,
                    likely_challenges=[],
                    recommended_actions=self._generate_recommendations(sig),
                )

                matches.append(match)
                self.matches[match.match_id] = match

        # Sort by similarity
        matches.sort(key=lambda m: m.similarity_score, reverse=True)
        return matches

    @staticmethod
    def _determine_transfer_type(similarity: float) -> TransferType:
        """Determine transfer type based on similarity"""
        if similarity > 0.8:
            return TransferType.EXACT_MATCH
        elif similarity > 0.6:
            return TransferType.DOMAIN_ANALOGY
        elif similarity > 0.4:
            return TransferType.METHODOLOGICAL
        else:
            return TransferType.PATTERN_GENERALIZATION

    @staticmethod
    def _generate_recommendations(source_sig: ConversationSignature) -> List[str]:
        """Generate recommendations based on source conversation"""
        recommendations = []

        if source_sig.success:
            recommendations.append(f"Use techniques: {', '.join(source_sig.key_techniques_used)}")

        if source_sig.conversation_length > 20:
            recommendations.append("Expect extended conversation")

        if "beginner" in source_sig.user_type:
            recommendations.append("Slow pace, more explanation")

        return recommendations

    def record_transfer_learning(
        self,
        source_conversation: str,
        target_conversation: str,
        insight: str,
        technique: str,
        source_success: bool,
    ) -> TransferLearning:
        """Record transfer learning instance"""
        learning = TransferLearning(
            learning_id=f"tl_{len(self.learned_transfers)}",
            source_conversation=source_conversation,
            target_conversation=target_conversation,
            insight=insight,
            technique=technique,
            success_in_source=source_success,
        )

        self.learned_transfers[learning.learning_id] = learning
        return learning

    def record_transfer_outcome(
        self,
        learning_id: str,
        applied: bool,
        effectiveness: float,
    ):
        """Record how well transfer learning worked"""
        if learning_id not in self.learned_transfers:
            return

        learning = self.learned_transfers[learning_id]
        learning.applied_in_target = applied
        learning.effectiveness_in_target = effectiveness

    def get_transfer_summary(self) -> Dict[str, Any]:
        """Get summary of transfer learning"""
        if not self.learned_transfers:
            return {"learnings": 0, "applied": 0}

        applied = [t for t in self.learned_transfers.values() if t.applied_in_target]
        avg_effectiveness = (
            sum(t.effectiveness_in_target for t in applied) / len(applied)
            if applied
            else 0
        )

        return {
            "total_learnings": len(self.learned_transfers),
            "applied": len(applied),
            "avg_effectiveness": round(avg_effectiveness, 2),
            "success_transfer_rate": round(len(applied) / len(self.learned_transfers), 2),
        }


class TransferManager:
    """Manage cross-conversation transfer learning"""

    def __init__(self):
        self.learners: Dict[str, TransferLearner] = {}

    def create_learner(self, learner_id: str) -> TransferLearner:
        """Create transfer learner"""
        learner = TransferLearner()
        self.learners[learner_id] = learner
        return learner

    def get_learner(self, learner_id: str) -> Optional[TransferLearner]:
        """Get learner"""
        return self.learners.get(learner_id)


# Global manager
transfer_manager = TransferManager()


# MCP Tools

def create_transfer_learner(learner_id: str) -> dict:
    """Create transfer learner"""
    learner = transfer_manager.create_learner(learner_id)
    return {"learner_id": learner_id, "created": True}


def register_conversation(
    learner_id: str,
    conversation_id: str,
    goal: str,
    topics: list,
    user_type: str,
    length: int,
    success: bool,
    techniques: list,
) -> dict:
    """Register conversation"""
    learner = transfer_manager.get_learner(learner_id)
    if not learner:
        return {"error": "Learner not found"}

    signature = learner.register_conversation(
        conversation_id, goal, topics, user_type, length, success, techniques
    )
    return signature.to_dict()


def find_similar_conversations(
    learner_id: str,
    current_goal: str,
    current_topics: list,
    current_user_type: str,
    min_similarity: float = 0.5,
) -> dict:
    """Find similar conversations"""
    learner = transfer_manager.get_learner(learner_id)
    if not learner:
        return {"error": "Learner not found"}

    matches = learner.find_similar_conversations(
        current_goal, current_topics, current_user_type, min_similarity
    )
    return {
        "matches": len(matches),
        "results": [m.to_dict() for m in matches],
    }


def record_transfer_learning(
    learner_id: str,
    source_conversation: str,
    target_conversation: str,
    insight: str,
    technique: str,
    source_success: bool,
) -> dict:
    """Record transfer learning"""
    learner = transfer_manager.get_learner(learner_id)
    if not learner:
        return {"error": "Learner not found"}

    learning = learner.record_transfer_learning(
        source_conversation, target_conversation, insight, technique, source_success
    )
    return learning.to_dict()


def record_transfer_outcome(
    learner_id: str,
    learning_id: str,
    applied: bool,
    effectiveness: float,
) -> dict:
    """Record transfer outcome"""
    learner = transfer_manager.get_learner(learner_id)
    if not learner:
        return {"error": "Learner not found"}

    learner.record_transfer_outcome(learning_id, applied, effectiveness)
    return {"recorded": True}


def get_transfer_summary(learner_id: str) -> dict:
    """Get transfer summary"""
    learner = transfer_manager.get_learner(learner_id)
    if not learner:
        return {"error": "Learner not found"}

    return learner.get_transfer_summary()


if __name__ == "__main__":
    learner = TransferLearner()

    # Register conversations
    sig1 = learner.register_conversation(
        "conv_1", "Learn Python", ["python", "functions"], "beginner", 10, True, ["step_by_step"]
    )

    sig2 = learner.register_conversation(
        "conv_2", "Learn JavaScript", ["javascript", "functions"], "beginner", 12, True, ["examples"]
    )

    # Find similar
    matches = learner.find_similar_conversations(
        "Learn TypeScript", ["typescript", "functions"], "beginner"
    )
    print(f"Found {len(matches)} similar conversations")
