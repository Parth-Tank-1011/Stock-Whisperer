"""Prediction orchestration service."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Dict

from app.core.cache import TTLCache
from app.services.model_service import LSTMModelService
from app.services.sentiment_service import SentimentService
from app.services.yahoo_service import YahooFinanceService
from app.utils.symbols import normalize_symbol


@dataclass
class PredictionResult:
    symbol: str
    predicted_price: float
    trend: str
    confidence: float
    rmse: float
    accuracy_percent: float
    horizon_predictions: Dict[str, float]
    model_used: str
    model_metrics: Dict[str, float]
    model_accuracy: Dict[str, float]
    sentiment_label: str
    sentiment_score: float
    suggestion: str
    headlines_analyzed: int


class PredictionService:
    def __init__(
        self,
        yahoo_service: YahooFinanceService,
        model_service: LSTMModelService,
        prediction_cache: TTLCache,
    ) -> None:
        self.yahoo_service = yahoo_service
        self.model_service = model_service
        self.prediction_cache = prediction_cache
        self.sentiment_service = SentimentService()

    def predict(self, symbol: str) -> PredictionResult:
        normalized_symbol = normalize_symbol(symbol)
        cache_key = f"predict:{normalized_symbol}"

        cached = self.prediction_cache.get(cache_key)
        if cached is not None:
            return cached

        df = self.yahoo_service.get_historical_data(normalized_symbol)
        model_output = self.model_service.predict_multi_horizon(normalized_symbol, df)

        last_close = float(df["Close"].iloc[-1])
        predicted_price = float(model_output["predicted_price"])
        trend = "UP" if predicted_price >= last_close else "DOWN"

        headlines = self.yahoo_service.get_news_headlines(normalized_symbol)
        sentiment = self.sentiment_service.analyze_headlines(headlines)
        suggestion = self.sentiment_service.suggest_action(trend, sentiment.label)

        result = PredictionResult(
            symbol=normalized_symbol,
            predicted_price=predicted_price,
            trend=trend,
            confidence=float(model_output["confidence"]),
            rmse=float(model_output["rmse"]),
            accuracy_percent=float(model_output["accuracy_percent"]),
            horizon_predictions={
                key: float(value)
                for key, value in model_output["horizon_predictions"].items()
            },
            model_used=str(model_output["model_used"]),
            model_metrics={
                key: float(value)
                for key, value in model_output["model_metrics"].items()
            },
            model_accuracy={
                key: float(value)
                for key, value in model_output.get("model_accuracy", {}).items()
            },
            sentiment_label=sentiment.label,
            sentiment_score=sentiment.score,
            suggestion=suggestion,
            headlines_analyzed=sentiment.headlines_analyzed,
        )

        self.prediction_cache.set(cache_key, result)
        return result
