"""Unit tests for toolbox helpers."""

from __future__ import annotations

from pathlib import Path
from typing import TYPE_CHECKING

import pytest
import yaml

from hephaestus import toolbox

if TYPE_CHECKING:
    from hephaestus.toolbox import ToolkitSettings


@pytest.fixture()
def sample_settings(tmp_path: Path) -> ToolkitSettings:
    config = {
        "coverage_threshold": 0.8,
        "hotspot_limit": 5,
        "repositories": ["repo-a", "repo-b"],
        "qa_profiles": {"smoke": {"coverage_goal": 0.6, "requires_ci": False}},
    }
    config_path = tmp_path / "config.yaml"
    config_path.write_text(yaml.safe_dump(config), encoding="utf-8")

    return toolbox.load_settings(config_path)  # type: ignore[no-any-return]


@pytest.fixture()
def analytics_settings(tmp_path: Path) -> ToolkitSettings:
    churn = [
        {"path": "repo-a/module_alpha.py", "churn": 140},
        {"path": "repo-a/module_beta.py", "churn": 95},
        {"path": "repo-b/module_delta.py", "churn": 30},
    ]
    coverage = {
        "repo-a/module_alpha.py": {"coverage": 0.55, "uncovered_lines": 68},
        "repo-a/module_beta.py": {"coverage": 0.42, "uncovered_lines": 91},
        "repo-b/module_delta.py": {"coverage": 0.92, "uncovered_lines": 3},
    }
    embeddings = {
        "repo-a/module_alpha.py": [0.1, 0.2, 0.3],
        "repo-a/module_beta.py": [0.6, 0.1, 0.1],
    }

    churn_path = tmp_path / "churn.yaml"
    coverage_path = tmp_path / "coverage.yaml"
    embeddings_path = tmp_path / "embeddings.yaml"

    churn_path.write_text(yaml.safe_dump(churn), encoding="utf-8")
    coverage_path.write_text(yaml.safe_dump(coverage), encoding="utf-8")
    embeddings_path.write_text(yaml.safe_dump(embeddings), encoding="utf-8")

    config = {
        "coverage_threshold": 0.8,
        "hotspot_limit": 5,
        "repositories": ["repo-a", "repo-b"],
        "qa_profiles": {"smoke": {"coverage_goal": 0.6, "requires_ci": False}},
        "analytics": {
            "churn_file": str(churn_path),
            "coverage_file": str(coverage_path),
            "embeddings_file": str(embeddings_path),
        },
    }

    config_path = tmp_path / "config.yaml"
    config_path.write_text(yaml.safe_dump(config), encoding="utf-8")

    return toolbox.load_settings(config_path)  # type: ignore[no-any-return]


def test_load_settings_missing_file_raises(tmp_path: Path) -> None:
    missing_path = tmp_path / "absent.yaml"
    with pytest.raises(FileNotFoundError):
        toolbox.load_settings(missing_path)


def test_analyze_hotspots_respects_limit(sample_settings: ToolkitSettings) -> None:
    results = toolbox.analyze_hotspots(sample_settings, limit=4)

    assert len(results) == 4
    assert results[0].churn >= results[-1].churn
    assert results[0].path.startswith("repo-b")


def test_analyze_hotspots_uses_ingested_signals(
    analytics_settings: ToolkitSettings,
) -> None:
    results = toolbox.analyze_hotspots(analytics_settings)

    assert [item.path for item in results][:2] == [
        "repo-a/module_alpha.py",
        "repo-a/module_beta.py",
    ]
    assert results[0].coverage == pytest.approx(0.55, rel=1e-2)


def test_find_coverage_gaps_uses_threshold(sample_settings: ToolkitSettings) -> None:
    gaps = toolbox.find_coverage_gaps(sample_settings)

    assert all(gap.uncovered_lines > 0 for gap in gaps)
    assert any(gap.risk_score >= 0.6 for gap in gaps)


def test_find_coverage_gaps_prefers_ingested_metrics(
    analytics_settings: ToolkitSettings,
) -> None:
    gaps = toolbox.find_coverage_gaps(analytics_settings)

    assert gaps[0].module == "repo-a/module_beta.py"
    assert gaps[0].uncovered_lines == 91
    assert gaps[0].risk_score >= gaps[1].risk_score


def test_enumerate_refactor_opportunities_uses_repositories(
    sample_settings: ToolkitSettings,
) -> None:
    opportunities = toolbox.enumerate_refactor_opportunities(sample_settings)

    assert opportunities[0].identifier.startswith("repo-a")
    assert any("strangler" in item.summary for item in opportunities)


def test_enumerate_refactor_opportunities_surface_ingested_gaps(
    analytics_settings: ToolkitSettings,
) -> None:
    opportunities = toolbox.enumerate_refactor_opportunities(analytics_settings)

    assert opportunities[0].identifier.startswith("repo-a-module_beta")
    assert "uncovered" in opportunities[0].summary
    assert opportunities[0].estimated_effort in {"medium", "high"}


def test_qa_profile_summary_returns_profile_data(
    sample_settings: ToolkitSettings,
) -> None:
    profile = toolbox.qa_profile_summary(sample_settings, "smoke")

    assert profile["coverage_goal"] == pytest.approx(0.6)
    assert bool(profile["requires_ci"]) is False


def test_qa_profile_summary_unknown_profile_raises(
    sample_settings: ToolkitSettings,
) -> None:
    with pytest.raises(KeyError):
        toolbox.qa_profile_summary(sample_settings, "missing")
