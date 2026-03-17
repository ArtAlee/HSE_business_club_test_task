from datetime import datetime

from pydantic import BaseModel, ConfigDict, Field


class TelegramAuthRequest(BaseModel):
    init_data: str = Field(..., description="Telegram Mini App initData")


class TokenResponse(BaseModel):
    access_token: str
    token_type: str = "bearer"


class UserInfo(BaseModel):
    telegram_id: int
    first_name: str | None = None
    last_name: str | None = None
    username: str | None = None


class VisitHistoryItem(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    visited_at: datetime
    point_id: int
    point_name: str
    points_awarded: int


class PurchaseHistoryItem(BaseModel):
    purchased_at: datetime
    product_id: int
    product_name: str
    points_spent: int


class CabinetResponse(BaseModel):
    balance: int
    history: list[VisitHistoryItem]
    purchases: list[PurchaseHistoryItem]


class ScanRequest(BaseModel):
    token: str


class ScanResponse(BaseModel):
    message: str
    awarded_points: int
    balance: int
    point_id: int
    point_name: str


class ProductCreate(BaseModel):
    name: str
    description: str | None = None
    price_points: int = Field(..., ge=1)
    stock: int = Field(..., ge=0)


class ProductRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    name: str
    description: str | None = None
    price_points: int
    stock: int


class PointCreate(BaseModel):
    name: str
    description: str | None = None
    reward_points: int = Field(..., ge=1)


class PointRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    name: str
    description: str | None = None
    reward_points: int


class QrTokenResponse(BaseModel):
    point_id: int
    point_name: str
    token: str
    expires_at: datetime
    ttl_seconds: int


class RedemptionResponse(BaseModel):
    message: str
    product_id: int
    product_name: str
    remaining_stock: int
    spent_points: int
    balance: int


class LeaderboardItem(BaseModel):
    telegram_id: int
    first_name: str | None = None
    last_name: str | None = None
    username: str | None = None
    balance: int
