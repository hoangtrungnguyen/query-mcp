# Query MCP - Troubleshooting Guide

Solutions for common issues.

## Startup Issues

### Server Won't Start

**Error:** `ModuleNotFoundError: No module named 'fastmcp'`

**Solution:**
```bash
pip install -r requirements.txt
pip install -e .
```

**Error:** `Python version not supported`

**Solution:**
```bash
python --version  # Need 3.8+
python3.11 server.py  # Use specific version
```

---

### Port Already in Use

**Error:** `Address already in use`

**Solution:**
```bash
# Find process using port
lsof -i :5432

# Kill process
kill -9 <PID>

# Or change port in docker-compose.yml
```

---

### Permission Denied

**Error:** `Permission denied` when accessing config

**Solution:**
```bash
# Fix directory permissions
chmod 755 ~/.query-mcp/
chmod 644 ~/.query-mcp/config.json

# Or create with proper permissions
mkdir -p ~/.query-mcp
```

---

## API Key Issues

### API Key Not Recognized

**Error:** `LLM API key not configured`

**Solution:**
```bash
# Verify env var is set
echo $QUERY_MCP_API_KEY

# If empty, set it
export QUERY_MCP_API_KEY="your-key"

# Or edit config.json
~/.query-mcp/config.json
```

---

### Invalid API Key Format

**Error:** API call fails with 401/403

**Solution:**
- Check key is correct: `echo $QUERY_MCP_API_KEY`
- Verify key hasn't expired
- Check provider (Z.ai vs Anthropic)
- Test directly:
  ```bash
  python -c "from zai import ZaiClient; ZaiClient(api_key='$QUERY_MCP_API_KEY')"
  ```

---

### Wrong API Key for Provider

**Error:** API returns provider-specific error

**Solution:**
```bash
# For Z.ai (starts with custom format)
export QUERY_MCP_API_KEY="d0662f7ffca1436ca9925c940fedd661.mJYqCfIg6KhS4OsG"

# For Anthropic (starts with sk-ant-)
export QUERY_MCP_API_KEY="sk-ant-your-anthropic-key"

# Check which provider is configured
cat ~/.query-mcp/config.json | grep llm_provider
```

---

## Database Connection Issues

### PostgreSQL Won't Connect

**Error:** `could not connect to server: Connection refused`

**Solution:**
```bash
# Check if PostgreSQL is running
psql -h localhost -U postgres -c "SELECT 1;"

# If using Docker
docker ps | grep postgres
docker logs query-mcp-postgres

# Start PostgreSQL (Docker)
docker-compose up -d postgres

# Or start local PostgreSQL
brew services start postgresql  # macOS
sudo systemctl start postgresql  # Linux
```

---

### Wrong PostgreSQL Credentials

**Error:** `password authentication failed`

**Solution:**
```bash
# Check credentials in config
cat ~/.query-mcp/config.json

# Test connection with psql
psql -h localhost -p 5440 -U postgres -d testdb

# Update config if needed
```

---

### Table Not Found

**Error:** `Table 'xyz' not found or has no columns`

**Solution:**
```bash
# List all tables
docker exec -it query-mcp-postgres psql -U postgres -d testdb -c "\dt"

# Check table name (case-sensitive)
SELECT * FROM information_schema.tables WHERE table_schema = 'public';

# Create table if missing
docker exec -it query-mcp-postgres psql -U postgres -d testdb < schema.sql
```

---

### Database Connection Timeout

**Error:** `Connection timeout after 10 seconds`

**Solution:**
```bash
# Check if PostgreSQL is responsive
docker exec query-mcp-postgres pg_isready

# Increase timeout in config (if available)
# Check network connectivity
docker network ls
docker network inspect query-mcp_query-mcp-network
```

---

## SQL Generation Issues

### Wrong SQL Generated

**Example:**
- **User:** "Show me expensive drugs"
- **Generated:** `SELECT * FROM drugs` (missing WHERE clause)

**Solution:**
```bash
# Use different LLM provider
"Using Claude, show me expensive drugs"

# Or be more specific
"Show me drugs with price > 50 sorted by price"

# Check if provider is switching correctly
"Use Z.ai to generate SQL for: show me expensive drugs"
```

---

### SQL Syntax Errors

**Error:** `syntax error at or near "SELECT"`

**Solution:**
```bash
# Try again with clearer request
"Find all active drugs with price between $20 and $100"

# Test SQL directly
docker exec -it query-mcp-postgres psql -U postgres -d testdb
testdb=# <paste your SQL here>
```

---

### Query Takes Too Long

**Error:** Query execution times out

**Solution:**
```bash
# Add LIMIT to avoid scanning all rows
"Show me the first 10 expensive drugs"

# Use indexes
docker exec -it query-mcp-postgres psql -U postgres -d testdb -c "\d drugs"

# Check query plan
EXPLAIN ANALYZE <your query>;
```

---

## Docker Issues

### Docker Compose Won't Start

**Error:** `service "postgres" has incorrect env vars`

**Solution:**
```bash
# Check docker-compose.yml syntax
docker-compose config

# Rebuild without cache
docker-compose down -v
docker-compose build --no-cache
docker-compose up -d
```

---

### Container Keeps Restarting

**Error:** Container exits with error code

**Solution:**
```bash
# Check logs
docker-compose logs postgres
docker-compose logs query-mcp

# Common causes:
# 1. Port already in use
# 2. Volume mount issues
# 3. Missing environment variables

# Restart with logs visible
docker-compose up postgres
```

---

### Docker Volume Issues

**Error:** `Error response from daemon: invalid mount config`

**Solution:**
```bash
# Check volume syntax in docker-compose.yml
cat docker-compose.yml | grep volumes

# Remove and recreate volumes
docker-compose down -v
docker-compose up -d

# Backup volume before deleting
docker run -v query-mcp_postgres_data:/data -v /tmp:/backup alpine tar czf /backup/backup.tar.gz /data
```

---

## MCP Integration Issues

### MCP Server Not Connecting

**Error:** "MCP connection failed" in Claude

**Solution:**
```bash
# Verify server is running
ps aux | grep server.py

# Test server manually
python server.py
# Should show connection info

# Check Claude config syntax
cat ~/Library/Application\ Support/Claude/claude_desktop_config.json | jq .

# Restart Claude
# Force quit and relaunch
```

---

### Claude Can't See Tools

**Error:** Tools don't appear in Claude

**Solution:**
```bash
# 1. Verify MCP is connected
# 2. Check server logs for errors
python server.py
# Look for error messages

# 3. Restart Claude and reconnect
# 4. Check file permissions
ls -la ~/.query-mcp/

# 5. Try with verbose output
PYTHONUNBUFFERED=1 python -u server.py
```

---

### Slow Response Times

**Error:** Claude takes 5+ seconds to respond

**Solution:**
```bash
# Check which provider is in use
cat ~/.query-mcp/config.json | grep llm_provider

# Z.ai is faster
"Use Z.ai for this query"

# Check LLM API latency
time curl https://api.z.ai/v1/chat/completions \
  -H "Authorization: Bearer $QUERY_MCP_API_KEY"

# Monitor local database performance
docker exec query-mcp-postgres pg_stat_statements
```

---

## Performance Issues

### High Memory Usage

**Symptom:** Process uses >500MB

**Solution:**
```bash
# Monitor memory
docker stats query-mcp-server

# Restart container
docker-compose restart query-mcp

# Check for memory leaks
python -m memory_profiler server.py
```

---

### Slow Database Queries

**Symptom:** Queries take 2+ seconds

**Solution:**
```bash
# Check indexes
docker exec -it query-mcp-postgres psql -U postgres -d testdb -c "\d drugs"

# Analyze query plan
EXPLAIN ANALYZE SELECT * FROM drugs WHERE price > 100;

# Add missing indexes
CREATE INDEX idx_drugs_price ON drugs(price);
CREATE INDEX idx_orders_user_id ON orders(user_id);
```

---

### High API Call Latency

**Symptom:** LLM responses slow

**Solution:**
```bash
# Check network connectivity
ping api.z.ai
ping api.anthropic.com

# Switch to faster provider
"Use Z.ai"

# Check API status
# Visit z.ai or anthropic status page
```

---

## Data Issues

### Sample Data Not Loaded

**Error:** Tables are empty

**Solution:**
```bash
# Check if init script ran
docker logs query-mcp-postgres | grep "Database initialized"

# Manually load sample data
docker exec -i query-mcp-postgres psql -U postgres -d testdb < init-db.sql

# Verify data exists
docker exec -it query-mcp-postgres psql -U postgres -d testdb -c "SELECT COUNT(*) FROM drugs;"
```

---

### Data Corruption

**Error:** Unexpected query results

**Solution:**
```bash
# Backup current data
docker exec query-mcp-postgres pg_dump -U postgres -d testdb > backup.sql

# Restore from init script
docker-compose down -v
docker-compose up -d

# Or manually reload
docker exec -i query-mcp-postgres psql -U postgres -d testdb < init-db.sql
```

---

## Configuration Issues

### Config File Not Found

**Error:** `Config file not found`

**Solution:**
```bash
# Check location
ls -la ~/.query-mcp/config.json

# Create default config
mkdir -p ~/.query-mcp
# Server will create it on first run

# Or copy example
cp .env.example ~/.query-mcp/config.json
```

---

### Invalid Configuration Format

**Error:** `JSON decode error` or similar

**Solution:**
```bash
# Validate JSON
jq . ~/.query-mcp/config.json

# If invalid, restore example
cp .env.example ~/.query-mcp/config.json

# Edit with proper JSON syntax
# Remember: JSON doesn't support comments
```

---

## Debugging Steps

### Enable Verbose Logging

```bash
# Python debug mode
PYTHONUNBUFFERED=1 python -u server.py

# Environment debug
export DEBUG=1
python server.py
```

### Test Each Component

```bash
# 1. Test LLM connection
python -c "from zai import ZaiClient; print('Z.ai OK')"
python -c "from anthropic import Anthropic; print('Anthropic OK')"

# 2. Test database connection
psql -h localhost -p 5440 -U postgres -d testdb -c "SELECT 1;"

# 3. Test MCP server
python server.py
# Should show startup messages

# 4. Test with curl (if HTTP)
curl -X POST http://localhost:8000/tools/generate_sql \
  -H "Content-Type: application/json" \
  -d '{"user_message": "Show me drugs", "table_name": "drugs"}'
```

---

## Getting Help

1. **Check relevant docs:**
   - README.md - General
   - API_REFERENCE.md - API issues
   - DOCKER_SETUP.md - Docker issues
   - INTEGRATION.md - Claude integration

2. **Enable debug mode:**
   ```bash
   PYTHONUNBUFFERED=1 python -u server.py
   ```

3. **Collect diagnostics:**
   ```bash
   python --version
   echo $QUERY_MCP_API_KEY
   cat ~/.query-mcp/config.json
   docker ps -a
   docker logs query-mcp-server
   ```

4. **Test each component:**
   - LLM API key works
   - PostgreSQL is accessible
   - Network connectivity is OK
   - MCP server starts

---

## Still Stuck?

- Review the error message carefully
- Check documentation for similar issues
- Test each component independently
- Enable debug logging
- Verify all prerequisites are met
