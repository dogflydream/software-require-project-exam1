"""Pydantic 数据模型（绿循校园）。"""
from typing import Optional

from pydantic import BaseModel, Field


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
