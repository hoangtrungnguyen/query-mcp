"""Ethical reasoning and value alignment"""

import json
from pathlib import Path
from datetime import datetime
from typing import Optional, List, Dict, Any
from dataclasses import dataclass, field
from enum import Enum

ETHICS_DIR = Path.home() / ".memory-mcp" / "ethical-reasoning"
ETHICS_DIR.mkdir(exist_ok=True, parents=True)


class EthicalPrinciple(Enum):
    """Core ethical principles"""
    AUTONOMY = "autonomy"  # Respect for individuals' choices
    BENEFICENCE = "beneficence"  # Do good
    NON_MALEFICENCE = "non_maleficence"  # Avoid harm
    JUSTICE = "justice"  # Fair distribution
    TRANSPARENCY = "transparency"  # Honesty and openness
    ACCOUNTABILITY = "accountability"  # Taking responsibility


class FairnessMetric(Enum):
    """Fairness evaluation metrics"""
    DEMOGRAPHIC_PARITY = "demographic_parity"  # Same outcomes across groups
    EQUAL_OPPORTUNITY = "equal_opportunity"  # Same opportunities
    PREDICTIVE_PARITY = "predictive_parity"  # Accuracy across groups
    CALIBRATION = "calibration"  # Prediction confidence across groups
    INDIVIDUAL_FAIRNESS = "individual_fairness"  # Similar treatment for similar cases


class StakeholderType(Enum):
    """Types of stakeholders"""
    USER = "user"
    ORGANIZATION = "organization"
    PUBLIC = "public"
    VULNERABLE_GROUP = "vulnerable_group"
    REGULATOR = "regulator"


@dataclass
class EthicalValue:
    """Ethical value or principle"""
    value_id: str
    principle: EthicalPrinciple
    description: str
    importance: float  # 0-1
    constraints: List[str] = field(default_factory=list)
    created_at: str = ""

    def __post_init__(self):
        if not self.created_at:
            self.created_at = datetime.now().isoformat()

    def to_dict(self) -> Dict:
        """Serialize value"""
        return {
            "value_id": self.value_id,
            "principle": self.principle.value,
            "importance": self.importance,
            "constraints": len(self.constraints),
        }


@dataclass
class StakeholderImpact:
    """Impact on stakeholder group"""
    stakeholder_type: StakeholderType
    description: str
    benefited: bool  # Does this help them?
    harm_risk: float  # 0-1, risk of harm
    unfairness_risk: float  # 0-1, risk of unfair treatment
    burden: float  # 0-1, burden imposed
    concerns: List[str] = field(default_factory=list)

    def to_dict(self) -> Dict:
        """Serialize impact"""
        return {
            "stakeholder": self.stakeholder_type.value,
            "benefited": self.benefited,
            "harm_risk": round(self.harm_risk, 2),
            "unfairness_risk": round(self.unfairness_risk, 2),
            "burden": round(self.burden, 2),
            "concerns": len(self.concerns),
        }


@dataclass
class EthicalDilemma:
    """Situation with ethical tensions"""
    dilemma_id: str
    description: str
    conflicting_values: List[EthicalPrinciple]  # Which values conflict
    stakeholder_impacts: List[StakeholderImpact] = field(default_factory=list)
    options: List[Dict[str, Any]] = field(default_factory=list)  # Different choices
    tradeoffs: List[str] = field(default_factory=list)  # What's being traded
    created_at: str = ""

    def __post_init__(self):
        if not self.created_at:
            self.created_at = datetime.now().isoformat()

    def to_dict(self) -> Dict:
        """Serialize dilemma"""
        return {
            "dilemma_id": self.dilemma_id,
            "conflicting_values": [v.value for v in self.conflicting_values],
            "stakeholder_count": len(self.stakeholder_impacts),
            "options": len(self.options),
            "tradeoffs": len(self.tradeoffs),
        }


@dataclass
class FairnessAnalysis:
    """Analysis of fairness aspects"""
    analysis_id: str
    decision_id: str
    metrics_evaluated: List[FairnessMetric] = field(default_factory=list)
    disparities_found: List[Dict[str, Any]] = field(default_factory=list)
    fairness_score: float = 0.5  # 0-1, higher = fairer
    vulnerable_groups_affected: List[str] = field(default_factory=list)
    recommendations: List[str] = field(default_factory=list)
    created_at: str = ""

    def __post_init__(self):
        if not self.created_at:
            self.created_at = datetime.now().isoformat()

    def to_dict(self) -> Dict:
        """Serialize analysis"""
        return {
            "analysis_id": self.analysis_id,
            "metrics_evaluated": len(self.metrics_evaluated),
            "disparities": len(self.disparities_found),
            "fairness_score": round(self.fairness_score, 2),
            "vulnerable_groups": len(self.vulnerable_groups_affected),
            "recommendations": len(self.recommendations),
        }


@dataclass
class EthicalDecision:
    """Decision made with ethical reasoning"""
    decision_id: str
    action: str
    ethical_justification: str
    values_considered: List[EthicalPrinciple] = field(default_factory=list)
    dilemma_resolved: Optional[str] = None  # dilemma_id
    fairness_analysis: Optional[FairnessAnalysis] = None
    risks_identified: List[str] = field(default_factory=list)
    mitigations: List[str] = field(default_factory=list)
    created_at: str = ""

    def __post_init__(self):
        if not self.created_at:
            self.created_at = datetime.now().isoformat()

    def to_dict(self) -> Dict:
        """Serialize decision"""
        return {
            "decision_id": self.decision_id,
            "action": self.action[:100],
            "values_considered": [v.value for v in self.values_considered],
            "risks": len(self.risks_identified),
            "mitigations": len(self.mitigations),
        }


class EthicalAnalyzer:
    """Analyze ethical aspects of decisions"""

    @staticmethod
    def analyze_fairness(
        groups_affected: Dict[str, Dict[str, Any]],
        metrics: List[FairnessMetric],
    ) -> FairnessAnalysis:
        """Analyze fairness across groups"""
        disparities = []

        # Check demographic parity
        if FairnessMetric.DEMOGRAPHIC_PARITY in metrics:
            outcomes = {g: d.get("outcome", 0) for g, d in groups_affected.items()}
            outcome_values = list(outcomes.values())
            if outcome_values:
                avg_outcome = sum(outcome_values) / len(outcome_values)
                for group, outcome in outcomes.items():
                    if abs(outcome - avg_outcome) > 0.2:  # >20% difference
                        disparities.append({
                            "group": group,
                            "metric": "demographic_parity",
                            "disparity": abs(outcome - avg_outcome),
                        })

        # Identify vulnerable groups
        vulnerable = [
            group for group, data in groups_affected.items()
            if data.get("vulnerable", False)
        ]

        # Calculate fairness score
        fairness_score = max(0, 1.0 - (len(disparities) * 0.1))

        analysis = FairnessAnalysis(
            analysis_id=f"fair_{int(datetime.now().timestamp())}",
            decision_id="",
            metrics_evaluated=metrics,
            disparities_found=disparities,
            fairness_score=fairness_score,
            vulnerable_groups_affected=vulnerable,
        )

        # Recommendations
        if disparities:
            analysis.recommendations.append("Review and mitigate identified disparities")
        if vulnerable:
            analysis.recommendations.append("Extra care for vulnerable groups")

        return analysis

    @staticmethod
    def identify_ethical_conflicts(
        action: str,
        principles: List[EthicalPrinciple],
    ) -> List[EthicalPrinciple]:
        """Identify conflicting ethical principles"""
        conflicts = []

        # Some principles inherently conflict
        if EthicalPrinciple.AUTONOMY in principles and EthicalPrinciple.BENEFICENCE in principles:
            # Paternalistic action might conflict
            conflicts.append(EthicalPrinciple.AUTONOMY)

        if EthicalPrinciple.TRANSPARENCY in principles and EthicalPrinciple.PRIVACY in principles if hasattr(EthicalPrinciple, 'PRIVACY') else []:
            conflicts.append(EthicalPrinciple.TRANSPARENCY)

        return conflicts

    @staticmethod
    def assess_harm_risk(
        action: str,
        vulnerable_groups: List[str],
    ) -> float:
        """Assess risk of harm"""
        harm_keywords = ["remove", "exclude", "terminate", "deny", "restrict"]

        harm_risk = 0.0
        for keyword in harm_keywords:
            if keyword in action.lower():
                harm_risk += 0.2

        # Increase if vulnerable groups affected
        if vulnerable_groups:
            harm_risk += 0.1 * len(vulnerable_groups)

        return min(1.0, harm_risk)


class EthicsFramework:
    """Ethical reasoning framework"""

    def __init__(self):
        self.values: Dict[str, EthicalValue] = {}
        self.dilemmas: Dict[str, EthicalDilemma] = {}
        self.decisions: Dict[str, EthicalDecision] = {}
        self.fairness_analyses: Dict[str, FairnessAnalysis] = {}

    def register_value(
        self,
        value_id: str,
        principle: EthicalPrinciple,
        description: str,
        importance: float = 0.8,
    ) -> EthicalValue:
        """Register ethical value"""
        value = EthicalValue(
            value_id=value_id,
            principle=principle,
            description=description,
            importance=importance,
        )
        self.values[value_id] = value
        return value

    def identify_dilemma(
        self,
        dilemma_id: str,
        description: str,
        values: List[EthicalPrinciple],
        stakeholder_impacts: List[StakeholderImpact],
    ) -> EthicalDilemma:
        """Identify ethical dilemma"""
        dilemma = EthicalDilemma(
            dilemma_id=dilemma_id,
            description=description,
            conflicting_values=values,
            stakeholder_impacts=stakeholder_impacts,
        )
        self.dilemmas[dilemma_id] = dilemma
        return dilemma

    def make_ethical_decision(
        self,
        decision_id: str,
        action: str,
        principles_considered: List[EthicalPrinciple],
        justification: str,
    ) -> EthicalDecision:
        """Make decision with ethical reasoning"""
        decision = EthicalDecision(
            decision_id=decision_id,
            action=action,
            ethical_justification=justification,
            values_considered=principles_considered,
        )

        # Assess harm risk
        harm_risk = EthicsFramyzer.assess_harm_risk(action, [])
        if harm_risk > 0.3:
            decision.risks_identified.append(f"Potential harm (risk: {harm_risk:.2f})")
            decision.mitigations.append("Implement safeguards")

        self.decisions[decision_id] = decision
        return decision

    def get_ethical_guidelines(self) -> Dict[str, Any]:
        """Get current ethical guidelines"""
        total_importance = sum(v.importance for v in self.values.values())

        return {
            "values_registered": len(self.values),
            "principles": [v.principle.value for v in self.values.values()],
            "total_importance": round(total_importance, 2),
            "dilemmas_identified": len(self.dilemmas),
            "decisions_made": len(self.decisions),
        }


class EthicsManager:
    """Manage ethical reasoning across systems"""

    def __init__(self):
        self.frameworks: Dict[str, EthicsFramework] = {}

    def create_framework(self, framework_id: str) -> EthicsFramework:
        """Create ethics framework"""
        framework = EthicsFramework()
        self.frameworks[framework_id] = framework
        return framework

    def get_framework(self, framework_id: str) -> Optional[EthicsFramework]:
        """Get framework"""
        return self.frameworks.get(framework_id)


# Global manager
ethics_manager = EthicsManager()


# MCP Tools

def create_ethics_framework(framework_id: str) -> dict:
    """Create ethical reasoning framework"""
    framework = ethics_manager.create_framework(framework_id)
    return {"framework_id": framework_id, "created": True}


def register_ethical_value(
    framework_id: str,
    value_id: str,
    principle: str,
    description: str,
    importance: float = 0.8,
) -> dict:
    """Register ethical value"""
    framework = ethics_manager.get_framework(framework_id)
    if not framework:
        return {"error": "Framework not found"}

    value = framework.register_value(
        value_id,
        EthicalPrinciple(principle),
        description,
        importance,
    )
    return value.to_dict()


def identify_ethical_dilemma(
    framework_id: str,
    dilemma_id: str,
    description: str,
    conflicting_principles: list,
) -> dict:
    """Identify ethical dilemma"""
    framework = ethics_manager.get_framework(framework_id)
    if not framework:
        return {"error": "Framework not found"}

    dilemma = framework.identify_dilemma(
        dilemma_id,
        description,
        [EthicalPrinciple(p) for p in conflicting_principles],
        [],
    )
    return dilemma.to_dict()


def make_ethical_decision(
    framework_id: str,
    decision_id: str,
    action: str,
    principles: list,
    justification: str,
) -> dict:
    """Make ethical decision"""
    framework = ethics_manager.get_framework(framework_id)
    if not framework:
        return {"error": "Framework not found"}

    decision = framework.make_ethical_decision(
        decision_id,
        action,
        [EthicalPrinciple(p) for p in principles],
        justification,
    )
    return decision.to_dict()


def analyze_fairness(
    framework_id: str,
    groups_affected: dict,
    metrics: list,
) -> dict:
    """Analyze fairness"""
    analysis = EthicalAnalyzer.analyze_fairness(groups_affected, [FairnessMetric(m) for m in metrics])
    return analysis.to_dict()


def get_ethical_guidelines(framework_id: str) -> dict:
    """Get ethical guidelines"""
    framework = ethics_manager.get_framework(framework_id)
    if not framework:
        return {"error": "Framework not found"}

    return framework.get_ethical_guidelines()


if __name__ == "__main__":
    # Test ethical reasoning
    framework = EthicsFramework()

    # Register values
    framework.register_value(
        "val_1",
        EthicalPrinciple.AUTONOMY,
        "Users should control their own data",
        0.9,
    )
    framework.register_value(
        "val_2",
        EthicalPrinciple.BENEFICENCE,
        "Systems should benefit users",
        0.85,
    )

    # Identify dilemma
    dilemma = framework.identify_dilemma(
        "dilemma_1",
        "Personalization vs Privacy",
        [EthicalPrinciple.AUTONOMY, EthicalPrinciple.BENEFICENCE],
        [
            StakeholderImpact(
                stakeholder_type=StakeholderType.USER,
                description="Improved experience but reduced privacy",
                benefited=True,
                harm_risk=0.3,
                unfairness_risk=0.0,
                burden=0.2,
            )
        ],
    )
    print(f"Dilemma: {dilemma.dilemma_id}")

    # Make decision
    decision = framework.make_ethical_decision(
        "dec_1",
        "Collect user behavioral data with explicit consent",
        [EthicalPrinciple.AUTONOMY, EthicalPrinciple.TRANSPARENCY],
        "Users can opt-in and control their data",
    )
    print(f"Decision: {decision.action}")

    # Guidelines
    guidelines = framework.get_ethical_guidelines()
    print(f"Guidelines: {json.dumps(guidelines, indent=2)}")
