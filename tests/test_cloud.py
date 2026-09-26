"""Exercise cloud routes over real local HTTP using a temporary SQLite store."""

import threading
import unittest
from unittest.mock import patch
import sqlite3

try:
    from werkzeug.serving import WSGIRequestHandler, make_server
    from wsgi import create_app
except ImportError as error:
    raise unittest.SkipTest("Install requirements-cloud.txt to run cloud API tests.") from error

import storage
from tests import test_app as local_tests


class QuietHandler(WSGIRequestHandler):
    def log_request(self, *args, **kwargs):
        pass


class CloudApiTests(local_tests.ApiTests):
    def start_server(self):
        application = create_app({
            "TESTING": True,
            "DATABASE_URL": self.database_path,
            "STORAGE": storage,
            "ALLOWED_ORIGINS": "http://localhost:5500,https://remisuki.github.io",
        })
        self.server = make_server(
            "127.0.0.1", 0, application, request_handler=QuietHandler
        )
        self.port = self.server.server_port
        self.thread = threading.Thread(
            target=lambda: self.server.serve_forever(poll_interval=0.02),
            daemon=True,
        )
        self.thread.start()

    def test_cors_preflight_has_no_body(self):
        status, body, headers = self.request(
            "OPTIONS", "/api/calculate",
            headers={"Origin": "https://remisuki.github.io",
                     "Access-Control-Request-Method": "POST"},
        )
        self.assertEqual(status, 204)
        self.assertIsNone(body)
        self.assertEqual(headers["Access-Control-Allow-Origin"],
                         "https://remisuki.github.io")
        self.assertEqual(headers.get("Content-Length", "0"), "0")

    def test_database_failure_is_not_reported_as_success(self):
        with patch("storage.save_history", side_effect=sqlite3.OperationalError("test")):
            with self.assertLogs("wsgi", level="ERROR"):
                status, data, _ = self.calculate()
        self.assertEqual(status, 500)
        self.assertEqual(data["code"], "DATABASE_ERROR")
        self.assertEqual(self.request("GET", "/api/history")[1]["total"], 0)

    def test_github_pages_origin_can_calculate(self):
        status, data, headers = self.request(
            "POST", "/api/calculate", {"expression": "0.1+0.2"},
            headers={"Origin": "https://remisuki.github.io"},
        )
        self.assertEqual(status, 201)
        self.assertEqual(data["result"], "0.3")
        self.assertEqual(headers["Access-Control-Allow-Origin"],
                         "https://remisuki.github.io")

    def test_repository_path_is_not_part_of_browser_origin(self):
        status, _, _ = self.request(
            "POST", "/api/calculate", {"expression": "1+1"},
            headers={"Origin":
                     "https://remisuki.github.io/832401321_calculator_frontend"},
        )
        self.assertEqual(status, 403)
