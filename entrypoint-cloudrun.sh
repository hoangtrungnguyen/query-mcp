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

# Run Alembic migrations
# If schema tables already exist but alembic_version is unset,
# stamp as head to avoid re-creating existing tables.
echo "Checking migration state..."
python - <<'PYEOF'
import json, sys, time
from pathlib import Path
import psycopg2

cfg = json.loads((Path.home() / ".query-mcp/config.json").read_text())
db = cfg["database"]

# Retry database connection with exponential backoff
max_retries = 3
conn = None
for attempt in range(1, max_retries + 1):
    try:
        conn = psycopg2.connect(
            host=db["host"], port=int(db["port"]),
            dbname=db["name"], user=db["user"], password=db["password"],
            connect_timeout=5
        )
        break
    except Exception as e:
        print(f"DB connection attempt {attempt}/{max_retries} failed: {e}")
        if attempt < max_retries:
            wait_time = 2 ** attempt
            print(f"Retrying in {wait_time}s...")
            time.sleep(wait_time)
        else:
            print("Failed to connect to database. Will attempt migrations anyway.")
            sys.exit(0)

try:
    cur = conn.cursor()

    # Check if alembic_version table exists and has a revision
    cur.execute("""
        SELECT EXISTS (
            SELECT FROM information_schema.tables
            WHERE table_schema = 'public' AND table_name = 'alembic_version'
        )
    """)
    version_table_exists = cur.fetchone()[0]

    stamped = False
    if version_table_exists:
        cur.execute("SELECT version_num FROM alembic_version")
        result = cur.fetchone()
        stamped = result is not None

    # Exit 0 = run upgrade head; Exit 2 = stamp head (tables exist, not tracked)
    if not stamped:
        # Check if medicine_bid already exists
        cur.execute("""
            SELECT EXISTS (
                SELECT FROM information_schema.tables
                WHERE table_schema = 'public' AND table_name = 'medicine_bid'
            )
        """)
        table_exists = cur.fetchone()[0]
        if table_exists:
            print("Schema exists but not tracked by Alembic — stamping as head.")
            cur.close()
            conn.close()
            sys.exit(2)

    cur.close()
    conn.close()
    sys.exit(0)
except Exception as e:
    print(f"Migration check failed: {e}")
    if conn:
        conn.close()
    sys.exit(0)  # Continue with upgrades even if check fails
PYEOF

EXIT_CODE=$?
if [ "$EXIT_CODE" = "2" ]; then
    echo "Stamping migration as head..."
    alembic stamp head || echo "Warning: alembic stamp head failed"
else
    echo "Running migrations..."
    alembic upgrade head || echo "Warning: alembic upgrade head failed"
fi

echo "Migrations complete."

# Start server
exec python -u src/server.py http ${PORT:-8080}
