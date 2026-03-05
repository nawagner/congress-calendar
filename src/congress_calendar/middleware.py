"""Request logging middleware for analytics."""

import hashlib
import logging
import time
from datetime import date

from starlette.middleware.base import BaseHTTPMiddleware, RequestResponseEndpoint
from starlette.requests import Request
from starlette.responses import Response

logger = logging.getLogger("congress-calendar.access")


def _get_client_ip(request: Request) -> str:
    """Extract the real client IP from proxy headers, falling back to request.client."""
    forwarded_for = request.headers.get("x-forwarded-for")
    if forwarded_for:
        return forwarded_for.split(",")[0].strip()
    real_ip = request.headers.get("x-real-ip")
    if real_ip:
        return real_ip.strip()
    if request.client:
        return request.client.host
    return "unknown"


def _hash_ip(ip: str, salt: str = "") -> str:
    """One-way hash an IP for privacy. Daily salt rotation prevents cross-day tracking."""
    return hashlib.sha256(f"{salt}:{ip}".encode()).hexdigest()[:16]


class RequestLoggingMiddleware(BaseHTTPMiddleware):
    """Log every request as structured JSON for analytics."""

    async def dispatch(
        self, request: Request, call_next: RequestResponseEndpoint
    ) -> Response:
        start = time.perf_counter()
        response = await call_next(request)
        duration_ms = (time.perf_counter() - start) * 1000

        if request.url.path == "/health":
            return response

        client_ip = _get_client_ip(request)
        daily_salt = date.today().isoformat()

        logger.info(
            "request",
            extra={
                "client_ip_hash": _hash_ip(client_ip, daily_salt),
                "method": request.method,
                "path": request.url.path,
                "query": str(request.query_params),
                "user_agent": request.headers.get("user-agent", ""),
                "referer": request.headers.get("referer", ""),
                "status_code": response.status_code,
                "duration_ms": round(duration_ms, 1),
            },
        )
        return response
