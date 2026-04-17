# GCP Deployment: query-mcp to Cloud Run

Deploy the query-mcp Text-to-SQL service to Google Cloud Run with Cloud SQL.

## Prerequisites

- Google Cloud project with Cloud Run and Cloud SQL enabled
- `gcloud` CLI installed and authenticated
- Docker installed locally
- Artifact Registry configured in the same GCP project
- Existing Cloud SQL instance (or create a new one)
- Database and tables already created in Cloud SQL

## Architecture

```
┌─────────────────────────────────────────┐
│         Google Cloud Run                 │
│  ┌──────────────────────────────────┐  │
│  │   query-mcp Service              │  │
│  │  - Port: 8080                    │  │
│  │  - Memory: 512Mi                 │  │
│  │  - Entrypoint: entrypoint.sh     │  │
│  └──────────────────────────────────┘  │
│           ↓ (Unix socket)               │
│  ┌──────────────────────────────────┐  │
│  │   Cloud SQL Proxy                │  │
│  │   /cloudsql/PROJECT:REGION:NAME  │  │
│  └──────────────────────────────────┘  │
└─────────────────────────────────────────┘
           ↓
   ┌───────────────────┐
   │   Cloud SQL       │
   │  (PostgreSQL)     │
   └───────────────────┘
```

## Configuration

query-mcp reads configuration from `~/.query-mcp/config.json`, which is created by the entrypoint script from environment variables:

| Env Var | Config Path | Purpose |
|---------|-------------|---------|
| `DATABASE_HOST` | `database.host` | Cloud SQL socket path (e.g., `/cloudsql/project:region:instance`) |
| `DATABASE_PORT` | `database.port` | Database port (default: 5432) |
| `DATABASE_NAME` | `database.name` | Database name (default: postgres) |
| `DATABASE_USER` | `database.user` | Database user (default: postgres) |
| `DATABASE_PASSWORD` | `database.password` | Database password |
| `QUERY_MCP_API_KEY` | `text_to_sql.llm_api_key` | LLM API key for text-to-SQL |
| `LLM_PROVIDER` | `text_to_sql.llm_provider` | LLM provider: `zai` or `anthropic` (default: zai) |
| `LLM_MODEL` | `text_to_sql.llm_model` | LLM model name (default: glm-4-flash) |

## Deployment Steps

### Step 1: Build Docker Image Locally

```bash
cd /home/htnguyen/Space/query-mcp
docker build -t asia-southeast1-docker.pkg.dev/PROJECT_ID/REPO/query-mcp:latest .
```

Replace:
- `PROJECT_ID` with your GCP project ID (e.g., `takumi-493116`)
- `REPO` with your Artifact Registry repo name (e.g., `med-tech-repo`)

### Step 2: Push to Artifact Registry

Ensure you're authenticated to Artifact Registry:
```bash
gcloud auth configure-docker asia-southeast1-docker.pkg.dev
```

Push the image:
```bash
docker push asia-southeast1-docker.pkg.dev/PROJECT_ID/REPO/query-mcp:latest
```

### Step 3: Deploy to Cloud Run

```bash
gcloud run deploy query-mcp \
  --image asia-southeast1-docker.pkg.dev/PROJECT_ID/REPO/query-mcp:latest \
  --region REGION \
  --project PROJECT_ID \
  --platform managed \
  --port 8080 \
  --memory 512Mi \
  --allow-unauthenticated \
  --add-cloudsql-instances PROJECT_ID:REGION:INSTANCE_NAME \
  --set-env-vars "\
    DATABASE_HOST=/cloudsql/PROJECT_ID:REGION:INSTANCE_NAME,\
    DATABASE_PORT=5432,\
    DATABASE_NAME=DATABASE_NAME,\
    DATABASE_USER=DATABASE_USER,\
    DATABASE_PASSWORD=DATABASE_PASSWORD,\
    QUERY_MCP_API_KEY=YOUR_LLM_API_KEY,\
    LLM_PROVIDER=zai,\
    LLM_MODEL=glm-4-flash"
```

Replace:
- `PROJECT_ID` — GCP project ID
- `REGION` — GCP region (e.g., `asia-southeast1`)
- `INSTANCE_NAME` — Cloud SQL instance name
- `DATABASE_NAME` — Database name (e.g., `testdb`)
- `DATABASE_USER` — Database user (e.g., `postgres`)
- `DATABASE_PASSWORD` — Database password
- `YOUR_LLM_API_KEY` — LLM API key for text-to-SQL

**Example (full command):**
```bash
gcloud run deploy query-mcp \
  --image asia-southeast1-docker.pkg.dev/takumi-493116/med-tech-repo/query-mcp:latest \
  --region asia-southeast1 \
  --project takumi-493116 \
  --platform managed \
  --port 8080 \
  --memory 512Mi \
  --allow-unauthenticated \
  --add-cloudsql-instances takumi-493116:asia-southeast1:takumi-med-tech \
  --set-env-vars "DATABASE_HOST=/cloudsql/takumi-493116:asia-southeast1:takumi-med-tech,DATABASE_PORT=5432,DATABASE_NAME=testdb,DATABASE_USER=postgres,DATABASE_PASSWORD=CJD*@FAp/t_1MsbQ,QUERY_MCP_API_KEY=d0662f7ffca1436ca9925c940fedd661.mJYqCfIg6KhS4OsG,LLM_PROVIDER=zai,LLM_MODEL=glm-4-flash"
```

### Step 4: Verify Deployment

After deployment completes, test the service:

```bash
SERVICE_URL="https://query-mcp-HASH.REGION.run.app"

# Check health endpoints
curl "$SERVICE_URL/health"      # → {"status": "ok"}
curl "$SERVICE_URL/api/health"  # → {"status": "ok"}

# Test text-to-SQL endpoint (requires database)
curl -X POST "$SERVICE_URL/api/text-to-sql/generate" \
  -H "Content-Type: application/json" \
  -d '{
    "message": "count all records",
    "table_name": "medicine_bid",
    "limit": 10
  }'
```

## Entrypoint Behavior

The `entrypoint-cloudrun.sh` script handles:

1. **Config generation** — Creates `~/.query-mcp/config.json` from env vars
2. **Database connectivity check** — Retries connection with exponential backoff (2s, 4s)
3. **Alembic migration detection** — Checks if `alembic_version` table exists and is tracked
4. **Smart migration strategy:**
   - If `alembic_version` is tracked → run `alembic upgrade head`
   - If tables exist but not tracked → run `alembic stamp head` (avoids re-creating)
   - If DB connection fails → continue anyway (migrations optional for runtime)
5. **Server startup** — Executes `python -u src/server.py http ${PORT:-8080}`

This design allows deployment even if:
- Cloud SQL connection is temporarily slow (retries with backoff)
- Alembic state is unknown (auto-detects and stamps or upgrades)
- Migration fails (service still starts)

## Troubleshooting

### Container fails to start ("Health check timeout")

Check Cloud Run logs:
```bash
gcloud logging read "resource.type=cloud_run_revision AND resource.labels.service_name=query-mcp" \
  --limit 50 \
  --project PROJECT_ID
```

Common causes:
- Database connection timeout — ensure Cloud SQL instance is running and accessible
- Invalid credentials — double-check `DATABASE_USER` and `DATABASE_PASSWORD`
- Port mismatch — ensure `--port 8080` matches server binding
- Slow migrations — Alembic can take 30+ seconds; increase `--timeout` if needed

### Database connection refused

Ensure:
1. Cloud SQL instance exists and is running:
   ```bash
   gcloud sql instances describe INSTANCE_NAME --project PROJECT_ID
   ```
2. Database and user exist:
   ```bash
   gcloud sql connect INSTANCE_NAME --user=postgres --project PROJECT_ID
   # Then: \l (list databases), \du (list users)
   ```
3. Cloud Run service account has Cloud SQL permission:
   ```bash
   gcloud projects get-iam-policy PROJECT_ID \
     --flatten="bindings[].members" \
     --filter="bindings.members:serviceAccount=*compute*"
   ```

### Service URL not accessible

Check service is public:
```bash
gcloud run services describe query-mcp --region REGION --project PROJECT_ID
# Look for: Ingress: All
# And: Public
```

Make public if needed:
```bash
gcloud run services update query-mcp \
  --allow-unauthenticated \
  --region REGION \
  --project PROJECT_ID
```

## Environment Variables Reference

Full list of env vars and their defaults:

```bash
DATABASE_HOST=/cloudsql/PROJECT_ID:REGION:INSTANCE_NAME  # Required: Cloud SQL socket path
DATABASE_PORT=5432                                         # Optional: DB port
DATABASE_NAME=postgres                                     # Optional: DB name
DATABASE_USER=postgres                                     # Optional: DB user
DATABASE_PASSWORD=postgres                                 # Optional: DB password
QUERY_MCP_API_KEY=                                         # Optional: LLM API key
LLM_PROVIDER=zai                                           # Optional: zai or anthropic
LLM_MODEL=glm-4-flash                                      # Optional: model name
PORT=8080                                                  # Optional: server port (Cloud Run sets this)
```

## Related Documentation

- [Architecture](./ARCHITECTURE.md) — System design and components
- [API Endpoints](./API_ENDPOINTS.md) — Available HTTP endpoints
- [Database Design](./DATABASE_DESIGN.md) — Schema and migrations
- [Docker Setup](./DOCKER_SETUP.md) — Local Docker development

## See Also

- [GCP Cloud Run Docs](https://cloud.google.com/run/docs)
- [Cloud SQL Proxy](https://cloud.google.com/sql/docs/postgres/cloud-sql-proxy)
- [Alembic Migrations](https://alembic.sqlalchemy.org/)
