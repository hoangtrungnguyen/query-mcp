# Query MCP Architecture

## Overview

Query MCP is a Model Context Protocol (MCP) server that bridges natural language queries to PostgreSQL databases using LLM APIs.

```
Claude (or any MCP client)
    ↓
MCP Protocol (stdio/http)
    ↓
Query MCP Server
    ├─ LLM Provider (Z.ai, Anthropic)
    └─ PostgreSQL Database
```

## Components

### 1. MCP Server (`server.py`)

Entry point that implements the Model Context Protocol.

**Responsibilities:**
- Expose 3 MCP tools
- Manage 2 MCP resources
- Expose 1 MCP prompt
- Load configuration
- Handle requests

**Key Classes:**
```python
mcp = FastMCP(...)  # MCP server instance
```

### 2. TextToSQL Engine (`text_to_sql.py`)

Core business logic for SQL generation and execution.

**Responsibilities:**
- Call LLM API to generate SQL
- Delegate DB operations to DatabaseService
- Auto-log queries to history
- Handle errors gracefully

**Key Class:**
```python
class TextToSQL:
    def __init__(llm_api_key, db_config, llm_provider="zai")
    def generate_sql(user_message, table_name) → Dict
    def execute_query(sql_query, limit) → Dict
    def generate_and_execute(user_message, table_name, limit, session_id) → Dict
```

### 3. Database Service (`db_service.py`)

Central database layer. All DB access goes through this service.

**Responsibilities:**
- Connection management with context managers (no resource leaks)
- Schema introspection (`get_table_schema`, `list_tables`)
- Query execution (SELECT, INSERT/UPDATE/DELETE)
- Query history logging and retrieval
- Convenience helpers (`fetch_all`, `fetch_one`, `count`)

**Key Class:**
```python
class DatabaseService:
    @classmethod
    def from_config() → DatabaseService          # Factory from config.json
    def connection() → contextmanager             # Managed psycopg2 connection
    def cursor(dict_cursor=False) → contextmanager
    def get_table_schema(table_name) → str
    def list_tables() → list[str]
    def execute_query(sql, params, limit) → Dict
    def execute_write(sql, params) → int
    def fetch_all(table, where, params, limit) → Dict
    def fetch_one(table, where, params) → Optional[dict]
    def count(table, where, params) → int
    def log_query(...) → int                      # Write to query_history
    def get_query_history(limit, session_id, success_only) → list[dict]
```

### 4. Migration Runner (`migrate.py`)

Versioned SQL migration system.

**Responsibilities:**
- Track applied migrations in `schema_migrations` table
- Apply pending `.sql` files from `migrations/` in order
- Per-migration transactions with rollback on failure
- Status reporting

**Usage:**
```bash
python src/migrate.py           # Apply pending migrations
python src/migrate.py status    # Show applied/pending
```

### 5. Configuration (`~/.query-mcp/config.json`)

Persistent JSON configuration file.

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
    "llm_api_key": "...",
    "llm_provider": "zai",
    "llm_model": "glm-5.1"
  }
}
```

## Data Flow

### 1. Generate SQL (No Execution)

```
User: "Show me all drugs with price > 100"
    ↓
generate_sql(user_message, table_name)
    ├─ Get table schema from PostgreSQL
    ├─ Build system prompt with schema
    ├─ Call LLM API with user message
    └─ Return generated SQL
    ↓
Response: { success: true, sql: "SELECT ...", error: null }
```

### 2. Execute SQL (No Generation)

```
User: "SELECT * FROM drugs WHERE price > 100"
    ↓
execute_query(sql_query, limit)
    ├─ Open PostgreSQL connection
    ├─ Execute SQL query
    ├─ Fetch results (up to limit)
    └─ Convert to list of dicts
    ↓
Response: { success: true, results: [...], row_count: N, error: null }
```

### 3. Generate + Execute (Combined)

```
User: "Show me all drugs with price > 100"
    ↓
text_to_sql_execute(user_message, table_name, limit)
    ├─ Start timer
    ├─ Call generate_sql()
    │   ├─ DatabaseService.get_table_schema()
    │   └─ Call LLM
    ├─ Call execute_query()
    │   ├─ DatabaseService.execute_query()
    │   └─ Fetch results
    ├─ Log to query_history (best-effort)
    │   └─ DatabaseService.log_query(message, sql, timing, ...)
    └─ Return both SQL and results
    ↓
Response: { success: true, sql: "SELECT ...", results: [...], row_count: N, error: null }
```

### 4. Migration Flow

```
python src/migrate.py
    ↓
Ensure schema_migrations table exists
    ↓
Read applied versions from schema_migrations
    ↓
Scan migrations/*.sql for pending files
    ↓
For each pending migration:
    ├─ BEGIN transaction
    ├─ Execute SQL file
    ├─ INSERT version into schema_migrations
    └─ COMMIT (or ROLLBACK on error)
```

## LLM Provider Integration

### Z.ai (Default)

```python
from zai import ZaiClient

client = ZaiClient(api_key="...")
response = client.chat.completions.create(
    model="glm-5.1",
    messages=[{"role": "user", "content": "..."}],
    system="..."
)
sql = response.choices[0].message.content
```

**Advantages:**
- Fast inference
- Good SQL generation
- Supports function calling (future)

### Anthropic Claude

```python
from anthropic import Anthropic

client = Anthropic(api_key="...")
response = client.messages.create(
    model="claude-3-5-sonnet-20241022",
    messages=[{"role": "user", "content": "..."}],
    system="..."
)
sql = response.content[0].text
```

**Advantages:**
- High quality outputs
- Better reasoning
- More reliable

## Provider Selection Strategy

Priority (highest to lowest):

1. **Per-Request** (`llm_provider` parameter)
   ```json
   {
     "user_message": "...",
     "table_name": "...",
     "llm_provider": "anthropic"
   }
   ```

2. **Config File** (`text_to_sql.llm_provider`)
   ```json
   {
     "text_to_sql": {
       "llm_provider": "zai"
     }
   }
   ```

3. **Default** ("zai")

This allows users to:
- Override globally on-demand
- Set a project-wide default
- Fall back to built-in default

## Database Integration

### Connection Management (DatabaseService)

All database access goes through `db_service.DatabaseService`, which uses context managers to guarantee connection/cursor cleanup:

```python
# Context-managed connections — no resource leaks
with db.connection() as conn:
    ...  # auto-closed on exit

with db.cursor(dict_cursor=True) as cur:
    ...  # auto-committed or rolled back, then closed
```

Each operation creates a new connection. Connections are never leaked thanks to `contextlib.contextmanager`.

### Schema Discovery

```python
db.get_table_schema('drugs')
# Queries information_schema.columns
# Returns formatted string: "Table: drugs\nColumns:\n  - id: integer\n  ..."

db.list_tables()
# Returns all user tables in public schema
```

Used to:
- Validate table exists
- Build LLM system prompt
- Show column types to LLM

### Query Execution

```python
# Read queries — returns dict with success/results/row_count/error
db.execute_query("SELECT * FROM drugs WHERE price > %s", params=(100,), limit=50)

# Write queries — returns affected row count
db.execute_write("UPDATE drugs SET stock = %s WHERE id = %s", (0, 1))
```

Safety:
- No SQL injection (uses parameterized queries)
- Context-managed connections prevent resource leaks
- Auto-adds LIMIT to prevent huge result sets
- Automatic rollback on exceptions

### Query History

Every `generate_and_execute()` call logs to `query_history`:

```python
db.log_query(
    user_message="Show me expensive drugs",
    table_name="drugs",
    generated_sql="SELECT ...",
    success=True,
    row_count=5,
    llm_provider="zai",
    llm_model="glm-5.1",
    execution_time_ms=1250,
    session_id="abc123",
)
```

Logging is best-effort — failures never break the main request.

### Database Schema

**Application tables:** `drugs`, `items`, `users`, `orders`
**System tables:** `schema_migrations`, `query_sessions`, `query_history`
**Views:** `active_drugs`, `drugs_by_category`, `expensive_items`

## Error Handling Strategy

### Error Types

| Error Type | Source | Handling |
|-----------|--------|----------|
| Config Error | Startup | Raise exception, won't start |
| API Key Error | API call | Return `{success: false, error: "..."}` |
| Database Connection | DB connect | Return `{success: false, error: "..."}` |
| Table Not Found | Schema lookup | Return `{success: false, error: "..."}` |
| SQL Generation | LLM API | Return `{success: false, error: "..."}` |
| Query Execution | SQL execute | Return `{success: false, error: "..."}` |

### Error Response Pattern

All tools return consistent format:
```json
{
  "success": false,
  "error": "Human-readable error message",
  "sql": null,
  "results": null
}
```

Users should always check `success` field.

## Configuration Precedence

### API Key
1. `QUERY_MCP_API_KEY` environment variable
2. `text_to_sql.llm_api_key` in config.json
3. Error if neither set

### LLM Provider
1. `llm_provider` parameter in request
2. `text_to_sql.llm_provider` in config.json
3. Default: "zai"

### Database
1. Values from `database.*` in config.json
2. Defaults in code (localhost:5432)
3. Error if required fields missing

## MCP Protocol Details

### Tools
- `generate_sql(user_message, table_name, llm_provider?)`
- `execute_sql(sql_query, limit?, llm_provider?)`
- `text_to_sql_execute(user_message, table_name, limit?, llm_provider?)`

### Resources
- `config://database` - Database config (no password)
- `config://text-to-sql` - LLM config (no API key)

### Prompts
- `sql_query_help(query_type?)` - Help for SQL queries

## Security Considerations

### API Key Handling
- ✅ Never logged
- ✅ Read from env var first (not stored in config)
- ✅ Config file excluded from git
- ⚠️ Sensitive in memory during runtime

### Database Credentials
- ✅ Stored in `~/.query-mcp/config.json` (user's home, not git)
- ✅ Never exposed in responses
- ⚠️ Stored in plaintext (consider encryption)

### SQL Execution
- ✅ User provides explicit SQL or natural language
- ✅ Auto-adds LIMIT to prevent huge exports
- ⚠️ No query validation or sandboxing
- ⚠️ Full table access (user responsibility)

### LLM Prompts
- ✅ System prompt includes schema, not sensitive data
- ✅ User queries sent to LLM (user responsibility)
- ⚠️ Table/column names sent to LLM

## Performance Characteristics

### Latency
- Schema discovery: ~100ms (PostgreSQL)
- LLM API call: 500-2000ms (Z.ai/Anthropic)
- Query execution: 50-500ms (depends on query)
- **Total: 1-3 seconds per request**

### Resource Usage
- Memory: ~50-100MB (Python + libraries)
- CPU: Low (I/O bound)
- Database connections: 1 per operation (context-managed, auto-closed)
- Query history adds ~5ms overhead per logged query

## Extensibility

### Adding New LLM Providers

1. Update `TextToSQL.__init__()`:
```python
elif llm_provider == "openai":
    from openai import OpenAI
    self.client = OpenAI(api_key=llm_api_key)
    self.model = llm_model or "gpt-4"
```

2. Update `generate_sql()` to handle new provider API:
```python
if self.llm_provider == "openai":
    response = self.client.chat.completions.create(...)
    sql = response.choices[0].message.content
```

3. Update config defaults

### Adding New Tools

1. Create function in `server.py`:
```python
@mcp.tool
def my_tool(param1: str, param2: int) -> dict:
    """Description"""
    ...
    return {...}
```

2. FastMCP auto-exposes via MCP protocol

### Database Support

To support other databases:
1. Replace psycopg2 with appropriate driver
2. Update schema query (information_schema is PostgreSQL-specific)
3. Update connection string format
4. Test query execution

## Testing Strategy

Currently: Manual testing only

Future recommendations:
- Unit tests for TextToSQL (mock LLM, mock DB)
- Integration tests with real PostgreSQL
- MCP protocol tests with mock clients
- LLM provider tests with real APIs

## Deployment Options

### Local Development
```bash
python server.py
```

### Claude Desktop Integration
```json
{
  "mcpServers": {
    "query-mcp": {
      "command": "python",
      "args": ["/path/to/server.py"],
      "env": {"QUERY_MCP_API_KEY": "..."}
    }
  }
}
```

### Docker (Future)
```dockerfile
FROM python:3.11
WORKDIR /app
COPY . .
RUN pip install -r requirements.txt
CMD ["python", "server.py"]
```

### Cloud (Future)
- AWS Lambda + RDS
- GCP Cloud Functions + Cloud SQL
- Azure Functions + Azure Database for PostgreSQL
