"""Tests for OpenTelemetry tracing and metrics (ADR-0003 Sprint 2)."""

from __future__ import annotations

from unittest.mock import MagicMock, patch

import pytest

from hephaestus.telemetry import metrics, tracing


class TestTracing:
    """Tests for tracing utilities."""

    @patch("hephaestus.telemetry.tracing.is_telemetry_enabled", return_value=False)
    def test_trace_command_disabled(self, mock_enabled):
        """Test that trace_command is no-op when telemetry disabled."""

        @tracing.trace_command("test-command")
        def test_func():
            return "result"

        result = test_func()
        assert result == "result"

    @patch("hephaestus.telemetry.tracing.is_telemetry_enabled", return_value=True)
    @patch("hephaestus.telemetry.tracing.get_tracer")
    def test_trace_command_enabled(self, mock_get_tracer, mock_enabled):
        """Test that trace_command creates spans when telemetry enabled."""
        mock_span = MagicMock()
        mock_tracer = MagicMock()
        mock_tracer.start_as_current_span.return_value.__enter__.return_value = mock_span
        mock_get_tracer.return_value = mock_tracer

        @tracing.trace_command("test-command")
        def test_func(arg1: str):
            return f"result-{arg1}"

        result = test_func("value")

        assert result == "result-value"
        mock_get_tracer.assert_called_once()
        mock_tracer.start_as_current_span.assert_called_once_with("cli.test-command")
        mock_span.set_attribute.assert_any_call("command.name", "test-command")
        mock_span.set_attribute.assert_any_call("command.success", True)

    @patch("hephaestus.telemetry.tracing.is_telemetry_enabled", return_value=True)
    @patch("hephaestus.telemetry.tracing.get_tracer")
    def test_trace_command_with_exception(self, mock_get_tracer, mock_enabled):
        """Test that trace_command records exceptions."""
        mock_span = MagicMock()
        mock_tracer = MagicMock()
        mock_tracer.start_as_current_span.return_value.__enter__.return_value = mock_span
        mock_get_tracer.return_value = mock_tracer

        @tracing.trace_command("test-command")
        def test_func():
            raise ValueError("test error")

        with pytest.raises(ValueError, match="test error"):
            test_func()

        mock_span.set_attribute.assert_any_call("command.success", False)
        mock_span.add_event.assert_called_once()

    @patch("hephaestus.telemetry.tracing.is_telemetry_enabled", return_value=False)
    def test_trace_operation_disabled(self, mock_enabled):
        """Test that trace_operation is no-op when telemetry disabled."""
        with tracing.trace_operation("test-op") as span:
            assert span is None

    @patch("hephaestus.telemetry.tracing.is_telemetry_enabled", return_value=True)
    @patch("hephaestus.telemetry.tracing.get_tracer")
    def test_trace_operation_enabled(self, mock_get_tracer, mock_enabled):
        """Test that trace_operation creates spans when telemetry enabled."""
        mock_span = MagicMock()
        mock_tracer = MagicMock()
        mock_tracer.start_as_current_span.return_value.__enter__.return_value = mock_span
        mock_get_tracer.return_value = mock_tracer

        with tracing.trace_operation("test-op", foo="bar") as span:
            assert span is mock_span

        mock_get_tracer.assert_called_once()
        mock_tracer.start_as_current_span.assert_called_once_with("test-op")
        mock_span.set_attribute.assert_any_call("operation.foo", "bar")
        mock_span.set_attribute.assert_any_call("operation.success", True)

    @patch("hephaestus.telemetry.tracing.is_telemetry_enabled", return_value=True)
    @patch("hephaestus.telemetry.tracing.get_tracer")
    def test_trace_operation_with_exception(self, mock_get_tracer, mock_enabled):
        """Test that trace_operation records exceptions."""
        mock_span = MagicMock()
        mock_tracer = MagicMock()
        mock_tracer.start_as_current_span.return_value.__enter__.return_value = mock_span
        mock_get_tracer.return_value = mock_tracer

        with pytest.raises(ValueError, match="test error"):
            with tracing.trace_operation("test-op"):
                raise ValueError("test error")

        mock_span.set_attribute.assert_any_call("operation.success", False)
        mock_span.add_event.assert_called_once()


class TestMetrics:
    """Tests for metrics utilities."""

    @patch("hephaestus.telemetry.metrics.is_metrics_enabled", return_value=False)
    def test_record_counter_disabled(self, mock_enabled):
        """Test that record_counter is no-op when metrics disabled."""
        # Should not raise
        metrics.record_counter("test.counter", 1)

    @patch("hephaestus.telemetry.metrics.is_metrics_enabled", return_value=True)
    @patch("hephaestus.telemetry.metrics.get_meter")
    def test_record_counter_enabled(self, mock_get_meter, mock_enabled):
        """Test that record_counter creates and adds to counter."""
        mock_counter = MagicMock()
        mock_meter = MagicMock()
        mock_meter.create_counter.return_value = mock_counter
        mock_get_meter.return_value = mock_meter

        metrics.record_counter("test.counter", 5, {"foo": "bar"})

        mock_meter.create_counter.assert_called_once()
        mock_counter.add.assert_called_once_with(5, {"foo": "bar"})

    @patch("hephaestus.telemetry.metrics.is_metrics_enabled", return_value=False)
    def test_record_gauge_disabled(self, mock_enabled):
        """Test that record_gauge is no-op when metrics disabled."""
        # Should not raise
        metrics.record_gauge("test.gauge", 42.5)

    @patch("hephaestus.telemetry.metrics.is_metrics_enabled", return_value=False)
    def test_record_histogram_disabled(self, mock_enabled):
        """Test that record_histogram is no-op when metrics disabled."""
        # Should not raise
        metrics.record_histogram("test.histogram", 123.45)

    @patch("hephaestus.telemetry.metrics.is_metrics_enabled", return_value=True)
    @patch("hephaestus.telemetry.metrics.get_meter")
    def test_record_histogram_enabled(self, mock_get_meter, mock_enabled):
        """Test that record_histogram creates and records to histogram."""
        mock_histogram = MagicMock()
        mock_meter = MagicMock()
        mock_meter.create_histogram.return_value = mock_histogram
        mock_get_meter.return_value = mock_meter

        metrics.record_histogram("test.histogram", 123.45, {"unit": "ms"})

        mock_meter.create_histogram.assert_called_once()
        mock_histogram.record.assert_called_once_with(123.45, {"unit": "ms"})


class TestNoOpImplementations:
    """Tests for no-op implementations."""

    def test_noop_meter_counter(self):
        """Test no-op meter counter."""
        meter = metrics._NoOpMeter()
        counter = meter.create_counter("test")
        counter.add(1, {})  # Should not raise

    def test_noop_meter_gauge(self):
        """Test no-op meter gauge."""
        meter = metrics._NoOpMeter()
        gauge = meter.create_observable_gauge("test", [])
        assert gauge is not None  # Should exist but do nothing

    def test_noop_meter_histogram(self):
        """Test no-op meter histogram."""
        meter = metrics._NoOpMeter()
        histogram = meter.create_histogram("test")
        histogram.record(1.0, {})  # Should not raise


class TestIntegration:
    """Integration tests for tracing and metrics together."""

    @patch("hephaestus.telemetry.tracing.is_telemetry_enabled", return_value=True)
    @patch("hephaestus.telemetry.metrics.is_metrics_enabled", return_value=True)
    @patch("hephaestus.telemetry.tracing.get_tracer")
    @patch("hephaestus.telemetry.metrics.get_meter")
    def test_trace_and_metrics_together(
        self, mock_get_meter, mock_get_tracer, mock_metrics_enabled, mock_trace_enabled
    ):
        """Test using tracing and metrics together."""
        mock_span = MagicMock()
        mock_tracer = MagicMock()
        mock_tracer.start_as_current_span.return_value.__enter__.return_value = mock_span
        mock_get_tracer.return_value = mock_tracer

        mock_counter = MagicMock()
        mock_meter = MagicMock()
        mock_meter.create_counter.return_value = mock_counter
        mock_get_meter.return_value = mock_meter

        @tracing.trace_command("test-command")
        def test_func():
            with tracing.trace_operation("test-op"):
                metrics.record_counter("test.counter", 1)
            return "result"

        result = test_func()

        assert result == "result"
        # Verify both tracing and metrics were called
        mock_get_tracer.assert_called()
        mock_get_meter.assert_called()
        mock_counter.add.assert_called_once()
