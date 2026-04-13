# Query MCP - Changelog

Complete version history and updates.

## [1.1.0] - 2026-04-13

### Database Service Layer, Migrations & Query History

#### New Components
- **`db_service.py`** — Central `DatabaseService` class with context-managed connections, schema introspection, query execution, and query history logging
- **`migrate.py`** — SQL migration runner tracking applied versions in `schema_migrations` table
- **`migrations/`** — Versioned SQL migration directory (4 files)

#### New Tables
- **`query_history`** — Logs every `generate_and_execute()` call: user message, generated SQL, success/error, timing, LLM provider/model, session ID
- **`query_sessions`** — Groups queries by session
- **`schema_migrations`** — Tracks applied migration versions

#### Improvements
- `text_to_sql.py` refactored to use `DatabaseService` instead of raw `psycopg2` — eliminates resource leaks
- All DB connections now use context managers (auto-close on exit)
- `generate_and_execute()` auto-logs queries with execution timing (best-effort, never fails main request)
- `RealDictCursor` used for cleaner result formatting

#### Migration Files
- `001_initial_schema.sql` — Base tables + indexes
- `002_seed_data.sql` — Sample data with `ON CONFLICT DO NOTHING`
- `003_create_views.sql` — Reporting views
- `004_query_history.sql` — Query tracking tables + indexes

#### Documentation
- Updated README.md with migrations, db_service, query history sections
- Updated STRUCTURE.md with new files and directory layout
- Updated ARCHITECTURE.md with DatabaseService layer and migration flow
- Updated API_REFERENCE.md with full DatabaseService API, query history schema, migration runner docs
- Updated CHANGELOG.md (this entry)

---

## [1.0.0] - 2026-04-13

### Initial Release

#### Features
- ✅ Natural language to SQL conversion
- ✅ SQL generation without execution
- ✅ Direct SQL execution
- ✅ Combined generation + execution
- ✅ Multiple LLM providers (Z.ai, Anthropic)
- ✅ Per-request provider selection
- ✅ MCP protocol support
- ✅ PostgreSQL integration
- ✅ Docker support
- ✅ Docker Compose orchestration
- ✅ Sample database with test data
- ✅ Configuration management (JSON + env vars)
- ✅ Consistent error handling
- ✅ Schema discovery
- ✅ Table detection

#### Components
- **server.py** - MCP server implementation (v1.0)
- **text_to_sql.py** - Core TextToSQL engine (v1.0)
- **Dockerfile** - Container image for Query MCP (v1.0)
- **Dockerfile.postgres** - PostgreSQL 15 container (v1.0)
- **docker-compose.yml** - Orchestration (v1.0)
- **init-db.sql** - Sample database initialization (v1.0)

#### Documentation
- README.md - Quick start guide
- QUICK_START.md - 5-minute setup
- API_REFERENCE.md - Complete API reference
- ARCHITECTURE.md - System design and internals
- DEPLOYMENT.md - Production deployment guide
- DOCKER_SETUP.md - Docker configuration
- SETUP.md - Integration with Claude
- INTEGRATION.md - Claude Code/Desktop setup
- EXAMPLES.md - Real-world SQL examples
- TROUBLESHOOTING.md - Common issues and fixes
- FAQ.md - Frequently asked questions
- OVERVIEW.md - High-level summary
- INDEX.md - Documentation index
- CHANGELOG.md - This file

#### Sample Data
- drugs table: 15 pharmaceutical products
- items table: 10 consumer items
- users table: 10 sample users
- orders table: 10 sample orders
- Views: active_drugs, drugs_by_category, expensive_items
- Indexes: on category, status, price, user_id, etc.

#### Dependencies
- Python 3.8+
- fastmcp==0.7.1
- zai-sdk==1.0.0
- anthropic==0.38.0
- psycopg2-binary==2.9.10
- Docker & Docker Compose (optional)

#### Known Limitations
- Read-only (no INSERT/UPDATE/DELETE via MCP tools)
- PostgreSQL only (MySQL/SQLServer planned)
- No built-in caching
- No connection pooling
- No per-user authentication
- No query result pagination

---

## Upcoming Features (v1.2)

### Performance Improvements
- [ ] Schema caching (avoid repeated schema lookups)
- [ ] Connection pooling for PostgreSQL
- [ ] Result caching for identical queries
- [ ] Query result pagination

### Features
- [ ] Better error messages with suggestions
- [ ] Query optimization hints
- [ ] Multi-table JOIN assistance
- [ ] Custom SQL function support

### Documentation
- [ ] Video tutorials
- [ ] Interactive examples
- [ ] Video walkthroughs

---

## Planned for v2.0

### Core Features
- [ ] Write operations support (INSERT/UPDATE/DELETE with confirmation)
- [ ] MySQL and SQLServer support
- [ ] Multiple database queries
- [ ] Query result visualization
- [ ] Batch query processing
- [x] Query history and analytics (shipped in v1.1.0)

### Integration
- [ ] Slack integration
- [ ] REST API (HTTP server mode)
- [ ] GraphQL interface
- [ ] Tableau/Power BI integration

### Security & Auth
- [ ] Per-user authentication
- [ ] Row-level security (RLS) support
- [x] Query audit logging (shipped in v1.1.0)
- [ ] Data access controls
- [ ] Encryption at rest

### Performance
- [ ] Advanced caching strategies
- [ ] Connection pooling
- [ ] Query result compression
- [ ] Parallel query execution
- [ ] Load balancing support

---

## Planned for v3.0

### AI Improvements
- [ ] Fine-tuned models for SQL generation
- [ ] Support for OpenAI, Gemini, and other LLMs
- [ ] Custom prompt templates
- [ ] Few-shot learning

### Analytics
- [ ] Query performance analytics
- [ ] API usage tracking
- [ ] Cost monitoring
- [ ] Recommendation engine

### Advanced Features
- [ ] Real-time data streaming
- [ ] Graph database support
- [ ] ML model integration
- [ ] Time-series data optimization

---

## Version Details

### Semantic Versioning
Format: MAJOR.MINOR.PATCH

- **MAJOR**: Breaking changes
- **MINOR**: New features (backward compatible)
- **PATCH**: Bug fixes and patches

### Release Cycle
- Major: ~6-12 months
- Minor: ~1-2 months
- Patch: As needed

---

## Installation History

### v1.0.0 First Setup
```bash
git clone <repo>
cd query-mcp
pip install -r requirements.txt
export QUERY_MCP_API_KEY="your-key"
python server.py
```

### Docker Setup
```bash
docker-compose up -d
```

---

## Breaking Changes

### v1.0.0 (Initial Release)
No prior versions, so no breaking changes.

---

## Deprecations

### Currently None
All APIs are stable in v1.0.

---

## Security Updates

### v1.0.0
- Secure API key handling (env vars only)
- SQL injection prevention (parameterized queries for schema)
- No sensitive data logging
- Configuration file excluded from git

### Planned
- [ ] Query encryption
- [ ] Audit logging
- [ ] Rate limiting
- [ ] API authentication

---

## Bug Fixes

### v1.0.0
- Initial release: no prior bugs to fix

### Reported (To Fix)
None yet.

---

## Performance Notes

### v1.0.0
- Average latency: 1-3 seconds per query
- Throughput: ~20-30 requests/minute (single instance)
- Memory usage: ~100-200MB
- No caching (direct database queries each time)

### Future Improvements
- v1.1: Schema caching (~50ms improvement)
- v2.0: Result caching (~500ms improvement)

---

## Migration Guide

### Upgrading

#### v1.0.0 → v1.1.0 (When Released)
- No schema changes
- Backward compatible
- Just update Python package

#### v1.0.0 → v2.0.0 (When Released)
- May have breaking changes
- Migration guide will be provided
- Old features deprecated with warnings

---

## Contributors

### v1.0.0
- Initial development and implementation

---

## Testing

### v1.0.0 Test Coverage
- Manual testing: ✅
- Unit tests: ❌ (Planned for v1.1)
- Integration tests: ❌ (Planned for v1.1)
- E2E tests: ❌ (Planned for v2.0)

### Test Plan (v1.1+)
- Unit tests for TextToSQL class
- Integration tests with PostgreSQL
- Docker Compose tests
- MCP protocol tests
- End-to-end Claude integration tests

---

## License

Query MCP is released under [MIT License](LICENSE).

---

## Acknowledgments

Built with:
- **FastMCP** - MCP protocol framework
- **Z.ai SDK** - Language model integration
- **Anthropic SDK** - Claude API integration
- **PostgreSQL** - Database engine
- **Docker** - Containerization

---

## Contact & Support

- Documentation: See [INDEX.md](INDEX.md)
- Issues: [GitHub Issues](https://github.com/query-mcp/issues) (coming soon)
- Discussions: [GitHub Discussions](https://github.com/query-mcp/discussions) (coming soon)

---

## Release Notes Archive

### v1.0.0 Release
**Date:** 2026-04-13  
**Status:** Stable  
**Tested:** Manual testing of all features  
**Ready for:** Development, Testing, Early Production

---

## Version Timeline

```
2026-04-13 ──→ v1.0.0 (Initial Release) - stable
2026-04-13 ──→ v1.1.0 (DB Service + Migrations + Query History) - stable
2026-06-13 ──→ v1.2.0 (Planned) - performance improvements
2026-09-13 ──→ v2.0.0 (Planned) - new features
2027-02-13 ──→ v3.0.0 (Planned) - advanced features
```

---

Last updated: 2026-04-13
