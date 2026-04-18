"""Explanation generation: create why/how/what-if explanations with contrastive reasoning"""

import json
from pathlib import Path
from datetime import datetime
from typing import Optional, List, Dict, Any
from dataclasses import dataclass, field
from enum import Enum

EXPLANATION_DIR = Path.home() / ".memory-mcp" / "explanation-generator"
EXPLANATION_DIR.mkdir(exist_ok=True, parents=True)


class ExplanationType(Enum):
    """Type of explanation"""
    WHY = "why"  # Why is this true/happening
    HOW = "how"  # How does it work/happen
    WHAT_IF = "what_if"  # What would happen if
    CONTRAST = "contrast"  # Compare X vs Y
    EXAMPLE = "example"  # Concrete example
    CAUSAL = "causal"  # Cause-effect chain


class ExplanationDepth(Enum):
    """Depth of explanation"""
    SURFACE = "surface"  # One-sentence summary
    MODERATE = "moderate"  # Multi-sentence with details
    DEEP = "deep"  # Full reasoning chain


@dataclass
class ExplanationFactor:
    """Single factor in explanation"""
    factor_id: str
    description: str
    contribution: float  # How much this contributes (0-1)
    evidence: str  # Supporting evidence
    importance: float  # How important to understanding (0-1)

    def to_dict(self) -> Dict:
        """Serialize factor"""
        return {
            "factor_id": self.factor_id,
            "description": self.description,
            "contribution": round(self.contribution, 2),
            "importance": round(self.importance, 2),
        }


@dataclass
class CausalChain:
    """Chain of causation"""
    chain_id: str
    steps: List[str]  # Event1 → Event2 → Event3...
    starting_condition: str
    ending_condition: str
    strength: float  # How strong the causal chain (0-1)

    def to_dict(self) -> Dict:
        """Serialize chain"""
        return {
            "chain_id": self.chain_id,
            "steps": len(self.steps),
            "strength": round(self.strength, 2),
        }


@dataclass
class Explanation:
    """Generated explanation"""
    explanation_id: str
    explanation_type: ExplanationType
    topic: str
    depth: ExplanationDepth
    summary: str  # One-sentence summary
    detailed_text: str  # Full explanation
    factors: List[ExplanationFactor] = field(default_factory=list)
    causal_chain: Optional[CausalChain] = None
    confidence: float = 0.7
    created_at: str = ""

    def __post_init__(self):
        if not self.created_at:
            self.created_at = datetime.now().isoformat()

    def to_dict(self) -> Dict:
        """Serialize explanation"""
        return {
            "explanation_id": self.explanation_id,
            "type": self.explanation_type.value,
            "depth": self.depth.value,
            "factors": len(self.factors),
            "confidence": round(self.confidence, 2),
        }


class ExplanationBuilder:
    """Build explanations with multiple approaches"""

    @staticmethod
    def build_why_explanation(
        topic: str,
        direct_cause: str,
        contributing_factors: List[str],
    ) -> str:
        """Build 'why' explanation"""
        explanation = f"{topic} because {direct_cause}."

        if contributing_factors:
            explanation += f" Contributing factors: {', '.join(contributing_factors[:2])}."

        return explanation

    @staticmethod
    def build_how_explanation(
        topic: str,
        steps: List[str],
    ) -> str:
        """Build 'how' explanation"""
        explanation = f"Here's how {topic} works:\n"

        for i, step in enumerate(steps, 1):
            explanation += f"{i}. {step}\n"

        return explanation.strip()

    @staticmethod
    def build_what_if_explanation(
        condition: str,
        consequence: str,
        alternative: Optional[str] = None,
    ) -> str:
        """Build 'what if' explanation"""
        explanation = f"If {condition}, then {consequence}."

        if alternative:
            explanation += f" Otherwise, {alternative}."

        return explanation

    @staticmethod
    def build_contrast_explanation(
        item_a: str,
        item_b: str,
        similarities: List[str],
        differences: List[str],
    ) -> str:
        """Build contrastive explanation"""
        explanation = f"Comparing {item_a} and {item_b}:\n"

        explanation += f"Similarities: {', '.join(similarities[:2])}\n"
        explanation += f"Differences: {', '.join(differences[:2])}"

        return explanation.strip()

    @staticmethod
    def build_causal_chain(
        start: str,
        steps: List[str],
        end: str,
    ) -> CausalChain:
        """Build causal chain"""
        chain_steps = [start] + steps + [end]

        return CausalChain(
            chain_id="chain_0",
            steps=chain_steps,
            starting_condition=start,
            ending_condition=end,
            strength=0.7,  # Default strength
        )


class ExplanationGenerator:
    """Generate explanations on demand"""

    def __init__(self):
        self.explanations: Dict[str, Explanation] = {}

    def generate_explanation(
        self,
        explanation_type: ExplanationType,
        topic: str,
        depth: ExplanationDepth,
        context_data: Dict[str, Any],
    ) -> Explanation:
        """Generate explanation of given type"""
        summary = ""
        detailed_text = ""

        if explanation_type == ExplanationType.WHY:
            direct_cause = context_data.get("direct_cause", "complex factors")
            factors = context_data.get("factors", [])
            summary = f"Because {direct_cause}"
            detailed_text = ExplanationBuilder.build_why_explanation(topic, direct_cause, factors)

        elif explanation_type == ExplanationType.HOW:
            steps = context_data.get("steps", [])
            summary = f"{topic} involves {len(steps)} key steps"
            detailed_text = ExplanationBuilder.build_how_explanation(topic, steps)

        elif explanation_type == ExplanationType.WHAT_IF:
            condition = context_data.get("condition", "X occurs")
            consequence = context_data.get("consequence", "Y happens")
            alternative = context_data.get("alternative")
            summary = f"If {condition}, then {consequence}"
            detailed_text = ExplanationBuilder.build_what_if_explanation(condition, consequence, alternative)

        elif explanation_type == ExplanationType.CONTRAST:
            item_a = context_data.get("item_a", "A")
            item_b = context_data.get("item_b", "B")
            similarities = context_data.get("similarities", [])
            differences = context_data.get("differences", [])
            summary = f"Comparing {item_a} and {item_b}"
            detailed_text = ExplanationBuilder.build_contrast_explanation(item_a, item_b, similarities, differences)

        elif explanation_type == ExplanationType.CAUSAL:
            start = context_data.get("start", "initial condition")
            steps = context_data.get("steps", [])
            end = context_data.get("end", "final result")
            summary = "Causal chain from cause to effect"
            detailed_text = f"{' → '.join([start] + steps + [end])}"

        else:  # EXAMPLE
            example = context_data.get("example", "instance")
            summary = f"Example: {example}"
            detailed_text = f"Here's a concrete example: {example}"

        explanation = Explanation(
            explanation_id=f"exp_{len(self.explanations)}",
            explanation_type=explanation_type,
            topic=topic,
            depth=depth,
            summary=summary,
            detailed_text=detailed_text,
            confidence=0.7,
        )

        self.explanations[explanation.explanation_id] = explanation
        return explanation

    def get_explanation(self, explanation_id: str) -> Optional[Dict]:
        """Get explanation by ID"""
        if explanation_id not in self.explanations:
            return None

        exp = self.explanations[explanation_id]
        return {
            "explanation_id": exp.explanation_id,
            "type": exp.explanation_type.value,
            "topic": exp.topic,
            "summary": exp.summary,
            "detailed": exp.detailed_text,
            "depth": exp.depth.value,
        }


class ExplanationManager:
    """Manage explanation generation across conversations"""

    def __init__(self):
        self.generators: Dict[str, ExplanationGenerator] = {}

    def create_generator(self, generator_id: str) -> ExplanationGenerator:
        """Create generator"""
        generator = ExplanationGenerator()
        self.generators[generator_id] = generator
        return generator

    def get_generator(self, generator_id: str) -> Optional[ExplanationGenerator]:
        """Get generator"""
        return self.generators.get(generator_id)


explanation_manager = ExplanationManager()


def create_explanation_generator(generator_id: str) -> dict:
    """Create explanation generator"""
    generator = explanation_manager.create_generator(generator_id)
    return {"generator_id": generator_id, "created": True}


def generate_explanation(
    generator_id: str,
    explanation_type: str,
    topic: str,
    depth: str,
    context_data: dict,
) -> dict:
    """Generate explanation"""
    generator = explanation_manager.get_generator(generator_id)
    if not generator:
        return {"error": "Generator not found"}

    try:
        etype = ExplanationType(explanation_type)
        edepth = ExplanationDepth(depth)
        explanation = generator.generate_explanation(etype, topic, edepth, context_data)
        return explanation.to_dict()
    except ValueError as e:
        return {"error": str(e)}


def get_explanation(generator_id: str, explanation_id: str) -> dict:
    """Get explanation"""
    generator = explanation_manager.get_generator(generator_id)
    if not generator:
        return {"error": "Generator not found"}

    exp = generator.get_explanation(explanation_id)
    return exp or {"error": "Explanation not found"}


if __name__ == "__main__":
    generator = ExplanationGenerator()

    exp = generator.generate_explanation(
        ExplanationType.HOW,
        "photosynthesis",
        ExplanationDepth.MODERATE,
        {
            "steps": [
                "Plants absorb light energy from sun",
                "Light energy splits water molecules",
                "Creates glucose and oxygen",
            ]
        },
    )

    print(f"Summary: {exp.summary}")
    print(f"Detailed: {exp.detailed_text}")
