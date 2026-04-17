# Query MCP - Local Setup Scripts

Helper scripts to run Query MCP locally with automatic migration handling.

## Prerequisites

- Python 3.8+
- PostgreSQL running on `localhost:5432` (user: `postgres`, password: `postgres`)
- API key for LLM provider (Gemini, Z.ai, or Anthropic)

## Quick Start

**All-in-one setup:**
```bash
./scripts/start.sh
```

Or use individual scripts:

## Individual Scripts

### `setup.sh` - Install Dependencies
Creates virtual environment and installs Python packages.
```bash
./scripts/setup.sh
```

Then activate:
```bash
source venv/bin/activate
```

### `migrate.sh` - Run Database Migrations
Creates `medicine_bid` table and indexes using Alembic.
```bash
source venv/bin/activate
./scripts/migrate.sh
```

Requires:
- PostgreSQL running
- Virtual environment activated
- Alembic installed (from `setup.sh`)

### `run.sh` - Start Server
Starts HTTP server on default port 8001 (or custom port).
```bash
source venv/bin/activate
./scripts/run.sh          # Port 8001
./scripts/run.sh 3000     # Custom port 3000
```

## Typical Workflow

**First time:**
```bash
./scripts/start.sh
# Completes setup, migrations, and starts server
```

**Subsequent runs:**
```bash
source venv/bin/activate
./scripts/run.sh          # Already set up & migrated
```

**Reset database:**
```bash
source venv/bin/activate
./scripts/migrate.sh      # Re-run migrations
```

## Troubleshooting

**PostgreSQL not found:**
```bash
# Make sure PostgreSQL is running
psql -h localhost -U postgres -c "SELECT 1"
```

**API key missing:**
```bash
export QUERY_MCP_API_KEY="your-api-key"
./scripts/run.sh
```

**Virtual environment not found:**
```bash
./scripts/setup.sh
```

## Server Endpoints

Once running, available at `http://localhost:8001`:

| Endpoint | Method | Purpose |
|----------|--------|---------|
| `/api/ask` | POST | Natural language → answer |
| `/api/query` | POST | Natural language → SQL + results |
| `/api/sql` | POST | Natural language → SQL |
| `/api/execute` | POST | Execute raw SQL |
| `/api/tables` | GET | List tables |
| `/health` | GET | Health check |

## Example Request

```bash
curl -X POST http://localhost:8001/api/ask \
  -H "Content-Type: application/json" \
  -d '{
    "user_message": "Show me top 5 medicines by price",
    "table_name": "medicine_bid",
    "limit": 5
  }'
```
