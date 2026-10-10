"""认证与授权：密码哈希、会话令牌、身份依赖。

设计要点（修复越权）：
- 身份不再由请求体/查询参数中的 user_id 决定，而是由服务端根据会话 Cookie 推导；
- 密码使用 PBKDF2-HMAC-SHA256 加盐哈希，数据库不存明文；
- 会话令牌随机生成、服务端存储、带过期时间，退出即失效。
"""
import hashlib
import secrets
from datetime import datetime, timedelta
from typing import Optional

from fastapi import Depends, HTTPException, Request, status

import database

SESSION_COOKIE = "gc_session"
SESSION_DAYS = 7
PBKDF2_ROUNDS = 120_000
PBKDF2_PREFIX = "pbkdf2_sha256"


# ---------------- 密码 ----------------
def hash_password(password: str, salt: Optional[str] = None) -> str:
    """返回 ``pbkdf2_sha256$<salt>$<hash>`` 格式的密码哈希。"""
    salt = salt or secrets.token_hex(16)
    dk = hashlib.pbkdf2_hmac("sha256", password.encode("utf-8"), salt.encode("utf-8"), PBKDF2_ROUNDS)
    return f"{PBKDF2_PREFIX}${salt}${dk.hex()}"


def verify_password(password: str, stored: Optional[str]) -> bool:
    """常量时间比对密码；格式非法或为空一律视为不匹配。"""
    if not stored:
        return False
    try:
        prefix, salt, digest = stored.split("$")
    except ValueError:
        return False
    if prefix != PBKDF2_PREFIX:
        return False
    expected = hashlib.pbkdf2_hmac("sha256", password.encode("utf-8"), salt.encode("utf-8"), PBKDF2_ROUNDS)
    return secrets.compare_digest(expected.hex(), digest)


# ---------------- 会话 ----------------
def new_token() -> str:
    return secrets.token_urlsafe(32)


def create_session(conn, user_id: int) -> str:
    """创建会话并返回令牌。"""
    token = new_token()
    expires = (datetime.now() + timedelta(days=SESSION_DAYS)).strftime("%Y-%m-%d %H:%M:%S")
    conn.execute(
        "INSERT INTO sessions (token, user_id, expires_at) VALUES (?, ?, ?)",
        (token, user_id, expires),
    )
    return token


def destroy_session(conn, token: str) -> None:
    conn.execute("DELETE FROM sessions WHERE token = ?", (token,))


def user_for_token(conn, token: str):
    """按令牌取用户；令牌不存在或已过期返回 None（并顺带清理过期会话）。"""
    if not token:
        return None
    row = conn.execute(
        """
        SELECT u.* FROM sessions s JOIN users u ON u.id = s.user_id
        WHERE s.token = ? AND s.expires_at > datetime('now','localtime')
        """,
        (token,),
    ).fetchone()
    if not row:
        conn.execute("DELETE FROM sessions WHERE expires_at <= datetime('now','localtime')")
        return None
    return row


# ---------------- FastAPI 依赖 ----------------
def current_user(request: Request) -> dict:
    """从会话 Cookie 解析当前用户；未登录返回 401。

    这是所有受保护接口的身份唯一来源——客户端无法通过传参冒充他人。
    """
    token = request.cookies.get(SESSION_COOKIE)
    if not token:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="请先登录")
    with database.db_session() as conn:
        row = user_for_token(conn, token)
    if not row:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="登录已过期，请重新登录")
    return dict(row)


def require_admin(user: dict = Depends(current_user)) -> dict:
    """管理员专属接口的权限边界：非 admin 一律 403。"""
    if user.get("role") != "admin":
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="需要管理员权限")
    return user

# ---------------- 登录失败限流 ----------------
MAX_LOGIN_FAILS = 5          # 连续失败次数上限
LOCK_MINUTES = 15            # 达到上限后锁定时长（分钟）


def check_login_allowed(conn, identifier: str) -> None:
    """检查该登录名是否处于锁定状态；未锁定则放行。"""
    row = conn.execute(
        "SELECT fail_count, locked_until FROM login_attempts WHERE identifier = ?", (identifier,)
    ).fetchone()
    if not row or not row["locked_until"]:
        return
    if row["locked_until"] > datetime.now().strftime("%Y-%m-%d %H:%M:%S"):
        remaining = _minutes_left(row["locked_until"])
        raise HTTPException(
            status_code=429,
            detail=f"登录失败次数过多，请 {remaining} 分钟后再试",
        )
    # 锁定已到期，重置计数
    conn.execute(
        "UPDATE login_attempts SET fail_count = 0, locked_until = NULL WHERE identifier = ?",
        (identifier,),
    )


def record_login_failure(conn, identifier: str) -> None:
    """累计失败次数，达到上限则锁定一段时间。"""
    row = conn.execute(
        "SELECT fail_count FROM login_attempts WHERE identifier = ?", (identifier,)
    ).fetchone()
    count = (row["fail_count"] if row else 0) + 1
    locked_until = None
    if count >= MAX_LOGIN_FAILS:
        locked_until = (datetime.now() + timedelta(minutes=LOCK_MINUTES)).strftime("%Y-%m-%d %H:%M:%S")
    conn.execute(
        """
        INSERT INTO login_attempts (identifier, fail_count, locked_until, last_fail_at)
        VALUES (?, ?, ?, datetime('now','localtime'))
        ON CONFLICT(identifier) DO UPDATE SET
            fail_count = excluded.fail_count,
            locked_until = excluded.locked_until,
            last_fail_at = excluded.last_fail_at
        """,
        (identifier, count, locked_until),
    )


def clear_login_failures(conn, identifier: str) -> None:
    conn.execute("DELETE FROM login_attempts WHERE identifier = ?", (identifier,))


def _minutes_left(locked_until: str) -> int:
    try:
        delta = datetime.strptime(locked_until, "%Y-%m-%d %H:%M:%S") - datetime.now()
        return max(1, int(delta.total_seconds() // 60) + 1)
    except ValueError:
        return LOCK_MINUTES
