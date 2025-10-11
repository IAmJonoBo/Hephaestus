from __future__ import annotations

from datetime import UTC, datetime

from hephaestus.analytics_streaming import StreamingAnalyticsIngestor


def _ingest_event(payload: dict[str, object]) -> datetime | None:
    ingestor = StreamingAnalyticsIngestor(retention=4)
    assert ingestor.ingest_mapping(payload)
    stored = list(ingestor._events)[0]
    return stored.timestamp


def test_ingest_mapping_parses_z_suffix() -> None:
    timestamp = _ingest_event(
        {
            "source": "ci",
            "kind": "coverage",
            "value": 0.9,
            "timestamp": "2025-01-02T03:04:05Z",
        }
    )

    assert timestamp == datetime(2025, 1, 2, 3, 4, 5, tzinfo=UTC)


def test_ingest_mapping_parses_utc_suffix() -> None:
    timestamp = _ingest_event(
        {
            "source": "ci",
            "kind": "latency",
            "value": 123.0,
            "timestamp": "2025-01-02T03:04:05 UTC",
        }
    )

    assert timestamp == datetime(2025, 1, 2, 3, 4, 5, tzinfo=UTC)


def test_ingest_mapping_parses_four_digit_offsets() -> None:
    timestamp = _ingest_event(
        {
            "source": "ci",
            "kind": "latency",
            "value": 123.0,
            "timestamp": "2025-01-02T03:04:05+0000",
        }
    )

    assert timestamp == datetime(2025, 1, 2, 3, 4, 5, tzinfo=UTC)


def test_ingest_mapping_accepts_naive_datetimes() -> None:
    timestamp = _ingest_event(
        {
            "source": "ci",
            "kind": "latency",
            "value": 123.0,
            "timestamp": "2025-01-02T03:04:05",
        }
    )

    assert timestamp == datetime(2025, 1, 2, 3, 4, 5)
