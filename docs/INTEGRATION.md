# Query MCP - Claude Integration Guide

How to integrate Query MCP with Claude Code and Claude Desktop.

## Claude Code Integration

### Step 1: Install Dependencies

```bash
cd /home/htnguyen/Space/query-mcp
python3 -m venv venv
source venv/bin/activate
pip install -r requirements.txt
```

### Step 2: Set API Key

```bash
export QUERY_MCP_API_KEY="your-zai-or-anthropic-key"
```

### Step 3: Add MCP Server

Open Claude Code → Settings → MCP Servers:

**Add New Server:**
- **Name:** Query MCP
- **Command:** `python`
- **Args:** `/home/htnguyen/Space/query-mcp/server.py`
- **Environment:**
  - `QUERY_MCP_API_KEY=your-key`

### Step 4: Connect

Click "Connect" and wait for connection confirmation.

### Step 5: Use in Claude

Ask Claude:
```
"Query the drugs table and show me all active items"
"Count how many orders each user has placed"
"Find the top 5 most expensive products"
```

Claude will:
1. Recognize the query request
2. Call Query MCP tool
3. Generate SQL
4. Execute on PostgreSQL
5. Format and present results

---

## Claude Desktop Integration

### macOS

Edit `~/Library/Application Support/Claude/claude_desktop_config.json`:

```json
{
  "mcpServers": {
    "query-mcp": {
      "command": "python",
      "args": ["/home/htnguyen/Space/query-mcp/server.py"],
      "env": {
        "QUERY_MCP_API_KEY": "your-key"
      }
    }
  }
}
```

Then restart Claude Desktop.

### Windows

Edit `%APPDATA%\Claude\claude_desktop_config.json`:

```json
{
  "mcpServers": {
    "query-mcp": {
      "command": "python",
      "args": ["C:\\path\\to\\query-mcp\\server.py"],
      "env": {
        "QUERY_MCP_API_KEY": "your-key"
      }
    }
  }
}
```

### Linux

Edit `~/.config/Claude/claude_desktop_config.json`:

```json
{
  "mcpServers": {
    "query-mcp": {
      "command": "python",
      "args": ["/home/user/query-mcp/server.py"],
      "env": {
        "QUERY_MCP_API_KEY": "your-key"
      }
    }
  }
}
```

Restart Claude Desktop.

---

## Docker Integration

If using Docker Compose:

```bash
cd /home/htnguyen/Space/query-mcp
export QUERY_MCP_API_KEY="your-key"
docker-compose up -d
```

Then in Claude Config:

```json
{
  "mcpServers": {
    "query-mcp": {
      "command": "docker",
      "args": ["exec", "-i", "query-mcp-server", "python", "server.py"],
      "env": {
        "QUERY_MCP_API_KEY": "your-key"
      }
    }
  }
}
```

---

## Testing the Integration

### In Claude Code

Ask:
```
"Show me a few drugs from the database"
```

Expected response:
- Claude recognizes database query
- Calls Query MCP
- Generates SQL
- Returns results

### Example Conversation

**You:** Query the drugs table for expensive items over $20

**Claude:** I'll search the drugs table for items priced over $20.
```
SELECT * FROM drugs WHERE price > 20 ORDER BY price DESC;
```

**Results:**
```
Found 10 drugs with price > $20:
1. Ciprofloxacin ($35.99)
2. Clopidogrel ($45.99)
3. Warfarin ($28.99)
...
```

---

## Available Tools in Claude

Once integrated, Claude can use:

### 1. `generate_sql`
Generate SQL without executing
```
"What SQL would find drugs in the Pain Relief category?"
```

### 2. `execute_sql`
Execute pre-written SQL
```
"Run this query: SELECT * FROM drugs LIMIT 5"
```

### 3. `text_to_sql_execute`
Natural language → SQL → Results (one step)
```
"Show me all active users sorted by name"
```

---

## Provider Selection in Claude

Claude can request specific providers:

```
"Using Z.ai, find expensive items"
→ Uses Z.ai provider

"Using Claude, analyze the order patterns"
→ Uses Anthropic Claude provider
```

---

## Troubleshooting Integration

### MCP Server Not Connecting

**Check:**
1. API key is set: `echo $QUERY_MCP_API_KEY`
2. Server is running: `ps aux | grep server.py`
3. Port is available (if using Docker)
4. Path is correct in config file

**Fix:**
```bash
# Kill any running servers
pkill -f "python server.py"

# Restart with verbose output
python -u server.py
```

### Connection Timeout

```bash
# Test PostgreSQL connection
psql -h localhost -p 5440 -U postgres -d testdb -c "SELECT 1;"

# Verify LLM API key
python -c "from zai import ZaiClient; ZaiClient(api_key='$QUERY_MCP_API_KEY')"
```

### Claude Can't See the Tool

**In Claude Code:**
- Try reconnecting MCP server
- Check settings for errors
- Check Claude logs for details

**In Claude Desktop:**
- Restart application
- Check config file syntax (must be valid JSON)
- Run: `cat ~/Library/Application\ Support/Claude/claude_desktop_config.json`

---

## Best Practices

### 1. Use Environment Variables
```bash
export QUERY_MCP_API_KEY="your-key"
# Never hardcode in config files
```

### 2. Test Before Integration
```bash
python server.py
# Manually test with psql before adding to Claude
```

### 3. Provide Context to Claude
```
"I have a PostgreSQL database with drugs, items, and users tables.
Show me all active drugs sorted by price."
```

### 4. Specify Provider if Needed
```
"Using Z.ai, what's the schema of the drugs table?"
```

### 5. Monitor API Usage
Track API calls to Z.ai or Anthropic for cost/quota.

---

## Advanced Integration

### Custom Database Views

Create views in PostgreSQL:

```sql
CREATE VIEW expensive_drugs AS
SELECT id, name, price
FROM drugs
WHERE price > 50
ORDER BY price DESC;
```

Then ask Claude:
```
"Show me expensive drugs"
→ Claude queries the view
```

### Multiple Databases

If you have multiple databases, set up separate Query MCP instances:

```json
{
  "mcpServers": {
    "query-mcp-main": {
      "command": "python",
      "args": ["/path/to/query-mcp/server.py"],
      "env": {"DB_NAME": "maindb", "QUERY_MCP_API_KEY": "..."}
    },
    "query-mcp-analytics": {
      "command": "python",
      "args": ["/path/to/query-mcp/server.py"],
      "env": {"DB_NAME": "analyticsdb", "QUERY_MCP_API_KEY": "..."}
    }
  }
}
```

### Custom Prompts

Guide Claude with system prompts:

```
"You have access to a medical database with:
- drugs table: id, name, category, price, stock
- users table: id, name, email, status
- orders table: id, user_id, total, status

When users ask about the database, use the Query MCP tools.
Always show SQL before results for transparency."
```

---

## Security Considerations

### API Key Protection
✅ Store in environment variable
✅ Never commit to git
✅ Rotate periodically
✅ Use separate keys for prod/dev

### Database Access
✅ Limit PostgreSQL user permissions
✅ Use strong passwords
✅ Only expose necessary tables
✅ Consider row-level security (RLS)

### Network Security
✅ Use TLS for remote connections
✅ Firewall PostgreSQL to internal only
✅ Authenticate API requests
✅ Log all queries

---

## Performance Tips

### For Z.ai (Faster)
```
"Use Z.ai for fast queries: Show me all drugs"
```
- Faster response time
- Good for simple queries
- Lower cost

### For Claude (Better)
```
"Use Claude for complex analysis: Analyze spending patterns by user"
```
- Better reasoning
- Good for complex queries
- Higher cost/latency

---

## Example Workflows

### Workflow 1: Data Exploration
1. "What tables do we have?"
2. "Show me the schema of drugs table"
3. "How many drugs are in stock?"
4. "What's the price range?"

### Workflow 2: Business Analysis
1. "Show me sales by category"
2. "Which users spent the most?"
3. "What are our top products?"
4. "Identify inactive users"

### Workflow 3: Report Generation
1. Claude executes multiple queries
2. Aggregates results
3. Formats as report
4. Provides insights

---

## Support

- See README.md for usage
- See API_REFERENCE.md for tool details
- See TROUBLESHOOTING.md for common issues
- See EXAMPLES.md for query examples
