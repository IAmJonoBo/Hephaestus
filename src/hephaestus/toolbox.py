"""Core quality, coverage, and refactor helpers for the Hephaestus toolkit."""

from __future__ import annotations

from collections.abc import Iterable
from dataclasses import dataclass
from pathlib import Path

import yaml
from pydantic import BaseModel, Field

from hephaestus.analytics import AnalyticsConfig, ModuleSignal, load_module_signals

_DEFAULT_CONFIG = Path("hephaestus-toolkit/refactoring/config/refactor.config.yaml")


class ToolkitSettings(BaseModel):
    """Runtime configuration for the toolkit."""

    coverage_threshold: float = Field(default=0.75, ge=0.0, le=1.0)
    hotspot_limit: int = Field(default=10, ge=1)
    repositories: list[str] = Field(default_factory=list)
    qa_profiles: dict[str, dict[str, float | int | str]] = Field(default_factory=dict)
    analytics: AnalyticsConfig | None = Field(
        default=None, description="Optional analytics ingestion sources"
    )


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

    settings = ToolkitSettings.model_validate(raw)
    if settings.analytics is not None:
        settings = settings.model_copy(
            update={"analytics": settings.analytics.resolve(target.parent)}
        )
    return settings


def analyze_hotspots(settings: ToolkitSettings, *, limit: int | None = None) -> list[Hotspot]:
    """Return a ranked list of hotspots using mock analytics.

    In the real system this would join churn analytics with coverage data and detection
    signals from the refactor scanners. Here we emit synthetic but deterministic data so
    the CLI remains functional inside the standalone toolkit.
    """

    limit = limit or settings.hotspot_limit
    signals = _load_signals(settings)

    if signals:
        ranked = sorted(
            signals,
            key=lambda signal: (signal.churn, signal.coverage or 0.0),
            reverse=True,
        )
        return [
            Hotspot(
                path=signal.path,
                churn=signal.churn,
                coverage=round(signal.coverage or 0.0, 2),
            )
            for signal in ranked[:limit]
        ]

    repositories: Iterable[str] = settings.repositories or ["monolith", "services/api"]
    hotspots: list[Hotspot] = []
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


def find_coverage_gaps(settings: ToolkitSettings) -> list[CoverageGap]:
    """Surface coverage gaps based on configured thresholds."""

    signals = _load_signals(settings)
    target = settings.coverage_threshold

    if signals:
        gaps: list[CoverageGap] = []
        for signal in signals:
            uncovered = signal.uncovered_lines or 0
            coverage = signal.coverage if signal.coverage is not None else 0.0
            if uncovered <= 0 and coverage >= target:
                continue
            risk = _calculate_risk(signal, target)
            gaps.append(
                CoverageGap(
                    module=signal.path,
                    uncovered_lines=uncovered,
                    risk_score=risk,
                )
            )
        gaps.sort(key=lambda gap: (gap.uncovered_lines, gap.risk_score), reverse=True)
        return gaps or [
            CoverageGap(
                module="unknown", uncovered_lines=0, risk_score=_calculate_risk(None, target)
            )
        ]

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


def enumerate_refactor_opportunities(
    settings: ToolkitSettings,
) -> list[RefactorOpportunity]:
    """Return a set of advisory refactor opportunities."""

    signals = _load_signals(settings)
    if signals:
        opportunities: list[RefactorOpportunity] = []
        for signal in sorted(
            signals,
            key=lambda value: (
                max(0.0, settings.coverage_threshold - (value.coverage or 0.0)),
                value.uncovered_lines or 0,
                value.churn,
            ),
            reverse=True,
        ):
            uncovered = signal.uncovered_lines or 0
            coverage_gap = max(0.0, settings.coverage_threshold - (signal.coverage or 0.0))
            if uncovered <= 0 and coverage_gap <= 0:
                continue
            effort = _estimate_effort(signal, coverage_gap)
            summary = _build_summary(signal, uncovered, coverage_gap)
            identifier = signal.path.replace("/", "-").replace(".", "-") + "-stabilise"
            opportunities.append(
                RefactorOpportunity(
                    identifier=identifier,
                    summary=summary,
                    estimated_effort=effort,
                )
            )
        if opportunities:
            return opportunities

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


def _load_signals(settings: ToolkitSettings) -> list[ModuleSignal]:
    if settings.analytics is None:
        return []
    signals = load_module_signals(settings.analytics)
    if not signals:
        return []
    repositories = settings.repositories
    if repositories:
        prefixes = tuple(f"{repo.rstrip('/')}/" for repo in repositories)
        filtered = [
            signal
            for signal in signals.values()
            if signal.path.startswith(prefixes) or signal.path in repositories
        ]
        if filtered:
            return filtered
    return list(signals.values())


def _calculate_risk(signal: ModuleSignal | None, coverage_target: float) -> float:
    if signal is None:
        return round(max(0.5, min(0.95, 1.0 - (coverage_target - 0.6))), 2)

    uncovered = signal.uncovered_lines or 0
    coverage = signal.coverage if signal.coverage is not None else 0.0
    churn = signal.churn

    coverage_gap = max(0.0, coverage_target - coverage)
    base = 0.4
    score = (
        base
        + (coverage_gap * 0.35)
        + (min(uncovered, 200) / 200 * 0.2)
        + (min(churn, 200) / 200 * 0.15)
    )
    return round(min(0.99, max(0.5, score)), 2)


def _estimate_effort(signal: ModuleSignal, coverage_gap: float) -> str:
    uncovered = signal.uncovered_lines or 0
    churn = signal.churn

    if uncovered >= 80 or churn >= 120:
        return "high"
    if uncovered >= 40 or churn >= 60:
        return "medium"
    if coverage_gap < 0.5 and uncovered < 20:
        return "low"
    return "medium"


def _build_summary(signal: ModuleSignal, uncovered: int, coverage_gap: float) -> str:
    coverage_display = f"{signal.coverage:.2f}" if signal.coverage is not None else "unknown"
    parts = [
        f"Stabilise {signal.path}",
        f"coverage={coverage_display}",
        f"churn={signal.churn}",
    ]
    if uncovered:
        parts.append(f"uncovered={uncovered}")
    if coverage_gap > 0:
        parts.append(f"gap={coverage_gap:.2f}")
    if signal.embedding is not None:
        parts.append("embedding-vector")
    return ", ".join(parts)
