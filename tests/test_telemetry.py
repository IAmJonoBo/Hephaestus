from __future__ import annotations

import importlib
import io
import json
import logging
import sys
from collections.abc import Iterator
from types import ModuleType
from typing import Any, cast

import pytest

from hephaestus import events
from hephaestus import logging as heph_logging
from hephaestus import telemetry


def _reset_logging() -> None:
    root = logging.getLogger()
    handlers = list(root.handlers)
    for handler in handlers:
        root.removeHandler(handler)
    filters = list(root.filters)
    for log_filter in filters:
        root.removeFilter(log_filter)
    root.setLevel(logging.WARNING)


@pytest.fixture(autouse=True)
def logging_guard() -> Iterator[None]:
    _reset_logging()
    try:
        yield
    finally:
        _reset_logging()


def test_event_validate_rejects_missing_fields() -> None:
    event = events.TelemetryEvent(
        "tests.event",
        "Test event",
        required_fields=("foo", "bar"),
    )

    with pytest.raises(ValueError, match="missing required fields"):
        event.validate({"foo": "value"})


def test_event_validate_rejects_unexpected_fields() -> None:
    event = events.TelemetryEvent(
        "tests.event",
        "Test event",
        required_fields=("foo",),
    )

    with pytest.raises(ValueError, match="unexpected fields"):
        event.validate({"foo": "value", "bar": "extra"})


def test_operation_context_merges_into_payload() -> None:
    stream = io.StringIO()
    heph_logging.configure_logging(log_format="json", stream=stream)
    logger = logging.getLogger("hephaestus.tests.telemetry")

    with events.operation_context("cli.cleanup", operation_id="op-123", command="cleanup"):
        events.emit_event(
            logger,
            events.CLI_CLEANUP_COMPLETE,
            message="Cleanup finished",
            removed=4,
            skipped=1,
            errors=0,
        )

    payload = json.loads(stream.getvalue())
    assert payload["event"] == events.CLI_CLEANUP_COMPLETE.name
    assert payload["payload"]["operation"] == "cli.cleanup"
    assert payload["payload"]["operation_id"] == "op-123"
    assert payload["payload"]["command"] == "cleanup"


def test_module_reexports_event_helpers() -> None:
    assert telemetry.emit_event is events.emit_event
    assert telemetry.CLI_CLEANUP_COMPLETE is events.CLI_CLEANUP_COMPLETE


class _FakeSampler:
    def __init__(self, **kwargs: object) -> None:
        self.kwargs = kwargs


class _FakeTraceIdRatioBased(_FakeSampler):
    def __init__(self, ratio: float) -> None:  # noqa: D401 - simple wrapper
        super().__init__(ratio=ratio)
        self.ratio = ratio


class _FakeParentBased(_FakeSampler):
    def __init__(self, delegate: object) -> None:  # noqa: D401 - simple wrapper
        super().__init__(delegate=delegate)
        self.delegate = delegate


def _install_fake_otel(monkeypatch: pytest.MonkeyPatch) -> ModuleType:
    trace_mod = ModuleType("opentelemetry.trace")
    resources_mod = ModuleType("opentelemetry.sdk.resources")
    sdk_trace_mod = ModuleType("opentelemetry.sdk.trace")
    sdk_trace_sampling_mod = ModuleType("opentelemetry.sdk.trace.sampling")
    sdk_trace_export_mod = ModuleType("opentelemetry.sdk.trace.export")
    exporter_mod = ModuleType("opentelemetry.exporter.otlp.proto.grpc.trace_exporter")

    class FakeTracerProvider:  # noqa: D401 - helper class for tests
        def __init__(self, *, resource: object, sampler: object | None = None) -> None:
            self.resource = resource
            self.sampler = sampler

    class FakeBatchSpanProcessor:  # noqa: D401 - helper class for tests
        def __init__(self, exporter: object) -> None:
            self.exporter = exporter

    class FakeResource:  # noqa: D401 - helper class for tests
        def __init__(self, attributes: dict[str, object]) -> None:
            self.attributes = attributes

    class FakeExporter:  # noqa: D401 - helper class for tests
        def __init__(self, endpoint: str | None = None) -> None:
            self.endpoint = endpoint

    def get_tracer(name: str) -> object:
        return {"name": name}

    provider_store: dict[str, object] = {}

    def set_tracer_provider(provider: object) -> None:
        provider_store["provider"] = provider

    trace_mod.get_tracer = get_tracer  # type: ignore[attr-defined]
    trace_mod.set_tracer_provider = set_tracer_provider  # type: ignore[attr-defined]
    trace_mod._provider_store = provider_store  # type: ignore[attr-defined]

    exporter_mod.OTLPSpanExporter = FakeExporter  # type: ignore[attr-defined]

    resources_mod.SERVICE_NAME = "service.name"  # type: ignore[attr-defined]
    resources_mod.Resource = FakeResource  # type: ignore[attr-defined]

    sdk_trace_mod.TracerProvider = FakeTracerProvider  # type: ignore[attr-defined]
    sdk_trace_mod.sampling = sdk_trace_sampling_mod  # type: ignore[attr-defined]

    sdk_trace_sampling_mod.ALWAYS_ON = _FakeSampler(mode="always_on")  # type: ignore[attr-defined]
    sdk_trace_sampling_mod.ALWAYS_OFF = _FakeSampler(mode="always_off")  # type: ignore[attr-defined]
    sdk_trace_sampling_mod.ParentBased = _FakeParentBased  # type: ignore[attr-defined]
    sdk_trace_sampling_mod.TraceIdRatioBased = _FakeTraceIdRatioBased  # type: ignore[attr-defined]

    sdk_trace_export_mod.BatchSpanProcessor = FakeBatchSpanProcessor  # type: ignore[attr-defined]

    module_map = {
        "opentelemetry.trace": trace_mod,
        "opentelemetry.exporter.otlp.proto.grpc.trace_exporter": exporter_mod,
        "opentelemetry.sdk.resources": resources_mod,
        "opentelemetry.sdk.trace": sdk_trace_mod,
        "opentelemetry.sdk.trace.export": sdk_trace_export_mod,
        "opentelemetry.sdk.trace.sampling": sdk_trace_sampling_mod,
    }

    for name, module in module_map.items():
        monkeypatch.setitem(sys.modules, name, module)

    return trace_mod


def _reload_telemetry() -> None:
    importlib.reload(telemetry)  # pragma: no cover - used for test isolation


@pytest.mark.usefixtures("logging_guard")
def test_configure_telemetry_respects_parentbased_ratio_sampler(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    trace_mod = _install_fake_otel(monkeypatch)
    monkeypatch.setenv("HEPHAESTUS_TELEMETRY_ENABLED", "true")
    monkeypatch.setenv("OTEL_TRACES_SAMPLER", "parentbased_traceidratio")
    monkeypatch.setenv("OTEL_TRACES_SAMPLER_ARG", "0.25")

    _reload_telemetry()
    telemetry.configure_telemetry()

    provider_store = cast(dict[str, Any], trace_mod._provider_store)
    provider = cast(Any, provider_store["provider"])
    assert isinstance(provider.sampler, _FakeParentBased)
    delegate = provider.sampler.delegate
    assert isinstance(delegate, _FakeTraceIdRatioBased)
    assert delegate.ratio == 0.25


@pytest.mark.usefixtures("logging_guard")
def test_configure_telemetry_defaults_to_parentbased(monkeypatch: pytest.MonkeyPatch) -> None:
    trace_mod = _install_fake_otel(monkeypatch)
    monkeypatch.setenv("HEPHAESTUS_TELEMETRY_ENABLED", "true")
    monkeypatch.delenv("OTEL_TRACES_SAMPLER", raising=False)
    monkeypatch.delenv("OTEL_TRACES_SAMPLER_ARG", raising=False)

    _reload_telemetry()
    telemetry.configure_telemetry()

    provider_store = cast(dict[str, Any], trace_mod._provider_store)
    provider = cast(Any, provider_store["provider"])
    assert isinstance(provider.sampler, _FakeParentBased)
    delegate = provider.sampler.delegate
    assert isinstance(delegate, _FakeTraceIdRatioBased)
    assert delegate.ratio == pytest.approx(telemetry.DEFAULT_TRACE_SAMPLER_RATIO)


@pytest.mark.usefixtures("logging_guard")
def test_configure_telemetry_handles_invalid_ratio(monkeypatch: pytest.MonkeyPatch) -> None:
    trace_mod = _install_fake_otel(monkeypatch)
    monkeypatch.setenv("HEPHAESTUS_TELEMETRY_ENABLED", "true")
    monkeypatch.setenv("OTEL_TRACES_SAMPLER", "traceidratio")
    monkeypatch.setenv("OTEL_TRACES_SAMPLER_ARG", "not-a-number")

    _reload_telemetry()
    telemetry.configure_telemetry()

    provider_store = cast(dict[str, Any], trace_mod._provider_store)
    provider = cast(Any, provider_store["provider"])
    assert isinstance(provider.sampler, _FakeTraceIdRatioBased)
    assert provider.sampler.ratio == pytest.approx(telemetry.DEFAULT_TRACE_SAMPLER_RATIO)
