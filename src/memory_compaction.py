"""Memory compaction and archival for context window optimization"""

import json
from pathlib import Path
from datetime import datetime, timedelta
from typing import Optional, List, Dict, Any
from memory_server import episodic, working

ARCHIVE_DIR = Path.home() / ".memory-mcp" / "archive"
ARCHIVE_DIR.mkdir(exist_ok=True, parents=True)


class TokenCounter:
    """Estimate token usage for conversation"""

    # Rough token estimates (varies by model)
    CHARS_PER_TOKEN = 4.0  # ~1 token per 4 chars
    OVERHEAD_PER_MESSAGE = 5  # roles, delimiters, etc.

    @staticmethod
    def estimate_tokens(text: str) -> int:
        """Estimate tokens in text"""
        return max(1, int(len(text) / TokenCounter.CHARS_PER_TOKEN))

    @staticmethod
    def estimate_conversation_tokens(messages: List[Dict]) -> int:
        """Estimate total tokens for conversation"""
        total = 0
        for msg in messages:
            content_tokens = TokenCounter.estimate_tokens(
                msg.get("content", "")
            )
            total += content_tokens + TokenCounter.OVERHEAD_PER_MESSAGE
        return total

    @staticmethod
    def count_by_role(messages: List[Dict]) -> Dict[str, int]:
        """Count tokens by role"""
        counts = {}
        for msg in messages:
            role = msg.get("role", "unknown")
            tokens = TokenCounter.estimate_tokens(msg.get("content", ""))
            counts[role] = counts.get(role, 0) + tokens
        return counts


class ConversationSummarizer:
    """Summarize conversations while preserving key information"""

    def __init__(self):
        self.summaries_dir = ARCHIVE_DIR / "summaries"
        self.summaries_dir.mkdir(exist_ok=True)

    def summarize_messages(
        self,
        messages: List[Dict],
        preserve_quotes: bool = True,
    ) -> Dict[str, Any]:
        """
        Create a summary of messages with key facts preserved.
        Simple heuristic-based approach (production would use LLM).
        """
        if not messages:
            return {"summary": "", "key_facts": [], "decisions": []}

        # Extract key sentences
        key_facts = []
        decisions = []
        quotes = []

        for msg in messages:
            content = msg.get("content", "")
            role = msg.get("role", "user")

            # Simple extraction: look for sentences with keywords
            keywords_facts = ["learned", "discovered", "found", "note", "important"]
            keywords_decisions = ["decided", "chose", "will", "plan", "agreed"]

            for keyword in keywords_facts:
                if keyword in content.lower():
                    sentences = content.split(".")
                    for sent in sentences:
                        if keyword in sent.lower() and len(sent) > 20:
                            # Direct quote for accuracy
                            quote = sent.strip()[:100]
                            if quote and quote not in key_facts:
                                key_facts.append(f'"{quote}"')
                            break

            for keyword in keywords_decisions:
                if keyword in content.lower():
                    sentences = content.split(".")
                    for sent in sentences:
                        if keyword in sent.lower() and len(sent) > 20:
                            quote = sent.strip()[:100]
                            if quote and quote not in decisions:
                                decisions.append(f'"{quote}"')
                            break

        # Build summary
        summary_text = f"""
Conversation Summary ({len(messages)} messages):
- Time period: {messages[0].get('timestamp', 'N/A')} to {messages[-1].get('timestamp', 'N/A')}
- Participants: {', '.join(set(m.get('role', 'unknown') for m in messages))}
- Key Facts: {key_facts[:5] if key_facts else 'None identified'}
- Decisions Made: {decisions[:5] if decisions else 'None identified'}
"""

        return {
            "summary": summary_text.strip(),
            "key_facts": key_facts[:5],
            "decisions": decisions[:5],
            "message_count": len(messages),
            "tokens_before": TokenCounter.estimate_conversation_tokens(messages),
        }

    def save_summary(
        self,
        agent_id: str,
        messages: List[Dict],
        summary: Dict,
    ) -> str:
        """Save summary and archived messages"""
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        archive_id = f"{agent_id}_{timestamp}"
        archive_file = self.summaries_dir / f"{archive_id}.json"

        archive_record = {
            "archive_id": archive_id,
            "agent_id": agent_id,
            "created_at": datetime.now().isoformat(),
            "summary": summary,
            "archived_messages": messages,
            "message_count": len(messages),
        }

        with open(archive_file, "w") as f:
            json.dump(archive_record, f, indent=2)

        return archive_id


class ArchiveManager:
    """Manage archival of old conversations"""

    def __init__(self):
        self.archive_dir = ARCHIVE_DIR / "conversations"
        self.archive_dir.mkdir(exist_ok=True)
        self.metadata_file = self.archive_dir / "manifest.jsonl"

    def archive_messages(
        self,
        agent_id: str,
        messages: List[Dict],
        reason: str = "manual",
    ) -> Dict[str, Any]:
        """Archive messages to cold storage"""
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        archive_id = f"{agent_id}_{timestamp}"
        archive_file = self.archive_dir / f"{archive_id}.jsonl"

        # Write messages to JSONL
        with open(archive_file, "w") as f:
            for msg in messages:
                f.write(json.dumps(msg) + "\n")

        # Record in manifest
        manifest_entry = {
            "archive_id": archive_id,
            "agent_id": agent_id,
            "archive_file": str(archive_file),
            "message_count": len(messages),
            "tokens": TokenCounter.estimate_conversation_tokens(messages),
            "reason": reason,
            "created_at": datetime.now().isoformat(),
            "date_range": {
                "start": messages[0].get("timestamp") if messages else None,
                "end": messages[-1].get("timestamp") if messages else None,
            },
        }

        with open(self.metadata_file, "a") as f:
            f.write(json.dumps(manifest_entry) + "\n")

        return manifest_entry

    def list_archives(self, agent_id: str) -> List[Dict]:
        """List archives for agent"""
        if not self.metadata_file.exists():
            return []

        archives = []
        with open(self.metadata_file) as f:
            for line in f:
                entry = json.loads(line)
                if entry.get("agent_id") == agent_id:
                    archives.append(entry)

        return sorted(archives, key=lambda x: x["created_at"], reverse=True)

    def retrieve_archive(self, archive_id: str) -> List[Dict]:
        """Retrieve archived messages"""
        # Find archive file from manifest
        if not self.metadata_file.exists():
            return []

        archive_file = None
        with open(self.metadata_file) as f:
            for line in f:
                entry = json.loads(line)
                if entry.get("archive_id") == archive_id:
                    archive_file = entry.get("archive_file")
                    break

        if not archive_file or not Path(archive_file).exists():
            return []

        # Read JSONL
        messages = []
        with open(archive_file) as f:
            for line in f:
                if line.strip():
                    messages.append(json.loads(line))

        return messages

    def cleanup_old_archives(self, agent_id: str, days: int = 30) -> int:
        """Delete archives older than N days"""
        cutoff = datetime.now() - timedelta(days=days)
        deleted = 0

        archives = self.list_archives(agent_id)
        for archive in archives:
            created = datetime.fromisoformat(archive["created_at"])
            if created < cutoff:
                archive_file = Path(archive["archive_file"])
                if archive_file.exists():
                    archive_file.unlink()
                    deleted += 1

        return deleted


class CompactionStrategy:
    """Progressive context window compaction"""

    def __init__(self, context_limit: int = 100000):
        self.context_limit = context_limit
        self.summarizer = ConversationSummarizer()
        self.archiver = ArchiveManager()

    def should_compact(self, messages: List[Dict]) -> bool:
        """Check if compaction is needed"""
        tokens = TokenCounter.estimate_conversation_tokens(messages)
        return tokens > (self.context_limit * 0.8)  # Trigger at 80%

    def apply_progressive_compaction(
        self,
        agent_id: str,
        messages: List[Dict],
    ) -> Dict[str, Any]:
        """
        Apply 3-tier progressive compaction:
        1. Trim tool results
        2. Summarize old sections
        3. Archive old messages
        """
        result = {
            "original_messages": len(messages),
            "original_tokens": TokenCounter.estimate_conversation_tokens(messages),
            "steps": [],
        }

        # Step 1: Trim tool results (remove long tool outputs)
        trimmed = self._trim_tool_results(messages)
        result["steps"].append({
            "step": "trim_tool_results",
            "messages_before": len(messages),
            "messages_after": len(trimmed),
            "tokens_saved": (
                TokenCounter.estimate_conversation_tokens(messages)
                - TokenCounter.estimate_conversation_tokens(trimmed)
            ),
        })

        # Check if still over limit
        if TokenCounter.estimate_conversation_tokens(trimmed) > (
            self.context_limit * 0.8
        ):
            # Step 2: Summarize old sections
            summarized, removed = self._summarize_old_section(agent_id, trimmed)
            summary = self.summarizer.summarize_messages(removed)
            self.summarizer.save_summary(agent_id, removed, summary)

            result["steps"].append({
                "step": "summarize_old_section",
                "messages_removed": len(removed),
                "summary_created": True,
                "tokens_saved": TokenCounter.estimate_conversation_tokens(removed),
            })

            messages = summarized

        # Check if still over limit
        if TokenCounter.estimate_conversation_tokens(messages) > (
            self.context_limit * 0.8
        ):
            # Step 3: Archive very old messages
            to_archive, remaining = self._split_by_age(messages, days=7)
            self.archiver.archive_messages(agent_id, to_archive, reason="compaction")

            result["steps"].append({
                "step": "archive_old_messages",
                "messages_archived": len(to_archive),
                "tokens_saved": TokenCounter.estimate_conversation_tokens(to_archive),
            })

            messages = remaining

        result["final_messages"] = len(messages)
        result["final_tokens"] = TokenCounter.estimate_conversation_tokens(messages)
        result["compacted"] = result["original_tokens"] > result["final_tokens"]

        return result

    def _trim_tool_results(self, messages: List[Dict]) -> List[Dict]:
        """Trim long tool results"""
        trimmed = []
        max_length = 500

        for msg in messages:
            content = msg.get("content", "")
            if len(content) > max_length and msg.get("role") == "assistant":
                msg = msg.copy()
                msg["content"] = content[:max_length] + "... [trimmed]"
            trimmed.append(msg)

        return trimmed

    def _summarize_old_section(
        self,
        agent_id: str,
        messages: List[Dict],
    ) -> tuple:
        """Extract and summarize oldest 30% of messages"""
        cutoff_idx = len(messages) // 3
        old_messages = messages[:cutoff_idx]
        recent_messages = messages[cutoff_idx:]

        return recent_messages, old_messages

    def _split_by_age(self, messages: List[Dict], days: int) -> tuple:
        """Split messages by age"""
        cutoff = datetime.now() - timedelta(days=days)
        old = []
        recent = []

        for msg in messages:
            try:
                msg_time = datetime.fromisoformat(msg.get("timestamp", ""))
                if msg_time < cutoff:
                    old.append(msg)
                else:
                    recent.append(msg)
            except:
                recent.append(msg)

        return old, recent


# Global instances
token_counter = TokenCounter()
summarizer = ConversationSummarizer()
archiver = ArchiveManager()
compactor = CompactionStrategy()


# MCP Tools (add to memory_server.py)

def estimate_tokens(text: str) -> int:
    """Estimate token count for text"""
    return token_counter.estimate_tokens(text)


def summarize_conversation(agent_id: str, limit: int = 50) -> dict:
    """Summarize recent conversation"""
    messages = episodic.get_messages(agent_id, limit=limit)
    summary = summarizer.summarize_messages(messages)
    return summary


def archive_old_messages(agent_id: str, days: int = 30) -> dict:
    """Archive messages older than N days"""
    messages = episodic.get_messages(agent_id, limit=1000)
    old, recent = compactor._split_by_age(messages, days=days)

    if old:
        result = archiver.archive_messages(agent_id, old, reason=f"older_than_{days}d")
        return result
    return {"status": "no_messages_to_archive"}


def compact_conversation(agent_id: str) -> dict:
    """Apply progressive compaction to conversation"""
    messages = episodic.get_messages(agent_id, limit=1000)
    return compactor.apply_progressive_compaction(agent_id, messages)


def list_archives(agent_id: str) -> list:
    """List all archives for agent"""
    return archiver.list_archives(agent_id)


def retrieve_archive(archive_id: str) -> list:
    """Retrieve archived messages"""
    return archiver.retrieve_archive(archive_id)


if __name__ == "__main__":
    # Test token counting
    test_text = "This is a test conversation message."
    tokens = token_counter.estimate_tokens(test_text)
    print(f"Text: {test_text}")
    print(f"Estimated tokens: {tokens}")

    # Test compaction
    messages = [
        {
            "id": "1",
            "role": "user",
            "content": "Hello, how are you?",
            "timestamp": (datetime.now() - timedelta(days=10)).isoformat(),
        },
        {
            "id": "2",
            "role": "assistant",
            "content": "I'm doing well. " * 50,  # Long response
            "timestamp": (datetime.now() - timedelta(days=10)).isoformat(),
        },
        {
            "id": "3",
            "role": "user",
            "content": "What's new?",
            "timestamp": datetime.now().isoformat(),
        },
    ]

    print(f"\nOriginal tokens: {token_counter.estimate_conversation_tokens(messages)}")
