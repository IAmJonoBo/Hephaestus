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

import os
from typing import Any

from hephaestus import events as _events

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
]

# Re-export event definitions for backwards compatibility with the legacy
# ``hephaestus.telemetry`` module.
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


# Exposed for tests that monkeypatch hephaestus.telemetry.trace
_trace_module: Any | None = None
trace: Any | None = None


def is_telemetry_enabled() -> bool:
    """Check if OpenTelemetry is enabled via environment variable.

    Returns:
        True if HEPHAESTUS_TELEMETRY_ENABLED is set to "true"
    """
    return os.getenv("HEPHAESTUS_TELEMETRY_ENABLED", "").lower() == "true"


def get_tracer(name: str) -> Any:
    """Get an OpenTelemetry tracer for the given module.

    Args:
        name: Module name (typically ``__name__``)

    Returns:
        Tracer instance if telemetry is enabled, otherwise a no-op tracer
    """
    global trace

    if not is_telemetry_enabled():
        return _NoOpTracer()

    try:
        from opentelemetry import trace as otel_trace  # type: ignore[import-not-found]
    except ImportError:
        # OpenTelemetry not installed, return no-op tracer
        trace = None
        return _NoOpTracer()
    else:
        global _trace_module
        _trace_module = otel_trace
        trace = otel_trace
        return otel_trace.get_tracer(name)


def configure_telemetry() -> None:
    """Initialize OpenTelemetry providers and exporters.

    This should be called once at application startup if telemetry is enabled.
    Uses environment variables for configuration:

    - OTEL_EXPORTER_OTLP_ENDPOINT: OTLP endpoint
    - OTEL_SERVICE_NAME: Service name (default: ``hephaestus``)
    """
    if not is_telemetry_enabled():
        return

    global trace

    try:
        import importlib

        trace_module = importlib.import_module("opentelemetry.trace")
        exporter_module = importlib.import_module(
            "opentelemetry.exporter.otlp.proto.grpc.trace_exporter"
        )
        resources_module = importlib.import_module("opentelemetry.sdk.resources")
        sdk_trace_module = importlib.import_module("opentelemetry.sdk.trace")
        sdk_export_module = importlib.import_module("opentelemetry.sdk.trace.export")
    except ImportError:
        # OpenTelemetry not installed, silently skip
        return
    except Exception as exc:
        # Log configuration errors but do not break functionality
        import logging

        logging.getLogger("hephaestus.telemetry").warning("Telemetry configuration error: %s", exc)
        return

    exporter_namespace = exporter_module.__dict__
    resources_namespace = resources_module.__dict__
    sdk_trace_namespace = sdk_trace_module.__dict__
    sdk_export_namespace = sdk_export_module.__dict__

    otlp_span_exporter_cls = exporter_namespace["OTLPSpanExporter"]
    resource_cls = resources_namespace["Resource"]
    service_name_attr = resources_namespace["SERVICE_NAME"]
    tracer_provider_cls = sdk_trace_namespace["TracerProvider"]
    batch_span_processor_cls = sdk_export_namespace["BatchSpanProcessor"]

    trace = trace_module

    # Create resource with service name
    service_name = os.getenv("OTEL_SERVICE_NAME", "hephaestus")
    resource = resource_cls(attributes={service_name_attr: service_name})

    # Configure tracer provider
    provider = tracer_provider_cls(resource=resource)

    # Add OTLP exporter if endpoint is configured
    endpoint = os.getenv("OTEL_EXPORTER_OTLP_ENDPOINT")
    if endpoint:
        otlp_exporter = otlp_span_exporter_cls(endpoint=endpoint)
        provider.add_span_processor(batch_span_processor_cls(otlp_exporter))

    # Set as global tracer provider
    trace_module.set_tracer_provider(provider)


class _NoOpTracer:
    """No-op tracer that provides the same interface as OpenTelemetry tracer."""

    def start_as_current_span(
        self,
        name: str,
        *args: Any,
        **kwargs: Any,
    ) -> _NoOpSpan:
        """Return a no-op context manager."""
        _ = name
        return _NoOpSpan()


class _NoOpSpan:
    """No-op span context manager."""

    def __enter__(self) -> _NoOpSpan:
        return self

    def __exit__(self, *args: Any) -> None:
        return None

    def set_attribute(self, key: str, value: Any) -> None:
        """No-op attribute setter."""
        _ = (key, value)

    def add_event(self, name: str, attributes: dict[str, Any] | None = None) -> None:
        """No-op event recorder."""
        _ = (name, attributes)
