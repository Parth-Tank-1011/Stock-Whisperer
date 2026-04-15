"""Configuration utilities for the stock prediction backend."""

from dataclasses import dataclass
import os


def _env_float(name: str, default: float) -> float:
    value = os.getenv(name)
    if value is None:
        return default
    try:
        return float(value)
    except ValueError:
        return default


def _env_int(name: str, default: int) -> int:
    value = os.getenv(name)
    if value is None:
        return default
    try:
        return int(value)
    except ValueError:
        return default


def _env_bool(name: str, default: bool) -> bool:
    value = os.getenv(name)
    if value is None:
        return default
    return value.strip().lower() in {"1", "true", "yes", "on"}


def _default_database_url() -> str:
    explicit = os.getenv("DATABASE_URL")
    if explicit:
        return explicit

    # Render persistent disk path; keeps users across restarts/redeploys when disk is attached.
    if os.getenv("APP_ENV", "development").lower() == "production" and os.path.isdir("/var/data"):
        return "sqlite:////var/data/stock_whisperer.db"

    return "sqlite:///./storage/app.db"


@dataclass(frozen=True)
class Settings:
    app_name: str = os.getenv("APP_NAME", "Stock Whisperer API")
    app_version: str = os.getenv("APP_VERSION", "1.0.0")
    environment: str = os.getenv("APP_ENV", "development")

    history_period: str = os.getenv("HISTORY_PERIOD", "2y")
    history_interval: str = os.getenv("HISTORY_INTERVAL", "1d")

    lookback_days: int = _env_int("LOOKBACK_DAYS", 60)
    model_epochs: int = _env_int("MODEL_EPOCHS", 10)
    model_batch_size: int = _env_int("MODEL_BATCH_SIZE", 16)

    retrain_after_days: int = _env_int("RETRAIN_AFTER_DAYS", 3)

    cache_ttl_seconds: int = _env_int("CACHE_TTL_SECONDS", 900)
    prediction_cache_ttl_seconds: int = _env_int("PREDICTION_CACHE_TTL_SECONDS", 300)
    live_cache_ttl_seconds: int = _env_int("LIVE_CACHE_TTL_SECONDS", 5)

    model_dir: str = os.getenv("MODEL_DIR", "storage/models")
    metadata_dir: str = os.getenv("METADATA_DIR", "storage/meta")
    yfinance_cache_dir: str = os.getenv("YFINANCE_CACHE_DIR", "storage/yfinance_cache")
    log_dir: str = os.getenv("LOG_DIR", "storage/logs")

    confidence_floor: float = _env_float("CONFIDENCE_FLOOR", 0.01)

    cors_origins: str = os.getenv("CORS_ORIGINS", "*")
    enable_xgboost: bool = _env_bool("ENABLE_XGBOOST", False)
    enable_deep_models: bool = _env_bool("ENABLE_DEEP_MODELS", False)

    database_url: str = _default_database_url()
    jwt_secret_key: str = os.getenv("JWT_SECRET_KEY", "change-this-in-production")
    jwt_algorithm: str = os.getenv("JWT_ALGORITHM", "HS256")
    access_token_expire_minutes: int = _env_int("ACCESS_TOKEN_EXPIRE_MINUTES", 60)

    rate_limit_window_seconds: int = _env_int("RATE_LIMIT_WINDOW_SECONDS", 60)
    rate_limit_max_requests: int = _env_int("RATE_LIMIT_MAX_REQUESTS", 80)
    request_log_enabled: bool = _env_bool("REQUEST_LOG_ENABLED", True)

    external_api_retries: int = _env_int("EXTERNAL_API_RETRIES", 2)
    external_api_retry_delay_ms: int = _env_int("EXTERNAL_API_RETRY_DELAY_MS", 400)


settings = Settings()
