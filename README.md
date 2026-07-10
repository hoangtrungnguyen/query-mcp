# Query MCP — Knowledge Base Retrieval

MCP server that answers questions from a markdown knowledge base (`kb/`): API curl
examples, business logic, schema notes, how-to guides.

## How it works

The client LLM drives the loop: read the KB index → pick docs → `read_doc` → answer
with citations. Snippets are quoted verbatim; questions the KB doesn't cover get an
honest "not documented".

## Tools

| Tool / resource | Purpose |
|---|---|
| `read_doc(path)` | Read a KB doc (path from the index) |
| `search_kb(query)` | Keyword/regex search across the KB |
| `kb://index` | Generated index — one line per doc |

## Usage

```bash
pip install -r requirements.txt
python scripts/build_index.py   # regenerate kb/_index.md after editing docs
python src/server.py            # run MCP server (KB_DIR env overrides ./kb)
```

## Roadmap

Phase 1 of a larger design (text-to-SQL fast path, LangGraph orchestration,
sandboxed analysis) — see the `query-mcp-design` repo. Previous text-to-SQL
implementation is archived on branch `archive/text-to-query-v.0.0`.
