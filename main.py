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


@app.get("/")
def index() -> FileResponse:
    return FileResponse(STATIC_DIR / "index.html")


app.mount("/static", StaticFiles(directory=STATIC_DIR), name="static")
