"""Database service layer for Query MCP.

Provides connection management, schema introspection, and query execution
with proper resource cleanup via context managers.
"""

import json
from contextlib import contextmanager
from pathlib import Path
from typing import Any, Optional

import psycopg2
import psycopg2.extras


CONFIG_FILE = Path.home() / ".query-mcp" / "config.json"

DEFAULT_DB = {
    "host": "localhost",
    "port": 5432,
    "name": "postgres",
    "user": "postgres",
    "password": "postgres",
}


class DatabaseService:
    """Manages PostgreSQL connections and query execution."""

    def __init__(
        self,
        host: str,
        port: int,
        name: str,
        user: str,
        password: str,
    ):
        self.host = host
        self.port = port
        self.name = name
        self.user = user
        self.password = password

    @classmethod
    def from_config(cls) -> "DatabaseService":
        """Create instance from config file or defaults."""
        if CONFIG_FILE.exists():
            with open(CONFIG_FILE) as f:
                db = json.load(f).get("database", DEFAULT_DB)
        else:
            db = DEFAULT_DB.copy()
        return cls(
            host=db["host"],
            port=int(db["port"]),
            name=db["name"],
            user=db["user"],
            password=db["password"],
        )

    @contextmanager
    def connection(self):
        """Yield a psycopg2 connection, auto-close on exit."""
        conn = psycopg2.connect(
            host=self.host,
            port=self.port,
            database=self.name,
            user=self.user,
            password=self.password,
        )
        try:
            yield conn
        finally:
            conn.close()

    @contextmanager
    def cursor(self, dict_cursor: bool = False):
        """Yield a cursor inside a managed connection."""
        factory = psycopg2.extras.RealDictCursor if dict_cursor else None
        with self.connection() as conn:
            cur = conn.cursor(cursor_factory=factory)
            try:
                yield cur
                conn.commit()
            except Exception:
                conn.rollback()
                raise
            finally:
                cur.close()

    # ------------------------------------------------------------------
    # Schema introspection
    # ------------------------------------------------------------------

    def get_table_schema(self, table_name: str) -> str:
        """Return human-readable schema string for a table."""
        with self.cursor() as cur:
            cur.execute(
                """
                SELECT column_name, data_type
                FROM information_schema.columns
                WHERE table_name = %s
                ORDER BY ordinal_position
                """,
                (table_name,),
            )
            columns = cur.fetchall()

        if not columns:
            raise ValueError(f"Table '{table_name}' not found or has no columns")

        lines = [f"Table: {table_name}", "Columns:"]
        for col_name, col_type in columns:
            lines.append(f"  - {col_name}: {col_type}")
        return "\n".join(lines)

    def list_tables(self) -> list[str]:
        """Return all user tables in public schema."""
        with self.cursor() as cur:
            cur.execute(
                """
                SELECT table_name
                FROM information_schema.tables
                WHERE table_schema = 'public'
                  AND table_type = 'BASE TABLE'
                ORDER BY table_name
                """
            )
            return [row[0] for row in cur.fetchall()]

    # ------------------------------------------------------------------
    # Query execution
    # ------------------------------------------------------------------

    def execute_query(
        self,
        sql: str,
        params: Optional[tuple] = None,
        limit: int = 100,
    ) -> dict[str, Any]:
        """Execute a SELECT query and return results as list of dicts.

        Args:
            sql: SQL query string (SELECT only for safety).
            params: Optional bind parameters.
            limit: Max rows. LIMIT appended if missing from query.

        Returns:
            Dict with success, results, row_count, error.
        """
        try:
            sql = sql.rstrip().rstrip(";")
            if "LIMIT" not in sql.upper():
                sql = f"{sql} LIMIT {limit}"

            with self.cursor(dict_cursor=True) as cur:
                cur.execute(sql, params)
                rows = cur.fetchall()

            return {
                "success": True,
                "results": [dict(r) for r in rows],
                "row_count": len(rows),
                "error": None,
            }
        except psycopg2.Error as e:
            return {
                "success": False,
                "results": None,
                "row_count": 0,
                "error": f"Query execution failed: {e}",
            }

    def execute_write(self, sql: str, params: Optional[tuple] = None) -> int:
        """Execute an INSERT/UPDATE/DELETE and return affected row count."""
        with self.cursor() as cur:
            cur.execute(sql, params)
            return cur.rowcount

    # ------------------------------------------------------------------
    # Convenience helpers
    # ------------------------------------------------------------------

    def fetch_all(
        self,
        table: str,
        where: Optional[str] = None,
        params: Optional[tuple] = None,
        limit: int = 100,
    ) -> dict[str, Any]:
        """Fetch rows from a table with optional WHERE clause."""
        sql = f"SELECT * FROM {table}"
        if where:
            sql += f" WHERE {where}"
        return self.execute_query(sql, params, limit)

    def fetch_one(
        self,
        table: str,
        where: str,
        params: Optional[tuple] = None,
    ) -> Optional[dict]:
        """Fetch a single row or None."""
        result = self.execute_query(
            f"SELECT * FROM {table} WHERE {where}",
            params,
            limit=1,
        )
        if result["success"] and result["results"]:
            return result["results"][0]
        return None

    def count(self, table: str, where: Optional[str] = None, params: Optional[tuple] = None) -> int:
        """Return row count for a table."""
        sql = f"SELECT COUNT(*) FROM {table}"
        if where:
            sql += f" WHERE {where}"
        with self.cursor() as cur:
            cur.execute(sql, params)
            return cur.fetchone()[0]

    # ------------------------------------------------------------------
    # Query history
    # ------------------------------------------------------------------

    def log_query(
        self,
        user_message: str,
        table_name: Optional[str] = None,
        generated_sql: Optional[str] = None,
        success: bool = False,
        row_count: int = 0,
        error: Optional[str] = None,
        llm_provider: Optional[str] = None,
        llm_model: Optional[str] = None,
        execution_time_ms: Optional[int] = None,
        session_id: Optional[str] = None,
    ) -> int:
        """Insert a record into query_history. Returns the new row id."""
        with self.cursor() as cur:
            cur.execute(
                """
                INSERT INTO query_history
                    (session_id, user_message, table_name, generated_sql,
                     success, row_count, error, llm_provider, llm_model,
                     execution_time_ms)
                VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s)
                RETURNING id
                """,
                (
                    session_id, user_message, table_name, generated_sql,
                    success, row_count, error, llm_provider, llm_model,
                    execution_time_ms,
                ),
            )
            return cur.fetchone()[0]

    def get_query_history(
        self,
        limit: int = 50,
        session_id: Optional[str] = None,
        success_only: bool = False,
    ) -> list[dict]:
        """Fetch recent query history records."""
        sql = "SELECT * FROM query_history WHERE 1=1"
        params: list = []
        if session_id:
            sql += " AND session_id = %s"
            params.append(session_id)
        if success_only:
            sql += " AND success = TRUE"
        sql += " ORDER BY created_at DESC LIMIT %s"
        params.append(limit)

        result = self.execute_query(sql, tuple(params), limit=limit)
        return result.get("results", [])
