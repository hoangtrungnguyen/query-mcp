# Query MCP — Ask Your Data Anything

Stop waiting on reports. Type a question, get an answer.

Query MCP connects your business database to an AI assistant so that anyone on your team — regardless of technical background — can get immediate answers from your data.

**Ask:** *"Which products drove the most revenue last month?"*  
**Get:** A clear answer in seconds, no SQL or coding required.

---

## Why Query MCP?

Most businesses sit on a goldmine of data locked behind technical barriers. Getting answers today means filing a request with your data team, waiting days, and hoping the report matches what you actually wanted.

Query MCP removes that bottleneck. Connect it to your database once, and your whole team can ask questions in plain English.

---

## What You Can Do

| Question You'd Ask | What You Learn |
|---|---|
| "What were our top 10 products by revenue this quarter?" | Your best performers, ranked |
| "Which customers haven't placed an order in 90 days?" | Churn risk list, ready to act on |
| "How does this month's sales compare to last month?" | Trend at a glance |
| "Which product category has the highest profit margin?" | Where to double down |
| "Show me all pending orders over $500" | High-priority queue |
| "Who are our most loyal customers?" | Your VIP segment |

---

## Key Benefits

| Benefit | Detail |
|---|---|
| **No SQL required** | Ask in plain English — the AI writes the query for you |
| **Instant answers** | Results in 1–3 seconds, not hours or days |
| **Safe by design** | Read-only access — nothing in your database can be modified |
| **Audit trail** | Every question and result is logged for accountability |
| **Your language** | Ask in any language; get answers back in the same language |
| **Clarifies ambiguity** | If your question is unclear, it asks before guessing |

---

## How It Works

```
You ask a question in plain English
          │
          ▼
  AI understands your intent
  and writes the correct database query
          │
          ▼
  Query runs against your database
          │
          ▼
  Results come back as a clear,
  human-readable answer
```

---

## Quick Example

**You ask:** *"Show me the top 5 products by total sales this year"*

**Query MCP returns:**
```
The top 5 products by total sales this year are:

1. Product A — $128,450 (342 units)
2. Product B — $97,200 (215 units)
3. Product C — $84,750 (180 units)
4. Product D — $76,300 (310 units)
5. Product E — $61,900 (95 units)
```

---

## Supported AI Engines

Query MCP works with leading AI providers. Your technical team can configure which one to use.

| Engine | Best For |
|---|---|
| Google Gemini | Fast, everyday queries — free tier available |
| Anthropic Claude | Complex analysis and nuanced questions |
| Z.ai GLM | High-volume, cost-effective usage |

---

## Setup

> **For your IT or development team** — business users don't need to do this.

**Requirements:** Python 3.8+, PostgreSQL

```bash
# Install dependencies
python3 -m venv venv
source venv/bin/activate
pip install -r requirements.txt

# Set your AI API key (Google Gemini has a free tier)
export QUERY_MCP_API_KEY="your-api-key"

# Initialize database
alembic upgrade head

# Start the server
python src/server.py http 8001
```

### Connect to Claude

1. Open Claude Code settings → MCP Servers → Add new server
2. Set:
   - **Command**: `python`
   - **Args**: `/path/to/query-mcp/src/server.py`
   - **Env**: `QUERY_MCP_API_KEY=your-api-key`
3. Click Connect

Once connected, ask Claude naturally: *"Show me the top 10 customers by revenue"* and it handles the rest.

---

## Configuration

### Priority Order

1. `QUERY_MCP_API_KEY` environment variable *(recommended)*
2. `~/.query-mcp/config.json` *(auto-created on first run)*

### Config File

```json
{
  "database": {
    "host": "your-db-host",
    "port": 5432,
    "name": "your-database",
    "user": "your-db-user",
    "password": "your-db-password"
  },
  "text_to_sql": {
    "llm_api_key": "",
    "llm_provider": "gemini",
    "llm_model": "gemini-2.5-flash"
  }
}
```

---

## Security & Privacy

- **Read-only**: Query MCP never modifies, deletes, or inserts data
- **Parameterized queries**: Protected against injection attacks
- **Schema validation**: Only accesses tables you explicitly allow
- **Local data**: Your data stays in your database; only table structure and query results are sent to the AI
- **Full audit log**: Every question, generated query, and result is recorded

---

## Audit Trail

Every query is automatically logged so you can track who asked what and when.

| Field | What It Captures |
|---|---|
| `user_message` | The original question asked |
| `generated_sql` | The query the AI created |
| `row_count` | How many records were returned |
| `execution_time_ms` | How fast the answer came back |
| `llm_provider` | Which AI engine answered |
| `created_at` | Timestamp |

---

## Deployment Options

| Option | Best For |
|---|---|
| Local / Docker | Internal team tools, pilots |
| Cloud Run | Production deployment, team-wide access |

See [docs/DEPLOYMENT.md](docs/DEPLOYMENT.md) for full deployment instructions, or [docs/DOCKER_SETUP.md](docs/DOCKER_SETUP.md) for container setup.

---

## Common Questions

**Do I need to know SQL or coding?**  
No. That's the point. Ask in plain English.

**Is my data safe?**  
Your data stays in your database. The AI only sees your table structure and the results of specific queries.

**What if the answer seems wrong?**  
Rephrase your question with more detail. If you said "show me top customers", try "show me top customers by total order value in 2025".

**What databases are supported?**  
PostgreSQL currently. MySQL and others are on the roadmap.

**Can someone accidentally delete data?**  
No. Query MCP is strictly read-only.

---

## Documentation

| Guide | Purpose |
|---|---|
| [QUICK_START.md](QUICK_START.md) | Get running in 5 minutes |
| [docs/OVERVIEW.md](docs/OVERVIEW.md) | Full feature overview |
| [docs/EXAMPLES.md](docs/EXAMPLES.md) | Sample questions and results |
| [docs/FAQ.md](docs/FAQ.md) | Common questions |
| [docs/DEPLOYMENT.md](docs/DEPLOYMENT.md) | Production setup |
| [docs/API_ENDPOINTS.md](docs/API_ENDPOINTS.md) | REST API reference (for developers) |
| [docs/ARCHITECTURE.md](docs/ARCHITECTURE.md) | System design (for developers) |

---

## Project Structure

```
query-mcp/
├── src/
│   ├── server.py          # MCP server + HTTP REST entry point
│   ├── text_to_sql.py     # Core AI-to-SQL engine
│   ├── db_service.py      # Database access layer
│   └── workflow.py        # Data loading workflow
├── alembic/               # Database schema migrations
├── docker/                # Container configuration
├── docs/                  # Full documentation
└── README.md
```
