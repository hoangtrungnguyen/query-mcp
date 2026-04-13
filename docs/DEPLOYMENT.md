# Query MCP Deployment Guide

## Local Development

### Prerequisites
- Python 3.8+
- PostgreSQL running (or remote PostgreSQL accessible)
- Z.ai or Anthropic API key

### Setup

```bash
cd /home/htnguyen/Space/query-mcp
python3 -m venv venv
source venv/bin/activate
pip install -r requirements.txt

# Set API key
export QUERY_MCP_API_KEY="your-api-key"

# Run server
python server.py
```

Server starts on stdio by default (ready for MCP clients).

## Claude Code Integration

### Step 1: Install Dependencies
```bash
pip install -r requirements.txt
```

### Step 2: Set API Key
```bash
export QUERY_MCP_API_KEY="your-api-key"
```

### Step 3: Add to Claude Code

In Claude Code settings → MCP Servers:

```json
{
  "name": "Query MCP",
  "command": "python",
  "args": ["/home/htnguyen/Space/query-mcp/server.py"],
  "env": {
    "QUERY_MCP_API_KEY": "your-api-key"
  }
}
```

### Step 4: Use in Claude

Ask Claude:
- "Query the users table and show me active accounts"
- "Find the top 10 most expensive products"
- "Count orders by status"

## Claude Desktop Integration

### macOS

Edit `~/Library/Application Support/Claude/claude_desktop_config.json`:

```json
{
  "mcpServers": {
    "query-mcp": {
      "command": "python",
      "args": ["/home/htnguyen/Space/query-mcp/server.py"],
      "env": {
        "QUERY_MCP_API_KEY": "your-api-key"
      }
    }
  }
}
```

### Windows

Edit `%APPDATA%\Claude\claude_desktop_config.json`:

```json
{
  "mcpServers": {
    "query-mcp": {
      "command": "python",
      "args": ["C:\\path\\to\\query-mcp\\server.py"],
      "env": {
        "QUERY_MCP_API_KEY": "your-api-key"
      }
    }
  }
}
```

### Linux

Edit `~/.config/Claude/claude_desktop_config.json`:

```json
{
  "mcpServers": {
    "query-mcp": {
      "command": "python",
      "args": ["/home/user/query-mcp/server.py"],
      "env": {
        "QUERY_MCP_API_KEY": "your-api-key"
      }
    }
  }
}
```

Then restart Claude Desktop.

## Server Deployment

### HTTP Mode (For API Clients)

Modify `server.py` to run HTTP server:

```python
if __name__ == "__main__":
    mcp.run(transport="http", host="0.0.0.0", port=8000)
```

Then access via HTTP:
```bash
curl -X POST http://localhost:8000/tools/generate_sql \
  -H "Content-Type: application/json" \
  -d '{
    "user_message": "...",
    "table_name": "..."
  }'
```

### Systemd Service (Linux)

Create `/etc/systemd/system/query-mcp.service`:

```ini
[Unit]
Description=Query MCP Server
After=network.target

[Service]
Type=simple
User=query-mcp
WorkingDirectory=/home/query-mcp/Space/query-mcp
Environment="QUERY_MCP_API_KEY=your-api-key"
ExecStart=/home/query-mcp/Space/query-mcp/venv/bin/python server.py
Restart=always
RestartSec=10

[Install]
WantedBy=multi-user.target
```

Then:
```bash
sudo systemctl daemon-reload
sudo systemctl enable query-mcp
sudo systemctl start query-mcp
```

### Docker

Create `Dockerfile`:

```dockerfile
FROM python:3.11-slim

WORKDIR /app
COPY requirements.txt .
RUN pip install -r requirements.txt

COPY server.py .
COPY text_to_sql.py .

ENV QUERY_MCP_API_KEY=${QUERY_MCP_API_KEY}

CMD ["python", "server.py"]
```

Build and run:
```bash
docker build -t query-mcp .
docker run -e QUERY_MCP_API_KEY="your-key" query-mcp
```

### Docker Compose

Create `docker-compose.yml`:

```yaml
version: '3.9'

services:
  query-mcp:
    build: .
    environment:
      QUERY_MCP_API_KEY: ${QUERY_MCP_API_KEY}
      POSTGRES_HOST: postgres
    depends_on:
      - postgres

  postgres:
    image: postgres:15
    environment:
      POSTGRES_DB: mydb
      POSTGRES_USER: postgres
      POSTGRES_PASSWORD: postgres
    volumes:
      - postgres_data:/var/lib/postgresql/data

volumes:
  postgres_data:
```

Then:
```bash
export QUERY_MCP_API_KEY="your-key"
docker-compose up -d
```

## Production Checklist

### Security
- [ ] API key stored in environment variable (never in config file)
- [ ] Database password in env var or secure vault (not in code)
- [ ] PostgreSQL user has limited permissions (not superuser)
- [ ] Firewall restricts database access
- [ ] HTTPS/TLS for API connections (if using HTTP)

### Monitoring
- [ ] Logging configured (see `Logging` section)
- [ ] Error alerting set up
- [ ] Performance monitoring (response time, errors)
- [ ] Database connection monitoring

### Reliability
- [ ] Restart policy configured (systemd/Docker)
- [ ] Health checks implemented
- [ ] Timeout handling for slow LLM/DB
- [ ] Graceful shutdown

### Database
- [ ] Database backup strategy
- [ ] Connection pooling (if many concurrent users)
- [ ] Query timeout limits
- [ ] Index optimization for schema queries

## Configuration for Production

### Environment Variables

Set these before running:

```bash
export QUERY_MCP_API_KEY="prod-api-key"
export QUERY_MCP_DB_HOST="prod-postgres.internal"
export QUERY_MCP_DB_USER="query_mcp_user"
export QUERY_MCP_DB_PASSWORD="secure-password"
export QUERY_MCP_DB_NAME="production_db"
```

Or create `.env` file:
```
QUERY_MCP_API_KEY=prod-api-key
QUERY_MCP_DB_HOST=prod-postgres.internal
QUERY_MCP_DB_USER=query_mcp_user
QUERY_MCP_DB_PASSWORD=secure-password
QUERY_MCP_DB_NAME=production_db
```

Then load before running:
```bash
set -a
source .env
set +a
python server.py
```

### Config File Encryption (Future)

For sensitive config files:

```bash
# Encrypt
openssl enc -aes-256-cbc -salt -in config.json -out config.json.enc

# Decrypt and run
openssl enc -aes-256-cbc -d -in config.json.enc | python server.py
```

## Logging

Currently minimal logging. To add logging:

```python
import logging

logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler('/var/log/query-mcp/server.log'),
        logging.StreamHandler()
    ]
)

logger = logging.getLogger(__name__)

# In server.py
@mcp.tool
def generate_sql(...):
    logger.info(f"Generating SQL for table: {table_name}")
    try:
        result = converter.generate_sql(...)
        logger.info(f"SQL generated: {result['sql']}")
        return result
    except Exception as e:
        logger.error(f"SQL generation failed: {e}")
        return {"success": False, "error": str(e)}
```

## Performance Tuning

### Database Connection Pooling

For high concurrency, use `psycopg2-pool`:

```bash
pip install psycopg2-pool
```

```python
from psycopg2 import pool

connection_pool = pool.SimpleConnectionPool(
    1, 20,
    host=db_host,
    user=db_user,
    password=db_password,
    database=db_name
)

def _get_db_connection():
    return connection_pool.getconn()
```

### Caching Schema

Cache table schemas to avoid repeated queries:

```python
from functools import lru_cache
import time

schema_cache = {}
CACHE_TTL = 3600  # 1 hour

def _get_table_schema(table_name):
    if table_name in schema_cache:
        cached_at, schema = schema_cache[table_name]
        if time.time() - cached_at < CACHE_TTL:
            return schema
    
    # Fetch schema
    schema = ... # existing logic
    schema_cache[table_name] = (time.time(), schema)
    return schema
```

## Scaling

### Load Balancing

Multiple instances behind load balancer:

```
LB (nginx/HAProxy)
├─ Instance 1 (port 8000)
├─ Instance 2 (port 8001)
└─ Instance 3 (port 8002)
```

All instances share same database.

### Database Connection Sharing

If using HTTP mode, ensure connection pooling is enabled.

For MCP stdio mode, new connection per request is fine.

## Troubleshooting Deployment

### Server won't start
```bash
# Check Python version
python --version

# Check dependencies
pip list

# Check config
cat ~/.query-mcp/config.json

# Run with full traceback
python -u server.py 2>&1
```

### API key not working
```bash
# Verify env var
echo $QUERY_MCP_API_KEY

# Test directly
python -c "from zai import ZaiClient; ZaiClient(api_key='$QUERY_MCP_API_KEY')"
```

### Database connection fails
```bash
# Test PostgreSQL connection
psql -h $POSTGRES_HOST -U $POSTGRES_USER -d $POSTGRES_DB -c "SELECT 1;"

# Check config
cat ~/.query-mcp/config.json | grep database -A 5
```

### Slow responses
```bash
# Check database performance
psql -U postgres -c "EXPLAIN ANALYZE SELECT column_name FROM information_schema.columns LIMIT 10;"

# Consider caching schema
# Consider connection pooling
# Consider LLM model choice
```

## Rollback Plan

If deployment fails:

1. Stop current instance
2. Revert config file
3. Switch back to previous version
4. Restart with previous config
5. Test endpoints

```bash
# Restore previous version
git checkout HEAD~1 -- server.py text_to_sql.py

# Restore previous config
cp ~/.query-mcp/config.json.bak ~/.query-mcp/config.json

# Restart
systemctl restart query-mcp
```

## Next Steps

- [ ] Set up monitoring (Prometheus, DataDog, etc.)
- [ ] Add structured logging (ELK stack)
- [ ] Set up alerting (PagerDuty, Slack)
- [ ] Implement rate limiting
- [ ] Add request authentication/authorization
- [ ] Performance benchmarking
