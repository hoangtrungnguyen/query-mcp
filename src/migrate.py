"""Database migration runner for Query MCP"""

import os
import sys
import json
from pathlib import Path
from datetime import datetime, timezone

import psycopg2


MIGRATIONS_DIR = Path(__file__).parent.parent / "migrations"
CONFIG_FILE = Path.home() / ".query-mcp" / "config.json"

DEFAULT_DB = {
    "host": "localhost",
    "port": 5432,
    "name": "postgres",
    "user": "postgres",
    "password": "postgres",
}


def _load_db_config() -> dict:
    if CONFIG_FILE.exists():
        with open(CONFIG_FILE) as f:
            return json.load(f).get("database", DEFAULT_DB)
    return DEFAULT_DB.copy()


def _connect():
    db = _load_db_config()
    return psycopg2.connect(
        host=db["host"],
        port=int(db["port"]),
        database=db["name"],
        user=db["user"],
        password=db["password"],
    )


def _ensure_migrations_table(conn):
    with conn.cursor() as cur:
        cur.execute("""
            CREATE TABLE IF NOT EXISTS schema_migrations (
                version VARCHAR(255) PRIMARY KEY,
                applied_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )
        """)
    conn.commit()


def _applied_versions(conn) -> set:
    with conn.cursor() as cur:
        cur.execute("SELECT version FROM schema_migrations ORDER BY version")
        return {row[0] for row in cur.fetchall()}


def _pending_migrations(applied: set) -> list[tuple[str, Path]]:
    """Return sorted list of (version, path) for unapplied migrations."""
    migrations = []
    for f in sorted(MIGRATIONS_DIR.glob("*.sql")):
        version = f.stem  # e.g. "001_initial_schema"
        if version not in applied:
            migrations.append((version, f))
    return migrations


def migrate():
    """Apply all pending migrations."""
    conn = _connect()
    try:
        _ensure_migrations_table(conn)
        applied = _applied_versions(conn)
        pending = _pending_migrations(applied)

        if not pending:
            print("No pending migrations.")
            return

        for version, path in pending:
            print(f"Applying {version}...")
            sql = path.read_text()
            with conn.cursor() as cur:
                cur.execute(sql)
                cur.execute(
                    "INSERT INTO schema_migrations (version) VALUES (%s)",
                    (version,),
                )
            conn.commit()
            print(f"  Applied {version}")

        print(f"\nDone. {len(pending)} migration(s) applied.")
    except Exception as e:
        conn.rollback()
        print(f"Migration failed: {e}", file=sys.stderr)
        sys.exit(1)
    finally:
        conn.close()


def status():
    """Show migration status."""
    conn = _connect()
    try:
        _ensure_migrations_table(conn)
        applied = _applied_versions(conn)
        pending = _pending_migrations(applied)

        print("Applied migrations:")
        for v in sorted(applied):
            print(f"  [x] {v}")

        if pending:
            print("\nPending migrations:")
            for v, _ in pending:
                print(f"  [ ] {v}")
        else:
            print("\nAll migrations applied.")
    finally:
        conn.close()


if __name__ == "__main__":
    cmd = sys.argv[1] if len(sys.argv) > 1 else "migrate"
    if cmd == "migrate":
        migrate()
    elif cmd == "status":
        status()
    else:
        print(f"Usage: python migrate.py [migrate|status]")
        sys.exit(1)
