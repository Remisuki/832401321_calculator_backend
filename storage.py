"""SQLite 存储，兼容初版 calculation_history 表及其已有数据。"""

from contextlib import contextmanager
from datetime import datetime, timezone
from pathlib import Path
import sqlite3


@contextmanager
def connect(database_path):
    """每次操作独立连接，完成后提交，并显式关闭文件连接。"""
    connection = sqlite3.connect(database_path, timeout=10)
    connection.row_factory = sqlite3.Row
    try:
        with connection:
            yield connection
    finally:
        connection.close()


def initialize_database(database_path):
    Path(database_path).parent.mkdir(parents=True, exist_ok=True)
    with connect(database_path) as connection:
        connection.execute(
            """
            CREATE TABLE IF NOT EXISTS calculation_history (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                expression TEXT NOT NULL,
                result TEXT NOT NULL,
                created_at TEXT NOT NULL
            )
            """
        )


def save_history(database_path, expression, result):
    created_at = datetime.now(timezone.utc).isoformat()
    with connect(database_path) as connection:
        cursor = connection.execute(
            "INSERT INTO calculation_history (expression, result, created_at) "
            "VALUES (?, ?, ?)",
            (expression, result, created_at),
        )
        history_id = cursor.lastrowid
    return {
        "id": history_id,
        "expression": expression,
        "result": result,
        "created_at": created_at,
    }


def get_history(database_path, limit, offset):
    with connect(database_path) as connection:
        # 两次读取处于同一事务，条数与记录保持同一个数据库快照。
        connection.execute("BEGIN")
        total = connection.execute(
            "SELECT COUNT(*) FROM calculation_history"
        ).fetchone()[0]
        records = connection.execute(
            "SELECT id, expression, result, created_at "
            "FROM calculation_history ORDER BY id DESC LIMIT ? OFFSET ?",
            (limit, offset),
        ).fetchall()
    return {
        "success": True,
        "records": [dict(record) for record in records],
        "total": total,
        "limit": limit,
        "offset": offset,
    }


def delete_history(database_path, history_id):
    with connect(database_path) as connection:
        cursor = connection.execute(
            "DELETE FROM calculation_history WHERE id = ?", (history_id,)
        )
        return cursor.rowcount > 0
