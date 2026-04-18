# Query MCP

A Model Context Protocol (MCP) server that converts natural language queries into PostgreSQL SQL using multiple LLM providers. It bridges natural language understanding and relational database operations — letting users query databases without writing SQL.

---

## Table of Contents

1. [Architecture](#architecture)
2. [Features](#features)
3. [Setup](#setup)
4. [Configuration](#configuration)
5. [MCP Tools](#mcp-tools)
6. [REST API](#rest-api)
7. [Database Service](#database-service)
8. [Query History](#query-history)
9. [Migrations](#migrations)
10. [Deployment](#deployment)
11. [Troubleshooting](#troubleshooting)

---

## Architecture

```
User Request (Natural Language or HTTP)
          │
          ▼
  ┌───────────────────────────────────┐
  │         server.py (MCP + HTTP)    │
  │  ┌─────────────┐ ┌─────────────┐ │
  │  │  MCP stdio  │ │  HTTP REST  │ │
  │  │  (Claude)   │ │  (curl/web) │ │
  │  └─────────────┘ └─────────────┘ │
  └──────────────┬────────────────────┘
                 │
                 ▼
  ┌───────────────────────────────────┐
  │      text_to_sql.py (Engine)      │
  │  ┌──────────┐  ┌───────────────┐ │
  │  │  LLM API │  │ Schema Fetch  │ │
  │  │ (Gemini/ │  │ (introspect)  │ │
  │  │  Z.ai /  │  └───────────────┘ │
  │  │Anthropic)│                    │
  │  └──────────┘                    │
  └──────────────┬────────────────────┘
                 │
                 ▼
  ┌───────────────────────────────────┐
  │      db_service.py (DB Layer)     │
  │  Schema · Execution · History     │
  └──────────────┬────────────────────┘
                 │
                 ▼
          PostgreSQL Database
```

### Pipeline

The core workflow for a natural language query:

1. **Schema Discovery** — introspect the target table to build an LLM prompt with column types and names
2. **SQL Generation** — send schema + user question to the LLM; receive SQL or a `CLARIFY:` message when the query is ambiguous
3. **Execution** — run the generated SQL against PostgreSQL with parameterized queries
4. **Summarization** — optionally pass results back to the LLM for a natural language answer
5. **Audit Logging** — record query, SQL, timing, provider, and success status in `query_history`

---

## Features

| Category | Detail |
|---|---|
| **LLM Providers** | Google Gemini (default), Z.ai GLM, Anthropic Claude |
| **Per-request override** | Choose LLM provider per call without changing config |
| **Protocols** | MCP stdio (Claude) + HTTP REST (curl/web) |
| **Ambiguity handling** | Auto-detects unclear queries and asks for clarification |
| **Multilingual** | Specify response language per request |
| **Security** | Parameterized queries, schema validation before dynamic SQL |
| **Audit trail** | Full query history with timing, provider, row count |
| **Schema introspection** | List tables, columns, stats, paginated data |
| **Migrations** | Alembic-managed schema versioning |

---

## Setup

**Requirements:** Python 3.8+, PostgreSQL

```bash
# Clone and install
cd /home/htnguyen/Space/query-mcp
python3 -m venv venv
source venv/bin/activate
pip install -r requirements.txt

# Set your LLM API key (Gemini is free-tier available)
export QUERY_MCP_API_KEY="your-gemini-api-key"

# Run migrations
alembic upgrade head

# Start the MCP server (stdio mode for Claude)
python src/server.py

# Or start in HTTP mode
python src/server.py http 8001
```

### Claude Code Integration

1. Open Claude Code settings → MCP Servers → Add new server
2. Set:
   - **Command**: `python`
   - **Args**: `/home/htnguyen/Space/query-mcp/src/server.py`
   - **Env**: `QUERY_MCP_API_KEY=your-api-key`
3. Click Connect

Once registered, ask Claude naturally: *"Show me the top 10 most expensive drugs"* and it will generate SQL, execute it, and return a readable answer.

---

## Configuration

### Priority Order

1. `QUERY_MCP_API_KEY` environment variable *(recommended)*
2. `~/.query-mcp/config.json` *(auto-created on first run)*

### Config File Structure

```json
{
  "database": {
    "host": "localhost",
    "port": 5432,
    "name": "postgres",
    "user": "postgres",
    "password": "postgres"
  },
  "text_to_sql": {
    "llm_api_key": "",
    "llm_provider": "gemini",
    "llm_model": "gemini-2.5-flash"
  }
}
```

### LLM Providers

| Provider | Key | Models | Notes |
|---|---|---|---|
| `gemini` | `QUERY_MCP_API_KEY` | `gemini-2.5-flash`, `gemini-2.0-flash` | Default; free tier via AI Studio |
| `zai` | `QUERY_MCP_API_KEY` | `glm-5.1` | Z.ai GLM |
| `anthropic` | `QUERY_MCP_API_KEY` | `claude-3-5-sonnet-20241022` | Anthropic Claude |

---

## MCP Tools

All tools accept an optional `llm_provider` parameter to override the configured default per-call.

### `ask` — Full Pipeline

Converts a natural language question into SQL, executes it, and returns a human-readable answer.

**Parameters:**

| Name | Type | Required | Default | Description |
|---|---|---|---|---|
| `user_message` | string | Yes | — | Natural language question |
| `table_name` | string | Yes | — | Target PostgreSQL table |
| `limit` | integer | No | 100 | Max rows |
| `llm_provider` | string | No | config | `"gemini"`, `"zai"`, or `"anthropic"` |
| `lang` | string | No | auto | Response language |

**Response:**
```json
{
  "success": true,
  "sql": "SELECT name, price FROM drugs ORDER BY price DESC LIMIT 5",
  "results": [{"name": "Clopidogrel", "price": 45.99}],
  "row_count": 5,
  "answer": "The most expensive drug is Clopidogrel at $45.99.",
  "error": null
}
```

---

### `generate_sql` — SQL Generation Only

Generates SQL from natural language without executing it.

**Parameters:** `user_message`, `table_name`, `llm_provider`, `lang`

**Response:**
```json
{
  "success": true,
  "sql": "SELECT * FROM drugs WHERE price > 100 LIMIT 100;",
  "error": null
}
```

**Clarification response** (when query is ambiguous):
```json
{
  "success": false,
  "sql": null,
  "error": "CLARIFY: Which time period do you want to filter by?"
}
```

---

### `text_to_sql_execute` — Generate and Execute

Generates SQL and runs it in one call. Returns raw results without natural language summarization.

**Parameters:** `user_message`, `table_name`, `limit`, `llm_provider`, `lang`

**Response:**
```json
{
  "success": true,
  "sql": "SELECT category, COUNT(*) as count FROM items GROUP BY category LIMIT 50;",
  "results": [{"category": "Electronics", "count": 25}],
  "row_count": 1,
  "error": null
}
```

---

### `execute_sql` — Execute Raw SQL

Runs an arbitrary SQL query directly.

**Parameters:**

| Name | Type | Required | Default |
|---|---|---|---|
| `sql_query` | string | Yes | — |
| `limit` | integer | No | 100 |

**Response:**
```json
{
  "success": true,
  "results": [{"id": 1, "name": "Drug A", "price": 150}],
  "row_count": 1,
  "error": null
}
```

---

### MCP Resources

| Resource | Description |
|---|---|
| `config://database` | Current DB config (password hidden) |
| `config://text-to-sql` | LLM config (API key hidden) |

### MCP Prompts

`sql_query_help(query_type)` — Returns SQL help for `"select"`, `"filter"`, or `"aggregate"`.

---

## REST API

Start the HTTP server:

```bash
python src/server.py http         # port 8001 (default)
python src/server.py http 9000    # custom port
```

### Endpoints

| Method | Path | Description |
|---|---|---|
| `POST` | `/api/ask` | Natural language → SQL → execute → text answer |
| `POST` | `/api/query` | Natural language → SQL → execute → raw results |
| `POST` | `/api/sql` | Natural language → SQL only |
| `POST` | `/api/execute` | Execute raw SQL |
| `GET` | `/api/health` | Health check |
| `GET` | `/api/tables` | List all tables with metadata |
| `GET` | `/api/tables/{table_id}` | Table details |
| `GET` | `/api/tables/{table_id}/schema` | Column definitions |
| `GET` | `/api/tables/{table_id}/data` | Paginated data with sorting |
| `GET` | `/api/tables/{table_id}/stats` | Row count, aggregates, distributions |
| `GET` | `/api/columns/{table_ref}` | Column names (for autocomplete) |
| `GET` | `/api/query/history` | Query execution history |

### curl Examples

```bash
# Get a natural language answer
curl -s -X POST http://localhost:8001/api/ask \
  -H "Content-Type: application/json" \
  -d '{"user_message": "What are the top 3 most expensive drugs?", "table_name": "drugs"}'

# Raw query results
curl -s -X POST http://localhost:8001/api/query \
  -H "Content-Type: application/json" \
  -d '{"user_message": "Count drugs by category", "table_name": "drugs"}'

# SQL only — no execution
curl -s -X POST http://localhost:8001/api/sql \
  -H "Content-Type: application/json" \
  -d '{"user_message": "Find inactive drugs", "table_name": "drugs"}'

# Execute raw SQL
curl -s -X POST http://localhost:8001/api/execute \
  -H "Content-Type: application/json" \
  -d '{"sql_query": "SELECT name, price FROM drugs WHERE price > 30", "limit": 5}'

# Paginated table data sorted by price descending
curl -s "http://localhost:8001/api/tables/src_abc12345/data?limit=10&offset=0&sort=price&order=desc"

# Table statistics
curl -s http://localhost:8001/api/tables/src_abc12345/stats

# Query history
curl -s "http://localhost:8001/api/query/history?limit=50"
```

---

## Database Service

`db_service.py` is the central data access layer used by both the MCP server and the text-to-SQL engine. All queries are parameterized to prevent SQL injection.

```python
from db_service import DatabaseService

db = DatabaseService.from_config()

# Schema inspection
db.list_tables()                                       # → ['drugs', 'items', ...]
db.get_table_schema('drugs')                           # → formatted column info string
db.get_table_columns('drugs')                          # → [{'name': ..., 'type': ...}, ...]

# Reads
db.execute_query("SELECT * FROM drugs WHERE price > 50")  # → {success, results, row_count, error}
db.fetch_all('drugs', where="price > %s", params=(50,))
db.fetch_one('users', where="id = %s", params=(1,))
db.count('drugs')                                      # → 42

# Paginated data with sorting
db.get_table_data('drugs', limit=20, offset=0, sort='price', order='desc')

# Table statistics (row count, numeric summaries, value distributions)
db.get_table_stats('drugs')

# Writes
db.execute_write("UPDATE drugs SET stock = %s WHERE id = %s", (0, 1))

# Query audit
db.log_query(user_message="...", table_name="drugs", generated_sql="...", success=True)
db.get_query_history(limit=50, success_only=True)
```

All database connections use context managers — connections are always closed even on error.

---

## Query History

Every `generate_and_execute()` call is automatically logged to the `query_history` table.

**Tracked fields:**

| Field | Description |
|---|---|
| `session_id` | Session identifier |
| `user_message` | Original natural language question |
| `table_name` | Target table |
| `generated_sql` | The SQL that was generated |
| `success` | Whether the query succeeded |
| `row_count` | Number of rows returned |
| `error` | Error message if failed |
| `llm_provider` | Which LLM generated the SQL |
| `llm_model` | Specific model used |
| `execution_time_ms` | End-to-end time in milliseconds |
| `created_at` | Timestamp |

**Example queries:**

```sql
-- Recent failures
SELECT user_message, error, created_at
FROM query_history
WHERE success = FALSE
ORDER BY created_at DESC LIMIT 10;

-- Average execution time per provider
SELECT llm_provider, AVG(execution_time_ms) AS avg_ms
FROM query_history
GROUP BY llm_provider;
```

---

## Migrations

Schema is managed by **Alembic**. The initial migration (`8f9881ec5d77_initial_schema.py`) creates the `query_history` table.

```bash
# Apply all pending migrations
alembic upgrade head

# Check current revision
alembic current

# Roll back one step
alembic downgrade -1

# Create a new migration
alembic revision -m "add_new_column"
# Edit the generated file in alembic/versions/, then:
alembic upgrade head
```

---

## Deployment

### Local Development

```bash
python src/server.py           # MCP stdio mode
python src/server.py http      # HTTP mode on port 8001
```

### Docker

```bash
docker-compose up -d           # Starts Query MCP + PostgreSQL
```

See [docs/DOCKER_SETUP.md](docs/DOCKER_SETUP.md) for configuration details.

### Production (Cloud Run)

Query MCP is deployed as part of the `med-tech-workload` stack. Migrations run automatically on every deployment.

See [docs/DEPLOYMENT.md](docs/DEPLOYMENT.md) for full production deployment instructions.

---

## Error Handling

All tools and endpoints return a consistent JSON structure:

```json
{
  "success": false,
  "error": "Human-readable error message",
  "sql": null,
  "results": null,
  "row_count": 0
}
```

### Common Errors

| Error | Cause | Fix |
|---|---|---|
| `LLM API key not configured` | Missing API key | Set `QUERY_MCP_API_KEY` |
| `Database connection failed` | Bad host/port/credentials | Check `~/.query-mcp/config.json`, verify PostgreSQL is running |
| `Table 'xyz' not found or has no columns` | Table does not exist | Use the correct table name (case-sensitive) |
| `Query execution failed: syntax error` | Bad SQL | Review generated SQL or provide valid SQL directly |
| `Unsupported LLM provider: xyz` | Unknown provider name | Use `"gemini"`, `"zai"`, or `"anthropic"` |

---

## Troubleshooting

**Server won't start:**
```bash
python --version                          # Need 3.8+
pip list | grep -E "fastmcp|psycopg2"    # Check deps
python -u src/server.py                   # Verbose output
```

**API key errors:**
```bash
echo $QUERY_MCP_API_KEY
cat ~/.query-mcp/config.json
```

**Database connection errors:**
```bash
psql -h localhost -U postgres -d postgres -c "SELECT 1;"
cat ~/.query-mcp/config.json | grep -A 5 database
```

---

## Project Structure

```
query-mcp/
├── src/
│   ├── server.py          # MCP server + HTTP REST entry point
│   ├── text_to_sql.py     # Core TextToSQL engine
│   ├── db_service.py      # Database service layer
│   ├── workflow.py        # Download & load workflow
│   └── cli_workflow.py    # CLI for workflow
├── alembic/
│   ├── env.py             # Alembic environment config
│   └── versions/
│       └── 8f9881ec5d77_initial_schema.py
├── alembic.ini
├── docker/
├── docs/
│   ├── API_ENDPOINTS.md   # Complete REST API reference
│   ├── ARCHITECTURE.md    # System design
│   ├── DEPLOYMENT.md      # Production deployment
│   └── DOCKER_SETUP.md    # Docker configuration
├── requirements.txt
└── README.md
```
