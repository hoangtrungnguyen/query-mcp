"""Confidence quantification and uncertainty estimation"""

import json
from pathlib import Path
from datetime import datetime
from typing import Optional, List, Dict, Any, Tuple
from dataclasses import dataclass, field
from enum import Enum
import math

CONFIDENCE_DIR = Path.home() / ".memory-mcp" / "confidence-uncertainty"
CONFIDENCE_DIR.mkdir(exist_ok=True, parents=True)


class UncertaintyType(Enum):
    """Types of uncertainty"""
    ALEATORIC = "aleatoric"  # Irreducible randomness in data
    EPISTEMIC = "epistemic"  # Reducible via more knowledge
    STRUCTURAL = "structural"  # Model limitations
    DISTRIBUTION_SHIFT = "distribution_shift"  # Out-of-distribution data


class ConfidenceLevel(Enum):
    """Confidence classification"""
    VERY_LOW = 0.1
    LOW = 0.3
    MODERATE = 0.5
    HIGH = 0.7
    VERY_HIGH = 0.9


@dataclass
class ConfidenceMetrics:
    """Confidence metrics for decision"""
    decision_id: str
    point_estimate: float  # Primary prediction value
    confidence: float  # 0-1, model's confidence
    lower_bound: float  # Lower confidence interval
    upper_bound: float  # Upper confidence interval
    interval_confidence: float = 0.95  # Typically 95%
    sources_of_uncertainty: List[str] = field(default_factory=list)
    evidence_count: int = 0
    conflicting_evidence: int = 0
    created_at: str = ""

    def __post_init__(self):
        if not self.created_at:
            self.created_at = datetime.now().isoformat()

    def get_confidence_category(self) -> ConfidenceLevel:
        """Categorize confidence level"""
        if self.confidence >= 0.85:
            return ConfidenceLevel.VERY_HIGH
        elif self.confidence >= 0.7:
            return ConfidenceLevel.HIGH
        elif self.confidence >= 0.5:
            return ConfidenceLevel.MODERATE
        elif self.confidence >= 0.3:
            return ConfidenceLevel.LOW
        else:
            return ConfidenceLevel.VERY_LOW

    def get_uncertainty_range(self) -> float:
        """Get width of uncertainty interval"""
        return self.upper_bound - self.lower_bound

    def is_high_uncertainty(self, threshold: float = 0.3) -> bool:
        """Check if uncertainty exceeds threshold"""
        return self.get_uncertainty_range() > threshold

    def to_dict(self) -> Dict:
        """Serialize metrics"""
        return {
            "decision_id": self.decision_id,
            "point_estimate": round(self.point_estimate, 3),
            "confidence": round(self.confidence, 3),
            "ci_lower": round(self.lower_bound, 3),
            "ci_upper": round(self.upper_bound, 3),
            "uncertainty_type": len(self.sources_of_uncertainty),
            "evidence": self.evidence_count,
            "conflicts": self.conflicting_evidence,
        }


@dataclass
class DecisionJustification:
    """Reasoning behind confidence assessment"""
    justification_id: str
    decision_id: str
    primary_factors: List[str]  # Key reasons for confidence
    supporting_evidence: List[Dict[str, Any]] = field(default_factory=list)
    limiting_factors: List[str] = field(default_factory=list)  # Reasons for uncertainty
    alternative_interpretations: List[str] = field(default_factory=list)
    expert_agreement: float = 0.0  # % of experts agreeing
    created_at: str = ""

    def __post_init__(self):
        if not self.created_at:
            self.created_at = datetime.now().isoformat()

    def to_dict(self) -> Dict:
        """Serialize justification"""
        return {
            "justification_id": self.justification_id,
            "primary_factors": len(self.primary_factors),
            "supporting_evidence": len(self.supporting_evidence),
            "limiting_factors": len(self.limiting_factors),
            "alternatives": len(self.alternative_interpretations),
            "expert_agreement": self.expert_agreement,
        }


@dataclass
class UncertaintyAnalysis:
    """Breakdown of uncertainty sources"""
    analysis_id: str
    decision_id: str
    aleatoric_uncertainty: float = 0.0  # Data randomness
    epistemic_uncertainty: float = 0.0  # Knowledge gap
    structural_uncertainty: float = 0.0  # Model limitation
    distribution_uncertainty: float = 0.0  # OOD risk
    total_uncertainty: float = 0.0
    dominant_uncertainty_type: Optional[UncertaintyType] = None
    created_at: str = ""

    def __post_init__(self):
        if not self.created_at:
            self.created_at = datetime.now().isoformat()

        # Calculate total
        self.total_uncertainty = (
            self.aleatoric_uncertainty +
            self.epistemic_uncertainty +
            self.structural_uncertainty +
            self.distribution_uncertainty
        )

        # Identify dominant type
        uncertainties = {
            UncertaintyType.ALEATORIC: self.aleatoric_uncertainty,
            UncertaintyType.EPISTEMIC: self.epistemic_uncertainty,
            UncertaintyType.STRUCTURAL: self.structural_uncertainty,
            UncertaintyType.DISTRIBUTION_SHIFT: self.distribution_uncertainty,
        }

        if uncertainties:
            self.dominant_uncertainty_type = max(
                uncertainties.items(),
                key=lambda x: x[1]
            )[0]

    def get_recommendations(self) -> List[str]:
        """Get mitigation recommendations"""
        recommendations = []

        if self.epistemic_uncertainty > 0.3:
            recommendations.append("Gather more training data")

        if self.structural_uncertainty > 0.3:
            recommendations.append("Consider model improvements")

        if self.distribution_uncertainty > 0.3:
            recommendations.append("Check for out-of-distribution inputs")

        if self.aleatoric_uncertainty > 0.3:
            recommendations.append("Uncertainty is inherent; focus on risk management")

        return recommendations

    def to_dict(self) -> Dict:
        """Serialize analysis"""
        return {
            "analysis_id": self.analysis_id,
            "aleatoric": round(self.aleatoric_uncertainty, 3),
            "epistemic": round(self.epistemic_uncertainty, 3),
            "structural": round(self.structural_uncertainty, 3),
            "distribution_shift": round(self.distribution_uncertainty, 3),
            "total": round(self.total_uncertainty, 3),
            "dominant": self.dominant_uncertainty_type.value if self.dominant_uncertainty_type else None,
        }


class ConfidenceEstimator:
    """Estimate confidence and uncertainty"""

    @staticmethod
    def estimate_from_agreement(responses: List[Tuple[str, float]]) -> float:
        """Estimate confidence from multiple responses"""
        if not responses:
            return 0.0

        # Group by response value
        response_groups = {}
        for resp, confidence in responses:
            response_groups[resp] = response_groups.get(resp, 0) + confidence

        # Confidence is agreement ratio weighted by source confidence
        total_confidence = sum(conf for _, conf in responses)
        max_group_confidence = max(response_groups.values()) if response_groups else 0

        return min(1.0, max_group_confidence / max(1, total_confidence))

    @staticmethod
    def estimate_confidence_interval(
        point_estimate: float,
        confidence: float,
        data_points: int = 10,
        std_dev: float = 0.15,
    ) -> Tuple[float, float]:
        """Estimate confidence interval"""
        if data_points < 2:
            # High uncertainty with limited data
            margin = 0.5
        else:
            # Standard error decreases with more data
            standard_error = std_dev / math.sqrt(data_points)
            z_score = 1.96  # 95% confidence interval
            margin = z_score * standard_error

        # Adjust margin by model confidence
        margin = margin * (1 - confidence)

        lower = max(0, point_estimate - margin)
        upper = min(1.0, point_estimate + margin)

        return lower, upper

    @staticmethod
    def detect_distribution_shift(
        new_input: Dict[str, Any],
        training_distribution: Dict[str, Any],
    ) -> float:
        """Detect out-of-distribution risk"""
        # Simple heuristic: feature differences
        differences = 0
        common_keys = set(new_input.keys()) & set(training_distribution.keys())

        if not common_keys:
            return 1.0  # Completely different

        for key in common_keys:
            new_val = new_input.get(key, 0)
            train_val = training_distribution.get(key, 0)

            if isinstance(new_val, (int, float)) and isinstance(train_val, (int, float)):
                if train_val != 0:
                    diff = abs(new_val - train_val) / abs(train_val)
                    if diff > 2.0:  # 2x difference
                        differences += 1

        return min(1.0, differences / len(common_keys)) if common_keys else 0.5


class ConfidenceTracker:
    """Track decision confidence over time"""

    def __init__(self):
        self.confidence_metrics: Dict[str, ConfidenceMetrics] = {}
        self.justifications: Dict[str, DecisionJustification] = {}
        self.uncertainty_analyses: Dict[str, UncertaintyAnalysis] = {}

    def record_decision(
        self,
        decision_id: str,
        point_estimate: float,
        confidence: float,
        evidence_count: int = 0,
    ) -> ConfidenceMetrics:
        """Record decision with confidence"""
        lower, upper = ConfidenceEstimator.estimate_confidence_interval(
            point_estimate,
            confidence,
            evidence_count,
        )

        metrics = ConfidenceMetrics(
            decision_id=decision_id,
            point_estimate=point_estimate,
            confidence=confidence,
            lower_bound=lower,
            upper_bound=upper,
            evidence_count=evidence_count,
        )

        self.confidence_metrics[decision_id] = metrics
        return metrics

    def record_justification(
        self,
        decision_id: str,
        primary_factors: List[str],
        limiting_factors: List[str],
        expert_agreement: float = 0.5,
    ) -> DecisionJustification:
        """Record decision justification"""
        justification = DecisionJustification(
            justification_id=f"just_{decision_id}",
            decision_id=decision_id,
            primary_factors=primary_factors,
            limiting_factors=limiting_factors,
            expert_agreement=expert_agreement,
        )

        self.justifications[decision_id] = justification
        return justification

    def analyze_uncertainty(
        self,
        decision_id: str,
        aleatoric: float = 0.0,
        epistemic: float = 0.0,
        structural: float = 0.0,
        distribution_shift: float = 0.0,
    ) -> UncertaintyAnalysis:
        """Analyze sources of uncertainty"""
        analysis = UncertaintyAnalysis(
            analysis_id=f"unc_{decision_id}",
            decision_id=decision_id,
            aleatoric_uncertainty=aleatoric,
            epistemic_uncertainty=epistemic,
            structural_uncertainty=structural,
            distribution_uncertainty=distribution_shift,
        )

        self.uncertainty_analyses[decision_id] = analysis
        return analysis

    def get_confidence_report(self, decision_id: str) -> Optional[Dict[str, Any]]:
        """Get comprehensive confidence report"""
        if decision_id not in self.confidence_metrics:
            return None

        metrics = self.confidence_metrics[decision_id]
        justification = self.justifications.get(decision_id)
        analysis = self.uncertainty_analyses.get(decision_id)

        return {
            "decision_id": decision_id,
            "confidence_metrics": metrics.to_dict(),
            "confidence_category": metrics.get_confidence_category().name,
            "uncertainty_range": round(metrics.get_uncertainty_range(), 3),
            "justification": justification.to_dict() if justification else None,
            "uncertainty_analysis": analysis.to_dict() if analysis else None,
            "high_uncertainty": metrics.is_high_uncertainty(),
        }

    def get_confidence_trends(self) -> Dict[str, Any]:
        """Analyze confidence trends"""
        if not self.confidence_metrics:
            return {}

        confidences = [m.confidence for m in self.confidence_metrics.values()]
        avg_confidence = sum(confidences) / len(confidences)
        min_confidence = min(confidences)
        max_confidence = max(confidences)

        low_confidence_decisions = [
            d for d, m in self.confidence_metrics.items()
            if m.confidence < 0.5
        ]

        return {
            "total_decisions": len(self.confidence_metrics),
            "avg_confidence": round(avg_confidence, 3),
            "confidence_range": (round(min_confidence, 3), round(max_confidence, 3)),
            "low_confidence_count": len(low_confidence_decisions),
            "high_uncertainty_count": sum(
                1 for m in self.confidence_metrics.values()
                if m.is_high_uncertainty()
            ),
        }


class ConfidenceManager:
    """Manage confidence tracking across sessions"""

    def __init__(self):
        self.trackers: Dict[str, ConfidenceTracker] = {}

    def create_tracker(self, tracker_id: str) -> ConfidenceTracker:
        """Create confidence tracker"""
        tracker = ConfidenceTracker()
        self.trackers[tracker_id] = tracker
        return tracker

    def get_tracker(self, tracker_id: str) -> Optional[ConfidenceTracker]:
        """Get tracker"""
        return self.trackers.get(tracker_id)


# Global manager
confidence_manager = ConfidenceManager()


# MCP Tools

def create_confidence_tracker(tracker_id: str) -> dict:
    """Create confidence tracker"""
    tracker = confidence_manager.create_tracker(tracker_id)
    return {"tracker_id": tracker_id, "created": True}


def record_decision_confidence(
    tracker_id: str,
    decision_id: str,
    point_estimate: float,
    confidence: float,
    evidence_count: int = 0,
) -> dict:
    """Record decision with confidence"""
    tracker = confidence_manager.get_tracker(tracker_id)
    if not tracker:
        return {"error": "Tracker not found"}

    metrics = tracker.record_decision(
        decision_id,
        point_estimate,
        confidence,
        evidence_count,
    )
    return metrics.to_dict()


def record_decision_justification(
    tracker_id: str,
    decision_id: str,
    primary_factors: list,
    limiting_factors: list,
) -> dict:
    """Record decision justification"""
    tracker = confidence_manager.get_tracker(tracker_id)
    if not tracker:
        return {"error": "Tracker not found"}

    justification = tracker.record_justification(
        decision_id,
        primary_factors,
        limiting_factors,
    )
    return justification.to_dict()


def analyze_decision_uncertainty(
    tracker_id: str,
    decision_id: str,
    aleatoric: float = 0.0,
    epistemic: float = 0.0,
) -> dict:
    """Analyze uncertainty sources"""
    tracker = confidence_manager.get_tracker(tracker_id)
    if not tracker:
        return {"error": "Tracker not found"}

    analysis = tracker.analyze_uncertainty(
        decision_id,
        aleatoric=aleatoric,
        epistemic=epistemic,
    )
    return analysis.to_dict()


def get_confidence_report(tracker_id: str, decision_id: str) -> dict:
    """Get confidence report"""
    tracker = confidence_manager.get_tracker(tracker_id)
    if not tracker:
        return {"error": "Tracker not found"}

    report = tracker.get_confidence_report(decision_id)
    return report or {"error": "Decision not found"}


def get_confidence_trends(tracker_id: str) -> dict:
    """Get confidence trends"""
    tracker = confidence_manager.get_tracker(tracker_id)
    if not tracker:
        return {"error": "Tracker not found"}

    return tracker.get_confidence_trends()


if __name__ == "__main__":
    # Test confidence quantification
    manager = ConfidenceManager()
    tracker = manager.create_tracker("tracker_1")

    # Record decisions
    tracker.record_decision("dec_1", 0.85, 0.9, evidence_count=15)
    tracker.record_decision("dec_2", 0.45, 0.5, evidence_count=3)

    # Add justifications
    tracker.record_justification(
        "dec_1",
        ["Strong supporting evidence", "High data quality"],
        ["Some edge cases not covered"],
        expert_agreement=0.85,
    )

    # Analyze uncertainty
    tracker.analyze_uncertainty(
        "dec_1",
        aleatoric=0.05,
        epistemic=0.02,
        structural=0.03,
    )

    # Report
    report = tracker.get_confidence_report("dec_1")
    print(f"Report: {json.dumps(report, indent=2)}")

    # Trends
    trends = tracker.get_confidence_trends()
    print(f"Trends: {json.dumps(trends, indent=2)}")
