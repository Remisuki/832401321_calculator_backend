"""用临时数据库和真实本地 HTTP 请求验证作业功能，不修改个人历史。"""

import http.client
import json
from pathlib import Path
import sqlite3
import tempfile
import threading
import unittest
from unittest.mock import patch

from app import CalculatorHandler, create_server
from calculator import CalculationError, calculate_expression
import storage


class CalculationTests(unittest.TestCase):
    def test_required_arithmetic(self):
        cases = {
            "12+8": "20", "8-3": "5", "5*8": "40", "10/2": "5",
            "1+2*3": "7", "(1+2)*3": "9", "10/2+7": "12",
            "-5+8": "3", "3*-2": "-6", "+5 + -2": "3",
            "-(2+3)": "-5", "1.5+2.25": "3.75",
            "0.1+0.2": "0.3", "0.3-0.2": "0.1", "0.1*0.2": "0.02",
            ".5 + 1.": "1.5", "001+2": "3", "8/4/2": "1",
            "8-3-2": "3", "(2+3)×4÷2": "10", "−2+5": "3", "-0": "0",
        }
        for expression, expected in cases.items():
            with self.subTest(expression=expression):
                self.assertEqual(calculate_expression(expression)[1], expected)

    def test_recurring_decimal_precision(self):
        self.assertEqual(calculate_expression("1/3")[1], "0." + "3" * 28)

    def test_invalid_expressions(self):
        for expression in ("", " ", "1++", "2(3)", "()", "(1+2",
                           "1+2)", "1 2", "1..2", "2**3", "5//2", "2%1"):
            with self.subTest(expression=expression):
                with self.assertRaises(CalculationError):
                    calculate_expression(expression)

    def test_code_and_non_numbers_are_rejected(self):
        for expression in ("True+1", "False", "1e999", "0x10", "1_000",
                           "__import__('os')", "abs(-2)", "[1]", "<script>1</script>"):
            with self.subTest(expression=expression):
                with self.assertRaises(CalculationError):
                    calculate_expression(expression)

    def test_non_string_is_rejected(self):
        for value in (None, 1, True, [], {}):
            with self.assertRaises(CalculationError):
                calculate_expression(value)

    def test_zero_division(self):
        for expression in ("1/0", "1/(2-2)", "1/-0"):
            with self.assertRaisesRegex(CalculationError, "除数"):
                calculate_expression(expression)

    def test_length_depth_and_magnitude_limits(self):
        for expression in ("1" * 201, "(" * 45 + "1" + ")" * 45,
                           "-" * 45 + "1", "9" * 101):
            with self.assertRaises(CalculationError):
                calculate_expression(expression)


class ApiTests(unittest.TestCase):
    def setUp(self):
        self.directory = tempfile.TemporaryDirectory()
        self.database_path = Path(self.directory.name) / "history.db"
        self.log_patch = patch.object(CalculatorHandler, "log_message")
        self.log_patch.start()
        self.start_server()

    def start_server(self):
        self.server = create_server("127.0.0.1", 0, self.database_path)
        self.port = self.server.server_port
        self.thread = threading.Thread(
            target=lambda: self.server.serve_forever(poll_interval=0.02),
            daemon=True,
        )
        self.thread.start()

    def stop_server(self):
        self.server.shutdown()
        self.server.server_close()
        self.thread.join(timeout=2)

    def tearDown(self):
        self.stop_server()
        self.log_patch.stop()
        self.directory.cleanup()

    def request(self, method, path, payload=None, raw=None, headers=None):
        request_headers = {"Content-Type": "application/json"}
        request_headers.update(headers or {})
        body = raw if raw is not None else (
            json.dumps(payload).encode("utf-8") if payload is not None else None
        )
        connection = http.client.HTTPConnection("127.0.0.1", self.port, timeout=5)
        try:
            connection.request(method, path, body=body, headers=request_headers)
            response = connection.getresponse()
            response_body = response.read()
            return (
                response.status,
                json.loads(response_body) if response_body else None,
                dict(response.getheaders()),
            )
        finally:
            connection.close()

    def calculate(self, expression="1+2"):
        return self.request("POST", "/api/calculate", {"expression": expression})

    def test_calculate_and_database_record(self):
        status, data, _ = self.calculate("(1+2)*3")
        self.assertEqual(status, 201)
        self.assertEqual(data["result"], "9")
        self.assertTrue(data["created_at"])
        with storage.connect(self.database_path) as database:
            row = database.execute("SELECT * FROM calculation_history").fetchone()
        self.assertEqual(row["expression"], "(1+2)*3")
        self.assertEqual(row["result"], "9")

    def test_error_does_not_create_history(self):
        for expression in ("1/0", "1++", "True", "<script>1</script>"):
            self.assertEqual(self.calculate(expression)[0], 400)
        self.assertEqual(self.request("GET", "/api/history")[1]["total"], 0)
        self.assertEqual(self.calculate("2+2")[1]["result"], "4")

    def test_invalid_json_shapes(self):
        for raw in (b"[]", b"null", b"true", b"1", b"{", b"\xff"):
            self.assertEqual(
                self.request("POST", "/api/calculate", raw=raw)[0], 400
            )
        for payload in ({}, {"expression": 1}, {"expression": None}):
            self.assertEqual(
                self.request("POST", "/api/calculate", payload)[0], 400
            )

    def test_media_type_and_body_limit(self):
        status, _, _ = self.request(
            "POST", "/api/calculate", raw=b"1+2",
            headers={"Content-Type": "text/plain"},
        )
        self.assertEqual(status, 415)
        self.assertEqual(self.request(
            "POST", "/api/calculate", raw=b"x" * 4097,
        )[0], 413)

    def test_deep_json_is_rejected_without_stopping_service(self):
        nested = b"[" * 1500 + b"0" + b"]" * 1500
        self.assertEqual(self.request(
            "POST", "/api/calculate", raw=nested,
        )[0], 400)
        self.assertEqual(self.calculate("6*7")[1]["result"], "42")

    def test_database_failure_is_not_reported_as_success(self):
        with patch("storage.save_history", side_effect=sqlite3.OperationalError("test")):
            with self.assertLogs("app", level="ERROR"):
                status, data, _ = self.calculate()
        self.assertEqual(status, 500)
        self.assertEqual(data["code"], "DATABASE_ERROR")
        self.assertEqual(self.request("GET", "/api/history")[1]["total"], 0)

    def test_pagination(self):
        ids = [self.calculate(str(value))[1]["id"] for value in range(7)]
        status, page, _ = self.request("GET", "/api/history?limit=5&offset=0")
        self.assertEqual(status, 200)
        self.assertEqual(page["total"], 7)
        self.assertEqual([row["id"] for row in page["records"]], ids[::-1][:5])
        remaining = self.request("GET", "/api/history?limit=5&offset=5")[1]
        self.assertEqual(len(remaining["records"]), 2)

    def test_invalid_pagination_and_ids(self):
        for query in ("limit=0", "limit=101", "offset=-1", "limit=x",
                      "offset=999999999999999999999999"):
            self.assertEqual(self.request("GET", "/api/history?" + query)[0], 400)
        self.assertEqual(self.request("DELETE", "/api/history/0")[0], 404)
        self.assertEqual(self.request(
            "DELETE", "/api/history/9999999999999999999",
        )[0], 404)

    def test_delete_only_requested_record(self):
        first = self.calculate("1+2")[1]["id"]
        second = self.calculate("5*8")[1]["id"]
        self.assertEqual(self.request("DELETE", "/api/history/" + str(first))[0], 200)
        page = self.request("GET", "/api/history")[1]
        self.assertEqual([row["id"] for row in page["records"]], [second])
        self.assertEqual(self.request("DELETE", "/api/history/" + str(first))[0], 404)
        with storage.connect(self.database_path) as database:
            count = database.execute(
                "SELECT COUNT(*) FROM calculation_history WHERE id = ?", (first,)
            ).fetchone()[0]
        self.assertEqual(count, 0)

    def test_persists_after_restart(self):
        saved = self.calculate("0.1+0.2")[1]
        self.stop_server()
        self.start_server()
        page = self.request("GET", "/api/history")[1]
        self.assertEqual(page["records"][0]["id"], saved["id"])
        self.assertEqual(page["records"][0]["result"], "0.3")

    def test_original_database_is_preserved(self):
        self.stop_server()
        with storage.connect(self.database_path) as database:
            database.execute(
                "INSERT INTO calculation_history VALUES (99, '5*8', '40', "
                "'2026-09-23T12:00:00+00:00')"
            )
        self.start_server()
        self.assertEqual(self.request("GET", "/api/history")[1]["records"][0]["id"], 99)

    def test_cors_preflight_has_no_body(self):
        status, body, headers = self.request(
            "OPTIONS", "/api/calculate",
            headers={"Origin": "http://localhost:5500",
                     "Access-Control-Request-Method": "POST"},
        )
        self.assertEqual(status, 204)
        self.assertIsNone(body)
        self.assertEqual(headers["Access-Control-Allow-Origin"], "http://localhost:5500")
        self.assertEqual(headers["Content-Length"], "0")

    def test_disallowed_browser_origin_cannot_write(self):
        status, _, headers = self.request(
            "POST", "/api/calculate", {"expression": "1+2"},
            headers={"Origin": "https://unrelated.example"},
        )
        self.assertEqual(status, 403)
        self.assertNotIn("Access-Control-Allow-Origin", headers)
        self.assertEqual(self.request("GET", "/api/history")[1]["total"], 0)

    def test_health_unknown_route_and_wrong_method(self):
        self.assertEqual(self.request("GET", "/api/health")[1], {"status": "ok"})
        self.assertEqual(self.request("GET", "/unknown")[0], 404)
        status, _, headers = self.request("GET", "/api/calculate")
        self.assertEqual(status, 405)
        self.assertIn("POST", headers["Allow"])


if __name__ == "__main__":
    unittest.main()

