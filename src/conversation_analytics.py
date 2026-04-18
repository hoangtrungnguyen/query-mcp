"""Conversation analytics and quality metrics"""

import json
from pathlib import Path
from datetime import datetime, timedelta
from typing import Optional, List, Dict, Any
from dataclasses import dataclass, field
from enum import Enum
import math

ANALYTICS_DIR = Path.home() / ".memory-mcp" / "conversation-analytics"
ANALYTICS_DIR.mkdir(exist_ok=True, parents=True)


class QualityDimension(Enum):
    """Dimensions of conversation quality"""
    RELEVANCE = "relevance"  # Responses match queries
    COMPLETENESS = "completeness"  # Answers are thorough
    CLARITY = "clarity"  # Easy to understand
    COHERENCE = "coherence"  # Logical flow
    ENGAGEMENT = "engagement"  # User stays engaged
    SAFETY = "safety"  # No harmful content
    EFFICIENCY = "efficiency"  # Concise and focused
    ACCURACY = "accuracy"  # Factually correct


class EngagementLevel(Enum):
    """User engagement levels"""
    VERY_LOW = 0.1
    LOW = 0.3
    MEDIUM = 0.5
    HIGH = 0.7
    VERY_HIGH = 0.9


@dataclass
class ConversationMetrics:
    """Metrics for single conversation"""
    conversation_id: str
    turn_count: int
    total_tokens: int
    user_token_count: int
    assistant_token_count: int
    avg_response_length: int
    conversation_duration_minutes: float
    user_satisfaction: float  # 0-5 or 0-1
    created_at: str = ""

    def __post_init__(self):
        if not self.created_at:
            self.created_at = datetime.now().isoformat()

    def to_dict(self) -> Dict:
        """Serialize metrics"""
        return {
            "conversation_id": self.conversation_id,
            "turns": self.turn_count,
            "tokens": self.total_tokens,
            "duration_minutes": round(self.conversation_duration_minutes, 1),
            "satisfaction": round(self.user_satisfaction, 2),
        }


@dataclass
class QualityScore:
    """Quality assessment"""
    score_id: str
    conversation_id: str
    dimension: QualityDimension
    score: float  # 0-1
    reasoning: str = ""
    evidence: List[str] = field(default_factory=list)  # Supporting examples
    created_at: str = ""

    def __post_init__(self):
        if not self.created_at:
            self.created_at = datetime.now().isoformat()

    def to_dict(self) -> Dict:
        """Serialize score"""
        return {
            "dimension": self.dimension.value,
            "score": round(self.score, 2),
            "evidence_items": len(self.evidence),
        }


@dataclass
class EngagementMetrics:
    """User engagement metrics"""
    engagement_id: str
    conversation_id: str
    turn_times: List[float]  # Minutes between turns
    response_times: List[float]  # How long assistant takes
    user_turn_lengths: List[int]  # Tokens in each user turn
    drop_off_point: Optional[int] = None  # When engagement dropped
    momentum: float = 0.0  # Conversation momentum
    engagement_level: EngagementLevel = EngagementLevel.MEDIUM
    created_at: str = ""

    def __post_init__(self):
        if not self.created_at:
            self.created_at = datetime.now().isoformat()

        # Calculate momentum
        if self.user_turn_lengths:
            avg_length = sum(self.user_turn_lengths) / len(self.user_turn_lengths)
            if avg_length > 50:
                self.momentum = 0.8
            elif avg_length > 20:
                self.momentum = 0.5
            else:
                self.momentum = 0.2

    def to_dict(self) -> Dict:
        """Serialize metrics"""
        return {
            "engagement_id": self.engagement_id,
            "turns_analyzed": len(self.turn_times),
            "avg_response_time": round(sum(self.response_times) / len(self.response_times), 2) if self.response_times else 0,
            "momentum": round(self.momentum, 2),
            "engagement_level": self.engagement_level.name,
        }


class MetricsCalculator:
    """Calculate conversation metrics"""

    @staticmethod
    def calculate_conversation_metrics(
        conversation_id: str,
        turns: List[Dict[str, Any]],
        start_time: datetime,
        end_time: datetime,
        user_satisfaction: float = 0.0,
    ) -> ConversationMetrics:
        """Calculate metrics for conversation"""
        turn_count = len(turns)
        user_tokens = sum(t.get("user_tokens", 0) for t in turns)
        assistant_tokens = sum(t.get("assistant_tokens", 0) for t in turns)
        total_tokens = user_tokens + assistant_tokens

        avg_response_length = assistant_tokens // max(1, turn_count)
        duration = (end_time - start_time).total_seconds() / 60

        return ConversationMetrics(
            conversation_id=conversation_id,
            turn_count=turn_count,
            total_tokens=total_tokens,
            user_token_count=user_tokens,
            assistant_token_count=assistant_tokens,
            avg_response_length=avg_response_length,
            conversation_duration_minutes=duration,
            user_satisfaction=user_satisfaction,
        )

    @staticmethod
    def assess_dimension(
        conversation_id: str,
        dimension: QualityDimension,
        turns: List[Dict[str, Any]],
    ) -> QualityScore:
        """Assess quality dimension"""
        # Simple heuristic-based assessment
        score = 0.5  # Default medium

        if dimension == QualityDimension.RELEVANCE:
            # Check if responses address queries
            score = 0.7 if len(turns) > 0 else 0.5

        elif dimension == QualityDimension.COMPLETENESS:
            # Check response lengths
            avg_length = sum(
                len(t.get("response", "").split())
                for t in turns
            ) / max(1, len(turns))
            score = min(1.0, avg_length / 100)

        elif dimension == QualityDimension.CLARITY:
            # Check for simple vocabulary
            score = 0.7

        elif dimension == QualityDimension.COHERENCE:
            # Check conversation flow
            score = 0.6 if len(turns) > 1 else 0.5

        elif dimension == QualityDimension.ENGAGEMENT:
            # Check user participation
            user_length = sum(
                len(t.get("user_input", "").split())
                for t in turns
            ) / max(1, len(turns))
            score = min(1.0, user_length / 50)

        elif dimension == QualityDimension.SAFETY:
            score = 0.95  # Assume safe

        elif dimension == QualityDimension.EFFICIENCY:
            # Check turn count vs tokens
            if len(turns) > 0:
                score = 0.8 if len(turns) < 20 else 0.5

        else:  # ACCURACY
            score = 0.8

        quality_score = QualityScore(
            score_id=f"q_{conversation_id}_{dimension.value}",
            conversation_id=conversation_id,
            dimension=dimension,
            score=min(1.0, max(0.0, score)),
        )

        return quality_score

    @staticmethod
    def calculate_engagement_metrics(
        conversation_id: str,
        turns: List[Dict[str, Any]],
    ) -> EngagementMetrics:
        """Calculate engagement metrics"""
        turn_times = []
        response_times = []
        user_lengths = []

        for i, turn in enumerate(turns):
            if i > 0:
                time_diff = turn.get("time", datetime.now()) - turns[i-1].get("time", datetime.now())
                turn_times.append(time_diff.total_seconds() / 60)

            response_times.append(turn.get("response_time_ms", 0) / 1000)
            user_lengths.append(len(turn.get("user_input", "").split()))

        engagement = EngagementMetrics(
            engagement_id=f"eng_{conversation_id}",
            conversation_id=conversation_id,
            turn_times=turn_times,
            response_times=response_times,
            user_turn_lengths=user_lengths,
        )

        # Determine engagement level
        if engagement.momentum > 0.7:
            engagement.engagement_level = EngagementLevel.HIGH
        elif engagement.momentum > 0.5:
            engagement.engagement_level = EngagementLevel.MEDIUM
        else:
            engagement.engagement_level = EngagementLevel.LOW

        return engagement


class ConversationAnalyzer:
    """Analyze conversations"""

    def __init__(self):
        self.metrics: Dict[str, ConversationMetrics] = {}
        self.quality_scores: Dict[str, List[QualityScore]] = {}
        self.engagement_metrics: Dict[str, EngagementMetrics] = {}

    def analyze_conversation(
        self,
        conversation_id: str,
        turns: List[Dict[str, Any]],
        start_time: datetime,
        end_time: datetime,
        user_satisfaction: float = 0.0,
    ) -> Dict[str, Any]:
        """Complete conversation analysis"""
        # Calculate metrics
        metrics = MetricsCalculator.calculate_conversation_metrics(
            conversation_id,
            turns,
            start_time,
            end_time,
            user_satisfaction,
        )
        self.metrics[conversation_id] = metrics

        # Assess quality dimensions
        quality_scores = []
        for dimension in QualityDimension:
            score = MetricsCalculator.assess_dimension(
                conversation_id,
                dimension,
                turns,
            )
            quality_scores.append(score)
        self.quality_scores[conversation_id] = quality_scores

        # Calculate engagement
        engagement = MetricsCalculator.calculate_engagement_metrics(
            conversation_id,
            turns,
        )
        self.engagement_metrics[conversation_id] = engagement

        # Overall quality
        avg_quality = sum(q.score for q in quality_scores) / len(quality_scores)

        return {
            "conversation_id": conversation_id,
            "metrics": metrics.to_dict(),
            "quality_scores": [q.to_dict() for q in quality_scores],
            "overall_quality": round(avg_quality, 2),
            "engagement": engagement.to_dict(),
        }

    def get_analytics_report(self, conversation_id: str) -> Optional[Dict]:
        """Get complete analytics report"""
        if conversation_id not in self.metrics:
            return None

        metrics = self.metrics[conversation_id]
        quality = self.quality_scores.get(conversation_id, [])
        engagement = self.engagement_metrics.get(conversation_id)

        avg_quality = sum(q.score for q in quality) / len(quality) if quality else 0.0

        return {
            "conversation_id": conversation_id,
            "metrics": metrics.to_dict(),
            "overall_quality": round(avg_quality, 2),
            "quality_breakdown": {
                q.dimension.value: q.score for q in quality
            },
            "engagement": engagement.to_dict() if engagement else None,
            "recommendations": self._generate_recommendations(metrics, quality, engagement),
        }

    def _generate_recommendations(
        self,
        metrics: ConversationMetrics,
        quality: List[QualityScore],
        engagement: Optional[EngagementMetrics],
    ) -> List[str]:
        """Generate improvement recommendations"""
        recommendations = []

        # Quality-based recommendations
        low_quality = [q for q in quality if q.score < 0.5]
        if low_quality:
            for q in low_quality:
                recommendations.append(f"Improve {q.dimension.value}")

        # Engagement-based recommendations
        if engagement and engagement.engagement_level == EngagementLevel.LOW:
            recommendations.append("Increase user engagement")

        # Efficiency recommendations
        if metrics.turn_count > 30:
            recommendations.append("Consider condensing conversations")

        return recommendations

    def get_system_analytics(self) -> Dict[str, Any]:
        """Get analytics across all conversations"""
        if not self.metrics:
            return {}

        all_metrics = list(self.metrics.values())
        avg_quality = sum(
            sum(q.score for q in self.quality_scores.get(m.conversation_id, []))
            / len(self.quality_scores.get(m.conversation_id, [1]))
            for m in all_metrics
        ) / len(all_metrics)

        return {
            "total_conversations": len(self.metrics),
            "avg_turn_count": sum(m.turn_count for m in all_metrics) / len(all_metrics),
            "avg_token_count": sum(m.total_tokens for m in all_metrics) / len(all_metrics),
            "avg_quality": round(avg_quality, 2),
            "avg_user_satisfaction": sum(m.user_satisfaction for m in all_metrics) / len(all_metrics),
        }


class AnalyticsManager:
    """Manage analytics across systems"""

    def __init__(self):
        self.analyzers: Dict[str, ConversationAnalyzer] = {}

    def create_analyzer(self, analyzer_id: str) -> ConversationAnalyzer:
        """Create analyzer"""
        analyzer = ConversationAnalyzer()
        self.analyzers[analyzer_id] = analyzer
        return analyzer

    def get_analyzer(self, analyzer_id: str) -> Optional[ConversationAnalyzer]:
        """Get analyzer"""
        return self.analyzers.get(analyzer_id)


# Global manager
analytics_manager = AnalyticsManager()


# MCP Tools

def create_analytics_system(analyzer_id: str) -> dict:
    """Create conversation analytics system"""
    analyzer = analytics_manager.create_analyzer(analyzer_id)
    return {"analyzer_id": analyzer_id, "created": True}


def analyze_conversation(
    analyzer_id: str,
    conversation_id: str,
    turns: list,
    start_time: str,
    end_time: str,
    user_satisfaction: float = 0.0,
) -> dict:
    """Analyze conversation"""
    analyzer = analytics_manager.get_analyzer(analyzer_id)
    if not analyzer:
        return {"error": "Analyzer not found"}

    try:
        start = datetime.fromisoformat(start_time)
        end = datetime.fromisoformat(end_time)
    except:
        return {"error": "Invalid datetime format"}

    return analyzer.analyze_conversation(
        conversation_id,
        turns,
        start,
        end,
        user_satisfaction,
    )


def get_analytics_report(analyzer_id: str, conversation_id: str) -> dict:
    """Get analytics report"""
    analyzer = analytics_manager.get_analyzer(analyzer_id)
    if not analyzer:
        return {"error": "Analyzer not found"}

    report = analyzer.get_analytics_report(conversation_id)
    return report or {"error": "Conversation not found"}


def get_system_analytics(analyzer_id: str) -> dict:
    """Get system-wide analytics"""
    analyzer = analytics_manager.get_analyzer(analyzer_id)
    if not analyzer:
        return {"error": "Analyzer not found"}

    return analyzer.get_system_analytics()


if __name__ == "__main__":
    # Test conversation analytics
    analyzer = ConversationAnalyzer()

    # Analyze conversation
    turns = [
        {"user_input": "Hello", "response": "Hi there", "user_tokens": 10, "assistant_tokens": 10, "response_time_ms": 500, "time": datetime.now()},
        {"user_input": "How are you?", "response": "I'm doing well", "user_tokens": 10, "assistant_tokens": 15, "response_time_ms": 600, "time": datetime.now()},
    ]

    start_time = datetime.now() - timedelta(minutes=10)
    end_time = datetime.now()

    report = analyzer.analyze_conversation(
        "conv_1",
        turns,
        start_time,
        end_time,
        user_satisfaction=0.9,
    )

    print(f"Report: {json.dumps(report, indent=2)}")

    # System analytics
    system = analyzer.get_system_analytics()
    print(f"System analytics: {json.dumps(system, indent=2)}")
