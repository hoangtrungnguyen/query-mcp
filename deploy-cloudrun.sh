#!/bin/bash
set -e

# Cloud Run deployment script for Query MCP
# Usage: ./deploy-cloudrun.sh [PROJECT_ID] [REGION]

PROJECT_ID=${1:-}
REGION=${2:-us-central1}
SERVICE_NAME="query-mcp"
ARTIFACT_REGION="us-central1"

if [ -z "$PROJECT_ID" ]; then
    echo "Usage: ./deploy-cloudrun.sh PROJECT_ID [REGION]"
    echo "Example: ./deploy-cloudrun.sh my-project us-central1"
    exit 1
fi

echo "🚀 Deploying Query MCP to Cloud Run"
echo "  Project: $PROJECT_ID"
echo "  Region: $REGION"
echo "  Service: $SERVICE_NAME"
echo ""

# Set gcloud project
gcloud config set project $PROJECT_ID

# Build and push image
echo "📦 Building and pushing Docker image..."
IMAGE_URL="$ARTIFACT_REGION-docker.pkg.dev/$PROJECT_ID/$SERVICE_NAME/server:latest"

gcloud builds submit \
  --tag $IMAGE_URL \
  --dockerfile=Dockerfile.cloudrun \
  --quiet

echo "✅ Image pushed to Artifact Registry"
echo ""

# Deploy to Cloud Run
echo "🌐 Deploying to Cloud Run..."

# Get existing Cloud SQL instance (if any)
DB_INSTANCE=$(gcloud sql instances list --filter="name:query-mcp-db" --format="value(name)" || true)

if [ -z "$DB_INSTANCE" ]; then
    echo "⚠️  Warning: No Cloud SQL instance found named 'query-mcp-db'"
    echo "   Create one with:"
    echo "   gcloud sql instances create query-mcp-db --database-version=POSTGRES_15 --tier=db-f1-micro --region=$REGION"
    echo ""
    CLOUDSQL_INSTANCE=""
else
    CLOUDSQL_INSTANCE="$PROJECT_ID:$REGION:$DB_INSTANCE"
    echo "✅ Found Cloud SQL instance: $CLOUDSQL_INSTANCE"
fi

# Get service account
SA_NAME="query-mcp-sa"
SA_EMAIL="$SA_NAME@$PROJECT_ID.iam.gserviceaccount.com"

if ! gcloud iam service-accounts describe $SA_EMAIL &>/dev/null; then
    echo "📋 Creating service account..."
    gcloud iam service-accounts create $SA_NAME \
      --display-name="Query MCP Service Account"

    # Grant Cloud SQL Client role
    gcloud projects add-iam-policy-binding $PROJECT_ID \
      --member=serviceAccount:$SA_EMAIL \
      --role=roles/cloudsql.client \
      --quiet
else
    echo "✅ Service account exists: $SA_EMAIL"
fi

# Deploy
echo "📤 Deploying service..."

DEPLOY_CMD="gcloud run deploy $SERVICE_NAME \
  --image=$IMAGE_URL \
  --region=$REGION \
  --platform=managed \
  --allow-unauthenticated \
  --memory=512Mi \
  --cpu=1 \
  --timeout=3600 \
  --service-account=$SA_EMAIL \
  --set-env-vars=PYTHONUNBUFFERED=1,PYTHONDONTWRITEBYTECODE=1"

if [ -n "$CLOUDSQL_INSTANCE" ]; then
    DEPLOY_CMD="$DEPLOY_CMD --add-cloudsql-instances=$CLOUDSQL_INSTANCE"
fi

eval $DEPLOY_CMD

echo ""
echo "✅ Deployment complete!"
echo ""

# Get service URL
SERVICE_URL=$(gcloud run services describe $SERVICE_NAME \
  --region=$REGION \
  --format='value(status.url)')

echo "🎉 Service URL: $SERVICE_URL"
echo ""
echo "Next steps:"
echo "  1. Test the service: curl $SERVICE_URL/api/health"
echo "  2. View logs: gcloud run logs read $SERVICE_NAME --region=$REGION --follow"
echo "  3. Configure database connection in Cloud Run environment"
echo ""
