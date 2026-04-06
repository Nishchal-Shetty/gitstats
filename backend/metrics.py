"""Prometheus metrics and HTTP instrumentation for the GitStats API."""

from __future__ import annotations

import time
from typing import Final

from prometheus_client import (
    CONTENT_TYPE_LATEST,
    Counter,
    Gauge,
    Histogram,
    REGISTRY,
    generate_latest,
)
from starlette.middleware.base import BaseHTTPMiddleware
from starlette.requests import Request
from starlette.responses import Response

# Default REGISTRY already registers process_* metrics (CPU, memory, etc.).

ERROR_NONE: Final = "none"
ERROR_NOT_FOUND: Final = "not_found"
ERROR_CLIENT: Final = "client_error"
ERROR_BAD_GATEWAY: Final = "bad_gateway"
ERROR_INTERNAL: Final = "internal"
ERROR_SERVER: Final = "server_error"


def classify_http_outcome(status_code: int) -> tuple[str, str]:
    """Return (status_class, error_type) with bounded label values for Prometheus."""
    if 100 <= status_code < 200:
        return "1xx", ERROR_NONE
    if 200 <= status_code < 300:
        return "2xx", ERROR_NONE
    if 300 <= status_code < 400:
        return "3xx", ERROR_NONE
    if 400 <= status_code < 500:
        if status_code == 404:
            return "4xx", ERROR_NOT_FOUND
        return "4xx", ERROR_CLIENT
    if status_code >= 500:
        if status_code == 502:
            return "5xx", ERROR_BAD_GATEWAY
        if status_code == 500:
            return "5xx", ERROR_INTERNAL
        return "5xx", ERROR_SERVER
    return "5xx", ERROR_INTERNAL


http_requests_total = Counter(
    "http_requests_total",
    "Total number of API requests",
    ["method", "path", "status_class", "error_type"],
)

http_request_duration_seconds = Histogram(
    "http_request_duration_seconds",
    "HTTP request latency in seconds",
    ["method", "path", "status_class", "error_type"],
    buckets=(
        0.005,
        0.01,
        0.025,
        0.05,
        0.1,
        0.25,
        0.5,
        1.0,
        2.5,
        5.0,
        10.0,
    ),
)

http_requests_errors_total = Counter(
    "http_requests_errors_total",
    "Total number of failed API requests (HTTP 4xx and 5xx)",
    ["method", "path", "status_class", "error_type"],
)

http_requests_in_progress = Gauge(
    "http_requests_in_progress",
    "Number of API requests currently being processed",
)

repo_compare_requests_total = Counter(
    "repo_compare_requests_total",
    "Repo stats / genre comparison requests (all outcomes)",
    ["outcome", "error_type"],
)

_REPO_COMPARE_ROUTE: Final = "/stats/repo/{owner}/{repo}"


def _route_template(request: Request) -> str:
    route = request.scope.get("route")
    if route is not None and getattr(route, "path", None):
        return route.path
    return request.url.path


def _record_repo_compare(status_code: int) -> None:
    status_class, error_type = classify_http_outcome(status_code)
    if status_class in ("1xx", "2xx", "3xx"):
        repo_compare_requests_total.labels(outcome="success", error_type=ERROR_NONE).inc()
    else:
        repo_compare_requests_total.labels(outcome="failure", error_type=error_type).inc()


class PrometheusHTTPMiddleware(BaseHTTPMiddleware):
    """Records HTTP metrics; skips /metrics and /health."""

    SKIP_PATHS = frozenset({"/metrics", "/health"})

    async def dispatch(self, request: Request, call_next):
        if request.url.path in self.SKIP_PATHS:
            return await call_next(request)

        method = request.method
        http_requests_in_progress.inc()
        start = time.perf_counter()
        status_code = 500
        try:
            response = await call_next(request)
            status_code = response.status_code
            return response
        except Exception:
            status_code = 500
            raise
        finally:
            elapsed = time.perf_counter() - start
            path = _route_template(request)
            http_requests_in_progress.dec()

            status_class, error_type = classify_http_outcome(status_code)
            http_requests_total.labels(
                method=method,
                path=path,
                status_class=status_class,
                error_type=error_type,
            ).inc()
            http_request_duration_seconds.labels(
                method=method,
                path=path,
                status_class=status_class,
                error_type=error_type,
            ).observe(elapsed)

            if status_class in ("4xx", "5xx"):
                http_requests_errors_total.labels(
                    method=method,
                    path=path,
                    status_class=status_class,
                    error_type=error_type,
                ).inc()

            if path == _REPO_COMPARE_ROUTE:
                _record_repo_compare(status_code)


def metrics_response() -> Response:
    return Response(generate_latest(REGISTRY), media_type=CONTENT_TYPE_LATEST)
