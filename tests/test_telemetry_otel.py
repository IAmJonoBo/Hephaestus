"""Tests for OpenTelemetry integration (ADR-0003 Phase 1)."""

from __future__ import annotations

import os
from unittest.mock import Mock, patch

import pytest

from hephaestus.telemetry import configure_telemetry, get_tracer, is_telemetry_enabled


def test_is_telemetry_enabled_default():
    """Telemetry should be disabled by default."""
    with patch.dict(os.environ, {}, clear=True):
        assert is_telemetry_enabled() is False


def test_is_telemetry_enabled_when_set():
    """Telemetry should be enabled when environment variable is set."""
    with patch.dict(os.environ, {"HEPHAESTUS_TELEMETRY_ENABLED": "true"}):
        assert is_telemetry_enabled() is True


def test_is_telemetry_enabled_case_insensitive():
    """Telemetry enabled check should be case insensitive."""
    with patch.dict(os.environ, {"HEPHAESTUS_TELEMETRY_ENABLED": "TRUE"}):
        assert is_telemetry_enabled() is True
    with patch.dict(os.environ, {"HEPHAESTUS_TELEMETRY_ENABLED": "True"}):
        assert is_telemetry_enabled() is True


def test_is_telemetry_enabled_other_values():
    """Other values should not enable telemetry."""
    with patch.dict(os.environ, {"HEPHAESTUS_TELEMETRY_ENABLED": "false"}):
        assert is_telemetry_enabled() is False
    with patch.dict(os.environ, {"HEPHAESTUS_TELEMETRY_ENABLED": "1"}):
        assert is_telemetry_enabled() is False


def test_get_tracer_when_disabled():
    """Should return no-op tracer when telemetry is disabled."""
    with patch.dict(os.environ, {}, clear=True):
        tracer = get_tracer(__name__)
        span = tracer.start_as_current_span("test")

        # Should be usable as context manager
        with span:
            span.set_attribute("key", "value")
            span.add_event("test_event")

        # No exceptions should be raised
        assert span is not None


def test_get_tracer_when_enabled_but_not_installed():
    """Should return no-op tracer when OpenTelemetry is not installed."""
    with patch.dict(os.environ, {"HEPHAESTUS_TELEMETRY_ENABLED": "true"}):
        with patch("hephaestus.telemetry.trace", side_effect=ImportError):
            tracer = get_tracer(__name__)
            span = tracer.start_as_current_span("test")

            with span:
                pass

            assert span is not None


@pytest.mark.skipif(
    os.environ.get("HEPHAESTUS_TELEMETRY_ENABLED", "").lower() != "true",
    reason="Requires HEPHAESTUS_TELEMETRY_ENABLED=true",
)
def test_get_tracer_when_enabled_and_installed():
    """Should return real tracer when telemetry is enabled and installed."""
    try:
        from opentelemetry import trace

        with patch.dict(os.environ, {"HEPHAESTUS_TELEMETRY_ENABLED": "true"}):
            tracer = get_tracer(__name__)
            # Real tracer should have expected methods
            assert hasattr(tracer, "start_as_current_span")
    except ImportError:
        pytest.skip("OpenTelemetry not installed")


def test_configure_telemetry_when_disabled():
    """Should not configure anything when telemetry is disabled."""
    with patch.dict(os.environ, {}, clear=True):
        # Should not raise any exceptions
        configure_telemetry()


def test_configure_telemetry_when_enabled_but_not_installed():
    """Should handle missing OpenTelemetry gracefully."""
    with patch.dict(os.environ, {"HEPHAESTUS_TELEMETRY_ENABLED": "true"}):
        # Should not raise exceptions even if OpenTelemetry is not installed
        configure_telemetry()


def test_configure_telemetry_when_enabled_and_installed():
    """Should configure OpenTelemetry when enabled and installed."""
    try:
        from opentelemetry import trace

        with patch("hephaestus.telemetry.is_telemetry_enabled", return_value=True):
            with patch.dict(
                os.environ,
                {
                    "HEPHAESTUS_TELEMETRY_ENABLED": "true",
                    "OTEL_SERVICE_NAME": "test-service",
                },
            ):
                configure_telemetry()
                # Should be able to get tracer after configuration
                tracer = trace.get_tracer(__name__)
                assert tracer is not None
    except ImportError:
        pytest.skip("OpenTelemetry not installed")


def test_noop_span_context_manager():
    """No-op span should work as context manager."""
    with patch.dict(os.environ, {}, clear=True):
        tracer = get_tracer(__name__)

        # Should work with nested spans
        with tracer.start_as_current_span("outer") as outer_span:
            outer_span.set_attribute("outer", "value")
            outer_span.add_event("outer_event")

            with tracer.start_as_current_span("inner") as inner_span:
                inner_span.set_attribute("inner", "value")
                inner_span.add_event("inner_event")

        # No exceptions should be raised
        assert True
