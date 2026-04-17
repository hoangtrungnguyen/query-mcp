# Cloud Run Deployment Guide

Deploy Query MCP server to Google Cloud Run with Cloud SQL backend.

## Prerequisites

```bash
# Install gcloud CLI
# https://cloud.google.com/sdk/docs/install

# Authenticate
gcloud auth login
gcloud config set project YOUR_PROJECT_ID

# Enable required APIs
gcloud services enable run.googleapis.com
gcloud services enable sqladmin.googleapis.com
gcloud services enable cloudbuild.googleapis.com
gcloud services enable artifactregistry.googleapis.com
```

## Setup Cloud SQL Database

Create PostgreSQL 15 instance:

```bash
# Create Cloud SQL instance
gcloud sql instances create query-mcp-db \
  --database-version=POSTGRES_15 \
  --tier=db-f1-micro \
  --region=us-central1 \
  --root-password=YOUR_ROOT_PASSWORD

# Create database
gcloud sql databases create query_db \
  --instance=query-mcp-db

# Create app user
gcloud sql users create app_user \
  --instance=query-mcp-db \
  --password=YOUR_APP_PASSWORD
```

Get connection string:
```bash
# Format: postgresql://app_user:PASSWORD@/query_db?host=/cloudsql/PROJECT:REGION:INSTANCE
gcloud sql instances describe query-mcp-db --format='value(connectionName)'
```

## Build & Push Image

### Option 1: Cloud Build (Recommended)

```bash
# Build and push to Artifact Registry
gcloud builds submit \
  --tag us-central1-docker.pkg.dev/YOUR_PROJECT_ID/query-mcp/server:latest \
  --dockerfile=Dockerfile.cloudrun

# Or use gcloud run deploy (auto-builds)
gcloud run deploy query-mcp \
  --source=. \
  --dockerfile=Dockerfile.cloudrun \
  --region=us-central1 \
  --platform=managed
```

### Option 2: Local Build & Push

```bash
# Authenticate Docker
gcloud auth configure-docker us-central1-docker.pkg.dev

# Build
docker build -f Dockerfile.cloudrun -t \
  us-central1-docker.pkg.dev/YOUR_PROJECT_ID/query-mcp/server:latest .

# Push
docker push us-central1-docker.pkg.dev/YOUR_PROJECT_ID/query-mcp/server:latest
```

## Deploy to Cloud Run

```bash
gcloud run deploy query-mcp \
  --image=us-central1-docker.pkg.dev/YOUR_PROJECT_ID/query-mcp/server:latest \
  --region=us-central1 \
  --platform=managed \
  --memory=512Mi \
  --cpu=1 \
  --timeout=3600 \
  --set-env-vars=DATABASE_HOST=cloudsql/PROJECT:REGION:INSTANCE \
  --set-env-vars=DATABASE_USER=app_user \
  --set-env-vars=DATABASE_NAME=query_db \
  --add-cloudsql-instances=PROJECT:REGION:query-mcp-db \
  --service-account=query-mcp-sa@YOUR_PROJECT_ID.iam.gserviceaccount.com
```

## Setup Service Account & Secrets

Create service account:
```bash
gcloud iam service-accounts create query-mcp-sa \
  --display-name="Query MCP Service Account"

# Grant Cloud SQL Client role
gcloud projects add-iam-policy-binding YOUR_PROJECT_ID \
  --member=serviceAccount:query-mcp-sa@YOUR_PROJECT_ID.iam.gserviceaccount.com \
  --role=roles/cloudsql.client
```

Store database password in Secret Manager:
```bash
echo -n "YOUR_APP_PASSWORD" | gcloud secrets create db-password --data-file=-

# Grant access to service account
gcloud secrets add-iam-policy-binding db-password \
  --member=serviceAccount:query-mcp-sa@YOUR_PROJECT_ID.iam.gserviceaccount.com \
  --role=roles/secretmanager.secretAccessor
```

Update deployment to use secret:
```bash
gcloud run deploy query-mcp \
  --image=us-central1-docker.pkg.dev/YOUR_PROJECT_ID/query-mcp/server:latest \
  --update-secrets DATABASE_PASSWORD=db-password:latest \
  ...
```

## Run Database Migrations

Migrations must run before deploying new versions with schema changes.

### Option 1: Cloud SQL Proxy (One-time)

```bash
# Install Cloud SQL Proxy
# https://cloud.google.com/sql/docs/postgres/sql-proxy

# Run proxy
cloud-sql-proxy PROJECT:REGION:query-mcp-db &

# Run migrations locally
export DATABASE_HOST=localhost
export DATABASE_USER=app_user
export DATABASE_PASSWORD=YOUR_APP_PASSWORD
export DATABASE_NAME=query_db

cd /path/to/query-mcp
alembic upgrade head
```

### Option 2: Cloud Build Step

Create `cloudbuild.yaml`:
```yaml
steps:
  - name: 'gcr.io/cloud-builders/gke-deploy'
    args:
      - run
      - --filename=.
      - --image=query-mcp:$COMMIT_SHA
      - --location=us-central1
      - --cluster=query-mcp-cluster

  - name: 'gcr.io/cloud-builders/kubectl'
    args:
      - run
      - -i
      - migration
      - --image=query-mcp:$COMMIT_SHA
      - --restart=Never
      - -- alembic upgrade head
    env:
      - 'CLOUDSDK_COMPUTE_REGION=us-central1'
      - 'CLOUDSDK_CONTAINER_CLUSTER=query-mcp-cluster'
```

## Environment Variables for Cloud Run

```bash
PORT=8080                                    # Cloud Run default
DATABASE_HOST=cloudsql/PROJECT:REGION:INSTANCE  # Cloud SQL Unix socket
DATABASE_PORT=5432
DATABASE_USER=app_user
DATABASE_PASSWORD=<from Secret Manager>
DATABASE_NAME=query_db
PYTHONUNBUFFERED=1
PYTHONDONTWRITEBYTECODE=1
```

## Monitoring & Logs

View Cloud Run logs:
```bash
gcloud run logs read query-mcp --limit 50 --region us-central1 --follow
```

View Cloud SQL logs:
```bash
gcloud sql operations list --instance=query-mcp-db --limit 10
```

## Cleanup

```bash
# Delete Cloud Run service
gcloud run services delete query-mcp --region us-central1

# Delete Cloud SQL instance
gcloud sql instances delete query-mcp-db

# Delete container image
gcloud container images delete \
  us-central1-docker.pkg.dev/YOUR_PROJECT_ID/query-mcp/server:latest

# Delete service account
gcloud iam service-accounts delete query-mcp-sa@YOUR_PROJECT_ID.iam.gserviceaccount.com
```

## Performance Tuning

### Memory & CPU
```bash
gcloud run deploy query-mcp \
  --memory=512Mi \      # 128Mi to 8Gi
  --cpu=1               # 1 to 4
  ...
```

### Concurrency
```bash
gcloud run deploy query-mcp \
  --concurrency=10      # Default 80
  ...
```

### Min Instances (keep warm)
```bash
gcloud run deploy query-mcp \
  --min-instances=1     # Prevents cold starts
  ...
```

## Troubleshooting

**"Cloud SQL connection failed"**
- Verify Cloud SQL Proxy connection string
- Check service account has `cloudsql.client` role
- Verify `--add-cloudsql-instances` is set correctly

**"No module named 'src'"**
- Ensure working directory in Dockerfile is /app
- Check COPY commands include all necessary files

**"Connection pool exhausted"**
- Increase `--memory` and `--cpu`
- Reduce `--concurrency`
- Check for connection leaks in code

**Database migrations pending**
- Migrations must run before deploy
- Check `alembic current` to see applied versions

## Cost Estimation

- Cloud SQL db-f1-micro: ~$15/month
- Cloud Run: ~$0.00002500 per request + $0.0000100 per GB-second
- Typical 100 req/day: < $1/month compute
- Total: ~$15-20/month base

## File Structure

```
.
├── Dockerfile.cloudrun      # Cloud Run optimized build
├── CLOUD_RUN_DEPLOYMENT.md  # This file
├── src/
│   ├── server.py
│   ├── db_service.py
│   └── ...
├── alembic/                 # Migrations
├── alembic.ini
└── requirements.txt
```
