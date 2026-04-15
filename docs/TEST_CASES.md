# Query MCP - Test Cases

Complete test suite for all API endpoints with curl examples and expected responses.

## Setup

```bash
# Start server
python3 src/server.py http 8001

# Verify server is running
curl http://localhost:8001/api/health
```

---

## Health Check Tests

### TC-001: Health check endpoint
**Endpoint:** `GET /health`
**Expected Status:** 200

```bash
curl http://localhost:8001/health
```

**Expected Response:**
```json
{"status": "ok"}
```

---

### TC-002: API health endpoint
**Endpoint:** `GET /api/health`
**Expected Status:** 200

```bash
curl http://localhost:8001/api/health
```

**Expected Response:**
```json
{"status": "ok"}
```

---

## Text-to-SQL Tests

### TC-003: Generate SQL from natural language
**Endpoint:** `POST /api/sql`
**Expected Status:** 200

```bash
curl -X POST http://localhost:8001/api/sql \
  -H "Content-Type: application/json" \
  -d '{
    "user_message": "show drugs with price > 100",
    "table_name": "drugs"
  }'
```

**Expected Response:**
```json
{
  "success": true,
  "sql": "SELECT * FROM drugs WHERE price > 100",
  "needs_clarification": false,
  "clarification": null,
  "error": null
}
```

---

### TC-004: SQL generation with clarification needed
**Endpoint:** `POST /api/sql`
**Expected Status:** 200

```bash
curl -X POST http://localhost:8001/api/sql \
  -H "Content-Type: application/json" \
  -d '{
    "user_message": "show best drugs",
    "table_name": "drugs"
  }'
```

**Expected Response:** (may ask for clarification)
```json
{
  "success": false,
  "sql": null,
  "needs_clarification": true,
  "clarification": "What do you mean by 'best' — lowest price, highest rating, or most prescribed?",
  "error": null
}
```

---

### TC-005: Generate and execute SQL
**Endpoint:** `POST /api/query`
**Expected Status:** 200

```bash
curl -X POST http://localhost:8001/api/query \
  -H "Content-Type: application/json" \
  -d '{
    "user_message": "count drugs by category",
    "table_name": "drugs",
    "limit": 10
  }'
```

**Expected Response:**
```json
{
  "success": true,
  "sql": "SELECT category, COUNT(*) as count FROM drugs GROUP BY category",
  "results": [
    {"category": "Pain Relief", "count": 6},
    {"category": "Antihistamine", "count": 4}
  ],
  "row_count": 10,
  "needs_clarification": false,
  "clarification": null,
  "error": null
}
```

---

### TC-006: Full pipeline (ask for answer)
**Endpoint:** `POST /api/ask`
**Expected Status:** 200

```bash
curl -X POST http://localhost:8001/api/ask \
  -H "Content-Type: application/json" \
  -d '{
    "user_message": "What is the average drug price?",
    "table_name": "drugs",
    "limit": 100
  }'
```

**Expected Response:**
```json
{
  "success": true,
  "sql": "SELECT AVG(price) FROM drugs",
  "results": [{"avg": 55.66}],
  "row_count": 1,
  "answer": "The average drug price is $55.66.",
  "needs_clarification": false,
  "clarification": null,
  "error": null
}
```

---

### TC-007: Execute raw SQL
**Endpoint:** `POST /api/execute`
**Expected Status:** 200

```bash
curl -X POST http://localhost:8001/api/execute \
  -H "Content-Type: application/json" \
  -d '{
    "sql_query": "SELECT name, price FROM drugs WHERE price > 100 ORDER BY price DESC LIMIT 5",
    "limit": 5
  }'
```

**Expected Response:**
```json
{
  "success": true,
  "results": [
    {"name": "Pracetam 400", "price": 830.0},
    {"name": "Statripsine", "price": 625.0}
  ],
  "row_count": 2,
  "error": null
}
```

---

### TC-008: Execute invalid SQL
**Endpoint:** `POST /api/execute`
**Expected Status:** 200

```bash
curl -X POST http://localhost:8001/api/execute \
  -H "Content-Type: application/json" \
  -d '{
    "sql_query": "SELCT * FROM drugs",
    "limit": 10
  }'
```

**Expected Response:**
```json
{
  "success": false,
  "results": null,
  "row_count": 0,
  "error": "Query execution failed: syntax error at or near 'SELCT'"
}
```

---

## Schema Inspection Tests

### TC-009: List all tables
**Endpoint:** `GET /api/tables`
**Expected Status:** 200

```bash
curl http://localhost:8001/api/tables
```

**Expected Response:**
```json
{
  "data": [
    {
      "id": "src_8266cbec",
      "name": "drugs",
      "format": "TABLE",
      "rows": "40",
      "size": "80 kB",
      "status": "active",
      "icon": "table_chart",
      "color": "#adc6ff"
    }
  ],
  "count": 1
}
```

---

### TC-010: Search tables by name
**Endpoint:** `GET /api/tables`
**Expected Status:** 200

```bash
curl "http://localhost:8001/api/tables?search=drug"
```

**Expected Response:** Tables matching "drug" in name

---

### TC-011: Get single table metadata
**Endpoint:** `GET /api/tables/{table_id}`
**Expected Status:** 200

```bash
curl http://localhost:8001/api/tables/src_8266cbec
```

**Expected Response:**
```json
{
  "id": "src_8266cbec",
  "name": "drugs",
  "format": "TABLE",
  "rows": "40",
  "size": "80 kB",
  "status": "active",
  "icon": "table_chart",
  "color": "#adc6ff"
}
```

---

### TC-012: Get table schema
**Endpoint:** `GET /api/tables/{table_id}/schema`
**Expected Status:** 200

```bash
curl http://localhost:8001/api/tables/src_8266cbec/schema
```

**Expected Response:**
```json
{
  "tableId": "src_8266cbec",
  "tableName": "drugs",
  "columns": [
    {
      "ordinal_position": 1,
      "column_name": "id",
      "data_type": "integer",
      "is_nullable": "NO",
      "is_primary_key": true
    },
    {
      "ordinal_position": 2,
      "column_name": "name",
      "data_type": "character varying",
      "is_nullable": "NO",
      "is_primary_key": false
    }
  ]
}
```

---

### TC-013: Get paginated table data
**Endpoint:** `GET /api/tables/{table_id}/data`
**Expected Status:** 200

```bash
curl "http://localhost:8001/api/tables/src_8266cbec/data?limit=10&offset=0"
```

**Expected Response:**
```json
{
  "tableId": "src_8266cbec",
  "rows": [
    {"id": 1, "name": "Aspirin", "price": 5.99, "stock": 500},
    {"id": 2, "name": "Ibuprofen", "price": 8.99, "stock": 450}
  ],
  "pagination": {
    "limit": 10,
    "offset": 0,
    "total": 40,
    "hasMore": true
  }
}
```

---

### TC-014: Get data with sorting ascending
**Endpoint:** `GET /api/tables/{table_id}/data`
**Expected Status:** 200

```bash
curl "http://localhost:8001/api/tables/src_8266cbec/data?sort=price&order=asc&limit=5"
```

**Expected:** First row should have lowest price

---

### TC-015: Get data with sorting descending
**Endpoint:** `GET /api/tables/{table_id}/data`
**Expected Status:** 200

```bash
curl "http://localhost:8001/api/tables/src_8266cbec/data?sort=price&order=desc&limit=5"
```

**Expected:** First row should have highest price

---

### TC-016: Get data pagination
**Endpoint:** `GET /api/tables/{table_id}/data`
**Expected Status:** 200

```bash
# Get next page (offset by 10)
curl "http://localhost:8001/api/tables/src_8266cbec/data?limit=10&offset=10"
```

**Expected:** Returns rows 11-20, hasMore should be true if total > 20

---

### TC-017: Get table statistics
**Endpoint:** `GET /api/tables/{table_id}/stats`
**Expected Status:** 200

```bash
curl http://localhost:8001/api/tables/src_8266cbec/stats
```

**Expected Response:**
```json
{
  "tableId": "src_8266cbec",
  "totalRows": 40,
  "columnCount": 9,
  "size": "80 kB",
  "format": "PostgreSQL",
  "numericSummaries": [
    {
      "field": "price",
      "avg": 55.66,
      "min": 1.04,
      "max": 830.0
    }
  ],
  "distributions": {
    "category": [
      {"label": "Pain Relief", "count": 6, "percent": 15, "color": "#4edea3"}
    ]
  }
}
```

---

### TC-018: Get column names for autocomplete
**Endpoint:** `GET /api/columns/{table_ref}`
**Expected Status:** 200

```bash
curl http://localhost:8001/api/columns/drugs
```

**Expected Response:**
```json
{
  "tableName": "drugs",
  "columns": ["id", "name", "category", "price", "stock", "status", "manufacturer", "created_at", "updated_at"]
}
```

---

### TC-019: Get columns using table ID
**Endpoint:** `GET /api/columns/{table_id}`
**Expected Status:** 200

```bash
curl http://localhost:8001/api/columns/src_8266cbec
```

**Expected Response:** Same as TC-018

---

## Query History Tests

### TC-020: Get recent query history
**Endpoint:** `GET /api/query/history`
**Expected Status:** 200

```bash
curl "http://localhost:8001/api/query/history?limit=10"
```

**Expected Response:**
```json
{
  "conversations": [
    {
      "id": "query_123",
      "user_message": "count drugs by category",
      "table_name": "drugs",
      "generated_sql": "SELECT category, COUNT(*) FROM drugs GROUP BY category",
      "success": true,
      "row_count": 8,
      "execution_time_ms": 45,
      "llm_provider": "gemini",
      "llm_model": "gemini-2.5-flash",
      "error": null,
      "created_at": "2026-04-15T18:18:45.702000",
      "session_id": "session_xyz"
    }
  ],
  "count": 1
}
```

---

### TC-021: Get query history for specific session
**Endpoint:** `GET /api/query/history`
**Expected Status:** 200

```bash
curl "http://localhost:8001/api/query/history?conversationId=session_xyz&limit=50"
```

**Expected:** Only queries from that session ID

---

## Error Handling Tests

### TC-022: Missing required parameter (POST)
**Endpoint:** `POST /api/ask`
**Expected Status:** 400

```bash
curl -X POST http://localhost:8001/api/ask \
  -H "Content-Type: application/json" \
  -d '{"user_message": "drugs"}'
```

**Expected Response:**
```json
{
  "success": false,
  "error": "Required: user_message, table_name"
}
```

---

### TC-023: Table not found
**Endpoint:** `GET /api/tables/src_nonexistent`
**Expected Status:** 404

```bash
curl http://localhost:8001/api/tables/src_nonexistent
```

**Expected Response:**
```json
{
  "error": "Table not found"
}
```

---

### TC-024: Database connection error
**Endpoint:** Any (when DB is down)
**Expected Status:** 500

```bash
# Stop postgres first, then request
curl http://localhost:8001/api/tables
```

**Expected Response:**
```json
{
  "success": false,
  "error": "connection to server... failed"
}
```

---

## Integration Tests

### TC-025: End-to-end workflow
Steps:
1. List available tables
2. Get schema for a table
3. Generate SQL from natural language
4. Execute the generated SQL
5. Check query history

```bash
# 1. List tables
curl http://localhost:8001/api/tables

# 2. Get schema
curl http://localhost:8001/api/tables/src_8266cbec/schema

# 3. Generate SQL
curl -X POST http://localhost:8001/api/sql \
  -H "Content-Type: application/json" \
  -d '{"user_message": "show top 5 expensive drugs", "table_name": "drugs"}'

# 4. Execute
curl -X POST http://localhost:8001/api/execute \
  -H "Content-Type: application/json" \
  -d '{"sql_query": "SELECT name, price FROM drugs ORDER BY price DESC LIMIT 5"}'

# 5. Check history
curl http://localhost:8001/api/query/history?limit=5
```

**Expected:** All steps complete successfully, query logged in history

---

## Performance Tests

### TC-026: Large offset pagination
**Endpoint:** `GET /api/tables/{table_id}/data`

```bash
curl "http://localhost:8001/api/tables/src_8266cbec/data?limit=20&offset=1000"
```

**Expected:** Should handle gracefully (return empty or error)

---

### TC-027: Maximum limit
**Endpoint:** `GET /api/tables/{table_id}/data`

```bash
# Request more than max (1000)
curl "http://localhost:8001/api/tables/src_8266cbec/data?limit=5000"
```

**Expected:** Limited to 1000 rows

---

### TC-028: Complex SQL execution
**Endpoint:** `POST /api/execute`

```bash
curl -X POST http://localhost:8001/api/execute \
  -H "Content-Type: application/json" \
  -d '{
    "sql_query": "SELECT category, COUNT(*) as cnt, AVG(price) as avg_price FROM drugs WHERE price > 50 GROUP BY category HAVING COUNT(*) > 2 ORDER BY avg_price DESC"
  }'
```

**Expected:** Complex query executes successfully

---

## Test Execution Commands

```bash
# Run all POST tests
for endpoint in ask query sql execute; do
  echo "Testing /api/$endpoint"
  curl -X POST http://localhost:8001/api/$endpoint \
    -H "Content-Type: application/json" \
    -d '{"user_message": "test", "table_name": "drugs"}' -s | jq '.success'
done

# Run all GET tests
for path in tables "tables?search=drug" tables/src_8266cbec tables/src_8266cbec/schema tables/src_8266cbec/data tables/src_8266cbec/stats columns/drugs query/history; do
  echo "Testing /api/$path"
  curl http://localhost:8001/api/$path -s | jq '.success // .status // "ok"'
done
```

---

## Test Summary

**Total Test Cases:** 28
**Categories:**
- Health Check: 2
- Text-to-SQL: 6
- Schema Inspection: 8
- Query History: 2
- Error Handling: 3
- Integration: 1
- Performance: 3
- Execution: 3

**Success Criteria:** All endpoints return expected status codes and response formats.