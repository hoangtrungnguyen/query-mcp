"""Information extraction and knowledge structuring from conversations"""

import json
from pathlib import Path
from datetime import datetime
from typing import Optional, List, Dict, Any
from dataclasses import dataclass, field
from enum import Enum

EXTRACTION_DIR = Path.home() / ".memory-mcp" / "information-extraction"
EXTRACTION_DIR.mkdir(exist_ok=True, parents=True)


class EntityType(Enum):
    """Types of entities to extract"""
    PERSON = "person"
    ORGANIZATION = "organization"
    LOCATION = "location"
    PRODUCT = "product"
    DATE = "date"
    QUANTITY = "quantity"
    CONCEPT = "concept"


class RelationType(Enum):
    """Types of relationships"""
    PART_OF = "part_of"
    OWNED_BY = "owned_by"
    WORKS_FOR = "works_for"
    LOCATED_IN = "located_in"
    RELATED_TO = "related_to"
    CAUSES = "causes"
    SIMILAR_TO = "similar_to"


@dataclass
class Entity:
    """Extracted entity"""
    entity_id: str
    text: str
    entity_type: EntityType
    confidence: float
    context: str = ""  # Surrounding text
    source_turn: int = 0  # Which turn in conversation
    attributes: Dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> Dict:
        """Serialize entity"""
        return {
            "entity_id": self.entity_id,
            "text": self.text,
            "type": self.entity_type.value,
            "confidence": round(self.confidence, 2),
            "attributes": len(self.attributes),
        }


@dataclass
class Relationship:
    """Extracted relationship between entities"""
    relationship_id: str
    subject_entity: str  # entity_id
    object_entity: str  # entity_id
    relation_type: RelationType
    confidence: float
    evidence: str = ""  # Supporting text
    source_turn: int = 0

    def to_dict(self) -> Dict:
        """Serialize relationship"""
        return {
            "relationship_id": self.relationship_id,
            "type": self.relation_type.value,
            "confidence": round(self.confidence, 2),
        }


@dataclass
class ExtractedFact:
    """Extracted fact from conversation"""
    fact_id: str
    statement: str
    subject: str  # entity_id
    predicate: str  # What property/action
    object: str  # entity_id or value
    confidence: float
    source_turn: int = 0
    supporting_evidence: List[str] = field(default_factory=list)
    verified: bool = False

    def to_dict(self) -> Dict:
        """Serialize fact"""
        return {
            "fact_id": self.fact_id,
            "statement": self.statement[:100],
            "confidence": round(self.confidence, 2),
            "verified": self.verified,
            "evidence_items": len(self.supporting_evidence),
        }


class EntityExtractor:
    """Extract entities from text"""

    ENTITY_PATTERNS = {
        EntityType.PERSON: ["person", "author", "character", "someone", "user"],
        EntityType.ORGANIZATION: ["company", "organization", "team", "group", "organization"],
        EntityType.LOCATION: ["place", "city", "country", "location", "area"],
        EntityType.PRODUCT: ["product", "service", "tool", "application", "software"],
        EntityType.DATE: ["day", "month", "year", "time", "when"],
        EntityType.QUANTITY: ["number", "amount", "count", "size", "length"],
    }

    @staticmethod
    def extract_entities(text: str, turn: int = 0) -> List[Entity]:
        """Extract entities from text"""
        entities = []

        # Simple pattern-based extraction
        for entity_type, keywords in EntityExtractor.ENTITY_PATTERNS.items():
            for keyword in keywords:
                if keyword in text.lower():
                    # Extract text around keyword
                    idx = text.lower().find(keyword)
                    start = max(0, idx - 10)
                    end = min(len(text), idx + len(keyword) + 10)
                    context = text[start:end].strip()

                    entity = Entity(
                        entity_id=f"ent_{entity_type.value}_{len(entities)}",
                        text=keyword,
                        entity_type=entity_type,
                        confidence=0.6,
                        context=context,
                        source_turn=turn,
                    )
                    entities.append(entity)

        return entities


class RelationshipExtractor:
    """Extract relationships between entities"""

    RELATION_KEYWORDS = {
        RelationType.PART_OF: ["part of", "component", "member"],
        RelationType.OWNED_BY: ["owned by", "belongs to", "property"],
        RelationType.WORKS_FOR: ["works for", "employed by", "works at"],
        RelationType.LOCATED_IN: ["located in", "based in", "at"],
        RelationType.RELATED_TO: ["related to", "associated with", "connected"],
    }

    @staticmethod
    def extract_relationships(
        text: str,
        entities: List[Entity],
    ) -> List[Relationship]:
        """Extract relationships between entities"""
        relationships = []

        if len(entities) < 2:
            return relationships

        # Simple keyword-based relationship extraction
        for rel_type, keywords in RelationshipExtractor.RELATION_KEYWORDS.items():
            for keyword in keywords:
                if keyword in text.lower():
                    # Assume first two entities have this relationship
                    rel = Relationship(
                        relationship_id=f"rel_{len(relationships)}",
                        subject_entity=entities[0].entity_id,
                        object_entity=entities[1].entity_id if len(entities) > 1 else entities[0].entity_id,
                        relation_type=rel_type,
                        confidence=0.5,
                        evidence=keyword,
                    )
                    relationships.append(rel)
                    break

        return relationships


class FactExtractor:
    """Extract facts from conversation"""

    @staticmethod
    def extract_facts(
        text: str,
        entities: List[Entity],
        turn: int = 0,
    ) -> List[ExtractedFact]:
        """Extract facts from text"""
        facts = []

        # Simple heuristic: each sentence is a potential fact
        sentences = text.split(".")
        for sentence in sentences:
            if len(sentence.split()) > 3:  # At least 3 words
                fact = ExtractedFact(
                    fact_id=f"fact_{len(facts)}",
                    statement=sentence.strip(),
                    subject=entities[0].entity_id if entities else "unknown",
                    predicate="stated",
                    object=sentence.strip(),
                    confidence=0.7,
                    source_turn=turn,
                )
                facts.append(fact)

        return facts


class KnowledgeGraph:
    """Build knowledge graph from extracted information"""

    def __init__(self):
        self.entities: Dict[str, Entity] = {}
        self.relationships: Dict[str, Relationship] = {}
        self.facts: Dict[str, ExtractedFact] = {}

    def add_entity(self, entity: Entity):
        """Add entity to graph"""
        self.entities[entity.entity_id] = entity

    def add_relationship(self, relationship: Relationship):
        """Add relationship to graph"""
        self.relationships[relationship.relationship_id] = relationship

    def add_fact(self, fact: ExtractedFact):
        """Add fact to graph"""
        self.facts[fact.fact_id] = fact

    def get_entity_info(self, entity_id: str) -> Optional[Dict]:
        """Get all info about entity"""
        if entity_id not in self.entities:
            return None

        entity = self.entities[entity_id]

        # Find relationships
        related = [
            r for r in self.relationships.values()
            if r.subject_entity == entity_id or r.object_entity == entity_id
        ]

        # Find facts
        entity_facts = [
            f for f in self.facts.values()
            if f.subject == entity_id
        ]

        return {
            "entity": entity.to_dict(),
            "relationships": [r.to_dict() for r in related],
            "facts": [f.to_dict() for f in entity_facts],
        }

    def get_graph_summary(self) -> Dict[str, Any]:
        """Get graph summary"""
        return {
            "entities": len(self.entities),
            "relationships": len(self.relationships),
            "facts": len(self.facts),
            "entity_types": list(set(e.entity_type.value for e in self.entities.values())),
            "relation_types": list(set(r.relation_type.value for r in self.relationships.values())),
        }


class ExtractionEngine:
    """Extract and structure information from conversations"""

    def __init__(self):
        self.knowledge_graphs: Dict[str, KnowledgeGraph] = {}

    def create_graph(self, graph_id: str) -> KnowledgeGraph:
        """Create knowledge graph"""
        graph = KnowledgeGraph()
        self.knowledge_graphs[graph_id] = graph
        return graph

    def extract_from_turn(
        self,
        graph_id: str,
        text: str,
        turn: int,
    ) -> Dict[str, Any]:
        """Extract information from conversation turn"""
        if graph_id not in self.knowledge_graphs:
            return {"error": "Graph not found"}

        graph = self.knowledge_graphs[graph_id]

        # Extract entities
        entities = EntityExtractor.extract_entities(text, turn)
        for entity in entities:
            graph.add_entity(entity)

        # Extract relationships
        relationships = RelationshipExtractor.extract_relationships(text, entities)
        for rel in relationships:
            graph.add_relationship(rel)

        # Extract facts
        facts = FactExtractor.extract_facts(text, entities, turn)
        for fact in facts:
            graph.add_fact(fact)

        return {
            "entities": len(entities),
            "relationships": len(relationships),
            "facts": len(facts),
            "total_extracted": len(entities) + len(relationships) + len(facts),
        }

    def get_graph_info(self, graph_id: str) -> Optional[Dict]:
        """Get graph information"""
        if graph_id not in self.knowledge_graphs:
            return None

        graph = self.knowledge_graphs[graph_id]
        return graph.get_graph_summary()


class ExtractionManager:
    """Manage extraction across conversations"""

    def __init__(self):
        self.engines: Dict[str, ExtractionEngine] = {}

    def create_engine(self, engine_id: str) -> ExtractionEngine:
        """Create extraction engine"""
        engine = ExtractionEngine()
        self.engines[engine_id] = engine
        return engine

    def get_engine(self, engine_id: str) -> Optional[ExtractionEngine]:
        """Get engine"""
        return self.engines.get(engine_id)


# Global manager
extraction_manager = ExtractionManager()


# MCP Tools

def create_extraction_engine(engine_id: str) -> dict:
    """Create information extraction engine"""
    engine = extraction_manager.create_engine(engine_id)
    return {"engine_id": engine_id, "created": True}


def create_knowledge_graph(engine_id: str, graph_id: str) -> dict:
    """Create knowledge graph"""
    engine = extraction_manager.get_engine(engine_id)
    if not engine:
        return {"error": "Engine not found"}

    graph = engine.create_graph(graph_id)
    return {"graph_id": graph_id, "created": True}


def extract_from_turn(
    engine_id: str,
    graph_id: str,
    text: str,
    turn: int,
) -> dict:
    """Extract information from turn"""
    engine = extraction_manager.get_engine(engine_id)
    if not engine:
        return {"error": "Engine not found"}

    return engine.extract_from_turn(graph_id, text, turn)


def get_graph_summary(engine_id: str, graph_id: str) -> dict:
    """Get graph summary"""
    engine = extraction_manager.get_engine(engine_id)
    if not engine:
        return {"error": "Engine not found"}

    summary = engine.get_graph_info(graph_id)
    return summary or {"error": "Graph not found"}


if __name__ == "__main__":
    # Test information extraction
    engine = ExtractionEngine()
    graph = engine.create_graph("graph_1")

    # Extract from text
    text = "John works for Acme Corporation in New York"
    engine.extract_from_turn("graph_1", text, 1)

    # Summary
    summary = engine.get_graph_info("graph_1")
    print(f"Graph: {json.dumps(summary, indent=2)}")

    # Entity info
    entities = graph.entities
    if entities:
        entity_id = list(entities.keys())[0]
        info = graph.get_entity_info(entity_id)
        print(f"Entity info: {json.dumps(info, indent=2)}")
