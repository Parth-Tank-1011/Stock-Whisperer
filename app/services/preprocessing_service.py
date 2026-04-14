"""Preprocessing utilities for feature engineering and sequence preparation."""

from __future__ import annotations

from typing import Sequence, Tuple

import numpy as np
import pandas as pd
from sklearn.preprocessing import MinMaxScaler


FEATURE_COLUMNS = [
    "Open",
    "High",
    "Low",
    "Close",
    "Volume",
    "RETURN_1D",
    "VOLATILITY_5D",
    "MOMENTUM_10D",
    "RSI",
    "MACD",
    "MACD_SIGNAL",
    "SMA_20",
    "EMA_20",
    "SMA_50",
    "EMA_50",
    "BB_UPPER",
    "BB_LOWER",
    "BB_WIDTH",
]


def _calculate_rsi(close: pd.Series, period: int = 14) -> pd.Series:
    delta = close.diff()
    gains = delta.clip(lower=0)
    losses = -delta.clip(upper=0)

    avg_gain = gains.ewm(alpha=1 / period, adjust=False).mean()
    avg_loss = losses.ewm(alpha=1 / period, adjust=False).mean()

    rs = avg_gain / (avg_loss + 1e-9)
    return 100 - (100 / (1 + rs))


def build_feature_frame(historical_df: pd.DataFrame) -> pd.DataFrame:
    """Create model features from raw OHLCV data and technical indicators."""
    feature_df = historical_df[["Open", "High", "Low", "Close", "Volume"]].copy()

    for column in ["Open", "High", "Low", "Close", "Volume"]:
        feature_df[column] = pd.to_numeric(feature_df[column], errors="coerce")

    close = feature_df["Close"]

    ema_12 = close.ewm(span=12, adjust=False).mean()
    ema_26 = close.ewm(span=26, adjust=False).mean()
    rolling_std_20 = close.rolling(window=20, min_periods=20).std()
    sma_20 = close.rolling(window=20, min_periods=20).mean()

    feature_df["RETURN_1D"] = close.pct_change()
    feature_df["VOLATILITY_5D"] = close.pct_change().rolling(window=5, min_periods=5).std()
    feature_df["MOMENTUM_10D"] = close - close.shift(10)
    feature_df["RSI"] = _calculate_rsi(close, period=14)
    feature_df["MACD"] = ema_12 - ema_26
    feature_df["MACD_SIGNAL"] = feature_df["MACD"].ewm(span=9, adjust=False).mean()
    feature_df["SMA_20"] = sma_20
    feature_df["EMA_20"] = close.ewm(span=20, adjust=False).mean()
    feature_df["SMA_50"] = close.rolling(window=50, min_periods=50).mean()
    feature_df["EMA_50"] = close.ewm(span=50, adjust=False).mean()
    feature_df["BB_UPPER"] = sma_20 + (2 * rolling_std_20)
    feature_df["BB_LOWER"] = sma_20 - (2 * rolling_std_20)
    feature_df["BB_WIDTH"] = (feature_df["BB_UPPER"] - feature_df["BB_LOWER"]) / (sma_20 + 1e-9)

    feature_df = feature_df.replace([np.inf, -np.inf], np.nan)
    feature_df = feature_df.ffill().bfill().dropna()

    return feature_df[FEATURE_COLUMNS].copy()


def fit_transform_features_target(
    feature_df: pd.DataFrame,
    target_column: str = "Close",
) -> Tuple[np.ndarray, np.ndarray, MinMaxScaler, MinMaxScaler]:
    """Scale input features and target independently for stable training."""
    feature_scaler = MinMaxScaler(feature_range=(0, 1))
    target_scaler = MinMaxScaler(feature_range=(0, 1))

    features = feature_df[FEATURE_COLUMNS].values
    target = feature_df[[target_column]].values

    scaled_features = feature_scaler.fit_transform(features)
    scaled_target = target_scaler.fit_transform(target)

    return scaled_features, scaled_target, feature_scaler, target_scaler


def create_multihorizon_sequences(
    scaled_features: np.ndarray,
    scaled_target: np.ndarray,
    lookback: int,
    horizons: Sequence[int],
) -> Tuple[np.ndarray, np.ndarray]:
    """Create multivariate windows with direct targets for multiple horizons."""
    x_data = []
    y_data = []

    max_horizon = max(horizons)
    n_rows = len(scaled_features)

    for start_idx in range(lookback, n_rows - max_horizon + 1):
        x_data.append(scaled_features[start_idx - lookback : start_idx, :])
        y_row = [scaled_target[start_idx + horizon - 1, 0] for horizon in horizons]
        y_data.append(y_row)

    return np.array(x_data), np.array(y_data)
