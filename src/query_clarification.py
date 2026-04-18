"""Query clarification and expansion for better understanding"""

import json
from pathlib import Path
from datetime import datetime
from typing import Optional, List, Dict, Any, Tuple
from dataclasses import dataclass, field
from enum import Enum

QUERY_DIR = Path.home() / ".memory-mcp" / "query-clarification"
QUERY_DIR.mkdir(exist_ok=True, parents=True)


class AmbiguityType(Enum):
    """Types of query ambiguity"""
    LEXICAL = "lexical"  # Word has multiple meanings
    SYNTACTIC = "syntactic"  # Structure unclear
    SEMANTIC = "semantic"  # Meaning unclear
    REFERENTIAL = "referential"  # "It" unclear
    SCOPE = "scope"  # Scope of modifiers unclear
    DOMAIN = "domain"  # Which domain context


class ClarificationStrategy(Enum):
    """How to clarify queries"""
    YES_NO_QUESTION = "yes_no"  # Is it X?
    MULTIPLE_CHOICE = "multiple_choice"  # Is it X, Y, or Z?
    ELABORATION = "elaboration"  # Tell me more about X
    CONFIRMATION = "confirmation"  # Do you mean X?
    CONTEXT_REQUEST = "context_request"  # What is the context?


@dataclass
class AmbiguousElement:
    """Ambiguous part of query"""
    element_id: str
    text: str
    ambiguity_type: AmbiguityType
    possible_interpretations: List[str]
    confidence: float  # How confident it's ambiguous
    location: str  # Where in query
    severity: float  # 0-1, how serious is ambiguity

    def to_dict(self) -> Dict:
        """Serialize element"""
        return {
            "element_id": self.element_id,
            "text": self.text,
            "type": self.ambiguity_type.value,
            "interpretations": len(self.possible_interpretations),
            "severity": round(self.severity, 2),
        }


@dataclass
class ClarificationQuestion:
    """Question to clarify ambiguity"""
    question_id: str
    question_text: str
    target_ambiguity: str  # element_id
    strategy: ClarificationStrategy
    options: List[str] = field(default_factory=list)  # For multiple choice
    expected_response_type: str = "text"  # "text", "yes_no", "choice"
    created_at: str = ""

    def __post_init__(self):
        if not self.created_at:
            self.created_at = datetime.now().isoformat()

    def to_dict(self) -> Dict:
        """Serialize question"""
        return {
            "question_id": self.question_id,
            "strategy": self.strategy.value,
            "options": len(self.options),
            "response_type": self.expected_response_type,
        }


@dataclass
class ExpandedQuery:
    """Expanded/clarified version of query"""
    expanded_id: str
    original_query: str
    expanded_query: str
    clarifications_applied: List[str] = field(default_factory=list)  # question_ids
    expansion_type: str = "semantic"  # How was it expanded
    additional_context: Dict[str, Any] = field(default_factory=dict)
    created_at: str = ""

    def __post_init__(self):
        if not self.created_at:
            self.created_at = datetime.now().isoformat()

    def to_dict(self) -> Dict:
        """Serialize expanded query"""
        return {
            "expanded_id": self.expanded_id,
            "original_length": len(self.original_query),
            "expanded_length": len(self.expanded_query),
            "clarifications": len(self.clarifications_applied),
            "type": self.expansion_type,
        }


class AmbiguityDetector:
    """Detect ambiguities in queries"""

    LEXICAL_AMBIGUITIES = {
        "bank": ["financial institution", "river bank"],
        "bat": ["animal", "sports equipment"],
        "lead": ["metal", "guide"],
        "record": ["document", "data storage"],
        "object": ["noun", "purpose"],
    }

    @staticmethod
    def detect_lexical_ambiguity(query: str) -> List[AmbiguousElement]:
        """Detect word ambiguities"""
        ambiguities = []

        for word, meanings in AmbiguityDetector.LEXICAL_AMBIGUITIES.items():
            if word.lower() in query.lower():
                element = AmbiguousElement(
                    element_id=f"lex_{word}_{int(datetime.now().timestamp())}",
                    text=word,
                    ambiguity_type=AmbiguityType.LEXICAL,
                    possible_interpretations=meanings,
                    confidence=0.8,
                    location=f"word '{word}'",
                    severity=0.6,
                )
                ambiguities.append(element)

        return ambiguities

    @staticmethod
    def detect_referential_ambiguity(query: str) -> List[AmbiguousElement]:
        """Detect pronoun ambiguities"""
        ambiguities = []

        pronouns = ["it", "this", "that", "they", "them"]
        for pronoun in pronouns:
            if pronoun in query.lower():
                # Check if antecedent is unclear
                element = AmbiguousElement(
                    element_id=f"ref_{pronoun}_{int(datetime.now().timestamp())}",
                    text=pronoun,
                    ambiguity_type=AmbiguityType.REFERENTIAL,
                    possible_interpretations=["multiple possible antecedents"],
                    confidence=0.5,
                    location=f"pronoun '{pronoun}'",
                    severity=0.4,
                )
                ambiguities.append(element)

        return ambiguities

    @staticmethod
    def detect_all_ambiguities(query: str) -> List[AmbiguousElement]:
        """Detect all ambiguities in query"""
        ambiguities = []

        # Lexical
        ambiguities.extend(AmbiguityDetector.detect_lexical_ambiguity(query))

        # Referential
        ambiguities.extend(AmbiguityDetector.detect_referential_ambiguity(query))

        # Semantic: short queries often ambiguous
        if len(query.split()) < 3:
            element = AmbiguousElement(
                element_id=f"sem_{int(datetime.now().timestamp())}",
                text="entire_query",
                ambiguity_type=AmbiguityType.SEMANTIC,
                possible_interpretations=["Multiple possible interpretations"],
                confidence=0.6,
                location="overall",
                severity=0.5,
            )
            ambiguities.append(element)

        return ambiguities


class ClarificationGenerator:
    """Generate clarification questions"""

    @staticmethod
    def generate_questions(
        ambiguities: List[AmbiguousElement],
    ) -> List[ClarificationQuestion]:
        """Generate clarification questions"""
        questions = []

        for amb in ambiguities:
            if amb.ambiguity_type == AmbiguityType.LEXICAL:
                # Multiple choice for lexical
                question = ClarificationQuestion(
                    question_id=f"q_{amb.element_id}",
                    question_text=f"When you say '{amb.text}', do you mean {' or '.join(amb.possible_interpretations[:2])}?",
                    target_ambiguity=amb.element_id,
                    strategy=ClarificationStrategy.MULTIPLE_CHOICE,
                    options=amb.possible_interpretations,
                    expected_response_type="choice",
                )
                questions.append(question)

            elif amb.ambiguity_type == AmbiguityType.REFERENTIAL:
                # Elaboration for pronouns
                question = ClarificationQuestion(
                    question_id=f"q_{amb.element_id}",
                    question_text=f"What does '{amb.text}' refer to?",
                    target_ambiguity=amb.element_id,
                    strategy=ClarificationStrategy.ELABORATION,
                    expected_response_type="text",
                )
                questions.append(question)

            elif amb.ambiguity_type == AmbiguityType.SEMANTIC:
                # Context request for semantic
                question = ClarificationQuestion(
                    question_id=f"q_{amb.element_id}",
                    question_text="Could you provide more details or context about what you're looking for?",
                    target_ambiguity=amb.element_id,
                    strategy=ClarificationStrategy.CONTEXT_REQUEST,
                    expected_response_type="text",
                )
                questions.append(question)

        return questions


class QueryExpander:
    """Expand and clarify queries"""

    @staticmethod
    def expand_from_clarifications(
        original_query: str,
        clarifications: Dict[str, str],
    ) -> str:
        """Expand query with clarification responses"""
        expanded = original_query

        for element_id, clarification in clarifications.items():
            # Add clarification to query
            expanded += f" (regarding {element_id}: {clarification})"

        return expanded

    @staticmethod
    def expand_search_space(query: str) -> List[str]:
        """Generate expanded query variants"""
        variants = [query]

        # Synonym expansion
        synonyms = {
            "find": ["search for", "locate", "discover"],
            "show": ["display", "present", "exhibit"],
            "get": ["retrieve", "obtain", "fetch"],
        }

        for word, syn_list in synonyms.items():
            if word in query.lower():
                for syn in syn_list:
                    variant = query.lower().replace(word, syn)
                    variants.append(variant)

        return list(set(variants))


class ClarificationEngine:
    """Engine for query clarification"""

    def __init__(self):
        self.detected_ambiguities: Dict[str, List[AmbiguousElement]] = {}
        self.clarification_questions: Dict[str, List[ClarificationQuestion]] = {}
        self.clarifications_provided: Dict[str, Dict[str, str]] = {}
        self.expanded_queries: Dict[str, ExpandedQuery] = {}

    def analyze_query(self, query_id: str, query_text: str) -> Tuple[List[AmbiguousElement], List[ClarificationQuestion]]:
        """Analyze query for ambiguities"""
        # Detect ambiguities
        ambiguities = AmbiguityDetector.detect_all_ambiguities(query_text)
        self.detected_ambiguities[query_id] = ambiguities

        # Generate questions
        questions = ClarificationGenerator.generate_questions(ambiguities)
        self.clarification_questions[query_id] = questions

        return ambiguities, questions

    def apply_clarifications(
        self,
        query_id: str,
        clarifications: Dict[str, str],
    ) -> ExpandedQuery:
        """Apply clarifications to expand query"""
        if query_id not in self.detected_ambiguities:
            return None

        # Get original query (stored during analysis)
        original_query = clarifications.get("_original_query", "")

        # Expand with clarifications
        expanded_text = QueryExpander.expand_from_clarifications(
            original_query,
            clarifications,
        )

        expanded = ExpandedQuery(
            expanded_id=f"exp_{query_id}",
            original_query=original_query,
            expanded_query=expanded_text,
            clarifications_applied=list(clarifications.keys()),
            expansion_type="clarification_based",
        )

        self.expanded_queries[expanded.expanded_id] = expanded
        return expanded

    def get_clarification_status(self, query_id: str) -> Dict[str, Any]:
        """Get clarification status for query"""
        ambiguities = self.detected_ambiguities.get(query_id, [])
        questions = self.clarification_questions.get(query_id, [])

        clarified = self.clarifications_provided.get(query_id, {})

        return {
            "query_id": query_id,
            "ambiguities_detected": len(ambiguities),
            "clarification_questions": len(questions),
            "severity_levels": [a.severity for a in ambiguities],
            "clarifications_provided": len(clarified),
            "fully_clarified": len(clarified) >= len(questions),
        }


class ClarificationManager:
    """Manage query clarification across sessions"""

    def __init__(self):
        self.engines: Dict[str, ClarificationEngine] = {}

    def create_engine(self, engine_id: str) -> ClarificationEngine:
        """Create clarification engine"""
        engine = ClarificationEngine()
        self.engines[engine_id] = engine
        return engine

    def get_engine(self, engine_id: str) -> Optional[ClarificationEngine]:
        """Get engine"""
        return self.engines.get(engine_id)


# Global manager
clarification_manager = ClarificationManager()


# MCP Tools

def create_clarification_engine(engine_id: str) -> dict:
    """Create query clarification engine"""
    engine = clarification_manager.create_engine(engine_id)
    return {"engine_id": engine_id, "created": True}


def analyze_query_ambiguity(engine_id: str, query_id: str, query_text: str) -> dict:
    """Analyze query for ambiguities"""
    engine = clarification_manager.get_engine(engine_id)
    if not engine:
        return {"error": "Engine not found"}

    ambiguities, questions = engine.analyze_query(query_id, query_text)

    # Store original query for later
    engine.clarifications_provided[query_id] = {"_original_query": query_text}

    return {
        "query_id": query_id,
        "ambiguities": [a.to_dict() for a in ambiguities],
        "ambiguity_count": len(ambiguities),
        "clarification_questions": [q.to_dict() for q in questions],
        "question_count": len(questions),
    }


def get_clarification_questions(engine_id: str, query_id: str) -> dict:
    """Get clarification questions for query"""
    engine = clarification_manager.get_engine(engine_id)
    if not engine:
        return {"error": "Engine not found"}

    questions = engine.clarification_questions.get(query_id, [])
    return {
        "query_id": query_id,
        "questions": [q.to_dict() for q in questions],
        "count": len(questions),
    }


def apply_clarifications(
    engine_id: str,
    query_id: str,
    clarifications: dict,
) -> dict:
    """Apply clarifications to expand query"""
    engine = clarification_manager.get_engine(engine_id)
    if not engine:
        return {"error": "Engine not found"}

    expanded = engine.apply_clarifications(query_id, clarifications)
    return expanded.to_dict() if expanded else {"error": "Query not found"}


def get_clarification_status(engine_id: str, query_id: str) -> dict:
    """Get clarification status"""
    engine = clarification_manager.get_engine(engine_id)
    if not engine:
        return {"error": "Engine not found"}

    return engine.get_clarification_status(query_id)


if __name__ == "__main__":
    # Test query clarification
    engine = ClarificationEngine()

    # Analyze query
    query = "I want to find a bank near me"
    ambiguities, questions = engine.analyze_query("q_1", query)

    print(f"Ambiguities detected: {len(ambiguities)}")
    for amb in ambiguities:
        print(f"  - {amb.text}: {amb.possible_interpretations}")

    print(f"\nClarification questions:")
    for q in questions:
        print(f"  - {q.question_text}")

    # Apply clarifications
    clarifications = {
        "bank": "financial institution",
        "_original_query": query,
    }
    expanded = engine.apply_clarifications("q_1", clarifications)
    print(f"\nExpanded query: {expanded.expanded_query}")

    # Status
    status = engine.get_clarification_status("q_1")
    print(f"\nStatus: {json.dumps(status, indent=2)}")
