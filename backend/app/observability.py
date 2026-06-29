"""Structured logging (structlog → JSON) and Prometheus metrics."""

import logging
import re
import time
import uuid
from collections.abc import Awaitable, Callable

import structlog
from prometheus_client import CONTENT_TYPE_LATEST, Counter, Histogram, generate_latest
from starlette.middleware.base import BaseHTTPMiddleware
from starlette.requests import Request
from starlette.responses import Response

# --------------------------------------------------------------------------- #
# Metrics (scraped at GET /metrics)
# --------------------------------------------------------------------------- #
EXECUTIONS = Counter(
    "flow_executions_total", "Workflow executions by terminal status", ["status"]
)
WEBHOOK_INGEST = Counter(
    "flow_webhook_ingest_total", "Webhook ingests by result", ["result"]
)
HTTP_REQUESTS = Counter(
    "flow_http_requests_total", "HTTP requests", ["method", "path", "status"]
)
HTTP_LATENCY = Histogram(
    "flow_http_request_duration_seconds", "HTTP request latency", ["method", "path"]
)

logger = structlog.get_logger("flow")

_UUID_RE = re.compile(
    r"/[0-9a-f]{8}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{12}", re.IGNORECASE
)


def _norm_path(path: str) -> str:
    """Collapse UUID segments so the metric path label stays low-cardinality."""
    return _UUID_RE.sub("/:id", path)


def configure_logging(level: str = "info") -> None:
    """Emit JSON logs to stdout and route stdlib logging through structlog."""
    log_level = getattr(logging, level.upper(), logging.INFO)
    shared = [
        structlog.contextvars.merge_contextvars,
        structlog.processors.add_log_level,
        structlog.processors.TimeStamper(fmt="iso"),
    ]
    structlog.configure(
        processors=[*shared, structlog.stdlib.ProcessorFormatter.wrap_for_formatter],
        logger_factory=structlog.stdlib.LoggerFactory(),
        wrapper_class=structlog.stdlib.BoundLogger,
        cache_logger_on_first_use=True,
    )
    formatter = structlog.stdlib.ProcessorFormatter(
        foreign_pre_chain=shared,
        processors=[
            structlog.stdlib.ProcessorFormatter.remove_processors_meta,
            structlog.processors.JSONRenderer(),
        ],
    )
    handler = logging.StreamHandler()
    handler.setFormatter(formatter)
    root = logging.getLogger()
    root.handlers = [handler]
    root.setLevel(log_level)


class ObservabilityMiddleware(BaseHTTPMiddleware):
    """Bind a request id, emit an access log, and record HTTP metrics."""

    async def dispatch(
        self,
        request: Request,
        call_next: Callable[[Request], Awaitable[Response]],
    ) -> Response:
        request_id = request.headers.get("x-request-id") or uuid.uuid4().hex[:12]
        structlog.contextvars.bind_contextvars(request_id=request_id)
        start = time.perf_counter()
        try:
            response = await call_next(request)
            elapsed = time.perf_counter() - start
            path = _norm_path(request.url.path)
            HTTP_REQUESTS.labels(request.method, path, response.status_code).inc()
            HTTP_LATENCY.labels(request.method, path).observe(elapsed)
            logger.info(
                "request",
                method=request.method,
                path=path,
                status=response.status_code,
                duration_ms=round(elapsed * 1000, 1),
            )
            response.headers["x-request-id"] = request_id
            return response
        finally:
            structlog.contextvars.clear_contextvars()


def metrics_response() -> Response:
    return Response(generate_latest(), media_type=CONTENT_TYPE_LATEST)
