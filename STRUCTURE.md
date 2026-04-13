# Query MCP - Project Structure

Complete directory and file organization.

```
query-mcp/
├── README.md                 ← Start here!
├── QUICK_START.md            ← 5-minute setup
├── INDEX.md                  ← Documentation index
├── STRUCTURE.md              ← This file
├── requirements.txt          ← Python dependencies
│
├── docs/                     ← All documentation
│   ├── OVERVIEW.md           ← High-level summary
│   ├── ARCHITECTURE.md       ← System design
│   ├── API_REFERENCE.md      ← Complete API docs
│   ├── INTEGRATION.md        ← Claude integration guide
│   ├── EXAMPLES.md           ← SQL query examples
│   ├── DEPLOYMENT.md         ← Production deployment
│   ├── DOCKER_SETUP.md       ← Docker configuration
│   ├── SETUP.md              ← Detailed setup
│   ├── TROUBLESHOOTING.md    ← Common issues & fixes
│   ├── FAQ.md                ← Frequently asked questions
│   └── CHANGELOG.md          ← Version history
│
├── src/                      ← Source code
│   ├── server.py             ← MCP server (main entry point)
│   ├── text_to_sql.py        ← Core TextToSQL engine
│   ├── db_service.py         ← Database service layer (connections, queries, history)
│   └── migrate.py            ← SQL migration runner
│
├── migrations/               ← Versioned SQL migrations
│   ├── 001_initial_schema.sql  ← Base tables & indexes
│   ├── 002_seed_data.sql       ← Sample data
│   ├── 003_create_views.sql    ← Reporting views
│   └── 004_query_history.sql   ← Query tracking tables
│
├── docker/                   ← Docker configuration
│   ├── Dockerfile            ← Query MCP container image
│   ├── Dockerfile.postgres   ← PostgreSQL container image
│   ├── docker-compose.yml    ← Docker Compose orchestration
│   ├── init-db.sql           ← Sample database initialization
│   └── .dockerignore         ← Files to exclude from image
│
├── .env.example              ← Environment variable template
├── .env                      ← Local environment variables (gitignored)
└── .gitignore                ← Git ignore patterns
```

## Directory Details

### `/docs` - Documentation
All markdown documentation files organized by topic.

| File | Purpose | Read Time |
|------|---------|-----------|
| `OVERVIEW.md` | What is Query MCP? | 10 min |
| `ARCHITECTURE.md` | How does it work? | 20 min |
| `API_REFERENCE.md` | API endpoints and parameters | 15 min |
| `INTEGRATION.md` | How to use with Claude | 15 min |
| `EXAMPLES.md` | SQL query examples | 15 min |
| `DEPLOYMENT.md` | Production setup | 20 min |
| `DOCKER_SETUP.md` | Docker configuration | 15 min |
| `SETUP.md` | Detailed setup guide | 10 min |
| `TROUBLESHOOTING.md` | Common issues | 10 min |
| `FAQ.md` | Frequently asked questions | 10 min |
| `CHANGELOG.md` | Version history | 5 min |

### `/src` - Source Code
Python application code.

| File | Purpose | Lines |
|------|---------|-------|
| `server.py` | MCP server implementation | ~220 |
| `text_to_sql.py` | TextToSQL core engine (uses DatabaseService) | ~200 |
| `db_service.py` | Database service layer (connections, queries, history) | ~270 |
| `migrate.py` | SQL migration runner (tracks via `schema_migrations`) | ~120 |

### `/migrations` - SQL Migrations
Versioned database schema files, applied in order by `migrate.py`.

| File | Purpose |
|------|---------|
| `001_initial_schema.sql` | Base tables (`drugs`, `items`, `users`, `orders`) + indexes |
| `002_seed_data.sql` | Sample data (15 drugs, 10 items, 10 users, 10 orders) |
| `003_create_views.sql` | Views: `active_drugs`, `drugs_by_category`, `expensive_items` |
| `004_query_history.sql` | Query tracking: `query_sessions`, `query_history` tables |

### `/docker` - Docker Configuration
Container and orchestration files.

| File | Purpose |
|------|---------|
| `Dockerfile` | Query MCP container image |
| `Dockerfile.postgres` | PostgreSQL 15 container image |
| `docker-compose.yml` | Orchestration (both services) |
| `init-db.sql` | Sample database (15 drugs, 10 items, etc.) |
| `.dockerignore` | Excludes files from Docker image |

### Root Level
Project configuration and entry points.

| File | Purpose |
|------|---------|
| `README.md` | Quick start and features overview |
| `QUICK_START.md` | 5-minute setup guide |
| `INDEX.md` | Documentation navigation index |
| `STRUCTURE.md` | This file (directory layout) |
| `requirements.txt` | Python package dependencies |
| `.env.example` | Environment variable template |
| `.env` | Local environment (gitignored) |
| `.gitignore` | Git ignore patterns |

## File Relationships

### Running Query MCP Locally

```
requirements.txt
    ↓
pip install -r requirements.txt
    ↓
python src/migrate.py          ← apply migrations
    ↓
src/server.py
  → text_to_sql.py → db_service.py → PostgreSQL
    ↓
Query MCP Server Running
```

### Running with Docker

```
docker/Dockerfile + docker/Dockerfile.postgres
    ↓
docker build
    ↓
docker/docker-compose.yml
    ↓
docker-compose up -d
    ↓
PostgreSQL (5440) + Query MCP (MCP protocol)
```

### Documentation Navigation

```
README.md (start)
    ↓
├─→ QUICK_START.md (5 min setup)
├─→ docs/OVERVIEW.md (what is it?)
├─→ docs/ARCHITECTURE.md (how works?)
├─→ docs/API_REFERENCE.md (API docs)
├─→ docs/INTEGRATION.md (Claude setup)
├─→ docs/EXAMPLES.md (SQL examples)
├─→ docs/DOCKER_SETUP.md (Docker)
├─→ docs/DEPLOYMENT.md (production)
├─→ docs/TROUBLESHOOTING.md (issues)
├─→ docs/FAQ.md (questions)
└─→ INDEX.md (all docs)
```

## Development Workflow

### 1. Setup Phase
```
requirements.txt
    ↓
python3 -m venv venv
    ↓
pip install -r requirements.txt
    ↓
.env (set QUERY_MCP_API_KEY)
```

### 2. Development Phase
```
src/server.py
    ↓
python src/server.py
    ↓
Test with Claude
```

### 3. Docker Phase
```
docker/Dockerfile + docker/Dockerfile.postgres
    ↓
docker/docker-compose.yml
    ↓
docker-compose -f docker/docker-compose.yml up -d
    ↓
PostgreSQL + Query MCP Running
```

### 4. Deployment Phase
```
docs/DEPLOYMENT.md
    ↓
Choose deployment option
    ↓
├─→ Kubernetes
├─→ Cloud Functions
├─→ Systemd Service
└─→ Container Registry
```

## Import Paths

### For MCP Integration (Claude)
```python
# From: src/server.py
from text_to_sql import TextToSQL
from db_service import DatabaseService
```

### For Docker
```dockerfile
COPY src/server.py /app/
COPY src/text_to_sql.py /app/
COPY src/db_service.py /app/
COPY src/migrate.py /app/
COPY migrations/ /app/migrations/
CMD ["python", "/app/server.py"]
```

## Configuration Files

### Required
- `requirements.txt` — Python dependencies

### Optional
- `.env` — Local environment variables
- `.env.example` — Template (check this first)
- `.gitignore` — What to exclude from git

## Documentation Map

### For Users
1. Start: `README.md`
2. Quick: `QUICK_START.md`
3. Learn: `docs/OVERVIEW.md`
4. Do: `docs/INTEGRATION.md`

### For Developers
1. Architecture: `docs/ARCHITECTURE.md`
2. API: `docs/API_REFERENCE.md`
3. Deploy: `docs/DEPLOYMENT.md`
4. Debug: `docs/TROUBLESHOOTING.md`

### For DevOps
1. Docker: `docs/DOCKER_SETUP.md`
2. Deploy: `docs/DEPLOYMENT.md`
3. Scale: `docs/ARCHITECTURE.md` (scaling section)

## Updating Documentation

When adding docs:
1. Save to `docs/` directory
2. Update `INDEX.md` with link
3. Format: markdown (.md)
4. Add to navigation in `README.md`

## Updating Source Code

When modifying code:
1. Edit files in `src/`
2. Test locally: `python src/server.py`
3. Test with Docker: `docker-compose -f docker/docker-compose.yml up`
4. Update docs if behavior changes

## Building & Running

### Local
```bash
pip install -r requirements.txt
python src/server.py
```

### Docker
```bash
cd docker
docker-compose up -d
```

### Custom
```bash
# Install specific Python version
python3.11 -m venv venv
source venv/bin/activate
pip install -r requirements.txt

# Run with args
PYTHONUNBUFFERED=1 python -u src/server.py
```

## Size Summary

| Directory | Files | Size |
|-----------|-------|------|
| docs/ | 11 | ~100KB |
| src/ | 4 | ~25KB |
| migrations/ | 4 | ~5KB |
| docker/ | 4 | ~6KB |
| Root | 8 | ~20KB |
| **Total** | **31** | **~156KB** |

## Quick References

### Read Documentation
```bash
cd docs/
ls -1                    # List all docs
cat OVERVIEW.md         # Start here
```

### Run Code
```bash
python src/server.py    # Local
cd docker && docker-compose up -d  # Docker
```

### Update Dependencies
```bash
pip install -r requirements.txt
pip list
```

### Check Structure
```bash
tree -L 2               # Show tree (if installed)
find . -type f -name "*.md" | head  # List docs
ls -R                   # Full listing
```

## Next Steps

1. Read `README.md`
2. Follow `QUICK_START.md`
3. Check `docs/OVERVIEW.md`
4. Choose integration method from `docs/INTEGRATION.md`

---

Last updated: 2026-04-13
