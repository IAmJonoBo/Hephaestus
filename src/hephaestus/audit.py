from __future__ import annotations

import json
import logging
import os
from collections.abc import Mapping
from datetime import UTC, datetime
from enum import Enum
from pathlib import Path
from typing import TYPE_CHECKING, Any

from hephaestus import telemetry

__all__ = ["AUDIT_LOG_DIR_ENV", "AuditStatus", "record_audit_event"]

AUDIT_LOG_DIR_ENV = "HEPHAESTUS_AUDIT_LOG_DIR"
DEFAULT_AUDIT_DIR = Path(".hephaestus/audit")

logger = logging.getLogger("hephaestus.audit")


class AuditStatus(str, Enum):
    """Outcome classification for audit events."""

    SUCCESS = "success"
    DENIED = "denied"
    FAILED = "failed"


if TYPE_CHECKING:  # pragma: no cover
    from hephaestus.api.auth import AuthenticatedPrincipal


def record_audit_event(
    principal: "AuthenticatedPrincipal",  # noqa: UP037
    *,
    operation: str,
    status: AuditStatus,
    parameters: Mapping[str, Any] | None = None,
    outcome: Mapping[str, Any] | None = None,
    protocol: str | None = None,
) -> None:
    """Persist and emit a structured audit event."""

    audit_dir = _resolve_audit_dir()
    audit_dir.mkdir(parents=True, exist_ok=True)

    timestamp = datetime.now(UTC)
    entry: dict[str, Any] = {
        "timestamp": timestamp.isoformat(),
        "principal": principal.principal,
        "key_id": principal.key_id,
        "operation": operation,
        "status": status.value,
    }
    if protocol:
        entry["protocol"] = protocol
    if parameters:
        entry["parameters"] = _serialise(parameters)
    if outcome:
        entry["outcome"] = _serialise(outcome)

    filename = audit_dir / f"audit-{timestamp.strftime('%Y%m%d')}.jsonl"
    with filename.open("a", encoding="utf-8") as handle:
        handle.write(json.dumps(entry, ensure_ascii=False) + "\n")

    payload: dict[str, Any] = {
        "principal": principal.principal,
        "operation": operation,
        "status": status.value,
        "key_id": principal.key_id,
    }
    if protocol:
        payload["protocol"] = protocol
    if parameters:
        payload["parameters"] = _serialise(parameters)
    if outcome:
        payload["outcome"] = _serialise(outcome)

    telemetry.emit_event(logger, telemetry.API_AUDIT_EVENT, **payload)


def _resolve_audit_dir() -> Path:
    override = os.environ.get(AUDIT_LOG_DIR_ENV)
    if override:
        return Path(override).expanduser()
    return DEFAULT_AUDIT_DIR


def _serialise(value: Any) -> Any:
    if isinstance(value, Mapping):
        return {str(key): _serialise(item) for key, item in value.items()}
    if isinstance(value, (list, tuple, set)):
        return [_serialise(item) for item in value]
    if isinstance(value, (str, int, float, bool)) or value is None:
        return value
    return str(value)
