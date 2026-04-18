"""Domain specialization and expertise development for agents"""

import json
from pathlib import Path
from datetime import datetime
from typing import Optional, List, Dict, Any, Set
from dataclasses import dataclass, field
from enum import Enum

DOMAIN_DIR = Path.home() / ".memory-mcp" / "domain-specialization"
DOMAIN_DIR.mkdir(exist_ok=True, parents=True)


class Domain(Enum):
    """Knowledge domains"""
    TECHNOLOGY = "technology"
    MEDICINE = "medicine"
    LAW = "law"
    FINANCE = "finance"
    SCIENCE = "science"
    HUMANITIES = "humanities"
    ARTS = "arts"
    BUSINESS = "business"
    ENGINEERING = "engineering"
    EDUCATION = "education"


class ExpertiseLevel(Enum):
    """Expertise progression levels"""
    NOVICE = 1
    BEGINNER = 2
    INTERMEDIATE = 3
    ADVANCED = 4
    EXPERT = 5
    MASTER = 6


@dataclass
class DomainTerm:
    """Specialized term in domain"""
    term: str
    definition: str
    domain: Domain
    synonyms: List[str] = field(default_factory=list)
    related_terms: List[str] = field(default_factory=list)
    usage_context: str = ""
    confidence: float = 0.8

    def to_dict(self) -> Dict:
        """Serialize term"""
        return {
            "term": self.term,
            "domain": self.domain.value,
            "definition": self.definition,
            "synonyms": len(self.synonyms),
            "context": self.usage_context,
            "confidence": self.confidence,
        }


@dataclass
class DomainConcept:
    """Key concept in domain"""
    concept_id: str
    name: str
    domain: Domain
    definition: str
    prerequisites: List[str] = field(default_factory=list)  # What must be learned first
    applications: List[str] = field(default_factory=list)  # Real-world uses
    related_concepts: List[str] = field(default_factory=list)
    importance: float = 0.7  # 0-1, how central to domain
    created_at: str = ""

    def __post_init__(self):
        if not self.created_at:
            self.created_at = datetime.now().isoformat()

    def to_dict(self) -> Dict:
        """Serialize concept"""
        return {
            "concept_id": self.concept_id,
            "name": self.name,
            "domain": self.domain.value,
            "importance": self.importance,
            "prerequisites": len(self.prerequisites),
            "applications": len(self.applications),
        }


@dataclass
class DomainPattern:
    """Recurring pattern in domain"""
    pattern_id: str
    name: str
    domain: Domain
    description: str
    when_to_use: str
    benefits: List[str] = field(default_factory=list)
    drawbacks: List[str] = field(default_factory=list)
    variations: List[str] = field(default_factory=list)
    frequency: int = 0  # How often encountered
    created_at: str = ""

    def __post_init__(self):
        if not self.created_at:
            self.created_at = datetime.now().isoformat()

    def to_dict(self) -> Dict:
        """Serialize pattern"""
        return {
            "pattern_id": self.pattern_id,
            "name": self.name,
            "domain": self.domain.value,
            "benefits": len(self.benefits),
            "drawbacks": len(self.drawbacks),
            "frequency": self.frequency,
        }


@dataclass
class DomainExpertise:
    """Agent expertise in domain"""
    expertise_id: str
    agent_id: str
    domain: Domain
    level: ExpertiseLevel
    years_experience: float = 0.0
    problems_solved: int = 0
    concepts_mastered: List[str] = field(default_factory=list)
    patterns_known: List[str] = field(default_factory=list)
    recent_learning: List[str] = field(default_factory=list)
    confidence: float = 0.5
    created_at: str = ""
    last_updated: str = ""

    def __post_init__(self):
        if not self.created_at:
            self.created_at = datetime.now().isoformat()
        if not self.last_updated:
            self.last_updated = self.created_at

    def update_level(self, new_level: ExpertiseLevel):
        """Progress expertise level"""
        self.level = new_level
        self.confidence = min(1.0, self.confidence + 0.1)
        self.last_updated = datetime.now().isoformat()

    def solve_problem(self):
        """Record problem solved"""
        self.problems_solved += 1
        self.years_experience += 0.1  # Incremental growth
        self.last_updated = datetime.now().isoformat()

    def to_dict(self) -> Dict:
        """Serialize expertise"""
        return {
            "expertise_id": self.expertise_id,
            "domain": self.domain.value,
            "level": self.level.name,
            "problems_solved": self.problems_solved,
            "concepts_mastered": len(self.concepts_mastered),
            "patterns_known": len(self.patterns_known),
            "confidence": self.confidence,
        }


class DomainKnowledgeBase:
    """Store domain knowledge"""

    def __init__(self):
        self.terms: Dict[str, DomainTerm] = {}
        self.concepts: Dict[str, DomainConcept] = {}
        self.patterns: Dict[str, DomainPattern] = {}

    def add_term(
        self,
        term: str,
        definition: str,
        domain: Domain,
        synonyms: List[str] = None,
    ) -> DomainTerm:
        """Add domain term"""
        domain_term = DomainTerm(
            term=term,
            definition=definition,
            domain=domain,
            synonyms=synonyms or [],
        )
        self.terms[term] = domain_term
        return domain_term

    def add_concept(
        self,
        concept_id: str,
        name: str,
        domain: Domain,
        definition: str,
        importance: float = 0.7,
    ) -> DomainConcept:
        """Add domain concept"""
        concept = DomainConcept(
            concept_id=concept_id,
            name=name,
            domain=domain,
            definition=definition,
            importance=importance,
        )
        self.concepts[concept_id] = concept
        return concept

    def add_pattern(
        self,
        pattern_id: str,
        name: str,
        domain: Domain,
        description: str,
    ) -> DomainPattern:
        """Add domain pattern"""
        pattern = DomainPattern(
            pattern_id=pattern_id,
            name=name,
            domain=domain,
            description=description,
            when_to_use="",
        )
        self.patterns[pattern_id] = pattern
        return pattern

    def search_terms(self, domain: Domain, query: str) -> List[DomainTerm]:
        """Search terms in domain"""
        results = []
        for term in self.terms.values():
            if term.domain != domain:
                continue

            if (query.lower() in term.term.lower() or
                query.lower() in term.definition.lower()):
                results.append(term)

        return results

    def get_domain_summary(self, domain: Domain) -> Dict[str, Any]:
        """Get domain knowledge summary"""
        domain_concepts = [c for c in self.concepts.values() if c.domain == domain]
        domain_patterns = [p for p in self.patterns.values() if p.domain == domain]
        domain_terms = [t for t in self.terms.values() if t.domain == domain]

        return {
            "domain": domain.value,
            "term_count": len(domain_terms),
            "concept_count": len(domain_concepts),
            "pattern_count": len(domain_patterns),
            "core_concepts": sorted(
                domain_concepts,
                key=lambda c: c.importance,
                reverse=True
            )[:3],
        }


class DomainSpecializationEngine:
    """Manage agent domain specialization"""

    def __init__(self):
        self.knowledge_base = DomainKnowledgeBase()
        self.expertises: Dict[str, DomainExpertise] = {}

    def initialize_agent_expertise(
        self,
        agent_id: str,
        domain: Domain,
        initial_level: ExpertiseLevel = ExpertiseLevel.NOVICE,
    ) -> DomainExpertise:
        """Initialize agent in domain"""
        expertise_id = f"exp_{agent_id}_{domain.value}"

        expertise = DomainExpertise(
            expertise_id=expertise_id,
            agent_id=agent_id,
            domain=domain,
            level=initial_level,
        )

        self.expertises[expertise_id] = expertise
        return expertise

    def progress_expertise(
        self,
        expertise_id: str,
        problems_solved: int = 1,
        new_concepts: List[str] = None,
    ) -> Optional[DomainExpertise]:
        """Progress agent expertise"""
        if expertise_id not in self.expertises:
            return None

        expertise = self.expertises[expertise_id]

        for _ in range(problems_solved):
            expertise.solve_problem()

        if new_concepts:
            expertise.concepts_mastered.extend(new_concepts)
            expertise.recent_learning = new_concepts

        # Auto-level up based on progress
        if expertise.problems_solved >= 10 and expertise.level == ExpertiseLevel.NOVICE:
            expertise.update_level(ExpertiseLevel.BEGINNER)
        elif expertise.problems_solved >= 30 and expertise.level == ExpertiseLevel.BEGINNER:
            expertise.update_level(ExpertiseLevel.INTERMEDIATE)
        elif expertise.problems_solved >= 100 and expertise.level == ExpertiseLevel.INTERMEDIATE:
            expertise.update_level(ExpertiseLevel.ADVANCED)

        return expertise

    def get_agent_expertise(self, expertise_id: str) -> Optional[DomainExpertise]:
        """Get agent expertise"""
        return self.expertises.get(expertise_id)

    def generate_learning_path(
        self,
        expertise_id: str,
    ) -> Optional[Dict[str, Any]]:
        """Generate personalized learning path"""
        if expertise_id not in self.expertises:
            return None

        expertise = self.expertises[expertise_id]

        # Get domain knowledge
        domain_summary = self.knowledge_base.get_domain_summary(expertise.domain)

        # Recommend next concepts based on level
        core_concepts = domain_summary.get("core_concepts", [])
        recommended = [
            c for c in core_concepts
            if c.concept_id not in expertise.concepts_mastered
        ]

        return {
            "expertise_id": expertise_id,
            "current_level": expertise.level.name,
            "domain": expertise.domain.value,
            "progress": min(100, expertise.problems_solved),
            "next_level_at": 10 * (expertise.level.value + 1),
            "recommended_concepts": [c.name for c in recommended[:3]],
            "estimated_time_to_next_level": f"{(10 * (expertise.level.value + 1) - expertise.problems_solved) * 0.5:.0f} hours",
        }

    def compare_expertise_domains(
        self,
        agent_id: str,
    ) -> List[Dict[str, Any]]:
        """Compare agent expertise across domains"""
        agent_expertises = [
            exp for exp in self.expertises.values()
            if exp.agent_id == agent_id
        ]

        return sorted(
            [exp.to_dict() for exp in agent_expertises],
            key=lambda x: x["level"],
            reverse=True
        )


class SpecializationManager:
    """Manage multiple domain specializations"""

    def __init__(self):
        self.engines: Dict[str, DomainSpecializationEngine] = {}

    def create_engine(self, engine_id: str) -> DomainSpecializationEngine:
        """Create specialization engine"""
        engine = DomainSpecializationEngine()
        self.engines[engine_id] = engine
        return engine

    def get_engine(self, engine_id: str) -> Optional[DomainSpecializationEngine]:
        """Get specialization engine"""
        return self.engines.get(engine_id)


# Global manager
specialization_manager = SpecializationManager()


# MCP Tools

def create_specialization_engine(engine_id: str) -> dict:
    """Create domain specialization engine"""
    engine = specialization_manager.create_engine(engine_id)
    return {"engine_id": engine_id, "created": True}


def initialize_agent_domain(
    engine_id: str,
    agent_id: str,
    domain: str,
) -> dict:
    """Initialize agent in domain"""
    engine = specialization_manager.get_engine(engine_id)
    if not engine:
        return {"error": "Engine not found"}

    expertise = engine.initialize_agent_expertise(
        agent_id,
        Domain(domain),
    )
    return expertise.to_dict()


def add_domain_knowledge(
    engine_id: str,
    knowledge_type: str,  # "term", "concept", "pattern"
    **kwargs,
) -> dict:
    """Add knowledge to domain"""
    engine = specialization_manager.get_engine(engine_id)
    if not engine:
        return {"error": "Engine not found"}

    if knowledge_type == "term":
        term = engine.knowledge_base.add_term(
            kwargs.get("term", ""),
            kwargs.get("definition", ""),
            Domain(kwargs.get("domain", "technology")),
            kwargs.get("synonyms", []),
        )
        return term.to_dict()

    elif knowledge_type == "concept":
        concept = engine.knowledge_base.add_concept(
            kwargs.get("concept_id", ""),
            kwargs.get("name", ""),
            Domain(kwargs.get("domain", "technology")),
            kwargs.get("definition", ""),
        )
        return concept.to_dict()

    elif knowledge_type == "pattern":
        pattern = engine.knowledge_base.add_pattern(
            kwargs.get("pattern_id", ""),
            kwargs.get("name", ""),
            Domain(kwargs.get("domain", "technology")),
            kwargs.get("description", ""),
        )
        return pattern.to_dict()

    return {"error": "Unknown knowledge type"}


def progress_expertise(
    engine_id: str,
    expertise_id: str,
    problems_solved: int = 1,
) -> dict:
    """Progress agent expertise"""
    engine = specialization_manager.get_engine(engine_id)
    if not engine:
        return {"error": "Engine not found"}

    expertise = engine.progress_expertise(expertise_id, problems_solved)
    return expertise.to_dict() if expertise else {"error": "Expertise not found"}


def get_learning_path(engine_id: str, expertise_id: str) -> dict:
    """Get personalized learning path"""
    engine = specialization_manager.get_engine(engine_id)
    if not engine:
        return {"error": "Engine not found"}

    path = engine.generate_learning_path(expertise_id)
    return path or {"error": "Learning path not found"}


def get_domain_summary(engine_id: str, domain: str) -> dict:
    """Get domain knowledge summary"""
    engine = specialization_manager.get_engine(engine_id)
    if not engine:
        return {"error": "Engine not found"}

    summary = engine.knowledge_base.get_domain_summary(Domain(domain))
    return summary


if __name__ == "__main__":
    # Test domain specialization
    engine = DomainSpecializationEngine()

    # Add terms
    engine.knowledge_base.add_term(
        "API",
        "Application Programming Interface",
        Domain.TECHNOLOGY,
        ["interface"],
    )
    engine.knowledge_base.add_term(
        "REST",
        "Representational State Transfer",
        Domain.TECHNOLOGY,
        ["RESTful"],
    )

    # Add concepts
    engine.knowledge_base.add_concept(
        "concept_1",
        "Client-Server Architecture",
        Domain.TECHNOLOGY,
        "Separation of concerns in networked systems",
        importance=0.9,
    )

    # Initialize agent
    expertise = engine.initialize_agent_expertise("agent_1", Domain.TECHNOLOGY)
    print(f"Expertise: {expertise.level.name}")

    # Progress expertise
    engine.progress_expertise("exp_agent_1_technology", problems_solved=5)
    expertise = engine.get_agent_expertise("exp_agent_1_technology")
    print(f"After progress: {expertise.problems_solved} problems")

    # Learning path
    path = engine.generate_learning_path("exp_agent_1_technology")
    print(f"Learning path: {json.dumps(path, indent=2)}")

    # Domain summary
    summary = engine.knowledge_base.get_domain_summary(Domain.TECHNOLOGY)
    print(f"Summary: {json.dumps(summary, indent=2, default=str)}")
