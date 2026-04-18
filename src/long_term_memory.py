"""Long-term memory and cross-session continuity for agents"""

import json
from pathlib import Path
from datetime import datetime, timedelta
from typing import Optional, List, Dict, Any
from dataclasses import dataclass, field
from enum import Enum
import math

MEMORY_DIR = Path.home() / ".memory-mcp" / "long-term-memory"
MEMORY_DIR.mkdir(exist_ok=True, parents=True)


class MemoryType(Enum):
    """Types of long-term memories"""
    EPISODIC = "episodic"  # Specific conversations/events
    SEMANTIC = "semantic"  # Facts and knowledge
    PROCEDURAL = "procedural"  # Skills and capabilities
    AUTOBIOGRAPHICAL = "autobiographical"  # Agent's own narrative


class MemoryStrength(Enum):
    """Memory retention strength"""
    VERY_WEAK = 0.1
    WEAK = 0.3
    MODERATE = 0.5
    STRONG = 0.7
    VERY_STRONG = 0.9


@dataclass
class MemoryTrace:
    """Single memory item"""
    trace_id: str
    memory_type: MemoryType
    content: str
    metadata: Dict[str, Any] = field(default_factory=dict)
    strength: float = 0.8
    last_accessed: str = ""
    access_count: int = 0
    created_at: str = ""
    related_traces: List[str] = field(default_factory=list)

    def __post_init__(self):
        if not self.created_at:
            self.created_at = datetime.now().isoformat()
        if not self.last_accessed:
            self.last_accessed = self.created_at

    def get_retention_strength(self) -> float:
        """Calculate current retention (Ebbinghaus forgetting curve)"""
        # Strength decays over time without access
        days_since_creation = (
            datetime.now() - datetime.fromisoformat(self.created_at)
        ).days
        days_since_access = (
            datetime.now() - datetime.fromisoformat(self.last_accessed)
        ).days

        # Forgetting curve: R = e^(-t/S) where t=time, S=strength
        decay_factor = math.exp(-days_since_access / max(1, self.strength * 10))
        return self.strength * decay_factor

    def refresh(self):
        """Update memory through recall (strengthens retention)"""
        self.last_accessed = datetime.now().isoformat()
        self.access_count += 1
        self.strength = min(0.99, self.strength * 1.1)  # Strengthen by 10%

    def to_dict(self) -> Dict:
        """Serialize memory"""
        return {
            "trace_id": self.trace_id,
            "memory_type": self.memory_type.value,
            "content": self.content,
            "strength": self.strength,
            "retention": self.get_retention_strength(),
            "access_count": self.access_count,
            "created_at": self.created_at,
            "metadata": self.metadata,
        }


@dataclass
class PersonaState:
    """Agent's evolving persona"""
    persona_id: str
    agent_id: str
    traits: Dict[str, float]  # trait -> strength (0-1)
    values: List[str]
    communication_style: str
    knowledge_domains: Dict[str, float]  # domain -> expertise (0-1)
    skill_levels: Dict[str, float]  # skill -> level (0-100)
    created_at: str = ""
    last_updated: str = ""

    def __post_init__(self):
        if not self.created_at:
            self.created_at = datetime.now().isoformat()
        if not self.last_updated:
            self.last_updated = self.created_at

    def update_trait(self, trait: str, adjustment: float):
        """Update personality trait"""
        if trait not in self.traits:
            self.traits[trait] = 0.5
        self.traits[trait] = max(0.0, min(1.0, self.traits[trait] + adjustment))
        self.last_updated = datetime.now().isoformat()

    def update_skill(self, skill: str, improvement: float):
        """Update skill level"""
        if skill not in self.skill_levels:
            self.skill_levels[skill] = 0.0
        self.skill_levels[skill] = min(100.0, self.skill_levels[skill] + improvement)
        self.last_updated = datetime.now().isoformat()

    def to_dict(self) -> Dict:
        """Serialize persona"""
        return {
            "persona_id": self.persona_id,
            "traits": self.traits,
            "values": self.values,
            "communication_style": self.communication_style,
            "knowledge_domains": self.knowledge_domains,
            "skill_levels": self.skill_levels,
            "created_at": self.created_at,
            "last_updated": self.last_updated,
        }


class MemoryConsolidation:
    """Consolidate and organize memories"""

    @staticmethod
    def identify_key_memories(traces: List[MemoryTrace], top_n: int = 5) -> List[MemoryTrace]:
        """Identify most important memories"""
        scored = [
            (t, t.get_retention_strength() * (t.access_count + 1))
            for t in traces
        ]
        return [t for t, _ in sorted(scored, key=lambda x: x[1], reverse=True)[:top_n]]

    @staticmethod
    def detect_narrative_themes(traces: List[MemoryTrace]) -> List[str]:
        """Extract narrative themes from memories"""
        themes = []
        content_words = " ".join(t.content for t in traces).lower().split()

        # Simple heuristic: common noun phrases
        common_words = {}
        for word in content_words:
            common_words[word] = common_words.get(word, 0) + 1

        # Get top words as themes
        for word, count in sorted(common_words.items(), key=lambda x: x[1], reverse=True)[:5]:
            if count > 2:  # Appears multiple times
                themes.append(word)

        return themes

    @staticmethod
    def consolidate_episodic_memories(traces: List[MemoryTrace]) -> Dict[str, Any]:
        """Consolidate episodic memories into abstract knowledge"""
        # Group by metadata patterns
        grouped = {}
        for trace in traces:
            if trace.memory_type != MemoryType.EPISODIC:
                continue

            key = tuple(sorted(trace.metadata.items()))
            if key not in grouped:
                grouped[key] = []
            grouped[key].append(trace)

        # Summarize patterns
        patterns = {}
        for key, group in grouped.items():
            if len(group) >= 3:  # Pattern if repeated 3+ times
                patterns[str(key)] = {
                    "frequency": len(group),
                    "examples": [t.content[:50] for t in group[:3]],
                }

        return patterns


class LongTermMemoryManager:
    """Manage agent long-term memory"""

    def __init__(self):
        self.traces: Dict[str, MemoryTrace] = {}
        self.personas: Dict[str, PersonaState] = {}
        self.consolidation = MemoryConsolidation()

    def store_memory(
        self,
        trace_id: str,
        memory_type: MemoryType,
        content: str,
        metadata: Optional[Dict] = None,
        strength: float = 0.8,
    ) -> MemoryTrace:
        """Store new memory"""
        trace = MemoryTrace(
            trace_id=trace_id,
            memory_type=memory_type,
            content=content,
            metadata=metadata or {},
            strength=strength,
        )
        self.traces[trace_id] = trace
        return trace

    def recall_memory(self, trace_id: str) -> Optional[MemoryTrace]:
        """Recall memory and strengthen it"""
        if trace_id not in self.traces:
            return None

        trace = self.traces[trace_id]
        trace.refresh()
        return trace

    def search_memories(
        self,
        query: str,
        memory_type: Optional[MemoryType] = None,
        min_strength: float = 0.3,
    ) -> List[MemoryTrace]:
        """Search memories by content"""
        results = []

        for trace in self.traces.values():
            if trace.get_retention_strength() < min_strength:
                continue

            if memory_type and trace.memory_type != memory_type:
                continue

            if query.lower() in trace.content.lower():
                results.append(trace)

        return results

    def create_persona(
        self,
        persona_id: str,
        agent_id: str,
        traits: Optional[Dict] = None,
    ) -> PersonaState:
        """Create agent persona"""
        persona = PersonaState(
            persona_id=persona_id,
            agent_id=agent_id,
            traits=traits or {},
            values=[],
            communication_style="neutral",
        )
        self.personas[persona_id] = persona
        return persona

    def get_agent_persona(self, agent_id: str) -> Optional[PersonaState]:
        """Get agent's current persona"""
        for persona in self.personas.values():
            if persona.agent_id == agent_id:
                return persona
        return None

    def consolidate_memories(self, agent_id: str) -> Dict[str, Any]:
        """Consolidate agent's memories"""
        agent_traces = [
            t for t in self.traces.values()
            if t.metadata.get("agent_id") == agent_id
        ]

        key_memories = self.consolidation.identify_key_memories(agent_traces)
        themes = self.consolidation.detect_narrative_themes(agent_traces)
        patterns = self.consolidation.consolidate_episodic_memories(agent_traces)

        return {
            "agent_id": agent_id,
            "total_memories": len(agent_traces),
            "key_memories": len(key_memories),
            "narrative_themes": themes,
            "discovered_patterns": len(patterns),
            "key_memory_ids": [m.trace_id for m in key_memories],
        }

    def detect_personality_drift(self, persona_id: str) -> Optional[Dict]:
        """Detect changes in personality over time"""
        if persona_id not in self.personas:
            return None

        persona = self.personas[persona_id]

        # Simple detection: check if traits changed significantly
        time_since_update = (
            datetime.now() - datetime.fromisoformat(persona.last_updated)
        ).days

        if time_since_update == 0:
            return None

        # Detect drift (high variance in trait changes)
        trait_variance = (
            sum(abs(v - 0.5) for v in persona.traits.values()) / len(persona.traits)
            if persona.traits else 0
        )

        drift_detected = trait_variance > 0.3  # Significant drift

        return {
            "persona_id": persona_id,
            "drift_detected": drift_detected,
            "days_since_update": time_since_update,
            "trait_variance": trait_variance,
        }

    def get_memory_health_report(self, agent_id: str) -> Dict[str, Any]:
        """Get memory health for agent"""
        agent_traces = [
            t for t in self.traces.values()
            if t.metadata.get("agent_id") == agent_id
        ]

        if not agent_traces:
            return {"status": "no_memories", "agent_id": agent_id}

        retention_scores = [t.get_retention_strength() for t in agent_traces]
        avg_retention = sum(retention_scores) / len(retention_scores)

        fading_memories = [t for t in agent_traces if t.get_retention_strength() < 0.3]

        return {
            "agent_id": agent_id,
            "total_memories": len(agent_traces),
            "avg_retention": avg_retention,
            "fading_count": len(fading_memories),
            "health_status": "healthy" if avg_retention > 0.6 else "degrading",
            "recommendation": (
                "Consolidate and review memories" if len(fading_memories) > len(agent_traces) * 0.3
                else "Memory health is good"
            ),
        }


# Global manager
ltm_manager = LongTermMemoryManager()


# MCP Tools (add to memory_server.py)

def store_long_term_memory(
    trace_id: str,
    memory_type: str,
    content: str,
    metadata: dict = None,
) -> dict:
    """Store memory"""
    trace = ltm_manager.store_memory(
        trace_id,
        MemoryType(memory_type),
        content,
        metadata,
    )
    return trace.to_dict()


def recall_long_term_memory(trace_id: str) -> dict:
    """Recall memory"""
    trace = ltm_manager.recall_memory(trace_id)
    return trace.to_dict() if trace else {"error": "Memory not found"}


def search_long_term_memories(query: str, memory_type: str = None) -> dict:
    """Search memories"""
    results = ltm_manager.search_memories(
        query,
        MemoryType(memory_type) if memory_type else None,
    )
    return {
        "query": query,
        "results": [r.to_dict() for r in results],
        "count": len(results),
    }


def create_agent_persona(agent_id: str, traits: dict = None) -> dict:
    """Create persona"""
    persona = ltm_manager.create_persona(f"persona_{agent_id}", agent_id, traits)
    return persona.to_dict()


def consolidate_agent_memories(agent_id: str) -> dict:
    """Consolidate memories"""
    return ltm_manager.consolidate_memories(agent_id)


def detect_personality_drift(agent_id: str) -> dict:
    """Detect personality drift"""
    persona = ltm_manager.get_agent_persona(agent_id)
    if persona:
        drift = ltm_manager.detect_personality_drift(persona.persona_id)
        return drift or {"status": "no_drift"}
    return {"error": "Persona not found"}


def get_memory_health(agent_id: str) -> dict:
    """Get memory health"""
    return ltm_manager.get_memory_health_report(agent_id)


if __name__ == "__main__":
    # Test long-term memory
    manager = LongTermMemoryManager()

    # Store memory
    trace = manager.store_memory(
        "mem_1",
        MemoryType.EPISODIC,
        "User asked about Python",
        {"agent_id": "agent_1", "topic": "python"},
    )
    print(f"Stored: {trace.trace_id}")

    # Recall memory
    recalled = manager.recall_memory("mem_1")
    print(f"Recalled: {recalled.content}")

    # Create persona
    persona = manager.create_persona("persona_1", "agent_1")
    persona.update_trait("helpfulness", 0.1)
    print(f"Persona created: {persona.persona_id}")

    # Consolidate
    consolidation = manager.consolidate_memories("agent_1")
    print(f"Consolidation: {json.dumps(consolidation, indent=2)}")
