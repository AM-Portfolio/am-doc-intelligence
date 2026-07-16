"""Plane A observability for Flask: /metrics + optional OTLP traces."""

from __future__ import annotations

import logging
import os
import time

logger = logging.getLogger(__name__)

_EXCLUDED = {"/metrics", "/api/v1/health", "/health"}


def setup_plane_a(app, *, application: str) -> None:
    _setup_metrics(app, application)
    _setup_tracing(app, application)


def _setup_metrics(app, application: str) -> None:
    try:
        from prometheus_client import CONTENT_TYPE_LATEST, Counter, Gauge, Histogram, generate_latest
    except ImportError:
        logger.warning("prometheus_client missing — /metrics not enabled")
        return

    Gauge("am_process_up", "1 if the process is up", ["application"]).labels(application=application).set(1)
    requests_total = Counter(
        "http_requests_total",
        "Total HTTP requests",
        ["application", "method", "handler", "status"],
    )
    request_duration = Histogram(
        "http_request_duration_seconds",
        "HTTP request latency in seconds",
        ["application", "method", "handler"],
    )

    @app.before_request
    def _start_timer():
        from flask import g, request
        if request.path in _EXCLUDED:
            return
        g._am_metrics_start = time.perf_counter()

    @app.after_request
    def _record_metrics(response):
        from flask import g, request
        if request.path in _EXCLUDED:
            return response
        start = getattr(g, "_am_metrics_start", None)
        if start is None:
            return response
        elapsed = time.perf_counter() - start
        handler = request.path if len(request.path) < 120 else request.path[:117] + "..."
        requests_total.labels(application, request.method, handler, str(response.status_code)).inc()
        request_duration.labels(application, request.method, handler).observe(elapsed)
        return response

    @app.route("/metrics")
    def metrics_endpoint():
        from flask import Response
        return Response(generate_latest(), mimetype=CONTENT_TYPE_LATEST)

    logger.info("Prometheus /metrics enabled application=%s", application)


def _setup_tracing(app, service_name: str) -> None:
    endpoint = (os.getenv("OTEL_EXPORTER_OTLP_TRACES_ENDPOINT") or "").strip()
    if not endpoint:
        logger.info("OTEL endpoint unset — tracing disabled")
        return
    try:
        sample = float(os.getenv("TRACING_SAMPLING_PROBABILITY", "1.0"))
    except ValueError:
        sample = 1.0
    sample = max(0.0, min(1.0, sample))
    try:
        from opentelemetry import trace
        from opentelemetry.exporter.otlp.proto.http.trace_exporter import OTLPSpanExporter
        from opentelemetry.instrumentation.flask import FlaskInstrumentor
        from opentelemetry.sdk.resources import Resource
        from opentelemetry.sdk.trace import TracerProvider
        from opentelemetry.sdk.trace.export import BatchSpanProcessor
        from opentelemetry.sdk.trace.sampling import ParentBased, TraceIdRatioBased
    except ImportError:
        logger.warning("opentelemetry deps missing — tracing not enabled")
        return
    resource = Resource.create({"service.name": service_name, "application": service_name})
    provider = TracerProvider(resource=resource, sampler=ParentBased(TraceIdRatioBased(sample)))
    provider.add_span_processor(BatchSpanProcessor(OTLPSpanExporter(endpoint=endpoint)))
    trace.set_tracer_provider(provider)
    FlaskInstrumentor().instrument_app(app)
    logger.info("OTEL tracing enabled service=%s sample=%s", service_name, sample)
