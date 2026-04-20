# Query MCP — Product Brief

## One-Liner

A conversational database interface that turns natural language questions into SQL, executes them, and returns human-readable answers — delivered as both an MCP server and a REST API.

---

## Problem

Accessing data in PostgreSQL requires SQL knowledge. Business users, analysts, and non-technical stakeholders depend on engineers to write queries or build dashboards for every data question. This creates bottlenecks, delays decisions, and underutilizes existing data assets.

## Solution

**Query MCP** lets users ask database questions in plain language. The system generates SQL, runs it safely, and returns both raw results and a natural language summary. It supports multi-turn conversations — follow-up questions like "filter those by Hanoi" or "show me the top 5" resolve context from prior exchanges.

---

## How It Works

```
User: "What are the most expensive drugs in Ho Chi Minh City?"
  → LLM generates SQL
  → System executes against PostgreSQL
  → LLM summarizes results
  → User gets: SQL + data table + plain language answer
```

**Architecture:**

```
Client (Claude Desktop / Web App / API consumer)
    ↓
MCP Server / REST API  (server.py)
    ↓
Text-to-SQL Engine  (text_to_sql.py)
    ├── LLM Provider (Gemini / Z.ai / Anthropic)
    └── Conversation Context Manager
    ↓
Database Service  (db_service.py)
    ↓
PostgreSQL
```

---

## Core Capabilities

| Capability | Description |
|---|---|
| **Natural language → SQL** | Converts questions to PostgreSQL queries via LLM |
| **Execute + summarize** | Runs generated SQL and returns a human-readable answer |
| **Multi-turn conversations** | Session-aware context — follow-ups resolve references from prior messages |
| **Multi-language** | Auto-detects user language (Vietnamese, English confirmed) |
| **Pluggable LLM providers** | Gemini (default), Z.ai, Anthropic Claude — switchable per-request |
| **Schema introspection** | Auto-discovers tables, columns, types, comments for LLM context |
| **Query history & audit** | Every query logged with provider, model, execution time, success/failure |
| **Dual interface** | MCP protocol (for Claude Desktop) + REST API (for web/mobile apps) |
| **Clarification flow** | When a question is ambiguous, asks the user to rephrase instead of guessing |

---

## API Surface

### MCP Tools (Claude Desktop integration)

- `ask` — Full pipeline: generate SQL → execute → summarize → answer
- `generate_sql` — SQL generation only
- `execute_sql` — Run pre-written SQL
- `text_to_sql_execute` — Generate + execute without summarization

### REST Endpoints (HTTP mode)

| Endpoint | Method | Purpose |
|---|---|---|
| `/api/ask` | POST | Full pipeline with natural language answer |
| `/api/query` | POST | Generate + execute (raw results) |
| `/api/sql` | POST | Generate SQL only |
| `/api/execute` | POST | Execute raw SQL |
| `/api/tables` | GET | List all tables with metadata |
| `/api/tables/{id}` | GET | Table schema details |
| `/api/tables/{id}/data` | GET | Paginated table data |
| `/api/tables/{id}/stats` | GET | Statistical summaries |
| `/api/columns/{ref}` | GET | Column list for autocomplete |
| `/api/query/history` | GET | Query audit log |
| `/health` | GET | Health check |

---

## Tech Stack

| Layer | Technology |
|---|---|
| Language | Python 3.11 |
| Protocol | FastMCP 0.7.1 |
| LLM | Google Gemini, Z.ai, Anthropic Claude |
| Database | PostgreSQL 15+ |
| Migrations | Alembic + SQLAlchemy |
| HTTP | Starlette (via FastMCP) |
| Containerization | Docker, Docker Compose |
| Deployment | Cloud Run (GCP), Docker, systemd |

---

## Primary Use Case

**Vietnamese drug procurement data** (`medicine_bid` — 42 columns)

Source: *Danh muc thuoc trung thau* (national drug bid catalogue). Fields include drug name, active ingredient, manufacturer, price, province, facility, contract dates, bid type, and registration number. Deduplication via PostgreSQL generated hash column.

The system is table-agnostic — any PostgreSQL table can be queried. Sample tables (`items`, `users`, `orders`) included for testing.

---

## Key Design Decisions

1. **Best-effort logging** — Query history never blocks the main request path
2. **SQL injection prevention** — All queries parameterized; identifier escaping via psycopg2 `sql` module
3. **Auto LIMIT enforcement** — Prevents unbounded result sets
4. **Per-request LLM override** — Use cheap providers for simple queries, premium for complex ones
5. **Context manager DB access** — All connections auto-close; no resource leaks possible
6. **Generated deduplication hash** — Database-level uniqueness, no application logic needed

---

## Current Status

### Built
- Full text-to-SQL pipeline (generate → execute → summarize)
- Multi-turn conversation with session persistence
- 3 LLM providers (Gemini, Z.ai, Anthropic)
- REST API with schema inspection, pagination, statistics
- Alembic migration system
- Docker Compose dev environment
- Cloud Run deployment with auto-migration
- Unit tests for conversation context

### Not Yet Built
- Authentication / authorization
- Connection pooling
- Rate limiting
- Query result caching
- Storing context to DB
- Query optimization suggestions
- Result visualization

---

## Deployment

| Environment | Method |
|---|---|
| Local (MCP) | `python src/server.py` (stdio) |
| Local (HTTP) | `python src/server.py http 8001` |
| Docker | `docker-compose -f docker/docker-compose.yml up` |
| Production | Cloud Run with Alembic auto-migration |

**Config**: Environment variables (`QUERY_MCP_API_KEY`) + config file (`~/.query-mcp/config.json`)

---

## Target Users

1. **Business analysts** — Query procurement data without SQL
2. **Government officials** — Access drug bid data via natural language
3. **Developers** — Integrate conversational DB access into apps via REST API
4. **Claude Desktop users** — Query databases directly from Claude via MCP
