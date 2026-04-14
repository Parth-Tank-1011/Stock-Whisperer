"""In-memory TTL cache implementation."""

from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime, timedelta
from threading import Lock
from typing import Any, Dict, Optional


@dataclass
class CacheEntry:
    value: Any
    expires_at: datetime


class TTLCache:
    def __init__(self, ttl_seconds: int = 900) -> None:
        self.ttl_seconds = ttl_seconds
        self._store: Dict[str, CacheEntry] = {}
        self._lock = Lock()

    def get(self, key: str) -> Optional[Any]:
        with self._lock:
            entry = self._store.get(key)
            if not entry:
                return None
            if datetime.utcnow() >= entry.expires_at:
                self._store.pop(key, None)
                return None
            return entry.value

    def set(self, key: str, value: Any) -> None:
        with self._lock:
            self._store[key] = CacheEntry(
                value=value,
                expires_at=datetime.utcnow() + timedelta(seconds=self.ttl_seconds),
            )

    def invalidate(self, key: str) -> None:
        with self._lock:
            self._store.pop(key, None)
