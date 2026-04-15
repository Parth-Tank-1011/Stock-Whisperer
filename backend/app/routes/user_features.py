"""Watchlist and alert management routes."""

from __future__ import annotations

import logging
from datetime import datetime, timezone
from typing import Annotated

from fastapi import APIRouter, Depends, HTTPException, Path, status
from sqlalchemy.orm import Session

from app.core.cache import TTLCache
from app.core.config import settings
from app.core.exceptions import DataFetchError, InputValidationError, InvalidStockSymbolError
from app.db.database import get_db
from app.db.models import Alert, User, WatchlistItem
from app.models.auth_schemas import (
    AlertCheckItem,
    AlertCheckResponse,
    AlertCreateRequest,
    AlertListResponse,
    AlertResponse,
    WatchlistAddRequest,
    WatchlistItemResponse,
    WatchlistListResponse,
    WatchlistQuoteRow,
    WatchlistQuotesResponse,
)
from app.models.schemas import LivePriceResponse
from app.services.yahoo_service import YahooFinanceService
from app.utils.symbols import STOCK_SYMBOL_PATTERN, normalize_symbol


logger = logging.getLogger(__name__)
router = APIRouter(tags=["product"])

SymbolPath = Annotated[
    str,
    Path(
        min_length=2,
        max_length=32,
        pattern=STOCK_SYMBOL_PATTERN,
        description="Stock symbol, e.g., RELIANCE.NS or TCS.BO",
    ),
]

live_cache = TTLCache(ttl_seconds=settings.live_cache_ttl_seconds)
yahoo_live_service = YahooFinanceService(cache=live_cache)


def get_guest_user(db: Session = Depends(get_db)) -> User:
    """Return a shared guest user so watchlist/alerts work without auth."""

    guest_username = "guest"
    guest_email = "guest@stockwhisperer.local"

    user = db.query(User).filter(User.username == guest_username).first()
    if user is not None:
        return user

    user = User(
        username=guest_username,
        email=guest_email,
        password_hash="disabled",
    )
    db.add(user)
    db.commit()
    db.refresh(user)
    return user


@router.get("/watchlist", response_model=WatchlistListResponse)
def list_watchlist(
    db: Session = Depends(get_db),
    user: User = Depends(get_guest_user),
) -> WatchlistListResponse:
    items = (
        db.query(WatchlistItem)
        .filter(WatchlistItem.user_id == user.id)
        .order_by(WatchlistItem.created_at.desc())
        .all()
    )

    return WatchlistListResponse(
        items=[
            WatchlistItemResponse(id=item.id, symbol=item.symbol, created_at=item.created_at)
            for item in items
        ]
    )


@router.get("/watchlist/quotes", response_model=WatchlistQuotesResponse)
def watchlist_live_quotes(
    db: Session = Depends(get_db),
    user: User = Depends(get_guest_user),
) -> WatchlistQuotesResponse:
    """Return the latest live quote for each watchlist symbol (best-effort per row)."""

    items = (
        db.query(WatchlistItem)
        .filter(WatchlistItem.user_id == user.id)
        .order_by(WatchlistItem.created_at.desc())
        .all()
    )

    rows: list[WatchlistQuoteRow] = []
    for item in items:
        try:
            raw = yahoo_live_service.get_live_quote(item.symbol)
            quote = LivePriceResponse(**raw)
            rows.append(WatchlistQuoteRow(symbol=item.symbol, quote=quote, error=None))
        except (DataFetchError, InvalidStockSymbolError, InputValidationError) as exc:
            rows.append(WatchlistQuoteRow(symbol=item.symbol, quote=None, error=str(exc)))
        except Exception:
            logger.exception("Watchlist quote failed for user_id=%s symbol=%s", user.id, item.symbol)
            rows.append(WatchlistQuoteRow(symbol=item.symbol, quote=None, error="Live quote unavailable"))

    return WatchlistQuotesResponse(items=rows)


@router.post("/watchlist", response_model=WatchlistItemResponse)
def add_watchlist_item(
    payload: WatchlistAddRequest,
    db: Session = Depends(get_db),
    user: User = Depends(get_guest_user),
) -> WatchlistItemResponse:
    symbol = normalize_symbol(payload.symbol)

    existing = (
        db.query(WatchlistItem)
        .filter(WatchlistItem.user_id == user.id, WatchlistItem.symbol == symbol)
        .first()
    )
    if existing is not None:
        raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail="Symbol already in watchlist")

    item = WatchlistItem(user_id=user.id, symbol=symbol)
    db.add(item)
    db.commit()
    db.refresh(item)

    return WatchlistItemResponse(id=item.id, symbol=item.symbol, created_at=item.created_at)


@router.delete("/watchlist/{symbol}")
def remove_watchlist_item(
    symbol: SymbolPath,
    db: Session = Depends(get_db),
    user: User = Depends(get_guest_user),
) -> dict:
    normalized = normalize_symbol(symbol)
    item = (
        db.query(WatchlistItem)
        .filter(WatchlistItem.user_id == user.id, WatchlistItem.symbol == normalized)
        .first()
    )
    if item is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Symbol not found in watchlist")

    db.delete(item)
    db.commit()
    return {"status": "removed", "symbol": normalized}


@router.get("/alerts", response_model=AlertListResponse)
def list_alerts(
    db: Session = Depends(get_db),
    user: User = Depends(get_guest_user),
) -> AlertListResponse:
    alerts = (
        db.query(Alert)
        .filter(Alert.user_id == user.id)
        .order_by(Alert.created_at.desc())
        .all()
    )

    return AlertListResponse(
        items=[
            AlertResponse(
                id=alert.id,
                symbol=alert.symbol,
                target_price=alert.target_price,
                direction=alert.direction,
                is_active=alert.is_active,
                last_price=alert.last_price,
                triggered_at=alert.triggered_at,
                created_at=alert.created_at,
            )
            for alert in alerts
        ]
    )


@router.post("/alerts", response_model=AlertResponse)
def create_alert(
    payload: AlertCreateRequest,
    db: Session = Depends(get_db),
    user: User = Depends(get_guest_user),
) -> AlertResponse:
    symbol = normalize_symbol(payload.symbol)

    alert = Alert(
        user_id=user.id,
        symbol=symbol,
        target_price=float(payload.target_price),
        direction=payload.direction,
        is_active=True,
    )
    db.add(alert)
    db.commit()
    db.refresh(alert)

    return AlertResponse(
        id=alert.id,
        symbol=alert.symbol,
        target_price=alert.target_price,
        direction=alert.direction,
        is_active=alert.is_active,
        last_price=alert.last_price,
        triggered_at=alert.triggered_at,
        created_at=alert.created_at,
    )


@router.delete("/alerts/{alert_id}")
def delete_alert(
    alert_id: int,
    db: Session = Depends(get_db),
    user: User = Depends(get_guest_user),
) -> dict:
    alert = db.query(Alert).filter(Alert.id == alert_id, Alert.user_id == user.id).first()
    if alert is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Alert not found")

    db.delete(alert)
    db.commit()
    return {"status": "deleted", "alert_id": alert_id}


@router.post("/alerts/check", response_model=AlertCheckResponse)
def check_alerts(
    db: Session = Depends(get_db),
    user: User = Depends(get_guest_user),
) -> AlertCheckResponse:
    active_alerts = (
        db.query(Alert)
        .filter(Alert.user_id == user.id, Alert.is_active.is_(True))
        .order_by(Alert.created_at.asc())
        .all()
    )

    checked_at = datetime.now(timezone.utc)
    results: list[AlertCheckItem] = []

    if not active_alerts:
        return AlertCheckResponse(checked_at=checked_at, results=[])

    symbol_to_price: dict[str, float] = {}

    for alert in active_alerts:
        current_price: float | None = None
        failure_message: str | None = None

        try:
            if alert.symbol not in symbol_to_price:
                quote = yahoo_live_service.get_live_quote(alert.symbol)
                symbol_to_price[alert.symbol] = float(quote["price"])
            current_price = symbol_to_price[alert.symbol]
        except DataFetchError:
            failure_message = "Live quote fetch failed"
            logger.warning("Live quote fetch failed for alert_id=%s symbol=%s", alert.id, alert.symbol)
        except Exception:
            failure_message = "Live quote unavailable"
            logger.exception("Unexpected alert quote error for alert_id=%s symbol=%s", alert.id, alert.symbol)

        is_triggered = False
        if current_price is not None:
            is_triggered = (current_price >= alert.target_price) if alert.direction == "ABOVE" else (current_price <= alert.target_price)
            alert.last_price = current_price
            if is_triggered:
                alert.is_active = False
                alert.triggered_at = checked_at

        results.append(
            AlertCheckItem(
                alert_id=alert.id,
                symbol=alert.symbol,
                target_price=alert.target_price,
                direction=alert.direction,
                current_price=current_price,
                triggered=is_triggered,
                triggered_at=alert.triggered_at,
                error=failure_message,
            )
        )

    db.commit()

    return AlertCheckResponse(checked_at=checked_at, results=results)
