from __future__ import annotations

import io
import json
import logging
from collections.abc import Iterator

import pytest  # type: ignore[import-not-found]

from hephaestus import events, telemetry
from hephaestus import logging as heph_logging


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
