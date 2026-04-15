# Query MCP - Text-to-SQL Server

MCP (Model Context Protocol) server that converts natural language queries to PostgreSQL SQL using multiple LLM providers (Z.ai, Anthropic Claude).

**Features:**
- ✨ Natural language → SQL query conversion
- 🔄 SQL generation & execution in one call
- 🔌 MCP-compatible for Claude integration
- 🎯 Per-request LLM provider selection
- 🐘 PostgreSQL database support
- ⚙️ Flexible configuration (env vars or JSON)
- 📦 Versioned SQL migrations
- 🗄️ Database service layer with connection management
- 📊 Query history tracking & audit log

## Quick Start

```bash
# 1. Install
cd /home/htnguyen/Space/query-mcp
python3 -m venv venv
source venv/bin/activate
pip install -r requirements.txt

# 2. Configure API key (Gemini default)
export QUERY_MCP_API_KEY="your-gemini-api-key"

# 3. Configure database (optional, defaults to localhost:5432)
# Edit ~/.query-mcp/config.json

# 4. Run
python server.py
```

## Configuration

### Priority Order (highest to lowest)
1. **Environment Variable** `QUERY_MCP_API_KEY` (recommended)
2. **Config File** `~/.query-mcp/config.json`

### Environment Variables
```bash
export QUERY_MCP_API_KEY="your-api-key"      # Gemini, Z.ai, or Anthropic key
```

### Config File: `~/.query-mcp/config.json`

Auto-created on first run with defaults:
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

**Database fields:**
- `host` - PostgreSQL server hostname
- `port` - PostgreSQL port (default 5432)
- `name` - Database name
- `user` - Database user
- `password` - Database password

**LLM Providers:**
- `gemini` (default) - Google Gemini models
  - Models: `gemini-2.5-flash`, `gemini-2.0-flash`
  - API key: https://aistudio.google.com/apikey (free tier available)
  - API docs: https://docs.cloud.google.com/vertex-ai/generative-ai/docs/sdks/overview
- `zai` - Z.ai GLM models
  - Models: `glm-5.1`
  - API docs: https://docs.z.ai/guides/develop/python/introduction
- `anthropic` - Anthropic Claude models
  - Models: `claude-3-5-sonnet-20241022`
  - API docs: https://docs.anthropic.com

## Tools

All tools support the `llm_provider` parameter to override the config default on a per-call basis.

### `ask` — Question to natural language answer (full pipeline)

Ask a question in natural language and get a human-readable answer. Generates SQL, executes it, then summarizes results with the LLM.

**Parameters:**
| Name | Type | Required | Default | Description |
|------|------|----------|---------|-------------|
| `user_message` | string | Yes | - | Natural language question |
| `table_name` | string | Yes | - | PostgreSQL table to query from |
| `limit` | integer | No | 100 | Max rows to return |
| `llm_provider` | string | No | config | LLM provider: "gemini", "zai", or "anthropic" |

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

### `generate_sql` — Generate SQL without executing

Generate a SQL query from natural language without executing it.

**Parameters:**
| Name | Type | Required | Default | Description |
|------|------|----------|---------|-------------|
| `user_message` | string | Yes | - | Natural language query (e.g., "Show me all drugs with price > 100") |
| `table_name` | string | Yes | - | PostgreSQL table to query from |
| `llm_provider` | string | No | config | LLM provider: "gemini", "zai", or "anthropic" |

**Response:**
```json
{
  "success": true,
  "sql": "SELECT * FROM drugs WHERE price > 100 LIMIT 100;",
  "error": null
}
```

**Error response:**
```json
{
  "success": false,
  "sql": null,
  "error": "Table 'drugs' not found or has no columns"
}
```

---

### `execute_sql` — Execute SQL and return results

Execute a raw SQL query and fetch results.

**Parameters:**
| Name | Type | Required | Default | Description |
|------|------|----------|---------|-------------|
| `sql_query` | string | Yes | - | SQL query to execute |
| `limit` | integer | No | 100 | Max rows to return |
| `llm_provider` | string | No | config | LLM provider (unused for execute, kept for consistency) |

**Response:**
```json
{
  "success": true,
  "results": [
    {"id": 1, "name": "Drug A", "price": 150},
    {"id": 2, "name": "Drug B", "price": 200}
  ],
  "row_count": 2,
  "error": null
}
```

**Error response:**
```json
{
  "success": false,
  "results": null,
  "row_count": 0,
  "error": "Query execution failed: syntax error"
}
```

---

### `text_to_sql_execute` — Generate SQL and execute (combined)

Convert natural language to SQL AND execute in one call.

**Parameters:**
| Name | Type | Required | Default | Description |
|------|------|----------|---------|-------------|
| `user_message` | string | Yes | - | Natural language query |
| `table_name` | string | Yes | - | PostgreSQL table to query |
| `limit` | integer | No | 100 | Max rows to return |
| `llm_provider` | string | No | config | LLM provider: "gemini", "zai", or "anthropic" |

**Response:**
```json
{
  "success": true,
  "sql": "SELECT * FROM drugs WHERE price > 100 LIMIT 100;",
  "results": [
    {"id": 1, "name": "Drug A", "price": 150}
  ],
  "row_count": 1,
  "error": null
}
```

**Example with explicit provider:**
```json
{
  "user_message": "Show me top 5 expensive drugs",
  "table_name": "drugs",
  "limit": 5,
  "llm_provider": "anthropic"
}
```

## Migrations

Versioned SQL migrations in `migrations/`. Tracked via `schema_migrations` table.

```bash
# Apply pending migrations
python src/migrate.py

# Check migration status
python src/migrate.py status
```

### Migration Files

| File | Description |
|------|-------------|
| `001_initial_schema.sql` | Base tables: `drugs`, `items`, `users`, `orders` + indexes |
| `002_seed_data.sql` | Sample data (15 drugs, 10 items, 10 users, 10 orders) |
| `003_create_views.sql` | Views: `active_drugs`, `drugs_by_category`, `expensive_items` |
| `004_query_history.sql` | Query tracking: `query_sessions`, `query_history` |

### Adding a New Migration

Create `migrations/NNN_description.sql`. Run `python src/migrate.py`.

## Database Service (`db_service.py`)

Central database layer used by `text_to_sql.py`. Replaces raw `psycopg2` calls with context-managed connections.

```python
from db_service import DatabaseService

db = DatabaseService.from_config()

# Schema introspection
db.list_tables()                          # → ['drugs', 'items', ...]
db.get_table_schema('drugs')              # → formatted column info

# Query execution
db.execute_query("SELECT * FROM drugs")   # → {success, results, row_count, error}
db.fetch_all('drugs', where="price > %s", params=(100,))
db.fetch_one('users', where="id = %s", params=(1,))
db.count('drugs')                         # → 15

# Write operations
db.execute_write("UPDATE drugs SET stock = %s WHERE id = %s", (0, 1))

# Query history
db.log_query(user_message="...", table_name="drugs", generated_sql="...", success=True)
db.get_query_history(limit=50, success_only=True)
```

## Query History

Every `generate_and_execute()` call is automatically logged to the `query_history` table.

**Tracked fields:** `user_message`, `table_name`, `generated_sql`, `success`, `row_count`, `error`, `llm_provider`, `llm_model`, `execution_time_ms`, `session_id`

```sql
-- Recent failed queries
SELECT user_message, error, created_at
FROM query_history WHERE success = FALSE
ORDER BY created_at DESC LIMIT 10;

-- Average execution time by provider
SELECT llm_provider, AVG(execution_time_ms) as avg_ms
FROM query_history GROUP BY llm_provider;
```

## Resources

### `config://database`
Get current database connection config (password hidden).

### `config://text-to-sql`
Get text-to-sql configuration (API key hidden).

## Prompts

### `sql_query_help`
Get help for different SQL query types:
- `select` - Basic SELECT queries
- `filter` - WHERE conditions
- `aggregate` - GROUP BY and aggregations

## Examples

### Example 1: Generate SQL (Gemini)
```json
{
  "user_message": "Find all items with status = 'active'",
  "table_name": "items",
  "llm_provider": "gemini"
}
```

Response:
```json
{
  "success": true,
  "sql": "SELECT * FROM items WHERE status = 'active' LIMIT 100;",
  "error": null
}
```

### Example 2: Generate + Execute (Anthropic Claude)
```json
{
  "user_message": "Count items by category",
  "table_name": "items",
  "limit": 50,
  "llm_provider": "anthropic"
}
```

Response:
```json
{
  "success": true,
  "sql": "SELECT category, COUNT(*) as count FROM items GROUP BY category LIMIT 50;",
  "results": [
    {"category": "Electronics", "count": 25},
    {"category": "Books", "count": 18}
  ],
  "row_count": 2,
  "error": null
}
```

### Example 3: Execute Raw SQL
```json
{
  "sql_query": "SELECT name, price FROM drugs WHERE price > 100 ORDER BY price DESC;",
  "limit": 10
}
```

## REST API (HTTP Mode)

Start the server in HTTP mode for curl/REST access:

```bash
# Start HTTP server (default port 8001)
python src/server.py http

# Custom port
python src/server.py http 9000
```

### Endpoints

See [API_ENDPOINTS.md](docs/API_ENDPOINTS.md) for complete endpoint documentation.

Quick reference:

| Method | Endpoint | Description |
|--------|----------|-------------|
| `POST` | `/api/ask` | Full pipeline: question → SQL → execute → natural language answer |
| `POST` | `/api/query` | Question → SQL → execute → raw results |
| `POST` | `/api/sql` | Question → SQL only (no execution) |
| `POST` | `/api/execute` | Run raw SQL query |
| `GET` | `/api/health` | Health check |
| `GET` | `/api/tables` | List all tables with metadata (schema inspection) |
| `GET` | `/api/tables/{table_id}` | Get table details |
| `GET` | `/api/tables/{table_id}/schema` | Get table column definitions |
| `GET` | `/api/tables/{table_id}/data` | Get paginated table data with sorting |
| `GET` | `/api/tables/{table_id}/stats` | Get table statistics (row count, aggregates, distributions) |
| `GET` | `/api/columns/{table_ref}` | Get column names for autocomplete |
| `GET` | `/api/query/history` | Get query execution history |

### curl Examples

Quick examples (see [API_ENDPOINTS.md](docs/API_ENDPOINTS.md) for complete reference):

```bash
# Ask — get a text answer
curl -s -X POST http://localhost:8001/api/ask \
  -H "Content-Type: application/json" \
  -d '{"user_message": "What are the top 3 most expensive drugs?", "table_name": "drugs"}'

# Query — raw data
curl -s -X POST http://localhost:8001/api/query \
  -H "Content-Type: application/json" \
  -d '{"user_message": "Count drugs by category", "table_name": "drugs"}'

# Generate SQL only (no execution)
curl -s -X POST http://localhost:8001/api/sql \
  -H "Content-Type: application/json" \
  -d '{"user_message": "Find inactive drugs", "table_name": "drugs"}'

# Execute raw SQL
curl -s -X POST http://localhost:8001/api/execute \
  -H "Content-Type: application/json" \
  -d '{"sql_query": "SELECT name, price FROM drugs WHERE price > 30", "limit": 5}'

# List tables (schema inspection)
curl -s http://localhost:8001/api/tables

# Get table data with pagination and sorting
curl -s "http://localhost:8001/api/tables/src_abc12345/data?limit=10&offset=0&sort=price&order=desc"

# Get table statistics (row count, numeric summaries, distributions)
curl -s http://localhost:8001/api/tables/src_abc12345/stats

# Get column names for autocomplete
curl -s http://localhost:8001/api/columns/drugs

# View query execution history
curl -s http://localhost:8001/api/query/history?limit=50
```

## Error Handling

All tools return consistent error format with `success: false`.

### Common Errors & Fixes

| Error | Cause | Fix |
|-------|-------|-----|
| `LLM API key not configured` | Missing API key | Set `QUERY_MCP_API_KEY` env var or config.json |
| `Database connection failed` | Invalid host/port/credentials | Check config, verify PostgreSQL is running |
| `Table 'xyz' not found or has no columns` | Table doesn't exist | Use correct table name (case-sensitive in PostgreSQL) |
| `Query execution failed: syntax error` | Invalid SQL | Check generated SQL or provide valid SQL |
| `Unsupported LLM provider: xyz` | Unknown LLM provider | Use "gemini", "zai", or "anthropic" |

### Error Response Format
```json
{
  "success": false,
  "error": "Human-readable error message",
  "sql": null,
  "results": null,
  "row_count": 0
}
```

## Integration with Claude

### Register with Claude Code
1. Open Claude Code settings
2. Go to "MCP Servers"
3. Add new server:
   - **Name**: Query MCP
   - **Command**: `python`
   - **Args**: `/home/htnguyen/Space/query-mcp/server.py`
   - **Env**: `QUERY_MCP_API_KEY=your-api-key`
4. Click "Connect"

### Usage in Claude
Once registered, you can ask Claude:
- "Query the drugs table and show me the top 10 most expensive items"
- "Count how many items are in each category"
- "Find all drugs with a price between $50-$100"
- "Show me recent orders with total > $1000"

Claude will:
1. Use the appropriate LLM provider
2. Generate SQL from your natural language request
3. Execute the query
4. Present results in a readable format

## Resources

### MCP Resources
- `config://database` - Get current database config (password hidden)
- `config://text-to-sql` - Get LLM config (API key hidden)

### MCP Prompts
- `sql_query_help(query_type)` - Get SQL query help
  - Types: "select", "filter", "aggregate"

## Architecture

```
User Request (Natural Language or HTTP)
    ↓
MCP Server (server.py)
    ├─ MCP Stdio Protocol (for Claude integration)
    └─ HTTP REST API (for direct HTTP access)
         ├─ Text-to-SQL endpoints (/api/ask, /api/query, /api/sql)
         └─ Schema inspection endpoints (/api/tables, /api/columns, etc)
    ↓
TextToSQL Engine (text_to_sql.py)
    ├─ LLM Provider (Gemini, Z.ai, or Anthropic)
    └─ DatabaseService (db_service.py)
        ├─ Schema Discovery
        ├─ Query Execution
        └─ Query History Logging
    ↓
PostgreSQL Database (local, external, or med-tech-workload deployment)
    ↓
Response (JSON)
```

## Deployment

- **Local Development**: Run `python src/server.py` with local postgres
- **Docker (Dev)**: See [DOCKER_SETUP.md](docs/DOCKER_SETUP.md) - docker-compose for Query MCP only (postgres managed separately)
- **Production**: Query MCP deployed as part of med-tech-workload stack with shared postgres instance

**File Structure:**
```
query-mcp/
├── src/
│   ├── server.py          # MCP server entry point
│   ├── text_to_sql.py     # Core TextToSQL engine
│   ├── db_service.py      # Database service layer
│   └── migrate.py         # Migration runner
├── migrations/
│   ├── 001_initial_schema.sql
│   ├── 002_seed_data.sql
│   ├── 003_create_views.sql
│   └── 004_query_history.sql
├── docker/                # Docker configuration
├── docs/                  # Documentation
├── requirements.txt
└── README.md
```

## Troubleshooting

### Server won't start
```bash
# Check Python version (need 3.8+)
python --version

# Check dependencies installed
pip list | grep -E "zai|anthropic|psycopg2|fastmcp"

# Run with verbose output
python -u server.py
```

### API key errors
```bash
# Verify env var is set
echo $QUERY_MCP_API_KEY

# Check config file
cat ~/.query-mcp/config.json

# Test API key with a simple request
python -c "from zai import ZaiClient; ZaiClient(api_key='your-key')"
```

### Database connection errors
```bash
# Test PostgreSQL connection
psql -h localhost -U postgres -d postgres -c "SELECT 1;"

# Check config
cat ~/.query-mcp/config.json | grep -A 5 database
```
