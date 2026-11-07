"""Pydantic 数据模型（绿循校园）。"""
from typing import Optional

from pydantic import BaseModel, Field, field_validator, model_validator

ITEM_STATUSES = ("available", "reserved", "completed", "offshelf")
REVIEW_STATUSES = ("approved", "pending", "rejected")


# ---------- 分类 ----------
class CategoryOut(BaseModel):
    id: int
    name: str
    icon: str = "box"
    carbon_factor: float = 2.0
    sort_order: int = 0
    protected: bool = False
    item_count: int = 0


class CategoryCreate(BaseModel):
    name: str = Field(min_length=1, max_length=10)
    icon: str = Field(default="box", max_length=30)
    carbon_factor: float = Field(default=2.0, ge=0, le=100)
    sort_order: int = Field(default=50, ge=0, le=999)


class CategoryUpdate(BaseModel):
    name: Optional[str] = Field(default=None, min_length=1, max_length=10)
    icon: Optional[str] = Field(default=None, max_length=30)
    carbon_factor: Optional[float] = Field(default=None, ge=0, le=100)
    sort_order: Optional[int] = Field(default=None, ge=0, le=999)


# ---------- 认证 ----------
class RegisterRequest(BaseModel):
    name: str = Field(min_length=1, max_length=20)
    student_no: str = Field(min_length=3, max_length=20)
    college: str = Field(default="未填写学院", max_length=30)
    password: str = Field(min_length=6, max_length=64)


class LoginRequest(BaseModel):
    login: str = Field(min_length=1, max_length=20, description="学号或姓名")
    password: str = Field(min_length=1, max_length=64)


class PasswordChange(BaseModel):
    old_password: str = Field(min_length=1, max_length=64)
    new_password: str = Field(min_length=6, max_length=64)


class AdminPasswordReset(BaseModel):
    """管理员为用户重置密码（用户忘记密码时使用）。"""
    new_password: str = Field(min_length=6, max_length=64)


# ---------- 用户 ----------
class UserOut(BaseModel):
    id: int
    name: str
    student_no: Optional[str] = None
    college: str
    role: str
    points: int
    avatar: Optional[str] = None
    bio: Optional[str] = None


class UserPublic(BaseModel):
    """对外公开的用户信息（不含联系方式等隐私）。"""
    id: int
    name: str
    college: str
    avatar: Optional[str] = None
    bio: Optional[str] = None


class ProfileUpdate(BaseModel):
    name: Optional[str] = Field(default=None, min_length=1, max_length=20)
    college: Optional[str] = Field(default=None, max_length=30)
    bio: Optional[str] = Field(default=None, max_length=200)


    @model_validator(mode="before")
    @classmethod
    def reject_contact(cls, value):
        if isinstance(value, dict) and "contact" in value:
            raise ValueError("平台不再收集联系方式，请使用订单站内沟通")
        return value


# ---------- 物品 ----------
class ItemCreate(BaseModel):
    title: str = Field(min_length=1, max_length=100)
    category: str = Field(min_length=1, max_length=10, description="分类名称，需为已启用的分类")
    description: str = Field(default="", max_length=500)
    price: float = Field(default=0, ge=0, le=99999)
    image: Optional[str] = Field(default=None, max_length=2_800_000)


class ItemUpdate(BaseModel):
    title: Optional[str] = Field(default=None, min_length=1, max_length=100)
    category: Optional[str] = Field(default=None, min_length=1, max_length=10)
    description: Optional[str] = Field(default=None, max_length=500)
    price: Optional[float] = Field(default=None, ge=0, le=99999)
    image: Optional[str] = Field(default=None, max_length=2_800_000)


class ItemOut(BaseModel):
    id: int
    owner_id: int
    owner_name: str = ""
    owner_college: str = ""
    owner_avatar: Optional[str] = None
    title: str
    category: str
    description: str
    price: float
    status: str
    review_status: str = "approved"
    review_note: Optional[str] = None
    image: Optional[str] = None
    cycle_count: int
    carbon_saved: float
    created_at: str


class ItemDetailOut(ItemOut):
    favorite_count: int = 0
    favorited: bool = False


# ---------- 收藏 ----------
class FavoriteOut(BaseModel):
    id: int
    item_id: int
    item_title: str = ""
    category: str = ""
    price: float = 0
    status: str = "available"
    image: Optional[str] = None
    owner_name: str = ""
    created_at: str


# ---------- 碳积分 / 商城 ----------
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


class ProductCreate(BaseModel):
    name: str = Field(min_length=1, max_length=40)
    description: str = Field(default="", max_length=200)
    cost_points: int = Field(ge=1, le=100000)
    stock: int = Field(default=0, ge=0, le=100000)
    emoji: str = Field(default="🎁", max_length=8)


class ProductUpdate(BaseModel):
    name: Optional[str] = Field(default=None, min_length=1, max_length=40)
    description: Optional[str] = Field(default=None, max_length=200)
    cost_points: Optional[int] = Field(default=None, ge=1, le=100000)
    stock: Optional[int] = Field(default=None, ge=0, le=100000)
    emoji: Optional[str] = Field(default=None, max_length=8)


class RedeemRequest(BaseModel):
    product_id: int


class RedeemOut(BaseModel):
    ok: bool
    message: str
    remaining_points: int
    redemption_id: int
    pickup_code: str


class RedemptionOut(BaseModel):
    id: int
    user_id: int
    product_id: Optional[int] = None
    product_name: str
    cost_points: int
    pickup_code: str
    created_at: str


# ---------- 订单 ----------
class OrderCreate(BaseModel):
    item_id: int


class OrderOut(BaseModel):
    id: int
    item_id: int
    item_title: str = ""
    item_category: str = ""
    item_image: Optional[str] = None
    buyer_id: int
    buyer_name: str = ""
    seller_id: int
    seller_name: str = ""
    status: str
    # Only the buyer receives an active order pickup credential.
    pickup_code: Optional[str] = None
    price: float = 0
    created_at: str
    updated_at: str


class OrderAction(BaseModel):
    pickup_code: Optional[str] = None


# ---------- 举报 ----------
class ReportCreate(BaseModel):
    item_id: int
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


class AdminItemOut(BaseModel):
    id: int
    title: str
    category: str
    price: float
    status: str
    review_status: str = "approved"
    review_note: Optional[str] = None
    image: Optional[str] = None
    cycle_count: int
    carbon_saved: float
    owner_id: int = 0
    owner_name: str = ""
    report_count: int = 0
    updated_at: Optional[str] = None


class ReviewAction(BaseModel):
    """管理员审核动作：通过 / 驳回（驳回需给出理由）。"""
    approve: bool
    note: Optional[str] = Field(default=None, max_length=200)


# ---------- 统计 ----------
class Health(BaseModel):
    status: str
    app: str
    version: str = ""


class MessageCreate(BaseModel):
    content: str = Field(min_length=1, max_length=1000)
    client_nonce: str = Field(min_length=8, max_length=64, pattern="^[a-zA-Z0-9_-]+$")

    @field_validator("content")
    @classmethod
    def trim_content(cls, value):
        value = value.strip()
        if not value:
            raise ValueError("消息内容不能为空")
        return value


class MessageOut(BaseModel):
    id: int
    order_id: int
    sender_id: int
    content: str
    client_nonce: str
    created_at: str


class MessageRead(BaseModel):
    last_message_id: int = Field(ge=1)
