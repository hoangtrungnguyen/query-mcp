# Query MCP Deployment Logs

This directory contains deployment logs and operational records for the query-mcp Cloud Run service.

## Log Files

### DEPLOYMENT_LOG_2026-04-17.md
**Date:** April 17, 2026  
**Status:** ✅ COMPLETE  
**Length:** 366 lines

Comprehensive log of the entire query-mcp Cloud Run deployment including:
- Infrastructure setup and configuration
- Docker image building and pushing
- Cloud Run deployment with multiple revisions
- LLM provider configuration (Z.ai → Gemini)
- Vertex AI service account setup
- Migration enforcement implementation
- API endpoint testing and verification
- Local environment configuration

**Key Sections:**
- Executive Summary
- Phase-by-phase breakdown (6 major phases)
- Infrastructure issues and solutions
- Commits and file changes
- Current status and next steps
- Troubleshooting guide

**Service URL:** `https://query-mcp-124848288278.asia-southeast1.run.app`

---

## Quick Reference

### Current Service Status
```bash
curl https://query-mcp-124848288278.asia-southeast1.run.app/health
# Response: {"status":"ok"}
```

### View Recent Cloud Run Logs
```bash
gcloud logging read "resource.type=cloud_run_revision AND resource.labels.service_name=query-mcp" \
  --limit 50 \
  --project takumi-493116
```

### Redeploy Service
```bash
cd /home/htnguyen/Space/query-mcp
docker build -t asia-southeast1-docker.pkg.dev/takumi-493116/med-tech-repo/query-mcp:latest .
docker push asia-southeast1-docker.pkg.dev/takumi-493116/med-tech-repo/query-mcp:latest
gcloud run deploy query-mcp \
  --image asia-southeast1-docker.pkg.dev/takumi-493116/med-tech-repo/query-mcp:latest \
  --region asia-southeast1 \
  --project takumi-493116 \
  --quiet
```

### Local Development
```bash
source ~/.bashrc.query-mcp
python -m med_tech.api --reload
```

---

## Important Files

- **Deployment Log:** `DEPLOYMENT_LOG_2026-04-17.md` (this session)
- **Entrypoint Script:** `/home/htnguyen/Space/query-mcp/entrypoint-cloudrun.sh`
- **Deployment Guide:** `/home/htnguyen/Space/query-mcp/docs/GCP_DEPLOYMENT.md`
- **Service Account Key:** `~/.query-mcp/vertex-ai-key.json`
- **Gemini API Key:** Stored in Cloud Run env var `QUERY_MCP_API_KEY`

---

## Service Details

**Cloud Run Service:** query-mcp  
**Region:** asia-southeast1  
**Project:** takumi-493116  
**Memory:** 512Mi  
**Port:** 8080  
**Database:** Cloud SQL (takumi-med-tech / testdb)  
**LLM Provider:** Gemini (Google AI)  
**Current Revision:** query-mcp-00010-qrl

---

## Testing Endpoints

### Health Checks
```bash
curl https://query-mcp-124848288278.asia-southeast1.run.app/health
curl https://query-mcp-124848288278.asia-southeast1.run.app/api/health
```

### Text-to-SQL
```bash
# Generate SQL
curl -X POST https://query-mcp-124848288278.asia-southeast1.run.app/api/sql \
  -H "Content-Type: application/json" \
  -d '{"user_message": "count records", "table_name": "medicine_bid"}'

# Execute query
curl -X POST https://query-mcp-124848288278.asia-southeast1.run.app/api/query \
  -H "Content-Type: application/json" \
  -d '{"user_message": "show first 5 records", "table_name": "medicine_bid"}'

# Multi-language
curl -X POST https://query-mcp-124848288278.asia-southeast1.run.app/api/ask \
  -H "Content-Type: application/json" \
  -d '{"user_message": "bao nhiêu bản ghi?", "table_name": "medicine_bid", "lang": "vi"}'
```

### Database Tables
```bash
curl https://query-mcp-124848288278.asia-southeast1.run.app/api/tables
```

---

## Key Achievements

✅ Service deployed to Cloud Run (asia-southeast1)  
✅ Cloud SQL integration working  
✅ Gemini API (text-to-SQL) operational  
✅ Migrations auto-run on every deployment  
✅ Multi-language support verified  
✅ All core endpoints tested and working  
✅ Comprehensive documentation created  
✅ Local development environment configured  

---

## Next Steps

1. Populate `medicine_bid` table with real data
2. Monitor Cloud Run metrics and performance
3. Test with production data volumes
4. Consider enabling authentication if needed
5. Set up monitoring/alerting for service health

---

*Logs directory created: 2026-04-17*  
*Last updated: 2026-04-17*
