"""Integration tests for telemetry with OpenTelemetry."""

from __future__ import annotations

import os

import pytest


def test_telemetry_disabled_by_default() -> None:
    """Test that telemetry is disabled by default."""
    from hephaestus.telemetry import is_telemetry_enabled

    # Ensure env var is not set
    if "HEPHAESTUS_TELEMETRY_ENABLED" in os.environ:
        del os.environ["HEPHAESTUS_TELEMETRY_ENABLED"]

    assert is_telemetry_enabled() is False


def test_telemetry_enabled_via_env() -> None:
    """Test that telemetry can be enabled via environment variable."""
    from hephaestus.telemetry import is_telemetry_enabled

    os.environ["HEPHAESTUS_TELEMETRY_ENABLED"] = "true"
    try:
        assert is_telemetry_enabled() is True
    finally:
        del os.environ["HEPHAESTUS_TELEMETRY_ENABLED"]


def test_telemetry_case_insensitive() -> None:
    """Test that telemetry environment variable is case-insensitive."""
    from hephaestus.telemetry import is_telemetry_enabled

    for value in ["True", "TRUE", "true", "TrUe"]:
        os.environ["HEPHAESTUS_TELEMETRY_ENABLED"] = value
        try:
            assert is_telemetry_enabled() is True
        finally:
            del os.environ["HEPHAESTUS_TELEMETRY_ENABLED"]


def test_get_tracer_without_otel() -> None:
    """Test that get_tracer returns no-op tracer when OpenTelemetry not available."""
    from hephaestus.telemetry import get_tracer

    # Disable telemetry
    if "HEPHAESTUS_TELEMETRY_ENABLED" in os.environ:
        del os.environ["HEPHAESTUS_TELEMETRY_ENABLED"]

    tracer = get_tracer("test")
    assert tracer is not None
    assert hasattr(tracer, "start_as_current_span")


def test_no_op_tracer_context_manager() -> None:
    """Test that no-op tracer works as context manager."""
    from hephaestus.telemetry import get_tracer

    # Disable telemetry
    if "HEPHAESTUS_TELEMETRY_ENABLED" in os.environ:
        del os.environ["HEPHAESTUS_TELEMETRY_ENABLED"]

    tracer = get_tracer("test")

    # Should work without errors
    with tracer.start_as_current_span("test_span") as span:
        span.set_attribute("test", "value")
        span.add_event("test_event")


def test_trace_command_decorator_no_op() -> None:
    """Test that trace_command decorator works even without OpenTelemetry."""
    from hephaestus.telemetry import trace_command

    # Disable telemetry
    if "HEPHAESTUS_TELEMETRY_ENABLED" in os.environ:
        del os.environ["HEPHAESTUS_TELEMETRY_ENABLED"]

    @trace_command("test")
    def dummy_command() -> str:
        return "success"

    result = dummy_command()
    assert result == "success"


def test_trace_operation_context_manager_no_op() -> None:
    """Test that trace_operation context manager works without OpenTelemetry."""
    from hephaestus.telemetry import trace_operation

    # Disable telemetry
    if "HEPHAESTUS_TELEMETRY_ENABLED" in os.environ:
        del os.environ["HEPHAESTUS_TELEMETRY_ENABLED"]

    # Should work without errors
    with trace_operation("test_op"):
        result = "success"

    assert result == "success"


def test_record_metrics_no_op() -> None:
    """Test that metric recording works without OpenTelemetry."""
    from hephaestus.telemetry import record_counter, record_gauge, record_histogram

    # Disable telemetry
    if "HEPHAESTUS_TELEMETRY_ENABLED" in os.environ:
        del os.environ["HEPHAESTUS_TELEMETRY_ENABLED"]

    # Should work without errors
    record_counter("test.counter", 1)
    record_gauge("test.gauge", 42.0)
    record_histogram("test.histogram", 3.14)


def test_configure_telemetry_without_otel() -> None:
    """Test that configure_telemetry handles missing OpenTelemetry gracefully."""
    from hephaestus.telemetry import configure_telemetry

    # Disable telemetry
    if "HEPHAESTUS_TELEMETRY_ENABLED" in os.environ:
        del os.environ["HEPHAESTUS_TELEMETRY_ENABLED"]

    # Should not raise errors
    configure_telemetry()


@pytest.mark.skipif(
    not os.getenv("HEPHAESTUS_TEST_WITH_OTEL"),
    reason="OpenTelemetry integration tests require HEPHAESTUS_TEST_WITH_OTEL=true",
)
def test_telemetry_with_otel_installed() -> None:
    """Test telemetry functionality when OpenTelemetry is installed."""
    pytest.importorskip("opentelemetry")

    from hephaestus.telemetry import configure_telemetry, get_tracer, is_telemetry_enabled

    os.environ["HEPHAESTUS_TELEMETRY_ENABLED"] = "true"
    try:
        assert is_telemetry_enabled() is True

        configure_telemetry()

        tracer = get_tracer("test")
        assert tracer is not None

        # Should create real spans
        with tracer.start_as_current_span("test_span") as span:
            span.set_attribute("test_key", "test_value")

    finally:
        del os.environ["HEPHAESTUS_TELEMETRY_ENABLED"]
