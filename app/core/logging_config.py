"""Simple application-wide logging setup."""

from __future__ import annotations

import logging
from logging.handlers import RotatingFileHandler
from pathlib import Path

from app.core.config import settings


def configure_logging() -> None:
    log_dir = Path(settings.log_dir)
    log_dir.mkdir(parents=True, exist_ok=True)

    formatter = logging.Formatter(
        "%(asctime)s | %(levelname)s | %(name)s | %(message)s"
    )

    root_logger = logging.getLogger()
    root_logger.setLevel(logging.INFO)

    has_console = any(isinstance(handler, logging.StreamHandler) for handler in root_logger.handlers)
    if not has_console:
        console_handler = logging.StreamHandler()
        console_handler.setFormatter(formatter)
        root_logger.addHandler(console_handler)

    log_file_path = str((log_dir / "app.log").resolve())
    has_file = any(
        isinstance(handler, RotatingFileHandler) and getattr(handler, "baseFilename", "") == log_file_path
        for handler in root_logger.handlers
    )
    if not has_file:
        file_handler = RotatingFileHandler(
            filename=log_file_path,
            maxBytes=2_000_000,
            backupCount=5,
            encoding="utf-8",
        )
        file_handler.setFormatter(formatter)
        root_logger.addHandler(file_handler)

