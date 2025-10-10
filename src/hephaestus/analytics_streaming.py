"""Streaming analytics ingestion utilities for REST and gRPC services."""

from __future__ import annotations

import threading
from collections import Counter, deque
from collections.abc import Mapping
from dataclasses import dataclass, field
from datetime import datetime
from typing import Any


@dataclass(slots=True)
class AnalyticsEvent:
    """Structured analytics event ingested from remote clients."""

    source: str
    kind: str
    value: float | None = None
    unit: str | None = None
    metrics: dict[str, float] = field(default_factory=dict)
    metadata: dict[str, Any] = field(default_factory=dict)
    timestamp: datetime | None = None


@dataclass(slots=True)
class IngestSnapshot:
    """Read-only snapshot of the ingestion buffer."""

    total_events: int
    accepted: int
    rejected: int
    kinds: dict[str, int]
    sources: dict[str, int]


class StreamingAnalyticsIngestor:
    """Thread-safe analytics ingestor with bounded retention."""

    def __init__(self, *, retention: int = 2048) -> None:
        self._events: deque[AnalyticsEvent] = deque(maxlen=retention)
        self._accepted = 0
        self._rejected = 0
        self._kinds: Counter[str] = Counter()
        self._sources: Counter[str] = Counter()
        self._lock = threading.Lock()

    def ingest_mapping(self, payload: Mapping[str, Any]) -> bool:
        """Ingest a mapping payload, returning ``True`` on success."""

        try:
            source = str(payload["source"]).strip()
            kind = str(payload["kind"]).strip()
        except KeyError:
            self.mark_rejected()
            return False

        if not source or not kind:
            self.mark_rejected()
            return False

        value_raw = payload.get("value")
        value = None
        if value_raw is not None:
            try:
                value = float(value_raw)
            except (TypeError, ValueError):
                self.mark_rejected()
                return False

        metrics: dict[str, float] = {}
        maybe_metrics = payload.get("metrics", {})
        if isinstance(maybe_metrics, Mapping):
            for key, metric_value in maybe_metrics.items():
                try:
                    metrics[str(key)] = float(metric_value)
                except (TypeError, ValueError):
                    continue

        metadata: dict[str, Any] = {}
        maybe_metadata = payload.get("metadata")
        if isinstance(maybe_metadata, Mapping):
            metadata = {str(key): value for key, value in maybe_metadata.items()}

        timestamp = None
        raw_timestamp = payload.get("timestamp")
        if isinstance(raw_timestamp, str) and raw_timestamp:
            try:
                timestamp = datetime.fromisoformat(raw_timestamp)
            except ValueError:
                timestamp = None

        event = AnalyticsEvent(
            source=source,
            kind=kind,
            value=value,
            unit=str(payload.get("unit")) if payload.get("unit") else None,
            metrics=metrics,
            metadata=metadata,
            timestamp=timestamp,
        )

        self._store_event(event)
        return True

    def _store_event(self, event: AnalyticsEvent) -> None:
        with self._lock:
            self._events.append(event)
            self._accepted += 1
            self._kinds[event.kind] += 1
            self._sources[event.source] += 1

    def mark_rejected(self) -> None:
        with self._lock:
            self._rejected += 1

    def snapshot(self) -> IngestSnapshot:
        """Return a snapshot of ingestion statistics."""

        with self._lock:
            return IngestSnapshot(
                total_events=len(self._events),
                accepted=self._accepted,
                rejected=self._rejected,
                kinds=dict(self._kinds),
                sources=dict(self._sources),
            )

    def reset(self) -> None:
        """Reset ingestion statistics (primarily for tests)."""

        with self._lock:
            self._events.clear()
            self._accepted = 0
            self._rejected = 0
            self._kinds.clear()
            self._sources.clear()


# Shared ingestor for REST and gRPC surfaces.
global_ingestor = StreamingAnalyticsIngestor()

__all__ = [
    "AnalyticsEvent",
    "IngestSnapshot",
    "StreamingAnalyticsIngestor",
    "global_ingestor",
]
