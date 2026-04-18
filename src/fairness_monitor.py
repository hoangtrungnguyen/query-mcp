"""Fairness monitoring: detect systematic biases in response ranking, adaptation, and attention allocation"""

import json
from pathlib import Path
from datetime import datetime
from typing import Optional, List, Dict, Any
from dataclasses import dataclass, field
from enum import Enum

FAIRNESS_DIR = Path.home() / ".memory-mcp" / "fairness-monitor"
FAIRNESS_DIR.mkdir(exist_ok=True, parents=True)


class BiasType(Enum):
    """Type of detected bias"""
    RANKING_BIAS = "ranking_bias"  # Systematically ranking certain responses higher
    ADAPTATION_BIAS = "adaptation_bias"  # Adapting differently to similar users
    ATTENTION_BIAS = "attention_bias"  # Spending more/less time on certain users
    STYLE_BIAS = "style_bias"  # Preferring certain communication styles
    DOMAIN_BIAS = "domain_bias"  # Biased toward/against certain domains


class BiasDirection(Enum):
    """Direction of bias"""
    FAVORING = "favoring"  # Unfairly favoring group A
    DISADVANTAGING = "disadvantaging"  # Unfairly disadvantaging group B
    NEUTRAL = "neutral"  # No bias detected


@dataclass
class UserSegment:
    """Group of users for fairness comparison"""
    segment_id: str
    segment_name: str  # "experienced", "beginner", "domain_X", etc.
    user_ids: List[str]
    size: int  # Number of users

    def to_dict(self) -> Dict:
        """Serialize segment"""
        return {
            "segment_id": self.segment_id,
            "segment_name": self.segment_name,
            "size": self.size,
        }


@dataclass
class FairnessMetric:
    """Fairness metric comparing two groups"""
    metric_id: str
    metric_type: BiasType
    segment_a: str
    segment_b: str
    value_a: float  # Metric value for segment A
    value_b: float  # Metric value for segment B
    difference: float  # Absolute difference
    disparity_ratio: float  # value_a / value_b (>1 = disparity)
    significance: float  # Statistical significance (0-1)
    timestamp: str = ""

    def __post_init__(self):
        if not self.timestamp:
            self.timestamp = datetime.now().isoformat()

    def to_dict(self) -> Dict:
        """Serialize metric"""
        return {
            "metric_id": self.metric_id,
            "type": self.metric_type.value,
            "segment_a": self.segment_a,
            "segment_b": self.segment_b,
            "difference": round(self.difference, 2),
            "disparity_ratio": round(self.disparity_ratio, 2),
        }


@dataclass
class BiasAlert:
    """Alert for detected bias"""
    alert_id: str
    bias_type: BiasType
    bias_direction: BiasDirection
    affected_segments: List[str]
    severity: float  # 0-1, how severe
    evidence: List[str]
    recommended_actions: List[str]
    detected_at: str = ""

    def __post_init__(self):
        if not self.detected_at:
            self.detected_at = datetime.now().isoformat()

    def to_dict(self) -> Dict:
        """Serialize alert"""
        return {
            "alert_id": self.alert_id,
            "bias_type": self.bias_type.value,
            "direction": self.bias_direction.value,
            "severity": round(self.severity, 2),
            "affected_segments": len(self.affected_segments),
        }


class FairnessAnalyzer:
    """Analyze fairness metrics"""

    @staticmethod
    def calculate_disparity_ratio(value_a: float, value_b: float) -> float:
        """Calculate disparity ratio (value_a / value_b)"""
        if value_b == 0:
            return 1.0
        return value_a / value_b

    @staticmethod
    def assess_disparity_severity(ratio: float) -> tuple:
        """Assess severity of disparity"""
        if 0.8 <= ratio <= 1.25:
            return BiasDirection.NEUTRAL, 0.0

        if ratio < 0.8:
            return BiasDirection.DISADVANTAGING, 1 - ratio
        else:
            return BiasDirection.FAVORING, ratio - 1

    @staticmethod
    def estimate_significance(sample_size_a: int, sample_size_b: int) -> float:
        """Estimate statistical significance from sample sizes"""
        avg_size = (sample_size_a + sample_size_b) / 2
        if avg_size < 10:
            return 0.2
        elif avg_size < 30:
            return 0.5
        elif avg_size < 100:
            return 0.7
        else:
            return 0.9


class FairnessMonitor:
    """Monitor fairness across conversations and users"""

    def __init__(self):
        self.segments: Dict[str, UserSegment] = {}
        self.metrics: Dict[str, FairnessMetric] = {}
        self.alerts: Dict[str, BiasAlert] = {}

    def register_segment(
        self,
        segment_name: str,
        user_ids: List[str],
    ) -> UserSegment:
        """Register user segment for fairness analysis"""
        segment = UserSegment(
            segment_id=f"seg_{len(self.segments)}",
            segment_name=segment_name,
            user_ids=user_ids,
            size=len(user_ids),
        )
        self.segments[segment.segment_id] = segment
        return segment

    def compare_groups(
        self,
        metric_type: BiasType,
        segment_a_id: str,
        segment_b_id: str,
        value_a: float,
        value_b: float,
        sample_size_a: int = 30,
        sample_size_b: int = 30,
    ) -> FairnessMetric:
        """Compare fairness metric between two groups"""
        disparity_ratio = FairnessAnalyzer.calculate_disparity_ratio(value_a, value_b)
        significance = FairnessAnalyzer.estimate_significance(sample_size_a, sample_size_b)

        metric = FairnessMetric(
            metric_id=f"metric_{len(self.metrics)}",
            metric_type=metric_type,
            segment_a=segment_a_id,
            segment_b=segment_b_id,
            value_a=value_a,
            value_b=value_b,
            difference=abs(value_a - value_b),
            disparity_ratio=disparity_ratio,
            significance=significance,
        )

        self.metrics[metric.metric_id] = metric

        direction, severity = FairnessAnalyzer.assess_disparity_severity(disparity_ratio)
        if direction != BiasDirection.NEUTRAL and severity > 0.1:
            self._raise_bias_alert(metric_type, direction, severity, [segment_a_id, segment_b_id])

        return metric

    def _raise_bias_alert(
        self,
        bias_type: BiasType,
        direction: BiasDirection,
        severity: float,
        affected_segments: List[str],
    ):
        """Raise alert for detected bias"""
        evidence = []
        if bias_type == BiasType.RANKING_BIAS:
            evidence.append("Response ranking shows disparity between groups")
        elif bias_type == BiasType.ADAPTATION_BIAS:
            evidence.append("Different adaptation rates observed")
        elif bias_type == BiasType.ATTENTION_BIAS:
            evidence.append("Attention/engagement varies by group")

        actions = [
            "Investigate root cause of disparity",
            "Review decision logic for fairness",
            "Collect more data to confirm trend",
        ]

        alert = BiasAlert(
            alert_id=f"alert_{len(self.alerts)}",
            bias_type=bias_type,
            bias_direction=direction,
            affected_segments=affected_segments,
            severity=severity,
            evidence=evidence,
            recommended_actions=actions,
        )

        self.alerts[alert.alert_id] = alert

    def get_fairness_report(self) -> Dict[str, Any]:
        """Get comprehensive fairness report"""
        if not self.metrics:
            return {"metrics": 0, "alerts": 0}

        by_type = {}
        biased = 0

        for metric in self.metrics.values():
            mtype = metric.metric_type.value
            if mtype not in by_type:
                by_type[mtype] = 0
            by_type[mtype] += 1

            if not (0.8 <= metric.disparity_ratio <= 1.25):
                biased += 1

        return {
            "total_metrics": len(self.metrics),
            "metrics_by_type": by_type,
            "biased_metrics": biased,
            "total_alerts": len(self.alerts),
            "active_alerts": len([a for a in self.alerts.values()]),
        }


class FairnessManager:
    """Manage fairness monitoring across system"""

    def __init__(self):
        self.monitors: Dict[str, FairnessMonitor] = {}

    def create_monitor(self, monitor_id: str) -> FairnessMonitor:
        """Create fairness monitor"""
        monitor = FairnessMonitor()
        self.monitors[monitor_id] = monitor
        return monitor

    def get_monitor(self, monitor_id: str) -> Optional[FairnessMonitor]:
        """Get monitor"""
        return self.monitors.get(monitor_id)


fairness_manager = FairnessManager()


def create_fairness_monitor(monitor_id: str) -> dict:
    """Create fairness monitor"""
    monitor = fairness_manager.create_monitor(monitor_id)
    return {"monitor_id": monitor_id, "created": True}


def register_segment(monitor_id: str, segment_name: str, user_ids: list) -> dict:
    """Register user segment"""
    monitor = fairness_manager.get_monitor(monitor_id)
    if not monitor:
        return {"error": "Monitor not found"}

    segment = monitor.register_segment(segment_name, user_ids)
    return segment.to_dict()


def compare_groups(
    monitor_id: str,
    metric_type: str,
    segment_a_id: str,
    segment_b_id: str,
    value_a: float,
    value_b: float,
    sample_size_a: int = 30,
    sample_size_b: int = 30,
) -> dict:
    """Compare groups for fairness"""
    monitor = fairness_manager.get_monitor(monitor_id)
    if not monitor:
        return {"error": "Monitor not found"}

    try:
        mtype = BiasType(metric_type)
        metric = monitor.compare_groups(
            mtype, segment_a_id, segment_b_id, value_a, value_b, sample_size_a, sample_size_b
        )
        return metric.to_dict()
    except ValueError:
        return {"error": f"Invalid metric type: {metric_type}"}


def get_fairness_report(monitor_id: str) -> dict:
    """Get fairness report"""
    monitor = fairness_manager.get_monitor(monitor_id)
    if not monitor:
        return {"error": "Monitor not found"}

    return monitor.get_fairness_report()


if __name__ == "__main__":
    monitor = FairnessMonitor()

    monitor.register_segment("experienced", ["user_1", "user_2", "user_3"])
    monitor.register_segment("beginner", ["user_4", "user_5", "user_6"])

    metric = monitor.compare_groups(
        BiasType.RANKING_BIAS,
        "experienced",
        "beginner",
        0.75,
        0.65,
    )

    report = monitor.get_fairness_report()
    print(f"Report: {json.dumps(report, indent=2)}")
