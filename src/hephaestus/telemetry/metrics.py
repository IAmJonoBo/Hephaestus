"""OpenTelemetry metrics collection for Hephaestus (ADR-0003 Sprint 2).

from __future__ import annotations

This module provides utilities for collecting and recording metrics
about command execution, quality gates, and resource usage.
"""

from __future__ import annotations

import importlib
import logging
import os
import re
import threading
from collections.abc import Callable
from http.server import BaseHTTPRequestHandler, HTTPServer
from socketserver import ThreadingMixIn
from typing import Any

__all__ = [
    "record_counter",
    "record_gauge",
    "record_histogram",
    "configure_metrics",
    "get_prometheus_endpoint",
    "shutdown_prometheus_exporter",
]


logger = logging.getLogger(__name__)


def is_metrics_enabled() -> bool:
    """Check if metrics collection is enabled."""

    return os.getenv("HEPHAESTUS_TELEMETRY_ENABLED", "").lower() == "true"


def get_meter(name: str = "hephaestus") -> Any:
    """Get an OpenTelemetry meter for metrics collection."""

    if not is_metrics_enabled():
        return _NoOpMeter()

    try:
        otel_metrics = importlib.import_module("opentelemetry.metrics")
        return otel_metrics.get_meter(name)
    except ImportError:
        return _NoOpMeter()


def configure_metrics(resource: Any | None = None) -> None:
    """Configure the Prometheus exporter when telemetry is enabled."""

    if not is_metrics_enabled():
        return

    if resource is not None:
        attributes = getattr(resource, "attributes", None)
        if isinstance(attributes, dict):
            _PROM_RESOURCE_ATTRIBUTES.clear()
            _PROM_RESOURCE_ATTRIBUTES.update({str(k): str(v) for k, v in attributes.items()})

    _ensure_prometheus_exporter()


def get_prometheus_endpoint() -> tuple[str, int] | None:
    """Return the bound Prometheus endpoint if available."""

    return _PROM_ENDPOINT


def shutdown_prometheus_exporter() -> None:
    """Shut down the Prometheus HTTP server (primarily for tests)."""

    global _PROM_SERVER, _PROM_THREAD, _PROM_ENDPOINT

    server = _PROM_SERVER
    if server is None:
        return

    server.shutdown()
    server.server_close()

    thread = _PROM_THREAD
    if thread and thread.is_alive():  # pragma: no branch - simple guard
        thread.join(timeout=1)

    _PROM_SERVER = None
    _PROM_THREAD = None
    _PROM_ENDPOINT = None
    _PROM_COUNTERS.clear()
    _PROM_GAUGES.clear()
    _PROM_HISTOGRAMS.clear()
    _PROM_COUNTER_FACTORY.clear()
    _PROM_GAUGE_FACTORY.clear()
    _PROM_HISTOGRAM_FACTORY.clear()
    _PROM_REGISTRY = None


def record_counter(
    name: str,
    value: int = 1,
    attributes: dict[str, Any] | None = None,
) -> None:
    """Record a counter metric."""

    if not is_metrics_enabled():
        return

    _export_to_prometheus(_prometheus_counter, name, float(value), attributes)

    meter = get_meter()
    counter = meter.create_counter(name, description=f"Counter for {name}")
    counter.add(value, attributes or {})


def record_gauge(
    name: str,
    value: float,
    attributes: dict[str, Any] | None = None,
) -> None:
    """Record a gauge metric."""

    if not is_metrics_enabled():
        return

    _export_to_prometheus(_prometheus_gauge, name, float(value), attributes)

    meter = get_meter()
    gauge = meter.create_observable_gauge(name, [lambda: value], description=f"Gauge for {name}")
    _ = gauge


def record_histogram(
    name: str,
    value: float,
    attributes: dict[str, Any] | None = None,
) -> None:
    """Record a histogram metric."""

    if not is_metrics_enabled():
        return

    _export_to_prometheus(_prometheus_histogram, name, float(value), attributes)

    meter = get_meter()
    histogram = meter.create_histogram(name, description=f"Histogram for {name}")
    histogram.record(value, attributes or {})


class _NoOpMeter:
    """No-op meter that provides the same interface as OpenTelemetry meter."""

    def create_counter(self, name: str, **kwargs: Any) -> _NoOpCounter:
        _ = (name, kwargs)
        return _NoOpCounter()

    def create_observable_gauge(self, name: str, callbacks: list, **kwargs: Any) -> _NoOpGauge:
        _ = (name, callbacks, kwargs)
        return _NoOpGauge()

    def create_histogram(self, name: str, **kwargs: Any) -> _NoOpHistogram:
        _ = (name, kwargs)
        return _NoOpHistogram()


class _NoOpCounter:
    """No-op counter."""

    def add(self, value: int, attributes: dict[str, Any]) -> None:
        _ = (value, attributes)


class _NoOpGauge:
    """No-op gauge."""

    def __iter__(self) -> Any:  # pragma: no cover - compatibility shim
        return iter(())


class _NoOpHistogram:
    """No-op histogram."""

    def record(self, value: float, attributes: dict[str, Any]) -> None:
        _ = (value, attributes)


class _PrometheusServer(ThreadingMixIn, HTTPServer):
    daemon_threads = True


_PROM_REGISTRY: Any | None = None
_PROM_COUNTERS: dict[str, Any] = {}
_PROM_GAUGES: dict[str, Any] = {}
_PROM_HISTOGRAMS: dict[str, Any] = {}
_PROM_SERVER: _PrometheusServer | None = None
_PROM_THREAD: threading.Thread | None = None
_PROM_ENDPOINT: tuple[str, int] | None = None
_PROM_RESOURCE_ATTRIBUTES: dict[str, str] = {}


def _ensure_prometheus_exporter() -> None:
    global _PROM_REGISTRY, _PROM_SERVER, _PROM_THREAD, _PROM_ENDPOINT

    if _PROM_SERVER is not None:
        return

    components = _load_prometheus_components()
    if components is None:
        logger.debug("Prometheus client not available; metrics exporter disabled")
        return

    registry_cls, counter_cls, gauge_cls, histogram_cls, generate_latest, content_type = components

    _PROM_REGISTRY = registry_cls()
    _PROM_COUNTERS.clear()
    _PROM_GAUGES.clear()
    _PROM_HISTOGRAMS.clear()

    host = os.getenv("HEPHAESTUS_PROMETHEUS_HOST", "0.0.0.0")
    port = int(os.getenv("HEPHAESTUS_PROMETHEUS_PORT", "9464"))

    handler = _build_handler(generate_latest, content_type)

    try:
        server = _PrometheusServer((host, port), handler)
    except OSError as exc:  # pragma: no cover - binding failures are rare and environment-specific
        logger.warning("Failed to start Prometheus exporter on %s:%s: %s", host, port, exc)
        _PROM_REGISTRY = None
        return

    _PROM_SERVER = server
    _PROM_ENDPOINT = (host, server.server_address[1])

    thread = threading.Thread(
        target=server.serve_forever, name="hephaestus-prometheus", daemon=True
    )
    thread.start()
    _PROM_THREAD = thread

    _PROM_COUNTER_FACTORY.update({"cls": counter_cls})
    _PROM_GAUGE_FACTORY.update({"cls": gauge_cls})
    _PROM_HISTOGRAM_FACTORY.update({"cls": histogram_cls})


def _load_prometheus_components() -> tuple[Any, Any, Any, Any, Callable[[Any], bytes], str] | None:
    try:
        from prometheus_client import CollectorRegistry, Counter, Gauge, Histogram
        from prometheus_client.exposition import CONTENT_TYPE_LATEST, generate_latest
    except ImportError:
        return None

    return CollectorRegistry, Counter, Gauge, Histogram, generate_latest, CONTENT_TYPE_LATEST


def _build_handler(
    generate_latest: Callable[[Any], bytes],
    content_type: str,
) -> type[BaseHTTPRequestHandler]:
    registry = _PROM_REGISTRY

    class PrometheusHandler(BaseHTTPRequestHandler):
        def do_GET(self) -> None:  # noqa: D401 - HTTP handler override
            if registry is None:
                self.send_error(503, "Prometheus registry unavailable")
                return

            if self.path not in {"/metrics", "/metrics/"}:
                self.send_error(404, "Not Found")
                return

            try:
                payload = generate_latest(registry)
            except Exception as exc:  # pragma: no cover - defensive guard for exporter failures
                logger.warning("Prometheus exporter error: %s", exc)
                self.send_error(500, "Exporter failure")
                return

            self.send_response(200)
            self.send_header("Content-Type", content_type)
            self.send_header("Content-Length", str(len(payload)))
            self.end_headers()
            self.wfile.write(payload)

        def log_message(self, format: str, *args: Any) -> None:  # noqa: A003 - signature required
            logger.debug("Prometheus exporter: " + format, *args)

    return PrometheusHandler


def _sanitize_metric_name(name: str) -> str:
    sanitized = re.sub(r"[^a-zA-Z0-9_:]", "_", name)
    if not re.match(r"^[a-zA-Z_:]", sanitized):
        sanitized = f"hephaestus_{sanitized}"
    return sanitized


def _merge_attributes(attributes: dict[str, Any] | None) -> dict[str, str]:
    merged: dict[str, str] = dict(_PROM_RESOURCE_ATTRIBUTES)
    if attributes:
        merged.update({str(k): str(v) for k, v in attributes.items()})
    return merged


def _serialize_attributes(attributes: dict[str, Any] | None) -> str:
    merged = _merge_attributes(attributes)
    if not merged:
        return ""
    return ",".join(f"{key}={value}" for key, value in sorted(merged.items()))


def _export_to_prometheus(
    factory: Callable[[str], Any],
    name: str,
    value: float,
    attributes: dict[str, Any] | None,
) -> None:
    if _PROM_REGISTRY is None:
        _ensure_prometheus_exporter()
    if _PROM_REGISTRY is None:
        return

    metric = factory(name)
    label_value = _serialize_attributes(attributes)

    labeled = metric.labels(attributes=label_value)

    if hasattr(labeled, "set"):
        labeled.set(value)
    elif hasattr(labeled, "observe"):
        labeled.observe(value)
    elif hasattr(labeled, "inc"):
        labeled.inc(value)


_PROM_COUNTER_FACTORY: dict[str, Any] = {}
_PROM_GAUGE_FACTORY: dict[str, Any] = {}
_PROM_HISTOGRAM_FACTORY: dict[str, Any] = {}


def _prometheus_counter(name: str) -> Any:
    sanitized = _sanitize_metric_name(name)
    counter = _PROM_COUNTERS.get(sanitized)
    if counter is None:
        counter_cls = _PROM_COUNTER_FACTORY.get("cls")
        if counter_cls is None:
            return _NoOpPrometheusMetric()
        counter = counter_cls(
            sanitized,
            f"Counter for {name}",
            labelnames=("attributes",),
            registry=_PROM_REGISTRY,
        )
        _PROM_COUNTERS[sanitized] = counter
    return counter


def _prometheus_gauge(name: str) -> Any:
    sanitized = _sanitize_metric_name(name)
    gauge = _PROM_GAUGES.get(sanitized)
    if gauge is None:
        gauge_cls = _PROM_GAUGE_FACTORY.get("cls")
        if gauge_cls is None:
            return _NoOpPrometheusMetric()
        gauge = gauge_cls(
            sanitized,
            f"Gauge for {name}",
            labelnames=("attributes",),
            registry=_PROM_REGISTRY,
        )
        _PROM_GAUGES[sanitized] = gauge
    return gauge


def _prometheus_histogram(name: str) -> Any:
    sanitized = _sanitize_metric_name(name)
    histogram = _PROM_HISTOGRAMS.get(sanitized)
    if histogram is None:
        histogram_cls = _PROM_HISTOGRAM_FACTORY.get("cls")
        if histogram_cls is None:
            return _NoOpPrometheusMetric()
        histogram = histogram_cls(
            sanitized,
            f"Histogram for {name}",
            labelnames=("attributes",),
            registry=_PROM_REGISTRY,
        )
        _PROM_HISTOGRAMS[sanitized] = histogram
    return histogram


class _NoOpPrometheusMetric:
    def labels(self, **_: Any) -> _NoOpPrometheusMetric:  # noqa: D401
        return self

    def inc(self, value: float) -> None:
        _ = value

    def observe(self, value: float) -> None:
        _ = value

    def set(self, value: float) -> None:
        _ = value
