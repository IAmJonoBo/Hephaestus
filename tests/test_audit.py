from __future__ import annotations

import json
from datetime import UTC, datetime, timedelta
from pathlib import Path
from typing import Any

import pytest

from hephaestus import audit as audit_module, telemetry
from hephaestus.api import auth
from hephaestus.audit import AuditStatus, record_audit_event


@pytest.fixture()
def principal() -> auth.AuthenticatedPrincipal:
    now = datetime.now(UTC)
    return auth.AuthenticatedPrincipal(
        principal="svc-audit@example.com",
        roles=frozenset({auth.Role.CLEANUP.value}),
        key_id="audit-key",
        issued_at=now - timedelta(minutes=1),
        expires_at=now + timedelta(hours=1),
    )


def test_record_audit_event_writes_json(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch, principal: auth.AuthenticatedPrincipal
) -> None:
    audit_dir = tmp_path / "audit"
    monkeypatch.setenv("HEPHAESTUS_AUDIT_LOG_DIR", str(audit_dir))

    events: list[tuple[Any, ...]] = []

    def fake_emit(logger: Any, event: Any, **kwargs: Any) -> None:
        events.append((logger, event, kwargs))

    monkeypatch.setattr(telemetry, "emit_event", fake_emit)

    record_audit_event(
        principal,
        operation="rest.cleanup.run",
        status=AuditStatus.SUCCESS,
        parameters={"dry_run": True},
        outcome={"files": 3, "bytes": 100},
        protocol="rest",
    )

    files = list(audit_dir.glob("*.jsonl"))
    assert len(files) == 1
    content = files[0].read_text(encoding="utf-8").strip()
    payload = json.loads(content)
    assert payload["principal"] == "svc-audit@example.com"
    assert payload["operation"] == "rest.cleanup.run"
    assert payload["status"] == "success"
    assert payload["parameters"] == {"dry_run": True}
    assert payload["outcome"] == {"files": 3, "bytes": 100}
    assert payload["protocol"] == "rest"

    assert events
    _, event_def, event_payload = events[0]
    assert event_def is telemetry.API_AUDIT_EVENT
    assert event_payload["operation"] == "rest.cleanup.run"
    assert event_payload["status"] == "success"


def test_record_audit_event_serialises_unknown_types(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
    principal: auth.AuthenticatedPrincipal,
) -> None:
    monkeypatch.setenv("HEPHAESTUS_AUDIT_LOG_DIR", str(tmp_path))

    class Sample:
        def __str__(self) -> str:
            return "sample"

    record_audit_event(
        principal,
        operation="rest.analytics.rankings",
        status=AuditStatus.FAILED,
        parameters={"object": Sample()},
        outcome={"data": {"value": {"set": {1, 2}}}},
        protocol="rest",
    )

    files = list(tmp_path.glob("*.jsonl"))
    assert len(files) == 1
    payload = json.loads(files[0].read_text(encoding="utf-8").strip())
    assert payload["parameters"] == {"object": "sample"}
    assert payload["outcome"] == {"data": {"value": {"set": [1, 2]}}}


def test_record_audit_event_uses_default_directory(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
    principal: auth.AuthenticatedPrincipal,
) -> None:
    target_dir = tmp_path / "audit-default"
    monkeypatch.delenv("HEPHAESTUS_AUDIT_LOG_DIR", raising=False)
    monkeypatch.setattr(audit_module, "DEFAULT_AUDIT_DIR", target_dir)

    record_audit_event(
        principal,
        operation="rest.guard-rails.run",
        status=AuditStatus.SUCCESS,
        parameters={},
        outcome={},
        protocol="rest",
    )

    files = list(target_dir.glob("*.jsonl"))
    assert files, "audit sink should create default directory"
