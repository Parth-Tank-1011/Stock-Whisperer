"""Auth/watchlist/alerts API schemas."""

from __future__ import annotations

from datetime import datetime
from typing import List, Literal

from pydantic import BaseModel, Field

from app.models.schemas import LivePriceResponse
from app.utils.symbols import STOCK_SYMBOL_PATTERN


class SignupRequest(BaseModel):
    username: str = Field(..., min_length=3, max_length=64, pattern=r"^[A-Za-z0-9_]+$")
    email: str = Field(..., min_length=5, max_length=128, pattern=r"^[^@\s]+@[^@\s]+\.[^@\s]+$")
    password: str = Field(..., min_length=8, max_length=128)


class LoginRequest(BaseModel):
    username: str = Field(..., min_length=3, max_length=128)
    password: str = Field(..., min_length=8, max_length=128)


class AuthTokenResponse(BaseModel):
    access_token: str
    token_type: str = "bearer"


class UserResponse(BaseModel):
    id: int
    username: str
    email: str
    created_at: datetime


class WatchlistAddRequest(BaseModel):
    symbol: str = Field(..., min_length=2, max_length=32, pattern=STOCK_SYMBOL_PATTERN)


class WatchlistItemResponse(BaseModel):
    id: int
    symbol: str
    created_at: datetime


class WatchlistListResponse(BaseModel):
    items: List[WatchlistItemResponse]


class WatchlistQuoteRow(BaseModel):
    symbol: str
    quote: LivePriceResponse | None = None
    error: str | None = None


class WatchlistQuotesResponse(BaseModel):
    items: List[WatchlistQuoteRow]


class AlertCreateRequest(BaseModel):
    symbol: str = Field(..., min_length=2, max_length=32, pattern=STOCK_SYMBOL_PATTERN)
    target_price: float = Field(..., gt=0)
    direction: Literal["ABOVE", "BELOW"]


class AlertResponse(BaseModel):
    id: int
    symbol: str
    target_price: float
    direction: str
    is_active: bool
    last_price: float | None = None
    triggered_at: datetime | None = None
    created_at: datetime


class AlertListResponse(BaseModel):
    items: List[AlertResponse]


class AlertCheckItem(BaseModel):
    alert_id: int
    symbol: str
    target_price: float
    direction: str
    current_price: float | None = None
    triggered: bool
    triggered_at: datetime | None = None
    error: str | None = None


class AlertCheckResponse(BaseModel):
    checked_at: datetime
    results: List[AlertCheckItem]
