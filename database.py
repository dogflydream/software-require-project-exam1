"""SQLite 数据库连接与初始化（绿循校园）。"""
import sqlite3
from pathlib import Path

DB_PATH = Path(__file__).parent / "campus.db"


def get_db() -> sqlite3.Connection:
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    conn.execute("PRAGMA foreign_keys = ON")
    return conn


def init_db() -> None:
    """自动建表并注入种子数据。"""
    conn = get_db()
    with open(Path(__file__).parent / "schema.sql", "r", encoding="utf-8") as f:
        conn.executescript(f.read())
    conn.commit()
    conn.close()
