"""Database configuration and session management."""

from __future__ import annotations

from pathlib import Path

from sqlalchemy import create_engine
from sqlalchemy.orm import declarative_base, sessionmaker

from app.core.config import settings


def _ensure_sqlite_path_exists() -> None:
    if not settings.database_url.startswith("sqlite:///"):
        return

    sqlite_path = settings.database_url.replace("sqlite:///", "", 1)
    path_obj = Path(sqlite_path)
    if not path_obj.is_absolute():
        path_obj = Path.cwd() / path_obj

    path_obj.parent.mkdir(parents=True, exist_ok=True)


_ensure_sqlite_path_exists()

connect_args = {"check_same_thread": False} if settings.database_url.startswith("sqlite") else {}
engine = create_engine(settings.database_url, future=True, connect_args=connect_args)
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine, future=True)
Base = declarative_base()


def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()


def init_db() -> None:
    from app.db import models  # noqa: F401

    Base.metadata.create_all(bind=engine)
