"""Response generation from dialogue context and goals"""

import json
from pathlib import Path
from datetime import datetime
from typing import Optional, List, Dict, Any
from dataclasses import dataclass, field
from enum import Enum

GEN_DIR = Path.home() / ".memory-mcp" / "response-generation"
GEN_DIR.mkdir(exist_ok=True, parents=True)


class GenerationStrategy(Enum):
    """Strategies for response generation"""
    TEMPLATE_BASED = "template_based"
    RULE_BASED = "rule_based"
    LEARNED = "learned"
    HYBRID = "hybrid"


class ResponseType(Enum):
    """Types of responses"""
    INFORMATIVE = "informative"
    CLARIFYING = "clarifying"
    CONFIRMING = "confirming"
    SUGGESTING = "suggesting"
    INSTRUCTIONAL = "instructional"
    EMPATHETIC = "empathetic"


@dataclass
class ResponseTemplate:
    """Template for response generation"""
    template_id: str
    response_type: ResponseType
    pattern: str  # Template pattern with slots
    slots: List[str] = field(default_factory=list)
    conditions: List[str] = field(default_factory=list)  # When applicable
    success_rate: float = 0.8

    def to_dict(self) -> Dict:
        """Serialize template"""
        return {
            "template_id": self.template_id,
            "type": self.response_type.value,
            "success_rate": round(self.success_rate, 2),
        }


@dataclass
class ResponseContext:
    """Context for response generation"""
    context_id: str
    dialogue_state: str  # Current state
    user_intent: str  # What user wants
    extracted_topic: str  # Main topic
    user_knowledge_level: str  # NOVICE, BEGINNER, etc.
    goals: List[str] = field(default_factory=list)  # Conversation goals
    constraints: List[str] = field(default_factory=list)  # Response constraints
    previous_responses: List[str] = field(default_factory=list)  # Avoid repetition

    def to_dict(self) -> Dict:
        """Serialize context"""
        return {
            "context_id": self.context_id,
            "state": self.dialogue_state,
            "intent": self.user_intent,
            "topic": self.extracted_topic,
            "knowledge_level": self.user_knowledge_level,
            "goals": len(self.goals),
        }


@dataclass
class CandidateResponse:
    """Generated candidate response"""
    response_id: str
    text: str
    response_type: ResponseType
    strategy: GenerationStrategy
    confidence: float  # Generation confidence
    length: int  # Token count estimate
    relevance_score: float = 0.0
    informativeness: float = 0.0
    coherence: float = 0.0
    created_at: str = ""

    def __post_init__(self):
        if not self.created_at:
            self.created_at = datetime.now().isoformat()

    def to_dict(self) -> Dict:
        """Serialize candidate"""
        return {
            "response_id": self.response_id,
            "type": self.response_type.value,
            "strategy": self.strategy.value,
            "confidence": round(self.confidence, 2),
            "length": self.length,
        }


class ResponseGenerator:
    """Generate candidate responses"""

    TEMPLATE_RESPONSES = {
        ResponseType.INFORMATIVE: [
            "Based on your question about {topic}, {fact}.",
            "{topic} can be understood as {explanation}.",
            "In the context of {topic}, {detail}.",
        ],
        ResponseType.CLARIFYING: [
            "Just to clarify, are you asking about {topic}?",
            "Do you mean {interpretation}?",
            "Let me make sure I understand: {rephrasing}?",
        ],
        ResponseType.SUGGESTING: [
            "I'd suggest {recommendation}.",
            "One approach could be {suggestion}.",
            "You might consider {option}.",
        ],
        ResponseType.EMPATHETIC: [
            "I understand you're concerned about {topic}.",
            "That's a valid point about {topic}.",
            "It makes sense to worry about {concern}.",
        ],
    }

    @staticmethod
    def generate(
        context: ResponseContext,
        strategy: GenerationStrategy = GenerationStrategy.HYBRID,
    ) -> List[CandidateResponse]:
        """Generate candidate responses"""
        candidates = []

        # Template-based generation
        if strategy in [GenerationStrategy.TEMPLATE_BASED, GenerationStrategy.HYBRID]:
            for resp_type, templates in ResponseGenerator.TEMPLATE_RESPONSES.items():
                for template in templates:
                    text = template.format(
                        topic=context.extracted_topic,
                        fact="key information",
                        explanation="definition",
                        detail="relevant details",
                        interpretation="your intended meaning",
                        rephrasing="your statement in other words",
                        recommendation="a practical approach",
                        suggestion="trying a different method",
                        option="an alternative approach",
                        concern="the potential issue",
                    )

                    candidate = CandidateResponse(
                        response_id=f"cand_{len(candidates)}",
                        text=text,
                        response_type=resp_type,
                        strategy=GenerationStrategy.TEMPLATE_BASED,
                        confidence=0.7,
                        length=len(text.split()),
                    )
                    candidates.append(candidate)

        # Rule-based generation
        if strategy in [GenerationStrategy.RULE_BASED, GenerationStrategy.HYBRID]:
            if context.user_intent == "seek_information":
                text = f"Regarding {context.extracted_topic}: {context.goals[0] if context.goals else 'here is relevant information'}."
                candidate = CandidateResponse(
                    response_id=f"cand_{len(candidates)}",
                    text=text,
                    response_type=ResponseType.INFORMATIVE,
                    strategy=GenerationStrategy.RULE_BASED,
                    confidence=0.8,
                    length=len(text.split()),
                )
                candidates.append(candidate)

            elif context.user_intent == "request_action":
                text = f"I can help with {context.extracted_topic}. Let me proceed with {context.goals[0] if context.goals else 'the requested action'}."
                candidate = CandidateResponse(
                    response_id=f"cand_{len(candidates)}",
                    text=text,
                    response_type=ResponseType.INSTRUCTIONAL,
                    strategy=GenerationStrategy.RULE_BASED,
                    confidence=0.85,
                    length=len(text.split()),
                )
                candidates.append(candidate)

        return candidates


class ResponseAnalyzer:
    """Analyze generated responses against constraints"""

    @staticmethod
    def analyze(
        response: CandidateResponse,
        context: ResponseContext,
    ) -> Dict[str, float]:
        """Analyze response quality"""
        scores = {}

        # Relevance: how well does it address intent
        scores["relevance"] = 0.8 if context.user_intent in response.text.lower() else 0.5

        # Informativeness: does it provide value
        word_count = len(response.text.split())
        scores["informativeness"] = min(1.0, word_count / 50)

        # Coherence: grammatical and logical consistency
        scores["coherence"] = 0.8

        # Constraint satisfaction
        scores["constraint_satisfaction"] = 1.0
        if context.constraints:
            if "avoid_repetition" in context.constraints:
                if any(prev in response.text for prev in context.previous_responses):
                    scores["constraint_satisfaction"] -= 0.3

        # Adaptation: response tailored to knowledge level
        if context.user_knowledge_level == "novice" and word_count > 100:
            scores["adaptation"] = 0.6
        else:
            scores["adaptation"] = 0.85

        return scores


class GenerationEngine:
    """Orchestrate response generation"""

    def __init__(self):
        self.candidates_generated: Dict[str, List[CandidateResponse]] = {}
        self.analyses: Dict[str, Dict] = {}

    def generate_responses(
        self,
        context: ResponseContext,
        strategy: GenerationStrategy = GenerationStrategy.HYBRID,
    ) -> Dict[str, Any]:
        """Generate and analyze response candidates"""
        candidates = ResponseGenerator.generate(context, strategy)
        self.candidates_generated[context.context_id] = candidates

        analyses = {}
        for candidate in candidates:
            analysis = ResponseAnalyzer.analyze(candidate, context)
            analyses[candidate.response_id] = analysis

        self.analyses[context.context_id] = analyses

        return {
            "context_id": context.context_id,
            "candidates_generated": len(candidates),
            "candidates": [c.to_dict() for c in candidates],
            "analysis_summary": {
                "avg_relevance": sum(a.get("relevance", 0) for a in analyses.values()) / len(analyses) if analyses else 0.0,
                "avg_informativeness": sum(a.get("informativeness", 0) for a in analyses.values()) / len(analyses) if analyses else 0.0,
            },
        }

    def get_best_candidates(
        self,
        context_id: str,
        top_k: int = 3,
    ) -> Optional[List[Dict]]:
        """Get top K candidates"""
        if context_id not in self.candidates_generated:
            return None

        candidates = self.candidates_generated[context_id]
        analyses = self.analyses.get(context_id, {})

        # Score candidates
        scored = []
        for cand in candidates:
            analysis = analyses.get(cand.response_id, {})
            score = sum(analysis.values()) / len(analysis) if analysis else 0.5
            scored.append((cand, score))

        # Sort by score
        scored.sort(key=lambda x: x[1], reverse=True)

        return [
            {
                "response": c.to_dict(),
                "score": round(s, 2),
            }
            for c, s in scored[:top_k]
        ]


class GenerationManager:
    """Manage generation across conversations"""

    def __init__(self):
        self.engines: Dict[str, GenerationEngine] = {}

    def create_engine(self, engine_id: str) -> GenerationEngine:
        """Create generation engine"""
        engine = GenerationEngine()
        self.engines[engine_id] = engine
        return engine

    def get_engine(self, engine_id: str) -> Optional[GenerationEngine]:
        """Get engine"""
        return self.engines.get(engine_id)


# Global manager
generation_manager = GenerationManager()


# MCP Tools

def create_generation_engine(engine_id: str) -> dict:
    """Create response generation engine"""
    engine = generation_manager.create_engine(engine_id)
    return {"engine_id": engine_id, "created": True}


def generate_responses(
    engine_id: str,
    context_id: str,
    dialogue_state: str,
    user_intent: str,
    topic: str,
    knowledge_level: str,
) -> dict:
    """Generate response candidates"""
    engine = generation_manager.get_engine(engine_id)
    if not engine:
        return {"error": "Engine not found"}

    context = ResponseContext(
        context_id=context_id,
        dialogue_state=dialogue_state,
        user_intent=user_intent,
        extracted_topic=topic,
        user_knowledge_level=knowledge_level,
    )

    return engine.generate_responses(context)


def get_best_candidates(
    engine_id: str,
    context_id: str,
    top_k: int = 3,
) -> dict:
    """Get top candidates"""
    engine = generation_manager.get_engine(engine_id)
    if not engine:
        return {"error": "Engine not found"}

    candidates = engine.get_best_candidates(context_id, top_k)
    return {"candidates": candidates} if candidates else {"error": "Context not found"}


if __name__ == "__main__":
    engine = GenerationEngine()
    context = ResponseContext(
        context_id="ctx_1",
        dialogue_state="information_seeking",
        user_intent="seek_information",
        extracted_topic="machine learning",
        user_knowledge_level="intermediate",
        goals=["understand neural networks"],
    )

    result = engine.generate_responses(context)
    print(f"Result: {json.dumps(result, indent=2)}")

    best = engine.get_best_candidates("ctx_1", 3)
    print(f"Best: {json.dumps(best, indent=2)}")
