"""Import Claude Code conversation history into memory"""

import json
from pathlib import Path
from typing import Optional
from memory_server import episodic, semantic

CLAUDE_PROJECTS_DIR = Path.home() / ".claude" / "projects"


def parse_claude_jsonl(filepath: Path) -> list:
    """Parse Claude Code JSONL conversation file"""
    messages = []
    if not filepath.exists():
        return messages

    with open(filepath) as f:
        for line in f:
            if not line.strip():
                continue
            try:
                msg = json.loads(line)
                messages.append(msg)
            except json.JSONDecodeError:
                continue
    return messages


def ingest_claude_conversation(
    project_dir: str, agent_id: str, limit: Optional[int] = None
) -> int:
    """
    Ingest Claude Code conversation history into episodic memory.

    Args:
        project_dir: Encoded project directory name (e.g., "-home-htnguyen-Space-query-mcp")
        agent_id: Agent identifier for memory storage
        limit: Max messages to import (None = all)

    Returns:
        Count of messages imported
    """
    jsonl_path = CLAUDE_PROJECTS_DIR / project_dir / "CLAUDE_CODE_CONVERSATION.jsonl"

    if not jsonl_path.exists():
        # Try to find any .jsonl files in the project dir
        project_path = CLAUDE_PROJECTS_DIR / project_dir
        if project_path.exists():
            jsonl_files = list(project_path.glob("*.jsonl"))
            if jsonl_files:
                jsonl_path = jsonl_files[0]
            else:
                return 0
        else:
            return 0

    messages = parse_claude_jsonl(jsonl_path)
    if limit:
        messages = messages[:limit]

    count = 0
    for msg in messages:
        role = msg.get("role", "user")
        content = msg.get("content", "")

        # Handle Claude Code message format
        if isinstance(content, list):
            # Multipart content: combine all text parts
            content = " | ".join(
                part.get("text", "") for part in content if part.get("type") == "text"
            )

        if content:
            episodic.store_message(
                agent_id=agent_id,
                role=role,
                content=content,
                metadata={
                    "source": "claude-code",
                    "project": project_dir,
                    "original_id": msg.get("id"),
                    "timestamp": msg.get("createdAt"),
                },
            )
            count += 1

    return count


def list_claude_projects() -> list:
    """List all Claude Code project directories"""
    if not CLAUDE_PROJECTS_DIR.exists():
        return []

    projects = []
    for project_dir in CLAUDE_PROJECTS_DIR.iterdir():
        if project_dir.is_dir():
            jsonl_files = list(project_dir.glob("*.jsonl"))
            if jsonl_files:
                projects.append(
                    {
                        "name": project_dir.name,
                        "path": str(project_dir),
                        "conversation_files": [f.name for f in jsonl_files],
                    }
                )

    return projects


def extract_facts_from_conversation(messages: list, category: str = "learned") -> list:
    """
    Extract semantic facts from a conversation.
    Simple heuristic: look for sentences with "learned", "discovered", "pattern", etc.
    """
    facts = []
    keywords = ["learned", "discovered", "pattern", "rule", "principle", "note", "remember"]

    for msg in messages:
        content = msg.get("content", "")
        if isinstance(content, str):
            for keyword in keywords:
                if keyword in content.lower():
                    # Extract surrounding sentences (naive approach)
                    sentences = content.split(".")
                    for sentence in sentences:
                        if keyword in sentence.lower():
                            fact = sentence.strip()
                            if len(fact) > 10:  # Filter short noise
                                facts.append(
                                    {
                                        "fact": fact,
                                        "category": category,
                                        "confidence": 0.7,
                                    }
                                )
                            break

    return facts


if __name__ == "__main__":
    # CLI for testing
    import sys

    if len(sys.argv) < 2:
        print("Usage: python claude_code_importer.py <project_dir> [agent_id] [--limit N]")
        print("\nAvailable Claude projects:")
        for proj in list_claude_projects():
            print(f"  {proj['name']}: {', '.join(proj['conversation_files'])}")
        sys.exit(1)

    project_dir = sys.argv[1]
    agent_id = sys.argv[2] if len(sys.argv) > 2 else f"claude_{project_dir}"
    limit = None

    if "--limit" in sys.argv:
        idx = sys.argv.index("--limit")
        if idx + 1 < len(sys.argv):
            limit = int(sys.argv[idx + 1])

    count = ingest_claude_conversation(project_dir, agent_id, limit)
    print(f"Imported {count} messages into {agent_id}")
