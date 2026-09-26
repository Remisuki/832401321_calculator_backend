"""计算器 HTTP API。本地教学服务器；公网部署限制见 README。"""

from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
import json
import logging
import os
from pathlib import Path
import re
import sqlite3
from urllib.parse import parse_qs, urlparse

from calculator import CalculationError, calculate_expression
import storage

BASE_DIR = Path(__file__).resolve().parent
MAX_BODY_BYTES = 4096
DEFAULT_ORIGINS = ("http://localhost:5500", "http://127.0.0.1:5500")
LOGGER = logging.getLogger(__name__)


class ApiError(Exception):
    def __init__(self, status, code, message):
        super().__init__(message)
        self.status = status
        self.code = code
        self.message = message


class CalculatorHandler(BaseHTTPRequestHandler):
    server_version = "CalculatorAPI/2.0"

    def setup(self):
        super().setup()
        self.connection.settimeout(10)

    def send_json(self, status, payload=None):
        response = (
            b"" if status == 204
            else json.dumps(payload, ensure_ascii=False, allow_nan=False).encode("utf-8")
        )
        self.send_response(status)
        self.send_header("Content-Type", "application/json; charset=utf-8")
        self.send_header("Content-Length", str(len(response)))
        self.send_header("Cache-Control", "no-store")
        self.send_header("X-Content-Type-Options", "nosniff")
        if status == 405:
            self.send_header("Allow", self.allowed_method + ", OPTIONS")
        origin = self.headers.get("Origin")
        self.send_header("Vary", "Origin")
        if origin in self.server.allowed_origins:
            self.send_header("Access-Control-Allow-Origin", origin)
            self.send_header("Access-Control-Allow-Methods", "GET, POST, DELETE, OPTIONS")
            self.send_header("Access-Control-Allow-Headers", "Content-Type")
        self.end_headers()
        if response:
            self.wfile.write(response)

    def read_json(self):
        if self.headers.get("Transfer-Encoding"):
            raise ApiError(400, "INVALID_BODY", "不支持该请求传输方式。")
        try:
            length = int(self.headers.get("Content-Length", "0"))
        except ValueError as error:
            raise ApiError(400, "INVALID_BODY", "请求长度不正确。") from error
        if length < 0:
            raise ApiError(400, "INVALID_BODY", "请求长度不正确。")
        if length > MAX_BODY_BYTES:
            raise ApiError(413, "BODY_TOO_LARGE", "请求内容过大。")
        if self.headers.get_content_type() != "application/json":
            raise ApiError(415, "UNSUPPORTED_MEDIA_TYPE", "请使用 JSON 格式提交表达式。")
        try:
            body = json.loads(self.rfile.read(length).decode("utf-8"))
        except (UnicodeDecodeError, ValueError, RecursionError) as error:
            raise ApiError(400, "INVALID_JSON", "JSON 格式不正确。") from error
        if not isinstance(body, dict):
            raise ApiError(400, "INVALID_BODY", "请求必须是包含 expression 的 JSON 对象。")
        return body

    def handle_api(self):
        try:
            self.route()
        except ApiError as error:
            self.send_json(error.status, {
                "success": False, "code": error.code, "message": error.message,
            })
        except CalculationError as error:
            self.send_json(400, {
                "success": False, "code": "INVALID_EXPRESSION", "message": str(error),
            })
        except sqlite3.Error:
            LOGGER.exception("Database operation failed")
            self.send_json(500, {
                "success": False,
                "code": "DATABASE_ERROR",
                "message": "历史记录暂时无法读写，请稍后重试。",
            })
        except (TimeoutError, ConnectionError):
            LOGGER.warning("Client connection ended or timed out")

    def route(self):
        url = urlparse(self.path)
        path = url.path
        history_match = re.fullmatch(r"/api/history/([1-9][0-9]{0,18})", path)
        methods = {
            "/api/health": "GET",
            "/api/calculate": "POST",
            "/api/history": "GET",
        }
        if history_match:
            method = "DELETE"
        elif path in methods:
            method = methods[path]
        else:
            raise ApiError(404, "NOT_FOUND", "接口或记录地址不存在。")

        origin = self.headers.get("Origin")
        if origin and origin not in self.server.allowed_origins:
            raise ApiError(403, "ORIGIN_NOT_ALLOWED", "该网页来源不在允许列表中。")
        if self.command == "OPTIONS":
            self.send_json(204)
            return
        if self.command != method:
            self.allowed_method = method
            raise ApiError(405, "METHOD_NOT_ALLOWED", "该接口不支持此请求方法。")

        if path == "/api/health":
            self.send_json(200, {"status": "ok"})
        elif path == "/api/calculate":
            expression, result = calculate_expression(self.read_json().get("expression"))
            record = storage.save_history(self.server.database_path, expression, result)
            self.send_json(201, {"success": True, **record})
        elif path == "/api/history":
            params = parse_qs(url.query, keep_blank_values=True)
            try:
                limit = int(params.get("limit", ["10"])[0])
                offset = int(params.get("offset", ["0"])[0])
                if not 1 <= limit <= 100 or not 0 <= offset <= 2**63 - 1:
                    raise ValueError()
            except ValueError as error:
                raise ApiError(400, "INVALID_PAGE", "分页参数不正确。") from error
            self.send_json(200, storage.get_history(
                self.server.database_path, limit, offset,
            ))
        else:
            history_id = int(history_match.group(1))
            if history_id > 2**63 - 1:
                raise ApiError(404, "NOT_FOUND", "这条记录不存在或已经被删除。")
            if not storage.delete_history(self.server.database_path, history_id):
                raise ApiError(404, "NOT_FOUND", "这条记录不存在或已经被删除。")
            self.send_json(200, {"success": True})

    def do_GET(self):
        self.handle_api()

    def do_POST(self):
        self.handle_api()

    def do_DELETE(self):
        self.handle_api()

    def do_OPTIONS(self):
        self.handle_api()

    def do_PUT(self):
        self.handle_api()

    def do_PATCH(self):
        self.handle_api()


def create_server(host, port, database_path, allowed_origins=DEFAULT_ORIGINS):
    storage.initialize_database(database_path)
    server = ThreadingHTTPServer((host, port), CalculatorHandler)
    server.database_path = Path(database_path)
    server.allowed_origins = set(allowed_origins)
    return server


def main():
    host = os.environ.get("HOST", "127.0.0.1")
    port = int(os.environ.get("PORT", "5000"))
    database_path = Path(os.environ.get("DATABASE_PATH", str(BASE_DIR / "calculator.db")))
    origins = tuple(
        value.strip()
        for value in os.environ.get("ALLOWED_ORIGINS", ",".join(DEFAULT_ORIGINS)).split(",")
        if value.strip()
    )
    server = create_server(host, port, database_path, origins)
    print(f"Calculator backend running at http://{host}:{server.server_port}", flush=True)
    print(f"Database: {database_path.resolve()}", flush=True)
    try:
        server.serve_forever()
    except KeyboardInterrupt:
        print("\nServer stopped")
    finally:
        server.server_close()


if __name__ == "__main__":
    main()
