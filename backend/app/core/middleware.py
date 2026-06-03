"""
Middleware: CORS, request logging, error handling, rate limiting.
"""

from __future__ import annotations

import time
import traceback
import uuid
from collections import defaultdict

from fastapi import FastAPI, Request, Response
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from starlette.middleware.base import BaseHTTPMiddleware

from app.config import get_settings
from app.core.exceptions import KnowledgeHubException


def setup_middleware(app: FastAPI) -> None:
    """Configure all middleware on the FastAPI application."""
    settings = get_settings()

    # CORS
    app.add_middleware(
        CORSMiddleware,
        allow_origins=settings.CORS_ORIGINS,
        allow_credentials=True,
        allow_methods=["*"],
        allow_headers=["*"],
    )

    # Request ID + Logging
    app.add_middleware(RequestLoggingMiddleware)

    # Rate Limiting
    app.add_middleware(RateLimitMiddleware)


class RequestLoggingMiddleware(BaseHTTPMiddleware):
    """Add request ID and log request/response details."""

    async def dispatch(self, request: Request, call_next):
        request_id = str(uuid.uuid4())[:8]
        request.state.request_id = request_id

        start_time = time.perf_counter()
        try:
            response = await call_next(request)
        except KnowledgeHubException as e:
            return JSONResponse(
                status_code=e.status_code,
                content={"detail": e.message, "request_id": request_id},
            )
        except Exception as e:
            traceback.print_exc()
            return JSONResponse(
                status_code=500,
                content={"detail": f"Internal server error: {str(e)}", "request_id": request_id},
            )

        elapsed_ms = (time.perf_counter() - start_time) * 1000
        response.headers["X-Request-ID"] = request_id
        response.headers["X-Response-Time"] = f"{elapsed_ms:.1f}ms"

        return response


class RateLimitMiddleware(BaseHTTPMiddleware):
    """Simple in-memory rate limiter (per IP)."""

    def __init__(self, app):
        super().__init__(app)
        self._requests: dict[str, list[float]] = defaultdict(list)
        self._settings = get_settings()

    async def dispatch(self, request: Request, call_next):
        # Skip rate limiting for static files and health checks
        if request.url.path.startswith(("/static", "/health", "/docs", "/openapi")):
            return await call_next(request)

        client_ip = request.client.host if request.client else "unknown"
        now = time.time()
        window = 60.0  # 1 minute window

        # Clean old entries
        self._requests[client_ip] = [
            t for t in self._requests[client_ip] if now - t < window
        ]

        if len(self._requests[client_ip]) >= self._settings.RATE_LIMIT_PER_MINUTE:
            return JSONResponse(
                status_code=429,
                content={"detail": "Rate limit exceeded. Please try again later."},
            )

        self._requests[client_ip].append(now)
        return await call_next(request)
