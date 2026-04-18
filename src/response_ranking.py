"""Response ranking and selection"""

import json
from pathlib import Path
from datetime import datetime
from typing import Optional, List, Dict, Any
from dataclasses import dataclass, field
from enum import Enum

RANK_DIR = Path.home() / ".memory-mcp" / "response-ranking"
RANK_DIR.mkdir(exist_ok=True, parents=True)


class RankingCriterion(Enum):
    """Criteria for ranking responses"""
    RELEVANCE = "relevance"  # How well addresses query
    SAFETY = "safety"  # No harmful content
    STYLE_MATCH = "style_match"  # Matches conversation style
    GOAL_ALIGNMENT = "goal_alignment"  # Advances conversation goals
    ENGAGEMENT = "engagement"  # Keeps user engaged
    INFORMATIVENESS = "informativeness"  # Provides valuable information
    CLARITY = "clarity"  # Easy to understand
    CONCISENESS = "conciseness"  # Appropriately brief


@dataclass
class CriterionScore:
    """Score on single ranking criterion"""
    criterion: RankingCriterion
    score: float  # 0-1
    confidence: float  # How confident in score
    evidence: List[str] = field(default_factory=list)  # Supporting evidence

    def to_dict(self) -> Dict:
        """Serialize score"""
        return {
            "criterion": self.criterion.value,
            "score": round(self.score, 2),
            "confidence": round(self.confidence, 2),
        }


@dataclass
class RankedResponse:
    """Response with ranking information"""
    response_id: str
    text: str
    overall_score: float  # Weighted combination
    ranking_position: int
    criterion_scores: Dict[str, CriterionScore] = field(default_factory=dict)
    ranking_justification: str = ""
    model_version: str = "1.0"
    created_at: str = ""

    def __post_init__(self):
        if not self.created_at:
            self.created_at = datetime.now().isoformat()

    def to_dict(self) -> Dict:
        """Serialize ranked response"""
        return {
            "response_id": self.response_id,
            "overall_score": round(self.overall_score, 2),
            "position": self.ranking_position,
            "criteria_evaluated": len(self.criterion_scores),
        }


@dataclass
class RankingContext:
    """Context for response ranking"""
    context_id: str
    user_intent: str
    dialogue_state: str
    user_knowledge_level: str
    goals: List[str] = field(default_factory=list)
    constraints: List[str] = field(default_factory=list)
    previous_responses: List[str] = field(default_factory=list)

    def to_dict(self) -> Dict:
        """Serialize context"""
        return {
            "context_id": self.context_id,
            "intent": self.user_intent,
            "state": self.dialogue_state,
            "goals": len(self.goals),
        }


class RankingModel:
    """Model for ranking responses"""

    # Default weights for criteria
    DEFAULT_WEIGHTS = {
        RankingCriterion.RELEVANCE: 0.25,
        RankingCriterion.SAFETY: 0.20,
        RankingCriterion.GOAL_ALIGNMENT: 0.15,
        RankingCriterion.INFORMATIVENESS: 0.15,
        RankingCriterion.CLARITY: 0.10,
        RankingCriterion.ENGAGEMENT: 0.10,
        RankingCriterion.STYLE_MATCH: 0.03,
        RankingCriterion.CONCISENESS: 0.02,
    }

    @staticmethod
    def compute_relevance(response: str, intent: str, previous: List[str]) -> CriterionScore:
        """Score relevance to user intent"""
        intent_match = 0.7 if intent.lower() in response.lower() else 0.3
        repetition_penalty = 0.8 if any(prev in response for prev in previous) else 1.0
        score = intent_match * repetition_penalty

        return CriterionScore(
            criterion=RankingCriterion.RELEVANCE,
            score=min(1.0, score),
            confidence=0.75,
            evidence=["Intent keyword present"] if intent_match > 0.5 else ["No direct intent match"],
        )

    @staticmethod
    def compute_safety(response: str) -> CriterionScore:
        """Score safety (no harmful content)"""
        harmful_keywords = ["kill", "hurt", "hate", "danger", "illegal"]
        harm_score = 1.0 - (len([k for k in harmful_keywords if k in response.lower()]) * 0.2)
        score = max(0.0, harm_score)

        return CriterionScore(
            criterion=RankingCriterion.SAFETY,
            score=min(1.0, score),
            confidence=0.9,
            evidence=["No harmful keywords detected"] if score > 0.8 else ["Potential safety concern"],
        )

    @staticmethod
    def compute_goal_alignment(
        response: str,
        goals: List[str],
    ) -> CriterionScore:
        """Score alignment with conversation goals"""
        if not goals:
            return CriterionScore(
                criterion=RankingCriterion.GOAL_ALIGNMENT,
                score=0.5,
                confidence=0.5,
            )

        matches = sum(1 for goal in goals if goal.lower() in response.lower())
        score = min(1.0, matches / len(goals)) if goals else 0.5

        return CriterionScore(
            criterion=RankingCriterion.GOAL_ALIGNMENT,
            score=score,
            confidence=0.7,
            evidence=[f"Matches {matches}/{len(goals)} goals"],
        )

    @staticmethod
    def compute_informativeness(response: str) -> CriterionScore:
        """Score informativeness"""
        word_count = len(response.split())
        unique_words = len(set(response.lower().split()))

        informativeness = min(1.0, (word_count / 50) * (unique_words / word_count))

        return CriterionScore(
            criterion=RankingCriterion.INFORMATIVENESS,
            score=informativeness,
            confidence=0.8,
            evidence=[f"{word_count} words, {unique_words} unique"],
        )

    @staticmethod
    def compute_clarity(response: str) -> CriterionScore:
        """Score clarity"""
        sentences = response.split(".")
        avg_sentence_length = sum(len(s.split()) for s in sentences) / len(sentences) if sentences else 0

        # Ideal: 15-25 words per sentence
        clarity = 1.0 if 15 <= avg_sentence_length <= 25 else max(0.5, 1.0 - abs(avg_sentence_length - 20) / 50)

        return CriterionScore(
            criterion=RankingCriterion.CLARITY,
            score=min(1.0, clarity),
            confidence=0.75,
            evidence=[f"Avg {avg_sentence_length:.1f} words/sentence"],
        )

    @staticmethod
    def compute_engagement(response: str) -> CriterionScore:
        """Score engagement potential"""
        engagement_markers = ["?", "!", "you", "your", "let's", "we", "together"]
        markers_found = sum(1 for m in engagement_markers if m in response.lower())
        score = min(1.0, markers_found / 4)

        return CriterionScore(
            criterion=RankingCriterion.ENGAGEMENT,
            score=score,
            confidence=0.7,
            evidence=[f"Found {markers_found} engagement markers"],
        )

    @staticmethod
    def compute_all_scores(
        response: str,
        context: RankingContext,
    ) -> Dict[RankingCriterion, CriterionScore]:
        """Compute scores across all criteria"""
        scores = {}

        scores[RankingCriterion.RELEVANCE] = RankingModel.compute_relevance(
            response, context.user_intent, context.previous_responses
        )
        scores[RankingCriterion.SAFETY] = RankingModel.compute_safety(response)
        scores[RankingCriterion.GOAL_ALIGNMENT] = RankingModel.compute_goal_alignment(
            response, context.goals
        )
        scores[RankingCriterion.INFORMATIVENESS] = RankingModel.compute_informativeness(response)
        scores[RankingCriterion.CLARITY] = RankingModel.compute_clarity(response)
        scores[RankingCriterion.ENGAGEMENT] = RankingModel.compute_engagement(response)

        return scores

    @staticmethod
    def compute_overall_score(
        criterion_scores: Dict[RankingCriterion, CriterionScore],
        weights: Dict[RankingCriterion, float] = None,
    ) -> float:
        """Compute weighted overall score"""
        if not weights:
            weights = RankingModel.DEFAULT_WEIGHTS

        total_weight = 0.0
        weighted_sum = 0.0

        for criterion, score_obj in criterion_scores.items():
            weight = weights.get(criterion, 0.1)
            weighted_sum += score_obj.score * weight
            total_weight += weight

        return weighted_sum / total_weight if total_weight > 0 else 0.5


class RankingExplainer:
    """Explain ranking decisions"""

    @staticmethod
    def explain_ranking(ranked_response: RankedResponse) -> str:
        """Generate explanation for ranking"""
        top_criteria = sorted(
            ranked_response.criterion_scores.items(),
            key=lambda x: x[1].score,
            reverse=True
        )[:3]

        explanation = f"Response ranked #{ranked_response.ranking_position} "
        explanation += f"(score: {ranked_response.overall_score:.2f}) "
        explanation += "because: "

        for criterion, score in top_criteria:
            explanation += f"{criterion.value} ({score.score:.2f}), "

        return explanation.rstrip(", ") + "."

    @staticmethod
    def explain_pair_comparison(
        response1: RankedResponse,
        response2: RankedResponse,
    ) -> str:
        """Explain why one response ranks higher"""
        score_diff = response1.overall_score - response2.overall_score
        direction = "better" if score_diff > 0 else "worse"

        explanation = f"Response 1 ranks {direction} than Response 2 "
        explanation += f"(difference: {abs(score_diff):.2f}). "

        # Find most impactful criterion
        for criterion in RankingCriterion:
            s1 = response1.criterion_scores.get(criterion)
            s2 = response2.criterion_scores.get(criterion)
            if s1 and s2:
                diff = abs(s1.score - s2.score)
                if diff > 0.2:
                    better = s1 if s1.score > s2.score else s2
                    explanation += f"Key difference: {criterion.value} ({better.score:.2f})"
                    break

        return explanation


class RankingEngine:
    """Orchestrate response ranking"""

    def __init__(self):
        self.ranked_responses: Dict[str, List[RankedResponse]] = {}

    def rank_responses(
        self,
        context: RankingContext,
        responses: List[str],
        weights: Dict[str, float] = None,
    ) -> List[RankedResponse]:
        """Rank response candidates"""
        ranked = []

        for i, response_text in enumerate(responses):
            criterion_scores = RankingModel.compute_all_scores(response_text, context)

            # Convert to proper type if needed
            if isinstance(weights, dict) and weights:
                weight_enums = {
                    RankingCriterion[k.upper()] if isinstance(k, str) else k: v
                    for k, v in weights.items()
                }
            else:
                weight_enums = None

            overall_score = RankingModel.compute_overall_score(criterion_scores, weight_enums)

            ranked_resp = RankedResponse(
                response_id=f"resp_{i}",
                text=response_text,
                overall_score=overall_score,
                ranking_position=0,
                criterion_scores={
                    criterion.value: score for criterion, score in criterion_scores.items()
                },
            )
            ranked.append(ranked_resp)

        # Sort and assign positions
        ranked.sort(key=lambda r: r.overall_score, reverse=True)
        for i, r in enumerate(ranked):
            r.ranking_position = i + 1
            r.ranking_justification = RankingExplainer.explain_ranking(r)

        self.ranked_responses[context.context_id] = ranked
        return ranked

    def get_top_ranked(self, context_id: str, k: int = 3) -> Optional[List[RankedResponse]]:
        """Get top K ranked responses"""
        responses = self.ranked_responses.get(context_id, [])
        return responses[:k] if responses else None


class RankingManager:
    """Manage ranking across conversations"""

    def __init__(self):
        self.engines: Dict[str, RankingEngine] = {}

    def create_engine(self, engine_id: str) -> RankingEngine:
        """Create ranking engine"""
        engine = RankingEngine()
        self.engines[engine_id] = engine
        return engine

    def get_engine(self, engine_id: str) -> Optional[RankingEngine]:
        """Get engine"""
        return self.engines.get(engine_id)


# Global manager
ranking_manager = RankingManager()


# MCP Tools

def create_ranking_engine(engine_id: str) -> dict:
    """Create response ranking engine"""
    engine = ranking_manager.create_engine(engine_id)
    return {"engine_id": engine_id, "created": True}


def rank_responses(
    engine_id: str,
    context_id: str,
    user_intent: str,
    dialogue_state: str,
    knowledge_level: str,
    responses: list,
) -> dict:
    """Rank response candidates"""
    engine = ranking_manager.get_engine(engine_id)
    if not engine:
        return {"error": "Engine not found"}

    context = RankingContext(
        context_id=context_id,
        user_intent=user_intent,
        dialogue_state=dialogue_state,
        user_knowledge_level=knowledge_level,
    )

    ranked = engine.rank_responses(context, responses)
    return {
        "context_id": context_id,
        "ranked_count": len(ranked),
        "ranked": [r.to_dict() for r in ranked],
    }


def get_top_responses(engine_id: str, context_id: str, k: int = 3) -> dict:
    """Get top ranked responses"""
    engine = ranking_manager.get_engine(engine_id)
    if not engine:
        return {"error": "Engine not found"}

    top = engine.get_top_ranked(context_id, k)
    return {
        "top_responses": [r.to_dict() for r in top] if top else [],
    } if top else {"error": "Context not found"}


if __name__ == "__main__":
    engine = RankingEngine()

    context = RankingContext(
        context_id="ctx_1",
        user_intent="seek_information",
        dialogue_state="information_seeking",
        user_knowledge_level="intermediate",
        goals=["understand machine learning"],
    )

    responses = [
        "Machine learning is a field of AI.",
        "ML enables systems to learn from data without explicit programming. It's used in recommendation systems, image recognition, and more.",
        "I don't know about that.",
    ]

    ranked = engine.rank_responses(context, responses)
    print(f"Ranked responses:")
    for r in ranked:
        print(f"  Position {r.ranking_position}: {r.overall_score:.2f}")
