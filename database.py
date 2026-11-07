"""SQLite 数据库连接与初始化（绿循校园）。

对外提供三类能力：
- ``get_db()``        —— 原始连接（供需要精细控制的场景使用）
- ``db_session()``    —— 上下文管理器：自动提交 / 回滚 / 关闭，避免连接泄漏
- ``init_db()``       —— 幂等建表并注入种子数据
"""
import secrets
import sqlite3
from contextlib import contextmanager
from pathlib import Path
from typing import Iterator

DB_PATH = Path(__file__).parent / "campus.db"
SCHEMA_PATH = Path(__file__).parent / "schema.sql"

# 单条 SQL 的最长等待时间（毫秒）：SQLite 单写者模型下，写锁冲突时自动重试
BUSY_TIMEOUT_MS = 5000


def get_db() -> sqlite3.Connection:
    """创建连接：行工厂为 Row、开启外键约束与写锁等待。"""
    conn = sqlite3.connect(DB_PATH, timeout=BUSY_TIMEOUT_MS / 1000)
    conn.row_factory = sqlite3.Row
    conn.execute("PRAGMA foreign_keys = ON")
    conn.execute(f"PRAGMA busy_timeout = {BUSY_TIMEOUT_MS}")
    # WAL 提升读写并发（读不阻塞写），NORMAL 同步在本地部署下兼顾安全与速度
    conn.execute("PRAGMA journal_mode = WAL")
    conn.execute("PRAGMA synchronous = NORMAL")
    return conn


@contextmanager
def db_session() -> Iterator[sqlite3.Connection]:
    """事务化连接上下文：正常退出提交，异常回滚，最终必定关闭。"""
    conn = get_db()
    try:
        yield conn
        conn.commit()
    except Exception:
        conn.rollback()
        raise
    finally:
        conn.close()


def add_points(conn: sqlite3.Connection, user_id: int, delta: int, reason: str) -> int:
    """增加/扣减积分并写入积分流水，返回用户新积分。

    扣分场景（delta < 0）使用条件更新，保证并发下不会透支为负余额。
    """
    if delta < 0:
        cur = conn.execute(
            "UPDATE users SET points = points + ? WHERE id = ? AND points + ? >= 0",
            (delta, user_id, delta),
        )
        if cur.rowcount == 0:
            raise ValueError("积分不足")
    else:
        conn.execute("UPDATE users SET points = points + ? WHERE id = ?", (delta, user_id))
    conn.execute(
        "INSERT INTO point_logs (user_id, delta, reason) VALUES (?, ?, ?)",
        (user_id, delta, reason),
    )
    row = conn.execute("SELECT points FROM users WHERE id = ?", (user_id,)).fetchone()
    return row[0] if row else 0


def init_db() -> None:
    """自动建表并注入种子数据（幂等，可重复执行）。"""
    with db_session() as conn:
        conn.executescript(SCHEMA_PATH.read_text(encoding="utf-8"))
        _migrate(conn)


# 增量 6/7 新增列（幂等补齐，兼容已存在的旧库）
MIGRATIONS = [
    ("users", "password_hash", "TEXT"),
    ("users", "avatar", "TEXT"),
    ("users", "bio", "TEXT"),
    ("items", "image", "TEXT"),
    ("items", "review_status", "TEXT DEFAULT 'approved'"),
    ("items", "review_note", "TEXT"),
    ("items", "updated_at", "TEXT"),
]


def _migrate(conn) -> None:
    """为旧库补齐新增列（SQLite 无 ADD COLUMN IF NOT EXISTS，用 PRAGMA 探测）。"""
    conn.execute("BEGIN IMMEDIATE")
    for table, column, coltype in MIGRATIONS:
        cols = {r[1] for r in conn.execute(f"PRAGMA table_info({table})").fetchall()}
        if column not in cols:
            conn.execute(f"ALTER TABLE {table} ADD COLUMN {column} {coltype}")


    # Invalidate credentials exposed by the former two-sided visibility policy once.
    policy = conn.execute("SELECT value FROM app_metadata WHERE key = 'pickup_policy'").fetchone()
    if policy is None:
        active = conn.execute("SELECT id FROM orders WHERE status IN ('reserved', 'confirmed')").fetchall()
        for order in active:
            conn.execute("UPDATE orders SET pickup_code = ? WHERE id = ?", (f"GC-{secrets.token_hex(3).upper()}", order['id']))
        conn.execute("INSERT INTO app_metadata (key, value) VALUES ('pickup_policy', 'buyer-holds-seller-verifies-v1')")

    if conn.execute("SELECT 1 FROM app_metadata WHERE key = 'contact_retired'").fetchone() is None:
        columns = {row[1] for row in conn.execute("PRAGMA table_info(users)")}
        if 'contact' in columns:
            conn.execute("UPDATE users SET contact = NULL")
        conn.execute("INSERT INTO app_metadata (key, value) VALUES ('contact_retired', 'order-chat-v1')")
