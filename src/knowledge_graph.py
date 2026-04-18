"""Knowledge graph integration for grounding conversations and augmenting responses"""

import json
from pathlib import Path
from datetime import datetime
from typing import Optional, List, Dict, Any, Set, Tuple
from dataclasses import dataclass, field
from enum import Enum

KG_DIR = Path.home() / ".memory-mcp" / "knowledge-graph"
KG_DIR.mkdir(exist_ok=True, parents=True)


class EntityType(Enum):
    """Types of entities in knowledge graph"""
    PERSON = "person"
    ORGANIZATION = "organization"
    LOCATION = "location"
    CONCEPT = "concept"
    EVENT = "event"
    PRODUCT = "product"
    TIME = "time"


class RelationType(Enum):
    """Types of relationships"""
    IS_A = "is_a"  # Type hierarchy
    PART_OF = "part_of"  # Composition
    RELATED_TO = "related_to"  # General relation
    CAUSED_BY = "caused_by"  # Causality
    INFLUENCES = "influences"  # Effect
    CONTRADICTS = "contradicts"  # Opposition
    EXTENDS = "extends"  # Enhancement


@dataclass
class Entity:
    """Knowledge graph entity"""
    entity_id: str
    name: str
    entity_type: EntityType
    description: str
    aliases: List[str] = field(default_factory=list)
    properties: Dict[str, Any] = field(default_factory=dict)
    confidence: float = 0.8
    source: Optional[str] = None
    created_at: str = ""

    def __post_init__(self):
        if not self.created_at:
            self.created_at = datetime.now().isoformat()

    def to_dict(self) -> Dict:
        """Serialize entity"""
        return {
            "entity_id": self.entity_id,
            "name": self.name,
            "entity_type": self.entity_type.value,
            "description": self.description,
            "aliases": self.aliases,
            "properties": self.properties,
            "confidence": self.confidence,
            "source": self.source,
            "created_at": self.created_at,
        }


@dataclass
class Relation:
    """Relationship between entities"""
    relation_id: str
    source_entity_id: str
    target_entity_id: str
    relation_type: RelationType
    description: str
    confidence: float = 0.8
    evidence: List[str] = field(default_factory=list)  # Supporting text
    created_at: str = ""

    def __post_init__(self):
        if not self.created_at:
            self.created_at = datetime.now().isoformat()

    def to_dict(self) -> Dict:
        """Serialize relation"""
        return {
            "relation_id": self.relation_id,
            "source_entity_id": self.source_entity_id,
            "target_entity_id": self.target_entity_id,
            "relation_type": self.relation_type.value,
            "description": self.description,
            "confidence": self.confidence,
            "evidence": self.evidence,
            "created_at": self.created_at,
        }


@dataclass
class Fact:
    """Grounded fact in knowledge graph"""
    fact_id: str
    statement: str
    subject_entity_id: str
    object_entity_id: Optional[str]
    property_value: Optional[Any]
    confidence: float
    source: str
    supporting_evidence: List[str] = field(default_factory=list)
    timestamp: str = ""

    def __post_init__(self):
        if not self.timestamp:
            self.timestamp = datetime.now().isoformat()

    def to_dict(self) -> Dict:
        """Serialize fact"""
        return {
            "fact_id": self.fact_id,
            "statement": self.statement,
            "subject_entity_id": self.subject_entity_id,
            "object_entity_id": self.object_entity_id,
            "property_value": self.property_value,
            "confidence": self.confidence,
            "source": self.source,
            "supporting_evidence": self.supporting_evidence,
            "timestamp": self.timestamp,
        }


class EntityExtractor:
    """Extract entities from conversation text"""

    ENTITY_KEYWORDS = {
        EntityType.PERSON: ["person", "user", "agent", "author", "creator", "founder"],
        EntityType.ORGANIZATION: ["company", "org", "team", "group", "organization"],
        EntityType.LOCATION: ["location", "place", "city", "country", "region"],
        EntityType.CONCEPT: ["concept", "idea", "theory", "principle"],
        EntityType.PRODUCT: ["product", "tool", "service", "platform"],
        EntityType.EVENT: ["event", "incident", "meeting", "conference"],
    }

    @staticmethod
    def extract_entities(text: str) -> List[Dict[str, Any]]:
        """Extract entities from text"""
        entities = []
        words = text.split()

        for i, word in enumerate(words):
            # Simple heuristic: capitalized words might be entities
            if word[0].isupper() and len(word) > 2:
                # Context-based type detection
                entity_type = EntityType.CONCEPT  # Default

                surrounding = " ".join(words[max(0, i - 2): min(len(words), i + 3)]).lower()

                for etype, keywords in EntityExtractor.ENTITY_KEYWORDS.items():
                    if any(kw in surrounding for kw in keywords):
                        entity_type = etype
                        break

                entities.append({
                    "name": word,
                    "type": entity_type.value,
                    "position": i,
                    "confidence": 0.6,
                })

        return entities


class RelationExtractor:
    """Extract relations between entities"""

    RELATION_PATTERNS = {
        RelationType.IS_A: ["is", "is a", "is an", "is the"],
        RelationType.PART_OF: ["part of", "member of", "component of"],
        RelationType.RELATED_TO: ["related to", "connected to", "associated with"],
        RelationType.CAUSED_BY: ["caused by", "due to", "resulted from"],
        RelationType.INFLUENCES: ["influences", "affects", "impacts"],
    }

    @staticmethod
    def extract_relations(text: str) -> List[Dict[str, Any]]:
        """Extract relations from text"""
        relations = []
        text_lower = text.lower()

        for relation_type, patterns in RelationExtractor.RELATION_PATTERNS.items():
            for pattern in patterns:
                if pattern in text_lower:
                    relations.append({
                        "type": relation_type.value,
                        "pattern": pattern,
                        "confidence": 0.5,
                    })

        return relations


class KnowledgeGraph:
    """Manage knowledge graph structure"""

    def __init__(self):
        self.entities: Dict[str, Entity] = {}
        self.relations: Dict[str, Relation] = {}
        self.facts: Dict[str, Fact] = {}
        self.entity_index: Dict[str, Set[str]] = {}  # name -> entity_ids
        self.extractor = EntityExtractor()
        self.rel_extractor = RelationExtractor()

    def add_entity(self, entity: Entity) -> bool:
        """Add entity to graph"""
        self.entities[entity.entity_id] = entity

        # Index by name and aliases
        if entity.name not in self.entity_index:
            self.entity_index[entity.name] = set()
        self.entity_index[entity.name].add(entity.entity_id)

        for alias in entity.aliases:
            if alias not in self.entity_index:
                self.entity_index[alias] = set()
            self.entity_index[alias].add(entity.entity_id)

        return True

    def add_relation(self, relation: Relation) -> bool:
        """Add relation to graph"""
        # Verify entities exist
        if (
            relation.source_entity_id not in self.entities
            or relation.target_entity_id not in self.entities
        ):
            return False

        self.relations[relation.relation_id] = relation
        return True

    def add_fact(self, fact: Fact) -> bool:
        """Add grounded fact"""
        if fact.subject_entity_id not in self.entities:
            return False

        if fact.object_entity_id and fact.object_entity_id not in self.entities:
            return False

        self.facts[fact.fact_id] = fact
        return True

    def find_entity(self, name: str) -> Optional[Entity]:
        """Find entity by name"""
        entity_ids = self.entity_index.get(name, set())
        if entity_ids:
            return self.entities[list(entity_ids)[0]]
        return None

    def get_related_entities(
        self,
        entity_id: str,
        relation_type: Optional[RelationType] = None,
    ) -> List[Entity]:
        """Get entities related to given entity"""
        related = []

        for relation in self.relations.values():
            if relation.source_entity_id == entity_id:
                if relation_type and relation.relation_type != relation_type:
                    continue
                if relation.target_entity_id in self.entities:
                    related.append(self.entities[relation.target_entity_id])

        return related

    def extract_and_link(self, text: str, source: str = "conversation") -> Dict[str, Any]:
        """Extract entities and relations from text"""
        extracted_entities = self.extractor.extract_entities(text)
        extracted_relations = self.rel_extractor.extract_relations(text)

        created_entities = []
        for ent in extracted_entities:
            entity_id = f"entity_{hash(ent['name'])}"
            if entity_id not in self.entities:
                entity = Entity(
                    entity_id=entity_id,
                    name=ent["name"],
                    entity_type=EntityType(ent["type"]),
                    description=f"Extracted from: {source}",
                    confidence=ent["confidence"],
                    source=source,
                )
                self.add_entity(entity)
                created_entities.append(entity)

        return {
            "entities_created": len(created_entities),
            "relations_found": len(extracted_relations),
            "entities": [e.to_dict() for e in created_entities],
            "relations": extracted_relations,
        }

    def ground_statement(self, statement: str) -> Optional[Fact]:
        """Check if statement is grounded in knowledge graph"""
        # Simple heuristic: check if statement entities exist in graph
        words = statement.split()

        for word in words:
            if word[0].isupper() and len(word) > 2:
                entity = self.find_entity(word)
                if entity:
                    # Statement mentions known entity
                    fact_id = f"fact_{hash(statement)}"
                    fact = Fact(
                        fact_id=fact_id,
                        statement=statement,
                        subject_entity_id=entity.entity_id,
                        object_entity_id=None,
                        property_value=None,
                        confidence=0.7,
                        source="grounding_check",
                    )
                    self.add_fact(fact)
                    return fact

        return None

    def get_graph_stats(self) -> Dict[str, Any]:
        """Get knowledge graph statistics"""
        return {
            "total_entities": len(self.entities),
            "entity_types": {
                etype.value: sum(
                    1 for e in self.entities.values()
                    if e.entity_type == etype
                )
                for etype in EntityType
            },
            "total_relations": len(self.relations),
            "relation_types": {
                rtype.value: sum(
                    1 for r in self.relations.values()
                    if r.relation_type == rtype
                )
                for rtype in RelationType
            },
            "total_facts": len(self.facts),
            "avg_entity_confidence": (
                sum(e.confidence for e in self.entities.values()) / len(self.entities)
                if self.entities
                else 0
            ),
        }

    def augment_response(self, response: str, topic: str) -> Dict[str, Any]:
        """Augment response with knowledge graph facts"""
        # Find entities mentioned in response
        augmentations = []

        for entity in self.entities.values():
            if entity.name in response:
                related = self.get_related_entities(entity.entity_id)
                if related:
                    augmentations.append({
                        "entity": entity.name,
                        "related_entities": [e.name for e in related],
                        "properties": entity.properties,
                    })

        return {
            "original_response": response,
            "augmentations": augmentations,
            "knowledge_enhanced": len(augmentations) > 0,
        }

    def save_graph(self) -> str:
        """Save knowledge graph to disk"""
        graph_data = {
            "entities": [e.to_dict() for e in self.entities.values()],
            "relations": [r.to_dict() for r in self.relations.values()],
            "facts": [f.to_dict() for f in self.facts.values()],
            "stats": self.get_graph_stats(),
        }

        filepath = KG_DIR / "knowledge_graph.json"
        with open(filepath, "w") as f:
            json.dump(graph_data, f, indent=2)

        return str(filepath)


# Global knowledge graph
knowledge_graph = KnowledgeGraph()


# MCP Tools (add to memory_server.py)

def add_knowledge_entity(
    entity_id: str,
    name: str,
    entity_type: str,
    description: str,
    aliases: list = None,
) -> dict:
    """Add entity to knowledge graph"""
    entity = Entity(
        entity_id=entity_id,
        name=name,
        entity_type=EntityType(entity_type),
        description=description,
        aliases=aliases or [],
    )
    success = knowledge_graph.add_entity(entity)
    return {"entity_id": entity_id, "added": success}


def create_knowledge_relation(
    relation_id: str,
    source_entity_id: str,
    target_entity_id: str,
    relation_type: str,
    description: str,
) -> dict:
    """Create relation between entities"""
    relation = Relation(
        relation_id=relation_id,
        source_entity_id=source_entity_id,
        target_entity_id=target_entity_id,
        relation_type=RelationType(relation_type),
        description=description,
    )
    success = knowledge_graph.add_relation(relation)
    return {"relation_id": relation_id, "created": success}


def extract_and_link_entities(text: str) -> dict:
    """Extract entities from text and link to graph"""
    return knowledge_graph.extract_and_link(text)


def ground_statement_in_kb(statement: str) -> dict:
    """Check if statement is grounded in knowledge"""
    fact = knowledge_graph.ground_statement(statement)
    return {
        "grounded": fact is not None,
        "fact": fact.to_dict() if fact else None,
    }


def augment_with_knowledge(response: str, topic: str = "") -> dict:
    """Augment response with knowledge graph"""
    return knowledge_graph.augment_response(response, topic)


def get_knowledge_graph_stats() -> dict:
    """Get knowledge graph statistics"""
    return knowledge_graph.get_graph_stats()


if __name__ == "__main__":
    # Test knowledge graph
    graph = KnowledgeGraph()

    # Add entities
    entity_a = Entity(
        entity_id="e1",
        name="Python",
        entity_type=EntityType.PRODUCT,
        description="Programming language",
    )
    graph.add_entity(entity_a)

    entity_b = Entity(
        entity_id="e2",
        name="Guido van Rossum",
        entity_type=EntityType.PERSON,
        description="Creator of Python",
    )
    graph.add_entity(entity_b)

    # Add relation
    relation = Relation(
        relation_id="r1",
        source_entity_id="e2",
        target_entity_id="e1",
        relation_type=RelationType.EXTENDS,
        description="Created Python",
    )
    graph.add_relation(relation)

    # Get stats
    stats = graph.get_graph_stats()
    print(f"Graph stats: {json.dumps(stats, indent=2)}")
