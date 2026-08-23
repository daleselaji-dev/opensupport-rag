"""Small dependency-optional metrics and tracing primitives."""

from __future__ import annotations

import time
from typing import Any

try:
    from prometheus_client import CONTENT_TYPE_LATEST, Counter, Histogram, generate_latest
except ModuleNotFoundError:  # pragma: no cover
    CONTENT_TYPE_LATEST = "text/plain; version=0.0.4"
    Counter = Histogram = None  # type: ignore[assignment,misc]

try:
    from opentelemetry import trace
except ModuleNotFoundError:  # pragma: no cover
    trace = None  # type: ignore[assignment]

try:
    from opentelemetry.exporter.otlp.proto.http.trace_exporter import OTLPSpanExporter
    from opentelemetry.sdk.resources import Resource
    from opentelemetry.sdk.trace import TracerProvider
    from opentelemetry.sdk.trace.export import BatchSpanProcessor
except ModuleNotFoundError:  # pragma: no cover
    OTLPSpanExporter = Resource = TracerProvider = BatchSpanProcessor = None  # type: ignore[assignment,misc]


if Counter is not None:
    HTTP_REQUESTS = Counter("opensupport_http_requests_total", "HTTP requests", ["method", "path", "status"])
    HTTP_ERRORS = Counter("opensupport_http_errors_total", "HTTP errors", ["path"])
    HTTP_LATENCY = Histogram("opensupport_http_request_duration_seconds", "HTTP request latency", ["method", "path"])
else:  # pragma: no cover
    HTTP_REQUESTS = HTTP_ERRORS = HTTP_LATENCY = None


def observe_request(method: str, path: str, status: int, started: float) -> None:
    if HTTP_REQUESTS is None:
        return
    HTTP_REQUESTS.labels(method, path, str(status)).inc()
    HTTP_LATENCY.labels(method, path).observe(max(0.0, time.perf_counter() - started))
    if status >= 500:
        HTTP_ERRORS.labels(path).inc()


def metrics_payload() -> tuple[bytes, str]:
    if generate_latest is None:  # pragma: no cover
        return b"# prometheus_client is not installed\n", CONTENT_TYPE_LATEST
    return generate_latest(), CONTENT_TYPE_LATEST


def tracer(name: str = "opensupport") -> Any:
    if trace is None:
        return None
    return trace.get_tracer(name)


def configure_otel(settings: Any) -> None:
    if not getattr(settings, "otel_enabled", False) or trace is None or TracerProvider is None:
        return
    try:
        provider = TracerProvider(resource=Resource.create({"service.name": "opensupport-rag"}))
        exporter = OTLPSpanExporter(endpoint=f"{settings.otel_exporter_endpoint}/v1/traces")
        provider.add_span_processor(BatchSpanProcessor(exporter))
        trace.set_tracer_provider(provider)
    except Exception:
        # Metrics and deterministic DB traces remain available if the collector
        # is offline; observability must never take down the query API.
        return
