"""API route definitions for stock history and prediction."""

from __future__ import annotations

from typing import Annotated

from fastapi import APIRouter, Depends, Path
from fastapi.concurrency import run_in_threadpool

from app.core.cache import TTLCache
from app.core.config import settings
from app.models.schemas import (
    HistoricalDataPoint,
    HistoricalStockResponse,
    LivePriceResponse,
    PredictionResponse,
)
from app.services.model_service import LSTMModelService
from app.services.prediction_service import PredictionService
from app.services.yahoo_service import YahooFinanceService
from app.utils.symbols import STOCK_SYMBOL_PATTERN, normalize_symbol, stock_code


router = APIRouter(tags=["stocks"])

SymbolPath = Annotated[
    str,
    Path(
        min_length=2,
        max_length=32,
        pattern=STOCK_SYMBOL_PATTERN,
        description="Stock symbol, e.g., RELIANCE.NS or TCS.BO",
    ),
]

history_cache = TTLCache(ttl_seconds=settings.cache_ttl_seconds)
prediction_cache = TTLCache(ttl_seconds=settings.prediction_cache_ttl_seconds)
live_cache = TTLCache(ttl_seconds=settings.live_cache_ttl_seconds)
yahoo_service = YahooFinanceService(cache=history_cache)
yahoo_live_service = YahooFinanceService(cache=live_cache)
model_service = LSTMModelService()
prediction_service = PredictionService(
    yahoo_service=yahoo_service,
    model_service=model_service,
    prediction_cache=prediction_cache,
)


def get_yahoo_service() -> YahooFinanceService:
    return yahoo_service


def get_live_service() -> YahooFinanceService:
    return yahoo_live_service


def get_prediction_service() -> PredictionService:
    return prediction_service


@router.get("/stock/{symbol}", response_model=HistoricalStockResponse)
async def get_stock_data(
    symbol: SymbolPath,
    service: YahooFinanceService = Depends(get_yahoo_service),
) -> HistoricalStockResponse:
    normalized = normalize_symbol(symbol)
    df = await run_in_threadpool(service.get_historical_data, normalized)

    records = [
        HistoricalDataPoint(
            date=index.date(),
            open=float(row["Open"]),
            high=float(row["High"]),
            low=float(row["Low"]),
            close=float(row["Close"]),
            volume=int(row["Volume"]),
        )
        for index, row in df.iterrows()
    ]

    return HistoricalStockResponse(
        stock=stock_code(normalized),
        exchange_symbol=normalized,
        currency="INR",
        data=records,
    )


@router.get("/live/{symbol}", response_model=LivePriceResponse)
async def get_live_price(
    symbol: SymbolPath,
    service: YahooFinanceService = Depends(get_live_service),
) -> LivePriceResponse:
    normalized = normalize_symbol(symbol)
    quote = await run_in_threadpool(service.get_live_quote, normalized)
    return LivePriceResponse(**quote)


@router.get("/predict/{symbol}", response_model=PredictionResponse)
async def predict_stock(
    symbol: SymbolPath,
    service: PredictionService = Depends(get_prediction_service),
) -> PredictionResponse:
    normalized = normalize_symbol(symbol)
    result = await run_in_threadpool(service.predict, normalized)
    rounded_horizons = {key: round(value, 2) for key, value in result.horizon_predictions.items()}

    return PredictionResponse(
        stock=stock_code(result.symbol),
        predicted_price=round(result.predicted_price, 2),
        prediction=result.trend,
        trend=result.trend,
        confidence=round(result.confidence, 4),
        rmse=round(result.rmse, 4),
        accuracy_percent=round(result.accuracy_percent, 2),
        sentiment=result.sentiment_label,
        sentiment_score=round(result.sentiment_score, 4),
        headlines_analyzed=result.headlines_analyzed,
        suggestion=result.suggestion,
        horizon_predictions=rounded_horizons,
        model_used=result.model_used,
        model_metrics={key: round(value, 4) for key, value in result.model_metrics.items()},
        model_accuracy={key: round(value, 2) for key, value in result.model_accuracy.items()},
    )
