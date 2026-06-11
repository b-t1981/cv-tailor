import time
from collections import defaultdict

from fastapi import Request
from starlette.middleware.base import BaseHTTPMiddleware
from starlette.responses import JSONResponse

from app.config import settings
from app.session import SESSION_COOKIE, is_valid_session_id


class RateLimitMiddleware(BaseHTTPMiddleware):
    """In-memory rate limiter keyed by session (or IP) and endpoint."""

    def __init__(self, app) -> None:
        super().__init__(app)
        self._hits: dict[str, list[float]] = defaultdict(list)

    def _client_key(self, request: Request) -> str:
        cookie_sid = request.cookies.get(SESSION_COOKIE)
        if is_valid_session_id(cookie_sid):
            return f"sid:{cookie_sid}"
        client = request.client.host if request.client else "unknown"
        return f"ip:{client}"

    async def dispatch(self, request: Request, call_next):
        path = request.url.path
        if not path.startswith("/api/") or path in ("/api/health", "/api/llm/providers"):
            return await call_next(request)

        key = f"{self._client_key(request)}:{path}"
        now = time.time()
        window = 60.0
        limit = settings.rate_limit_per_minute

        self._hits[key] = [t for t in self._hits[key] if now - t < window]
        if len(self._hits[key]) >= limit:
            return JSONResponse(
                status_code=429,
                content={"detail": "Too many requests. Please wait a moment."},
            )

        self._hits[key].append(now)
        return await call_next(request)
