# Query MCP - Frequently Asked Questions

Common questions and answers.

## General

**Q: What is Query MCP?**
A: Query MCP is a tool that converts natural language questions into SQL queries using AI (Z.ai or Claude). It's an MCP-compatible server that integrates with Claude.

**Q: What can I use it for?**
A: Business queries, data exploration, analytics, reporting, ad-hoc data analysis.

**Q: Is it free?**
A: The software is open-source (free), but you pay for LLM API calls (Z.ai or Anthropic).

**Q: What's the difference between Z.ai and Anthropic?**
A: Z.ai is faster and cheaper. Anthropic Claude is more accurate for complex queries. Choose based on your needs.

**Q: Can I use both providers?**
A: Yes! Switch per-request: "Use Z.ai for this" or "Use Claude for this".

---

## Setup & Installation

**Q: Do I need to install anything?**
A: Just Docker (recommended) or Python 3.8+.

**Q: How long does setup take?**
A: ~5 minutes with Docker, ~10 minutes manually.

**Q: Can I run on Windows?**
A: Yes, with Docker Desktop or WSL2 + Python.

**Q: Do I need to modify my database?**
A: No, Query MCP reads from existing tables. No schema changes needed.

**Q: Can I use my own database?**
A: Yes! Update config with your PostgreSQL connection details.

---

## Usage

**Q: How do I ask questions?**
A: Natural language: "Show me expensive drugs" or "Count items by category".

**Q: Do I need to know SQL?**
A: No! That's the whole point. Ask in English, we generate SQL.

**Q: What if the generated SQL is wrong?**
A: Try rephrasing: "Show drugs with price > 100 sorted by price".

**Q: Can I see the SQL before it runs?**
A: Yes, use `generate_sql` tool to see SQL without executing.

**Q: What tables can I query?**
A: Any table in your PostgreSQL database.

---

## API Keys & Security

**Q: How do I get an API key?**
A: 
- **Z.ai:** https://z.ai (create account)
- **Anthropic:** https://anthropic.com (create account)

**Q: Is my API key safe?**
A: Yes, stored in environment variables (not in code). Never committed to git.

**Q: What if my API key is exposed?**
A: Regenerate it immediately in your provider account.

**Q: Can I use multiple API keys?**
A: Yes, one per provider in config.

**Q: Do I need to store my database password?**
A: Yes, in `~/.query-mcp/config.json` (user-local, git-ignored).

---

## Database & SQL

**Q: What databases are supported?**
A: Currently PostgreSQL only. MySQL/SQLServer planned.

**Q: Can I query multiple databases?**
A: Not simultaneously. Set up separate Query MCP instances if needed.

**Q: Does it modify data?**
A: No, only SELECT queries. Write operations not supported.

**Q: How many rows can I retrieve?**
A: Default limit is 100 rows per query (configurable).

**Q: What about performance on large tables?**
A: Should be fine for tables with millions of rows. Use indexes for best performance.

**Q: Can I create tables or views?**
A: No, Query MCP is read-only. Create schemas manually in PostgreSQL.

---

## LLM & AI

**Q: How does SQL generation work?**
A: LLM receives table schema + your question → generates SQL → executes.

**Q: Can I fine-tune the LLM?**
A: Not yet, planned for future versions.

**Q: How long does SQL generation take?**
A: ~500ms with Z.ai, ~1-2s with Claude.

**Q: What if the LLM is down?**
A: Query MCP fails gracefully with error message. Try again later.

**Q: Can I use a local LLM?**
A: Not yet, but extensible architecture allows it in future.

---

## Docker & Deployment

**Q: Do I need Docker?**
A: No, but recommended. Can run standalone with local PostgreSQL.

**Q: What's the Docker image size?**
A: Query MCP: ~300MB, PostgreSQL: ~150MB.

**Q: Can I use Docker Compose?**
A: Yes! We provide `docker-compose.yml` with PostgreSQL + Query MCP.

**Q: How do I backup my database?**
A: With Docker: `docker exec postgres pg_dump ...` or use volumes.

**Q: Is Docker production-ready?**
A: For development yes. For production, see DEPLOYMENT.md for scaling setup.

---

## Integration with Claude

**Q: How do I add Query MCP to Claude?**
A: See INTEGRATION.md. Simple: add MCP server in Claude settings.

**Q: Does it work with Claude Code?**
A: Yes, both Claude Code and Claude Desktop.

**Q: What if Claude can't see the tools?**
A: Check MCP connection status, restart Claude, verify config.

**Q: Can I use Query MCP offline?**
A: No, needs network access to LLM API and PostgreSQL.

**Q: What data does Claude see?**
A: Only table schemas and query results. Schema is sent to LLM.

---

## Performance & Scaling

**Q: How many queries per second can it handle?**
A: Single instance: ~20-30 req/s. With load balancing: scales linearly.

**Q: How much memory does it use?**
A: ~100-200MB for server, depends on query result size.

**Q: Is there caching?**
A: Not yet, but planned for v2.

**Q: Will it slow down my database?**
A: Minimal impact. Only reads, no locking.

**Q: Can I deploy to Kubernetes?**
A: Yes, stateless design works great with K8s.

---

## Costs

**Q: How much does it cost to run?**
A: Only LLM API costs (Z.ai or Anthropic per call).

**Q: Typical costs per month?**
A: Depends on usage. Z.ai is ~$0.01-0.05 per query.

**Q: Any free tier?**
A: Check with Z.ai and Anthropic for their free tiers.

**Q: How can I reduce costs?**
A: Use Z.ai (cheaper) for simple queries, cache results, batch queries.

---

## Troubleshooting

**Q: Query takes forever. Why?**
A: Could be slow database, large result set, or slow LLM. Check logs.

**Q: "API key not configured". What do I do?**
A: Set `export QUERY_MCP_API_KEY="your-key"` before running.

**Q: PostgreSQL won't connect.**
A: Check it's running: `psql -h localhost -U postgres`.

**Q: "Table not found".**
A: Table name is case-sensitive. Check exact name in database.

**Q: Wrong SQL generated.**
A: Rephrase question more specifically. Or try different LLM provider.

---

## Advanced

**Q: Can I extend Query MCP?**
A: Yes! Modular design allows adding new features. See ARCHITECTURE.md.

**Q: How do I add a new LLM provider?**
A: Update `text_to_sql.py` to support new provider API. See code comments.

**Q: Can I use custom database views?**
A: Yes! Create views in PostgreSQL, Query MCP will discover them.

**Q: What about data privacy?**
A: Queries sent to LLM API (Z.ai or Anthropic). Keep sensitive data considerations in mind.

**Q: Can I audit queries?**
A: Not built-in, but PostgreSQL `pg_stat_statements` tracks all queries.

---

## Limitations

**Q: What can't Query MCP do?**
A:
- No write operations (INSERT, UPDATE, DELETE)
- No multi-database queries
- No real-time streaming
- No graph databases
- No authentication per user (yet)

**Q: Why no write operations?**
A: Safety-first design. Prevents accidental data loss.

**Q: Will these be added?**
A: Write operations under consideration for v2. Others on roadmap.

---

## Getting Help

**Q: Where do I find documentation?**
A: See [INDEX.md](INDEX.md) for all docs.

**Q: Still stuck?**
A: Check [TROUBLESHOOTING.md](TROUBLESHOOTING.md) for common issues.

**Q: How do I report a bug?**
A: GitHub issues (coming soon).

**Q: Can I contribute?**
A: Yes! This is an open-source project.

---

## Common Phrases for Claude

Use these to get better results:

```
"Using Z.ai, show me..."
"Using Claude, analyze..."
"Show me [X] sorted by [Y]"
"Count [X] by [Y]"
"Find [X] where [condition]"
"Top 10 [X] by [Y]"
"[X] between [A] and [B]"
```

---

For more information, see the complete documentation in [INDEX.md](INDEX.md).
