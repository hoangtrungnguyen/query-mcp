"""Few-shot learning and rapid adaptation for agents"""

import json
from pathlib import Path
from datetime import datetime
from typing import Optional, List, Dict, Any, Tuple, Callable
from dataclasses import dataclass, field
from enum import Enum

LEARNING_DIR = Path.home() / ".memory-mcp" / "few-shot-learning"
LEARNING_DIR.mkdir(exist_ok=True, parents=True)


class AdaptationStrategy(Enum):
    """Few-shot adaptation approaches"""
    DIRECT_MATCHING = "direct_matching"  # Find most similar example
    PATTERN_GENERALIZATION = "pattern_generalization"  # Extract generalizable pattern
    META_LEARNING = "meta_learning"  # Learn to learn
    ANALOGY = "analogy"  # Map to analogous domain
    PROTOTYPE = "prototype"  # Build prototype from examples


class ExampleQuality(Enum):
    """Quality indicators for examples"""
    POOR = 0.2
    FAIR = 0.4
    GOOD = 0.6
    EXCELLENT = 0.8
    EXPERT = 1.0


@dataclass
class Example:
    """Single learning example"""
    example_id: str
    input_text: str
    output_text: str
    explanation: Optional[str] = None
    quality_score: float = 0.8
    domain: str = "general"
    difficulty: float = 0.5  # 0-1, higher = harder
    created_at: str = ""

    def __post_init__(self):
        if not self.created_at:
            self.created_at = datetime.now().isoformat()

    def to_dict(self) -> Dict:
        """Serialize example"""
        return {
            "example_id": self.example_id,
            "input": self.input_text[:100],
            "output": self.output_text[:100],
            "quality": self.quality_score,
            "domain": self.domain,
            "difficulty": self.difficulty,
        }


@dataclass
class LearningPattern:
    """Pattern extracted from examples"""
    pattern_id: str
    pattern_type: str  # "input_feature", "output_structure", "transformation_rule"
    description: str
    examples_used: List[str]  # example IDs
    confidence: float  # 0-1
    generalization_score: float  # How well does it generalize
    created_at: str = ""

    def __post_init__(self):
        if not self.created_at:
            self.created_at = datetime.now().isoformat()

    def to_dict(self) -> Dict:
        """Serialize pattern"""
        return {
            "pattern_id": self.pattern_id,
            "type": self.pattern_type,
            "description": self.description,
            "confidence": self.confidence,
            "generalization": self.generalization_score,
            "examples_used": len(self.examples_used),
        }


@dataclass
class AdaptationResult:
    """Result of applying few-shot learning"""
    result_id: str
    query: str
    adapted_response: str
    strategy_used: AdaptationStrategy
    matched_examples: List[str]  # example IDs
    confidence: float
    patterns_applied: List[str]  # pattern IDs
    created_at: str = ""

    def __post_init__(self):
        if not self.created_at:
            self.created_at = datetime.now().isoformat()

    def to_dict(self) -> Dict:
        """Serialize result"""
        return {
            "result_id": self.result_id,
            "query": self.query[:100],
            "response": self.adapted_response[:100],
            "strategy": self.strategy_used.value,
            "confidence": self.confidence,
            "examples_matched": len(self.matched_examples),
            "patterns_applied": len(self.patterns_applied),
        }


class PatternExtractor:
    """Extract generalizable patterns from examples"""

    @staticmethod
    def extract_input_features(examples: List[Example]) -> List[Dict]:
        """Extract common input features"""
        features = []
        if not examples:
            return features

        # Extract common words
        all_words = {}
        for ex in examples:
            words = ex.input_text.lower().split()
            for word in words:
                if len(word) > 3:  # Skip short words
                    all_words[word] = all_words.get(word, 0) + 1

        # Common features appear in multiple examples
        for word, count in sorted(all_words.items(), key=lambda x: x[1], reverse=True)[:5]:
            if count >= len(examples) * 0.4:  # In 40%+ of examples
                features.append({
                    "feature": word,
                    "frequency": count,
                    "prevalence": count / len(examples),
                })

        return features

    @staticmethod
    def extract_output_structure(examples: List[Example]) -> Dict:
        """Extract common output structure"""
        structures = {}

        for ex in examples:
            output_len = len(ex.output_text)
            sentence_count = len([s for s in ex.output_text.split(".") if s.strip()])

            key = f"len_{output_len // 50 * 50}_sents_{sentence_count}"
            structures[key] = structures.get(key, 0) + 1

        # Most common structure
        if structures:
            most_common = max(structures.items(), key=lambda x: x[1])[0]
            return {
                "structure": most_common,
                "frequency": structures[most_common],
                "avg_output_length": sum(len(e.output_text) for e in examples) / len(examples),
            }

        return {}

    @staticmethod
    def extract_transformation_rules(examples: List[Example]) -> List[Dict]:
        """Extract transformation rules from input-output pairs"""
        rules = []

        for ex in examples:
            input_words = set(ex.input_text.lower().split())
            output_words = set(ex.output_text.lower().split())

            # Words in output not in input (likely added)
            added = output_words - input_words
            removed = input_words - output_words

            rules.append({
                "example_id": ex.example_id,
                "words_added": len(added),
                "words_removed": len(removed),
                "expansion_ratio": len(ex.output_text) / max(1, len(ex.input_text)),
            })

        return rules


class ExampleMatcher:
    """Match query to most relevant examples"""

    @staticmethod
    def calculate_similarity(query: str, example: Example) -> float:
        """Calculate similarity between query and example"""
        query_words = set(query.lower().split())
        example_words = set(example.input_text.lower().split())

        if not query_words or not example_words:
            return 0.0

        overlap = len(query_words & example_words)
        jaccard = overlap / len(query_words | example_words)

        # Weighted by example quality
        return jaccard * example.quality_score

    @staticmethod
    def find_similar_examples(
        query: str,
        examples: List[Example],
        top_k: int = 3,
    ) -> List[Tuple[Example, float]]:
        """Find most similar examples"""
        scores = [
            (ex, ExampleMatcher.calculate_similarity(query, ex))
            for ex in examples
        ]

        return sorted(scores, key=lambda x: x[1], reverse=True)[:top_k]


class AdaptationEngine:
    """Apply few-shot learning to adapt behavior"""

    def __init__(self):
        self.examples: Dict[str, Example] = {}
        self.patterns: Dict[str, LearningPattern] = {}
        self.results: Dict[str, AdaptationResult] = {}
        self.extractor = PatternExtractor()
        self.matcher = ExampleMatcher()

    def add_example(
        self,
        example_id: str,
        input_text: str,
        output_text: str,
        explanation: Optional[str] = None,
        quality: float = 0.8,
        domain: str = "general",
    ) -> Example:
        """Add learning example"""
        example = Example(
            example_id=example_id,
            input_text=input_text,
            output_text=output_text,
            explanation=explanation,
            quality_score=quality,
            domain=domain,
        )
        self.examples[example_id] = example
        return example

    def extract_patterns(self, domain: Optional[str] = None) -> List[LearningPattern]:
        """Extract generalizable patterns"""
        examples = [
            ex for ex in self.examples.values()
            if domain is None or ex.domain == domain
        ]

        if not examples:
            return []

        patterns = []

        # Extract input features
        input_features = self.extractor.extract_input_features(examples)
        for i, feature in enumerate(input_features):
            pattern = LearningPattern(
                pattern_id=f"pattern_input_{i}",
                pattern_type="input_feature",
                description=f"Common input feature: {feature['feature']}",
                examples_used=[ex.example_id for ex in examples],
                confidence=min(1.0, feature["prevalence"] + 0.2),
                generalization_score=feature["prevalence"],
            )
            self.patterns[pattern.pattern_id] = pattern
            patterns.append(pattern)

        # Extract output structure
        output_struct = self.extractor.extract_output_structure(examples)
        if output_struct:
            pattern = LearningPattern(
                pattern_id="pattern_output_struct",
                pattern_type="output_structure",
                description=f"Common output structure: {output_struct.get('structure', 'varied')}",
                examples_used=[ex.example_id for ex in examples],
                confidence=0.7,
                generalization_score=0.6,
            )
            self.patterns[pattern.pattern_id] = pattern
            patterns.append(pattern)

        # Extract transformation rules
        transform_rules = self.extractor.extract_transformation_rules(examples)
        if transform_rules:
            avg_expansion = sum(r["expansion_ratio"] for r in transform_rules) / len(transform_rules)
            pattern = LearningPattern(
                pattern_id="pattern_transform",
                pattern_type="transformation_rule",
                description=f"Output typically {avg_expansion:.1f}x longer than input",
                examples_used=[ex.example_id for ex in examples],
                confidence=0.8,
                generalization_score=0.7,
            )
            self.patterns[pattern.pattern_id] = pattern
            patterns.append(pattern)

        return patterns

    def adapt(
        self,
        query: str,
        strategy: AdaptationStrategy = AdaptationStrategy.DIRECT_MATCHING,
        top_k: int = 3,
    ) -> AdaptationResult:
        """Adapt to new query using few-shot learning"""
        # Find similar examples
        similar = self.matcher.find_similar_examples(query, list(self.examples.values()), top_k)

        if not similar:
            return AdaptationResult(
                result_id=f"adapt_{len(self.results)}",
                query=query,
                adapted_response="No similar examples found",
                strategy_used=strategy,
                matched_examples=[],
                confidence=0.0,
                patterns_applied=[],
            )

        matched_ids = [ex.example_id for ex, _ in similar]
        matched_examples = [ex for ex, _ in similar]

        # Generate response based on strategy
        if strategy == AdaptationStrategy.DIRECT_MATCHING:
            adapted_response = similar[0][0].output_text if similar else ""
            confidence = similar[0][1] if similar else 0.0

        elif strategy == AdaptationStrategy.PATTERN_GENERALIZATION:
            # Extract and apply patterns
            patterns = self.extract_patterns()
            pattern_ids = [p.pattern_id for p in patterns[:3]]

            adapted_response = f"[Adapted using {len(pattern_ids)} patterns] "
            adapted_response += " ".join([ex.output_text[:30] for ex, _ in similar])
            confidence = sum(score for _, score in similar) / len(similar) if similar else 0.0

        elif strategy == AdaptationStrategy.ANALOGY:
            # Map to analogous solution
            adapted_response = f"[Analogous to: {matched_examples[0].domain}] "
            adapted_response += similar[0][0].output_text if similar else ""
            confidence = similar[0][1] * 0.9 if similar else 0.0

        else:  # PROTOTYPE or META_LEARNING
            # Synthesize from multiple examples
            adapted_response = "[Synthesized response] "
            adapted_response += " ".join([ex.output_text[:25] for ex in matched_examples])
            confidence = min(1.0, sum(score for _, score in similar) / len(similar)) if similar else 0.0

        result = AdaptationResult(
            result_id=f"adapt_{len(self.results)}",
            query=query,
            adapted_response=adapted_response,
            strategy_used=strategy,
            matched_examples=matched_ids,
            confidence=confidence,
            patterns_applied=[],
        )

        self.results[result.result_id] = result
        return result

    def get_learning_summary(self, domain: Optional[str] = None) -> Dict[str, Any]:
        """Summarize learning progress"""
        domain_examples = [
            ex for ex in self.examples.values()
            if domain is None or ex.domain == domain
        ]

        avg_quality = (
            sum(ex.quality_score for ex in domain_examples) / len(domain_examples)
            if domain_examples else 0.0
        )

        return {
            "domain": domain or "all",
            "example_count": len(domain_examples),
            "avg_quality": avg_quality,
            "pattern_count": len(self.patterns),
            "adaptation_count": len(self.results),
            "avg_confidence": (
                sum(r.confidence for r in self.results.values()) / len(self.results)
                if self.results else 0.0
            ),
        }


class RapidAdaptationManager:
    """Manage multiple adaptation sessions"""

    def __init__(self):
        self.engines: Dict[str, AdaptationEngine] = {}

    def create_session(self, session_id: str) -> AdaptationEngine:
        """Create new adaptation session"""
        engine = AdaptationEngine()
        self.engines[session_id] = engine
        return engine

    def get_session(self, session_id: str) -> Optional[AdaptationEngine]:
        """Get adaptation session"""
        return self.engines.get(session_id)

    def get_all_sessions_summary(self) -> List[Dict]:
        """Get summary of all sessions"""
        summaries = []

        for session_id, engine in self.engines.items():
            summary = engine.get_learning_summary()
            summary["session_id"] = session_id
            summaries.append(summary)

        return summaries


# Global manager
adaptation_manager = RapidAdaptationManager()


# MCP Tools

def create_adaptation_session(session_id: str) -> dict:
    """Create few-shot learning session"""
    engine = adaptation_manager.create_session(session_id)
    return {"session_id": session_id, "created": True}


def add_learning_example(
    session_id: str,
    example_id: str,
    input_text: str,
    output_text: str,
    quality: float = 0.8,
    domain: str = "general",
) -> dict:
    """Add example to session"""
    engine = adaptation_manager.get_session(session_id)
    if not engine:
        return {"error": "Session not found"}

    example = engine.add_example(
        example_id,
        input_text,
        output_text,
        quality=quality,
        domain=domain,
    )
    return example.to_dict()


def extract_learning_patterns(session_id: str, domain: str = None) -> dict:
    """Extract patterns from examples"""
    engine = adaptation_manager.get_session(session_id)
    if not engine:
        return {"error": "Session not found"}

    patterns = engine.extract_patterns(domain)
    return {
        "domain": domain or "all",
        "patterns": [p.to_dict() for p in patterns],
        "count": len(patterns),
    }


def adapt_to_query(
    session_id: str,
    query: str,
    strategy: str = "direct_matching",
) -> dict:
    """Adapt to new query"""
    engine = adaptation_manager.get_session(session_id)
    if not engine:
        return {"error": "Session not found"}

    result = engine.adapt(query, AdaptationStrategy(strategy))
    return result.to_dict()


def get_learning_summary(session_id: str) -> dict:
    """Get session summary"""
    engine = adaptation_manager.get_session(session_id)
    if not engine:
        return {"error": "Session not found"}

    return engine.get_learning_summary()


if __name__ == "__main__":
    # Test few-shot learning
    manager = RapidAdaptationManager()
    engine = manager.create_session("session_1")

    # Add examples
    engine.add_example(
        "ex_1",
        "Translate English to French: Hello",
        "Bonjour",
        quality=0.9,
        domain="translation",
    )
    engine.add_example(
        "ex_2",
        "Translate English to French: Thank you",
        "Merci",
        quality=0.9,
        domain="translation",
    )
    engine.add_example(
        "ex_3",
        "Translate English to French: Good morning",
        "Bonjour",
        quality=0.9,
        domain="translation",
    )

    # Extract patterns
    patterns = engine.extract_patterns("translation")
    print(f"Patterns: {len(patterns)}")

    # Adapt to new query
    result = engine.adapt("Translate English to French: Goodbye")
    print(f"Adaptation: {result.adapted_response}")

    # Summary
    summary = engine.get_learning_summary("translation")
    print(f"Summary: {json.dumps(summary, indent=2)}")
