"""Structured logging utilities for the Hephaestus toolkit."""

from __future__ import annotations

import contextlib
import contextvars
import json
import logging
import sys
from collections.abc import Iterator
from datetime import UTC, datetime
from typing import IO, Any, Literal, cast

__all__ = [
    "configure_logging",
    "log_context",
    "log_event",
]


LogFormat = Literal["text", "json"]


_context: contextvars.ContextVar[dict[str, Any] | None] = contextvars.ContextVar(
    "hephaestus_log_context", default=None,
)


class RunIDFilter(logging.Filter):
    """Inject a constant run identifier into every log record."""

    def __init__(self, run_id: str | None) -> None:
        super().__init__(name="hephaestus-run-id")
        self._run_id = run_id

    def filter(self, record: logging.LogRecord) -> bool:  # noqa: D401 - standard logging hook
        if self._run_id:
            record_with_extra = cast(Any, record)
            record_with_extra.run_id = self._run_id
        return True


class StructuredTextFormatter(logging.Formatter):
    """Append structured context to standard text logs."""

    def __init__(self) -> None:
        super().__init__(fmt="%(levelname)s %(name)s: %(message)s")

    def format(self, record: logging.LogRecord) -> str:  # noqa: D401 - inherited behaviour
        message = super().format(record)
        extras: list[str] = []

        event = getattr(record, "event", None)
        if event:
            extras.append(f"event={event}")

        run_id = getattr(record, "run_id", None)
        if run_id:
            extras.append(f"run_id={run_id}")

        payload = getattr(record, "payload", None)
        if isinstance(payload, dict) and payload:
            extras.extend(f"{key}={_stringify(value)}" for key, value in payload.items())

        if extras:
            message = f"{message} | {' '.join(extras)}"

        return message


class StructuredJSONFormatter(logging.Formatter):
    """Emit structured JSON logs for machine consumption."""

    def format(self, record: logging.LogRecord) -> str:  # noqa: D401 - inherited behaviour
        payload: dict[str, Any] = {
            "timestamp": datetime.fromtimestamp(record.created, tz=UTC).isoformat(),
            "level": record.levelname,
            "logger": record.name,
            "message": record.getMessage(),
        }

        run_id = getattr(record, "run_id", None)
        if run_id:
            payload["run_id"] = run_id

        event = getattr(record, "event", None)
        if event:
            payload["event"] = event

        record_payload = getattr(record, "payload", None)
        if isinstance(record_payload, dict) and record_payload:
            payload["payload"] = record_payload

        if record.exc_info:
            payload["exc_info"] = self.formatException(record.exc_info)

        return json.dumps(payload, default=_stringify)


def configure_logging(
    *,
    log_format: LogFormat = "text",
    level: int | str = logging.INFO,
    run_id: str | None = None,
    stream: IO[str] | None = None,
) -> None:
    """Configure global logging handlers for the CLI."""

    root = logging.getLogger()
    numeric_level = _normalise_level(level)
    root.setLevel(numeric_level)

    for handler in list(root.handlers):
        root.removeHandler(handler)
    for log_filter in list(root.filters):
        root.removeFilter(log_filter)

    handler = logging.StreamHandler(stream or sys.stderr)
    handler.setLevel(numeric_level)
    handler.addFilter(RunIDFilter(run_id))
    if log_format == "json":
        handler.setFormatter(StructuredJSONFormatter())
    else:
        handler.setFormatter(StructuredTextFormatter())

    root.addHandler(handler)


@contextlib.contextmanager
def log_context(**fields: Any) -> Iterator[None]:
    """Bind contextual fields to subsequent log events."""

    if not fields:
        yield
        return

    current = dict(_context.get() or {})
    current.update(fields)
    token = _context.set(current)
    try:
        yield
    finally:
        _context.reset(token)


def log_event(
    logger: logging.Logger,
    event: str,
    *,
    level: int = logging.INFO,
    message: str | None = None,
    **payload: Any,
) -> None:
    """Emit a structured log event that honours the active context."""

    merged_payload = dict(_context.get() or {})
    merged_payload.update(payload)

    extra: dict[str, Any] = {"event": event}
    if merged_payload:
        extra["payload"] = merged_payload

    logger.log(level, message or event, extra=extra)


def _normalise_level(level: int | str) -> int:
    if isinstance(level, str):
        candidate = level.upper()
        level_number = logging.getLevelName(candidate)
        if isinstance(level_number, str):
            raise ValueError(f"Unknown log level: {level!r}")
        return cast(int, level_number)
    return level


def _stringify(value: Any) -> Any:
    if isinstance(value, (str, int, float, bool)) or value is None:
        return value
    if isinstance(value, (list, tuple)):
        return [_stringify(item) for item in value]
    if isinstance(value, dict):
        return {str(key): _stringify(val) for key, val in value.items()}
    return repr(value)
