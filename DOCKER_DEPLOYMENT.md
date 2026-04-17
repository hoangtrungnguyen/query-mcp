# Docker Deployment Guide

Query MCP server with PostgreSQL database, Alembic migrations, and health checks.

## Quick Start

```bash
# Build and run with docker-compose
docker-compose -f docker/docker-compose.yml up --build

# Server runs on http://localhost:8000
# Database on localhost:5432
```

## Architecture

- **Base Image**: Python 3.11-slim
- **Database**: PostgreSQL 15-alpine (persistent volume)
- **Port**: 8000 (API), 5432 (DB)
- **Network**: query-mcp-network (bridge)

## Services

### postgres
- PostgreSQL 15 database
- Volume: `postgres_data` (persists across restarts)
- Healthcheck: pg_isready every 10s
- Credentials: postgres/postgres

### query-mcp
- FastMCP server with Text-to-SQL tools
- Runs Alembic migrations automatically on startup
- Depends on postgres service
- Auto-restart on failure

## Environment Variables

All configurable via docker-compose.yml or `.env`:

```bash
DATABASE_HOST=postgres
DATABASE_PORT=5432
DATABASE_USER=postgres
DATABASE_PASSWORD=postgres
DATABASE_NAME=query_db
PYTHONUNBUFFERED=1
```

## Building Separately

```bash
# Build image only
docker build -f docker/Dockerfile -t query-mcp:latest .

# Run with custom database
docker run -p 8000:8000 \
  -e DATABASE_HOST=my-db.example.com \
  -e DATABASE_USER=dbuser \
  -e DATABASE_PASSWORD=dbpass \
  query-mcp:latest
```

## Debugging

```bash
# View logs
docker-compose -f docker/docker-compose.yml logs -f query-mcp

# Check database connection
docker exec query-mcp-postgres psql -U postgres -d query_db -c "SELECT version();"

# Shell into container
docker exec -it query-mcp-server bash

# Test healthcheck manually
docker exec query-mcp-server pg_isready -h postgres -U postgres
```

## Migration Management

Alembic migrations run automatically at startup via `entrypoint.sh`:

```bash
# Check migration status
docker exec query-mcp-server alembic current
docker exec query-mcp-server alembic history

# Create new migration (manual)
docker exec query-mcp-server alembic revision --autogenerate -m "description"
```

## Production Deployment

For production, create `.env.prod`:

```bash
DATABASE_HOST=prod-db.example.com
DATABASE_USER=prod_user
DATABASE_PASSWORD=<secure_password>
DATABASE_NAME=query_prod
```

Run with env file:
```bash
docker-compose -f docker/docker-compose.yml --env-file .env.prod up -d
```

## Cleanup

```bash
# Remove all containers and volumes
docker-compose -f docker/docker-compose.yml down -v

# Remove images
docker rmi query-mcp:latest postgres:15-alpine
```

## File Structure

```
docker/
├── Dockerfile           # Container build config
├── entrypoint.sh       # Startup script (migrations + server)
├── docker-compose.yml  # Multi-container orchestration
├── .dockerignore       # Build context exclusions
└── init-db.sql         # Optional DB initialization
```
