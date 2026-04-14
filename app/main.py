"""FastAPI application entrypoint."""

from __future__ import annotations

import logging
import os
from pathlib import Path

from fastapi import FastAPI, Request
from fastapi.exceptions import RequestValidationError
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from fastapi.staticfiles import StaticFiles

from app.core.config import settings
from app.core.exceptions import (
    DataFetchError,
    InputValidationError,
    InvalidStockSymbolError,
    ModelTrainingError,
)
from app.core.logging_config import configure_logging
from app.db.database import init_db
from app.routes.auth import router as auth_router
from app.routes.stock import router as stock_router
from app.routes.user_features import router as user_features_router
from app.utils.middleware import RateLimitMiddleware, RequestLoggingMiddleware


configure_logging()
logger = logging.getLogger(__name__)


app = FastAPI(title=settings.app_name, version=settings.app_version)

origins = [origin.strip() for origin in settings.cors_origins.split(",") if origin.strip()]
if origins == ["*"]:
    allow_origins = ["*"]
else:
    allow_origins = origins

app.add_middleware(
    CORSMiddleware,
    allow_origins=allow_origins,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)
app.add_middleware(
    RateLimitMiddleware,
    max_requests=settings.rate_limit_max_requests,
    window_seconds=settings.rate_limit_window_seconds,
)
if settings.request_log_enabled:
    app.add_middleware(RequestLoggingMiddleware)


@app.on_event("startup")
def startup() -> None:
    init_db()


@app.get("/health")
def health() -> dict:
    return {"status": "ok", "service": settings.app_name, "version": settings.app_version}


@app.exception_handler(InputValidationError)
async def input_validation_handler(_: Request, exc: InputValidationError) -> JSONResponse:
    return JSONResponse(status_code=422, content={"detail": str(exc)})


@app.exception_handler(RequestValidationError)
async def request_validation_handler(_: Request, exc: RequestValidationError) -> JSONResponse:
    return JSONResponse(status_code=422, content={"detail": "Invalid request", "errors": exc.errors()})


@app.exception_handler(InvalidStockSymbolError)
async def invalid_stock_handler(_: Request, exc: InvalidStockSymbolError) -> JSONResponse:
    return JSONResponse(status_code=404, content={"detail": str(exc)})


@app.exception_handler(DataFetchError)
async def fetch_error_handler(_: Request, exc: DataFetchError) -> JSONResponse:
    return JSONResponse(status_code=502, content={"detail": str(exc)})


@app.exception_handler(ModelTrainingError)
async def model_error_handler(_: Request, exc: ModelTrainingError) -> JSONResponse:
    return JSONResponse(status_code=500, content={"detail": str(exc)})


@app.exception_handler(Exception)
async def generic_handler(_: Request, exc: Exception) -> JSONResponse:
    logger.exception("Unhandled server exception", exc_info=exc)
    return JSONResponse(status_code=500, content={"detail": "Internal server error"})


app.include_router(stock_router)
app.include_router(auth_router)
app.include_router(user_features_router)


def _mount_frontend_spa(application: FastAPI) -> None:
    """Serve the Vite production bundle from the same origin (set FRONTEND_DIST_DIR in Docker)."""

    raw = os.getenv("FRONTEND_DIST_DIR", "").strip()
    if not raw:
        return

    dist_path = Path(raw)
    if not dist_path.is_dir():
        logger.warning("FRONTEND_DIST_DIR is set but not a directory: %s", raw)
        return

    application.mount("/", StaticFiles(directory=str(dist_path), html=True), name="spa")
    logger.info("Serving SPA static files from %s", dist_path.resolve())


_mount_frontend_spa(app)
