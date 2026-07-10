"""Server-side KB answer agent: question -> Gemini + read tools -> cited answer.

Used by the web interface. MCP clients don't need this — they drive the loop
with their own model.
"""

import json
import os
from pathlib import Path

from google import genai
from google.genai import types

CONFIG_FILE = Path.home() / ".query-mcp" / "config.json"
MODEL = os.environ.get("KB_LLM_MODEL", "gemini-flash-latest")

SYSTEM_PROMPT = """You answer questions from a markdown knowledge base.

Rules:
- Start from the index below. Use read_doc to read the most relevant doc(s); use
  search_kb if the index doesn't make the right doc obvious. At most 3 tool calls.
- Cite the doc path (and heading) every answer is based on.
- Quote code/curl snippets VERBATIM from the docs — never reconstruct or extrapolate
  them. Keep placeholders like $GTW_TOKEN and <TD_ACCOUNT_ID> as written.
- If the KB doesn't cover the question, say "Not documented" and name the closest
  doc. Never guess.
- Answer in the user's language.

KB INDEX:
{index}
"""


def _api_key() -> str:
    key = os.environ.get("GEMINI_API_KEY") or os.environ.get("GOOGLE_API_KEY")
    if not key and CONFIG_FILE.exists():
        key = json.loads(CONFIG_FILE.read_text()).get("text_to_sql", {}).get("llm_api_key", "")
    if not key:
        raise RuntimeError("No Gemini key: set GEMINI_API_KEY or ~/.query-mcp/config.json")
    return key


def answer(question: str, read_doc, search_kb, index: str) -> str:
    """Answer a question against the KB. Tool errors are returned as strings so the
    model can recover instead of crashing the request."""

    def safe_read_doc(path: str) -> str:
        """Read a markdown document from the knowledge base by its index path."""
        try:
            return read_doc(path)
        except Exception as e:
            return f"ERROR: {e}"

    def safe_search_kb(query: str) -> str:
        """Search the knowledge base for a keyword or regex (case-insensitive)."""
        try:
            return search_kb(query)
        except Exception as e:
            return f"ERROR: {e}"

    client = genai.Client(api_key=_api_key())
    response = client.models.generate_content(
        model=MODEL,
        contents=question,
        config=types.GenerateContentConfig(
            system_instruction=SYSTEM_PROMPT.format(index=index),
            tools=[safe_read_doc, safe_search_kb],  # automatic function calling
            temperature=0.1,
        ),
    )
    return response.text or "No answer generated."
