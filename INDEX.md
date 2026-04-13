# Query MCP Documentation Index

Complete documentation for the Query MCP server.

## Quick Links

| Document | Purpose | Read Time |
|----------|---------|-----------|
| [README.md](README.md) | Start here! Setup, features, basic usage | 10 min |
| [SETUP.md](SETUP.md) | Detailed setup and integration instructions | 10 min |
| [API_REFERENCE.md](API_REFERENCE.md) | Complete API reference for all tools/resources | 15 min |
| [ARCHITECTURE.md](ARCHITECTURE.md) | System design, data flow, components | 20 min |
| [DEPLOYMENT.md](DEPLOYMENT.md) | Production deployment, scaling, troubleshooting | 20 min |

## By Use Case

### I want to...

**Get started quickly**
→ Read [README.md](README.md)

**Set up with my IDE/Claude**
→ Read [SETUP.md](SETUP.md)

**Understand all available endpoints/parameters**
→ Read [API_REFERENCE.md](API_REFERENCE.md)

**Understand how it works internally**
→ Read [ARCHITECTURE.md](ARCHITECTURE.md)

**Deploy to production**
→ Read [DEPLOYMENT.md](DEPLOYMENT.md)

**Troubleshoot issues**
→ See [Troubleshooting](#troubleshooting) section below

**Extend/modify the code**
→ Read [ARCHITECTURE.md](ARCHITECTURE.md) then check [CODE_STRUCTURE](#code-structure)

---

## Documentation Structure

```
query-mcp/
├── README.md              ← Quick start, features overview
├── SETUP.md               ← Detailed setup instructions
├── API_REFERENCE.md       ← Complete API documentation
├── ARCHITECTURE.md        ← System design & components
├── DEPLOYMENT.md          ← Production deployment guide
├── INDEX.md              ← This file
├── server.py              ← Main MCP server
├── text_to_sql.py         ← Core TextToSQL class
├── requirements.txt       ← Python dependencies
└── .gitignore            ← Git ignore patterns
```

---

## Code Structure

### server.py (Main Server)

Entry point for the MCP server.

**Key Sections:**
- Configuration loading (`load_config()`, `save_config()`)
- MCP tool definitions (`@mcp.tool`)
- MCP resource definitions (`@mcp.resource`)
- MCP prompt definitions (`@mcp.prompt`)

**Main Functions:**
- `load_config()` - Load JSON config from disk
- `save_config()` - Save JSON config to disk
- `_get_converter()` - Create TextToSQL instance
- `generate_sql()` - Generate SQL from natural language
- `execute_sql()` - Execute SQL and return results
- `text_to_sql_execute()` - Generate and execute SQL
- `get_database_config()` - Return database config
- `get_text_to_sql_config()` - Return LLM config
- `sql_query_help()` - Return help for SQL queries

### text_to_sql.py (Core Logic)

Core business logic for SQL generation and execution.

**Key Class:**
```python
class TextToSQL:
    def __init__()          # Initialize with LLM + DB config
    def generate_sql()      # Generate SQL from natural language
    def execute_query()     # Execute SQL and return results
    def generate_and_execute()  # Do both in one call
```

**Helper Methods:**
- `_get_db_connection()` - Create PostgreSQL connection
- `_get_table_schema()` - Fetch table schema for LLM context

---

## Feature Checklist

| Feature | Status | Details |
|---------|--------|---------|
| Generate SQL from natural language | ✅ | Uses Claude or Z.ai |
| Execute SQL and return results | ✅ | Direct PostgreSQL query |
| Combined generation + execution | ✅ | Single call for both |
| Per-request LLM provider selection | ✅ | Override config default |
| Multiple LLM providers | ✅ | Z.ai (default), Anthropic |
| Database schema discovery | ✅ | Auto-fetches table info |
| Error handling | ✅ | Consistent error format |
| Configuration management | ✅ | JSON file + env vars |
| MCP protocol support | ✅ | Tools, resources, prompts |
| Claude Code integration | ✅ | Add as MCP server |
| Claude Desktop integration | ✅ | Edit config file |
| Production deployment | ✅ | Docker, systemd, etc. |
| Logging (basic) | ✅ | Built-in |
| Connection pooling | ⏳ | Recommended for scale |
| Schema caching | ⏳ | Recommended for perf |
| Rate limiting | ⏳ | Recommended for prod |
| Request authentication | ⏳ | Not implemented |

---

## Getting Help

### Common Issues

**Q: "LLM API key not configured"**
A: Set `QUERY_MCP_API_KEY` environment variable or edit `~/.query-mcp/config.json`

**Q: "Database connection failed"**
A: Check PostgreSQL is running, verify host/port/credentials in config

**Q: "Table 'xyz' not found"**
A: Table names are case-sensitive in PostgreSQL. Check spelling.

**Q: Server won't start**
A: Check Python version (need 3.8+), verify dependencies installed

See [DEPLOYMENT.md](DEPLOYMENT.md) for more troubleshooting.

### Getting in Touch

- Check [README.md](README.md) for quick answers
- See [ARCHITECTURE.md](ARCHITECTURE.md) for how things work
- See [DEPLOYMENT.md](DEPLOYMENT.md) for deployment questions
- Review code comments in `server.py` and `text_to_sql.py`

---

## Quick Reference

### Setup (1 minute)

```bash
cd /home/htnguyen/Space/query-mcp
python3 -m venv venv && source venv/bin/activate
pip install -r requirements.txt
export QUERY_MCP_API_KEY="your-key"
python server.py
```

### Add to Claude Code

Settings → MCP Servers → Add:
- Command: `python`
- Args: `/home/htnguyen/Space/query-mcp/server.py`
- Env: `QUERY_MCP_API_KEY=your-key`

### Use in Claude

Ask Claude: "Query the drugs table for items with price > 100"

### Switch LLM Provider

In request: `"llm_provider": "anthropic"`

Or in config: `~/.query-mcp/config.json`

### Configure Database

Edit `~/.query-mcp/config.json`:
```json
{
  "database": {
    "host": "your-host",
    "port": 5432,
    "name": "your-db",
    "user": "your-user",
    "password": "your-password"
  }
}
```

---

## Version & Updates

- **Current Version:** 1.0.0
- **Last Updated:** 2026-04-13
- **Python:** 3.8+
- **Dependencies:**
  - fastmcp==0.7.1
  - zai-sdk==1.0.0
  - anthropic==0.38.0
  - psycopg2-binary==2.9.10

---

## License & Attribution

Query MCP is a standalone tool for text-to-SQL conversion via LLM APIs.

Uses:
- Z.ai API (https://z.ai)
- Anthropic Claude API (https://anthropic.com)
- PostgreSQL (https://postgresql.org)
- FastMCP (MCP protocol implementation)

---

## Roadmap

### Coming Soon
- [ ] Schema caching for performance
- [ ] Connection pooling for high concurrency
- [ ] Rate limiting
- [ ] Request logging and monitoring
- [ ] Query result caching

### Future
- [ ] Support for other databases (MySQL, SQLServer)
- [ ] Query result visualization
- [ ] Batch query processing
- [ ] Query history/analytics
- [ ] Fine-tuning LLM for better SQL generation
- [ ] User authentication/authorization

---

## File Summary

### Documentation Files

- **README.md** (10KB) - Quick start guide, features, basic usage
- **SETUP.md** (8KB) - Detailed setup and integration
- **API_REFERENCE.md** (12KB) - Complete API reference
- **ARCHITECTURE.md** (20KB) - System design and internals
- **DEPLOYMENT.md** (18KB) - Production deployment guide
- **INDEX.md** (this file) - Documentation index

### Code Files

- **server.py** (5KB) - MCP server implementation
- **text_to_sql.py** (8KB) - Core TextToSQL class
- **requirements.txt** (1KB) - Python dependencies
- **.gitignore** (1KB) - Git ignore patterns

---

## Next Steps

1. **Read** [README.md](README.md) (5-10 minutes)
2. **Setup** using [SETUP.md](SETUP.md) (5-10 minutes)
3. **Test** using examples in [API_REFERENCE.md](API_REFERENCE.md) (5 minutes)
4. **Deploy** using [DEPLOYMENT.md](DEPLOYMENT.md) when ready

---

## Quick Answers

**Q: How do I use Z.ai instead of Anthropic?**
A: It's the default! Just set your Z.ai API key in `QUERY_MCP_API_KEY`

**Q: Can I use Anthropic Claude instead?**
A: Yes! Pass `"llm_provider": "anthropic"` in requests or set it in config

**Q: How many concurrent users can it handle?**
A: Currently ~10-20. For more, enable connection pooling (see DEPLOYMENT.md)

**Q: Can I use with MySQL or SQLServer?**
A: Not yet. Would need to update schema query and connection code. See ARCHITECTURE.md

**Q: Is it secure?**
A: API key stored in env var (not committed to git). Database creds in `~/.query-mcp/config.json`. No query validation.

**Q: Where is config stored?**
A: `~/.query-mcp/config.json` (user's home directory)

**Q: Can I access data I'm not supposed to?**
A: Yes. PostgreSQL permissions apply. Restrict database user accordingly.

**Q: How do I monitor errors?**
A: Check logs. Implement logging wrapper (see DEPLOYMENT.md)

**Q: Can I cache results?**
A: Not built-in. Could add caching layer (see DEPLOYMENT.md)

**Q: Is there a REST API?**
A: No, only MCP protocol. Could be added in future.
