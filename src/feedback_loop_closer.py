"""Feedback integration: apply user corrections to improve responses in real-time"""

import json
from pathlib import Path
from datetime import datetime
from typing import Optional, List, Dict, Any
from dataclasses import dataclass, field
from enum import Enum

FEEDBACK_DIR = Path.home() / ".memory-mcp" / "feedback-loop-closer"
FEEDBACK_DIR.mkdir(exist_ok=True, parents=True)


class CorrectionType(Enum):
    """Type of user correction"""
    FACTUAL = "factual"  # Agent stated wrong fact
    TONE = "tone"  # Response tone was off
    CLARITY = "clarity"  # Unclear or confusing
    COMPLETENESS = "completeness"  # Missing important info
    RELEVANCE = "relevance"  # Not relevant to question
    STYLE = "style"  # Doesn't match user style
    LOGIC = "logic"  # Logical error in reasoning


@dataclass
class UserCorrection:
    """User correction to agent response"""
    correction_id: str
    response_id: str  # What response was corrected
    turn_num: int
    correction_type: CorrectionType
    original_text: str  # What agent said
    correction_text: str  # What user said / wanted
    explanation: str  # Why this is wrong/better
    timestamp: str = ""

    def __post_init__(self):
        if not self.timestamp:
            self.timestamp = datetime.now().isoformat()

    def to_dict(self) -> Dict:
        """Serialize correction"""
        return {
            "correction_id": self.correction_id,
            "type": self.correction_type.value,
            "turn": self.turn_num,
        }


@dataclass
class CorrectionPattern:
    """Learned pattern from corrections"""
    pattern_id: str
    correction_type: CorrectionType
    affected_dimension: str  # What aspect was wrong (clarity, tone, etc.)
    frequency: int  # How many times this pattern occurred
    suggested_fix: str  # General fix for this pattern
    confidence: float  # Confidence in suggested fix (0-1)

    def to_dict(self) -> Dict:
        """Serialize pattern"""
        return {
            "pattern_id": self.pattern_id,
            "type": self.correction_type.value,
            "frequency": self.frequency,
            "confidence": round(self.confidence, 2),
        }


@dataclass
class ResponseImprovement:
    """Improved response based on correction"""
    improvement_id: str
    original_response: str
    corrected_response: str
    corrections_applied: List[str]  # Which corrections influenced this
    quality_increase: float  # Estimated improvement (0-1)
    actually_better: bool = False  # User confirmed it's better

    def to_dict(self) -> Dict:
        """Serialize improvement"""
        return {
            "improvement_id": self.improvement_id,
            "corrections_applied": len(self.corrections_applied),
            "estimated_quality_increase": round(self.quality_increase, 2),
            "confirmed_better": self.actually_better,
        }


class FeedbackAnalyzer:
    """Analyze user corrections to identify patterns"""

    @staticmethod
    def extract_fix_from_correction(
        correction: UserCorrection,
    ) -> Dict[str, str]:
        """Extract actionable fix from correction"""
        fixes = {
            "original": correction.original_text,
            "corrected": correction.correction_text,
            "type": correction.correction_type.value,
            "principle": "",
        }

        # Generate principle based on correction type
        if correction.correction_type == CorrectionType.CLARITY:
            fixes["principle"] = "Simplify language, be more direct, avoid ambiguity"
        elif correction.correction_type == CorrectionType.TONE:
            fixes["principle"] = "Adjust tone to match user preference (formal/casual/empathetic)"
        elif correction.correction_type == CorrectionType.COMPLETENESS:
            fixes["principle"] = "Include all relevant details, cover edge cases"
        elif correction.correction_type == CorrectionType.FACTUAL:
            fixes["principle"] = "Verify facts, use correct terminology, cite sources"
        elif correction.correction_type == CorrectionType.STYLE:
            fixes["principle"] = "Match user communication style (verbose/concise, technical/simple)"
        elif correction.correction_type == CorrectionType.RELEVANCE:
            fixes["principle"] = "Ensure response directly addresses the question asked"
        elif correction.correction_type == CorrectionType.LOGIC:
            fixes["principle"] = "Check logical consistency, avoid fallacies"

        return fixes

    @staticmethod
    def generate_improved_response(
        original: str,
        correction: UserCorrection,
    ) -> str:
        """Generate improved response based on correction"""
        # Simple improvement: use corrected text if available
        if correction.correction_text:
            return correction.correction_text

        # Otherwise, apply principle
        fixes = FeedbackAnalyzer.extract_fix_from_correction(correction)
        principle = fixes["principle"]

        if "Simplify" in principle:
            return original[:100] + "..."  # Truncate as simplification

        return original


class FeedbackLoopCloser:
    """Apply corrections to improve responses"""

    def __init__(self):
        self.corrections: List[UserCorrection] = []
        self.patterns: Dict[CorrectionType, CorrectionPattern] = {}
        self.improvements: Dict[str, ResponseImprovement] = {}
        self.correction_count_by_type: Dict[CorrectionType, int] = {t: 0 for t in CorrectionType}

    def record_correction(
        self,
        response_id: str,
        turn_num: int,
        correction_type: CorrectionType,
        original_text: str,
        correction_text: str,
        explanation: str,
    ) -> UserCorrection:
        """Record user correction"""
        correction = UserCorrection(
            correction_id=f"corr_{len(self.corrections)}",
            response_id=response_id,
            turn_num=turn_num,
            correction_type=correction_type,
            original_text=original_text,
            correction_text=correction_text,
            explanation=explanation,
        )

        self.corrections.append(correction)
        self.correction_count_by_type[correction_type] += 1

        # Update patterns
        self._update_pattern(correction_type)

        return correction

    def _update_pattern(self, correction_type: CorrectionType):
        """Update correction patterns"""
        count = self.correction_count_by_type[correction_type]

        if correction_type not in self.patterns:
            self.patterns[correction_type] = CorrectionPattern(
                pattern_id=f"pat_{correction_type.value}",
                correction_type=correction_type,
                affected_dimension=correction_type.value,
                frequency=count,
                suggested_fix=f"Improve {correction_type.value} in responses",
                confidence=min(1.0, count / 5),  # Confidence grows with frequency
            )
        else:
            pattern = self.patterns[correction_type]
            pattern.frequency = count
            pattern.confidence = min(1.0, count / 5)

    def generate_improved_response(
        self,
        original_response: str,
        relevant_corrections: List[UserCorrection],
    ) -> ResponseImprovement:
        """Generate improved response based on corrections"""
        corrected = original_response

        for correction in relevant_corrections:
            # Apply correction principle
            fixes = FeedbackAnalyzer.extract_fix_from_correction(correction)
            # In real system, would apply NLG transformation here
            corrected = correction.correction_text if correction.correction_text else corrected

        # Estimate quality increase (simple: count of corrections applied)
        quality_increase = min(0.9, len(relevant_corrections) * 0.2)

        improvement = ResponseImprovement(
            improvement_id=f"imp_{len(self.improvements)}",
            original_response=original_response,
            corrected_response=corrected,
            corrections_applied=[c.correction_id for c in relevant_corrections],
            quality_increase=quality_increase,
        )

        self.improvements[improvement.improvement_id] = improvement
        return improvement

    def confirm_improvement(self, improvement_id: str, user_confirmed: bool):
        """Record whether improvement was actually better"""
        if improvement_id in self.improvements:
            self.improvements[improvement_id].actually_better = user_confirmed

    def get_correction_summary(self) -> Dict[str, Any]:
        """Get summary of corrections and patterns learned"""
        confirmed_improvements = [i for i in self.improvements.values() if i.actually_better]

        return {
            "total_corrections": len(self.corrections),
            "corrections_by_type": {
                t.value: self.correction_count_by_type[t] for t in CorrectionType
            },
            "patterns_learned": len(self.patterns),
            "improvements_generated": len(self.improvements),
            "confirmed_improvements": len(confirmed_improvements),
            "improvement_success_rate": (
                len(confirmed_improvements) / len(self.improvements)
                if self.improvements
                else 0
            ),
        }

    def get_top_improvement_areas(self, top_n: int = 3) -> List[Dict]:
        """Get top areas for improvement based on corrections"""
        patterns = sorted(
            self.patterns.values(),
            key=lambda p: p.frequency,
            reverse=True,
        )

        return [
            {
                "type": p.correction_type.value,
                "frequency": p.frequency,
                "suggested_fix": p.suggested_fix,
                "confidence": round(p.confidence, 2),
            }
            for p in patterns[:top_n]
        ]


class FeedbackManager:
    """Manage feedback loop closing across conversations"""

    def __init__(self):
        self.closers: Dict[str, FeedbackLoopCloser] = {}

    def create_closer(self, closer_id: str) -> FeedbackLoopCloser:
        """Create feedback loop closer"""
        closer = FeedbackLoopCloser()
        self.closers[closer_id] = closer
        return closer

    def get_closer(self, closer_id: str) -> Optional[FeedbackLoopCloser]:
        """Get closer"""
        return self.closers.get(closer_id)


feedback_manager = FeedbackManager()


def create_feedback_closer(closer_id: str) -> dict:
    """Create feedback closer"""
    closer = feedback_manager.create_closer(closer_id)
    return {"closer_id": closer_id, "created": True}


def record_correction(
    closer_id: str,
    response_id: str,
    turn_num: int,
    correction_type: str,
    original_text: str,
    correction_text: str,
    explanation: str,
) -> dict:
    """Record correction"""
    closer = feedback_manager.get_closer(closer_id)
    if not closer:
        return {"error": "Closer not found"}

    try:
        ctype = CorrectionType(correction_type)
        correction = closer.record_correction(
            response_id, turn_num, ctype, original_text, correction_text, explanation
        )
        return correction.to_dict()
    except ValueError:
        return {"error": f"Invalid correction type: {correction_type}"}


def generate_improved_response(
    closer_id: str,
    original_response: str,
    relevant_correction_ids: list,
) -> dict:
    """Generate improved response"""
    closer = feedback_manager.get_closer(closer_id)
    if not closer:
        return {"error": "Closer not found"}

    relevant = [c for c in closer.corrections if c.correction_id in relevant_correction_ids]
    improvement = closer.generate_improved_response(original_response, relevant)

    return improvement.to_dict()


def get_correction_summary(closer_id: str) -> dict:
    """Get correction summary"""
    closer = feedback_manager.get_closer(closer_id)
    if not closer:
        return {"error": "Closer not found"}

    return closer.get_correction_summary()


def get_improvement_areas(closer_id: str, top_n: int = 3) -> dict:
    """Get improvement areas"""
    closer = feedback_manager.get_closer(closer_id)
    if not closer:
        return {"error": "Closer not found"}

    areas = closer.get_top_improvement_areas(top_n)
    return {"top_improvement_areas": areas}


if __name__ == "__main__":
    closer = FeedbackLoopCloser()

    correction = closer.record_correction(
        "resp_1",
        1,
        CorrectionType.CLARITY,
        "The implementation of paradigm X necessitates...",
        "Here's how X works in simple terms...",
        "Too complex for audience",
    )

    summary = closer.get_correction_summary()
    print(f"Summary: {json.dumps(summary, indent=2)}")
