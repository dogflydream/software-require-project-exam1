"""绿循校园——校园闲置教材与物品循环流转系统。"""
from pathlib import Path
from typing import List, Optional

from fastapi import FastAPI, HTTPException, Query
from fastapi.responses import FileResponse
from fastapi.staticfiles import StaticFiles

import database
from models import Health, ItemCreate, ItemOut, PointLogOut, ProductOut, RedeemOut, RedeemRequest, UserOut

app = FastAPI(title="绿循校园", version="0.2.0")

STATIC_DIR = Path(__file__).parent / "static"

# 发布一件闲置奖励的碳积分
REWARD_PUBLISH = 10


def rows_to_dicts(rows) -> List[dict]:
    return [dict(r) for r in rows]


@app.on_event("startup")
def startup() -> None:
    database.init_db()


@app.get("/api/health", response_model=Health)
def health() -> Health:
    return Health(status="ok", app="绿循校园")


@app.get("/api/users", response_model=List[UserOut])
def list_users() -> List[dict]:
    conn = database.get_db()
    rows = conn.execute("SELECT * FROM users ORDER BY id").fetchall()
    conn.close()
    return rows_to_dicts(rows)


@app.get("/api/items", response_model=List[ItemOut])
def list_items(
    category: Optional[str] = Query(None, pattern="^(教材|考研|生活品)$"),
    keyword: Optional[str] = None,
) -> List[dict]:
    """物品列表检索与分类筛选。"""
    sql = """
        SELECT i.*, u.name AS owner_name, u.college AS owner_college
        FROM items i JOIN users u ON u.id = i.owner_id
        WHERE i.status IN ('available', 'reserved')
    """
    params: list = []
    if category:
        sql += " AND i.category = ?"
        params.append(category)
    if keyword:
        sql += " AND (i.title LIKE ? OR i.description LIKE ?)"
        params += [f"%{keyword}%", f"%{keyword}%"]
    sql += " ORDER BY i.created_at DESC, i.id DESC"
    conn = database.get_db()
    rows = conn.execute(sql, params).fetchall()
    conn.close()
    return rows_to_dicts(rows)


@app.post("/api/items", response_model=ItemOut, status_code=201)
def create_item(payload: ItemCreate) -> dict:
    """发布闲置物品。"""
    conn = database.get_db()
    owner = conn.execute("SELECT * FROM users WHERE id = ?", (payload.owner_id,)).fetchone()
    if not owner:
        conn.close()
        raise HTTPException(status_code=404, detail="用户不存在")
    cur = conn.execute(
        "INSERT INTO items (owner_id, title, category, description, price) VALUES (?, ?, ?, ?, ?)",
        (payload.owner_id, payload.title, payload.category, payload.description, payload.price),
    )
    # 发布闲置赠送碳积分并记录流水
    database.add_points(conn, payload.owner_id, REWARD_PUBLISH, f"发布闲置《{payload.title}》获得碳积分")
    row = conn.execute(
        """
        SELECT i.*, u.name AS owner_name, u.college AS owner_college
        FROM items i JOIN users u ON u.id = i.owner_id WHERE i.id = ?
        """,
        (cur.lastrowid,),
    ).fetchone()
    conn.commit()
    conn.close()
    return dict(row)


@app.get("/api/point-logs", response_model=List[PointLogOut])
def list_point_logs(user_id: int) -> List[dict]:
    """某用户的积分流水。"""
    conn = database.get_db()
    rows = conn.execute(
        "SELECT * FROM point_logs WHERE user_id = ? ORDER BY id DESC LIMIT 50", (user_id,)
    ).fetchall()
    conn.close()
    return rows_to_dicts(rows)


@app.get("/api/products", response_model=List[ProductOut])
def list_products() -> List[dict]:
    conn = database.get_db()
    rows = conn.execute("SELECT * FROM products ORDER BY cost_points").fetchall()
    conn.close()
    return rows_to_dicts(rows)


@app.post("/api/redeem", response_model=RedeemOut)
def redeem(payload: RedeemRequest) -> RedeemOut:
    """积分商城礼品兑换。"""
    conn = database.get_db()
    user = conn.execute("SELECT * FROM users WHERE id = ?", (payload.user_id,)).fetchone()
    product = conn.execute("SELECT * FROM products WHERE id = ?", (payload.product_id,)).fetchone()
    if not user or not product:
        conn.close()
        raise HTTPException(status_code=404, detail="用户或礼品不存在")
    if product["stock"] <= 0:
        conn.close()
        raise HTTPException(status_code=400, detail="礼品库存不足")
    if user["points"] < product["cost_points"]:
        conn.close()
        raise HTTPException(status_code=400, detail=f"碳积分不足，还差 {product['cost_points'] - user['points']} 分")
    remaining = database.add_points(conn, payload.user_id, -product["cost_points"], f"兑换礼品「{product['name']}」")
    conn.execute("UPDATE products SET stock = stock - 1 WHERE id = ?", (payload.product_id,))
    conn.commit()
    conn.close()
    return RedeemOut(ok=True, message=f"成功兑换「{product['name']}」，请到学生会办公室领取", remaining_points=remaining)


@app.get("/")
def index() -> FileResponse:
    return FileResponse(STATIC_DIR / "index.html")


app.mount("/static", StaticFiles(directory=STATIC_DIR), name="static")
