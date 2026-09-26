"""Check adapter boundaries without requiring a user's Neon credentials."""

import unittest
from unittest.mock import MagicMock, patch

try:
    import psycopg
    import postgres_storage
except ImportError as error:
    raise unittest.SkipTest("Install requirements-cloud.txt to test PostgreSQL adapter.") from error


class PostgresAdapterTests(unittest.TestCase):
    def test_missing_connection_string_is_rejected(self):
        with patch("postgres_storage.psycopg.connect") as connect:
            for invalid in (None, "", "calculator.db"):
                with self.assertRaises(RuntimeError):
                    postgres_storage.connect(invalid)
            connect.assert_not_called()

    def test_insert_passes_untrusted_expression_as_parameter(self):
        connection = MagicMock()
        database = connection.__enter__.return_value
        expression = "'); DROP TABLE calculation_history; --"
        record = {"id": 12, "expression": expression, "result": "0",
                  "created_at": "2026-01-01T00:00:00+00:00"}
        database.execute.return_value.fetchone.return_value = record
        with patch("postgres_storage.connect", return_value=connection):
            saved = postgres_storage.save_history("unused", expression, "0")
        sql, values = database.execute.call_args.args
        self.assertNotIn(expression, sql)
        self.assertEqual(values[:2], (expression, "0"))
        self.assertEqual(saved, record)

    def test_commit_failure_propagates_instead_of_reporting_success(self):
        connection = MagicMock()
        connection.__enter__.return_value.execute.return_value.fetchone.return_value = {
            "id": 1, "expression": "1+1", "result": "2", "created_at": "test"
        }
        connection.__exit__.side_effect = psycopg.OperationalError("commit failed")
        with patch("postgres_storage.connect", return_value=connection):
            with self.assertRaises(psycopg.OperationalError):
                postgres_storage.save_history("unused", "1+1", "2")
