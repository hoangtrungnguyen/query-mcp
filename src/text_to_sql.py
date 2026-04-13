"""Text-to-SQL module using LLM API to convert natural language to SQL queries"""

import time
from typing import Optional, Dict, Any

from db_service import DatabaseService


class TextToSQL:
    """Convert natural language to SQL queries using LLM API"""

    def __init__(
        self,
        llm_api_key: str,
        db_host: str,
        db_port: int,
        db_name: str,
        db_user: str,
        db_password: str,
        llm_provider: str = "zai",
        llm_model: str = None
    ):
        """
        Initialize TextToSQL converter

        Args:
            llm_api_key: API key for LLM provider
            db_host: PostgreSQL host
            db_port: PostgreSQL port
            db_name: Database name
            db_user: Database user
            db_password: Database password
            llm_provider: LLM provider (zai, anthropic)
            llm_model: Model name (auto-detected if None)
        """
        self.llm_provider = llm_provider
        self.llm_api_key = llm_api_key
        self.db = DatabaseService(
            host=db_host,
            port=db_port,
            name=db_name,
            user=db_user,
            password=db_password,
        )

        if llm_provider == "zai":
            try:
                from zai import ZaiClient
            except ImportError:
                raise ValueError("zai-sdk required for Z.ai provider. Install: pip install zai-sdk")
            self.client = ZaiClient(api_key=llm_api_key)
            self.model = llm_model or "glm-5.1"
        elif llm_provider == "anthropic":
            try:
                from anthropic import Anthropic
            except ImportError:
                raise ValueError("anthropic SDK required. Install: pip install anthropic")
            self.client = Anthropic(api_key=llm_api_key)
            self.model = llm_model or "claude-3-5-sonnet-20241022"
        else:
            raise ValueError(f"Unsupported LLM provider: {llm_provider}")

    def _get_table_schema(self, table_name: str) -> str:
        """Get schema information for a table via DatabaseService."""
        return self.db.get_table_schema(table_name)

    def generate_sql(self, user_message: str, table_name: str) -> Dict[str, Any]:
        """
        Generate SQL query from natural language

        Args:
            user_message: Natural language query from user
            table_name: PostgreSQL table to query from

        Returns:
            Dict with 'success', 'sql', 'error' fields
        """
        try:
            # Get table schema
            schema = self._get_table_schema(table_name)

            # Create prompt for LLM
            system_prompt = f"""You are a SQL expert. Convert natural language queries to PostgreSQL SQL.
Always return ONLY the SQL query, no explanation, no markdown, no code blocks.
Do not use backticks or SQL language markers.

{schema}

Rules:
- Generate valid PostgreSQL syntax
- Only query the specified table
- Use the exact column names from the schema
- Do not modify data (SELECT only)
- Include LIMIT clause if appropriate"""

            if self.llm_provider == "zai":
                # Z.ai SDK
                response = self.client.chat.completions.create(
                    model=self.model,
                    max_tokens=500,
                    system=system_prompt,
                    messages=[
                        {
                            "role": "user",
                            "content": user_message
                        }
                    ]
                )
                sql_query = response.choices[0].message.content.strip()
            elif self.llm_provider == "anthropic":
                # Anthropic SDK
                response = self.client.messages.create(
                    model=self.model,
                    max_tokens=500,
                    system=system_prompt,
                    messages=[
                        {
                            "role": "user",
                            "content": user_message
                        }
                    ]
                )
                sql_query = response.content[0].text.strip()

            # Remove markdown code blocks if present
            if sql_query.startswith("```"):
                sql_query = sql_query.split("\n", 1)[1].rsplit("```", 1)[0].strip()

            return {
                "success": True,
                "sql": sql_query,
                "error": None
            }
        except Exception as e:
            return {
                "success": False,
                "sql": None,
                "error": str(e)
            }

    def execute_query(self, sql_query: str, limit: int = 100) -> Dict[str, Any]:
        """
        Execute SQL query and return results via DatabaseService.

        Args:
            sql_query: SQL query to execute
            limit: Max rows to return

        Returns:
            Dict with 'success', 'results', 'error', 'row_count' fields
        """
        return self.db.execute_query(sql_query, limit=limit)

    def generate_and_execute(
        self,
        user_message: str,
        table_name: str,
        limit: int = 100,
        session_id: str = None,
    ) -> Dict[str, Any]:
        """
        Generate SQL and execute in one call

        Args:
            user_message: Natural language query
            table_name: PostgreSQL table to query
            limit: Max rows to return
            session_id: Optional session id for query history tracking

        Returns:
            Dict with 'success', 'sql', 'results', 'error' fields
        """
        t0 = time.monotonic()

        # Generate SQL
        gen_result = self.generate_sql(user_message, table_name)
        if not gen_result["success"]:
            self._log(user_message, table_name, None, False, 0,
                      gen_result["error"], session_id, t0)
            return {
                "success": False,
                "sql": None,
                "results": None,
                "error": gen_result["error"]
            }

        # Execute SQL
        exec_result = self.execute_query(gen_result["sql"], limit)
        elapsed = exec_result.get("row_count", 0)

        self._log(user_message, table_name, gen_result["sql"],
                  exec_result["success"], exec_result.get("row_count", 0),
                  exec_result["error"], session_id, t0)

        return {
            "success": exec_result["success"],
            "sql": gen_result["sql"],
            "results": exec_result["results"],
            "row_count": exec_result.get("row_count", 0),
            "error": exec_result["error"]
        }

    def _log(self, user_message, table_name, sql, success, row_count,
             error, session_id, t0):
        """Best-effort write to query_history."""
        try:
            elapsed_ms = int((time.monotonic() - t0) * 1000)
            self.db.log_query(
                user_message=user_message,
                table_name=table_name,
                generated_sql=sql,
                success=success,
                row_count=row_count,
                error=error,
                llm_provider=self.llm_provider,
                llm_model=self.model,
                execution_time_ms=elapsed_ms,
                session_id=session_id,
            )
        except Exception:
            pass  # never fail the main request for logging
