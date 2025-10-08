"""Tests for analytics ingestion helpers."""

from __future__ import annotations

from pathlib import Path

import pytest
import yaml

from hephaestus.analytics import (
    AnalyticsConfig,
    AnalyticsLoadError,
    load_module_signals,
)


def test_load_module_signals_merges_sources(tmp_path: Path) -> None:
    churn_path = tmp_path / "churn.yaml"
    coverage_path = tmp_path / "coverage.yaml"
    embeddings_path = tmp_path / "embeddings.yaml"

    churn_path.write_text(
        yaml.safe_dump(
            [
                {"path": "repo-a/mod.py", "churn": 75, "metadata": {"owner": "payments"}},
                {"path": "repo-b/mod.py", "churn": 15},
            ]
        ),
        encoding="utf-8",
    )
    coverage_path.write_text(
        yaml.safe_dump(
            {
                "repo-a/mod.py": {"coverage": 0.61, "uncovered_lines": 44},
                "repo-b/mod.py": {"coverage": 0.93, "uncovered_lines": 6},
            }
        ),
        encoding="utf-8",
    )
    embeddings_path.write_text(
        yaml.safe_dump(
            {
                "repo-a/mod.py": [0.1, 0.2, 0.3],
            }
        ),
        encoding="utf-8",
    )

    config = AnalyticsConfig(
        churn_file=churn_path,
        coverage_file=coverage_path,
        embeddings_file=embeddings_path,
    )

    signals = load_module_signals(config)

    assert set(signals) == {"repo-a/mod.py", "repo-b/mod.py"}
    module = signals["repo-a/mod.py"]
    assert module.churn == 75
    assert module.coverage == pytest.approx(0.61)
    assert module.uncovered_lines == 44
    assert module.embedding == (0.1, 0.2, 0.3)
    assert module.metadata["owner"] == "payments"


def test_load_module_signals_missing_file_raises(tmp_path: Path) -> None:
    missing = tmp_path / "absent.yaml"
    config = AnalyticsConfig(churn_file=missing)

    with pytest.raises(FileNotFoundError):
        load_module_signals(config)


def test_iter_records_rejects_invalid_payload(tmp_path: Path) -> None:
    churn_path = tmp_path / "churn.yaml"
    churn_path.write_text(yaml.safe_dump(["not-a-dict"]), encoding="utf-8")
    config = AnalyticsConfig(churn_file=churn_path)

    with pytest.raises(AnalyticsLoadError):
        load_module_signals(config)


def test_analytics_config_resolve_relative_paths(tmp_path: Path) -> None:
    churn_rel = Path("metrics/churn.yaml")
    metrics_dir = tmp_path / "metrics"
    metrics_dir.mkdir()
    (metrics_dir / "churn.yaml").write_text(yaml.safe_dump([]), encoding="utf-8")

    config = AnalyticsConfig(churn_file=churn_rel)
    resolved = config.resolve(tmp_path)

    assert resolved.churn_file == metrics_dir / "churn.yaml"


def test_load_module_signals_rejects_non_iterable_embedding(tmp_path: Path) -> None:
    embeddings_path = tmp_path / "embeddings.yaml"
    embeddings_path.write_text(
        yaml.safe_dump({"repo-a/mod.py": 5}),
        encoding="utf-8",
    )
    config = AnalyticsConfig(embeddings_file=embeddings_path)

    with pytest.raises(AnalyticsLoadError):
        load_module_signals(config)


def test_load_module_signals_with_no_config_returns_empty() -> None:
    assert load_module_signals(None) == {}
