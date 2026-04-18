"""Conversation indexing and search implementation"""

import os
from pathlib import Path
from typing import Optional
from difflib import SequenceMatcher

from memory_server import episodic, semantic

# Try to use Whoosh for full-text search (optional dependency)
try:
    from whoosh.fields import Schema, TEXT, ID, DATETIME
    from whoosh.index import create_in
    from whoosh.qparser import QueryParser
    WHOOSH_AVAILABLE = True
except ImportError:
    WHOOSH_AVAILABLE = False


INDEX_DIR = Path.home() / ".memory-mcp" / "indexes"
INDEX_DIR.mkdir(exist_ok=True, parents=True)


class ConversationIndex:
    """Full-text search index for conversations"""

    def __init__(self, index_name: str = "conversations"):
        self.index_name = index_name
        self.index_dir = INDEX_DIR / index_name
        self.index_dir.mkdir(exist_ok=True)

        if WHOOSH_AVAILABLE:
            self._init_whoosh()
        self.message_cache = {}  # Fallback in-memory index

    def _init_whoosh(self):
        """Initialize Whoosh index"""
        schema = Schema(
            id=ID(stored=True),
            agent_id=ID(stored=True),
            role=TEXT(stored=True),
            content=TEXT(stored=True),
            timestamp=DATETIME(stored=True),
        )

        if not os.path.exists(self.index_dir / "WRITELOCK"):
            self.index = create_in(self.index_dir, schema)
        else:
            # Try to open existing index
            try:
                from whoosh.index import open_dir
                self.index = open_dir(self.index_dir)
            except:
                self.index = None

    def index_message(self, message: dict):
        """Add a message to the index"""
        self.message_cache[message.get("id")] = message

        if WHOOSH_AVAILABLE and hasattr(self, "index") and self.index:
            try:
                writer = self.index.writer()
                writer.add_document(
                    id=message.get("id"),
                    agent_id=message.get("agent_id"),
                    role=message.get("role"),
                    content=message.get("content"),
                    timestamp=message.get("timestamp"),
                )
                writer.commit()
            except Exception as e:
                print(f"Whoosh indexing error: {e}")

    def build_index(self, agent_id: str):
        """Build index from episodic memory"""
        messages = episodic.get_messages(agent_id, limit=1000)
        for msg in messages:
            self.index_message(msg)

    def search_content(self, query: str, agent_id: Optional[str] = None) -> list:
        """Full-text search with Whoosh fallback"""
        results = []

        if WHOOSH_AVAILABLE and hasattr(self, "index") and self.index:
            try:
                with self.index.searcher() as searcher:
                    qp = QueryParser("content", self.index.schema)
                    parsed_query = qp.parse(query)
                    hits = searcher.search(parsed_query, limit=20)

                    for hit in hits:
                        if not agent_id or hit["agent_id"] == agent_id:
                            results.append(
                                {
                                    "id": hit["id"],
                                    "content": hit["content"],
                                    "role": hit["role"],
                                    "score": hit.score,
                                }
                            )
                    return results
            except Exception as e:
                print(f"Whoosh search error: {e}")

        # Fallback: simple substring search
        for msg_id, msg in self.message_cache.items():
            if agent_id and msg.get("agent_id") != agent_id:
                continue
            if query.lower() in msg.get("content", "").lower():
                results.append(
                    {
                        "id": msg_id,
                        "content": msg.get("content"),
                        "role": msg.get("role"),
                        "score": 1.0,
                    }
                )

        return results


class FuzzyMatcher:
    """Fuzzy search using Levenshtein distance"""

    @staticmethod
    def levenshtein_distance(s1: str, s2: str) -> int:
        """Calculate Levenshtein distance between two strings"""
        if len(s1) < len(s2):
            return FuzzyMatcher.levenshtein_distance(s2, s1)

        if len(s2) == 0:
            return len(s1)

        previous_row = range(len(s2) + 1)
        for i, c1 in enumerate(s1):
            current_row = [i + 1]
            for j, c2 in enumerate(s2):
                insertions = previous_row[j + 1] + 1
                deletions = current_row[j] + 1
                substitutions = previous_row[j] + (c1 != c2)
                current_row.append(min(insertions, deletions, substitutions))
            previous_row = current_row

        return previous_row[-1]

    @staticmethod
    def similarity(s1: str, s2: str) -> float:
        """Return similarity score (0.0 to 1.0)"""
        distance = FuzzyMatcher.levenshtein_distance(s1, s2)
        max_len = max(len(s1), len(s2))
        return 1.0 - (distance / max_len) if max_len > 0 else 1.0

    @staticmethod
    def fuzzy_search(query: str, candidates: list, threshold: float = 0.7) -> list:
        """Search candidates with fuzzy matching"""
        results = []
        for candidate in candidates:
            score = FuzzyMatcher.similarity(query.lower(), candidate.lower())
            if score >= threshold:
                results.append({"candidate": candidate, "score": score})

        return sorted(results, key=lambda x: x["score"], reverse=True)


class ConversationFilter:
    """Filter conversations by metadata"""

    @staticmethod
    def by_role(messages: list, role: str) -> list:
        """Filter by role (user/assistant)"""
        return [m for m in messages if m.get("role") == role]

    @staticmethod
    def by_date_range(messages: list, start_date: str, end_date: str) -> list:
        """Filter by timestamp range (ISO format)"""
        return [
            m
            for m in messages
            if start_date <= m.get("timestamp", "") <= end_date
        ]

    @staticmethod
    def by_tags(messages: list, tags: list) -> list:
        """Filter by metadata tags"""
        results = []
        for msg in messages:
            msg_tags = msg.get("metadata", {}).get("tags", [])
            if any(tag in msg_tags for tag in tags):
                results.append(msg)
        return results

    @staticmethod
    def by_length(messages: list, min_len: int = 0, max_len: int = 10000) -> list:
        """Filter by content length"""
        return [
            m
            for m in messages
            if min_len <= len(m.get("content", "")) <= max_len
        ]


# Global index instance
conversation_index = ConversationIndex()


# MCP Tools (add to memory_server.py)

def search_conversations_fulltext(agent_id: str, query: str) -> list:
    """Full-text search conversations"""
    return conversation_index.search_content(query, agent_id)


def fuzzy_search_conversations(agent_id: str, query: str, threshold: float = 0.7) -> list:
    """Fuzzy search message content"""
    messages = episodic.get_messages(agent_id, limit=100)
    candidates = [m.get("content", "") for m in messages]
    fuzzy_results = FuzzyMatcher.fuzzy_search(query, candidates, threshold)

    results = []
    for i, fr in enumerate(fuzzy_results):
        results.append(
            {
                "index": i,
                "content": fr["candidate"],
                "score": fr["score"],
                "message": messages[candidates.index(fr["candidate"])],
            }
        )
    return results


def filter_conversations(
    agent_id: str,
    role: Optional[str] = None,
    start_date: Optional[str] = None,
    end_date: Optional[str] = None,
    tags: Optional[list] = None,
) -> list:
    """Filter conversations by multiple criteria"""
    messages = episodic.get_messages(agent_id, limit=1000)

    if role:
        messages = ConversationFilter.by_role(messages, role)

    if start_date and end_date:
        messages = ConversationFilter.by_date_range(messages, start_date, end_date)

    if tags:
        messages = ConversationFilter.by_tags(messages, tags)

    return messages


if __name__ == "__main__":
    # Test fuzzy search
    test_queries = ["conversatin", "mesage", "epsiode"]
    candidates = ["conversation", "message", "episode", "memory", "semantic"]

    for query in test_queries:
        results = FuzzyMatcher.fuzzy_search(query, candidates, 0.6)
        print(f"Query '{query}': {results}")
