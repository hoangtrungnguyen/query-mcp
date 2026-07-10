"""Query MCP — knowledge-base retrieval server (Phase 1).

Answers come from markdown files in the KB directory. The client LLM drives
the loop: read the index, pick docs, read them, answer with citations.
"""

import os
import re
import logging
from pathlib import Path

from fastmcp import FastMCP

logging.basicConfig(level=logging.INFO, format="[%(levelname)s] %(asctime)s - %(message)s")
logger = logging.getLogger(__name__)

KB_DIR = Path(os.environ.get("KB_DIR", Path(__file__).resolve().parent.parent / "kb"))
INDEX_FILE = "_index.md"
MAX_SEARCH_RESULTS = 20
SNIPPET_CONTEXT_LINES = 2

mcp = FastMCP(
    "Query MCP (KB)",
    instructions=(
        "Answer questions from the markdown knowledge base. "
        "Start from the kb://index resource (or read_doc('_index.md')), pick the most "
        "relevant doc(s), read them with read_doc, and answer citing the doc path and "
        "heading. Quote code/curl snippets verbatim — never reconstruct them. "
        "If no doc covers the question, say so and name the closest doc."
    ),
)


def _resolve(path: str) -> Path:
    """Resolve a KB-relative path, refusing escapes outside KB_DIR."""
    target = (KB_DIR / path).resolve()
    if not target.is_relative_to(KB_DIR.resolve()):
        raise ValueError(f"Path escapes knowledge base: {path}")
    return target


@mcp.tool
def read_doc(path: str) -> str:
    """Read a markdown document from the knowledge base.

    Args:
        path: Doc path relative to the KB root, as listed in the index
              (e.g. "howto/onboarding.md" or "_index.md").
    """
    target = _resolve(path)
    if not target.is_file():
        available = ", ".join(
            sorted(str(p.relative_to(KB_DIR)) for p in KB_DIR.rglob("*.md"))[:10]
        )
        return f"ERROR: '{path}' not found. Available docs include: {available}"
    return target.read_text(encoding="utf-8")


@mcp.tool
def search_kb(query: str) -> str:
    """Search the knowledge base for a keyword or regex.

    Returns matching doc paths with line numbers and surrounding context.
    Case-insensitive. Use when the index doesn't make the right doc obvious.

    Args:
        query: Keyword or regular expression to search for.
    """
    try:
        pattern = re.compile(query, re.IGNORECASE)
    except re.error:
        pattern = re.compile(re.escape(query), re.IGNORECASE)

    results = []
    for doc in sorted(KB_DIR.rglob("*.md")):
        if doc.name == INDEX_FILE:
            continue
        rel = doc.relative_to(KB_DIR)
        lines = doc.read_text(encoding="utf-8", errors="replace").splitlines()
        for i, line in enumerate(lines):
            if pattern.search(line):
                lo = max(0, i - SNIPPET_CONTEXT_LINES)
                hi = min(len(lines), i + SNIPPET_CONTEXT_LINES + 1)
                snippet = "\n".join(lines[lo:hi])
                results.append(f"## {rel}:{i + 1}\n{snippet}")
                break  # one hit per doc keeps output scannable; read_doc for detail
        if len(results) >= MAX_SEARCH_RESULTS:
            break

    if not results:
        return f"No matches for '{query}'. Try broader keywords or read_doc('_index.md')."
    return "\n\n".join(results)


@mcp.resource("kb://index")
def kb_index() -> str:
    """The knowledge-base index: one line per doc (path + summary)."""
    index = KB_DIR / INDEX_FILE
    if index.is_file():
        return index.read_text(encoding="utf-8")
    docs = "\n".join(f"- {p.relative_to(KB_DIR)}" for p in sorted(KB_DIR.rglob("*.md")))
    return f"# KB Index (unbuilt — run scripts/build_index.py)\n\n{docs}"


if __name__ == "__main__":
    logger.info("Serving KB from %s (%d docs)", KB_DIR, len(list(KB_DIR.rglob("*.md"))))
    mcp.run()
