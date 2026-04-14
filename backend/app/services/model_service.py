"""Hybrid model training, persistence, and inference service."""

from __future__ import annotations

import json
import logging
from datetime import datetime, timezone
from pathlib import Path
from threading import Lock
from typing import Dict, List, Tuple

import joblib
import numpy as np
import pandas as pd
from sklearn.ensemble import RandomForestRegressor
from sklearn.multioutput import MultiOutputRegressor

try:
    from tensorflow.keras.layers import GRU, LSTM, Dense, Dropout
    from tensorflow.keras.models import Sequential, load_model

    HAS_TENSORFLOW = True
except Exception:  # pragma: no cover - tensorflow may be unavailable on host Python
    HAS_TENSORFLOW = False
    GRU = LSTM = Dense = Dropout = Sequential = None  # type: ignore[assignment]
    load_model = None  # type: ignore[assignment]

from app.core.config import settings
from app.core.exceptions import ModelTrainingError
from app.services.preprocessing_service import (
    FEATURE_COLUMNS,
    build_feature_frame,
    create_multihorizon_sequences,
    fit_transform_features_target,
)

try:
    from xgboost import XGBRegressor

    HAS_XGBOOST = True
except Exception:  # pragma: no cover - xgboost may be unavailable
    HAS_XGBOOST = False


logger = logging.getLogger(__name__)


FEATURE_SET_VERSION = 4
PREDICTION_HORIZONS: Tuple[int, ...] = (1, 3, 7)
DEEP_MODELS = {"lstm", "gru"}


class LSTMModelService:
    """Maintains backward class name while running a multi-model forecasting pipeline."""

    def __init__(self) -> None:
        self.model_dir = Path(settings.model_dir)
        self.meta_dir = Path(settings.metadata_dir)
        self.model_dir.mkdir(parents=True, exist_ok=True)
        self.meta_dir.mkdir(parents=True, exist_ok=True)

        self._locks_guard = Lock()
        self._train_locks: Dict[str, Lock] = {}
        self._artifact_cache: Dict[str, Dict[str, object]] = {}

    @staticmethod
    def _safe_symbol(symbol: str) -> str:
        return symbol.replace(".", "_").replace("/", "_").upper()

    def _model_path(self, symbol: str, model_name: str) -> Path:
        suffix = "keras" if model_name in DEEP_MODELS else "joblib"
        return self.model_dir / f"{self._safe_symbol(symbol)}_{model_name}.{suffix}"

    def _scaler_path(self, symbol: str) -> Path:
        return self.model_dir / f"{self._safe_symbol(symbol)}_scalers.gz"

    def _meta_path(self, symbol: str) -> Path:
        return self.meta_dir / f"{self._safe_symbol(symbol)}_meta.json"

    def _get_symbol_lock(self, symbol: str) -> Lock:
        safe_symbol = self._safe_symbol(symbol)
        with self._locks_guard:
            lock = self._train_locks.get(safe_symbol)
            if lock is None:
                lock = Lock()
                self._train_locks[safe_symbol] = lock
        return lock

    @staticmethod
    def _inverse_matrix(values: np.ndarray, target_scaler) -> np.ndarray:
        if values.ndim == 1:
            values = values.reshape(-1, 1)

        out = np.zeros_like(values, dtype=float)
        for col in range(values.shape[1]):
            out[:, col] = target_scaler.inverse_transform(values[:, [col]]).ravel()
        return out

    def _is_retrain_required(self, symbol: str, latest_data_date: pd.Timestamp) -> bool:
        scaler_path = self._scaler_path(symbol)
        meta_path = self._meta_path(symbol)

        if not scaler_path.exists() or not meta_path.exists():
            return True

        try:
            metadata = json.loads(meta_path.read_text(encoding="utf-8"))
            trained_at = datetime.fromisoformat(metadata["trained_at"])
            last_trained_data_date = pd.to_datetime(metadata["last_data_date"])
            model_version = int(metadata.get("feature_set_version", 0))
            feature_columns = metadata.get("feature_columns", [])
            horizons = tuple(int(h) for h in metadata.get("horizons", []))
            available_models = metadata.get("available_models", [])
        except Exception:
            return True

        if model_version != FEATURE_SET_VERSION:
            return True
        if feature_columns != FEATURE_COLUMNS:
            return True
        if horizons != PREDICTION_HORIZONS:
            return True
        if not available_models:
            return True

        for model_name in available_models:
            if not self._model_path(symbol, model_name).exists():
                return True

        now = datetime.now(timezone.utc)
        age_days = (now - trained_at).days

        if latest_data_date > last_trained_data_date:
            return True

        return age_days >= settings.retrain_after_days

    @staticmethod
    def _build_lstm_model(lookback: int, n_features: int, output_dim: int) -> Sequential:
        if not HAS_TENSORFLOW:
            raise ModelTrainingError("TensorFlow is not installed; deep models are unavailable on this host.")
        model = Sequential(
            [
                LSTM(24, return_sequences=True, input_shape=(lookback, n_features)),
                Dropout(0.2),
                LSTM(16, return_sequences=False),
                Dropout(0.2),
                Dense(16, activation="relu"),
                Dense(output_dim),
            ]
        )
        model.compile(optimizer="adam", loss="mean_squared_error")
        return model

    @staticmethod
    def _build_gru_model(lookback: int, n_features: int, output_dim: int) -> Sequential:
        if not HAS_TENSORFLOW:
            raise ModelTrainingError("TensorFlow is not installed; deep models are unavailable on this host.")
        model = Sequential(
            [
                GRU(24, return_sequences=True, input_shape=(lookback, n_features)),
                Dropout(0.2),
                GRU(16, return_sequences=False),
                Dropout(0.2),
                Dense(16, activation="relu"),
                Dense(output_dim),
            ]
        )
        model.compile(optimizer="adam", loss="mean_squared_error")
        return model

    def _save_metadata(
        self,
        symbol: str,
        last_data_date: pd.Timestamp,
        rmse_by_model: Dict[str, float],
        accuracy_by_model: Dict[str, float],
        best_model: str,
        available_models: List[str],
    ) -> None:
        payload = {
            "symbol": symbol.upper(),
            "trained_at": datetime.now(timezone.utc).isoformat(),
            "last_data_date": str(last_data_date.date()),
            "lookback_days": settings.lookback_days,
            "validation_rmse": float(rmse_by_model[best_model]),
            "feature_set_version": FEATURE_SET_VERSION,
            "feature_columns": FEATURE_COLUMNS,
            "horizons": list(PREDICTION_HORIZONS),
            "available_models": available_models,
            "rmse_by_model": rmse_by_model,
            "accuracy_by_model": accuracy_by_model,
            "best_model": best_model,
        }
        self._meta_path(symbol).write_text(json.dumps(payload, indent=2), encoding="utf-8")

    def _confidence_from_rmse(self, rmse: float, baseline_price: float) -> float:
        if baseline_price <= 0:
            return settings.confidence_floor
        normalized_error = rmse / baseline_price
        confidence = 1.0 - normalized_error
        return float(max(settings.confidence_floor, min(1.0, confidence)))

    def _predict_scaled(self, model_name: str, model_obj, last_window_scaled: np.ndarray) -> np.ndarray:
        if model_name in DEEP_MODELS:
            pred = model_obj.predict(last_window_scaled, verbose=0)
            return pred.reshape(-1)

        flat = last_window_scaled.reshape(1, -1)
        pred = model_obj.predict(flat)
        return pred.reshape(-1)


    @staticmethod
    def _accuracy_percent_from_series(y_true: np.ndarray, y_pred: np.ndarray) -> float:
        epsilon = 1e-6
        denom = np.maximum(np.abs(y_true), epsilon)
        mape = float(np.mean(np.abs((y_true - y_pred) / denom)))
        accuracy = (1.0 - mape) * 100.0
        return float(max(0.0, min(100.0, accuracy)))

    def _cache_artifacts(self, symbol: str, payload: Dict[str, object]) -> None:
        meta_path = self._meta_path(symbol)
        scaler_path = self._scaler_path(symbol)
        safe_symbol = self._safe_symbol(symbol)

        self._artifact_cache[safe_symbol] = {
            "meta_mtime": meta_path.stat().st_mtime if meta_path.exists() else None,
            "scaler_mtime": scaler_path.stat().st_mtime if scaler_path.exists() else None,
            "payload": payload,
        }

    def _train_models(
        self,
        symbol: str,
        feature_df: pd.DataFrame,
        latest_data_date: pd.Timestamp,
    ) -> Dict[str, object]:
        scaled_features, scaled_target, feature_scaler, target_scaler = fit_transform_features_target(
            feature_df
        )

        x_all, y_all = create_multihorizon_sequences(
            scaled_features,
            scaled_target,
            settings.lookback_days,
            PREDICTION_HORIZONS,
        )

        if len(x_all) < 40:
            raise ModelTrainingError(
                "Not enough data points to train multi-horizon models. Try a symbol with longer history."
            )

        split_index = int(len(x_all) * 0.85)
        x_train, x_test = x_all[:split_index], x_all[split_index:]
        y_train, y_test = y_all[:split_index], y_all[split_index:]

        if len(x_test) == 0:
            raise ModelTrainingError("Not enough test data for validation")

        x_train_flat = x_train.reshape(len(x_train), -1)
        x_test_flat = x_test.reshape(len(x_test), -1)

        # Keep first-call latency practical for API usage.
        max_train_samples = 1200
        if len(x_train) > max_train_samples:
            x_train = x_train[-max_train_samples:]
            y_train = y_train[-max_train_samples:]
            x_train_flat = x_train.reshape(len(x_train), -1)

        train_epochs = max(3, settings.model_epochs)

        models: Dict[str, object] = {}
        rmse_by_model: Dict[str, float] = {}
        accuracy_by_model: Dict[str, float] = {}
        y_test_real = self._inverse_matrix(y_test, target_scaler)

        if settings.enable_deep_models and HAS_TENSORFLOW:
            lstm = self._build_lstm_model(settings.lookback_days, len(FEATURE_COLUMNS), len(PREDICTION_HORIZONS))
            lstm.fit(
                x_train,
                y_train,
                validation_data=(x_test, y_test),
                epochs=train_epochs,
                batch_size=settings.model_batch_size,
                verbose=0,
            )
            lstm_pred_real = self._inverse_matrix(lstm.predict(x_test, verbose=0), target_scaler)
            rmse_by_model["lstm"] = float(np.sqrt(np.mean((lstm_pred_real[:, 0] - y_test_real[:, 0]) ** 2)))
            accuracy_by_model["lstm"] = self._accuracy_percent_from_series(y_test_real[:, 0], lstm_pred_real[:, 0])
            models["lstm"] = lstm

            gru = self._build_gru_model(settings.lookback_days, len(FEATURE_COLUMNS), len(PREDICTION_HORIZONS))
            gru.fit(
                x_train,
                y_train,
                validation_data=(x_test, y_test),
                epochs=train_epochs,
                batch_size=settings.model_batch_size,
                verbose=0,
            )
            gru_pred_real = self._inverse_matrix(gru.predict(x_test, verbose=0), target_scaler)
            rmse_by_model["gru"] = float(np.sqrt(np.mean((gru_pred_real[:, 0] - y_test_real[:, 0]) ** 2)))
            accuracy_by_model["gru"] = self._accuracy_percent_from_series(y_test_real[:, 0], gru_pred_real[:, 0])
            models["gru"] = gru
        elif settings.enable_deep_models and not HAS_TENSORFLOW:
            logger.warning("ENABLE_DEEP_MODELS is true but TensorFlow is unavailable; skipping LSTM/GRU models.")

        rf = RandomForestRegressor(
            n_estimators=300,
            max_depth=12,
            min_samples_leaf=1,
            min_samples_split=4,
            max_features="sqrt",
            random_state=42,
            n_jobs=1,
        )
        rf.fit(x_train_flat, y_train)
        rf_pred_real = self._inverse_matrix(rf.predict(x_test_flat), target_scaler)
        rmse_by_model["random_forest"] = float(np.sqrt(np.mean((rf_pred_real[:, 0] - y_test_real[:, 0]) ** 2)))
        accuracy_by_model["random_forest"] = self._accuracy_percent_from_series(y_test_real[:, 0], rf_pred_real[:, 0])
        models["random_forest"] = rf

        if HAS_XGBOOST and settings.enable_xgboost:
            xgb = MultiOutputRegressor(
                XGBRegressor(
                    n_estimators=60,
                    max_depth=4,
                    learning_rate=0.05,
                    subsample=0.9,
                    colsample_bytree=0.9,
                    objective="reg:squarederror",
                    random_state=42,
                    tree_method="hist",
                    n_jobs=1,
                )
            )
            xgb.fit(x_train_flat, y_train)
            xgb_pred_real = self._inverse_matrix(xgb.predict(x_test_flat), target_scaler)
            rmse_by_model["xgboost"] = float(
                np.sqrt(np.mean((xgb_pred_real[:, 0] - y_test_real[:, 0]) ** 2))
            )
            accuracy_by_model["xgboost"] = self._accuracy_percent_from_series(y_test_real[:, 0], xgb_pred_real[:, 0])
            models["xgboost"] = xgb

        available_models = list(models.keys())
        best_model = min(rmse_by_model, key=rmse_by_model.get)

        for name, model_obj in models.items():
            path = self._model_path(symbol, name)
            if name in DEEP_MODELS:
                model_obj.save(path)
            else:
                joblib.dump(model_obj, path)

        joblib.dump(
            {
                "feature_scaler": feature_scaler,
                "target_scaler": target_scaler,
                "feature_columns": FEATURE_COLUMNS,
                "feature_set_version": FEATURE_SET_VERSION,
                "horizons": list(PREDICTION_HORIZONS),
                "available_models": available_models,
            },
            self._scaler_path(symbol),
        )

        self._save_metadata(symbol, latest_data_date, rmse_by_model, accuracy_by_model, best_model, available_models)

        payload = {
            "models": models,
            "feature_scaler": feature_scaler,
            "target_scaler": target_scaler,
            "rmse_by_model": rmse_by_model,
            "accuracy_by_model": accuracy_by_model,
            "best_model": best_model,
            "available_models": available_models,
        }
        self._cache_artifacts(symbol, payload)

        logger.info(
            "Trained models for %s. Best model: %s (RMSE day-1: %.4f)",
            symbol.upper(),
            best_model,
            rmse_by_model[best_model],
        )

        return payload

    def _load_artifacts(self, symbol: str) -> Dict[str, object]:
        safe_symbol = self._safe_symbol(symbol)
        meta_path = self._meta_path(symbol)
        scaler_path = self._scaler_path(symbol)

        cached = self._artifact_cache.get(safe_symbol)
        if cached and meta_path.exists() and scaler_path.exists():
            if (
                cached.get("meta_mtime") == meta_path.stat().st_mtime
                and cached.get("scaler_mtime") == scaler_path.stat().st_mtime
            ):
                logger.info("Using in-memory artifacts for %s", symbol.upper())
                return cached["payload"]

        scaler_bundle = joblib.load(scaler_path)
        if not isinstance(scaler_bundle, dict):
            raise ModelTrainingError("Stored scaler format is outdated; retraining required")

        version = int(scaler_bundle.get("feature_set_version", 0))
        columns = scaler_bundle.get("feature_columns", [])
        horizons = tuple(int(h) for h in scaler_bundle.get("horizons", []))
        available_models = scaler_bundle.get("available_models", [])
        feature_scaler = scaler_bundle.get("feature_scaler")
        target_scaler = scaler_bundle.get("target_scaler")

        if version != FEATURE_SET_VERSION or columns != FEATURE_COLUMNS or horizons != PREDICTION_HORIZONS:
            raise ModelTrainingError("Stored artifacts are incompatible; retraining required")

        if feature_scaler is None or target_scaler is None:
            raise ModelTrainingError("Stored scalers are incomplete; retraining required")

        metadata = json.loads(meta_path.read_text(encoding="utf-8"))
        rmse_by_model = {
            key: float(value)
            for key, value in (metadata.get("rmse_by_model") or {}).items()
        }
        accuracy_by_model = {
            key: float(value)
            for key, value in (metadata.get("accuracy_by_model") or {}).items()
        }
        best_model = metadata.get("best_model", "lstm")

        models: Dict[str, object] = {}
        for name in available_models:
            path = self._model_path(symbol, name)
            if not path.exists():
                raise ModelTrainingError("Stored model file missing; retraining required")

            if name in DEEP_MODELS:
                if not HAS_TENSORFLOW or load_model is None:
                    raise ModelTrainingError("Stored deep model requires TensorFlow, which is unavailable on this host.")
                models[name] = load_model(path, compile=False)
            else:
                models[name] = joblib.load(path)

        if best_model not in models:
            best_model = next(iter(models.keys()), "random_forest")

        payload = {
            "models": models,
            "feature_scaler": feature_scaler,
            "target_scaler": target_scaler,
            "rmse_by_model": rmse_by_model,
            "accuracy_by_model": accuracy_by_model,
            "best_model": best_model,
            "available_models": list(models.keys()),
        }
        self._cache_artifacts(symbol, payload)
        return payload

    def predict_multi_horizon(self, symbol: str, historical_df: pd.DataFrame) -> Dict[str, object]:
        try:
            feature_df = build_feature_frame(historical_df)
            latest_date = pd.to_datetime(feature_df.index.max())
        except Exception as exc:
            raise ModelTrainingError("Unable to generate features from historical stock data") from exc

        if len(feature_df) <= settings.lookback_days + max(PREDICTION_HORIZONS):
            raise ModelTrainingError(
                f"Need at least {settings.lookback_days + max(PREDICTION_HORIZONS) + 1} data points for prediction"
            )

        lock = self._get_symbol_lock(symbol)
        with lock:
            retrain = self._is_retrain_required(symbol, latest_date)

            if retrain:
                logger.info("Retraining models for %s", symbol.upper())
                artifacts = self._train_models(symbol, feature_df, latest_date)
            else:
                logger.info("Using cached models for %s", symbol.upper())
                try:
                    artifacts = self._load_artifacts(symbol)
                except ModelTrainingError:
                    logger.info("Cached artifacts incompatible. Retraining models for %s", symbol.upper())
                    artifacts = self._train_models(symbol, feature_df, latest_date)

        last_window = feature_df[FEATURE_COLUMNS].values[-settings.lookback_days :]
        last_window_scaled = artifacts["feature_scaler"].transform(last_window).reshape(
            1, settings.lookback_days, len(FEATURE_COLUMNS)
        )

        model_predictions: Dict[str, Dict[str, float]] = {}
        for model_name, model_obj in artifacts["models"].items():
            pred_scaled = self._predict_scaled(model_name, model_obj, last_window_scaled)
            pred_real = self._inverse_matrix(pred_scaled.reshape(1, -1), artifacts["target_scaler"])[0]
            model_predictions[model_name] = {
                f"{horizon}d": float(pred_real[idx])
                for idx, horizon in enumerate(PREDICTION_HORIZONS)
            }

        best_model = artifacts["best_model"]
        if best_model not in model_predictions:
            best_model = next(iter(model_predictions.keys()))

        best_predictions = model_predictions[best_model]
        last_close = float(feature_df["Close"].iloc[-1])

        rmse_metrics = {
            model_name: float(rmse)
            for model_name, rmse in artifacts["rmse_by_model"].items()
        }
        accuracy_metrics = {
            model_name: float(acc)
            for model_name, acc in artifacts.get("accuracy_by_model", {}).items()
        }

        if not accuracy_metrics:
            accuracy_metrics = {
                model_name: self._confidence_from_rmse(rmse, baseline_price=last_close) * 100.0
                for model_name, rmse in rmse_metrics.items()
            }

        best_rmse = float(rmse_metrics.get(best_model, np.std(feature_df["Close"].values) * 0.05))
        confidence = self._confidence_from_rmse(best_rmse, baseline_price=last_close)
        best_accuracy = float(accuracy_metrics.get(best_model, confidence * 100.0))

        return {
            "horizon_predictions": best_predictions,
            "predicted_price": float(best_predictions["1d"]),
            "confidence": confidence,
            "rmse": best_rmse,
            "accuracy_percent": max(0.0, min(100.0, best_accuracy)),
            "model_used": best_model,
            "model_metrics": rmse_metrics,
            "model_accuracy": accuracy_metrics,
            "all_model_predictions": model_predictions,
            "last_close": last_close,
        }

    def predict_next_close(self, symbol: str, historical_df: pd.DataFrame) -> Tuple[float, float]:
        result = self.predict_multi_horizon(symbol, historical_df)
        return float(result["predicted_price"]), float(result["confidence"])
