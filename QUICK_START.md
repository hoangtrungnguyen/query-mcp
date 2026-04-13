# Query MCP - Quick Start Guide

Get up and running in 5 minutes.

## Prerequisites

- Docker & Docker Compose installed
- Z.ai API key (or Anthropic)

## 1. Set API Key

```bash
export QUERY_MCP_API_KEY="d0662f7ffca1436ca9925c940fedd661.mJYqCfIg6KhS4OsG"
```

## 2. Start Services

```bash
cd /home/htnguyen/Space/query-mcp
docker-compose up -d
```

## 3. Verify Running

```bash
docker-compose ps
```

Expected output:
```
NAME                     STATUS
query-mcp-postgres       running (healthy)
query-mcp-server         running
```

## 4. Test Database

```bash
docker exec -it query-mcp-postgres psql -U postgres -d testdb -c "SELECT COUNT(*) FROM drugs;"
```

Expected output:
```
 count 
-------
    15
(1 row)
```

---

## Access Points

| Service | Address | Port | Use |
|---------|---------|------|-----|
| PostgreSQL | localhost | 5440 | Query database |
| Query MCP | (internal) | - | MCP protocol |

---

## Common Commands

### Query Database

```bash
# Interactive shell
docker exec -it query-mcp-postgres psql -U postgres -d testdb

# Run query
docker exec -it query-mcp-postgres psql -U postgres -d testdb -c "SELECT * FROM drugs LIMIT 5;"
```

### View Logs

```bash
# All services
docker-compose logs -f

# Specific service
docker-compose logs -f postgres
docker-compose logs -f query-mcp
```

### Stop Services

```bash
docker-compose down
```

### Restart Services

```bash
docker-compose restart
```

---

## Add to Claude Code

1. Settings → MCP Servers
2. Add new:
   - **Name:** Query MCP
   - **Command:** `docker`
   - **Args:** `exec -i query-mcp-server python server.py`
3. Click Connect

## Use in Claude

Ask Claude:
- "Query the drugs table and show me the top 10 most expensive items"
- "Count how many drugs are in each category"
- "Find all active items ordered by price"

---

## Sample Queries

```sql
-- List all drugs
SELECT * FROM drugs;

-- Find expensive drugs
SELECT name, price FROM drugs WHERE price > 20 ORDER BY price DESC;

-- Count by category
SELECT category, COUNT(*) FROM drugs GROUP BY category;

-- View
SELECT * FROM active_drugs;

-- Orders with totals
SELECT u.name, COUNT(o.id), SUM(o.total) FROM users u LEFT JOIN orders o ON u.id = o.user_id GROUP BY u.name;
```

---

## Troubleshooting

**Services won't start:**
```bash
# Check logs
docker-compose logs

# Rebuild
docker-compose down -v
docker-compose build --no-cache
docker-compose up -d
```

**Can't connect to PostgreSQL:**
```bash
# Verify it's running
docker-compose ps

# Check port
lsof -i :5440
```

**API key not working:**
```bash
# Verify env var
echo $QUERY_MCP_API_KEY

# Restart services
docker-compose restart
```

---

## Next Steps

- Read [README.md](README.md) for full features
- Read [DOCKER_SETUP.md](DOCKER_SETUP.md) for advanced Docker setup
- See [API_REFERENCE.md](API_REFERENCE.md) for all endpoints
- See [ARCHITECTURE.md](ARCHITECTURE.md) for system design

---

## Configuration

Current setup:
- **PostgreSQL:** `localhost:5440`
- **Database:** `testdb`
- **User:** `postgres`
- **Password:** `postgres`
- **LLM Provider:** Z.ai (default)
- **LLM Model:** GLM-5.1

To change: Edit `docker-compose.yml` and rebuild.

---

That's it! You're ready to use Query MCP with PostgreSQL.
