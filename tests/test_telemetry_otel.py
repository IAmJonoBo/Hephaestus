"""Tests for OpenTelemetry integration (ADR-0003 Phase 1)."""

from __future__ import annotations

import importlib
import importlib.util
import os
from unittest.mock import patch

import pytest  # type: ignore[import-not-found]

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
