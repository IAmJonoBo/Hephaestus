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

__all__ = [
    "is_telemetry_enabled",
    "get_tracer",
    "configure_telemetry",
]


# Exposed for tests that monkeypatch hephaestus.telemetry.trace
_trace_module: Any | None = None


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
    if not is_telemetry_enabled():
        return _NoOpTracer()

    try:
        from opentelemetry import trace as otel_trace

        global _trace_module
        _trace_module = otel_trace
        return otel_trace.get_tracer(name)
    except ImportError:
        # OpenTelemetry not installed, return no-op tracer
        return _NoOpTracer()


def configure_telemetry() -> None:
    """Initialize OpenTelemetry providers and exporters.

    This should be called once at application startup if telemetry is enabled.
    Uses environment variables for configuration:

    - OTEL_EXPORTER_OTLP_ENDPOINT: OTLP endpoint
    - OTEL_SERVICE_NAME: Service name (default: ``hephaestus``)
    """
    if not is_telemetry_enabled():
        return

    try:
        from opentelemetry import trace
        from opentelemetry.exporter.otlp.proto.grpc.trace_exporter import (
            OTLPSpanExporter,
        )
        from opentelemetry.sdk.resources import SERVICE_NAME, Resource
        from opentelemetry.sdk.trace import TracerProvider
        from opentelemetry.sdk.trace.export import BatchSpanProcessor

        # Create resource with service name
        service_name = os.getenv("OTEL_SERVICE_NAME", "hephaestus")
        resource = Resource(attributes={SERVICE_NAME: service_name})

        # Configure tracer provider
        provider = TracerProvider(resource=resource)

        # Add OTLP exporter if endpoint is configured
        endpoint = os.getenv("OTEL_EXPORTER_OTLP_ENDPOINT")
        if endpoint:
            otlp_exporter = OTLPSpanExporter(endpoint=endpoint)
            provider.add_span_processor(BatchSpanProcessor(otlp_exporter))

        # Set as global tracer provider
        trace.set_tracer_provider(provider)
    except ImportError:
        # OpenTelemetry not installed, silently skip
        pass
    except Exception as exc:
        # Log configuration errors but do not break functionality
        import logging

        logging.getLogger("hephaestus.telemetry").warning("Telemetry configuration error: %s", exc)
        pass


class _NoOpTracer:
    """No-op tracer that provides the same interface as OpenTelemetry tracer."""

    def start_as_current_span(
        self,
        name: str,
        *args: Any,
        **kwargs: Any,
    ) -> _NoOpSpan:
        """Return a no-op context manager."""
        return _NoOpSpan()


class _NoOpSpan:
    """No-op span context manager."""

    def __enter__(self) -> _NoOpSpan:
        return self

    def __exit__(self, *args: Any) -> None:
        pass

    def set_attribute(self, key: str, value: Any) -> None:
        """No-op attribute setter."""
        pass

    def add_event(self, name: str, attributes: dict[str, Any] | None = None) -> None:
        """No-op event recorder."""
        pass
