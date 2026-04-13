"""MCP Server for Text-to-SQL functionality - Query MCP"""

import os
import json
from pathlib import Path
from fastmcp import FastMCP
from text_to_sql import TextToSQL


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
        "llm_provider": "zai",
        "llm_model": "glm-5.1"
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
    provider = llm_provider or llm_config.get("llm_provider", "zai")

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
def generate_sql(user_message: str, table_name: str, llm_provider: str = None) -> dict:
    """
    Generate SQL query from natural language without executing.

    Args:
        user_message: Natural language query (e.g., "Show me all drugs with price > 100")
        table_name: PostgreSQL table to query from
        llm_provider: LLM provider to use - "zai" or "anthropic" (uses config default if None)

    Returns:
        Dict with 'success', 'sql', 'error' fields
    """
    try:
        converter = _get_converter(llm_provider)
        result = converter.generate_sql(user_message, table_name)
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
def text_to_sql_execute(user_message: str, table_name: str, limit: int = 100, llm_provider: str = None) -> dict:
    """
    Generate SQL from natural language and execute in one step.

    Args:
        user_message: Natural language query (e.g., "Count items by status")
        table_name: PostgreSQL table to query from
        limit: Max rows to return (default: 100)
        llm_provider: LLM provider to use - "zai" or "anthropic" (uses config default if None)

    Returns:
        Dict with 'success', 'sql', 'results', 'row_count', 'error' fields
    """
    try:
        converter = _get_converter(llm_provider)
        result = converter.generate_and_execute(user_message, table_name, limit)
        return result
    except Exception as e:
        return {
            "success": False,
            "sql": None,
            "results": None,
            "row_count": 0,
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

    print(f"Query MCP Server starting...")
    print(f"Config file: {CONFIG_FILE}")
    mcp.run()
