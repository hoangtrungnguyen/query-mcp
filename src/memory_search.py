"""Memory search and retrieval system"""

import json
from pathlib import Path
from datetime import datetime
from typing import Optional, List, Dict, Any
from dataclasses import dataclass, field
from enum import Enum

SEARCH_DIR = Path.home() / ".memory-mcp" / "memory-search"
SEARCH_DIR.mkdir(exist_ok=True, parents=True)


class SearchStrategy(Enum):
    """Search strategies"""
    KEYWORD = "keyword"
    SEMANTIC = "semantic"
    HYBRID = "hybrid"
    TEMPORAL = "temporal"


@dataclass
class SearchResult:
    """Search result entry"""
    result_id: str
    conversation_id: str
    relevance_score: float
    snippet: str
    source_type: str = "conversation"
    matched_on: str = ""  # What matched
    created_at: str = ""

    def __post_init__(self):
        if not self.created_at:
            self.created_at = datetime.now().isoformat()

    def to_dict(self) -> Dict:
        return {
            "conversation_id": self.conversation_id,
            "relevance": round(self.relevance_score, 2),
            "snippet": self.snippet[:100],
            "matched_on": self.matched_on,
        }


@dataclass
class ConversationIndex:
    """Index for searchable conversation data"""
    conversation_id: str
    keywords: List[str] = field(default_factory=list)
    topics: List[str] = field(default_factory=list)
    entities: List[str] = field(default_factory=list)
    summary: str = ""
    embedding_hash: int = 0  # For semantic search
    turn_count: int = 0
    indexed_at: str = ""

    def __post_init__(self):
        if not self.indexed_at:
            self.indexed_at = datetime.now().isoformat()

    def to_dict(self) -> Dict:
        return {
            "conversation_id": self.conversation_id,
            "keywords": len(self.keywords),
            "topics": len(self.topics),
            "entities": len(self.entities),
        }


class MemoryIndexer:
    """Index conversations for search"""

    def __init__(self):
        self.indices: Dict[str, ConversationIndex] = {}

    def index_conversation(
        self,
        conversation_id: str,
        text: str,
        entities: List[str] = None,
    ) -> ConversationIndex:
        """Index conversation"""
        # Extract keywords
        words = text.lower().split()
        keywords = [w for w in words if len(w) > 3][:20]

        # Extract topics (simple heuristic)
        topic_words = ["python", "learning", "question", "problem", "solution"]
        topics = [t for t in topic_words if t in text.lower()]

        index = ConversationIndex(
            conversation_id=conversation_id,
            keywords=keywords,
            topics=topics,
            entities=entities or [],
            summary=text[:200],
        )

        self.indices[conversation_id] = index
        return index

    def search_by_keyword(
        self,
        query: str,
        top_k: int = 5,
    ) -> List[SearchResult]:
        """Search by keywords"""
        query_words = set(query.lower().split())
        results = []

        for conv_id, index in self.indices.items():
            matches = len(set(index.keywords) & query_words)
            if matches > 0:
                score = matches / len(query_words)
                result = SearchResult(
                    result_id=f"res_{conv_id}",
                    conversation_id=conv_id,
                    relevance_score=score,
                    snippet=index.summary,
                    matched_on="keywords",
                )
                results.append(result)

        return sorted(results, key=lambda x: x.relevance_score, reverse=True)[:top_k]

    def search_by_topic(
        self,
        query: str,
        top_k: int = 5,
    ) -> List[SearchResult]:
        """Search by topics"""
        query_lower = query.lower()
        results = []

        for conv_id, index in self.indices.items():
            for topic in index.topics:
                if topic in query_lower:
                    result = SearchResult(
                        result_id=f"res_{conv_id}",
                        conversation_id=conv_id,
                        relevance_score=0.8,
                        snippet=index.summary,
                        matched_on=f"topic: {topic}",
                    )
                    results.append(result)
                    break

        return results[:top_k]

    def search_by_entity(
        self,
        entity: str,
        top_k: int = 5,
    ) -> List[SearchResult]:
        """Search by entities"""
        results = []

        for conv_id, index in self.indices.items():
            if entity in index.entities:
                result = SearchResult(
                    result_id=f"res_{conv_id}",
                    conversation_id=conv_id,
                    relevance_score=0.9,
                    snippet=index.summary,
                    matched_on=f"entity: {entity}",
                )
                results.append(result)

        return results[:top_k]


class MemorySearchEngine:
    """Search over memory"""

    def __init__(self):
        self.indexer = MemoryIndexer()

    def index_conversation(
        self,
        conversation_id: str,
        text: str,
    ) -> Dict:
        """Index conversation"""
        index = self.indexer.index_conversation(conversation_id, text)
        return index.to_dict()

    def search(
        self,
        query: str,
        strategy: str = "hybrid",
        top_k: int = 5,
    ) -> Dict:
        """Search memory"""
        results = []

        if strategy in ["keyword", "hybrid"]:
            results.extend(self.indexer.search_by_keyword(query, top_k))

        if strategy in ["semantic", "hybrid"]:
            results.extend(self.indexer.search_by_topic(query, top_k))

        # Deduplicate and sort
        unique = {}
        for r in results:
            if r.conversation_id not in unique or r.relevance_score > unique[r.conversation_id].relevance_score:
                unique[r.conversation_id] = r

        sorted_results = sorted(unique.values(), key=lambda x: x.relevance_score, reverse=True)[:top_k]

        return {
            "query": query,
            "strategy": strategy,
            "results": [r.to_dict() for r in sorted_results],
            "count": len(sorted_results),
        }


# Global engine
search_engine = MemorySearchEngine()


def index_conversation(conversation_id: str, text: str) -> dict:
    """Index conversation"""
    return search_engine.index_conversation(conversation_id, text)


def search_memory(query: str, strategy: str = "hybrid") -> dict:
    """Search memory"""
    return search_engine.search(query, strategy)
