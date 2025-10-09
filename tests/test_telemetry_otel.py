"""Tests for OpenTelemetry integration (ADR-0003 Phase 1)."""

from __future__ import annotations

import importlib
import importlib.util
import os
from unittest.mock import patch

import pytest

from hephaestus import telemetry
from hephaestus.telemetry import configure_telemetry, get_tracer, is_telemetry_enabled


def test_is_telemetry_enabled_default() -> None:
    """Telemetry should be disabled by default."""
    with patch.dict(os.environ, {}, clear=True):
        assert is_telemetry_enabled() is False


def test_is_telemetry_enabled_when_set() -> None:
    """Telemetry should be enabled when environment variable is set."""
    with patch.dict(os.environ, {"HEPHAESTUS_TELEMETRY_ENABLED": "true"}):
        assert is_telemetry_enabled() is True


def test_is_telemetry_enabled_case_insensitive() -> None:
    """Telemetry enabled check should be case insensitive."""
    with patch.dict(os.environ, {"HEPHAESTUS_TELEMETRY_ENABLED": "TRUE"}):
        assert is_telemetry_enabled() is True
    with patch.dict(os.environ, {"HEPHAESTUS_TELEMETRY_ENABLED": "True"}):
        assert is_telemetry_enabled() is True


def test_is_telemetry_enabled_other_values() -> None:
    """Other values should not enable telemetry."""
    with patch.dict(os.environ, {"HEPHAESTUS_TELEMETRY_ENABLED": "false"}):
        assert is_telemetry_enabled() is False
    with patch.dict(os.environ, {"HEPHAESTUS_TELEMETRY_ENABLED": "1"}):
        assert is_telemetry_enabled() is False


def test_get_tracer_when_disabled() -> None:
    """Should return no-op tracer when telemetry is disabled."""
    with patch.dict(os.environ, {}, clear=True):
        tracer = get_tracer(__name__)
        span = tracer.start_as_current_span("test")

        with span:
            span.set_attribute("key", "value")
            span.add_event("test_event")

        assert span is not None


def test_get_tracer_when_enabled_but_not_installed() -> None:
    """Should return no-op tracer when OpenTelemetry is not installed."""
    with patch.dict(os.environ, {"HEPHAESTUS_TELEMETRY_ENABLED": "true"}):
        with patch("hephaestus.telemetry.importlib.import_module", side_effect=ImportError):
            tracer = get_tracer(__name__)
            span = tracer.start_as_current_span("test")

            with span:
                span.add_event("noop")

            assert span is not None


@pytest.mark.skipif(
    os.environ.get("HEPHAESTUS_TELEMETRY_ENABLED", "").lower() != "true",
    reason="Requires HEPHAESTUS_TELEMETRY_ENABLED=true",
)
def test_get_tracer_when_enabled_and_installed() -> None:
    """Should return real tracer when telemetry is enabled and installed."""
    if importlib.util.find_spec("opentelemetry.trace") is None:
        pytest.skip("OpenTelemetry not installed")

    with patch.dict(os.environ, {"HEPHAESTUS_TELEMETRY_ENABLED": "true"}):
        tracer = get_tracer(__name__)
        assert hasattr(tracer, "start_as_current_span")


def test_configure_telemetry_when_disabled() -> None:
    """Should not configure anything when telemetry is disabled."""
    with patch.dict(os.environ, {}, clear=True):
        configure_telemetry()


def test_configure_telemetry_when_enabled_but_not_installed() -> None:
    """Should handle missing OpenTelemetry gracefully."""
    with patch.dict(os.environ, {"HEPHAESTUS_TELEMETRY_ENABLED": "true"}):
        with patch("hephaestus.telemetry.importlib.import_module", side_effect=ImportError):
            configure_telemetry()


@pytest.mark.skipif(
    os.environ.get("HEPHAESTUS_TELEMETRY_ENABLED", "").lower() != "true",
    reason="Requires HEPHAESTUS_TELEMETRY_ENABLED=true",
)
def test_configure_telemetry_when_enabled_and_installed() -> None:
    """Should configure OpenTelemetry when enabled and installed."""
    spec = importlib.util.find_spec("opentelemetry.trace")
    if spec is None:
        pytest.skip("OpenTelemetry not installed")

    trace_module = importlib.import_module("opentelemetry.trace")

    with patch.dict(
        os.environ,
        {
            "HEPHAESTUS_TELEMETRY_ENABLED": "true",
            "OTEL_SERVICE_NAME": "test-service",
        },
    ):
        configure_telemetry()
        tracer = trace_module.get_tracer(__name__)
        assert tracer is not None


def test_noop_span_context_manager() -> None:
    """No-op span should work as context manager."""
    with patch.dict(os.environ, {}, clear=True):
        tracer = get_tracer(__name__)

        with tracer.start_as_current_span("outer") as outer_span:
            outer_span.set_attribute("outer", "value")
            outer_span.add_event("outer_event")

            with tracer.start_as_current_span("inner") as inner_span:
                inner_span.set_attribute("inner", "value")
                inner_span.add_event("inner_event")

        assert telemetry.trace is None


def test_trace_command_decorator_when_disabled() -> None:
    """trace_command decorator should work when telemetry is disabled."""
    with patch.dict(os.environ, {}, clear=True):
        from hephaestus.telemetry import trace_command

        @trace_command("test_command")
        def sample_command(x: int) -> int:
            return x * 2

        result = sample_command(5)
        assert result == 10


def test_trace_operation_context_when_disabled() -> None:
    """trace_operation context manager should work when telemetry is disabled."""
    with patch.dict(os.environ, {}, clear=True):
        from hephaestus.telemetry import trace_operation

        with trace_operation("test_operation"):
            result = 1 + 1

        assert result == 2


def test_record_counter_when_disabled() -> None:
    """record_counter should work when telemetry is disabled."""
    with patch.dict(os.environ, {}, clear=True):
        from hephaestus.telemetry import record_counter

        # Should not raise
        record_counter("test.counter", 1)
        record_counter("test.counter", 5, attributes={"key": "value"})


def test_record_gauge_when_disabled() -> None:
    """record_gauge should work when telemetry is disabled."""
    with patch.dict(os.environ, {}, clear=True):
        from hephaestus.telemetry import record_gauge

        # Should not raise
        record_gauge("test.gauge", 42.5)
        record_gauge("test.gauge", 100.0, attributes={"key": "value"})


def test_record_histogram_when_disabled() -> None:
    """record_histogram should work when telemetry is disabled."""
    with patch.dict(os.environ, {}, clear=True):
        from hephaestus.telemetry import record_histogram

        # Should not raise
        record_histogram("test.histogram", 1.5)
        record_histogram("test.histogram", 2.5, attributes={"key": "value"})


def test_telemetry_attribute_access() -> None:
    """Telemetry module should re-export events module attributes."""
    # Test that we can access events module attributes through telemetry
    assert hasattr(telemetry, "TelemetryEvent")
    assert hasattr(telemetry, "TelemetryRegistry")
    assert hasattr(telemetry, "emit_event")
    assert hasattr(telemetry, "generate_run_id")
    assert hasattr(telemetry, "generate_operation_id")


def test_telemetry_missing_attribute() -> None:
    """Telemetry module should raise AttributeError for missing attributes."""
    with pytest.raises(AttributeError, match="has no attribute 'nonexistent'"):
        _ = telemetry.nonexistent


def test_get_meter_when_enabled_with_otel() -> None:
    """Test get_meter when telemetry is enabled with OpenTelemetry installed."""
    from hephaestus.telemetry.metrics import get_meter

    with patch.dict(os.environ, {"HEPHAESTUS_TELEMETRY_ENABLED": "true"}):
        with patch("importlib.import_module") as mock_import:
            mock_otel = type("MockOTel", (), {})()
            mock_otel.get_meter = lambda name: f"meter-{name}"
            mock_import.return_value = mock_otel

            meter = get_meter("test")
            assert meter == "meter-test"


def test_get_meter_when_enabled_without_otel() -> None:
    """Test get_meter when telemetry is enabled but OpenTelemetry not installed."""
    from hephaestus.telemetry.metrics import get_meter

    with patch.dict(os.environ, {"HEPHAESTUS_TELEMETRY_ENABLED": "true"}):
        with patch("importlib.import_module", side_effect=ImportError):
            meter = get_meter("test")
            # Should return no-op meter
            assert hasattr(meter, "create_counter")


def test_is_metrics_enabled() -> None:
    """Test is_metrics_enabled function."""
    from hephaestus.telemetry.metrics import is_metrics_enabled

    with patch.dict(os.environ, {}, clear=True):
        assert is_metrics_enabled() is False

    with patch.dict(os.environ, {"HEPHAESTUS_TELEMETRY_ENABLED": "true"}):
        assert is_metrics_enabled() is True


def test_get_tracer_when_enabled_with_otel_module() -> None:
    """Test get_tracer with OpenTelemetry module available."""
    with patch.dict(os.environ, {"HEPHAESTUS_TELEMETRY_ENABLED": "true"}):
        with patch("importlib.import_module") as mock_import:
            mock_otel = type("MockTrace", (), {})()
            mock_otel.get_tracer = lambda name: f"tracer-{name}"
            mock_import.return_value = mock_otel

            tracer = get_tracer("test")
            assert tracer == "tracer-test"


def test_configure_telemetry_with_endpoint() -> None:
    """Test configure_telemetry with OTLP endpoint set."""
    with patch.dict(
        os.environ,
        {
            "HEPHAESTUS_TELEMETRY_ENABLED": "true",
            "OTEL_EXPORTER_OTLP_ENDPOINT": "http://localhost:4317",
            "OTEL_SERVICE_NAME": "test-service",
        },
    ):
        with patch("importlib.import_module") as mock_import:
            # Create mock modules
            mock_trace = type("MockTrace", (), {})()
            mock_exporter = type("MockExporter", (), {})()
            mock_resources = type("MockResources", (), {"SERVICE_NAME": "service.name"})()
            mock_sdk_trace = type("MockSDKTrace", (), {})()
            mock_sdk_export = type("MockSDKExport", (), {})()

            # Setup mocks
            mock_trace.set_tracer_provider = lambda p: None
            mock_exporter.OTLPSpanExporter = lambda endpoint: "span_exporter"
            mock_resources.Resource = lambda attributes: "resource"
            mock_sdk_trace.TracerProvider = lambda resource: type(
                "MockProvider", (), {"add_span_processor": lambda self, p: None}
            )()
            mock_sdk_export.BatchSpanProcessor = lambda exporter: "processor"

            def import_side_effect(module_name: str):
                if "trace_exporter" in module_name:
                    return mock_exporter
                elif "resources" in module_name:
                    return mock_resources
                elif "sdk.trace.export" in module_name:
                    return mock_sdk_export
                elif "sdk.trace" in module_name:
                    return mock_sdk_trace
                elif "trace" in module_name:
                    return mock_trace
                raise ImportError(f"Unknown module: {module_name}")

            mock_import.side_effect = import_side_effect

            # Should not raise
            configure_telemetry()
