from __future__ import annotations

import io
import json
import logging
from collections.abc import Iterator

import pytest

from hephaestus import logging as heph_logging
from hephaestus import events as telemetry


def _reset_logging() -> None:
    root = logging.getLogger()
    for handler in list(root.handlers):
        root.removeHandler(handler)
    for log_filter in list(root.filters):
        root.removeFilter(log_filter)
    root.setLevel(logging.WARNING)


@pytest.fixture(autouse=True)
def logging_guard() -> Iterator[None]:
    _reset_logging()
    try:
        yield
    finally:
        _reset_logging()


def test_emit_event_rejects_missing_fields() -> None:
    heph_logging.configure_logging(stream=io.StringIO())
    logger = logging.getLogger("hephaestus.tests.telemetry")

    with pytest.raises(ValueError, match="missing required fields"):
        telemetry.emit_event(
            logger,
            telemetry.CLI_RELEASE_INSTALL_START,
            repository="owner/project",
            tag="latest",
            destination="/tmp",
            allow_unsigned=False,
            asset_pattern="*",
            manifest_pattern="*",
            sigstore_pattern="*.sigstore",
            require_sigstore=False,
            timeout=30,
        )


def test_emit_event_rejects_unexpected_fields() -> None:
    heph_logging.configure_logging(stream=io.StringIO())
    logger = logging.getLogger("hephaestus.tests.telemetry")

    with pytest.raises(ValueError, match="unexpected fields"):
        telemetry.emit_event(
            logger,
            telemetry.CLI_CLEANUP_COMPLETE,
            removed=0,
            skipped=0,
            errors=0,
            audit_manifest=None,
            extraneous=True,
        )


def test_operation_context_merges_into_payload() -> None:
    stream = io.StringIO()
    heph_logging.configure_logging(log_format="json", stream=stream)
    logger = logging.getLogger("hephaestus.tests.telemetry")

    with telemetry.operation_context("cli.cleanup", operation_id="op-123", command="cleanup"):
        telemetry.emit_event(
            logger,
            telemetry.CLI_CLEANUP_COMPLETE,
            message="Cleanup finished",
            removed=4,
            skipped=1,
            errors=0,
        )

    payload = json.loads(stream.getvalue())
    assert payload["event"] == telemetry.CLI_CLEANUP_COMPLETE.name
    assert payload["payload"]["operation"] == "cli.cleanup"
    assert payload["payload"]["operation_id"] == "op-123"
    assert payload["payload"]["command"] == "cleanup"
