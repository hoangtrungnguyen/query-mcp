"""Text-to-SQL module using LLM API to convert natural language to SQL queries"""

import json
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
        llm_provider: str = "gemini",
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
            llm_provider: LLM provider (gemini, zai, anthropic)
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

        if llm_provider == "gemini":
            try:
                from google import genai
            except ImportError:
                raise ValueError("google-genai required for Gemini provider. Install: pip install google-genai")
            self.client = genai.Client(api_key=llm_api_key)
            self.model = llm_model or "gemini-2.5-flash"
        elif llm_provider == "zai":
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
            raise ValueError(f"Unsupported LLM provider: {llm_provider}. Use: gemini, zai, anthropic")

    # ------------------------------------------------------------------
    # LLM helper
    # ------------------------------------------------------------------

    def _call_llm(self, system_prompt: str, user_message: str, max_tokens: int = 500) -> str:
        """Call the configured LLM provider and return text response."""
        if self.llm_provider == "gemini":
            from google.genai import types
            response = self.client.models.generate_content(
                model=self.model,
                config=types.GenerateContentConfig(
                    system_instruction=system_prompt,
                    max_output_tokens=max_tokens,
                ),
                contents=user_message,
            )
            return response.text.strip()
        elif self.llm_provider == "zai":
            response = self.client.chat.completions.create(
                model=self.model,
                max_tokens=max_tokens,
                messages=[
                    {"role": "system", "content": system_prompt},
                    {"role": "user", "content": user_message},
                ],
            )
            return response.choices[0].message.content.strip()
        elif self.llm_provider == "anthropic":
            response = self.client.messages.create(
                model=self.model,
                max_tokens=max_tokens,
                system=system_prompt,
                messages=[{"role": "user", "content": user_message}],
            )
            return response.content[0].text.strip()

    # ------------------------------------------------------------------
    # Core methods
    # ------------------------------------------------------------------

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
            Dict with 'success', 'sql', 'error', 'needs_clarification', 'clarification' fields
        """
        try:
            schema = self._get_table_schema(table_name)

            system_prompt = f"""You are a SQL expert. Convert natural language queries to PostgreSQL SQL.
You understand queries in multiple languages including English and Vietnamese.

{schema}

Rules:
- Generate valid PostgreSQL syntax
- Only query the specified table
- Use the exact column names from the schema
- Do not modify data (SELECT only)
- Include LIMIT clause if appropriate

If the query is clear, return ONLY the SQL query — no explanation, no markdown, no code blocks.

If the query is unclear, ambiguous, or cannot be mapped to the table schema, return exactly:
CLARIFY: <your question to the user explaining what is unclear and suggesting how they can rephrase>
Reply the CLARIFY message in the same language as the user's query.

Examples of when to ask for clarification:
- The user references columns that don't exist in the schema
- The query is too vague (e.g., "show me stuff", "cho xem cái gì đó")
- The request is ambiguous (e.g., "show me the best drugs" — best by what metric?)
- The request asks for data not in this table"""

            response = self._call_llm(system_prompt, user_message)

            # Remove markdown code blocks if present
            if response.startswith("```"):
                response = response.split("\n", 1)[1].rsplit("```", 1)[0].strip()

            # Check if LLM is asking for clarification
            if response.upper().startswith("CLARIFY:"):
                clarification = response[len("CLARIFY:"):].strip()
                return {
                    "success": False,
                    "sql": None,
                    "error": None,
                    "needs_clarification": True,
                    "clarification": clarification,
                }

            return {
                "success": True,
                "sql": response,
                "error": None,
                "needs_clarification": False,
                "clarification": None,
            }
        except Exception as e:
            return {
                "success": False,
                "sql": None,
                "error": str(e),
                "needs_clarification": False,
                "clarification": None,
            }

    def summarize_results(
        self,
        user_message: str,
        sql: str,
        results: list,
        row_count: int,
    ) -> str:
        """
        Ask LLM to interpret query results into a natural language answer.

        Args:
            user_message: The original user question
            sql: The SQL that was executed
            results: List of result dicts from the query
            row_count: Number of rows returned

        Returns:
            Natural language summary string
        """
        system_prompt = """You are a helpful data analyst. The user asked a question about their database.
A SQL query was generated and executed. Now summarize the results in clear, natural language.
Reply in the same language as the user's original question.

Rules:
- Answer the user's original question directly
- Include key numbers, names, and insights from the data
- Be concise but complete
- If results are empty, say so clearly
- Format numbers nicely (currency, percentages, etc. where appropriate)
- Do not show SQL or raw JSON — just the answer
- Match the language of the user (e.g., reply in Vietnamese if asked in Vietnamese)"""

        results_text = json.dumps(results[:50], indent=2, default=str) if results else "No results"

        prompt = f"""Original question: {user_message}

SQL executed: {sql}

Results ({row_count} rows):
{results_text}"""

        return self._call_llm(system_prompt, prompt, max_tokens=1000)

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
        if gen_result.get("needs_clarification"):
            self._log(user_message, table_name, None, False, 0,
                      "needs_clarification", session_id, t0)
            return {
                "success": False,
                "sql": None,
                "results": None,
                "row_count": 0,
                "error": None,
                "needs_clarification": True,
                "clarification": gen_result["clarification"],
            }
        if not gen_result["success"]:
            self._log(user_message, table_name, None, False, 0,
                      gen_result["error"], session_id, t0)
            return {
                "success": False,
                "sql": None,
                "results": None,
                "row_count": 0,
                "error": gen_result["error"],
                "needs_clarification": False,
                "clarification": None,
            }

        # Execute SQL
        exec_result = self.execute_query(gen_result["sql"], limit)

        self._log(user_message, table_name, gen_result["sql"],
                  exec_result["success"], exec_result.get("row_count", 0),
                  exec_result["error"], session_id, t0)

        return {
            "success": exec_result["success"],
            "sql": gen_result["sql"],
            "results": exec_result["results"],
            "row_count": exec_result.get("row_count", 0),
            "error": exec_result["error"],
            "needs_clarification": False,
            "clarification": None,
        }

    def ask(
        self,
        user_message: str,
        table_name: str,
        limit: int = 100,
        session_id: str = None,
    ) -> Dict[str, Any]:
        """
        Full pipeline: generate SQL → execute → summarize results → return answer.

        Args:
            user_message: Natural language question
            table_name: PostgreSQL table to query
            limit: Max rows to return
            session_id: Optional session id for history tracking

        Returns:
            Dict with 'success', 'sql', 'results', 'row_count', 'answer',
            'needs_clarification', 'clarification', 'error'
        """
        t0 = time.monotonic()

        # Step 1: Generate SQL
        gen_result = self.generate_sql(user_message, table_name)
        if gen_result.get("needs_clarification"):
            self._log(user_message, table_name, None, False, 0,
                      "needs_clarification", session_id, t0)
            return {
                "success": False,
                "sql": None,
                "results": None,
                "row_count": 0,
                "answer": None,
                "needs_clarification": True,
                "clarification": gen_result["clarification"],
                "error": None,
            }
        if not gen_result["success"]:
            self._log(user_message, table_name, None, False, 0,
                      gen_result["error"], session_id, t0)
            return {
                "success": False,
                "sql": None,
                "results": None,
                "row_count": 0,
                "answer": None,
                "needs_clarification": False,
                "clarification": None,
                "error": gen_result["error"],
            }

        # Step 2: Execute SQL
        exec_result = self.execute_query(gen_result["sql"], limit)
        if not exec_result["success"]:
            self._log(user_message, table_name, gen_result["sql"], False, 0,
                      exec_result["error"], session_id, t0)
            return {
                "success": False,
                "sql": gen_result["sql"],
                "results": None,
                "row_count": 0,
                "answer": None,
                "needs_clarification": False,
                "clarification": None,
                "error": exec_result["error"],
            }

        # Step 3: Summarize with LLM
        try:
            answer = self.summarize_results(
                user_message,
                gen_result["sql"],
                exec_result["results"],
                exec_result["row_count"],
            )
        except Exception as e:
            answer = None

        self._log(user_message, table_name, gen_result["sql"],
                  True, exec_result["row_count"], None, session_id, t0)

        return {
            "success": True,
            "sql": gen_result["sql"],
            "results": exec_result["results"],
            "row_count": exec_result["row_count"],
            "answer": answer,
            "needs_clarification": False,
            "clarification": None,
            "error": None,
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
