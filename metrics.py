import time
from functools import wraps
from typing import Any, Callable

from prometheus_client import (
    CollectorRegistry,
    Counter,
    Histogram,
    start_http_server,
)


REGISTRY = CollectorRegistry()

REQUESTS_TOTAL = Counter(
    "ai_agent_requests_total",
    "Total number of AI agent requests.",
    ["status"],
    registry=REGISTRY,
)

REQUEST_DURATION = Histogram(
    "ai_agent_request_duration_seconds",
    "Time spent processing AI agent requests.",
    registry=REGISTRY,
)

TOOL_USAGE_TOTAL = Counter(
    "ai_agent_tool_usage_total",
    "Total number of MCP tool selections.",
    ["tool"],
    registry=REGISTRY,
)

_metrics_server_started = False


def start_metrics_server() -> None:
    global _metrics_server_started

    if not _metrics_server_started:
        start_http_server(8000, registry=REGISTRY)
        _metrics_server_started = True


def monitored(function: Callable[..., Any]) -> Callable[..., Any]:
    @wraps(function)
    def wrapper(*args: Any, **kwargs: Any) -> Any:
        started_at = time.perf_counter()

        try:
            result = function(*args, **kwargs)

            REQUESTS_TOTAL.labels(status="success").inc()

            if isinstance(result, tuple) and len(result) >= 2:
                for tool_name in result[1]:
                    TOOL_USAGE_TOTAL.labels(tool=tool_name).inc()

            return result

        except Exception:
            REQUESTS_TOTAL.labels(status="error").inc()
            raise

        finally:
            REQUEST_DURATION.observe(
                time.perf_counter() - started_at
            )

    return wrapper
