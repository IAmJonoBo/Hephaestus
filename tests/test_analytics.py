"""Tests for analytics ingestion helpers."""

from __future__ import annotations

from pathlib import Path

import pytest
import yaml

from hephaestus.analytics import (
    AnalyticsConfig,
    AnalyticsLoadError,
    RankingStrategy,
    load_module_signals,
    rank_modules,
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


def test_rank_modules_risk_weighted_strategy(tmp_path: Path) -> None:
    """Test risk-weighted ranking prioritizes high-risk modules."""
    churn_path = tmp_path / "churn.yaml"
    coverage_path = tmp_path / "coverage.yaml"

    churn_path.write_text(
        yaml.safe_dump(
            [
                {"path": "high_risk.py", "churn": 120},
                {"path": "medium_risk.py", "churn": 50},
                {"path": "low_risk.py", "churn": 10},
            ]
        ),
        encoding="utf-8",
    )
    coverage_path.write_text(
        yaml.safe_dump(
            {
                "high_risk.py": {"coverage": 0.50, "uncovered_lines": 80},
                "medium_risk.py": {"coverage": 0.70, "uncovered_lines": 30},
                "low_risk.py": {"coverage": 0.90, "uncovered_lines": 5},
            }
        ),
        encoding="utf-8",
    )

    config = AnalyticsConfig(churn_file=churn_path, coverage_file=coverage_path)
    signals = load_module_signals(config)

    ranked = rank_modules(signals, strategy=RankingStrategy.RISK_WEIGHTED, coverage_threshold=0.75)

    assert len(ranked) == 3
    assert ranked[0].path == "high_risk.py"
    assert ranked[0].rank == 1
    assert ranked[0].score > ranked[1].score
    assert ranked[1].path == "medium_risk.py"
    assert ranked[2].path == "low_risk.py"


def test_rank_modules_coverage_first_strategy(tmp_path: Path) -> None:
    """Test coverage-first strategy prioritizes coverage gaps."""
    churn_path = tmp_path / "churn.yaml"
    coverage_path = tmp_path / "coverage.yaml"

    churn_path.write_text(
        yaml.safe_dump(
            [
                {"path": "low_coverage.py", "churn": 5},
                {"path": "high_churn.py", "churn": 200},
            ]
        ),
        encoding="utf-8",
    )
    coverage_path.write_text(
        yaml.safe_dump(
            {
                "low_coverage.py": {"coverage": 0.40, "uncovered_lines": 100},
                "high_churn.py": {"coverage": 0.95, "uncovered_lines": 2},
            }
        ),
        encoding="utf-8",
    )

    config = AnalyticsConfig(churn_file=churn_path, coverage_file=coverage_path)
    signals = load_module_signals(config)

    ranked = rank_modules(signals, strategy=RankingStrategy.COVERAGE_FIRST, coverage_threshold=0.75)

    assert ranked[0].path == "low_coverage.py"
    assert "Coverage-first" in ranked[0].rationale


def test_rank_modules_churn_based_strategy(tmp_path: Path) -> None:
    """Test churn-based strategy prioritizes high-churn modules."""
    churn_path = tmp_path / "churn.yaml"
    coverage_path = tmp_path / "coverage.yaml"

    churn_path.write_text(
        yaml.safe_dump(
            [
                {"path": "high_churn.py", "churn": 180},
                {"path": "low_churn.py", "churn": 20},
            ]
        ),
        encoding="utf-8",
    )
    coverage_path.write_text(
        yaml.safe_dump(
            {
                "high_churn.py": {"coverage": 0.90},
                "low_churn.py": {"coverage": 0.50},
            }
        ),
        encoding="utf-8",
    )

    config = AnalyticsConfig(churn_file=churn_path, coverage_file=coverage_path)
    signals = load_module_signals(config)

    ranked = rank_modules(signals, strategy=RankingStrategy.CHURN_BASED)

    assert ranked[0].path == "high_churn.py"
    assert "Churn-based" in ranked[0].rationale


def test_rank_modules_composite_strategy_with_embeddings(tmp_path: Path) -> None:
    """Test composite strategy gives bonus for embedding availability."""
    churn_path = tmp_path / "churn.yaml"
    coverage_path = tmp_path / "coverage.yaml"
    embeddings_path = tmp_path / "embeddings.yaml"

    churn_path.write_text(
        yaml.safe_dump(
            [
                {"path": "with_embedding.py", "churn": 50},
                {"path": "without_embedding.py", "churn": 50},
            ]
        ),
        encoding="utf-8",
    )
    coverage_path.write_text(
        yaml.safe_dump(
            {
                "with_embedding.py": {"coverage": 0.60, "uncovered_lines": 40},
                "without_embedding.py": {"coverage": 0.60, "uncovered_lines": 40},
            }
        ),
        encoding="utf-8",
    )
    embeddings_path.write_text(
        yaml.safe_dump({"with_embedding.py": [0.1, 0.2, 0.3]}),
        encoding="utf-8",
    )

    config = AnalyticsConfig(
        churn_file=churn_path, coverage_file=coverage_path, embeddings_file=embeddings_path
    )
    signals = load_module_signals(config)

    ranked = rank_modules(signals, strategy=RankingStrategy.COMPOSITE, coverage_threshold=0.75)

    assert ranked[0].path == "with_embedding.py"
    assert "embedding_available" in ranked[0].rationale
    assert ranked[0].score > ranked[1].score


def test_rank_modules_with_limit(tmp_path: Path) -> None:
    """Test limit parameter restricts number of results."""
    churn_path = tmp_path / "churn.yaml"
    churn_path.write_text(
        yaml.safe_dump([{"path": f"module_{i}.py", "churn": 100 - i * 10} for i in range(10)]),
        encoding="utf-8",
    )

    config = AnalyticsConfig(churn_file=churn_path)
    signals = load_module_signals(config)

    ranked = rank_modules(signals, strategy=RankingStrategy.CHURN_BASED, limit=5)

    assert len(ranked) == 5
    assert ranked[0].rank == 1
    assert ranked[4].rank == 5


def test_rank_modules_empty_signals_returns_empty() -> None:
    """Test ranking with no signals returns empty list."""
    ranked = rank_modules({}, strategy=RankingStrategy.RISK_WEIGHTED)
    assert ranked == []
