"""Tests for conversation context feature in TextToSQL.

Validates that session_id-based conversation history is fetched from
query_sessions.messages and injected into LLM prompts.
"""

import sys
import os
import unittest
from unittest.mock import MagicMock, patch

# Add src to path
sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "src"))

# Mock heavy dependencies before importing text_to_sql
sys.modules["psycopg2"] = MagicMock()
sys.modules["psycopg2.extras"] = MagicMock()
sys.modules["psycopg2.sql"] = MagicMock()

from text_to_sql import TextToSQL


def _make_converter():
    """Create a TextToSQL instance with mocked DB and LLM client."""
    converter = TextToSQL.__new__(TextToSQL)
    converter.llm_provider = "gemini"
    converter.llm_api_key = "test-key"
    converter.model = "test-model"
    converter.db = MagicMock()
    converter.client = MagicMock()
    return converter


# ── _get_conversation_context ──────────────────────────────────────


class TestGetConversationContext(unittest.TestCase):

    def test_returns_empty_when_no_session_id(self):
        c = _make_converter()
        self.assertEqual(c._get_conversation_context(None), "")

    def test_returns_empty_when_no_messages(self):
        c = _make_converter()
        c.db.get_session_messages.return_value = []
        self.assertEqual(c._get_conversation_context("s1"), "")

    def test_returns_empty_on_db_error(self):
        c = _make_converter()
        c.db.get_session_messages.side_effect = Exception("DB down")
        self.assertEqual(c._get_conversation_context("s1"), "")

    def test_builds_context_from_messages(self):
        c = _make_converter()
        c.db.get_session_messages.return_value = [
            {"role": "user", "content": "first question", "timestamp": "t1"},
            {"role": "assistant", "sql": "SELECT 1", "answer": "One.", "row_count": 1,
             "success": True, "error": None, "timestamp": "t1"},
            {"role": "user", "content": "second question", "timestamp": "t2"},
            {"role": "assistant", "sql": "SELECT 2", "answer": "Two.", "row_count": 1,
             "success": True, "error": None, "timestamp": "t2"},
        ]
        result = c._get_conversation_context("s1")

        self.assertIn("Previous conversation in this session:", result)
        self.assertIn("User: first question", result)
        self.assertIn("User: second question", result)
        self.assertIn("SQL: SELECT 1", result)
        self.assertIn("Answer: One.", result)
        # Verify order — first before second
        idx1 = result.index("first question")
        idx2 = result.index("second question")
        self.assertLess(idx1, idx2)

    def test_includes_errors(self):
        c = _make_converter()
        c.db.get_session_messages.return_value = [
            {"role": "user", "content": "bad query", "timestamp": "t"},
            {"role": "assistant", "sql": None, "answer": None, "row_count": 0,
             "success": False, "error": "syntax error", "timestamp": "t"},
        ]
        result = c._get_conversation_context("s1")
        self.assertIn("Error: syntax error", result)

    def test_respects_limit(self):
        c = _make_converter()
        # 10 messages, limit to 4
        c.db.get_session_messages.return_value = [
            {"role": "user", "content": f"msg-{i}", "timestamp": "t"} for i in range(10)
        ]
        result = c._get_conversation_context("s1", limit=4)
        # Should only contain last 4 messages (msg-6 through msg-9)
        self.assertNotIn("msg-5", result)
        self.assertIn("msg-6", result)
        self.assertIn("msg-9", result)


# ── generate_sql context injection ────────────────────────────────


class TestGenerateSqlWithContext(unittest.TestCase):

    def test_no_context_without_session_id(self):
        c = _make_converter()
        c.db.get_table_schema.return_value = "CREATE TABLE t (id INT)"

        with patch.object(c, "_call_llm", return_value="SELECT 1") as mock_llm:
            c.generate_sql("count rows", "t", session_id=None)
            prompt = mock_llm.call_args[0][0]
            self.assertNotIn("Previous conversation", prompt)

    def test_context_injected_with_session_id(self):
        c = _make_converter()
        c.db.get_table_schema.return_value = "CREATE TABLE t (id INT, price NUMERIC)"
        c.db.get_session_messages.return_value = [
            {"role": "user", "content": "Show all items", "timestamp": "t"},
            {"role": "assistant", "sql": "SELECT * FROM t", "answer": "42 items.",
             "row_count": 42, "success": True, "error": None, "timestamp": "t"},
        ]

        with patch.object(c, "_call_llm", return_value="SELECT COUNT(*) FROM t") as mock_llm:
            result = c.generate_sql("how many?", "t", session_id="s1")
            prompt = mock_llm.call_args[0][0]
            self.assertIn("Previous conversation in this session:", prompt)
            self.assertIn("User: Show all items", prompt)
            self.assertIn("SQL: SELECT * FROM t", prompt)
            self.assertIn('resolve references like "those"', prompt)
            self.assertTrue(result["success"])


# ── summarize_results context injection ───────────────────────────


class TestSummarizeWithContext(unittest.TestCase):

    def test_no_context_without_session_id(self):
        c = _make_converter()

        with patch.object(c, "_call_llm", return_value="5 items.") as mock_llm:
            c.summarize_results("how many?", "SELECT COUNT(*)", [{"count": 5}], 1)
            prompt = mock_llm.call_args[0][0]
            self.assertNotIn("Previous conversation", prompt)

    def test_context_injected_with_session_id(self):
        c = _make_converter()
        c.db.get_session_messages.return_value = [
            {"role": "user", "content": "Show expensive", "timestamp": "t"},
            {"role": "assistant", "sql": "SELECT * FROM t WHERE price>100",
             "answer": "3 items.", "row_count": 3, "success": True, "error": None, "timestamp": "t"},
        ]

        with patch.object(c, "_call_llm", return_value="3 expensive items.") as mock_llm:
            c.summarize_results(
                "how many?", "SELECT COUNT(*)", [{"count": 3}], 1,
                session_id="s1",
            )
            prompt = mock_llm.call_args[0][0]
            self.assertIn("Previous conversation in this session:", prompt)
            self.assertIn("contextually relevant answers", prompt)


# ── Pipeline wiring ───────────────────────────────────────────────


class TestPipelineWiring(unittest.TestCase):

    def test_ask_passes_session_id_everywhere(self):
        c = _make_converter()

        with patch.object(c, "generate_sql", return_value={
            "success": True, "sql": "SELECT 1", "error": None,
            "needs_clarification": False, "clarification": None,
        }) as mock_gen, \
             patch.object(c, "execute_query", return_value={
                 "success": True, "results": [{"1": 1}], "row_count": 1, "error": None,
             }), \
             patch.object(c, "summarize_results", return_value="Answer") as mock_sum, \
             patch.object(c, "_log"):

            c.ask("test", "t", session_id="sess-abc")
            self.assertEqual(mock_gen.call_args[1]["session_id"], "sess-abc")
            self.assertEqual(mock_sum.call_args[1]["session_id"], "sess-abc")

    def test_generate_and_execute_passes_session_id(self):
        c = _make_converter()

        with patch.object(c, "generate_sql", return_value={
            "success": True, "sql": "SELECT 1", "error": None,
            "needs_clarification": False, "clarification": None,
        }) as mock_gen, \
             patch.object(c, "execute_query", return_value={
                 "success": True, "results": [{"1": 1}], "row_count": 1, "error": None,
             }), \
             patch.object(c, "_log"):

            c.generate_and_execute("test", "t", session_id="sess-xyz")
            self.assertEqual(mock_gen.call_args[1]["session_id"], "sess-xyz")


# ── _log saves to session ────────────────────────────────────────


class TestLogSavesToSession(unittest.TestCase):

    def test_log_calls_save_session_message(self):
        c = _make_converter()
        import time
        t0 = time.monotonic()

        c._log("question", "tbl", "SELECT 1", True, 5, None, "sess-1", t0, answer="Five rows.")

        c.db.save_session_message.assert_called_once_with(
            session_id="sess-1",
            user_message="question",
            table_name="tbl",
            generated_sql="SELECT 1",
            answer="Five rows.",
            row_count=5,
            success=True,
            error=None,
        )

    def test_log_skips_session_save_without_session_id(self):
        c = _make_converter()
        import time
        t0 = time.monotonic()

        c._log("question", "tbl", "SELECT 1", True, 5, None, None, t0)
        c.db.save_session_message.assert_not_called()

    def test_log_does_not_raise_on_session_save_failure(self):
        c = _make_converter()
        c.db.save_session_message.side_effect = Exception("boom")
        import time
        t0 = time.monotonic()

        # Should not raise
        c._log("q", "t", "S", True, 0, None, "s1", t0)


if __name__ == "__main__":
    unittest.main()
