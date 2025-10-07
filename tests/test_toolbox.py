"""Unit tests for toolbox helpers."""

from __future__ import annotations

import json
from pathlib import Path

import pytest

from hephaestus import toolbox


@pytest.fixture()
def sample_settings(tmp_path: Path) -> toolbox.ToolkitSettings:
    config = {
        "coverage_threshold": 0.8,
        "hotspot_limit": 5,
        "repositories": ["repo-a", "repo-b"],
        "qa_profiles": {"smoke": {"coverage_goal": 0.6, "requires_ci": False}},
    }
    config_path = tmp_path / "config.yaml"
    config_path.write_text(json.dumps(config), encoding="utf-8")

    return toolbox.load_settings(config_path)


def test_load_settings_missing_file_raises(tmp_path: Path) -> None:
    missing_path = tmp_path / "absent.yaml"
    with pytest.raises(FileNotFoundError):
        toolbox.load_settings(missing_path)


def test_analyze_hotspots_respects_limit(sample_settings: toolbox.ToolkitSettings) -> None:
    results = toolbox.analyze_hotspots(sample_settings, limit=4)

    assert len(results) == 4
    assert results[0].churn >= results[-1].churn
    assert results[0].path.startswith("repo-b")


def test_find_coverage_gaps_uses_threshold(sample_settings: toolbox.ToolkitSettings) -> None:
    gaps = toolbox.find_coverage_gaps(sample_settings)

    assert all(gap.uncovered_lines > 0 for gap in gaps)
    assert any(gap.risk_score >= 0.6 for gap in gaps)


def test_enumerate_refactor_opportunities_uses_repositories(
    sample_settings: toolbox.ToolkitSettings,
) -> None:
    opportunities = toolbox.enumerate_refactor_opportunities(sample_settings)

    assert opportunities[0].identifier.startswith("repo-a")
    assert any("strangler" in item.summary for item in opportunities)


def test_qa_profile_summary_returns_profile_data(
    sample_settings: toolbox.ToolkitSettings,
) -> None:
    profile = toolbox.qa_profile_summary(sample_settings, "smoke")

    assert profile["coverage_goal"] == pytest.approx(0.6)
    assert bool(profile["requires_ci"]) is False


def test_qa_profile_summary_unknown_profile_raises(
    sample_settings: toolbox.ToolkitSettings,
) -> None:
    with pytest.raises(KeyError):
        toolbox.qa_profile_summary(sample_settings, "missing")
