from __future__ import annotations

import io
import json
import logging
from collections.abc import Iterator

import pytest

from hephaestus import logging as heph_logging


def _reset_logging() -> None:
    root = logging.getLogger()
    for handler in list(root.handlers):
        root.removeHandler(handler)
    for log_filter in list(root.filters):
        root.removeFilter(log_filter)
    root.setLevel(logging.WARNING)


@pytest.fixture(autouse=True)
def logging_state_guard() -> Iterator[None]:
    _reset_logging()
    try:
        yield
    finally:
        _reset_logging()


def test_configure_logging_json_emits_structured_payload() -> None:
    stream = io.StringIO()
    heph_logging.configure_logging(log_format="json", run_id="test-run", stream=stream)
    logger = logging.getLogger("hephaestus.tests.logging")

    heph_logging.log_event(
        logger,
        "tests.event",
        message="Structured event",
        repository="owner/project",
        asset="wheelhouse.tar.gz",
        attempt=1,
    )

    payload = json.loads(stream.getvalue())
    assert payload["event"] == "tests.event"
    assert payload["run_id"] == "test-run"
    assert payload["payload"] == {
        "repository": "owner/project",
        "asset": "wheelhouse.tar.gz",
        "attempt": 1,
    }
    assert payload["message"] == "Structured event"
    assert payload["level"] == "INFO"


def test_log_context_merges_with_payload() -> None:
    stream = io.StringIO()
    heph_logging.configure_logging(log_format="json", stream=stream)
    logger = logging.getLogger("hephaestus.tests.logging")

    with heph_logging.log_context(repository="owner/project", command="cleanup"):
        heph_logging.log_event(
            logger,
            "cleanup.run.completed",
            message="Cleanup finished",
            removed=5,
        )

    payload = json.loads(stream.getvalue())
    assert payload["payload"] == {
        "repository": "owner/project",
        "command": "cleanup",
        "removed": 5,
    }


def test_text_formatter_includes_context_fields() -> None:
    stream = io.StringIO()
    heph_logging.configure_logging(log_format="text", run_id="abc123", stream=stream)
    logger = logging.getLogger("hephaestus.tests.logging")

    heph_logging.log_event(
        logger,
        "release.download.completed",
        message="Download complete",
        repository="owner/project",
        asset="wheelhouse.tar.gz",
    )

    output = stream.getvalue().strip()
    assert "Download complete" in output
    assert "release.download.completed" in output
    assert "repository=owner/project" in output
    assert "asset=wheelhouse.tar.gz" in output
    assert "run_id=abc123" in output


def test_configure_logging_replaces_existing_handlers() -> None:
    first_stream = io.StringIO()
    heph_logging.configure_logging(stream=first_stream)

    second_stream = io.StringIO()
    heph_logging.configure_logging(stream=second_stream)

    logger = logging.getLogger("hephaestus.tests.logging")
    heph_logging.log_event(logger, "tests.event", message="After reconfigure")

    assert first_stream.getvalue() == ""
    assert "After reconfigure" in second_stream.getvalue()


def test_log_event_respects_log_level() -> None:
    stream = io.StringIO()
    heph_logging.configure_logging(stream=stream)
    logger = logging.getLogger("hephaestus.tests.logging")

    heph_logging.log_event(
        logger,
        "tests.warning",
        message="Warning event",
        level=logging.WARNING,
    )

    output = stream.getvalue()
    assert "WARNING" in output
    assert "Warning event" in output
    assert "tests.warning" in output
