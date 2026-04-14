"""Middleware for request logging and in-memory rate limiting."""

from __future__ import annotations

import logging
import threading
import time
import uuid
from collections import deque
from typing import Dict

from fastapi import Request
from fastapi.responses import JSONResponse
from starlette.middleware.base import BaseHTTPMiddleware
from starlette.types import ASGIApp


logger = logging.getLogger(__name__)


class RequestLoggingMiddleware(BaseHTTPMiddleware):
    def __init__(self, app: ASGIApp) -> None:
        super().__init__(app)

    async def dispatch(self, request: Request, call_next):
        request_id = uuid.uuid4().hex[:12]
        request.state.request_id = request_id
        client_ip = request.client.host if request.client else "unknown"
        start = time.perf_counter()

        logger.info(
            "request.start id=%s method=%s path=%s ip=%s",
            request_id,
            request.method,
            request.url.path,
            client_ip,
        )

        try:
            response = await call_next(request)
        except Exception:
            elapsed_ms = (time.perf_counter() - start) * 1000.0
            logger.exception("request.error id=%s elapsed_ms=%.2f", request_id, elapsed_ms)
            raise

        elapsed_ms = (time.perf_counter() - start) * 1000.0
        response.headers["X-Request-ID"] = request_id
        logger.info(
            "request.end id=%s status=%s elapsed_ms=%.2f",
            request_id,
            response.status_code,
            elapsed_ms,
        )
        return response


class RateLimitMiddleware(BaseHTTPMiddleware):
    def __init__(self, app: ASGIApp, max_requests: int, window_seconds: int) -> None:
        super().__init__(app)
        self.max_requests = max_requests
        self.window_seconds = window_seconds
        self._hits: Dict[str, deque[float]] = {}
        self._lock = threading.Lock()

    async def dispatch(self, request: Request, call_next):
        if request.url.path == "/health":
            return await call_next(request)

        client_ip = request.client.host if request.client else "unknown"
        now = time.time()

        with self._lock:
            bucket = self._hits.get(client_ip)
            if bucket is None:
                bucket = deque()
                self._hits[client_ip] = bucket

            cutoff = now - self.window_seconds
            while bucket and bucket[0] < cutoff:
                bucket.popleft()

            if len(bucket) >= self.max_requests:
                retry_after = max(1, int(self.window_seconds - (now - bucket[0])))
                return JSONResponse(
                    status_code=429,
                    headers={"Retry-After": str(retry_after)},
                    content={
                        "detail": "Rate limit exceeded. Please retry later.",
                        "retry_after_seconds": retry_after,
                    },
                )

            bucket.append(now)

        return await call_next(request)
