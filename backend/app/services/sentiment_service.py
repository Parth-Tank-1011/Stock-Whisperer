"""News sentiment scoring and suggestion helpers."""

from __future__ import annotations

import re
from dataclasses import dataclass
from typing import Iterable


POSITIVE_WORDS = {
    "beat", "beats", "growth", "surge", "strong", "bullish", "upgrade", "profit",
    "profits", "record", "gain", "gains", "rally", "expands", "expansion", "outperform",
    "optimistic", "positive", "improves", "improved", "momentum", "rebound", "higher",
}

NEGATIVE_WORDS = {
    "miss", "misses", "fall", "falls", "drop", "drops", "weak", "bearish", "downgrade",
    "loss", "losses", "risk", "risks", "warning", "lawsuit", "decline", "declines",
    "slowdown", "lower", "cuts", "cut", "slump", "volatility", "negative", "pressure",
}


@dataclass
class SentimentResult:
    score: float
    label: str
    headlines_analyzed: int


class SentimentService:
    @staticmethod
    def _tokenize(text: str) -> list[str]:
        return re.findall(r"[a-zA-Z]+", text.lower())

    def analyze_headlines(self, headlines: Iterable[str]) -> SentimentResult:
        items = [headline.strip() for headline in headlines if headline and headline.strip()]
        if not items:
            return SentimentResult(score=0.0, label="NEUTRAL", headlines_analyzed=0)

        positive_hits = 0
        negative_hits = 0

        for headline in items:
            tokens = self._tokenize(headline)
            positive_hits += sum(1 for token in tokens if token in POSITIVE_WORDS)
            negative_hits += sum(1 for token in tokens if token in NEGATIVE_WORDS)

        total_hits = positive_hits + negative_hits
        if total_hits == 0:
            return SentimentResult(score=0.0, label="NEUTRAL", headlines_analyzed=len(items))

        score = (positive_hits - negative_hits) / total_hits

        if score > 0.15:
            label = "POSITIVE"
        elif score < -0.15:
            label = "NEGATIVE"
        else:
            label = "NEUTRAL"

        return SentimentResult(score=float(score), label=label, headlines_analyzed=len(items))

    @staticmethod
    def suggest_action(trend: str, sentiment_label: str) -> str:
        trend_normalized = trend.upper()
        sentiment_normalized = sentiment_label.upper()

        if trend_normalized == "UP" and sentiment_normalized == "POSITIVE":
            return "BUY"
        if trend_normalized == "DOWN" and sentiment_normalized == "NEGATIVE":
            return "SELL"
        if trend_normalized == "UP" and sentiment_normalized == "NEGATIVE":
            return "HOLD"
        if trend_normalized == "DOWN" and sentiment_normalized == "POSITIVE":
            return "HOLD"
        return "HOLD"
