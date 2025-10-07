"""Core quality, coverage, and refactor helpers for the Hephaestus toolkit."""
from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
from typing import Iterable, List

import yaml
from pydantic import BaseModel, Field


_DEFAULT_CONFIG = Path("hephaestus-toolkit/refactoring/config/refactor.config.yaml")


class ToolkitSettings(BaseModel):
    """Runtime configuration for the toolkit."""

    coverage_threshold: float = Field(default=0.75, ge=0.0, le=1.0)
    hotspot_limit: int = Field(default=10, ge=1)
    repositories: List[str] = Field(default_factory=list)
    qa_profiles: dict[str, dict[str, float | int | str]] = Field(default_factory=dict)


@dataclass(slots=True, frozen=True)
class Hotspot:
    """Representation of a code hotspot."""

    path: str
    churn: int
    coverage: float


@dataclass(slots=True, frozen=True)
class CoverageGap:
    """Coverage gap surfaced by analytics."""

    module: str
    uncovered_lines: int
    risk_score: float


@dataclass(slots=True, frozen=True)
class RefactorOpportunity:
    """Evidence-based refactor suggestion."""

    identifier: str
    summary: str
    estimated_effort: str


def load_settings(path: str | Path | None = None) -> ToolkitSettings:
    """Read configuration from disk, falling back to the default toolkit file."""

    target = Path(path) if path else _DEFAULT_CONFIG
    if not target.exists():
        raise FileNotFoundError(f"Configuration file not found: {target}")

    with target.open("r", encoding="utf-8") as handle:
        raw = yaml.safe_load(handle) or {}

    return ToolkitSettings.model_validate(raw)


def analyze_hotspots(settings: ToolkitSettings, *, limit: int | None = None) -> List[Hotspot]:
    """Return a ranked list of hotspots using mock analytics.

    In the real system this would join churn analytics with coverage data and detection
    signals from the refactor scanners. Here we emit synthetic but deterministic data so
    the CLI remains functional inside the standalone toolkit.
    """

    limit = limit or settings.hotspot_limit
    repositories: Iterable[str] = settings.repositories or ["monolith", "services/api"]

    hotspots: List[Hotspot] = []
    churn_seed = 17
    for repo in repositories:
        for index in range(1, 4):
            churn = churn_seed + index * 3
            coverage = max(0.0, 1.0 - (index * 0.12))
            hotspots.append(
                Hotspot(
                    path=f"{repo}/module_{index}.py",
                    churn=churn,
                    coverage=round(coverage, 2),
                )
            )
        churn_seed += 11

    return sorted(hotspots, key=lambda item: item.churn, reverse=True)[:limit]


def find_coverage_gaps(settings: ToolkitSettings) -> List[CoverageGap]:
    """Surface coverage gaps based on configured thresholds."""

    target = settings.coverage_threshold
    base_score = max(0.5, min(0.95, 1.0 - (target - 0.6)))

    return [
        CoverageGap(
            module="services/api/payments.py",
            uncovered_lines=42,
            risk_score=round(base_score + 0.07, 2),
        ),
        CoverageGap(
            module="monolith/order_flow.py",
            uncovered_lines=27,
            risk_score=round(base_score, 2),
        ),
    ]


def enumerate_refactor_opportunities(settings: ToolkitSettings) -> List[RefactorOpportunity]:
    """Return a set of advisory refactor opportunities."""

    repositories = settings.repositories or ["monolith"]
    primary = repositories[0]

    return [
        RefactorOpportunity(
            identifier=f"{primary}-payments-saga-split",
            summary=f"Break the legacy payments saga in {primary} into domain-oriented modules",
            estimated_effort="medium",
        ),
        RefactorOpportunity(
            identifier="notifications-strangler",
            summary="Adopt strangler fig wrapper for notifications API",
            estimated_effort="high",
        ),
    ]


def qa_profile_summary(settings: ToolkitSettings, profile: str) -> dict[str, float | int | str]:
    """Return configuration metadata for a QA profile defined in settings."""

    profiles = settings.qa_profiles or {
        "quick": {"coverage_goal": 0.7, "requires_ci": False},
        "full": {"coverage_goal": 0.9, "requires_ci": True},
    }
    if profile not in profiles:
        raise KeyError(f"Unknown QA profile: {profile}")
    return profiles[profile]
