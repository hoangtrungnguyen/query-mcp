# Query MCP - API Reference

Quick reference for all MCP tools, REST API, resources, and prompts.

## Tools

### ask

Full pipeline: generate SQL from natural language, execute it, then summarize results with LLM.

```
Tool: ask
```

**Parameters:**

| Parameter | Type | Required | Default | Description |
|-----------|------|----------|---------|-------------|
| `user_message` | string | Yes | - | Natural language question |
| `table_name` | string | Yes | - | PostgreSQL table name |
| `limit` | integer | No | 100 | Max rows to return |
| `llm_provider` | string | No | config | "gemini", "zai", or "anthropic" |

**Request:**
```json
{
  "user_message": "What are the top 3 most expensive drugs?",
  "table_name": "drugs",
  "limit": 5
}
```

**Success Response:**
```json
{
  "success": true,
  "sql": "SELECT name, price FROM drugs ORDER BY price DESC LIMIT 3",
  "results": [
    {"name": "Clopidogrel", "price": 45.99},
    {"name": "Ciprofloxacin", "price": 35.99},
    {"name": "Warfarin", "price": 28.99}
  ],
  "row_count": 3,
  "answer": "The top 3 most expensive drugs are: 1. Clopidogrel ($45.99), 2. Ciprofloxacin ($35.99), 3. Warfarin ($28.99).",
  "error": null
}
```

**Error Response:**
```json
{
  "success": false,
  "sql": null,
  "results": null,
  "row_count": 0,
  "answer": null,
  "error": "Table 'xyz' not found or has no columns"
}
```

---

### generate_sql

Generate a SQL query from natural language without executing it.

```
Tool: generate_sql
```

**Parameters:**

| Parameter | Type | Required | Default | Description |
|-----------|------|----------|---------|-------------|
| `user_message` | string | ✓ | - | Natural language query |
| `table_name` | string | ✓ | - | PostgreSQL table name |
| `llm_provider` | string | - | config | "gemini", "zai", or "anthropic" |

**Request:**
```json
{
  "user_message": "Show me all drugs with price > 100",
  "table_name": "drugs",
  "llm_provider": "gemini"
}
```

**Success Response:**
```json
{
  "success": true,
  "sql": "SELECT * FROM drugs WHERE price > 100 LIMIT 100;",
  "error": null
}
```

**Error Response:**
```json
{
  "success": false,
  "sql": null,
  "error": "Table 'drugs' not found or has no columns"
}
```

---

### execute_sql

Execute a SQL query and return results.

```
Tool: execute_sql
```

**Parameters:**

| Parameter | Type | Required | Default | Description |
|-----------|------|----------|---------|-------------|
| `sql_query` | string | ✓ | - | SQL query to execute |
| `limit` | integer | - | 100 | Max rows to return |
| `llm_provider` | string | - | config | Unused (for consistency) |

**Request:**
```json
{
  "sql_query": "SELECT * FROM drugs WHERE price > 100",
  "limit": 50,
  "llm_provider": "gemini"
}
```

**Success Response:**
```json
{
  "success": true,
  "results": [
    {"id": 1, "name": "Drug A", "price": 150.00},
    {"id": 2, "name": "Drug B", "price": 200.00}
  ],
  "row_count": 2,
  "error": null
}
```

**Error Response:**
```json
{
  "success": false,
  "results": null,
  "row_count": 0,
  "error": "Query execution failed: syntax error at or near \"WHERE\""
}
```

---

### text_to_sql_execute

Generate SQL from natural language AND execute in one call.

```
Tool: text_to_sql_execute
```

**Parameters:**

| Parameter | Type | Required | Default | Description |
|-----------|------|----------|---------|-------------|
| `user_message` | string | ✓ | - | Natural language query |
| `table_name` | string | ✓ | - | PostgreSQL table name |
| `limit` | integer | - | 100 | Max rows to return |
| `llm_provider` | string | - | config | "gemini", "zai", or "anthropic" |

**Request:**
```json
{
  "user_message": "Count drugs by price range",
  "table_name": "drugs",
  "limit": 50,
  "llm_provider": "anthropic"
}
```

**Success Response:**
```json
{
  "success": true,
  "sql": "SELECT CASE WHEN price < 50 THEN 'Low' WHEN price < 100 THEN 'Medium' ELSE 'High' END as price_range, COUNT(*) as count FROM drugs GROUP BY price_range LIMIT 50;",
  "results": [
    {"price_range": "Low", "count": 25},
    {"price_range": "Medium", "count": 30},
    {"price_range": "High", "count": 15}
  ],
  "row_count": 3,
  "error": null
}
```

**Error Response:**
```json
{
  "success": false,
  "sql": null,
  "results": null,
  "row_count": 0,
  "error": "LLM API key not configured"
}
```

---

## Resources

### config://database

Read-only resource exposing database configuration (password hidden).

```
Resource: config://database
```

**Response:**
```json
{
  "host": "localhost",
  "port": 5432,
  "name": "postgres",
  "user": "postgres"
}
```

**Note:** Password is intentionally omitted from response.

---

### config://text-to-sql

Read-only resource exposing LLM configuration (API key hidden).

```
Resource: config://text-to-sql
```

**Response:**
```json
{
  "llm_provider": "gemini",
  "llm_api_key_configured": true
}
```

**Note:** Actual API key is intentionally hidden. Only shows whether it's configured.

---

## REST API (HTTP Mode)

When running in HTTP mode (`python src/server.py http [port]`), these REST endpoints are available alongside the MCP protocol.

### `POST /api/ask`
Full pipeline: question → SQL → execute → LLM summary. Same as the `ask` MCP tool.

**Body:** `{"user_message": "...", "table_name": "...", "limit": 100, "llm_provider": "gemini"}`

### `POST /api/query`
Generate SQL and execute. Returns raw results (no LLM summary). Same as `text_to_sql_execute` MCP tool.

**Body:** `{"user_message": "...", "table_name": "...", "limit": 100}`

### `POST /api/sql`
Generate SQL only (no execution). Same as `generate_sql` MCP tool.

**Body:** `{"user_message": "...", "table_name": "..."}`

### `POST /api/execute`
Execute raw SQL. Same as `execute_sql` MCP tool.

**Body:** `{"sql_query": "SELECT ...", "limit": 100}`

### `GET /health`
Health check. Returns `{"status": "ok"}`.

### Error Handling
All endpoints validate request body and return structured errors:
```json
// 400 Bad Request — missing required fields
{"success": false, "error": "Required: user_message, table_name"}

// 500 Internal Error — execution failure
{"success": false, "error": "Database connection failed: ..."}
```

### Data Types
`Decimal` and `datetime` values from PostgreSQL are auto-serialized to `float` and ISO 8601 strings.

---

## Prompts

### sql_query_help

Get help for different SQL query types.

```
Prompt: sql_query_help
```

**Parameters:**

| Parameter | Type | Required | Default | Description |
|-----------|------|----------|---------|-------------|
| `query_type` | string | - | "select" | "select", "filter", "aggregate" |

**Example Requests:**

```
sql_query_help()
→ Help for all query types

sql_query_help("filter")
→ Help for WHERE conditions

sql_query_help("aggregate")
→ Help for GROUP BY and aggregations
```

---

## Error Codes & Messages

### Configuration Errors

```
"LLM API key not configured"
→ Set QUERY_MCP_API_KEY env var or config.json llm_api_key

"Database config incomplete"
→ Missing required fields in database config (host, port, name, user, password)

"unsupported provider: xyz"
→ Use "zai" or "anthropic"
```

### Database Errors

```
"Database connection failed: [details]"
→ PostgreSQL connection error (check host, port, credentials)

"Table 'xyz' not found or has no columns"
→ Table doesn't exist or is empty (check table name - case sensitive)

"Query execution failed: [details]"
→ SQL syntax error or query execution error
```

### LLM Errors

```
"SQL generation failed: [details]"
→ Error calling LLM API (check API key, network, rate limits)
```

---

## Request/Response Format

All requests and responses use JSON format.

### Success Response Format

```json
{
  "success": true,
  "sql": "...",           // For generate_sql, text_to_sql_execute
  "results": [...],       // For execute_sql, text_to_sql_execute
  "row_count": 0,         // For execute_sql, text_to_sql_execute
  "error": null
}
```

### Error Response Format

```json
{
  "success": false,
  "sql": null,            // If applicable
  "results": null,        // If applicable
  "row_count": 0,         // If applicable
  "error": "Error message"
}
```

---

## Common Query Examples

### Example 1: Simple SELECT

**Request:**
```json
{
  "user_message": "Show me the first 10 drugs ordered by price",
  "table_name": "drugs"
}
```

**Generated SQL:**
```sql
SELECT * FROM drugs ORDER BY price ASC LIMIT 10;
```

---

### Example 2: Filtering with Conditions

**Request:**
```json
{
  "user_message": "Find all active drugs with price between $50 and $100",
  "table_name": "drugs"
}
```

**Generated SQL:**
```sql
SELECT * FROM drugs WHERE status = 'active' AND price >= 50 AND price <= 100 LIMIT 100;
```

---

### Example 3: Aggregation

**Request:**
```json
{
  "user_message": "Count how many drugs we have in each category",
  "table_name": "drugs"
}
```

**Generated SQL:**
```sql
SELECT category, COUNT(*) as drug_count FROM drugs GROUP BY category LIMIT 100;
```

---

### Example 4: Sorting

**Request:**
```json
{
  "user_message": "Show me the top 5 most expensive drugs",
  "table_name": "drugs"
}
```

**Generated SQL:**
```sql
SELECT * FROM drugs ORDER BY price DESC LIMIT 5;
```

---

### Example 5: Using Specific Provider

**Request:**
```json
{
  "user_message": "Find all expired drugs",
  "table_name": "drugs",
  "llm_provider": "anthropic"
}
```

**Uses:** Claude instead of Gemini (overrides config default)

---

## Provider Differences

### Google Gemini (Default)

- **Pros:** Free tier, fast, good SQL generation
- **Model:** `gemini-2.5-flash`
- **Best for:** General use, free tier
- **Free:** 500 req/day (2.5-flash), 1500 req/day (2.0-flash)
- **API key:** https://aistudio.google.com/apikey
- **Docs:** https://docs.cloud.google.com/vertex-ai/generative-ai/docs/sdks/overview

### Z.ai

- **Pros:** Fast inference, good SQL generation
- **Model:** `glm-5.1`
- **Best for:** Simple queries, real-time use
- **Docs:** https://docs.z.ai

### Anthropic Claude

- **Pros:** Better reasoning, complex queries, higher accuracy
- **Model:** `claude-3-5-sonnet-20241022`
- **Best for:** Complex queries, analysis
- **Docs:** https://docs.anthropic.com

---

## Rate Limiting

Currently no rate limiting. For production:

```python
from functools import wraps
from time import time

def rate_limit(max_calls=100, time_window=60):
    def decorator(func):
        calls = []
        
        @wraps(func)
        def wrapper(*args, **kwargs):
            now = time()
            calls[:] = [c for c in calls if c > now - time_window]
            if len(calls) >= max_calls:
                raise Exception(f"Rate limit exceeded: {max_calls} calls per {time_window}s")
            calls.append(now)
            return func(*args, **kwargs)
        return wrapper
    return decorator

@mcp.tool
@rate_limit(max_calls=100, time_window=60)
def generate_sql(...):
    ...
```

---

## Testing

### Test with Python

```python
from server import generate_sql, execute_sql, text_to_sql_execute

# Test generate_sql
result = generate_sql("Show me all drugs", "drugs")
print(result)

# Test execute_sql
result = execute_sql("SELECT * FROM drugs LIMIT 5")
print(result)

# Test combined
result = text_to_sql_execute("Show me top 5 expensive drugs", "drugs", 5)
print(result)
```

### Test with curl (if running HTTP server)

```bash
curl -X POST http://localhost:8000/tools/generate_sql \
  -H "Content-Type: application/json" \
  -d '{
    "user_message": "Show me all drugs",
    "table_name": "drugs"
  }'
```

---

## Database Service (`db_service.py`)

The `DatabaseService` class provides all database operations. Used internally by `TextToSQL` and available for direct use.

### Constructor

```python
from db_service import DatabaseService

# From config file (~/.query-mcp/config.json)
db = DatabaseService.from_config()

# Manual
db = DatabaseService(host="localhost", port=5432, name="testdb", user="postgres", password="postgres")
```

### Schema Methods

#### `list_tables() → list[str]`
Returns all user tables in the `public` schema.

#### `get_table_schema(table_name) → str`
Returns formatted column names and types. Raises `ValueError` if table not found.

### Query Methods

#### `execute_query(sql, params=None, limit=100) → dict`
Execute a SELECT query. Auto-appends `LIMIT` if missing.

**Returns:**
```json
{"success": true, "results": [{"id": 1, ...}], "row_count": 1, "error": null}
```

#### `execute_write(sql, params=None) → int`
Execute INSERT/UPDATE/DELETE. Returns affected row count.

#### `fetch_all(table, where=None, params=None, limit=100) → dict`
Convenience wrapper for `SELECT * FROM table [WHERE ...]`.

#### `fetch_one(table, where, params=None) → Optional[dict]`
Fetch a single row or `None`.

#### `count(table, where=None, params=None) → int`
Return row count.

### Query History Methods

#### `log_query(...) → int`
Insert a record into `query_history`. Returns the new row id.

**Parameters:**

| Parameter | Type | Required | Description |
|-----------|------|----------|-------------|
| `user_message` | str | Yes | The natural language query |
| `table_name` | str | No | Target table |
| `generated_sql` | str | No | SQL produced by LLM |
| `success` | bool | No | Whether execution succeeded |
| `row_count` | int | No | Number of result rows |
| `error` | str | No | Error message if failed |
| `llm_provider` | str | No | Provider used (zai/anthropic) |
| `llm_model` | str | No | Model name |
| `execution_time_ms` | int | No | Total time in milliseconds |
| `session_id` | str | No | Session identifier |

#### `get_query_history(limit=50, session_id=None, success_only=False) → list[dict]`
Fetch recent query history records, newest first.

---

## Query History Tables

### `query_sessions`

| Column | Type | Description |
|--------|------|-------------|
| `id` | SERIAL PK | Auto-increment |
| `session_id` | VARCHAR(64) | Session identifier |
| `started_at` | TIMESTAMP | Session start time |

### `query_history`

| Column | Type | Description |
|--------|------|-------------|
| `id` | SERIAL PK | Auto-increment |
| `session_id` | VARCHAR(64) | Links to session |
| `user_message` | TEXT | Natural language query |
| `table_name` | VARCHAR(255) | Target table |
| `generated_sql` | TEXT | SQL from LLM |
| `success` | BOOLEAN | Execution result |
| `row_count` | INTEGER | Rows returned |
| `error` | TEXT | Error message |
| `llm_provider` | VARCHAR(50) | zai or anthropic |
| `llm_model` | VARCHAR(100) | Model name |
| `execution_time_ms` | INTEGER | Total time ms |
| `created_at` | TIMESTAMP | When logged |

**Indexes:** `session_id`, `created_at`, `table_name`, `success`

---

## Migration Runner (`migrate.py`)

### CLI Usage

```bash
# Apply all pending migrations
python src/migrate.py

# Show migration status
python src/migrate.py status
```

### Migration Files

Place numbered `.sql` files in `migrations/`:
```
migrations/
├── 001_initial_schema.sql
├── 002_seed_data.sql
├── 003_create_views.sql
└── 004_query_history.sql
```

**Naming convention:** `NNN_description.sql` — sorted lexically.

### Tracking Table: `schema_migrations`

| Column | Type | Description |
|--------|------|-------------|
| `version` | VARCHAR(255) PK | Migration filename stem (e.g. `001_initial_schema`) |
| `applied_at` | TIMESTAMP | When applied |

Each migration runs in a transaction. On failure, the transaction rolls back and no version is recorded.

---

## Configuration Options

| Option | Type | Default | Example |
|--------|------|---------|---------|
| `QUERY_MCP_API_KEY` | env var | - | `AIzaSy...` (Gemini key) |
| `text_to_sql.llm_api_key` | config | - | (same as above) |
| `text_to_sql.llm_provider` | config | "gemini" | "gemini", "zai", "anthropic" |
| `text_to_sql.llm_model` | config | "gemini-2.5-flash" | "gemini-2.0-flash", "glm-5.1", "claude-3-5-sonnet-20241022" |
| `database.host` | config | "localhost" | "postgres.example.com" |
| `database.port` | config | 5432 | 5432 |
| `database.name` | config | "postgres" | "mydb" |
| `database.user` | config | "postgres" | "app_user" |
| `database.password` | config | "postgres" | (secure password) |

---

## Limits

- **Result limit:** Default 100 rows, max 10000 (configurable)
- **Query timeout:** 30 seconds (configurable)
- **API key length:** Up to 256 characters
- **Table name length:** PostgreSQL limits (typically 63 characters)
- **SQL generation limit:** 500 tokens

---

## Support

For issues:
1. Check error message
2. Review this reference
3. Check README.md
4. Check ARCHITECTURE.md
5. Review DEPLOYMENT.md for deployment issues
