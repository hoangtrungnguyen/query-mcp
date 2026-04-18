"""Context persistence and memory compression across conversation turns"""

import json
from pathlib import Path
from datetime import datetime
from typing import Optional, List, Dict, Any
from dataclasses import dataclass, field
from enum import Enum

PERSISTENCE_DIR = Path.home() / ".memory-mcp" / "context-persistence"
PERSISTENCE_DIR.mkdir(exist_ok=True, parents=True)


class ImportanceLevel(Enum):
    """Importance of context element"""
    CRITICAL = "critical"  # Must preserve (e.g., user identity)
    HIGH = "high"  # Important for understanding (e.g., stated goals)
    MEDIUM = "medium"  # Helpful context (e.g., previous attempts)
    LOW = "low"  # Background info (e.g., mentioned once)


class CompressionStrategy(Enum):
    """How to compress context"""
    SUMMARIZE = "summarize"  # Reduce to key points
    EXTRACT = "extract"  # Keep only essentials
    ABSTRACT = "abstract"  # Generalize concrete details
    ELIMINATE = "eliminate"  # Remove entirely


@dataclass
class ContextElement:
    """Single element in conversation context"""
    element_id: str
    element_type: str  # entity, fact, goal, assumption, etc.
    content: str
    turn_introduced: int
    importance: ImportanceLevel
    references: int = 0  # How many times referenced
    last_referenced: int = 0
    compression_strategy: CompressionStrategy = CompressionStrategy.SUMMARIZE

    def to_dict(self) -> Dict:
        """Serialize element"""
        return {
            "element_id": self.element_id,
            "type": self.element_type,
            "importance": self.importance.value,
            "references": self.references,
        }


@dataclass
class ContextCache:
    """Cache of conversation context"""
    cache_id: str
    turn_num: int
    elements: List[ContextElement] = field(default_factory=list)
    total_tokens: int = 0
    compressed_at: Optional[str] = None
    compression_ratio: float = 1.0  # 1.0 = no compression

    def to_dict(self) -> Dict:
        """Serialize cache"""
        return {
            "cache_id": self.cache_id,
            "turn": self.turn_num,
            "elements": len(self.elements),
            "tokens": self.total_tokens,
            "compression_ratio": round(self.compression_ratio, 2),
        }


class ContextCompressor:
    """Compress context to prevent information loss"""

    COMPRESSION_RATIOS = {
        CompressionStrategy.SUMMARIZE: 0.7,  # Keep 70%
        CompressionStrategy.EXTRACT: 0.5,  # Keep 50%
        CompressionStrategy.ABSTRACT: 0.6,  # Keep 60%
        CompressionStrategy.ELIMINATE: 0.0,  # Keep 0%
    }

    @staticmethod
    def estimate_token_count(text: str) -> int:
        """Estimate tokens (rough: ~4 chars per token)"""
        return len(text) // 4

    @staticmethod
    def compress_element(
        element: ContextElement,
        context: str = "",
    ) -> str:
        """Compress single context element"""
        strategy = element.compression_strategy

        if strategy == CompressionStrategy.SUMMARIZE:
            # Keep first sentence + key info
            sentences = element.content.split(".")
            return sentences[0] + "."

        elif strategy == CompressionStrategy.EXTRACT:
            # Keep only 50% - first + last sentence
            sentences = element.content.split(".")
            if len(sentences) > 2:
                return sentences[0] + ". ... " + sentences[-1] + "."
            return sentences[0] + "."

        elif strategy == CompressionStrategy.ABSTRACT:
            # Generalize
            text = element.content.lower()
            if "user said" in text:
                return "User expressed this point."
            elif "the system" in text:
                return "System property noted."
            else:
                return "Context recorded."

        else:  # ELIMINATE
            return ""

    @staticmethod
    def calculate_importance(
        element: ContextElement,
        current_turn: int,
    ) -> ImportanceLevel:
        """Recalculate importance based on usage"""
        turns_since_intro = current_turn - element.turn_introduced
        turns_since_ref = current_turn - element.last_referenced

        # Elements referenced recently = high importance
        if turns_since_ref <= 2:
            return ImportanceLevel.HIGH

        # Elements never referenced = low importance
        if element.references == 0:
            return ImportanceLevel.LOW

        # Old elements with few references = medium
        if turns_since_intro > 10 and element.references < 2:
            return ImportanceLevel.MEDIUM

        return element.importance


class ContextManager:
    """Manage persistent context across turns"""

    def __init__(self):
        self.caches: Dict[str, ContextCache] = {}
        self.all_elements: Dict[str, ContextElement] = {}
        self.compression_history: List[Dict] = []

    def add_element(
        self,
        cache_id: str,
        element_type: str,
        content: str,
        importance: ImportanceLevel,
        turn_num: int,
    ) -> ContextElement:
        """Add element to context"""
        element = ContextElement(
            element_id=f"elem_{len(self.all_elements)}",
            element_type=element_type,
            content=content,
            turn_introduced=turn_num,
            importance=importance,
        )

        self.all_elements[element.element_id] = element

        if cache_id not in self.caches:
            self.caches[cache_id] = ContextCache(
                cache_id=cache_id,
                turn_num=turn_num,
            )

        cache = self.caches[cache_id]
        cache.elements.append(element)
        cache.total_tokens += ContextCompressor.estimate_token_count(content)

        return element

    def reference_element(self, element_id: str, turn_num: int):
        """Record element reference"""
        if element_id in self.all_elements:
            element = self.all_elements[element_id]
            element.references += 1
            element.last_referenced = turn_num

    def compress_context(
        self,
        cache_id: str,
        current_turn: int,
        max_tokens: int = 2000,
    ) -> Dict[str, Any]:
        """Compress context if exceeds token limit"""
        if cache_id not in self.caches:
            return {"error": "Cache not found"}

        cache = self.caches[cache_id]

        if cache.total_tokens <= max_tokens:
            return {"compressed": False, "tokens": cache.total_tokens}

        # Recalculate importance
        for element in cache.elements:
            element.importance = ContextCompressor.calculate_importance(
                element,
                current_turn,
            )

        # Sort by importance
        cache.elements.sort(
            key=lambda e: (e.importance.value, e.references),
            reverse=True,
        )

        # Compress low-importance elements
        original_tokens = cache.total_tokens
        for element in cache.elements:
            if cache.total_tokens <= max_tokens:
                break

            if element.importance in [ImportanceLevel.LOW, ImportanceLevel.MEDIUM]:
                compressed = ContextCompressor.compress_element(element)
                original_size = ContextCompressor.estimate_token_count(element.content)
                new_size = ContextCompressor.estimate_token_count(compressed)

                element.content = compressed
                cache.total_tokens -= (original_size - new_size)

        cache.compressed_at = datetime.now().isoformat()
        cache.compression_ratio = cache.total_tokens / original_tokens

        self.compression_history.append({
            "cache_id": cache_id,
            "original_tokens": original_tokens,
            "compressed_tokens": cache.total_tokens,
            "ratio": cache.compression_ratio,
            "turn": current_turn,
        })

        return {
            "compressed": True,
            "original_tokens": original_tokens,
            "compressed_tokens": cache.total_tokens,
            "ratio": round(cache.compression_ratio, 2),
        }

    def recover_context(
        self,
        cache_id: str,
        turn_num: int,
    ) -> List[str]:
        """Recover context at specific turn"""
        if cache_id not in self.caches:
            return []

        cache = self.caches[cache_id]

        # Get elements introduced before this turn
        relevant = [
            e.content for e in cache.elements
            if e.turn_introduced <= turn_num
        ]

        return relevant

    def get_cache_summary(self, cache_id: str) -> Optional[Dict]:
        """Get cache summary"""
        cache = self.caches.get(cache_id)
        if not cache:
            return None

        critical = [e for e in cache.elements if e.importance == ImportanceLevel.CRITICAL]
        compressed = [e for e in cache.elements if e.content != e.content]  # Simplified

        return {
            "cache_id": cache_id,
            "elements": len(cache.elements),
            "critical_elements": len(critical),
            "tokens": cache.total_tokens,
            "compressed": cache.compressed_at is not None,
            "compression_ratio": round(cache.compression_ratio, 2),
        }


class PersistenceManager:
    """Manage context persistence across conversations"""

    def __init__(self):
        self.managers: Dict[str, ContextManager] = {}

    def create_manager(self, manager_id: str) -> ContextManager:
        """Create context manager"""
        manager = ContextManager()
        self.managers[manager_id] = manager
        return manager

    def get_manager(self, manager_id: str) -> Optional[ContextManager]:
        """Get manager"""
        return self.managers.get(manager_id)


# Global manager
persistence_manager = PersistenceManager()


# MCP Tools

def create_persistence_manager(manager_id: str) -> dict:
    """Create persistence manager"""
    manager = persistence_manager.create_manager(manager_id)
    return {"manager_id": manager_id, "created": True}


def add_context_element(
    manager_id: str,
    cache_id: str,
    element_type: str,
    content: str,
    importance: str,
    turn_num: int,
) -> dict:
    """Add context element"""
    manager = persistence_manager.get_manager(manager_id)
    if not manager:
        return {"error": "Manager not found"}

    try:
        imp = ImportanceLevel(importance)
        element = manager.add_element(cache_id, element_type, content, imp, turn_num)
        return element.to_dict()
    except ValueError:
        return {"error": f"Invalid importance: {importance}"}


def reference_element(manager_id: str, element_id: str, turn_num: int) -> dict:
    """Record element reference"""
    manager = persistence_manager.get_manager(manager_id)
    if not manager:
        return {"error": "Manager not found"}

    manager.reference_element(element_id, turn_num)
    return {"recorded": True}


def compress_context(
    manager_id: str,
    cache_id: str,
    current_turn: int,
    max_tokens: int = 2000,
) -> dict:
    """Compress context"""
    manager = persistence_manager.get_manager(manager_id)
    if not manager:
        return {"error": "Manager not found"}

    return manager.compress_context(cache_id, current_turn, max_tokens)


def get_cache_summary(manager_id: str, cache_id: str) -> dict:
    """Get cache summary"""
    manager = persistence_manager.get_manager(manager_id)
    if not manager:
        return {"error": "Manager not found"}

    summary = manager.get_cache_summary(cache_id)
    return summary or {"error": "Cache not found"}


if __name__ == "__main__":
    manager = ContextManager()

    # Add elements
    manager.add_element("cache_1", "entity", "User is John", ImportanceLevel.CRITICAL, 1)
    manager.add_element("cache_1", "goal", "Learn Python", ImportanceLevel.HIGH, 2)
    manager.add_element("cache_1", "fact", "Python is popular", ImportanceLevel.LOW, 3)

    # Reference elements
    manager.reference_element("elem_0", 5)

    # Get summary
    summary = manager.get_cache_summary("cache_1")
    print(f"Summary: {json.dumps(summary, indent=2)}")

    # Compress
    result = manager.compress_context("cache_1", 10, max_tokens=100)
    print(f"Compression: {json.dumps(result, indent=2)}")
