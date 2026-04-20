"""MCP Server for Text-to-SQL functionality - Query MCP"""

import os
import json
import hashlib
import logging
from pathlib import Path
from fastmcp import FastMCP
from text_to_sql import TextToSQL
from db_service import DatabaseService

# Setup logging
logging.basicConfig(
    level=logging.INFO,
    format='[%(levelname)s] %(asctime)s - %(message)s'
)
logger = logging.getLogger(__name__)


# Configuration
CONFIG_FILE = Path.home() / ".query-mcp" / "config.json"

DEFAULT_CONFIG = {
    "database": {
        "host": "localhost",
        "port": 5432,
        "name": "postgres",
        "user": "postgres",
        "password": "postgres"
    },
    "text_to_sql": {
        "llm_api_key": "",
        "llm_provider": "gemini",
        "llm_model": "gemini-2.5-flash"
    }
}


def load_config() -> dict:
    """Load config from file"""
    if CONFIG_FILE.exists():
        with open(CONFIG_FILE) as f:
            return json.load(f)
    return DEFAULT_CONFIG.copy()


def save_config(config: dict):
    """Save config to file"""
    CONFIG_FILE.parent.mkdir(parents=True, exist_ok=True)
    with open(CONFIG_FILE, "w") as f:
        json.dump(config, f, indent=2)


# Initialize MCP server
mcp = FastMCP(
    "Query MCP",
    instructions="Convert natural language queries to PostgreSQL SQL and execute them"
)


def _table_id(table_name: str) -> str:
    """Generate a stable, short ID from a table name."""
    return "src_" + hashlib.md5(table_name.encode()).hexdigest()[:8]


def _find_table_by_id(db: DatabaseService, table_id: str) -> str | None:
    """Reverse-lookup a table name from its generated ID."""
    for name in db.list_tables():
        if _table_id(name) == table_id:
            return name
    return None


def _db_service() -> DatabaseService:
    """Get a DatabaseService from config (no LLM key needed)."""
    config = load_config()
    db = config.get("database", {})
    return DatabaseService(
        host=db.get("host", "localhost"),
        port=int(db.get("port", 5432)),
        name=db.get("name", "postgres"),
        user=db.get("user", "postgres"),
        password=db.get("password", "postgres"),
    )


def _get_table_metadata(db: DatabaseService, table_name: str = None) -> list:
    """Fetch table metadata (row_count, size). If table_name provided, return single row; else all tables."""
    from psycopg2 import sql as pg_sql

    where_clause = "AND t.table_name = %s" if table_name else ""
    params = (table_name,) if table_name else ()

    with db.cursor(dict_cursor=True) as cur:
        query = f"""
            SELECT
                t.table_name,
                COALESCE(s.n_live_tup, 0) AS row_count,
                pg_size_pretty(
                    COALESCE(pg_total_relation_size(c.oid), 0)
                ) AS size
            FROM information_schema.tables t
            LEFT JOIN pg_stat_user_tables s
                ON s.relname = t.table_name
            LEFT JOIN pg_class c
                ON c.relname = t.table_name AND c.relkind = 'r'
            WHERE t.table_schema = 'public'
              AND t.table_type = 'BASE TABLE'
            {where_clause}
            ORDER BY t.table_name
        """
        cur.execute(query, params)
        return cur.fetchall()


def _get_converter(llm_provider: str = None) -> TextToSQL:
    """Helper to get configured TextToSQL instance"""
    config = load_config()

    # Check environment variable first (takes precedence)
    llm_api_key = os.getenv("QUERY_MCP_API_KEY")

    # Fall back to config file
    if not llm_api_key:
        llm_api_key = config.get("text_to_sql", {}).get("llm_api_key")

    if not llm_api_key:
        raise ValueError(
            "LLM API key not configured. "
            f"Set QUERY_MCP_API_KEY environment variable or edit {CONFIG_FILE}"
        )

    db_config = config.get("database", {})
    required_fields = ["host", "port", "name", "user", "password"]
    if not all(db_config.get(k) for k in required_fields):
        raise ValueError(f"Database config incomplete. Required: {', '.join(required_fields)}")

    llm_config = config.get("text_to_sql", {})
    # Use provided provider or fall back to config
    provider = llm_provider or llm_config.get("llm_provider", "gemini")

    return TextToSQL(
        llm_api_key=llm_api_key,
        db_host=db_config.get("host"),
        db_port=int(db_config.get("port")),
        db_name=db_config.get("name"),
        db_user=db_config.get("user"),
        db_password=db_config.get("password"),
        llm_provider=provider,
        llm_model=llm_config.get("llm_model")
    )


@mcp.tool
def generate_sql(user_message: str, table_name: str = None, llm_provider: str = None, session_id: str = None) -> dict:
    """
    Generate SQL query from natural language without executing.

    Args:
        user_message: Natural language query (e.g., "Show me all drugs with price > 100")
        table_name: PostgreSQL table to query from (auto-detects if omitted)
        llm_provider: LLM provider to use - "zai" or "anthropic" (uses config default if None)
        session_id: Optional session id for conversation context (enables follow-up queries)

    Returns:
        Dict with 'success', 'sql', 'error' fields
    """
    try:
        converter = _get_converter(llm_provider)
        result = converter.generate_sql(user_message, table_name, session_id=session_id)
        return result
    except Exception as e:
        return {
            "success": False,
            "sql": None,
            "error": str(e)
        }


@mcp.tool
def execute_sql(sql_query: str, limit: int = 100, llm_provider: str = None) -> dict:
    """
    Execute SQL query and return results.

    Args:
        sql_query: SQL query to execute
        limit: Max rows to return (default: 100)
        llm_provider: LLM provider (not used for execution, but kept for consistency)

    Returns:
        Dict with 'success', 'results', 'row_count', 'error' fields
    """
    try:
        converter = _get_converter(llm_provider)
        result = converter.execute_query(sql_query, limit)
        return result
    except Exception as e:
        return {
            "success": False,
            "results": None,
            "row_count": 0,
            "error": str(e)
        }


@mcp.tool
def text_to_sql_execute(user_message: str, table_name: str = None, limit: int = 100, llm_provider: str = None, session_id: str = None) -> dict:
    """
    Generate SQL from natural language and execute in one step.

    Args:
        user_message: Natural language query (e.g., "Count items by status")
        table_name: PostgreSQL table to query from (auto-detects if omitted)
        limit: Max rows to return (default: 100)
        llm_provider: LLM provider to use - "zai" or "anthropic" (uses config default if None)
        session_id: Optional session id for conversation context (enables follow-up queries)

    Returns:
        Dict with 'success', 'sql', 'results', 'row_count', 'error' fields
    """
    try:
        converter = _get_converter(llm_provider)
        result = converter.generate_and_execute(user_message, table_name, limit, session_id=session_id)
        return result
    except Exception as e:
        return {
            "success": False,
            "sql": None,
            "results": None,
            "row_count": 0,
            "error": str(e)
        }


@mcp.tool
def ask(user_message: str, table_name: str = None, limit: int = 100, llm_provider: str = None, lang: str = None, session_id: str = None) -> dict:
    """
    Ask a question in natural language and get a human-readable answer.

    Full pipeline: generate SQL → execute query → LLM summarizes results.

    Args:
        user_message: Natural language question (e.g., "What are the top 5 most expensive drugs?")
        table_name: PostgreSQL table to query from (auto-detects if omitted)
        limit: Max rows to return (default: 100)
        llm_provider: LLM provider to use - "gemini", "zai", or "anthropic" (uses config default if None)
        lang: Response language (e.g., "vi", "en", "Vietnamese"). Auto-detects from query if None.
        session_id: Optional session id for conversation context (enables follow-up queries)

    Returns:
        Dict with 'success', 'sql', 'results', 'row_count', 'answer', 'error' fields
    """
    try:
        converter = _get_converter(llm_provider)
        result = converter.ask(user_message, table_name, limit, session_id=session_id, lang=lang)
        return result
    except Exception as e:
        return {
            "success": False,
            "sql": None,
            "results": None,
            "row_count": 0,
            "answer": None,
            "error": str(e)
        }


@mcp.resource("config://database")
def get_database_config() -> dict:
    """Get current database configuration (password hidden)"""
    config = load_config()
    db_config = config.get("database", {})
    return {
        "host": db_config.get("host"),
        "port": db_config.get("port"),
        "name": db_config.get("name"),
        "user": db_config.get("user")
    }


@mcp.resource("config://text-to-sql")
def get_text_to_sql_config() -> dict:
    """Get text-to-sql configuration (API key hidden)"""
    config = load_config()
    ttl_config = config.get("text_to_sql", {})
    return {
        "llm_provider": ttl_config.get("llm_provider", "anthropic"),
        "llm_api_key_configured": bool(ttl_config.get("llm_api_key"))
    }


@mcp.prompt
def sql_query_help(query_type: str = "select") -> str:
    """Get help for different types of SQL queries"""
    help_text = {
        "select": "Ask for specific data from a table. Example: 'Show me all drugs with price > 100' or 'Count drugs by category'",
        "filter": "Filter data by conditions. Example: 'Find drugs where status is active' or 'Get items from category X'",
        "aggregate": "Group and count data. Example: 'Count items by category' or 'Get average price by manufacturer'"
    }
    return help_text.get(query_type, str(help_text))


if __name__ == "__main__":
    # Check for API key in environment or config
    api_key = os.getenv("QUERY_MCP_API_KEY")
    if api_key:
        config = load_config()
        config["text_to_sql"]["llm_api_key"] = api_key
        save_config(config)
        print(f"✓ API key loaded from QUERY_MCP_API_KEY")

    # Verify config
    config = load_config()
    if not config.get("text_to_sql", {}).get("llm_api_key"):
        print(f"⚠ Warning: No LLM API key configured")
        print(f"  Set QUERY_MCP_API_KEY environment variable or edit {CONFIG_FILE}")

    import sys
    transport = sys.argv[1] if len(sys.argv) > 1 else "stdio"
    port = int(sys.argv[2]) if len(sys.argv) > 2 else 8001

    print(f"Query MCP Server starting...")
    print(f"Config file: {CONFIG_FILE}")
    print(f"Transport: {transport}")

    if transport == "http":
        # Add REST endpoints for curl usage
        import decimal
        import datetime
        from starlette.requests import Request
        from starlette.responses import JSONResponse
        from starlette.middleware.cors import CORSMiddleware

        class _Encoder(json.JSONEncoder):
            def default(self, o):
                if isinstance(o, decimal.Decimal):
                    return float(o)
                if isinstance(o, (datetime.datetime, datetime.date)):
                    return o.isoformat()
                return super().default(o)

        def _json_response(data, status=200):
            body = json.dumps(data, cls=_Encoder)
            return JSONResponse(content=json.loads(body), status_code=status)

        async def _parse_body(request: Request):
            try:
                return await request.json()
            except Exception:
                return None

        @mcp.custom_route("/api/ask", methods=["POST"])
        async def api_ask(request: Request) -> JSONResponse:
            body = await _parse_body(request)
            logger.info(f"POST /api/ask - Payload: {json.dumps(body) if body else 'None'}")
            if not body or "user_message" not in body:
                return _json_response({"success": False, "error": "Required: user_message"}, 400)
            try:
                converter = _get_converter(body.get("llm_provider"))
                result = converter.ask(body["user_message"], body.get("table_name"), body.get("limit", 100), session_id=body.get("session_id"), lang=body.get("lang"))
                return _json_response(result)
            except Exception as e:
                return _json_response({"success": False, "error": str(e)}, 500)

        @mcp.custom_route("/api/query", methods=["POST"])
        async def api_query(request: Request) -> JSONResponse:
            body = await _parse_body(request)
            logger.info(f"POST /api/query - Payload: {json.dumps(body) if body else 'None'}")
            if not body or "user_message" not in body:
                return _json_response({"success": False, "error": "Required: user_message"}, 400)
            try:
                converter = _get_converter(body.get("llm_provider"))
                result = converter.generate_and_execute(body["user_message"], body.get("table_name"), body.get("limit", 100), session_id=body.get("session_id"), lang=body.get("lang"))
                return _json_response(result)
            except Exception as e:
                return _json_response({"success": False, "error": str(e)}, 500)

        @mcp.custom_route("/api/sql", methods=["POST"])
        async def api_sql(request: Request) -> JSONResponse:
            body = await _parse_body(request)
            logger.info(f"POST /api/sql - Payload: {json.dumps(body) if body else 'None'}")
            if not body or "user_message" not in body:
                return _json_response({"success": False, "error": "Required: user_message"}, 400)
            try:
                converter = _get_converter(body.get("llm_provider"))
                result = converter.generate_sql(body["user_message"], body.get("table_name"), lang=body.get("lang"), session_id=body.get("session_id"))
                return _json_response(result)
            except Exception as e:
                return _json_response({"success": False, "error": str(e)}, 500)

        @mcp.custom_route("/api/execute", methods=["POST"])
        async def api_execute(request: Request) -> JSONResponse:
            body = await _parse_body(request)
            logger.info(f"POST /api/execute - Payload: {json.dumps(body) if body else 'None'}")
            if not body or "sql_query" not in body:
                return _json_response({"success": False, "error": "Required: sql_query"}, 400)
            try:
                converter = _get_converter(body.get("llm_provider"))
                result = converter.execute_query(body["sql_query"], body.get("limit", 100))
                return _json_response(result)
            except Exception as e:
                return _json_response({"success": False, "error": str(e)}, 500)

        @mcp.custom_route("/health", methods=["GET"])
        async def health(request: Request) -> JSONResponse:
            return JSONResponse({"status": "ok"})

        @mcp.custom_route("/health", methods=["OPTIONS"])
        async def health_options(request: Request) -> JSONResponse:
            return JSONResponse({"status": "ok"})

        @mcp.custom_route("/api/health", methods=["GET"])
        async def api_health(request: Request) -> JSONResponse:
            return JSONResponse({"status": "ok"})

        # ------------------------------------------------------------------
        # Tables endpoints
        # ------------------------------------------------------------------

        @mcp.custom_route("/api/tables", methods=["GET"])
        async def api_tables_list(request: Request) -> JSONResponse:
            search = request.query_params.get("search", "").lower()
            status_filter = request.query_params.get("status", "")
            logger.info(f"GET /api/tables - Query params: search='{search}', status='{status_filter}'")
            try:
                db = _db_service()
                rows = _get_table_metadata(db, table_name="medicine_bid")

                result = []
                for row in rows:
                    name = row["table_name"]
                    if search and search not in name.lower():
                        continue
                    result.append({
                        "id": _table_id(name),
                        "name": name,
                        "format": "TABLE",
                        "rows": f"{row['row_count']:,}",
                        "size": row["size"] or "—",
                        "status": "active",
                        "icon": "table_chart",
                        "color": "#adc6ff",
                    })

                if status_filter and status_filter != "active":
                    result = []

                return _json_response({"data": result, "count": len(result)})
            except Exception as e:
                return _json_response({"success": False, "error": str(e)}, 500)

        @mcp.custom_route("/api/tables/{table_id}", methods=["GET"])
        async def api_table_detail(request: Request) -> JSONResponse:
            table_id = request.path_params["table_id"]
            logger.info(f"GET /api/tables/{table_id}")
            try:
                db = _db_service()
                table_name = _find_table_by_id(db, table_id)
                if not table_name:
                    return _json_response({"error": "Table not found"}, 404)

                rows = _get_table_metadata(db, table_name)
                if not rows:
                    return _json_response({"error": "Table not found"}, 404)

                row = rows[0]

                with db.cursor(dict_cursor=True) as cur:
                    cur.execute("""
                        SELECT
                            a.attname                                   AS column_name,
                            pg_catalog.format_type(a.atttypid, a.atttypmod) AS data_type,
                            col_description(c.oid, a.attnum)            AS comment,
                            NOT a.attnotnull                             AS nullable
                        FROM pg_class c
                        JOIN pg_attribute a ON a.attrelid = c.oid
                        WHERE c.relname = %s
                          AND a.attnum > 0
                          AND NOT a.attisdropped
                        ORDER BY a.attnum
                    """, (row["table_name"],))
                    columns = [
                        {
                            "name": col["column_name"],
                            "type": col["data_type"],
                            "comment": col["comment"],
                            "nullable": col["nullable"],
                        }
                        for col in cur.fetchall()
                    ]

                return _json_response({
                    "id": table_id,
                    "name": row["table_name"],
                    "format": "TABLE",
                    "rows": f"{row['row_count']:,}",
                    "size": row["size"] or "—",
                    "status": "active",
                    "icon": "table_chart",
                    "color": "#adc6ff",
                    "columns": columns,
                })
            except Exception as e:
                return _json_response({"success": False, "error": str(e)}, 500)

        @mcp.custom_route("/api/tables/{table_id}/schema", methods=["GET"])
        async def api_table_schema(request: Request) -> JSONResponse:
            table_id = request.path_params["table_id"]
            logger.info(f"GET /api/tables/{table_id}/schema")
            try:
                db = _db_service()
                table_name = _find_table_by_id(db, table_id)
                if not table_name:
                    return _json_response({"error": "Table not found"}, 404)

                with db.cursor(dict_cursor=True) as cur:
                    cur.execute("""
                        SELECT
                            c.ordinal_position,
                            c.column_name,
                            c.data_type,
                            c.is_nullable,
                            COALESCE((
                                SELECT TRUE
                                FROM information_schema.table_constraints tc
                                JOIN information_schema.key_column_usage kcu
                                    ON tc.constraint_name = kcu.constraint_name
                                    AND tc.table_name = kcu.table_name
                                WHERE tc.table_name = c.table_name
                                  AND tc.constraint_type = 'PRIMARY KEY'
                                  AND kcu.column_name = c.column_name
                                LIMIT 1
                            ), FALSE) AS is_primary_key
                        FROM information_schema.columns c
                        WHERE c.table_name = %s
                        ORDER BY c.ordinal_position
                    """, (table_name,))
                    columns = [dict(r) for r in cur.fetchall()]

                return _json_response({
                    "tableId": table_id,
                    "tableName": table_name,
                    "columns": columns,
                })
            except Exception as e:
                return _json_response({"success": False, "error": str(e)}, 500)

        @mcp.custom_route("/api/tables/{table_id}/data", methods=["GET"])
        async def api_table_data(request: Request) -> JSONResponse:
            from psycopg2 import sql as pg_sql
            table_id = request.path_params["table_id"]
            limit = request.query_params.get("limit", "20")
            offset = request.query_params.get("offset", "0")
            sort = request.query_params.get("sort", "")
            order = request.query_params.get("order", "asc")
            logger.info(f"GET /api/tables/{table_id}/data - limit={limit}, offset={offset}, sort='{sort}', order={order}")
            try:
                limit = min(int(request.query_params.get("limit", 20)), 1000)
                offset = max(int(request.query_params.get("offset", 0)), 0)
                sort = request.query_params.get("sort", "")
                order = request.query_params.get("order", "asc").upper()
                if order not in ("ASC", "DESC"):
                    order = "ASC"

                db = _db_service()
                table_name = _find_table_by_id(db, table_id)
                if not table_name:
                    return _json_response({"error": "Table not found"}, 404)

                # Validate sort column against schema to prevent SQL injection
                if sort:
                    with db.cursor() as cur:
                        cur.execute("""
                            SELECT column_name FROM information_schema.columns
                            WHERE table_name = %s
                        """, (table_name,))
                        valid_cols = {r[0] for r in cur.fetchall()}
                    if sort not in valid_cols:
                        sort = ""

                # Total row count (parameterized)
                with db.cursor() as cur:
                    count_sql = pg_sql.SQL("SELECT COUNT(*) FROM {tbl}").format(
                        tbl=pg_sql.Identifier(table_name)
                    )
                    cur.execute(count_sql)
                    total = cur.fetchone()[0]

                # Data query with optional sort (parameterized)
                data_sql = pg_sql.SQL("SELECT * FROM {tbl}").format(
                    tbl=pg_sql.Identifier(table_name)
                )
                if sort:
                    data_sql = pg_sql.SQL("{q} ORDER BY {col} {dir}").format(
                        q=data_sql,
                        col=pg_sql.Identifier(sort),
                        dir=pg_sql.SQL(order)
                    )
                data_sql = pg_sql.SQL("{q} LIMIT %s OFFSET %s").format(q=data_sql)

                with db.cursor(dict_cursor=True) as cur:
                    cur.execute(data_sql, (limit, offset))
                    data_rows = [dict(r) for r in cur.fetchall()]

                return _json_response({
                    "tableId": table_id,
                    "rows": data_rows,
                    "pagination": {
                        "limit": limit,
                        "offset": offset,
                        "total": total,
                        "hasMore": offset + limit < total,
                    },
                })
            except Exception as e:
                return _json_response({"success": False, "error": str(e)}, 500)

        @mcp.custom_route("/api/tables/{table_id}/stats", methods=["GET"])
        async def api_table_stats(request: Request) -> JSONResponse:
            from psycopg2 import sql as pg_sql
            table_id = request.path_params["table_id"]
            logger.info(f"GET /api/tables/{table_id}/stats")
            _DIST_COLORS = ["#4edea3", "#adc6ff", "#ffb3b0", "#ffd280", "#c2c6d6", "#8c909f"]
            _NUMERIC_TYPES = {
                "integer", "bigint", "smallint", "numeric", "decimal",
                "real", "double precision", "money",
            }
            _TEXT_TYPES = {
                "character varying", "varchar", "text", "char", "character", "boolean",
            }
            try:
                db = _db_service()
                table_name = _find_table_by_id(db, table_id)
                if not table_name:
                    return _json_response({"error": "Table not found"}, 404)

                with db.cursor(dict_cursor=True) as cur:
                    cur.execute("""
                        SELECT column_name, data_type
                        FROM information_schema.columns
                        WHERE table_name = %s
                        ORDER BY ordinal_position
                    """, (table_name,))
                    columns = [dict(r) for r in cur.fetchall()]

                # Total row count (parameterized)
                with db.cursor() as cur:
                    count_sql = pg_sql.SQL("SELECT COUNT(*) FROM {tbl}").format(
                        tbl=pg_sql.Identifier(table_name)
                    )
                    cur.execute(count_sql)
                    total_rows = cur.fetchone()[0]

                with db.cursor() as cur:
                    cur.execute(
                        "SELECT pg_size_pretty(pg_total_relation_size(%s))",
                        (table_name,)
                    )
                    size = cur.fetchone()[0] or "—"

                # Numeric summaries (up to 5 columns, parameterized)
                numeric_cols = [
                    c["column_name"] for c in columns
                    if c["data_type"] in _NUMERIC_TYPES
                ][:5]
                numeric_summaries = []
                for col in numeric_cols:
                    with db.cursor() as cur:
                        stats_sql = pg_sql.SQL(
                            "SELECT AVG({c}), MIN({c}), MAX({c}) FROM {tbl}"
                        ).format(
                            c=pg_sql.Identifier(col),
                            tbl=pg_sql.Identifier(table_name)
                        )
                        cur.execute(stats_sql)
                        avg, mn, mx = cur.fetchone()
                    if avg is not None:
                        numeric_summaries.append({
                            "field": col,
                            "avg": float(avg),
                            "min": float(mn),
                            "max": float(mx),
                        })

                # Distributions for low-cardinality text columns (up to 3, parameterized)
                cat_cols = [
                    c["column_name"] for c in columns
                    if c["data_type"] in _TEXT_TYPES
                ][:3]
                distributions = {}
                for col in cat_cols:
                    with db.cursor() as cur:
                        distinct_sql = pg_sql.SQL(
                            "SELECT COUNT(DISTINCT {c}) FROM {tbl}"
                        ).format(
                            c=pg_sql.Identifier(col),
                            tbl=pg_sql.Identifier(table_name)
                        )
                        cur.execute(distinct_sql)
                        if cur.fetchone()[0] > 20:
                            continue
                    with db.cursor(dict_cursor=True) as cur:
                        dist_sql = pg_sql.SQL("""
                            SELECT {c} AS label, COUNT(*) AS count
                            FROM {tbl}
                            WHERE {c} IS NOT NULL
                            GROUP BY {c}
                            ORDER BY COUNT(*) DESC
                            LIMIT 10
                        """).format(
                            c=pg_sql.Identifier(col),
                            tbl=pg_sql.Identifier(table_name)
                        )
                        cur.execute(dist_sql)
                        dist_rows = [dict(r) for r in cur.fetchall()]
                    if dist_rows:
                        distributions[col] = [
                            {
                                "label": str(r["label"]),
                                "count": r["count"],
                                "percent": int(r["count"] * 100 / max(total_rows, 1)),
                                "color": _DIST_COLORS[i % len(_DIST_COLORS)],
                            }
                            for i, r in enumerate(dist_rows)
                        ]

                return _json_response({
                    "tableId": table_id,
                    "totalRows": total_rows,
                    "columnCount": len(columns),
                    "size": size,
                    "format": "PostgreSQL",
                    "numericSummaries": numeric_summaries,
                    "distributions": distributions,
                })
            except Exception as e:
                return _json_response({"success": False, "error": str(e)}, 500)

        # ------------------------------------------------------------------
        # Columns endpoint (autocomplete support)
        # ------------------------------------------------------------------

        @mcp.custom_route("/api/columns/{table_ref}", methods=["GET"])
        async def api_columns(request: Request) -> JSONResponse:
            table_ref = request.path_params["table_ref"]
            logger.info(f"GET /api/columns/{table_ref}")
            try:
                db = _db_service()
                # Accept either a table ID or a plain table name
                table_name = _find_table_by_id(db, table_ref) or table_ref
                with db.cursor() as cur:
                    cur.execute("""
                        SELECT column_name
                        FROM information_schema.columns
                        WHERE table_name = %s
                        ORDER BY ordinal_position
                    """, (table_name,))
                    columns = [r[0] for r in cur.fetchall()]
                if not columns:
                    return _json_response(
                        {"error": f"Table '{table_ref}' not found"}, 404
                    )
                return _json_response({"tableName": table_name, "columns": columns})
            except Exception as e:
                return _json_response({"success": False, "error": str(e)}, 500)

        # ------------------------------------------------------------------
        # Query history endpoint
        # ------------------------------------------------------------------

        @mcp.custom_route("/api/query/history", methods=["GET"])
        async def api_query_history(request: Request) -> JSONResponse:
            session_id = request.query_params.get("conversationId")
            limit = int(request.query_params.get("limit", 50))
            logger.info(f"GET /api/query/history - conversationId='{session_id}', limit={limit}")
            try:
                db = _db_service()
                history = db.get_query_history(limit=limit, session_id=session_id)
                return _json_response({"conversations": history, "count": len(history)})
            except Exception as e:
                return _json_response({"success": False, "error": str(e)}, 500)

        # Add CORS middleware
        http_app = mcp.http_app(transport="streamable-http")
        http_app.add_middleware(
            CORSMiddleware,
            allow_origins=["*"],
            allow_credentials=True,
            allow_methods=["*"],
            allow_headers=["*"],
        )

        import uvicorn
        uvicorn.run(http_app, host="0.0.0.0", port=port)
    else:
        mcp.run()
