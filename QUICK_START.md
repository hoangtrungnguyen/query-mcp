# Quick Start — 5 Minutes to Your First Insight

> **For your IT or development team.** Once set up, business users can ask questions without any technical steps.

---

## Prerequisites

- Docker & Docker Compose
- An AI API key — Google Gemini is recommended ([free tier available at Google AI Studio](https://aistudio.google.com))

---

## 1. Set Your API Key

```bash
export QUERY_MCP_API_KEY="your-gemini-api-key"
```

## 2. Start the Service

```bash
cd /home/htnguyen/Space/query-mcp
docker-compose up -d
```

## 3. Verify It's Running

```bash
docker-compose ps
```

Expected output:
```
NAME                     STATUS
query-mcp-postgres       running (healthy)
query-mcp-server         running
```

---

## 4. Connect to Claude

**In Claude Code:**
1. Settings → MCP Servers → Add new server
2. Set:
   - **Name:** Query MCP
   - **Command:** `docker`
   - **Args:** `exec -i query-mcp-server python server.py`
3. Click Connect

**In Claude Desktop:**  
See [docs/INTEGRATION.md](docs/INTEGRATION.md) for the config file location.

---

## 5. Start Asking Questions

Once connected, Claude can answer business questions directly from your data:

- *"What are our top 5 products by revenue?"*
- *"How many customers placed orders this month?"*
- *"Which items are running low on stock?"*
- *"Show me all orders over $200 that are still pending"*

No SQL, no coding — just ask.

---

## What's Included in the Demo Database

The Docker setup includes a sample database with realistic business data so you can explore right away:

| Data | Records | What you can explore |
|------|---------|----------------------|
| Products | 15 | Pricing, categories, stock levels |
| Items | 10 | Inventory by category |
| Customers | 10 | Active/inactive, spending history |
| Orders | 10 | Status, totals, customer linkage |

**Try asking:**
- "Which products have the highest price?"
- "How much has each customer spent in total?"
- "Show me all completed orders sorted by value"

---

## Access Details

| Service | Address | Use |
|---------|---------|-----|
| PostgreSQL | localhost:5440 | Direct database access (for developers) |
| Query MCP | Connected via Claude | Natural language queries (for everyone) |

---

## Common Operations

### Stop the service
```bash
docker-compose down
```

### Restart the service
```bash
docker-compose restart
```

### View logs
```bash
docker-compose logs -f
```

### Connect your own database

Edit `docker-compose.yml` with your PostgreSQL connection details, then restart.  
See [docs/DOCKER_SETUP.md](docs/DOCKER_SETUP.md) for all configuration options.

---

## Troubleshooting

**Services won't start:**
```bash
docker-compose logs          # Check for errors
docker-compose down -v       # Clean slate
docker-compose build --no-cache
docker-compose up -d
```

**Can't connect to the database:**
```bash
docker-compose ps            # Is it running?
lsof -i :5440                # Is the port in use?
```

**API key errors:**
```bash
echo $QUERY_MCP_API_KEY      # Is it set?
docker-compose restart       # Apply the env var
```

---

## Next Steps

- **Connect your real database** — see [docs/DOCKER_SETUP.md](docs/DOCKER_SETUP.md)
- **Share with your team** — see [docs/DEPLOYMENT.md](docs/DEPLOYMENT.md) for production deployment
- **See what's possible** — browse [docs/EXAMPLES.md](docs/EXAMPLES.md) for question ideas
- **Common questions** — [docs/FAQ.md](docs/FAQ.md)
