"""Cloud API: Flask + Gunicorn + persistent PostgreSQL/Neon storage."""

import json
import os
import re
import sqlite3

from flask import Flask, jsonify, request
import psycopg

from calculator import CalculationError, calculate_expression
import postgres_storage


def create_app(config=None):
    app = Flask(__name__)
    app.json.ensure_ascii = False
    app.config.update(
        DATABASE_URL=os.environ.get("DATABASE_URL", ""),
        ALLOWED_ORIGINS=os.environ.get(
            "ALLOWED_ORIGINS",
            "http://localhost:5500,http://127.0.0.1:5500",
        ),
        MAX_CONTENT_LENGTH=4096,
        STORAGE=postgres_storage,
    )
    if config:
        app.config.update(config)
    configured_origins = app.config["ALLOWED_ORIGINS"]
    if isinstance(configured_origins, str):
        configured_origins = configured_origins.split(",")
    allowed_origins = {origin.strip().rstrip("/")
                       for origin in configured_origins if origin.strip()}
    database_url = app.config["DATABASE_URL"]
    store = app.config["STORAGE"]
    store.initialize_database(database_url)

    def failure(status, code, message):
        return jsonify(success=False, code=code, message=message), status

    @app.before_request
    def check_origin():
        origin = request.headers.get("Origin")
        if origin and origin not in allowed_origins:
            return failure(403, "ORIGIN_NOT_ALLOWED", "该网页来源不在允许列表中。")
        if request.method == "OPTIONS" and request.url_rule is not None:
            return "", 204

    @app.after_request
    def response_headers(response):
        response.headers["Cache-Control"] = "no-store"
        response.headers["X-Content-Type-Options"] = "nosniff"
        response.vary.add("Origin")
        origin = request.headers.get("Origin")
        if origin in allowed_origins:
            response.headers["Access-Control-Allow-Origin"] = origin
            response.headers["Access-Control-Allow-Methods"] = (
                "GET, POST, DELETE, OPTIONS"
            )
            response.headers["Access-Control-Allow-Headers"] = "Content-Type"
        return response

    @app.errorhandler(CalculationError)
    def invalid_expression(error):
        return failure(400, "INVALID_EXPRESSION", str(error))

    def database_failure(error):
        # Keep database URLs and passwords out of response bodies and logs.
        app.logger.error("Database operation failed (%s)", type(error).__name__)
        return failure(500, "DATABASE_ERROR", "历史记录暂时无法读写，请稍后重试。")

    app.register_error_handler(psycopg.Error, database_failure)
    app.register_error_handler(sqlite3.Error, database_failure)

    @app.errorhandler(413)
    def too_large(error):
        return failure(413, "BODY_TOO_LARGE", "请求内容过大。")

    @app.errorhandler(404)
    def not_found(error):
        return failure(404, "NOT_FOUND", "接口或记录地址不存在。")

    @app.errorhandler(405)
    def wrong_method(error):
        response, status = failure(405, "METHOD_NOT_ALLOWED", "该接口不支持此请求方法。")
        response.headers["Allow"] = ", ".join(sorted(error.valid_methods or []))
        return response, status

    @app.errorhandler(400)
    def bad_request(error):
        return failure(400, "INVALID_BODY", "请求内容不正确。")

    @app.get("/api/health")
    def health():
        return jsonify(status="ok")

    @app.post("/api/calculate")
    def calculate():
        if request.mimetype != "application/json":
            return failure(415, "UNSUPPORTED_MEDIA_TYPE", "请使用 JSON 格式提交表达式。")
        try:
            body = json.loads(request.get_data().decode("utf-8"))
        except (ValueError, UnicodeDecodeError, RecursionError):
            return failure(400, "INVALID_JSON", "JSON 格式不正确。")
        if not isinstance(body, dict):
            return failure(400, "INVALID_BODY", "请求必须是包含 expression 的 JSON 对象。")
        expression, result = calculate_expression(body.get("expression"))
        saved = store.save_history(database_url, expression, result)
        return jsonify(success=True, **saved), 201

    @app.get("/api/history")
    def history():
        try:
            limit = int(request.args.get("limit", "10"))
            offset = int(request.args.get("offset", "0"))
            if not 1 <= limit <= 100 or not 0 <= offset <= 2**63 - 1:
                raise ValueError()
        except ValueError:
            return failure(400, "INVALID_PAGE", "分页参数不正确。")
        return jsonify(store.get_history(database_url, limit, offset))

    @app.delete("/api/history/<history_id>")
    def delete_history(history_id):
        if not re.fullmatch(r"[1-9][0-9]{0,18}", history_id):
            return failure(404, "NOT_FOUND", "这条记录不存在或已经被删除。")
        record_id = int(history_id)
        if record_id > 2**63 - 1 or not store.delete_history(database_url, record_id):
            return failure(404, "NOT_FOUND", "这条记录不存在或已经被删除。")
        return jsonify(success=True)

    return app
