"""OpenTelemetry metrics collection for Hephaestus (ADR-0003 Sprint 2).

This module provides utilities for collecting and recording metrics
about command execution, quality gates, and resource usage.
"""

from __future__ import annotations

import importlib
import os
from typing import Any

__all__ = [
    "record_counter",
    "record_gauge",
    "record_histogram",
]


def is_metrics_enabled() -> bool:
    """Check if metrics collection is enabled."""
    return os.getenv("HEPHAESTUS_TELEMETRY_ENABLED", "").lower() == "true"


def get_meter(name: str = "hephaestus") -> Any:
    """Get an OpenTelemetry meter for metrics collection.

    Args:
        name: Meter name (default: "hephaestus")

    Returns:
        Meter instance or no-op meter if telemetry disabled
    """
    if not is_metrics_enabled():
        return _NoOpMeter()

    try:
        otel_metrics = importlib.import_module("opentelemetry.metrics")
        return otel_metrics.get_meter(name)
    except ImportError:
        return _NoOpMeter()


def record_counter(
    name: str,
    value: int = 1,
    attributes: dict[str, Any] | None = None,
) -> None:
    """Record a counter metric.

    Counters are cumulative metrics that represent a single monotonically
    increasing counter whose value can only increase or be reset to zero.

    Args:
        name: Metric name (e.g., "hephaestus.commands.executed")
        value: Value to add to the counter (default: 1)
        attributes: Optional attributes to attach to the metric

    Example:
        record_counter("hephaestus.commands.executed", 1, {"command": "guard-rails"})
        record_counter("hephaestus.quality_gates.passed", 1, {"gate": "ruff-check"})
    """
    if not is_metrics_enabled():
        return

    meter = get_meter()
    counter = meter.create_counter(name, description=f"Counter for {name}")
    counter.add(value, attributes or {})


def record_gauge(
    name: str,
    value: float,
    attributes: dict[str, Any] | None = None,
) -> None:
    """Record a gauge metric.

    Gauges represent a single numerical value that can arbitrarily go up and down.

    Args:
        name: Metric name (e.g., "hephaestus.test_coverage")
        value: Current value of the gauge
        attributes: Optional attributes to attach to the metric

    Example:
        record_gauge("hephaestus.test_coverage", 87.29, {"project": "hephaestus"})
        record_gauge("hephaestus.files_cleaned", 142, {"deep_clean": "true"})
    """
    if not is_metrics_enabled():
        return

    meter = get_meter()
    gauge = meter.create_observable_gauge(name, [lambda: value], description=f"Gauge for {name}")
    _ = gauge  # Gauge is auto-collected


def record_histogram(
    name: str,
    value: float,
    attributes: dict[str, Any] | None = None,
) -> None:
    """Record a histogram metric.

    Histograms are used to track the distribution of values.

    Args:
        name: Metric name (e.g., "hephaestus.command.duration")
        value: Value to record in the histogram
        attributes: Optional attributes to attach to the metric

    Example:
        record_histogram("hephaestus.command.duration", 32.1, {"command": "guard-rails"})
        record_histogram("hephaestus.cleanup.size_freed", 15.2, {"unit": "MB"})
    """
    if not is_metrics_enabled():
        return

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

    pass


class _NoOpHistogram:
    """No-op histogram."""

    def record(self, value: float, attributes: dict[str, Any]) -> None:
        _ = (value, attributes)
