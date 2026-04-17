#!/bin/sh

# Write config.json from env vars
mkdir -p /root/.query-mcp
cat > /root/.query-mcp/config.json <<EOF
{
  "database": {
    "host": "${DATABASE_HOST:-localhost}",
    "port": ${DATABASE_PORT:-5432},
    "name": "${DATABASE_NAME:-postgres}",
    "user": "${DATABASE_USER:-postgres}",
    "password": "${DATABASE_PASSWORD:-postgres}"
  },
  "text_to_sql": {
    "llm_api_key": "${QUERY_MCP_API_KEY:-}",
    "llm_provider": "${LLM_PROVIDER:-zai}",
    "llm_model": "${LLM_MODEL:-glm-4-flash}"
  }
}
EOF

# ============================================================
# ALEMBIC MIGRATIONS - ALWAYS RUN BEFORE SERVICE STARTUP
# ============================================================
echo "=========================================="
echo "MIGRATION PHASE: Starting..."
echo "=========================================="

# Determine migration strategy
echo "Checking migration state..."
python - <<'PYEOF'
import json, sys, time
from pathlib import Path
import psycopg2

cfg = json.loads((Path.home() / ".query-mcp/config.json").read_text())
db = cfg["database"]

# Retry database connection with exponential backoff
max_retries = 5
conn = None
for attempt in range(1, max_retries + 1):
    try:
        conn = psycopg2.connect(
            host=db["host"], port=int(db["port"]),
            dbname=db["name"], user=db["user"], password=db["password"],
            connect_timeout=10
        )
        print(f"✅ Database connected on attempt {attempt}")
        break
    except Exception as e:
        print(f"⚠️  DB connection attempt {attempt}/{max_retries} failed: {e}")
        if attempt < max_retries:
            wait_time = 2 ** attempt
            print(f"   Retrying in {wait_time}s...")
            time.sleep(wait_time)
        else:
            print("❌ Failed to connect to database after {max_retries} attempts.")
            print("   Will still attempt migrations (may fail).")
            sys.exit(0)

try:
    cur = conn.cursor()

    # Check if alembic_version table exists
    cur.execute("""
        SELECT EXISTS (
            SELECT FROM information_schema.tables
            WHERE table_schema = 'public' AND table_name = 'alembic_version'
        )
    """)
    version_table_exists = cur.fetchone()[0]
    print(f"   alembic_version table exists: {version_table_exists}")

    stamped = False
    if version_table_exists:
        cur.execute("SELECT COUNT(*) FROM alembic_version")
        stamped = cur.fetchone()[0] > 0
        print(f"   alembic_version is tracked: {stamped}")

    # Check for existing schema
    if not stamped:
        cur.execute("""
            SELECT EXISTS (
                SELECT FROM information_schema.tables
                WHERE table_schema = 'public' AND table_name = 'medicine_bid'
            )
        """)
        schema_exists = cur.fetchone()[0]
        print(f"   medicine_bid table exists: {schema_exists}")

        if schema_exists:
            print("⚠️  Schema exists but not tracked by Alembic → STAMP mode")
            cur.close()
            conn.close()
            sys.exit(2)

    print("→ Running UPGRADE mode (new or clean database)")
    cur.close()
    conn.close()
    sys.exit(0)

except Exception as e:
    print(f"❌ Migration check error: {e}")
    if conn:
        conn.close()
    print("→ Attempting UPGRADE mode anyway")
    sys.exit(0)
PYEOF

MIGRATION_MODE=$?

# Always run migrations - either stamp or upgrade
echo ""
if [ "$MIGRATION_MODE" = "2" ]; then
    echo "MIGRATION STRATEGY: STAMP (tables exist, mark as tracked)"
    echo "Running: alembic stamp head"
    alembic stamp head
    MIGRATION_EXIT=$?
else
    echo "MIGRATION STRATEGY: UPGRADE (create/update schema)"
    echo "Running: alembic upgrade head"
    alembic upgrade head
    MIGRATION_EXIT=$?
fi

echo ""
if [ "$MIGRATION_EXIT" = "0" ]; then
    echo "✅ MIGRATIONS SUCCESSFUL"
else
    echo "❌ MIGRATIONS FAILED (exit code: $MIGRATION_EXIT)"
    echo "⚠️  Attempting to start service anyway..."
fi

echo "=========================================="
echo "MIGRATION PHASE: Complete"
echo "=========================================="
echo ""

# Start server
exec python -u src/server.py http ${PORT:-8080}
