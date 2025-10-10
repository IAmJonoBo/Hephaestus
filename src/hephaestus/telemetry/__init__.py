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
from collections.abc import Callable
from contextlib import AbstractContextManager, nullcontext
from functools import lru_cache
from typing import Any, cast

from hephaestus import events as _events

TraceDecorator = Callable[[Callable[..., Any]], Callable[..., Any]]
TraceCommand = Callable[[str], TraceDecorator]
TraceOperation = Callable[..., AbstractContextManager[Any]]
CounterRecorder = Callable[..., None]
GaugeRecorder = Callable[..., None]
HistogramRecorder = Callable[..., None]


def _noop_trace_command(
    command_name: str,
) -> TraceDecorator:  # pragma: no cover - exercised only when OTEL unavailable
    """Return a decorator that leaves the wrapped function unchanged."""

    def decorator(func: Callable[..., Any]) -> Callable[..., Any]:
        _ = (command_name,)
        return func

    return decorator


def _noop_trace_operation(
    operation_name: str, **kwargs: Any
) -> AbstractContextManager[Any]:  # pragma: no cover - OTEL disabled path
    """Provide a no-op context manager when telemetry is unavailable."""

    _ = (operation_name, kwargs)
    return nullcontext()


def _noop_record_counter(
    name: str,
    value: int = 1,
    attributes: dict[str, Any] | None = None,
) -> None:  # pragma: no cover - OTEL disabled path
    _ = (name, value, attributes)


def _noop_record_gauge(
    name: str,
    value: float,
    attributes: dict[str, Any] | None = None,
) -> None:  # pragma: no cover - OTEL disabled path
    _ = (name, value, attributes)


def _noop_record_histogram(
    name: str,
    value: float,
    attributes: dict[str, Any] | None = None,
) -> None:  # pragma: no cover - OTEL disabled path
    _ = (name, value, attributes)


@lru_cache(maxsize=1)
def _resolve_tracing() -> tuple[TraceCommand, TraceOperation] | None:
    try:
        tracing_mod = importlib.import_module("hephaestus.telemetry.tracing")
    except ImportError:  # pragma: no cover - import failure handled in production deployments only
        return None
    return (
        cast(TraceCommand, tracing_mod.trace_command),
        cast(TraceOperation, tracing_mod.trace_operation),
    )


@lru_cache(maxsize=1)
def _resolve_metrics() -> tuple[CounterRecorder, GaugeRecorder, HistogramRecorder] | None:
    try:
        metrics_mod = importlib.import_module("hephaestus.telemetry.metrics")
    except ImportError:  # pragma: no cover - import failure handled in production deployments only
        return None
    return (
        cast(CounterRecorder, metrics_mod.record_counter),
        cast(GaugeRecorder, metrics_mod.record_gauge),
        cast(HistogramRecorder, metrics_mod.record_histogram),
    )


def trace_command(command_name: str) -> TraceDecorator:
    """Return the tracing decorator or a no-op fallback."""

    resolved = _resolve_tracing()
    if resolved is None:  # pragma: no cover - exercised only without telemetry modules
        return _noop_trace_command(command_name)

    real_trace_command, _ = resolved
    return real_trace_command(command_name)


def trace_operation(operation_name: str, **kwargs: Any) -> AbstractContextManager[Any]:
    """Return an operation context manager with tracing when available."""

    resolved = _resolve_tracing()
    if resolved is None:  # pragma: no cover - exercised only without telemetry modules
        return _noop_trace_operation(operation_name, **kwargs)

    _, real_trace_operation = resolved
    return real_trace_operation(operation_name, **kwargs)


def record_counter(
    name: str,
    value: int = 1,
    attributes: dict[str, Any] | None = None,
) -> None:
    resolved = _resolve_metrics()
    if resolved is None:  # pragma: no cover - exercised only without telemetry modules
        _noop_record_counter(name, value, attributes)
        return

    real_record_counter, _, _ = resolved
    real_record_counter(name, value=value, attributes=attributes)


def record_gauge(
    name: str,
    value: float,
    attributes: dict[str, Any] | None = None,
) -> None:
    resolved = _resolve_metrics()
    if resolved is None:  # pragma: no cover - exercised only without telemetry modules
        _noop_record_gauge(name, value, attributes)
        return

    _, real_record_gauge, _ = resolved
    real_record_gauge(name, value=value, attributes=attributes)


def record_histogram(
    name: str,
    value: float,
    attributes: dict[str, Any] | None = None,
) -> None:
    resolved = _resolve_metrics()
    if resolved is None:  # pragma: no cover - exercised only without telemetry modules
        _noop_record_histogram(name, value, attributes)
        return

    _, _, real_record_histogram = resolved
    real_record_histogram(name, value=value, attributes=attributes)


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
    "DEFAULT_TRACE_SAMPLER_RATIO",
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


DEFAULT_TRACE_SAMPLER_RATIO = 0.2
DEFAULT_TRACE_SAMPLER = "parentbased_traceidratio"


def _coerce_ratio(value: str | None) -> float:
    try:
        ratio = float(value) if value is not None else DEFAULT_TRACE_SAMPLER_RATIO
    except ValueError:
        return DEFAULT_TRACE_SAMPLER_RATIO
    return min(max(ratio, 0.0), 1.0)


def _load_sampling_module(sdk_trace: Any) -> Any | None:
    sampling = getattr(sdk_trace, "sampling", None)
    if sampling is not None:
        return sampling
    try:
        return importlib.import_module("opentelemetry.sdk.trace.sampling")
    except ImportError:
        return None


def _build_sampler(sdk_trace: Any) -> Any | None:
    sampling = _load_sampling_module(sdk_trace)
    if sampling is None:
        return None

    sampler_name = os.getenv("OTEL_TRACES_SAMPLER", DEFAULT_TRACE_SAMPLER).lower()
    sampler_arg = os.getenv("OTEL_TRACES_SAMPLER_ARG")

    match sampler_name:
        case "always_on":
            return getattr(sampling, "ALWAYS_ON", None)
        case "always_off":
            return getattr(sampling, "ALWAYS_OFF", None)
        case "traceidratio":
            ratio = _coerce_ratio(sampler_arg)
            if hasattr(sampling, "TraceIdRatioBased"):
                return sampling.TraceIdRatioBased(ratio)
        case "parentbased_always_on":
            parent = getattr(sampling, "ALWAYS_ON", None)
            if parent is not None and hasattr(sampling, "ParentBased"):
                return sampling.ParentBased(parent)
        case "parentbased_always_off":
            parent = getattr(sampling, "ALWAYS_OFF", None)
            if parent is not None and hasattr(sampling, "ParentBased"):
                return sampling.ParentBased(parent)
        case "parentbased_traceidratio" | "parentbased":
            if hasattr(sampling, "ParentBased") and hasattr(sampling, "TraceIdRatioBased"):
                ratio = _coerce_ratio(sampler_arg)
                return sampling.ParentBased(sampling.TraceIdRatioBased(ratio))

    # Fallback: parentbased traceidratio using default ratio when available.
    if hasattr(sampling, "ParentBased") and hasattr(sampling, "TraceIdRatioBased"):
        return sampling.ParentBased(sampling.TraceIdRatioBased(DEFAULT_TRACE_SAMPLER_RATIO))
    return getattr(sampling, "ALWAYS_ON", None)


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

    sampler = _build_sampler(sdk_trace)

    if sampler is not None:
        provider = tracer_provider_cls(resource=resource, sampler=sampler)
    else:
        provider = tracer_provider_cls(resource=resource)

    endpoint = os.getenv("OTEL_EXPORTER_OTLP_ENDPOINT")
    if endpoint:
        otlp_exporter = otlp_span_exporter_cls(endpoint=endpoint)
        provider.add_span_processor(batch_span_processor_cls(otlp_exporter))

    otel_trace.set_tracer_provider(provider)

    try:
        metrics_mod = importlib.import_module("hephaestus.telemetry.metrics")
    except ImportError:  # pragma: no cover - defensive: metrics module missing in deployment
        return

    configure_metrics = getattr(metrics_mod, "configure_metrics", None)
    if callable(configure_metrics):  # pragma: no branch - simple guard
        configure_metrics(resource)


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
