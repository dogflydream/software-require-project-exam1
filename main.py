"""绿循校园——校园闲置教材与物品循环流转系统。"""
import secrets
import sqlite3
from pathlib import Path
from typing import List, Optional

from fastapi import FastAPI, HTTPException, Query
from fastapi.responses import FileResponse
from fastapi.staticfiles import StaticFiles

import database
from models import (
    AdminItemOut, Health, ItemCreate, ItemOut, OrderAction, OrderCreate, OrderOut,
    PointLogOut, ProductOut, RedeemOut, RedeemRequest, ReportCreate, ReportOut,
    UserAction, UserOut,
)

app = FastAPI(title="绿循校园", version="0.4.0")

STATIC_DIR = Path(__file__).parent / "static"

# 发布一件闲置奖励的碳积分
REWARD_PUBLISH = 10
# 完成一次流转奖励卖家的碳积分
REWARD_CYCLE = 20

# 订单状态机：当前状态 -> 允许扭转的目标状态
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

# 核心指标算法：单次流转的减碳量估算系数（kg CO₂e，按物品类别）
CARBON_FACTOR = {"教材": 2.5, "考研": 2.0, "生活品": 3.5}


def estimate_carbon(category: str) -> float:
    """单次流转减碳量估算。"""
    return CARBON_FACTOR.get(category, 2.0)


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


@app.get("/api/stats/summary")
def stats_summary() -> dict:
    """平台全局环保汇总指标。"""
    conn = database.get_db()
    total_published = conn.execute("SELECT COUNT(*) FROM items").fetchone()[0]
    total_cycles = conn.execute("SELECT COALESCE(SUM(cycle_count), 0) FROM items").fetchone()[0]
    total_carbon = conn.execute("SELECT COALESCE(SUM(carbon_saved), 0) FROM items").fetchone()[0]
    total_users = conn.execute("SELECT COUNT(*) FROM users").fetchone()[0]
    total_points = conn.execute("SELECT COALESCE(SUM(points), 0) FROM users").fetchone()[0]
    conn.close()
    return {
        "total_published": total_published,
        "total_cycles": total_cycles,
        "total_carbon_kg": round(total_carbon, 2),
        "total_users": total_users,
        "total_points": total_points,
        "trees_equivalent": round(total_carbon / 18.0, 1),  # 一棵树每年约吸收 18kg CO₂
    }


@app.get("/api/rank/users")
def rank_users(limit: int = 10) -> List[dict]:
    """全校环保先锋榜：按个人累计减碳量排序。"""
    conn = database.get_db()
    rows = conn.execute(
        """
        SELECT u.id, u.name, u.college, u.points,
               COALESCE(SUM(i.cycle_count), 0) AS cycles,
               COALESCE(SUM(i.carbon_saved), 0) AS carbon_kg
        FROM users u LEFT JOIN items i ON i.owner_id = u.id
        GROUP BY u.id
        ORDER BY carbon_kg DESC, cycles DESC, u.points DESC
        LIMIT ?
        """,
        (limit,),
    ).fetchall()
    conn.close()
    return rows_to_dicts(rows)


@app.get("/api/rank/colleges")
def rank_colleges() -> List[dict]:
    """学院减碳排行大屏数据。"""
    conn = database.get_db()
    rows = conn.execute(
        """
        SELECT u.college,
               COUNT(DISTINCT u.id) AS members,
               COALESCE(SUM(i.cycle_count), 0) AS cycles,
               COALESCE(SUM(i.carbon_saved), 0) AS carbon_kg
        FROM users u LEFT JOIN items i ON i.owner_id = u.id
        GROUP BY u.college
        ORDER BY carbon_kg DESC
        """
    ).fetchall()
    conn.close()
    data = rows_to_dicts(rows)
    top = max((d["carbon_kg"] for d in data), default=0) or 1
    for d in data:
        d["carbon_kg"] = round(d["carbon_kg"], 2)
        d["percent"] = round(d["carbon_kg"] / top * 100)
    return data


ORDER_SQL = """
    SELECT o.*, i.title AS item_title, i.price,
           b.name AS buyer_name, s.name AS seller_name
    FROM orders o
    JOIN items i ON i.id = o.item_id
    JOIN users b ON b.id = o.buyer_id
    JOIN users s ON s.id = o.seller_id
"""


def _transition(conn, order_id: int, from_status: str, to_status: str) -> sqlite3.Row:
    """带状态机校验的订单状态扭转。"""
    order = conn.execute("SELECT * FROM orders WHERE id = ?", (order_id,)).fetchone()
    if not order:
        conn.close()
        raise HTTPException(status_code=404, detail="订单不存在")
    if order["status"] != from_status:
        conn.close()
        raise HTTPException(status_code=400, detail=f"订单状态为「{STATUS_LABEL[order['status']]}」，不能执行该操作")
    if to_status not in ORDER_TRANSITIONS.get(from_status, set()):
        conn.close()
        raise HTTPException(status_code=400, detail=f"不允许从「{STATUS_LABEL[from_status]}」流转到「{STATUS_LABEL[to_status]}」")
    conn.execute("UPDATE orders SET status = ?, updated_at = datetime('now','localtime') WHERE id = ?", (to_status, order_id))
    return order


@app.get("/api/orders", response_model=List[OrderOut])
def list_orders(user_id: int) -> List[dict]:
    """某用户相关的订单（我是买家或我是卖家）。"""
    conn = database.get_db()
    rows = conn.execute(
        ORDER_SQL + " WHERE o.buyer_id = ? OR o.seller_id = ? ORDER BY o.id DESC",
        (user_id, user_id),
    ).fetchall()
    conn.close()
    return rows_to_dicts(rows)


@app.post("/api/orders", response_model=OrderOut, status_code=201)
def create_order(payload: OrderCreate) -> dict:
    """买家发起预约意向：物品 available -> reserved，订单进入 reserved。"""
    conn = database.get_db()
    item = conn.execute("SELECT * FROM items WHERE id = ?", (payload.item_id,)).fetchone()
    if not item:
        conn.close()
        raise HTTPException(status_code=404, detail="物品不存在")
    if item["owner_id"] == payload.buyer_id:
        conn.close()
        raise HTTPException(status_code=400, detail="不能预约自己发布的物品")
    if item["status"] != "available":
        conn.close()
        raise HTTPException(status_code=400, detail="该物品当前不可预约")
    code = f"GC-{secrets.token_hex(3).upper()}"
    cur = conn.execute(
        "INSERT INTO orders (item_id, buyer_id, seller_id, status, pickup_code) VALUES (?, ?, ?, 'reserved', ?)",
        (payload.item_id, payload.buyer_id, item["owner_id"], code),
    )
    conn.execute("UPDATE items SET status = 'reserved' WHERE id = ?", (payload.item_id,))
    row = conn.execute(ORDER_SQL + " WHERE o.id = ?", (cur.lastrowid,)).fetchone()
    conn.commit()
    conn.close()
    return dict(row)


@app.post("/api/orders/{order_id}/confirm", response_model=OrderOut)
def confirm_order(order_id: int, payload: OrderAction) -> dict:
    """卖家确认预约意向：reserved -> confirmed（约定线下验货自提）。"""
    conn = database.get_db()
    order = _transition(conn, order_id, "reserved", "confirmed")
    if payload.user_id != order["seller_id"]:
        conn.rollback()
        conn.close()
        raise HTTPException(status_code=403, detail="只有卖家可以确认预约")
    row = conn.execute(ORDER_SQL + " WHERE o.id = ?", (order_id,)).fetchone()
    conn.commit()
    conn.close()
    return dict(row)


@app.post("/api/orders/{order_id}/complete", response_model=OrderOut)
def complete_order(order_id: int, payload: OrderAction) -> dict:
    """线下验货自提后确认完成流转：confirmed -> completed。
    物品循环度 +1、累计减碳量增加、卖家获得碳积分奖励。"""
    conn = database.get_db()
    order = conn.execute("SELECT * FROM orders WHERE id = ?", (order_id,)).fetchone()
    if not order:
        conn.close()
        raise HTTPException(status_code=404, detail="订单不存在")
    if payload.user_id not in (order["buyer_id"], order["seller_id"]):
        conn.close()
        raise HTTPException(status_code=403, detail="只有订单参与方可以确认完成")
    if payload.pickup_code != order["pickup_code"]:
        conn.close()
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
    conn.commit()
    conn.close()
    return dict(row)


@app.post("/api/orders/{order_id}/cancel", response_model=OrderOut)
def cancel_order(order_id: int, payload: OrderAction) -> dict:
    """取消订单，物品回到 available。"""
    conn = database.get_db()
    order = conn.execute("SELECT * FROM orders WHERE id = ?", (order_id,)).fetchone()
    if not order:
        conn.close()
        raise HTTPException(status_code=404, detail="订单不存在")
    if payload.user_id not in (order["buyer_id"], order["seller_id"]):
        conn.close()
        raise HTTPException(status_code=403, detail="只有订单参与方可以取消")
    _transition(conn, order_id, order["status"], "cancelled")
    conn.execute("UPDATE items SET status = 'available' WHERE id = ?", (order["item_id"],))
    row = conn.execute(ORDER_SQL + " WHERE o.id = ?", (order_id,)).fetchone()
    conn.commit()
    conn.close()
    return dict(row)


def _require_admin(conn: sqlite3.Connection, user_id: int) -> sqlite3.Row:
    """管理员权限校验。"""
    user = conn.execute("SELECT * FROM users WHERE id = ?", (user_id,)).fetchone()
    if not user or user["role"] != "admin":
        conn.close()
        raise HTTPException(status_code=403, detail="需要管理员权限")
    return user


@app.post("/api/reports", status_code=201)
def create_report(payload: ReportCreate) -> dict:
    """用户举报违规物品。"""
    conn = database.get_db()
    item = conn.execute("SELECT * FROM items WHERE id = ?", (payload.item_id,)).fetchone()
    if not item:
        conn.close()
        raise HTTPException(status_code=404, detail="物品不存在")
    cur = conn.execute(
        "INSERT INTO reports (item_id, reporter_id, reason) VALUES (?, ?, ?)",
        (payload.item_id, payload.reporter_id, payload.reason),
    )
    row = conn.execute("SELECT * FROM reports WHERE id = ?", (cur.lastrowid,)).fetchone()
    conn.commit()
    conn.close()
    return dict(row)


@app.get("/api/admin/summary")
def admin_summary(user_id: int) -> dict:
    """后台全局汇总数据卡片。"""
    conn = database.get_db()
    try:
        _require_admin(conn, user_id)
        orders_by_status = {
            r["status"]: r["cnt"]
            for r in conn.execute("SELECT status, COUNT(*) AS cnt FROM orders GROUP BY status").fetchall()
        }
        open_reports = conn.execute("SELECT COUNT(*) FROM reports WHERE status = 'open'").fetchone()[0]
        flagged_items = conn.execute(
            "SELECT COUNT(DISTINCT item_id) FROM reports WHERE status = 'open'"
        ).fetchone()[0]
    finally:
        conn.close()
    return {
        **stats_summary(),
        "orders_total": sum(orders_by_status.values()),
        "orders_completed": orders_by_status.get("completed", 0),
        "orders_active": sum(orders_by_status.get(s, 0) for s in ("reserved", "confirmed")),
        "open_reports": open_reports,
        "flagged_items": flagged_items,
    }


@app.get("/api/admin/items", response_model=List[AdminItemOut])
def admin_items(user_id: int) -> List[dict]:
    """管理员物品清单（含已下架），并附带未处理举报数。"""
    conn = database.get_db()
    try:
        _require_admin(conn, user_id)
        rows = conn.execute(
            """
            SELECT i.id, i.title, i.category, i.price, i.status, i.cycle_count, i.carbon_saved,
                   u.name AS owner_name,
                   (SELECT COUNT(*) FROM reports r WHERE r.item_id = i.id AND r.status = 'open') AS report_count
            FROM items i JOIN users u ON u.id = i.owner_id
            ORDER BY report_count DESC, i.id DESC
            """
        ).fetchall()
    finally:
        conn.close()
    return rows_to_dicts(rows)


@app.post("/api/admin/items/{item_id}/offshelf", response_model=AdminItemOut)
def admin_offshelf(item_id: int, payload: UserAction) -> dict:
    """管理员下架违规物品。"""
    conn = database.get_db()
    try:
        _require_admin(conn, payload.user_id)
        item = conn.execute("SELECT * FROM items WHERE id = ?", (item_id,)).fetchone()
        if not item:
            raise HTTPException(status_code=404, detail="物品不存在")
        if item["status"] == "offshelf":
            raise HTTPException(status_code=400, detail="物品已是下架状态")
        conn.execute("UPDATE items SET status = 'offshelf' WHERE id = ?", (item_id,))
        row = conn.execute(
            """
            SELECT i.*, u.name AS owner_name,
                   (SELECT COUNT(*) FROM reports r WHERE r.item_id = i.id AND r.status = 'open') AS report_count
            FROM items i JOIN users u ON u.id = i.owner_id WHERE i.id = ?
            """,
            (item_id,),
        ).fetchone()
        conn.commit()
    finally:
        conn.close()
    return dict(row)


@app.post("/api/admin/items/{item_id}/restore", response_model=AdminItemOut)
def admin_restore(item_id: int, payload: UserAction) -> dict:
    """管理员恢复上架（仅当无进行中订单时回到 available）。"""
    conn = database.get_db()
    try:
        _require_admin(conn, payload.user_id)
        item = conn.execute("SELECT * FROM items WHERE id = ?", (item_id,)).fetchone()
        if not item:
            raise HTTPException(status_code=404, detail="物品不存在")
        if item["status"] != "offshelf":
            raise HTTPException(status_code=400, detail="仅下架物品可恢复上架")
        conn.execute("UPDATE items SET status = 'available' WHERE id = ?", (item_id,))
        row = conn.execute(
            """
            SELECT i.*, u.name AS owner_name,
                   (SELECT COUNT(*) FROM reports r WHERE r.item_id = i.id AND r.status = 'open') AS report_count
            FROM items i JOIN users u ON u.id = i.owner_id WHERE i.id = ?
            """,
            (item_id,),
        ).fetchone()
        conn.commit()
    finally:
        conn.close()
    return dict(row)


@app.get("/api/admin/reports", response_model=List[ReportOut])
def admin_reports(user_id: int, status: Optional[str] = None) -> List[dict]:
    """管理员查看举报列表。"""
    conn = database.get_db()
    try:
        _require_admin(conn, user_id)
        sql = """
            SELECT r.*, i.title AS item_title, u.name AS reporter_name
            FROM reports r JOIN items i ON i.id = r.item_id JOIN users u ON u.id = r.reporter_id
        """
        params: list = []
        if status:
            sql += " WHERE r.status = ?"
            params.append(status)
        sql += " ORDER BY r.id DESC"
        rows = conn.execute(sql, params).fetchall()
    finally:
        conn.close()
    return rows_to_dicts(rows)


@app.post("/api/admin/reports/{report_id}/resolve", response_model=ReportOut)
def admin_resolve_report(report_id: int, payload: UserAction) -> dict:
    """管理员处理完结举报。"""
    conn = database.get_db()
    try:
        _require_admin(conn, payload.user_id)
        report = conn.execute("SELECT * FROM reports WHERE id = ?", (report_id,)).fetchone()
        if not report:
            raise HTTPException(status_code=404, detail="举报不存在")
        if report["status"] == "resolved":
            raise HTTPException(status_code=400, detail="该举报已处理")
        conn.execute("UPDATE reports SET status = 'resolved' WHERE id = ?", (report_id,))
        row = conn.execute(
            """
            SELECT r.*, i.title AS item_title, u.name AS reporter_name
            FROM reports r JOIN items i ON i.id = r.item_id JOIN users u ON u.id = r.reporter_id
            WHERE r.id = ?
            """,
            (report_id,),
        ).fetchone()
        conn.commit()
    finally:
        conn.close()
    return dict(row)


@app.get("/")
def index() -> FileResponse:
    return FileResponse(STATIC_DIR / "index.html")


app.mount("/static", StaticFiles(directory=STATIC_DIR), name="static")
