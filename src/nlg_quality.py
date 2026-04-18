"""Natural language generation quality optimization"""

import json
from pathlib import Path
from datetime import datetime
from typing import Optional, List, Dict, Any
from dataclasses import dataclass, field

NLG_DIR = Path.home() / ".memory-mcp" / "nlg-quality"
NLG_DIR.mkdir(exist_ok=True, parents=True)


@dataclass
class QualityMetric:
    """NLG quality metric"""
    metric_name: str
    score: float  # 0-1
    description: str
    suggestions: List[str] = field(default_factory=list)

    def to_dict(self) -> Dict:
        return {
            "metric": self.metric_name,
            "score": round(self.score, 2),
            "suggestions": len(self.suggestions),
        }


class NLGQualityAnalyzer:
    """Analyze NLG quality"""

    def __init__(self):
        self.analyses: Dict[str, List[QualityMetric]] = {}

    def analyze_fluency(self, text: str) -> QualityMetric:
        """Analyze text fluency"""
        # Simple heuristics
        sentences = text.split(".")
        avg_length = sum(len(s.split()) for s in sentences) / max(1, len(sentences))

        # Fluency is good when average sentence length is 10-20 words
        if 10 <= avg_length <= 20:
            score = 0.9
        elif 5 <= avg_length <= 30:
            score = 0.7
        else:
            score = 0.4

        suggestions = []
        if avg_length < 5:
            suggestions.append("Sentences too short, combine ideas")
        elif avg_length > 30:
            suggestions.append("Sentences too long, break into smaller units")

        return QualityMetric(
            metric_name="fluency",
            score=score,
            description="Readability and sentence structure",
            suggestions=suggestions,
        )

    def analyze_coherence(self, text: str) -> QualityMetric:
        """Analyze text coherence"""
        sentences = text.split(".")
        
        # Check for pronoun consistency
        pronouns_used = sum(1 for s in sentences if "this" in s or "that" in s)
        coherence_score = min(1.0, pronouns_used / max(1, len(sentences)))

        # Check for topic consistency
        if len(sentences) > 1:
            first_words = set(s.split()[0] for s in sentences if s.split())
            if len(first_words) > len(sentences) * 0.5:
                coherence_score *= 0.8  # Lower if jumping between topics

        suggestions = []
        if coherence_score < 0.5:
            suggestions.append("Add transitional words (however, therefore, etc)")
            suggestions.append("Ensure logical flow between sentences")

        return QualityMetric(
            metric_name="coherence",
            score=coherence_score,
            description="Logical flow and connections",
            suggestions=suggestions,
        )

    def analyze_clarity(self, text: str) -> QualityMetric:
        """Analyze text clarity"""
        # Check for jargon and complex words
        complex_words = []
        words = text.split()

        for word in words:
            if len(word) > 12:  # Likely complex
                complex_words.append(word)

        jargon_ratio = len(complex_words) / max(1, len(words))
        clarity_score = 1.0 - (jargon_ratio * 0.5)

        suggestions = []
        if jargon_ratio > 0.1:
            suggestions.append("Use simpler vocabulary")
            suggestions.append("Define technical terms")

        return QualityMetric(
            metric_name="clarity",
            score=clarity_score,
            description="Simplicity and accessibility",
            suggestions=suggestions,
        )

    def analyze_completeness(self, text: str) -> QualityMetric:
        """Analyze response completeness"""
        # Check for common completion indicators
        completeness_indicators = [
            "conclusion" in text.lower(),
            "summary" in text.lower(),
            "therefore" in text.lower(),
            text.endswith("."),
        ]

        complete_score = sum(completeness_indicators) / 4.0

        suggestions = []
        if complete_score < 0.5:
            suggestions.append("Add concluding sentence")
            suggestions.append("Summarize key points")

        return QualityMetric(
            metric_name="completeness",
            score=complete_score,
            description="Response completeness",
            suggestions=suggestions,
        )

    def analyze_response(self, response_id: str, text: str) -> Dict:
        """Analyze complete response quality"""
        metrics = [
            self.analyze_fluency(text),
            self.analyze_coherence(text),
            self.analyze_clarity(text),
            self.analyze_completeness(text),
        ]

        self.analyses[response_id] = metrics

        avg_score = sum(m.score for m in metrics) / len(metrics)

        # Generate overall quality assessment
        if avg_score > 0.8:
            quality_level = "excellent"
        elif avg_score > 0.6:
            quality_level = "good"
        elif avg_score > 0.4:
            quality_level = "fair"
        else:
            quality_level = "needs_improvement"

        return {
            "response_id": response_id,
            "overall_score": round(avg_score, 2),
            "quality_level": quality_level,
            "metrics": [m.to_dict() for m in metrics],
            "all_suggestions": [
                s for m in metrics for s in m.suggestions
            ][:5],  # Top 5 suggestions
        }


# Global analyzer
nlg_analyzer = NLGQualityAnalyzer()


def analyze_response_quality(response_id: str, text: str) -> dict:
    """Analyze response quality"""
    return nlg_analyzer.analyze_response(response_id, text)
