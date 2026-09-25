"""Pydantic 数据模型（绿循校园）。"""
from pydantic import BaseModel


class Health(BaseModel):
    status: str
    app: str
