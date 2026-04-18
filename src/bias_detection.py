"""Bias detection and fairness assurance"""

import json
from pathlib import Path
from datetime import datetime
from typing import Optional, List, Dict, Any
from dataclasses import dataclass, field

BIAS_DIR = Path.home() / ".memory-mcp" / "bias-detection"
BIAS_DIR.mkdir(exist_ok=True, parents=True)


@dataclass
class BiasAlert:
    """Detected bias in response"""
    alert_id: str
    bias_type: str
    severity: float  # 0-1
    description: str
    affected_groups: List[str] = field(default_factory=list)
    mitigation: str = ""
    created_at: str = ""

    def __post_init__(self):
        if not self.created_at:
            self.created_at = datetime.now().isoformat()

    def to_dict(self) -> Dict:
        return {
            "bias_type": self.bias_type,
            "severity": round(self.severity, 2),
            "affected_groups": len(self.affected_groups),
            "mitigation": self.mitigation[:100],
        }


class BiasDetector:
    """Detect bias in responses"""

    BIAS_KEYWORDS = {
        "gender": ["he", "she", "man", "woman", "male", "female"],
        "age": ["young", "old", "elderly", "millennial"],
        "ethnicity": ["african", "asian", "european", "latino"],
        "ability": ["disabled", "normal", "healthy"],
    }

    def __init__(self):
        self.detected_biases: List[BiasAlert] = []

    def analyze_response(
        self,
        response: str,
        context: Dict[str, Any],
    ) -> List[BiasAlert]:
        """Analyze response for bias"""
        alerts = []

        response_lower = response.lower()

        # Check for gendered language
        male_refs = sum(1 for word in ["he", "man", "his"] if word in response_lower)
        female_refs = sum(1 for word in ["she", "woman", "her"] if word in response_lower)

        if male_refs > 3 or female_refs > 3:
            ratio = max(male_refs, female_refs) / (male_refs + female_refs + 1)
            if ratio > 0.7:
                alert = BiasAlert(
                    alert_id=f"bias_gender_{len(alerts)}",
                    bias_type="gender_bias",
                    severity=0.6 if ratio > 0.8 else 0.3,
                    description="Overuse of gendered language",
                    affected_groups=["gender minorities"],
                    mitigation="Use neutral pronouns or 'they/them'",
                )
                alerts.append(alert)

        # Check for age bias
        age_words = ["old", "elderly", "young"]
        age_count = sum(1 for word in age_words if word in response_lower)
        if age_count > 2:
            alert = BiasAlert(
                alert_id=f"bias_age_{len(alerts)}",
                bias_type="age_bias",
                severity=0.4,
                description="Language assumes specific age group",
                affected_groups=["older adults", "youth"],
                mitigation="Use age-neutral language",
            )
            alerts.append(alert)

        # Check for ability bias
        ability_words = ["disabled", "normal", "healthy"]
        ability_count = sum(1 for word in ability_words if word in response_lower)
        if ability_count > 1:
            alert = BiasAlert(
                alert_id=f"bias_ability_{len(alerts)}",
                bias_type="ability_bias",
                severity=0.5,
                description="Language assumes ability status",
                affected_groups=["people with disabilities"],
                mitigation="Use person-first or identity-first language appropriately",
            )
            alerts.append(alert)

        self.detected_biases.extend(alerts)
        return alerts


class FairnessAssurance:
    """Ensure fairness in responses"""

    def __init__(self):
        self.bias_detector = BiasDetector()
        self.fairness_score = 1.0

    def evaluate_response(
        self,
        response: str,
        context: Dict[str, Any],
    ) -> Dict:
        """Evaluate response for fairness"""
        alerts = self.bias_detector.analyze_response(response, context)

        # Calculate fairness score
        if alerts:
            avg_severity = sum(a.severity for a in alerts) / len(alerts)
            fairness_score = 1.0 - (avg_severity * 0.5)
        else:
            fairness_score = 1.0

        return {
            "fairness_score": round(fairness_score, 2),
            "biases_detected": len(alerts),
            "alerts": [a.to_dict() for a in alerts],
            "status": "fair" if fairness_score > 0.8 else "needs_review",
        }

    def mitigate_bias(
        self,
        response: str,
        alerts: List[BiasAlert],
    ) -> str:
        """Apply bias mitigations"""
        mitigated = response

        for alert in alerts:
            if alert.bias_type == "gender_bias":
                # Replace gendered pronouns
                mitigated = mitigated.replace(" he ", " they ")
                mitigated = mitigated.replace(" she ", " they ")

            elif alert.bias_type == "age_bias":
                # Remove age assumptions
                mitigated = mitigated.replace("old", "experienced")
                mitigated = mitigated.replace("young", "newer")

        return mitigated


# Global engine
fairness_engine = FairnessAssurance()


def evaluate_response_fairness(response: str, context: dict = None) -> dict:
    """Evaluate response fairness"""
    return fairness_engine.evaluate_response(response, context or {})


def mitigate_bias(response: str, alerts: list) -> dict:
    """Mitigate detected biases"""
    alert_objs = [
        BiasAlert(
            alert_id=a.get("alert_id", ""),
            bias_type=a.get("bias_type", ""),
            severity=a.get("severity", 0.5),
            description=a.get("description", ""),
        )
        for a in alerts
    ]
    mitigated = fairness_engine.mitigate_bias(response, alert_objs)
    return {"mitigated_response": mitigated}
