"""Pydantic 数据模型（绿循校园）。"""
from typing import Optional

from pydantic import BaseModel, Field


class PointLogOut(BaseModel):
    id: int
    user_id: int
    delta: int
    reason: str
    created_at: str


class ProductOut(BaseModel):
    id: int
    name: str
    description: str
    cost_points: int
    stock: int
    emoji: str


class RedeemRequest(BaseModel):
    user_id: int
    product_id: int


class OrderCreate(BaseModel):
    item_id: int
    buyer_id: int


class OrderOut(BaseModel):
    id: int
    item_id: int
    item_title: str = ""
    buyer_id: int
    buyer_name: str = ""
    seller_id: int
    seller_name: str = ""
    status: str
    pickup_code: str
    price: float = 0
    created_at: str
    updated_at: str


class OrderAction(BaseModel):
    user_id: int
    pickup_code: Optional[str] = None


class ReportCreate(BaseModel):
    item_id: int
    reporter_id: int
    reason: str = Field(min_length=2, max_length=200)


class ReportOut(BaseModel):
    id: int
    item_id: int
    item_title: str = ""
    reporter_id: int
    reporter_name: str = ""
    reason: str
    status: str
    created_at: str


class UserAction(BaseModel):
    user_id: int


class AdminItemOut(BaseModel):
    id: int
    title: str
    category: str
    price: float
    status: str
    cycle_count: int
    carbon_saved: float
    owner_name: str = ""
    report_count: int = 0


class RedeemOut(BaseModel):
    ok: bool
    message: str
    remaining_points: int


class Health(BaseModel):
    status: str
    app: str


class UserOut(BaseModel):
    id: int
    name: str
    college: str
    role: str
    points: int


class ItemCreate(BaseModel):
    owner_id: int
    title: str = Field(min_length=1, max_length=100)
    category: str = Field(pattern="^(教材|考研|生活品)$")
    description: str = Field(default="", max_length=500)
    price: float = Field(default=0, ge=0)


class ItemOut(BaseModel):
    id: int
    owner_id: int
    owner_name: str = ""
    owner_college: str = ""
    title: str
    category: str
    description: str
    price: float
    status: str
    cycle_count: int
    carbon_saved: float
    created_at: str
