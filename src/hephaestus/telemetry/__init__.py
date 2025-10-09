"""OpenTelemetry integration for observability (ADR-0003 Phase 1).

This module provides optional distributed tracing and metrics collection
using OpenTelemetry. All functionality is opt-in and disabled by default.

Environment Variables:
    HEPHAESTUS_TELEMETRY_ENABLED: Set to 'true' to enable telemetry
    OTEL_EXPORTER_OTLP_ENDPOINT: OTLP exporter endpoint (default: http://localhost:4318)
    OTEL_SERVICE_NAME: Service name for traces (default: hephaestus)
    HEPHAESTUS_TELEMETRY_PRIVACY: Privacy mode (strict|balanced|minimal, default: strict)

Example:
    export HEPHAESTUS_TELEMETRY_ENABLED=true
    export OTEL_EXPORTER_OTLP_ENDPOINT=http://localhost:4318
    hephaestus guard-rails
"""

from __future__ import annotations

import importlib
import os
from typing import Any

from hephaestus import events as _events

# Import tracing and metrics modules
try:
    from hephaestus.telemetry import metrics as _metrics, tracing as _tracing

    trace_command = _tracing.trace_command
    trace_operation = _tracing.trace_operation  # type: ignore[has-type]
    record_counter = _metrics.record_counter
    record_gauge = _metrics.record_gauge
    record_histogram = _metrics.record_histogram
except ImportError:
    # If OpenTelemetry not installed, provide no-op implementations
    def trace_command(name: str):  # type: ignore[no-untyped-def,misc]
        def decorator(func):  # type: ignore[no-untyped-def]
            return func

        return decorator

    def trace_operation(name: str, **kwargs):  # type: ignore[no-untyped-def]
        from contextlib import nullcontext

        return nullcontext()

    def record_counter(name: str, value: int = 1, attributes=None):  # type: ignore[no-untyped-def]
        pass

    def record_gauge(name: str, value: float, attributes=None):  # type: ignore[no-untyped-def]
        pass

    def record_histogram(name: str, value: float, attributes=None):  # type: ignore[no-untyped-def]
        pass


__all__ = [
    "is_telemetry_enabled",
    "get_tracer",
    "configure_telemetry",
    "TelemetryEvent",
    "TelemetryRegistry",
    "registry",
    "emit_event",
    "operation_context",
    "generate_run_id",
    "generate_operation_id",
    # Tracing utilities
    "trace_command",
    "trace_operation",
    # Metrics utilities
    "record_counter",
    "record_gauge",
    "record_histogram",
]

# Re-export event definitions for backwards compatibility with the legacy module.
__all__ += [name for name in _events.__all__ if name not in __all__]

TelemetryEvent = _events.TelemetryEvent
TelemetryRegistry = _events.TelemetryRegistry
registry = _events.registry
emit_event = _events.emit_event
operation_context = _events.operation_context
generate_run_id = _events.generate_run_id
generate_operation_id = _events.generate_operation_id


def __getattr__(name: str) -> Any:
    if hasattr(_events, name):
        return getattr(_events, name)
    raise AttributeError(f"module 'hephaestus.telemetry' has no attribute {name!r}")


trace: Any | None = None


def is_telemetry_enabled() -> bool:
    """Check if OpenTelemetry is enabled via environment variable."""

    return os.getenv("HEPHAESTUS_TELEMETRY_ENABLED", "").lower() == "true"


def get_tracer(name: str) -> Any:
    """Get an OpenTelemetry tracer for the given module."""

    global trace

    if not is_telemetry_enabled():
        return _NoOpTracer()

    try:
        otel_trace = importlib.import_module("opentelemetry.trace")
    except ImportError:
        trace = None
        return _NoOpTracer()

    trace = otel_trace
    return otel_trace.get_tracer(name)


def configure_telemetry() -> None:
    """Initialize OpenTelemetry providers and exporters."""

    global trace

    if not is_telemetry_enabled():
        return

    try:
        otel_trace = importlib.import_module("opentelemetry.trace")
        otel_exporter = importlib.import_module(
            "opentelemetry.exporter.otlp.proto.grpc.trace_exporter"
        )
        sdk_resources = importlib.import_module("opentelemetry.sdk.resources")
        sdk_trace = importlib.import_module("opentelemetry.sdk.trace")
        sdk_trace_export = importlib.import_module("opentelemetry.sdk.trace.export")
    except ImportError:
        return
    except Exception as exc:  # pragma: no cover - defensive logging path
        import logging

        logging.getLogger("hephaestus.telemetry").warning("Telemetry configuration error: %s", exc)
        return

    trace = otel_trace

    otlp_span_exporter_cls = otel_exporter.OTLPSpanExporter
    service_name_attr = sdk_resources.SERVICE_NAME
    resource_cls = sdk_resources.Resource
    tracer_provider_cls = sdk_trace.TracerProvider
    batch_span_processor_cls = sdk_trace_export.BatchSpanProcessor

    service_name = os.getenv("OTEL_SERVICE_NAME", "hephaestus")
    resource = resource_cls(attributes={service_name_attr: service_name})

    provider = tracer_provider_cls(resource=resource)

    endpoint = os.getenv("OTEL_EXPORTER_OTLP_ENDPOINT")
    if endpoint:
        otlp_exporter = otlp_span_exporter_cls(endpoint=endpoint)
        provider.add_span_processor(batch_span_processor_cls(otlp_exporter))

    otel_trace.set_tracer_provider(provider)


class _NoOpTracer:
    """No-op tracer that provides the same interface as OpenTelemetry tracer."""

    def start_as_current_span(
        self,
        name: str,
        *args: Any,
        **kwargs: Any,
    ) -> _NoOpSpan:
        _ = (name, args, kwargs)
        return _NoOpSpan()


class _NoOpSpan:
    """No-op span context manager."""

    def __enter__(self) -> _NoOpSpan:
        return self

    def __exit__(self, *args: Any) -> None:
        _ = args

    def set_attribute(self, key: str, value: Any) -> None:
        _ = (key, value)

    def add_event(self, name: str, attributes: dict[str, Any] | None = None) -> None:
        _ = (name, attributes)
