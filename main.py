"""绿循校园——校园闲置教材与物品循环流转系统。

分层：
- 常量与业务规则（REWARD_*、分类减碳系数、ORDER_TRANSITIONS）
- 认证与授权层：auth.py（会话 Cookie 派生身份）
- API 控制层：FastAPI 路由
- 业务逻辑层：_transition / estimate_carbon 等纯业务函数
- 数据访问层：database.py

安全边界（本版本重点）：
- 所有受保护接口的身份来自服务端会话，客户端传入的任何 user_id 一律被忽略；
- 管理员接口统一经 require_admin 校验，非 admin 一律 403；
- 资源级授权：修改/下架物品需为物主，订单操作需为订单参与方。
"""
import base64
import binascii
import logging
import re
import secrets
import uuid
from contextlib import asynccontextmanager
from pathlib import Path
from typing import List, Optional

from fastapi import Depends, FastAPI, HTTPException, Query, Request
from fastapi.exceptions import RequestValidationError
from fastapi.responses import FileResponse, JSONResponse, Response
from fastapi.staticfiles import StaticFiles

import auth
import database
from auth import SESSION_COOKIE, SESSION_DAYS, current_user, hash_password, require_admin, verify_password
from models import (
    AdminItemOut, AdminPasswordReset, CategoryCreate, CategoryOut, CategoryUpdate, FavoriteOut,
    Health, ItemCreate, ItemDetailOut, ItemOut, ItemUpdate, LoginRequest, OrderAction, OrderCreate,
    OrderOut, PasswordChange, PointLogOut, ProductCreate, ProductOut, ProductUpdate,
    ProfileUpdate, RedeemOut, RedeemRequest, RegisterRequest, ReportCreate, ReportOut,
    ReviewAction, UserOut, UserPublic,
)

APP_NAME = "绿循校园"
APP_VERSION = "2.0.0"

logger = logging.getLogger("greencampus")

STATIC_DIR = Path(__file__).parent / "static"
UPLOAD_DIR = STATIC_DIR / "uploads"

REWARD_PUBLISH = 10
REWARD_CYCLE = 20

ORDER_TRANSITIONS = {
    "reserved": {"confirmed", "cancelled"},
    "confirmed": {"completed", "cancelled"},
}

STATUS_LABEL = {
    "reserved": "已预约",
    "confirmed": "待自提",
    "completed": "已完成",
    "cancelled": "已取消",
}

CARBON_FACTOR_FALLBACK = 2.0
TREE_ABSORB_PER_YEAR = 18.0

# 分类缓存：分类数据变动极少，启动时载入并在管理员增删改后失效
_category_factors: dict = {}


def refresh_category_cache(conn=None) -> None:
    """重新载入分类减碳系数缓存。"""
    global _category_factors
    if conn is not None:
        rows = conn.execute("SELECT name, carbon_factor FROM categories").fetchall()
    else:
        with database.db_session() as c:
            rows = c.execute("SELECT name, carbon_factor FROM categories").fetchall()
    _category_factors = {r["name"]: r["carbon_factor"] for r in rows}


def category_names(conn) -> set:
    """当前启用中的分类名称集合。"""
    return {r["name"] for r in conn.execute("SELECT name FROM categories").fetchall()}


def require_category(conn, name: str) -> None:
    """校验分类存在（管理员可管理分类，物品只能引用已启用分类）。"""
    if name not in category_names(conn):
        raise HTTPException(status_code=422, detail=f"分类「{name}」不存在，请从可用分类中选择")

# 图片上传约束：客户端先等比压缩再以 data URL 提交，服务端解码落盘
MAX_IMAGE_BYTES = 2 * 1024 * 1024  # 2MB
ALLOWED_IMAGE_TYPES = {
    "image/png": "png",
    "image/jpeg": "jpg",
    "image/webp": "webp",
    "image/gif": "gif",
}
DATA_URL_RE = re.compile(r"^data:(image/[a-zA-Z0-9.+-]+);base64,(.+)$", re.S)

# 演示账号初始密码（仅用于课程演示；生产环境应由用户自行注册）
DEMO_PASSWORD = "campus123"


@asynccontextmanager
async def lifespan(app: FastAPI):
    database.init_db()
    _seed_demo_passwords()
    UPLOAD_DIR.mkdir(parents=True, exist_ok=True)
    refresh_category_cache()
    logger.info("%s v%s 启动完成，数据库就绪", APP_NAME, APP_VERSION)
    yield


def _seed_demo_passwords() -> None:
    """为种子账号补齐初始密码（仅当尚未设置时），使演示可直接登录。"""
    with database.db_session() as conn:
        rows = conn.execute("SELECT id FROM users WHERE password_hash IS NULL OR password_hash = ''").fetchall()
        for r in rows:
            conn.execute("UPDATE users SET password_hash = ? WHERE id = ?", (hash_password(DEMO_PASSWORD), r["id"]))


app = FastAPI(title=APP_NAME, version=APP_VERSION, lifespan=lifespan)


# ---------------- 统一异常处理 ----------------
@app.exception_handler(RequestValidationError)
async def validation_handler(request: Request, exc: RequestValidationError) -> JSONResponse:
    first = exc.errors()[0] if exc.errors() else {}
    field = ".".join(str(p) for p in first.get("loc", ()) if p not in ("body", "query"))
    msg = first.get("msg", "参数校验失败")
    detail = f"参数「{field}」不合法：{msg}" if field else f"参数不合法：{msg}"
    return JSONResponse(status_code=422, content={"detail": detail})


@app.exception_handler(Exception)
async def unhandled_handler(request: Request, exc: Exception) -> JSONResponse:
    logger.exception("未处理异常 %s %s", request.method, request.url.path)
    return JSONResponse(status_code=500, content={"detail": "服务器内部错误，请稍后重试"})


def estimate_carbon(category: str) -> float:
    """单次流转减碳量估算，系数取自分类配置（未知分类用兜底值）。"""
    return _category_factors.get(category, CARBON_FACTOR_FALLBACK)


def rows_to_dicts(rows) -> List[dict]:
    return [dict(r) for r in rows]


def save_data_url(data_url: str) -> str:
    """解码 data URL 图片并落盘，返回可访问的相对路径。

    只接受白名单图片类型并限制大小，文件名由服务端生成（不采用客户端文件名），
    避免路径穿越与可执行文件上传。
    """
    if not data_url:
        raise HTTPException(status_code=400, detail="图片内容为空")
    m = DATA_URL_RE.match(data_url.strip())
    if not m:
        raise HTTPException(status_code=400, detail="图片格式不正确，请上传 PNG/JPG/WebP/GIF")
    mime, b64 = m.group(1), m.group(2)
    ext = ALLOWED_IMAGE_TYPES.get(mime.lower())
    if not ext:
        raise HTTPException(status_code=400, detail="不支持的图片类型，仅限 PNG/JPG/WebP/GIF")
    try:
        raw = base64.b64decode(b64, validate=True)
    except (binascii.Error, ValueError):
        raise HTTPException(status_code=400, detail="图片数据损坏，无法解析")
    if len(raw) > MAX_IMAGE_BYTES:
        raise HTTPException(status_code=400, detail=f"图片过大，请压缩到 {MAX_IMAGE_BYTES // 1024 // 1024}MB 以内")
    if not raw:
        raise HTTPException(status_code=400, detail="图片内容为空")
    UPLOAD_DIR.mkdir(parents=True, exist_ok=True)
    filename = f"{uuid.uuid4().hex}.{ext}"
    (UPLOAD_DIR / filename).write_bytes(raw)
    return f"/static/uploads/{filename}"


def set_session_cookie(response: Response, token: str) -> None:
    """写入会话 Cookie：HttpOnly + SameSite=Lax，避免脚本读取与 CSRF。"""
    response.set_cookie(
        key=SESSION_COOKIE, value=token, max_age=SESSION_DAYS * 86400,
        httponly=True, samesite="lax", path="/",
    )


# =======================================================================
# 健康检查
# =======================================================================
@app.get("/api/health", response_model=Health)
def health() -> Health:
    return Health(status="ok", app=APP_NAME, version=APP_VERSION)


# =======================================================================
# 认证：注册 / 登录 / 退出 / 当前身份
# =======================================================================
@app.post("/api/auth/register", response_model=UserOut, status_code=201)
def register(payload: RegisterRequest, response: Response) -> dict:
    """注册新账号并直接登录。学号唯一。"""
    with database.db_session() as conn:
        dup = conn.execute("SELECT 1 FROM users WHERE student_no = ?", (payload.student_no,)).fetchone()
        if dup:
            raise HTTPException(status_code=400, detail="该学号已注册，请直接登录")
        cur = conn.execute(
            "INSERT INTO users (name, student_no, college, role, points, password_hash) VALUES (?, ?, ?, 'student', 0, ?)",
            (payload.name, payload.student_no, payload.college, hash_password(payload.password)),
        )
        user_id = cur.lastrowid
        token = auth.create_session(conn, user_id)
        row = conn.execute("SELECT * FROM users WHERE id = ?", (user_id,)).fetchone()
    set_session_cookie(response, token)
    return dict(row)


@app.post("/api/auth/login", response_model=UserOut)
def login(payload: LoginRequest, response: Response) -> dict:
    """学号或姓名 + 密码登录。

    失败提示不区分账号是否存在，避免账号枚举；连续失败达上限则临时锁定，
    防止暴力破解。
    """
    identifier = payload.login.strip()

    # 先在独立事务中检查锁定状态（读取后即提交，避免与后续失败计数互相干扰）
    with database.db_session() as conn:
        auth.check_login_allowed(conn, identifier)
        row = conn.execute(
            "SELECT * FROM users WHERE student_no = ? OR name = ? ORDER BY id LIMIT 1",
            (identifier, identifier),
        ).fetchone()
        ok = bool(row) and verify_password(payload.password, row["password_hash"])
        if ok:
            auth.clear_login_failures(conn, identifier)
            token = auth.create_session(conn, row["id"])

    if not ok:
        # 失败计数必须独立提交：上面的会话若以异常结束会回滚，导致计数丢失
        with database.db_session() as conn:
            auth.record_login_failure(conn, identifier)
        raise HTTPException(status_code=401, detail="学号/姓名或密码不正确")

    set_session_cookie(response, token)
    return dict(row)


@app.post("/api/auth/logout")
def logout(request: Request, response: Response) -> dict:
    token = request.cookies.get(SESSION_COOKIE)
    if token:
        with database.db_session() as conn:
            auth.destroy_session(conn, token)
    response.delete_cookie(SESSION_COOKIE, path="/")
    return {"ok": True}


@app.get("/api/auth/me", response_model=UserOut)
def whoami(user: dict = Depends(current_user)) -> dict:
    return user


@app.post("/api/auth/password", status_code=200)
def change_password(payload: PasswordChange, user: dict = Depends(current_user)) -> dict:
    """修改密码；校验旧密码，成功后注销该用户的其它会话。"""
    if not verify_password(payload.old_password, user["password_hash"]):
        raise HTTPException(status_code=400, detail="原密码不正确")
    with database.db_session() as conn:
        conn.execute("UPDATE users SET password_hash = ? WHERE id = ?", (hash_password(payload.new_password), user["id"]))
        conn.execute("DELETE FROM sessions WHERE user_id = ?", (user["id"],))
    return {"ok": True, "message": "密码已更新，请重新登录"}


# =======================================================================
# 用户资料
# =======================================================================
@app.get("/api/users", response_model=List[UserPublic])
def list_users() -> List[dict]:
    """公开的用户列表（不含联系方式）。"""
    with database.db_session() as conn:
        rows = conn.execute("SELECT id, name, college, avatar, bio FROM users ORDER BY id").fetchall()
    return rows_to_dicts(rows)


@app.patch("/api/users/me", response_model=UserOut)
def update_profile(payload: ProfileUpdate, user: dict = Depends(current_user)) -> dict:
    """更新本人资料（身份取自会话，不能改他人）。"""
    fields = payload.model_dump(exclude_none=True)
    if not fields:
        raise HTTPException(status_code=400, detail="没有需要修改的内容")
    with database.db_session() as conn:
        if "name" in fields:
            dup = conn.execute("SELECT 1 FROM users WHERE name = ? AND id != ?", (fields["name"], user["id"])).fetchone()
            if dup:
                raise HTTPException(status_code=400, detail="该姓名已被使用")
        sets = ", ".join(f"{k} = ?" for k in fields)
        conn.execute(f"UPDATE users SET {sets} WHERE id = ?", (*fields.values(), user["id"]))
        row = conn.execute("SELECT * FROM users WHERE id = ?", (user["id"],)).fetchone()
    return dict(row)


@app.post("/api/users/me/avatar", response_model=UserOut)
def upload_avatar(payload: dict, user: dict = Depends(current_user)) -> dict:
    """上传本人头像（data URL）。"""
    path = save_data_url(payload.get("image", ""))
    with database.db_session() as conn:
        conn.execute("UPDATE users SET avatar = ? WHERE id = ?", (path, user["id"]))
        row = conn.execute("SELECT * FROM users WHERE id = ?", (user["id"],)).fetchone()
    return dict(row)


@app.get("/api/users/{user_id}/profile")
def user_profile(user_id: int) -> dict:
    """公开的用户主页聚合：资料 + 环保统计 + 在售物品（不含隐私与订单）。"""
    with database.db_session() as conn:
        user = conn.execute(
            "SELECT id, name, college, role, points, avatar, bio, created_at FROM users WHERE id = ?", (user_id,)
        ).fetchone()
        if not user:
            raise HTTPException(status_code=404, detail="用户不存在")
        published = conn.execute("SELECT COUNT(*) FROM items WHERE owner_id = ?", (user_id,)).fetchone()[0]
        carbon = conn.execute("SELECT COALESCE(SUM(carbon_saved), 0) FROM items WHERE owner_id = ?", (user_id,)).fetchone()[0]
        cycles = conn.execute("SELECT COALESCE(SUM(cycle_count), 0) FROM items WHERE owner_id = ?", (user_id,)).fetchone()[0]
        on_sale = conn.execute(
            "SELECT COUNT(*) FROM items WHERE owner_id = ? AND status IN ('available','reserved')", (user_id,)
        ).fetchone()[0]
        items = conn.execute(
            ITEM_SQL + " WHERE i.owner_id = ? AND i.status IN ('available','reserved') ORDER BY i.id DESC LIMIT 12",
            (user_id,),
        ).fetchall()
    return {
        **dict(user),
        "stats": {
            "published": published, "on_sale": on_sale, "cycles": cycles, "carbon_kg": round(carbon, 2),
        },
        "items": rows_to_dicts(items),
    }


@app.get("/api/me/summary")
def my_summary(user: dict = Depends(current_user)) -> dict:
    """本人私密聚合：资料 + 统计 + 最近流水（仅本人可见）。"""
    uid = user["id"]
    with database.db_session() as conn:
        published = conn.execute("SELECT COUNT(*) FROM items WHERE owner_id = ?", (uid,)).fetchone()[0]
        sold = conn.execute("SELECT COUNT(*) FROM orders WHERE seller_id = ? AND status='completed'", (uid,)).fetchone()[0]
        bought = conn.execute("SELECT COUNT(*) FROM orders WHERE buyer_id = ? AND status='completed'", (uid,)).fetchone()[0]
        active = conn.execute(
            "SELECT COUNT(*) FROM orders WHERE (buyer_id = ? OR seller_id = ?) AND status IN ('reserved','confirmed')",
            (uid, uid),
        ).fetchone()[0]
        carbon = conn.execute("SELECT COALESCE(SUM(carbon_saved), 0) FROM items WHERE owner_id = ?", (uid,)).fetchone()[0]
        cycles = conn.execute("SELECT COALESCE(SUM(cycle_count), 0) FROM items WHERE owner_id = ?", (uid,)).fetchone()[0]
        favorites = conn.execute("SELECT COUNT(*) FROM favorites WHERE user_id = ?", (uid,)).fetchone()[0]
    return {
        "user": user,
        "stats": {
            "published": published, "sold": sold, "bought": bought, "active_orders": active,
            "cycles": cycles, "carbon_kg": round(carbon, 2), "favorites": favorites,
        },
    }


# =======================================================================
# 物品分类（公开读取；管理员增删改）
# =======================================================================
CATEGORY_SQL = """
    SELECT c.*, (SELECT COUNT(*) FROM items i WHERE i.category = c.name) AS item_count
    FROM categories c
"""


@app.get("/api/categories", response_model=List[CategoryOut])
def list_categories() -> List[dict]:
    """可用分类列表（发布/筛选/展示共用）。"""
    with database.db_session() as conn:
        rows = conn.execute(CATEGORY_SQL + " ORDER BY c.sort_order, c.id").fetchall()
    data = rows_to_dicts(rows)
    for d in data:
        d["protected"] = bool(d["protected"])
    return data


@app.post("/api/admin/categories", response_model=CategoryOut, status_code=201)
def admin_create_category(payload: CategoryCreate, admin: dict = Depends(require_admin)) -> dict:
    name = payload.name.strip()
    if not name:
        raise HTTPException(status_code=400, detail="分类名称不能为空")
    with database.db_session() as conn:
        if conn.execute("SELECT 1 FROM categories WHERE name = ?", (name,)).fetchone():
            raise HTTPException(status_code=400, detail=f"分类「{name}」已存在")
        cur = conn.execute(
            "INSERT INTO categories (name, icon, carbon_factor, sort_order, protected) VALUES (?, ?, ?, ?, 0)",
            (name, payload.icon, payload.carbon_factor, payload.sort_order),
        )
        row = conn.execute(CATEGORY_SQL + " WHERE c.id = ?", (cur.lastrowid,)).fetchone()
        refresh_category_cache(conn)
    data = dict(row)
    data["protected"] = bool(data["protected"])
    return data


@app.patch("/api/admin/categories/{category_id}", response_model=CategoryOut)
def admin_update_category(category_id: int, payload: CategoryUpdate, admin: dict = Depends(require_admin)) -> dict:
    """重命名分类时同步更新引用该分类的物品，保持数据一致。"""
    with database.db_session() as conn:
        cat = conn.execute("SELECT * FROM categories WHERE id = ?", (category_id,)).fetchone()
        if not cat:
            raise HTTPException(status_code=404, detail="分类不存在")
        fields = payload.model_dump(exclude_none=True)
        if not fields:
            raise HTTPException(status_code=400, detail="没有需要修改的内容")
        new_name = fields.get("name")
        if new_name:
            new_name = new_name.strip()
            if not new_name:
                raise HTTPException(status_code=400, detail="分类名称不能为空")
            dup = conn.execute(
                "SELECT 1 FROM categories WHERE name = ? AND id != ?", (new_name, category_id)
            ).fetchone()
            if dup:
                raise HTTPException(status_code=400, detail=f"分类「{new_name}」已存在")
            fields["name"] = new_name
            if new_name != cat["name"]:
                conn.execute("UPDATE items SET category = ? WHERE category = ?", (new_name, cat["name"]))
        sets = ", ".join(f"{k} = ?" for k in fields)
        conn.execute(f"UPDATE categories SET {sets} WHERE id = ?", (*fields.values(), category_id))
        row = conn.execute(CATEGORY_SQL + " WHERE c.id = ?", (category_id,)).fetchone()
        refresh_category_cache(conn)
    data = dict(row)
    data["protected"] = bool(data["protected"])
    return data


@app.delete("/api/admin/categories/{category_id}")
def admin_delete_category(category_id: int, admin: dict = Depends(require_admin)) -> dict:
    """删除分类：兜底分类与仍被物品引用的分类不可删除。"""
    with database.db_session() as conn:
        cat = conn.execute("SELECT * FROM categories WHERE id = ?", (category_id,)).fetchone()
        if not cat:
            raise HTTPException(status_code=404, detail="分类不存在")
        if cat["protected"]:
            raise HTTPException(status_code=400, detail=f"「{cat['name']}」为系统兜底分类，不可删除")
        used = conn.execute("SELECT COUNT(*) FROM items WHERE category = ?", (cat["name"],)).fetchone()[0]
        if used:
            raise HTTPException(
                status_code=400,
                detail=f"仍有 {used} 件物品属于「{cat['name']}」，请先将其归入其它分类后再删除",
            )
        conn.execute("DELETE FROM categories WHERE id = ?", (category_id,))
        refresh_category_cache(conn)
    return {"ok": True}


# =======================================================================
# 物品（市集）
# =======================================================================
ITEM_SQL = """
    SELECT i.*, u.name AS owner_name, u.college AS owner_college, u.avatar AS owner_avatar
    FROM items i JOIN users u ON u.id = i.owner_id
"""

SORT_SQL = {
    "latest": "i.created_at DESC, i.id DESC",
    "price_asc": "i.price ASC, i.id DESC",
    "price_desc": "i.price DESC, i.id DESC",
    "cycle": "i.cycle_count DESC, i.carbon_saved DESC, i.id DESC",
}


@app.get("/api/items", response_model=List[ItemOut])
def list_items(
    category: Optional[str] = Query(None, max_length=10),
    keyword: Optional[str] = Query(None, max_length=50),
    sort: str = Query("latest", pattern="^(latest|price_asc|price_desc|cycle)$"),
    limit: int = Query(60, ge=1, le=200),
    offset: int = Query(0, ge=0),
) -> List[dict]:
    # 仅展示已通过审核的在售/已预约物品
    sql = ITEM_SQL + " WHERE i.status IN ('available', 'reserved') AND i.review_status = 'approved'"
    params: list = []
    if category:
        sql += " AND i.category = ?"
        params.append(category)
    if keyword:
        sql += " AND (i.title LIKE ? OR i.description LIKE ?)"
        params += [f"%{keyword}%", f"%{keyword}%"]
    sql += f" ORDER BY {SORT_SQL[sort]} LIMIT ? OFFSET ?"
    params += [limit, offset]
    with database.db_session() as conn:
        rows = conn.execute(sql, params).fetchall()
    return rows_to_dicts(rows)


@app.get("/api/items/mine", response_model=List[ItemOut])
def my_items(user: dict = Depends(current_user)) -> List[dict]:
    """我发布的全部物品（含待审核/已驳回，身份取自会话）。"""
    with database.db_session() as conn:
        rows = conn.execute(ITEM_SQL + " WHERE i.owner_id = ? ORDER BY i.id DESC", (user["id"],)).fetchall()
    return rows_to_dicts(rows)


@app.get("/api/items/{item_id}", response_model=ItemDetailOut)
def get_item(item_id: int, request: Request) -> dict:
    """物品详情。

    待审核/已驳回的物品仅物主与管理员可见，避免未审核内容对外暴露。
    """
    token = request.cookies.get(SESSION_COOKIE)
    viewer = None
    with database.db_session() as conn:
        if token:
            viewer = auth.user_for_token(conn, token)
        row = conn.execute(ITEM_SQL + " WHERE i.id = ?", (item_id,)).fetchone()
        if not row:
            raise HTTPException(status_code=404, detail="物品不存在")
        is_privileged = bool(viewer and (viewer["id"] == row["owner_id"] or viewer["role"] == "admin"))
        if row["review_status"] != "approved" and not is_privileged:
            raise HTTPException(status_code=404, detail="物品不存在")
        data = dict(row)
        data["favorite_count"] = conn.execute("SELECT COUNT(*) FROM favorites WHERE item_id = ?", (item_id,)).fetchone()[0]
        data["favorited"] = bool(viewer and conn.execute(
            "SELECT 1 FROM favorites WHERE user_id = ? AND item_id = ?", (viewer["id"], item_id)
        ).fetchone())
    return data


@app.post("/api/items", response_model=ItemOut, status_code=201)
def create_item(payload: ItemCreate, user: dict = Depends(current_user)) -> dict:
    """发布闲置物品（归属为当前登录用户，客户端无法指定 owner）。"""
    image = save_data_url(payload.image) if payload.image else None
    with database.db_session() as conn:
        require_category(conn, payload.category)
        cur = conn.execute(
            """INSERT INTO items (owner_id, title, category, description, price, image, review_status, updated_at)
               VALUES (?, ?, ?, ?, ?, ?, 'approved', datetime('now','localtime'))""",
            (user["id"], payload.title, payload.category, payload.description, payload.price, image),
        )
        database.add_points(conn, user["id"], REWARD_PUBLISH, f"发布闲置《{payload.title}》获得碳积分")
        row = conn.execute(ITEM_SQL + " WHERE i.id = ?", (cur.lastrowid,)).fetchone()
    return dict(row)


@app.patch("/api/items/{item_id}", response_model=ItemOut)
def update_item(item_id: int, payload: ItemUpdate, user: dict = Depends(current_user)) -> dict:
    """物主修改自己物品（资源级授权：非物主 403）。

    修改内容后物品需重新提交审核：状态置为 pending，市集暂不展示，
    由管理员复核通过后恢复在售。
    """
    with database.db_session() as conn:
        item = conn.execute("SELECT * FROM items WHERE id = ?", (item_id,)).fetchone()
        if not item:
            raise HTTPException(status_code=404, detail="物品不存在")
        if item["owner_id"] != user["id"]:
            raise HTTPException(status_code=403, detail="只能修改自己发布的物品")
        if item["status"] in ("completed", "offshelf"):
            raise HTTPException(status_code=400, detail="该物品已流转结束或已下架，不能修改")
        fields = payload.model_dump(exclude_none=True)
        if not fields:
            raise HTTPException(status_code=400, detail="没有需要修改的内容")
        if "category" in fields:
            require_category(conn, fields["category"])
        if "price" in fields and item["status"] == "reserved":
            raise HTTPException(status_code=400, detail="物品已被预约，不能修改价格")
        if "image" in fields:
            fields["image"] = save_data_url(fields["image"])
        # 重新提交审核：清空上次驳回理由，并记录更新时间
        fields["review_status"] = "pending"
        fields["review_note"] = None
        sets = ", ".join(f"{k} = ?" for k in fields)
        conn.execute(
            f"UPDATE items SET {sets}, updated_at = datetime('now','localtime') WHERE id = ?",
            (*fields.values(), item_id),
        )
        row = conn.execute(ITEM_SQL + " WHERE i.id = ?", (item_id,)).fetchone()
    return dict(row)


@app.delete("/api/items/{item_id}", response_model=ItemOut)
def offshelf_own_item(item_id: int, user: dict = Depends(current_user)) -> dict:
    """物主下架自己物品（资源级授权）。"""
    with database.db_session() as conn:
        item = conn.execute("SELECT * FROM items WHERE id = ?", (item_id,)).fetchone()
        if not item:
            raise HTTPException(status_code=404, detail="物品不存在")
        if item["owner_id"] != user["id"]:
            raise HTTPException(status_code=403, detail="只能下架自己发布的物品")
        if item["status"] == "offshelf":
            raise HTTPException(status_code=400, detail="物品已是下架状态")
        active = conn.execute(
            "SELECT 1 FROM orders WHERE item_id = ? AND status IN ('reserved','confirmed')", (item_id,)
        ).fetchone()
        if active:
            raise HTTPException(status_code=400, detail="该物品有进行中的订单，请先取消订单")
        conn.execute("UPDATE items SET status = 'offshelf' WHERE id = ?", (item_id,))
        row = conn.execute(ITEM_SQL + " WHERE i.id = ?", (item_id,)).fetchone()
    return dict(row)


# =======================================================================
# 收藏（全部基于会话身份）
# =======================================================================
FAV_SQL = """
    SELECT f.id, f.item_id, f.created_at, i.title AS item_title, i.category, i.price, i.status,
           i.image, u.name AS owner_name
    FROM favorites f JOIN items i ON i.id = f.item_id JOIN users u ON u.id = i.owner_id
"""


@app.get("/api/favorites", response_model=List[FavoriteOut])
def list_favorites(user: dict = Depends(current_user)) -> List[dict]:
    with database.db_session() as conn:
        rows = conn.execute(FAV_SQL + " WHERE f.user_id = ? ORDER BY f.id DESC", (user["id"],)).fetchall()
    return rows_to_dicts(rows)


@app.post("/api/favorites", response_model=FavoriteOut, status_code=201)
def add_favorite(payload: dict, user: dict = Depends(current_user)) -> dict:
    item_id = payload.get("item_id")
    if not isinstance(item_id, int):
        raise HTTPException(status_code=422, detail="参数「item_id」不合法：应为整数")
    with database.db_session() as conn:
        item = conn.execute("SELECT review_status FROM items WHERE id = ?", (item_id,)).fetchone()
        if not item:
            raise HTTPException(status_code=404, detail="物品不存在")
        if item["review_status"] != "approved":
            raise HTTPException(status_code=400, detail="该物品尚未通过审核，暂不可收藏")
        if conn.execute("SELECT 1 FROM favorites WHERE user_id = ? AND item_id = ?", (user["id"], item_id)).fetchone():
            raise HTTPException(status_code=400, detail="已收藏该物品")
        cur = conn.execute("INSERT INTO favorites (user_id, item_id) VALUES (?, ?)", (user["id"], item_id))
        row = conn.execute(FAV_SQL + " WHERE f.id = ?", (cur.lastrowid,)).fetchone()
    return dict(row)


@app.delete("/api/favorites/{item_id}")
def remove_favorite(item_id: int, user: dict = Depends(current_user)) -> dict:
    with database.db_session() as conn:
        cur = conn.execute("DELETE FROM favorites WHERE user_id = ? AND item_id = ?", (user["id"], item_id))
        if cur.rowcount == 0:
            raise HTTPException(status_code=404, detail="尚未收藏该物品")
    return {"ok": True}


# =======================================================================
# 碳积分与商城
# =======================================================================
@app.get("/api/point-logs", response_model=List[PointLogOut])
def list_point_logs(user: dict = Depends(current_user), limit: int = Query(50, ge=1, le=200)) -> List[dict]:
    """本人积分流水（仅本人可见）。"""
    with database.db_session() as conn:
        rows = conn.execute(
            "SELECT * FROM point_logs WHERE user_id = ? ORDER BY id DESC LIMIT ?", (user["id"], limit)
        ).fetchall()
    return rows_to_dicts(rows)


@app.get("/api/products", response_model=List[ProductOut])
def list_products() -> List[dict]:
    with database.db_session() as conn:
        rows = conn.execute("SELECT * FROM products ORDER BY cost_points").fetchall()
    return rows_to_dicts(rows)


@app.post("/api/redeem", response_model=RedeemOut)
def redeem(payload: RedeemRequest, user: dict = Depends(current_user)) -> RedeemOut:
    """兑换礼品（扣分与减库存同事务；扣分对象为当前登录用户）。"""
    with database.db_session() as conn:
        product = conn.execute("SELECT * FROM products WHERE id = ?", (payload.product_id,)).fetchone()
        if not product:
            raise HTTPException(status_code=404, detail="礼品不存在")
        if product["stock"] <= 0:
            raise HTTPException(status_code=400, detail="礼品库存不足")
        cur = conn.execute(
            "UPDATE users SET points = points - ? WHERE id = ? AND points >= ?",
            (product["cost_points"], user["id"], product["cost_points"]),
        )
        if cur.rowcount == 0:
            fresh = conn.execute("SELECT points FROM users WHERE id = ?", (user["id"],)).fetchone()
            raise HTTPException(status_code=400, detail=f"碳积分不足，还差 {product['cost_points'] - fresh[0]} 分")
        conn.execute(
            "INSERT INTO point_logs (user_id, delta, reason) VALUES (?, ?, ?)",
            (user["id"], -product["cost_points"], f"兑换礼品「{product['name']}」"),
        )
        cur = conn.execute("UPDATE products SET stock = stock - 1 WHERE id = ? AND stock > 0", (payload.product_id,))
        if cur.rowcount == 0:
            raise HTTPException(status_code=400, detail="礼品库存不足")
        remaining = conn.execute("SELECT points FROM users WHERE id = ?", (user["id"],)).fetchone()[0]
    return RedeemOut(ok=True, message=f"成功兑换「{product['name']}」，请到学生会办公室领取", remaining_points=remaining)


# =======================================================================
# 统计与排行
# =======================================================================
def stats_summary() -> dict:
    """平台全局环保汇总指标。

    统计口径与「市集可见」保持一致：仅计入已通过审核的物品，避免看板数字
    高于用户实际能看到的物品总量；待审/驳回物品单独计数。
    """
    with database.db_session() as conn:
        total_published = conn.execute(
            "SELECT COUNT(*) FROM items WHERE review_status = 'approved'"
        ).fetchone()[0]
        pending_items = conn.execute(
            "SELECT COUNT(*) FROM items WHERE review_status != 'approved'"
        ).fetchone()[0]
        total_cycles = conn.execute(
            "SELECT COALESCE(SUM(cycle_count), 0) FROM items WHERE review_status = 'approved'"
        ).fetchone()[0]
        total_carbon = conn.execute(
            "SELECT COALESCE(SUM(carbon_saved), 0) FROM items WHERE review_status = 'approved'"
        ).fetchone()[0]
        total_users = conn.execute("SELECT COUNT(*) FROM users").fetchone()[0]
        total_points = conn.execute("SELECT COALESCE(SUM(points), 0) FROM users").fetchone()[0]
        total_orders = conn.execute("SELECT COUNT(*) FROM orders").fetchone()[0]
    return {
        "total_published": total_published,
        "pending_items": pending_items,
        "total_cycles": total_cycles,
        "total_carbon_kg": round(total_carbon, 2),
        "total_users": total_users,
        "total_points": total_points,
        "total_orders": total_orders,
        "trees_equivalent": round(total_carbon / TREE_ABSORB_PER_YEAR, 1),
    }


@app.get("/api/stats/summary")
def stats() -> dict:
    return stats_summary()


@app.get("/api/stats/trends")
def stats_trends(days: int = Query(14, ge=3, le=60)) -> dict:
    with database.db_session() as conn:
        rows = conn.execute(
            """
            SELECT date(o.updated_at) AS d, COUNT(*) AS cycles,
                   COALESCE(SUM(COALESCE(c.carbon_factor, 2.0)), 0) AS carbon
            FROM orders o
            JOIN items i ON i.id = o.item_id
            LEFT JOIN categories c ON c.name = i.category
            WHERE o.status = 'completed'
            GROUP BY date(o.updated_at) ORDER BY d DESC LIMIT ?
            """,
            (days,),
        ).fetchall()
        by_cat = conn.execute(
            """SELECT category, COUNT(*) AS cnt, COALESCE(SUM(carbon_saved), 0) AS carbon
               FROM items WHERE review_status = 'approved' GROUP BY category"""
        ).fetchall()
        by_status = conn.execute("SELECT status, COUNT(*) AS cnt FROM items GROUP BY status").fetchall()
    return {"trend": [dict(r) for r in reversed(rows)], "by_category": rows_to_dicts(by_cat), "by_status": rows_to_dicts(by_status)}


@app.get("/api/rank/users")
def rank_users(limit: int = Query(10, ge=1, le=50)) -> List[dict]:
    with database.db_session() as conn:
        rows = conn.execute(
            """
            SELECT u.id, u.name, u.college, u.points, u.avatar,
                   COALESCE(SUM(i.cycle_count), 0) AS cycles,
                   COALESCE(SUM(i.carbon_saved), 0) AS carbon_kg
            FROM users u LEFT JOIN items i ON i.owner_id = u.id
            GROUP BY u.id ORDER BY carbon_kg DESC, cycles DESC, u.points DESC LIMIT ?
            """,
            (limit,),
        ).fetchall()
    return rows_to_dicts(rows)


@app.get("/api/rank/colleges")
def rank_colleges() -> List[dict]:
    with database.db_session() as conn:
        rows = conn.execute(
            """
            SELECT u.college, COUNT(DISTINCT u.id) AS members,
                   COALESCE(SUM(i.cycle_count), 0) AS cycles,
                   COALESCE(SUM(i.carbon_saved), 0) AS carbon_kg
            FROM users u LEFT JOIN items i ON i.owner_id = u.id
            GROUP BY u.college ORDER BY carbon_kg DESC
            """
        ).fetchall()
    data = rows_to_dicts(rows)
    top = max((d["carbon_kg"] for d in data), default=0) or 1
    for d in data:
        d["carbon_kg"] = round(d["carbon_kg"], 2)
        d["percent"] = round(d["carbon_kg"] / top * 100)
    return data


# =======================================================================
# 订单
# =======================================================================
ORDER_SQL = """
    SELECT o.*, i.title AS item_title, i.category AS item_category, i.image AS item_image, i.price,
           b.name AS buyer_name, s.name AS seller_name
    FROM orders o
    JOIN items i ON i.id = o.item_id
    JOIN users b ON b.id = o.buyer_id
    JOIN users s ON s.id = o.seller_id
"""


def attach_counterparty(conn, order: dict, viewer_id: Optional[int]) -> dict:
    """为订单补充「交易对方」的联系方式，仅当查看者是订单参与方时返回。

    线下履约需要买卖双方取得联系（约定自提时间地点），因此把对方的
    姓名与联系方式开放给对侧参与方；非参与方（含管理员）一律不返回，
    避免联系方式被无关人员读取。
    """
    order["counterparty_name"] = None
    order["counterparty_contact"] = None
    if viewer_id is None:
        return order
    if viewer_id == order["buyer_id"]:
        other_id = order["seller_id"]
    elif viewer_id == order["seller_id"]:
        other_id = order["buyer_id"]
    else:
        return order
    row = conn.execute("SELECT name, contact FROM users WHERE id = ?", (other_id,)).fetchone()
    if row:
        order["counterparty_name"] = row["name"]
        order["counterparty_contact"] = row["contact"]
    return order


def _transition(conn, order_id: int, from_status: str, to_status: str):
    order = conn.execute("SELECT * FROM orders WHERE id = ?", (order_id,)).fetchone()
    if not order:
        raise HTTPException(status_code=404, detail="订单不存在")
    if order["status"] != from_status:
        raise HTTPException(status_code=400, detail=f"订单状态为「{STATUS_LABEL.get(order['status'], order['status'])}」，不能执行该操作")
    if to_status not in ORDER_TRANSITIONS.get(from_status, set()):
        raise HTTPException(status_code=400, detail=f"不允许从「{STATUS_LABEL.get(from_status, from_status)}」流转到「{STATUS_LABEL.get(to_status, to_status)}」")
    conn.execute("UPDATE orders SET status = ?, updated_at = datetime('now','localtime') WHERE id = ?", (to_status, order_id))
    return order


@app.get("/api/orders", response_model=List[OrderOut])
def list_orders(user: dict = Depends(current_user), role: Optional[str] = Query(None, pattern="^(buy|sell)$")) -> List[dict]:
    """本人相关订单（仅本人可见，身份取自会话）。"""
    sql = ORDER_SQL
    params: list = []
    if role == "buy":
        sql += " WHERE o.buyer_id = ?"
        params.append(user["id"])
    elif role == "sell":
        sql += " WHERE o.seller_id = ?"
        params.append(user["id"])
    else:
        sql += " WHERE o.buyer_id = ? OR o.seller_id = ?"
        params += [user["id"], user["id"]]
    sql += " ORDER BY o.id DESC"
    with database.db_session() as conn:
        rows = conn.execute(sql, params).fetchall()
        data = [attach_counterparty(conn, dict(r), user["id"]) for r in rows]
    return data


@app.post("/api/orders", response_model=OrderOut, status_code=201)
def create_order(payload: OrderCreate, user: dict = Depends(current_user)) -> dict:
    """买家发起预约（买家即当前登录用户）。

    并发安全：先以条件更新抢占物品（``WHERE status='available'``）并检查影响行数，
    抢占成功后再写入订单。这样即使多个买家同时预约，也只有一个能拿到物品，
    避免 check-then-act 竞态导致的重复订单（超卖）。
    """
    with database.db_session() as conn:
        item = conn.execute("SELECT * FROM items WHERE id = ?", (payload.item_id,)).fetchone()
        if not item:
            raise HTTPException(status_code=404, detail="物品不存在")
        if item["owner_id"] == user["id"]:
            raise HTTPException(status_code=400, detail="不能预约自己发布的物品")
        if item["review_status"] != "approved":
            raise HTTPException(status_code=400, detail="该物品尚未通过审核，暂不可预约")
        # 原子抢占：仅当仍为 available 时置为 reserved
        claimed = conn.execute(
            "UPDATE items SET status = 'reserved' WHERE id = ? AND status = 'available'",
            (payload.item_id,),
        )
        if claimed.rowcount == 0:
            raise HTTPException(status_code=400, detail="该物品当前不可预约")
        code = f"GC-{secrets.token_hex(3).upper()}"
        cur = conn.execute(
            "INSERT INTO orders (item_id, buyer_id, seller_id, status, pickup_code) VALUES (?, ?, ?, 'reserved', ?)",
            (payload.item_id, user["id"], item["owner_id"], code),
        )
        row = conn.execute(ORDER_SQL + " WHERE o.id = ?", (cur.lastrowid,)).fetchone()
        return attach_counterparty(conn, dict(row), user["id"])


@app.post("/api/orders/{order_id}/confirm", response_model=OrderOut)
def confirm_order(order_id: int, payload: OrderAction, user: dict = Depends(current_user)) -> dict:
    with database.db_session() as conn:
        order = conn.execute("SELECT * FROM orders WHERE id = ?", (order_id,)).fetchone()
        if not order:
            raise HTTPException(status_code=404, detail="订单不存在")
        if user["id"] != order["seller_id"]:
            raise HTTPException(status_code=403, detail="只有卖家可以确认预约")
        _transition(conn, order_id, "reserved", "confirmed")
        row = conn.execute(ORDER_SQL + " WHERE o.id = ?", (order_id,)).fetchone()
        return attach_counterparty(conn, dict(row), user["id"])


@app.post("/api/orders/{order_id}/complete", response_model=OrderOut)
def complete_order(order_id: int, payload: OrderAction, user: dict = Depends(current_user)) -> dict:
    """凭自提码完成流转（仅订单参与方）。"""
    with database.db_session() as conn:
        order = conn.execute("SELECT * FROM orders WHERE id = ?", (order_id,)).fetchone()
        if not order:
            raise HTTPException(status_code=404, detail="订单不存在")
        if user["id"] not in (order["buyer_id"], order["seller_id"]):
            raise HTTPException(status_code=403, detail="只有订单参与方可以确认完成")
        if payload.pickup_code != order["pickup_code"]:
            raise HTTPException(status_code=400, detail="自提码不正确")
        _transition(conn, order_id, "confirmed", "completed")
        item = conn.execute("SELECT * FROM items WHERE id = ?", (order["item_id"],)).fetchone()
        carbon = estimate_carbon(item["category"])
        conn.execute(
            "UPDATE items SET status = 'completed', cycle_count = cycle_count + 1, carbon_saved = carbon_saved + ? WHERE id = ?",
            (carbon, order["item_id"]),
        )
        database.add_points(conn, order["seller_id"], REWARD_CYCLE, f"完成流转《{item['title']}》获得碳积分")
        row = conn.execute(ORDER_SQL + " WHERE o.id = ?", (order_id,)).fetchone()
        return attach_counterparty(conn, dict(row), user["id"])


@app.post("/api/orders/{order_id}/cancel", response_model=OrderOut)
def cancel_order(order_id: int, payload: OrderAction, user: dict = Depends(current_user)) -> dict:
    with database.db_session() as conn:
        order = conn.execute("SELECT * FROM orders WHERE id = ?", (order_id,)).fetchone()
        if not order:
            raise HTTPException(status_code=404, detail="订单不存在")
        if user["id"] not in (order["buyer_id"], order["seller_id"]):
            raise HTTPException(status_code=403, detail="只有订单参与方可以取消")
        _transition(conn, order_id, order["status"], "cancelled")
        conn.execute("UPDATE items SET status = 'available' WHERE id = ?", (order["item_id"],))
        row = conn.execute(ORDER_SQL + " WHERE o.id = ?", (order_id,)).fetchone()
        return attach_counterparty(conn, dict(row), user["id"])


# =======================================================================
# 举报
# =======================================================================
REPORT_SQL = """
    SELECT r.*, i.title AS item_title, u.name AS reporter_name
    FROM reports r JOIN items i ON i.id = r.item_id JOIN users u ON u.id = r.reporter_id
"""

@app.post("/api/reports", status_code=201)
def create_report(payload: ReportCreate, user: dict = Depends(current_user)) -> dict:
    with database.db_session() as conn:
        item = conn.execute("SELECT * FROM items WHERE id = ?", (payload.item_id,)).fetchone()
        if not item:
            raise HTTPException(status_code=404, detail="物品不存在")
        if item["owner_id"] == user["id"]:
            raise HTTPException(status_code=400, detail="不能举报自己发布的物品")
        dup = conn.execute(
            "SELECT 1 FROM reports WHERE item_id = ? AND reporter_id = ? AND status = 'open'",
            (payload.item_id, user["id"]),
        ).fetchone()
        if dup:
            raise HTTPException(status_code=400, detail="你已举报过该物品，管理员正在处理")
        cur = conn.execute(
            "INSERT INTO reports (item_id, reporter_id, reason) VALUES (?, ?, ?)",
            (payload.item_id, user["id"], payload.reason),
        )
        row = conn.execute("SELECT * FROM reports WHERE id = ?", (cur.lastrowid,)).fetchone()
    return dict(row)


@app.get("/api/reports/mine", response_model=List[ReportOut])
def my_reports(user: dict = Depends(current_user)) -> List[dict]:
    """我提交过的举报及其处理进度（仅本人可见）。"""
    with database.db_session() as conn:
        rows = conn.execute(
            REPORT_SQL + " WHERE r.reporter_id = ? ORDER BY r.id DESC", (user["id"],)
        ).fetchall()
    return rows_to_dicts(rows)


# =======================================================================
# 后台管理（全部 require_admin，身份来自会话）
# =======================================================================
@app.get("/api/admin/summary")
def admin_summary(admin: dict = Depends(require_admin)) -> dict:
    with database.db_session() as conn:
        orders_by_status = {
            r["status"]: r["cnt"]
            for r in conn.execute("SELECT status, COUNT(*) AS cnt FROM orders GROUP BY status").fetchall()
        }
        open_reports = conn.execute("SELECT COUNT(*) FROM reports WHERE status = 'open'").fetchone()[0]
        flagged_items = conn.execute("SELECT COUNT(DISTINCT item_id) FROM reports WHERE status = 'open'").fetchone()[0]
        pending_review = conn.execute("SELECT COUNT(*) FROM items WHERE review_status = 'pending'").fetchone()[0]
    return {
        **stats_summary(),
        "orders_total": sum(orders_by_status.values()),
        "orders_completed": orders_by_status.get("completed", 0),
        "orders_active": sum(orders_by_status.get(s, 0) for s in ("reserved", "confirmed")),
        "open_reports": open_reports,
        "flagged_items": flagged_items,
        "pending_review": pending_review,
    }


ADMIN_ITEM_SQL = """
    SELECT i.id, i.title, i.category, i.price, i.status, i.image, i.cycle_count, i.carbon_saved,
           i.review_status, i.review_note, i.owner_id, i.updated_at,
           u.name AS owner_name,
           (SELECT COUNT(*) FROM reports r WHERE r.item_id = i.id AND r.status = 'open') AS report_count
    FROM items i JOIN users u ON u.id = i.owner_id
"""


@app.get("/api/admin/items", response_model=List[AdminItemOut])
def admin_items(
    admin: dict = Depends(require_admin),
    status: Optional[str] = None,
    review_status: Optional[str] = Query(None, pattern="^(approved|pending|rejected)$"),
) -> List[dict]:
    """管理员物品清单：待审核优先，其次按未处理举报数与更新时间排序。"""
    with database.db_session() as conn:
        sql = ADMIN_ITEM_SQL
        params: list = []
        where: list = []
        if status:
            where.append("i.status = ?")
            params.append(status)
        if review_status:
            where.append("i.review_status = ?")
            params.append(review_status)
        if where:
            sql += " WHERE " + " AND ".join(where)
        sql += """
            ORDER BY CASE i.review_status WHEN 'pending' THEN 0 WHEN 'rejected' THEN 1 ELSE 2 END,
                     report_count DESC, i.id DESC
        """
        rows = conn.execute(sql, params).fetchall()
    return rows_to_dicts(rows)


@app.post("/api/admin/items/{item_id}/review", response_model=AdminItemOut)
def admin_review_item(item_id: int, payload: ReviewAction, admin: dict = Depends(require_admin)) -> dict:
    """审核物品：通过后进入市集在售；驳回需给出理由，物品不再对外展示。"""
    with database.db_session() as conn:
        item = conn.execute("SELECT * FROM items WHERE id = ?", (item_id,)).fetchone()
        if not item:
            raise HTTPException(status_code=404, detail="物品不存在")
        if item["review_status"] == "approved" and payload.approve:
            raise HTTPException(status_code=400, detail="该物品已是审核通过状态")
        if not payload.approve and not (payload.note or "").strip():
            raise HTTPException(status_code=400, detail="驳回时必须填写理由")
        new_status = "approved" if payload.approve else "rejected"
        conn.execute(
            """UPDATE items SET review_status = ?, review_note = ?,
               updated_at = datetime('now','localtime') WHERE id = ?""",
            (new_status, (payload.note or None) if not payload.approve else None, item_id),
        )
        row = conn.execute(ADMIN_ITEM_SQL + " WHERE i.id = ?", (item_id,)).fetchone()
    return dict(row)


@app.post("/api/admin/items/{item_id}/offshelf", response_model=AdminItemOut)
def admin_offshelf(item_id: int, admin: dict = Depends(require_admin)) -> dict:
    with database.db_session() as conn:
        item = conn.execute("SELECT * FROM items WHERE id = ?", (item_id,)).fetchone()
        if not item:
            raise HTTPException(status_code=404, detail="物品不存在")
        if item["status"] == "offshelf":
            raise HTTPException(status_code=400, detail="物品已是下架状态")
        conn.execute(
            "UPDATE items SET status = 'offshelf', updated_at = datetime('now','localtime') WHERE id = ?",
            (item_id,),
        )
        row = conn.execute(ADMIN_ITEM_SQL + " WHERE i.id = ?", (item_id,)).fetchone()
    return dict(row)


@app.post("/api/admin/items/{item_id}/restore", response_model=AdminItemOut)
def admin_restore(item_id: int, admin: dict = Depends(require_admin)) -> dict:
    """恢复上架：未通过审核的物品恢复后仍不可见，需先审核通过。"""
    with database.db_session() as conn:
        item = conn.execute("SELECT * FROM items WHERE id = ?", (item_id,)).fetchone()
        if not item:
            raise HTTPException(status_code=404, detail="物品不存在")
        if item["status"] != "offshelf":
            raise HTTPException(status_code=400, detail="仅下架物品可恢复上架")
        conn.execute(
            "UPDATE items SET status = 'available', updated_at = datetime('now','localtime') WHERE id = ?",
            (item_id,),
        )
        row = conn.execute(ADMIN_ITEM_SQL + " WHERE i.id = ?", (item_id,)).fetchone()
    return dict(row)



@app.get("/api/admin/reports", response_model=List[ReportOut])
def admin_reports(admin: dict = Depends(require_admin), status: Optional[str] = None) -> List[dict]:
    with database.db_session() as conn:
        sql = REPORT_SQL
        params: list = []
        if status:
            sql += " WHERE r.status = ?"
            params.append(status)
        sql += " ORDER BY r.id DESC"
        rows = conn.execute(sql, params).fetchall()
    return rows_to_dicts(rows)


@app.post("/api/admin/reports/{report_id}/resolve", response_model=ReportOut)
def admin_resolve_report(report_id: int, admin: dict = Depends(require_admin)) -> dict:
    with database.db_session() as conn:
        report = conn.execute("SELECT * FROM reports WHERE id = ?", (report_id,)).fetchone()
        if not report:
            raise HTTPException(status_code=404, detail="举报不存在")
        if report["status"] == "resolved":
            raise HTTPException(status_code=400, detail="该举报已处理")
        conn.execute("UPDATE reports SET status = 'resolved' WHERE id = ?", (report_id,))
        row = conn.execute(REPORT_SQL + " WHERE r.id = ?", (report_id,)).fetchone()
    return dict(row)


@app.get("/api/admin/orders", response_model=List[OrderOut])
def admin_orders(
    admin: dict = Depends(require_admin),
    status: Optional[str] = None,
    limit: int = Query(50, ge=1, le=200),
    offset: int = Query(0, ge=0),
) -> List[dict]:
    """全平台订单（分页，按最新在前）。"""
    with database.db_session() as conn:
        sql = ORDER_SQL
        params: list = []
        if status:
            sql += " WHERE o.status = ?"
            params.append(status)
        sql += " ORDER BY o.id DESC LIMIT ? OFFSET ?"
        params += [limit, offset]
        rows = conn.execute(sql, params).fetchall()
    return rows_to_dicts(rows)


@app.get("/api/admin/users")
def admin_users(admin: dict = Depends(require_admin)) -> List[dict]:
    with database.db_session() as conn:
        rows = conn.execute(
            """
            SELECT u.id, u.name, u.student_no, u.college, u.role, u.points, u.avatar,
                   COUNT(DISTINCT i.id) AS item_count,
                   COALESCE(SUM(i.cycle_count), 0) AS cycles,
                   COALESCE(SUM(i.carbon_saved), 0) AS carbon_kg
            FROM users u LEFT JOIN items i ON i.owner_id = u.id
            GROUP BY u.id ORDER BY carbon_kg DESC, u.id
            """
        ).fetchall()
    data = rows_to_dicts(rows)
    for d in data:
        d["carbon_kg"] = round(d["carbon_kg"], 2)
    return data


@app.post("/api/admin/users/{user_id}/password")
def admin_reset_password(user_id: int, payload: AdminPasswordReset, admin: dict = Depends(require_admin)) -> dict:
    """管理员为用户重置密码（用于用户忘记密码的场景）。

    重置后注销该用户全部会话、清除其登录失败锁定，用户需用新密码重新登录。
    """
    with database.db_session() as conn:
        target = conn.execute("SELECT id, name, student_no FROM users WHERE id = ?", (user_id,)).fetchone()
        if not target:
            raise HTTPException(status_code=404, detail="用户不存在")
        conn.execute("UPDATE users SET password_hash = ? WHERE id = ?", (hash_password(payload.new_password), user_id))
        conn.execute("DELETE FROM sessions WHERE user_id = ?", (user_id,))
        # 该用户可能因连续失败被锁定，一并清除，避免重置后仍无法登录
        if target["student_no"]:
            auth.clear_login_failures(conn, target["student_no"])
        auth.clear_login_failures(conn, target["name"])
    return {"ok": True, "message": f"已重置「{target['name']}」的密码，请通知其使用新密码登录"}


@app.post("/api/admin/products", response_model=ProductOut, status_code=201)
def admin_create_product(payload: ProductCreate, admin: dict = Depends(require_admin)) -> dict:
    with database.db_session() as conn:
        cur = conn.execute(
            "INSERT INTO products (name, description, cost_points, stock, emoji) VALUES (?, ?, ?, ?, ?)",
            (payload.name, payload.description, payload.cost_points, payload.stock, payload.emoji),
        )
        row = conn.execute("SELECT * FROM products WHERE id = ?", (cur.lastrowid,)).fetchone()
    return dict(row)


@app.patch("/api/admin/products/{product_id}", response_model=ProductOut)
def admin_update_product(product_id: int, payload: ProductUpdate, admin: dict = Depends(require_admin)) -> dict:
    with database.db_session() as conn:
        product = conn.execute("SELECT * FROM products WHERE id = ?", (product_id,)).fetchone()
        if not product:
            raise HTTPException(status_code=404, detail="礼品不存在")
        fields = payload.model_dump(exclude_none=True)
        if not fields:
            raise HTTPException(status_code=400, detail="没有需要修改的内容")
        sets = ", ".join(f"{k} = ?" for k in fields)
        conn.execute(f"UPDATE products SET {sets} WHERE id = ?", (*fields.values(), product_id))
        row = conn.execute("SELECT * FROM products WHERE id = ?", (product_id,)).fetchone()
    return dict(row)


@app.delete("/api/admin/products/{product_id}")
def admin_delete_product(product_id: int, admin: dict = Depends(require_admin)) -> dict:
    with database.db_session() as conn:
        cur = conn.execute("DELETE FROM products WHERE id = ?", (product_id,))
        if cur.rowcount == 0:
            raise HTTPException(status_code=404, detail="礼品不存在")
    return {"ok": True}


# =======================================================================
# 静态资源与前端路由
# =======================================================================
@app.get("/favicon.svg")
def favicon() -> FileResponse:
    return FileResponse(STATIC_DIR / "favicon.svg", media_type="image/svg+xml")


# 挂载构建产物（/static/assets/* 等）
app.mount("/static", StaticFiles(directory=STATIC_DIR), name="static")


@app.get("/{full_path:path}", include_in_schema=False)
def spa_fallback(full_path: str):
    """SPA 前端路由回退：非 /api、非 /static 的路径一律返回 index.html。

    这样 /login、/me、/items/3 等前端路由可直接访问或刷新而不 404。
    未被上面路由匹配的 /api/* 会落到这里，显式返回 404 JSON 而非 HTML。
    """
    if full_path.startswith("api/"):
        raise HTTPException(status_code=404, detail="接口不存在")
    index = STATIC_DIR / "index.html"
    if not index.exists():
        raise HTTPException(status_code=503, detail="前端尚未构建，请在 web/ 目录执行 bun run build")
    return FileResponse(index)

