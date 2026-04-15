# Query MCP Docker Setup Guide

Complete guide for running Query MCP in **local development** with Docker.

## Architecture Note

- **Local Dev** (this guide): `query-mcp/docker-compose.yml` runs Query MCP only (assumes local postgres)
- **Production Deploy**: Query MCP connects to postgres managed in `/home/htnguyen/Space/med-tech-workload/docker-compose.yml`
  - postgres service defined separately, not in query-mcp
  - Query MCP configured via `~/.query-mcp/config.json` to point to that postgres instance

## Quick Start (2 minutes)

Requires: PostgreSQL running elsewhere (localhost:5432, external host, or med-tech-workload deployment).

```bash
cd /home/htnguyen/Space/query-mcp

# Set API key
export QUERY_MCP_API_KEY="your-zai-api-key"

# Configure database (edit ~/.query-mcp/config.json to point to postgres instance)
# Defaults: localhost:5432, user=postgres, password=postgres

# Start Query MCP
docker-compose up -d

# Verify service running
docker ps
docker-compose logs
```

Access:
- **Query MCP:** Running, ready for MCP clients (no direct HTTP port exposed by default)

---

## Components

### Dockerfile (Query MCP Server)

Builds Query MCP server with all dependencies.

```dockerfile
FROM python:3.11-slim
# Install postgres-client
# Install Python dependencies from requirements.txt
# Copy application files
# Run server.py
```

**Image size:** ~300MB

### docker-compose.yml (Orchestration)

Defines single service:
- **query-mcp** - Query MCP server

**Note:** PostgreSQL is **not** included. Configure database connection in `~/.query-mcp/config.json` pointing to your postgres instance (local, external, or med-tech-workload deployment).

---

## Setup Instructions

### Prerequisites

- Docker Desktop installed and running
- Z.ai or Anthropic API key
- PostgreSQL instance running (local, external, or via med-tech-workload deployment)
- ~300MB disk space (Query MCP image only)

### Step 1: Navigate to Project

```bash
cd /home/htnguyen/Space/query-mcp
```

### Step 2: Set Environment Variable

```bash
# Z.ai
export QUERY_MCP_API_KEY="your-zai-key"

# OR Anthropic
export QUERY_MCP_API_KEY="sk-ant-your-anthropic-key"
```

**Verify it's set:**
```bash
echo $QUERY_MCP_API_KEY
```

### Step 3: Configure Database

Edit `~/.query-mcp/config.json` to point to your postgres instance:

```json
{
  "database": {
    "host": "postgres.example.com",
    "port": 5432,
    "name": "testdb",
    "user": "postgres",
    "password": "postgres"
  },
  ...
}
```

### Step 4: Build Image

First time only:
```bash
docker-compose build
```

This builds:
- `query-mcp:latest` - Query MCP server

### Step 5: Start Service

```bash
docker-compose up -d
```

**Output:**
```
[+] Running 1/1
 ✓ Container query-mcp-server   Started
```

### Step 6: Verify Service

```bash
# Check container running
docker ps

# Check logs
docker-compose logs -f
```

**Expected logs:**
```
query-mcp-server    | Query MCP Server starting...
query-mcp-server    | Config file: /root/.query-mcp/config.json
```

### Step 7: Test Database Connection

```bash
# Verify postgres is reachable from container
docker exec query-mcp-server psql -h postgres.example.com -U postgres -d testdb -c "SELECT 1;"

# Should return: 1 (success)
```

---

## Usage

### Test Query MCP with PostgreSQL

```bash
# Option 1: Use the running MCP server
# Query MCP is already listening for MCP connections

# Option 2: Connect directly to PostgreSQL
docker exec -it query-mcp-postgres psql -U postgres -d testdb

# Option 3: Use psql from your machine (if installed)
psql -h localhost -U postgres -d testdb
```

### Example Queries

Using `psql`:

```sql
-- List all active drugs
SELECT * FROM drugs WHERE status = 'active' LIMIT 5;

-- Count drugs by category
SELECT category, COUNT(*) as count FROM drugs GROUP BY category;

-- Find expensive items
SELECT name, price FROM items WHERE price > 50 ORDER BY price DESC;

-- Get user orders
SELECT u.name, COUNT(o.id) as order_count, SUM(o.total) as total_spent
FROM users u
LEFT JOIN orders o ON u.id = o.user_id
GROUP BY u.id, u.name;

-- View active drugs
SELECT * FROM active_drugs;

-- View drug statistics
SELECT * FROM drugs_by_category;
```

### Connect Query MCP to Claude

1. Query MCP server is running inside Docker
2. Add to Claude Code MCP servers:
   - **Command:** `docker`
   - **Args:** `exec -i query-mcp-server python server.py`
   - **Env:** Already set in compose file

---

## Management

### Stop Services

```bash
# Stop and keep containers
docker-compose stop

# Stop and remove containers
docker-compose down
```

### View Logs

```bash
# All services
docker-compose logs -f

# Specific service
docker-compose logs -f postgres
docker-compose logs -f query-mcp
```

### Restart Services

```bash
# Restart all
docker-compose restart

# Restart specific service
docker-compose restart postgres
docker-compose restart query-mcp
```

### Remove Everything

```bash
# Stop and remove containers, volumes, networks
docker-compose down -v

# Also remove images
docker rmi query-mcp query-mcp-postgres
```

### Access PostgreSQL Shell

```bash
# Interactive shell
docker exec -it query-mcp-postgres psql -U postgres

# Run SQL file
docker exec -it query-mcp-postgres psql -U postgres -f /path/to/file.sql

# Run single query
docker exec -it query-mcp-postgres psql -U postgres -c "SELECT COUNT(*) FROM drugs;"
```

---

## Configuration

### Environment Variables

Set these before running `docker-compose up`:

```bash
# Required
export QUERY_MCP_API_KEY="your-api-key"

# Optional (defaults below)
export POSTGRES_DB=testdb
export POSTGRES_USER=postgres
export POSTGRES_PASSWORD=postgres
export POSTGRES_PORT=5432
```

### Database Configuration

Edit `docker-compose.yml` environment section:

```yaml
services:
  postgres:
    environment:
      POSTGRES_DB: testdb
      POSTGRES_USER: postgres
      POSTGRES_PASSWORD: postgres
```

### Custom Database Initialization

Replace `init-db.sql` with your own schema:

```bash
# Backup original
cp init-db.sql init-db.sql.bak

# Create your own
cat > init-db.sql << 'EOF'
CREATE TABLE my_table (
  id SERIAL PRIMARY KEY,
  name VARCHAR(255)
);
INSERT INTO my_table (name) VALUES ('test');
EOF

# Restart with new data
docker-compose down -v
docker-compose up -d
```

### Change Ports

Current configuration: PostgreSQL on **5440**

Edit `docker-compose.yml` to change:

```yaml
services:
  postgres:
    ports:
      - "5441:5432"  # Change from 5440 to 5441
```

Then restart:
```bash
docker-compose down
docker-compose up -d
```

---

## Networking

### Database Connection

Query MCP connects to PostgreSQL via `~/.query-mcp/config.json` (not docker-compose env vars).

**Local postgres (host machine):**
```json
{
  "database": {
    "host": "host.docker.internal",  // or "localhost" depending on Docker setup
    "port": 5432
  }
}
```

**med-tech-workload deployment:**
```json
{
  "database": {
    "host": "postgres",  // service name in med-tech-workload compose network
    "port": 5432
  }
}
```

**External postgres:**
```json
{
  "database": {
    "host": "postgres.example.com",
    "port": 5432
  }
}
```

### Host-to-Container Communication

From your machine:

```bash
# Query MCP
# Accessible via MCP protocol (no direct HTTP port exposed by default)
# Can add HTTP ports in docker-compose.yml if needed
```

---

## Volumes

### Persistent Data

PostgreSQL data persists in `postgres_data` volume:

```bash
# List volumes
docker volume ls | grep query

# Inspect volume
docker volume inspect query-mcp_postgres_data

# Backup volume
docker run -v query-mcp_postgres_data:/data -v /tmp:/backup alpine tar czf /backup/postgres_backup.tar.gz /data

# Restore volume
docker run -v query-mcp_postgres_data:/data -v /tmp:/backup alpine tar xzf /backup/postgres_backup.tar.gz -C /
```

### Configuration Files

Local `~/.query-mcp/` directory mounted to container:

```bash
# Copy config to host
docker cp query-mcp-server:/root/.query-mcp/config.json ~/.query-mcp/

# Edit locally
vi ~/.query-mcp/config.json

# Changes reflected in container immediately
```

---

## Troubleshooting

### Services won't start

```bash
# Check if ports are already in use
lsof -i :5440    # PostgreSQL
lsof -i :8000    # Query MCP (if used)

# Kill process using port (Linux)
kill -9 <PID>

# Or change ports in docker-compose.yml
```

### PostgreSQL won't initialize

```bash
# Check logs
docker-compose logs postgres

# Rebuild without cache
docker-compose down -v
docker-compose build --no-cache
docker-compose up -d
```

### Query MCP can't connect to PostgreSQL

```bash
# Check PostgreSQL health
docker exec query-mcp-postgres pg_isready

# Check connectivity from Query MCP container
docker exec query-mcp-server psql -h postgres -U postgres -d testdb -c "SELECT 1;"

# Check network
docker network inspect query-mcp_query-mcp-network
```

### API key not working

```bash
# Verify env var in container
docker exec query-mcp-server env | grep QUERY_MCP_API_KEY

# Check logs
docker-compose logs query-mcp

# Re-set and restart
export QUERY_MCP_API_KEY="new-key"
docker-compose down
docker-compose up -d
```

### Permission denied errors

```bash
# Check file permissions
ls -la ~/.query-mcp/

# Fix permissions (Linux/Mac)
chmod 755 ~/.query-mcp/
chmod 644 ~/.query-mcp/config.json

# Docker on Windows: use WSL2
```

---

## Performance

### Resource Limits

Add to `docker-compose.yml`:

```yaml
services:
  postgres:
    deploy:
      resources:
        limits:
          cpus: '1'
          memory: 512M
        reservations:
          cpus: '0.5'
          memory: 256M
  
  query-mcp:
    deploy:
      resources:
        limits:
          cpus: '1'
          memory: 256M
        reservations:
          cpus: '0.5'
          memory: 128M
```

Then use `docker-compose` (newer versions):
```bash
docker-compose up -d
```

### Connection Pooling

PostgreSQL with persistent volumes:

```bash
# Persistent data across restarts
docker-compose up -d
# Data survives: docker-compose down
# Data lost: docker-compose down -v
```

---

## Backup & Restore

### Backup Database

```bash
# Dump schema and data
docker exec query-mcp-postgres pg_dump -U postgres -d testdb > backup.sql

# Backup with compression
docker exec query-mcp-postgres pg_dump -U postgres -d testdb | gzip > backup.sql.gz
```

### Restore Database

```bash
# Drop and recreate
docker exec -it query-mcp-postgres psql -U postgres -d testdb << 'EOF'
DROP SCHEMA public CASCADE;
CREATE SCHEMA public;
EOF

# Restore from dump
docker exec -i query-mcp-postgres psql -U postgres -d testdb < backup.sql

# Or from compressed
gunzip < backup.sql.gz | docker exec -i query-mcp-postgres psql -U postgres -d testdb
```

---

## Production Deployment

### Not Recommended For Production

Current setup is for **development/testing only**:
- ❌ No persistent volumes by default
- ❌ Sample data exposed
- ❌ No authentication
- ❌ No TLS/SSL
- ❌ No backup strategy
- ❌ No monitoring/logging

### For Production Use

See [DEPLOYMENT.md](DEPLOYMENT.md) for:
- Kubernetes deployment
- AWS/GCP/Azure setup
- SSL/TLS configuration
- Backup strategies
- Monitoring and logging
- High availability setup

---

## Docker Basics

### Common Commands

```bash
# View running containers
docker ps

# View all containers (including stopped)
docker ps -a

# View images
docker images

# View volumes
docker volume ls

# View networks
docker network ls

# Inspect container
docker inspect query-mcp-server

# Get container IP
docker inspect -f '{{range .NetworkSettings.Networks}}{{.IPAddress}}{{end}}' query-mcp-server
```

### File Operations

```bash
# Copy file from container to host
docker cp query-mcp-server:/app/server.py ./

# Copy file from host to container
docker cp ./config.json query-mcp-server:/root/.query-mcp/

# List files in container
docker exec query-mcp-server ls -la /root/.query-mcp/
```

### Execute Commands

```bash
# Run command in running container
docker exec query-mcp-server python --version

# Interactive shell
docker exec -it query-mcp-server bash

# Run with environment
docker exec -e MY_VAR=value query-mcp-server env | grep MY_VAR
```

---

## Next Steps

1. ✅ Start services: `docker-compose up -d`
2. ✅ Test database: `docker exec -it query-mcp-postgres psql ...`
3. ✅ Verify Query MCP: Check logs
4. ✅ Add to Claude Code: Configure MCP server
5. 📚 Deploy to production: See DEPLOYMENT.md

---

## Support

- Check Docker logs: `docker-compose logs -f`
- Check service health: `docker-compose ps`
- Restart services: `docker-compose restart`
- See [DEPLOYMENT.md](DEPLOYMENT.md) for advanced setup
- See [README.md](README.md) for Query MCP usage
