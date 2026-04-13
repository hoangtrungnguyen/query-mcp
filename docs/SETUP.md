# Setup Query MCP Server

## Step 1: Install Dependencies

```bash
cd /home/htnguyen/Space/query-mcp
python3 -m venv venv
source venv/bin/activate
pip install -r requirements.txt
```

## Step 2: Configure Database & API Key

### Option A: Environment Variable (Recommended)
```bash
export QUERY_MCP_API_KEY="your-zai-api-key"
python server.py
```

### Option B: Config File
Edit `~/.query-mcp/config.json`:
```json
{
  "database": {
    "host": "your-postgres-host",
    "port": 5432,
    "name": "your-database",
    "user": "postgres",
    "password": "your-password"
  },
  "text_to_sql": {
    "llm_api_key": "your-zai-api-key",
    "llm_provider": "zai",
    "llm_model": "glm-5.1"
  }
}
```

**For Anthropic Claude instead:**
```json
{
  "text_to_sql": {
    "llm_api_key": "sk-ant-...",
    "llm_provider": "anthropic",
    "llm_model": "claude-3-5-sonnet-20241022"
  }
}
```

## Step 3: Add to Claude Code (MCP Integration)

### For Claude.ai/code users:
1. Open Claude Code settings
2. Go to "MCP Servers"
3. Add new server:
   - **Name**: Query MCP
   - **Command**: `python`
   - **Args**: `/home/htnguyen/Space/query-mcp/server.py`
4. Click "Connect"

### For Claude Desktop:
Edit `~/Library/Application Support/Claude/claude_desktop_config.json` (macOS) or equivalent on other OS:
```json
{
  "mcpServers": {
    "query-mcp": {
      "command": "python",
      "args": ["/home/htnguyen/Space/query-mcp/server.py"],
      "env": {
        "QUERY_MCP_API_KEY": "sk-proj-..."
      }
    }
  }
}
```

## Step 4: Test

```bash
# Terminal test - start server
python server.py

# In Claude, try:
# "Query the drugs table for items with price > 100"
# "Count how many items are in each category"
# "Show me the most recent 5 drugs added"
```

## Troubleshooting

**"LLM API key not configured"**
- Set `QUERY_MCP_API_KEY` environment variable
- OR edit `~/.query-mcp/config.json` and set `text_to_sql.llm_api_key`

**"Database connection failed"**
- Check PostgreSQL is running
- Verify credentials in `~/.query-mcp/config.json`
- Test: `psql -h localhost -U postgres -d postgres`

**"Table not found"**
- Verify table exists: `psql -h localhost -U postgres -d postgres -c "\dt"`
- Table name is case-sensitive in PostgreSQL
