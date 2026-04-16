# Query MCP - API Endpoints Reference

Complete documentation for all HTTP REST API endpoints.

**Base URL:** `http://localhost:8001` (or custom port)

---

## Health Check Endpoints

### GET `/health`
Health check (root level).

**Response:**
```json
{
  "status": "ok"
}
```

### GET `/api/health`
Health check (API namespace).

**Response:**
```json
{
  "status": "ok"
}
```

---

## Text-to-SQL Endpoints

### POST `/api/ask`
**Full pipeline:** Generate SQL from natural language → Execute query → Generate natural language answer.

**Request Body:**
```json
{
  "user_message": "What are the top 5 most expensive drugs?",
  "table_name": "drugs",
  "limit": 100,
  "llm_provider": "gemini",
  "lang": "en"
}
```

| Parameter | Type | Required | Default | Description |
|-----------|------|----------|---------|-------------|
| `user_message` | string | Yes | - | Natural language question |
| `table_name` | string | Yes | - | PostgreSQL table to query |
| `limit` | integer | No | 100 | Maximum rows to return |
| `llm_provider` | string | No | config | LLM provider: "gemini", "zai", or "anthropic" |
| `lang` | string | No | "en" | Response language: "en", "vi", etc. |

**Response (Success - HTTP 200):**
```json
{
  "success": true,
  "sql": "SELECT name, price FROM drugs ORDER BY price DESC LIMIT 5",
  "results": [
    {"name": "Drug A", "price": 150.00},
    {"name": "Drug B", "price": 140.00}
  ],
  "row_count": 5,
  "answer": "The most expensive drugs are Drug A at $150 and Drug B at $140.",
  "needs_clarification": false,
  "clarification": null,
  "error": null
}
```

**Response (Clarification Needed - HTTP 200):**
```json
{
  "success": false,
  "sql": null,
  "results": null,
  "row_count": 0,
  "answer": null,
  "needs_clarification": true,
  "clarification": "You asked about 'drugs with best price', but 'best' is ambiguous. Do you mean lowest price, highest price, or most recommended by doctors?",
  "error": null
}
```

**Response (Error - HTTP 200):**
```json
{
  "success": false,
  "sql": null,
  "results": null,
  "row_count": 0,
  "answer": null,
  "needs_clarification": false,
  "clarification": null,
  "error": "Table 'drugs' not found or has no columns"
}
```

**HTTP Status Codes:**
| Code | Meaning |
|------|---------|
| 200 | Success OR error with details (check `success` field) |
| 400 | Bad request (missing required parameters) |
| 500 | Server error (database/LLM failure) |

**curl Example:**
```bash
curl -s -X POST http://localhost:8001/api/ask \
  -H "Content-Type: application/json" \
  -d '{
    "user_message": "Show me the top 5 most expensive drugs",
    "table_name": "drugs",
    "limit": 5,
    "llm_provider": "gemini"
  }'
```

---

### POST `/api/query`
**Generate SQL and execute** (returns raw results without natural language summary).

**Request Body:**
```json
{
  "user_message": "Count drugs by category",
  "table_name": "drugs",
  "limit": 50,
  "llm_provider": "gemini",
  "lang": "en"
}
```

| Parameter | Type | Required | Default | Description |
|-----------|------|----------|---------|-------------|
| `user_message` | string | Yes | - | Natural language query |
| `table_name` | string | Yes | - | PostgreSQL table to query |
| `limit` | integer | No | 100 | Maximum rows to return |
| `llm_provider` | string | No | config | LLM provider: "gemini", "zai", or "anthropic" |
| `lang` | string | No | "en" | Response language ("en", "vi", etc.) |

**Response (Success - HTTP 200):**
```json
{
  "success": true,
  "sql": "SELECT category, COUNT(*) as count FROM drugs GROUP BY category",
  "results": [
    {"category": "Pain Relief", "count": 5},
    {"category": "Antibiotics", "count": 3}
  ],
  "row_count": 2,
  "needs_clarification": false,
  "clarification": null,
  "error": null
}
```

**Response (Clarification Needed - HTTP 200):**
```json
{
  "success": false,
  "sql": null,
  "results": null,
  "row_count": 0,
  "needs_clarification": true,
  "clarification": "Query unclear: do you want count by category or by price range?",
  "error": null
}
```

**curl Example:**
```bash
curl -s -X POST http://localhost:8001/api/query \
  -H "Content-Type: application/json" \
  -d '{
    "user_message": "Count drugs by category",
    "table_name": "drugs"
  }'
```

---

### POST `/api/sql`
**Generate SQL only** (no execution).

**Request Body:**
```json
{
  "user_message": "Find all inactive drugs",
  "table_name": "drugs",
  "llm_provider": "gemini",
  "lang": "en"
}
```

| Parameter | Type | Required | Default | Description |
|-----------|------|----------|---------|-------------|
| `user_message` | string | Yes | - | Natural language query |
| `table_name` | string | Yes | - | PostgreSQL table to query |
| `llm_provider` | string | No | config | LLM provider: "gemini", "zai", or "anthropic" |
| `lang` | string | No | "en" | Response language ("en", "vi", etc.) |

**Response (Success - HTTP 200):**
```json
{
  "success": true,
  "sql": "SELECT * FROM drugs WHERE status = 'inactive'",
  "needs_clarification": false,
  "clarification": null,
  "error": null
}
```

**Response (Clarification Needed - HTTP 200):**
```json
{
  "success": false,
  "sql": null,
  "needs_clarification": true,
  "clarification": "The column 'status' does not exist in the drugs table. Available columns are: id, name, price, category.",
  "error": null
}
```

**curl Example:**
```bash
curl -s -X POST http://localhost:8001/api/sql \
  -H "Content-Type: application/json" \
  -d '{
    "user_message": "Find inactive drugs",
    "table_name": "drugs"
  }'
```

---

### POST `/api/execute`
**Execute raw SQL** (no generation, just execution).

**Request Body:**
```json
{
  "sql_query": "SELECT name, price FROM drugs WHERE price > 100 ORDER BY price DESC",
  "limit": 10
}
```

| Parameter | Type | Required | Default | Description |
|-----------|------|----------|---------|-------------|
| `sql_query` | string | Yes | - | SQL query to execute |
| `limit` | integer | No | 100 | Maximum rows to return |

**Response (Success - HTTP 200):**
```json
{
  "success": true,
  "results": [
    {"name": "Premium Drug A", "price": 250.00},
    {"name": "Premium Drug B", "price": 200.00}
  ],
  "row_count": 2,
  "error": null
}
```

**Response (Error - HTTP 200):**
```json
{
  "success": false,
  "results": null,
  "row_count": 0,
  "error": "Query execution failed: syntax error at or near 'SELEC'"
}
```

**HTTP Status Codes:**
| Code | Meaning |
|------|---------|
| 200 | Success OR error with details (check `success` field) |
| 400 | Bad request (missing `sql_query` parameter) |
| 500 | Server error (database failure) |

**curl Example:**
```bash
curl -s -X POST http://localhost:8001/api/execute \
  -H "Content-Type: application/json" \
  -d '{
    "sql_query": "SELECT name, price FROM drugs WHERE price > 100",
    "limit": 5
  }'
```

---

## Schema Inspection Endpoints

### GET `/api/tables`
**List all tables** with metadata (row counts, size, etc.).

**Query Parameters:**
| Parameter | Type | Default | Description |
|-----------|------|---------|-------------|
| `search` | string | "" | Filter tables by name substring (case-insensitive) |
| `status` | string | "" | Filter by status: "active" (currently always active) |

**Response (HTTP 200):**
```json
{
  "data": [
    {
      "id": "src_a1b2c3d4",
      "name": "drugs",
      "format": "TABLE",
      "rows": "15",
      "size": "64 kB",
      "status": "active",
      "icon": "table_chart",
      "color": "#adc6ff"
    },
    {
      "id": "src_e5f6g7h8",
      "name": "users",
      "format": "TABLE",
      "rows": "10",
      "size": "32 kB",
      "status": "active",
      "icon": "table_chart",
      "color": "#adc6ff"
    }
  ],
  "count": 2
}
```

**Error Response (HTTP 500):**
```json
{
  "success": false,
  "error": "Database connection failed"
}
```

**curl Example:**
```bash
# List all tables
curl -s http://localhost:8001/api/tables

# Search for specific table
curl -s "http://localhost:8001/api/tables?search=drug"

# Filter by status
curl -s "http://localhost:8001/api/tables?status=active"
```

---

### GET `/api/tables/{table_id}`
**Get single table metadata including all columns with their types and comments.**

**Path Parameters:**
| Parameter | Type | Description |
|-----------|------|-------------|
| `table_id` | string | Table ID from `/api/tables` (e.g., `"src_03630eec"`) |

**Response (HTTP 200):**
```json
{
  "id": "src_03630eec",
  "name": "medicine_bid",
  "format": "TABLE",
  "rows": "1,988",
  "size": "1760 kB",
  "status": "active",
  "icon": "table_chart",
  "color": "#adc6ff",
  "columns": [
    {
      "name": "id",
      "type": "integer",
      "comment": null,
      "nullable": false
    },
    {
      "name": "name",
      "type": "text",
      "comment": "Tên thuốc",
      "nullable": false
    },
    {
      "name": "registration_number",
      "type": "text",
      "comment": "Số DK (số đăng ký)",
      "nullable": true
    }
  ]
}
```

**Column fields:**
| Field | Type | Description |
|-------|------|-------------|
| `name` | string | Column name |
| `type` | string | PostgreSQL data type (e.g. `"text"`, `"integer"`, `"numeric(10,2)"`) |
| `comment` | string\|null | Column comment — Vietnamese name for `medicine_bid` columns, XLS source column name for imported fields; `null` if no comment set |
| `nullable` | boolean | Whether the column accepts NULL values |

**Error Response (HTTP 404):**
```json
{
  "error": "Table not found"
}
```

**Error Response (HTTP 500):**
```json
{
  "success": false,
  "error": "Database connection failed"
}
```

**curl Example:**
```bash
curl -s http://localhost:8001/api/tables/src_03630eec
```

---

### GET `/api/tables/{table_id}/schema`
**Get table column definitions** (includes column names, types, nullability, and primary key info).

**Path Parameters:**
| Parameter | Type | Description |
|-----------|------|-------------|
| `table_id` | string | Table ID (e.g., "src_a1b2c3d4") |

**Response (HTTP 200):**
```json
{
  "tableId": "src_a1b2c3d4",
  "tableName": "drugs",
  "columns": [
    {
      "ordinal_position": 1,
      "column_name": "id",
      "data_type": "integer",
      "is_nullable": false,
      "is_primary_key": true
    },
    {
      "ordinal_position": 2,
      "column_name": "name",
      "data_type": "character varying",
      "is_nullable": false,
      "is_primary_key": false
    },
    {
      "ordinal_position": 3,
      "column_name": "price",
      "data_type": "numeric",
      "is_nullable": true,
      "is_primary_key": false
    },
    {
      "ordinal_position": 4,
      "column_name": "status",
      "data_type": "character varying",
      "is_nullable": true,
      "is_primary_key": false
    }
  ]
}
```

**Error Response (HTTP 404):**
```json
{
  "error": "Table not found"
}
```

**curl Example:**
```bash
curl -s http://localhost:8001/api/tables/src_a1b2c3d4/schema
```

---

### GET `/api/tables/{table_id}/data`
**Get paginated table data** with optional sorting (uses parameterized queries for safety).

**Path Parameters:**
| Parameter | Type | Description |
|-----------|------|-------------|
| `table_id` | string | Table ID (e.g., "src_a1b2c3d4") |

**Query Parameters:**
| Parameter | Type | Default | Description |
|-----------|------|---------|-------------|
| `limit` | integer | 20 | Number of rows per page (max 1000) |
| `offset` | integer | 0 | Number of rows to skip (pagination) |
| `sort` | string | "" | Column name to sort by (must be valid column) |
| `order` | string | "asc" | Sort direction: "asc" or "desc" |

**Response (HTTP 200):**
```json
{
  "tableId": "src_a1b2c3d4",
  "rows": [
    {
      "id": 1,
      "name": "Aspirin",
      "price": 5.99,
      "status": "active"
    },
    {
      "id": 2,
      "name": "Ibuprofen",
      "price": 8.99,
      "status": "active"
    },
    {
      "id": 3,
      "name": "Paracetamol",
      "price": 4.99,
      "status": "inactive"
    }
  ],
  "pagination": {
    "limit": 20,
    "offset": 0,
    "total": 15,
    "hasMore": false
  }
}
```

**Error Response (HTTP 404):**
```json
{
  "error": "Table not found"
}
```

**Notes:**
- Table/column names validated against schema before query (prevents SQL injection)
- Sort column validated against schema
- Returns all columns from table in natural order

**curl Examples:**
```bash
# Get first 20 rows
curl -s http://localhost:8001/api/tables/src_a1b2c3d4/data

# Get rows 10-30
curl -s "http://localhost:8001/api/tables/src_a1b2c3d4/data?limit=20&offset=10"

# Sort by price descending
curl -s "http://localhost:8001/api/tables/src_a1b2c3d4/data?sort=price&order=desc&limit=10"

# Sort by name ascending
curl -s "http://localhost:8001/api/tables/src_a1b2c3d4/data?sort=name&order=asc"
```

---

### GET `/api/tables/{table_id}/stats`
**Get table statistics** (row count, column summaries, numeric aggregates, text distributions).

**Path Parameters:**
| Parameter | Type | Description |
|-----------|------|-------------|
| `table_id` | string | Table ID (e.g., "src_a1b2c3d4") |

**Response (HTTP 200):**
```json
{
  "tableId": "src_a1b2c3d4",
  "totalRows": 15,
  "columnCount": 4,
  "size": "64 kB",
  "format": "PostgreSQL",
  "numericSummaries": [
    {
      "field": "price",
      "avg": 45.50,
      "min": 4.99,
      "max": 299.99
    },
    {
      "field": "id",
      "avg": 8.0,
      "min": 1,
      "max": 15
    }
  ],
  "distributions": {
    "status": [
      {
        "label": "active",
        "count": 12,
        "percent": 80,
        "color": "#4edea3"
      },
      {
        "label": "inactive",
        "count": 3,
        "percent": 20,
        "color": "#adc6ff"
      }
    ]
  }
}
```

**Error Response (HTTP 404):**
```json
{
  "error": "Table not found"
}
```

**Notes:**
- `numericSummaries`: AVG, MIN, MAX for numeric columns (up to 5 columns included)
  - Types: integer, bigint, smallint, numeric, decimal, real, double precision, money
- `distributions`: Value counts for low-cardinality text columns (≤20 distinct values, up to 3 columns included)
  - Types: character varying, varchar, text, char, character, boolean
- `color`: UI-friendly color codes for visualization (#4edea3, #adc6ff, #ffb3b0, #ffd280, #c2c6d6, #8c909f)

**curl Example:**
```bash
curl -s http://localhost:8001/api/tables/src_a1b2c3d4/stats
```

---

### GET `/api/columns/{table_ref}`
**Get column names** for autocomplete (supports table ID or table name).

**Path Parameters:**
| Parameter | Type | Description |
|-----------|------|-------------|
| `table_ref` | string | Table ID (e.g., "src_a1b2c3d4") or plain table name (e.g., "drugs") |

**Response (HTTP 200):**
```json
{
  "tableName": "drugs",
  "columns": [
    "id",
    "name",
    "price",
    "status",
    "category"
  ]
}
```

**Error Response (HTTP 404 - Table not found):**
```json
{
  "error": "Table 'nonexistent' not found"
}
```

**Notes:**
- Accepts both table ID and table name for flexibility
- Returns columns in ordinal (creation) order
- Useful for autocomplete UIs and form builders

**curl Examples:**
```bash
# Using table ID
curl -s http://localhost:8001/api/columns/src_a1b2c3d4

# Using table name
curl -s http://localhost:8001/api/columns/drugs
```

---

## Query History Endpoint

### GET `/api/query/history`
**Get execution history** of past queries (SQL generation and execution logs for audit trail).

**Query Parameters:**
| Parameter | Type | Default | Description |
|-----------|------|---------|-------------|
| `conversationId` | string | null | Filter by session/conversation ID |
| `limit` | integer | 50 | Maximum number of history records to return |

**Response (HTTP 200):**
```json
{
  "conversations": [
    {
      "id": "query_123abc",
      "user_message": "Show me the top 5 most expensive drugs",
      "table_name": "drugs",
      "generated_sql": "SELECT name, price FROM drugs ORDER BY price DESC LIMIT 5",
      "success": true,
      "row_count": 5,
      "execution_time_ms": 45,
      "llm_provider": "gemini",
      "llm_model": "gemini-2.5-flash",
      "error": null,
      "created_at": "2026-04-15T10:30:45Z",
      "session_id": "session_xyz789"
    },
    {
      "id": "query_456def",
      "user_message": "Count items by category",
      "table_name": "items",
      "generated_sql": "SELECT category, COUNT(*) FROM items GROUP BY category",
      "success": true,
      "row_count": 8,
      "execution_time_ms": 32,
      "llm_provider": "gemini",
      "llm_model": "gemini-2.5-flash",
      "error": null,
      "created_at": "2026-04-15T10:25:12Z",
      "session_id": "session_xyz789"
    }
  ],
  "count": 2
}
```

**Error Response (HTTP 500):**
```json
{
  "success": false,
  "error": "Database connection failed"
}
```

**Notes:**
- All queries are logged automatically (success and failure)
- `execution_time_ms`: Time from query submission to results returned
- `error`: Only populated if `success` is false
- Sorted by `created_at` in descending order (newest first)

**curl Examples:**
```bash
# Get recent 50 queries
curl -s http://localhost:8001/api/query/history

# Get 100 queries
curl -s "http://localhost:8001/api/query/history?limit=100"

# Get queries from specific conversation
curl -s "http://localhost:8001/api/query/history?conversationId=session_xyz789&limit=50"
```

---

## Error Responses

### 400 Bad Request
Missing or invalid required parameters.

```json
{
  "success": false,
  "error": "Required: user_message, table_name"
}
```

**When:** POST endpoints receive request missing required fields
**Action:** Check request body has all required parameters

---

### 404 Not Found
Resource not found (table, column, etc.).

```json
{
  "error": "Table not found"
}
```

**When:** Requesting a table/table_id that doesn't exist in database
**Action:** Check table name spelling (case-sensitive in PostgreSQL)

---

### 500 Internal Server Error
Server error (database connection, LLM API failure, etc.).

```json
{
  "success": false,
  "error": "Database connection failed: could not connect to server"
}
```

**When:** Database unreachable, LLM API down, query execution error
**Action:** Check database connection config, verify LLM API key, check database logs

---

### 200 OK with Error Details
Text-to-SQL endpoints return 200 even on errors (check `success` field).

```json
{
  "success": false,
  "sql": null,
  "results": null,
  "row_count": 0,
  "answer": null,
  "needs_clarification": false,
  "clarification": null,
  "error": "Unsupported LLM provider: gpt-4"
}
```

**When:** POST /api/ask, /api/query, /api/sql return structured error response
**Action:** Check `error` field for details, or check `needs_clarification` if user needs to rephrase

---

## Common Error Messages

| Error | Cause | Fix |
|-------|-------|-----|
| `Required: user_message, table_name` | Missing required POST parameters | Include both fields in request body |
| `Table 'xyz' not found or has no columns` | Table doesn't exist | Check table name (case-sensitive in PostgreSQL) |
| `LLM API key not configured` | Missing API key | Set `QUERY_MCP_API_KEY` env var or config.json |
| `Database connection failed` | Can't connect to postgres | Verify postgres is running, check config.json |
| `Query execution failed: syntax error` | Invalid SQL generated | Check generated SQL, try different phrasing |
| `Unsupported LLM provider: xyz` | Unknown provider | Use "gemini", "zai", or "anthropic" |

---

## Authentication

Currently **no authentication required** for HTTP endpoints. For production deployment, add:
- API key validation middleware
- Rate limiting
- CORS restrictions

See [DEPLOYMENT.md](DEPLOYMENT.md) for security recommendations.

---

## Rate Limits

No built-in rate limiting. For production:
- Implement per-IP rate limits
- Cache frequently accessed schema data
- Use connection pooling for postgres

---

## Response Formats

All responses use `Content-Type: application/json`.

**Standard success response:**
```json
{
  "success": true,
  "data": {...}
}
```

**Standard error response:**
```json
{
  "success": false,
  "error": "Human-readable error message"
}
```

---

## Examples by Use Case

### Use Case 1: Simple Natural Language Query
Ask a question, get a text answer.

```bash
curl -s -X POST http://localhost:8001/api/ask \
  -H "Content-Type: application/json" \
  -d '{
    "user_message": "What is the average drug price?",
    "table_name": "drugs"
  }'
```

### Use Case 2: Generate SQL for Review
Generate SQL without executing it.

```bash
curl -s -X POST http://localhost:8001/api/sql \
  -H "Content-Type: application/json" \
  -d '{
    "user_message": "Show drugs with price > $50",
    "table_name": "drugs"
  }'
```

### Use Case 3: Raw Data Export
Get paginated table data for export/processing.

```bash
curl -s "http://localhost:8001/api/tables/src_abc123/data?limit=1000&offset=0" | jq '.rows' > export.json
```

### Use Case 4: Schema Discovery
Understand table structure before querying.

```bash
# List all tables
curl -s http://localhost:8001/api/tables

# Get specific table schema
curl -s http://localhost:8001/api/tables/src_abc123/schema

# Get statistics
curl -s http://localhost:8001/api/tables/src_abc123/stats
```

### Use Case 5: Execute Custom SQL
Run your own SQL directly.

```bash
curl -s -X POST http://localhost:8001/api/execute \
  -H "Content-Type: application/json" \
  -d '{
    "sql_query": "SELECT COUNT(*) as total FROM drugs WHERE price > 100",
    "limit": 10
  }'
```

### Use Case 6: Audit Trail
Review query history.

```bash
# Recent queries
curl -s http://localhost:8001/api/query/history

# Queries from specific session
curl -s "http://localhost:8001/api/query/history?conversationId=myconversation&limit=100"
```

---

## Testing with curl

```bash
# 1. Check health
curl http://localhost:8001/api/health

# 2. List tables
curl http://localhost:8001/api/tables

# 3. Ask a question
curl -X POST http://localhost:8001/api/ask \
  -H "Content-Type: application/json" \
  -d '{"user_message":"top 5 items","table_name":"drugs"}'

# 4. Get table data
curl "http://localhost:8001/api/tables/src_TABLEID/data?limit=5"

# 5. View history
curl http://localhost:8001/api/query/history
```
