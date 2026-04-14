"""Pydantic API schemas."""

from datetime import date, datetime
from typing import Dict, List

from pydantic import BaseModel, Field


class HistoricalDataPoint(BaseModel):
    date: date
    open: float
    high: float
    low: float
    close: float
    volume: int


class HistoricalStockResponse(BaseModel):
    stock: str
    exchange_symbol: str
    currency: str
    data: List[HistoricalDataPoint]


class LivePriceResponse(BaseModel):
    stock: str
    exchange_symbol: str
    price: float
    change: float
    change_percent: float
    currency: str
    timestamp: datetime


class PredictionResponse(BaseModel):
    stock: str
    predicted_price: float = Field(..., description="Next day predicted closing price")
    prediction: str = Field(..., description="UP or DOWN")
    trend: str = Field(..., description="UP or DOWN")
    confidence: float = Field(..., ge=0.0, le=1.0)
    rmse: float = Field(..., ge=0.0, description="Best model validation RMSE for 1-day horizon")
    accuracy_percent: float = Field(..., ge=0.0, le=100.0, description="Best model 1-day accuracy percentage")
    sentiment: str = Field(..., description="POSITIVE, NEGATIVE, or NEUTRAL")
    sentiment_score: float = Field(..., ge=-1.0, le=1.0)
    headlines_analyzed: int = Field(..., ge=0)
    suggestion: str = Field(..., description="BUY, SELL, or HOLD")
    horizon_predictions: Dict[str, float] = Field(
        ..., description="Predicted prices by horizon (1d, 3d, 7d)"
    )
    model_used: str = Field(..., description="Best model selected by validation RMSE")
    model_metrics: Dict[str, float] = Field(
        ..., description="Validation RMSE (day-1) for each trained model"
    )
    model_accuracy: Dict[str, float] = Field(
        default_factory=dict,
        description="Accuracy percentage (day-1) for each trained model",
    )
