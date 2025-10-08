"""Analytics ingestion adapters for Hephaestus quality tooling."""

from __future__ import annotations

from collections.abc import Iterable
from dataclasses import dataclass, field
from enum import Enum
from pathlib import Path
from typing import Any

import yaml
from pydantic import BaseModel, Field


class AnalyticsConfig(BaseModel):
    """Configuration describing structured analytics sources."""

    churn_file: Path | None = Field(default=None, description="Path to churn metrics data")
    coverage_file: Path | None = Field(default=None, description="Path to coverage metrics data")
    embeddings_file: Path | None = Field(
        default=None, description="Path to embeddings or similarity vectors"
    )

    def resolve(self, base: Path) -> AnalyticsConfig:
        """Return a copy with relative paths resolved from ``base``."""

        def _resolve(path: Path | None) -> Path | None:
            if path is None:
                return None
            if path.is_absolute():
                return path
            return (base / path).resolve()

        return self.model_copy(
            update={
                "churn_file": _resolve(self.churn_file),
                "coverage_file": _resolve(self.coverage_file),
                "embeddings_file": _resolve(self.embeddings_file),
            }
        )

    @property
    def is_configured(self) -> bool:
        """Return True when at least one analytics source is configured."""

        return any((self.churn_file, self.coverage_file, self.embeddings_file))


@dataclass(slots=True)
class ModuleSignal:
    """Aggregated analytics signals for a source file or module."""

    path: str
    churn: int = 0
    coverage: float | None = None
    uncovered_lines: int | None = None
    embedding: tuple[float, ...] | None = None
    metadata: dict[str, Any] = field(default_factory=dict)


class AnalyticsLoadError(RuntimeError):
    """Raised when analytics data cannot be parsed."""


class RankingStrategy(str, Enum):
    """Strategies for ranking modules by refactoring priority."""

    RISK_WEIGHTED = "risk_weighted"
    COVERAGE_FIRST = "coverage_first"
    CHURN_BASED = "churn_based"
    COMPOSITE = "composite"


@dataclass(slots=True, frozen=True)
class RankedModule:
    """Module with computed ranking score."""

    path: str
    score: float
    churn: int
    coverage: float | None
    uncovered_lines: int | None
    rank: int
    rationale: str


def load_module_signals(config: AnalyticsConfig | None) -> dict[str, ModuleSignal]:
    """Load analytics signals from the configured data sources."""

    if config is None or not config.is_configured:
        return {}

    signals: dict[str, ModuleSignal] = {}

    if config.churn_file is not None:
        _merge_churn(signals, config.churn_file)
    if config.coverage_file is not None:
        _merge_coverage(signals, config.coverage_file)
    if config.embeddings_file is not None:
        _merge_embeddings(signals, config.embeddings_file)

    return signals


def _merge_churn(target: dict[str, ModuleSignal], path: Path) -> None:
    entries = _load_structured(path)
    for record in _iter_records(entries, required_keys=("path", "churn")):
        churn_value = record["churn"]
        try:
            churn = int(churn_value)
        except (TypeError, ValueError) as exc:  # pragma: no cover - defensive guard
            msg = f"Invalid churn value for {record['path']!r}: {churn_value!r}"
            raise AnalyticsLoadError(msg) from exc

        module = _ensure_signal(target, record["path"])
        module.churn = churn
        metadata = record.get("metadata")
        if isinstance(metadata, dict):
            module.metadata.update(metadata)


def _merge_coverage(target: dict[str, ModuleSignal], path: Path) -> None:
    entries = _load_structured(path)
    for record in _iter_records(entries, required_keys=("path",)):
        module = _ensure_signal(target, record["path"])

        coverage_value = record.get("coverage")
        if coverage_value is not None:
            try:
                coverage = float(coverage_value)
            except (TypeError, ValueError) as exc:  # pragma: no cover - defensive guard
                msg = f"Invalid coverage value for {record['path']!r}: {coverage_value!r}"
                raise AnalyticsLoadError(msg) from exc
            module.coverage = max(0.0, min(1.0, coverage))

        uncovered_value = record.get("uncovered_lines")
        if uncovered_value is not None:
            try:
                module.uncovered_lines = int(uncovered_value)
            except (TypeError, ValueError) as exc:  # pragma: no cover - defensive guard
                msg = f"Invalid uncovered_lines value for {record['path']!r}: {uncovered_value!r}"
                raise AnalyticsLoadError(msg) from exc


def _merge_embeddings(target: dict[str, ModuleSignal], path: Path) -> None:
    entries = _load_structured(path)
    if isinstance(entries, dict):
        iterable: Iterable[dict[str, Any]] = (
            {"path": key, "embedding": value} for key, value in entries.items()
        )
    else:
        iterable = _iter_records(entries, required_keys=("path", "embedding"))

    for record in iterable:
        module = _ensure_signal(target, record["path"])
        vector = record.get("embedding", [])
        if not isinstance(vector, Iterable):
            msg = f"Embedding for {record['path']!r} must be iterable; received {type(vector)!r}"
            raise AnalyticsLoadError(msg)
        embedding = tuple(float(value) for value in vector)
        module.embedding = embedding


def _ensure_signal(target: dict[str, ModuleSignal], path: str) -> ModuleSignal:
    if path not in target:
        target[path] = ModuleSignal(path=path)
    return target[path]


def _load_structured(path: Path) -> Any:
    if not path.exists():
        raise FileNotFoundError(path)
    data = yaml.safe_load(path.read_text(encoding="utf-8"))
    if data is None:
        return []
    return data


def _iter_records(data: Any, *, required_keys: tuple[str, ...]) -> Iterable[dict[str, Any]]:
    if isinstance(data, dict):
        for key, value in data.items():
            if isinstance(value, dict):
                for required in required_keys:
                    if required != "path" and required not in value:
                        msg = f"Missing required key {required!r} in analytics record for {key!r}"
                        raise AnalyticsLoadError(msg)
                yield {"path": key, **value}
            else:
                msg = f"Expected mapping for analytics record {key!r}; received {type(value)!r}"
                raise AnalyticsLoadError(msg)
        return

    if isinstance(data, list | tuple):
        for item in data:
            if not isinstance(item, dict):
                msg = f"Expected mapping entries; received {type(item)!r}"
                raise AnalyticsLoadError(msg)
            for required in required_keys:
                if required not in item:
                    msg = f"Missing required key {required!r} in analytics record"
                    raise AnalyticsLoadError(msg)
            yield item
        return

    msg = f"Unsupported analytics payload type: {type(data)!r}"
    raise AnalyticsLoadError(msg)


def rank_modules(
    signals: dict[str, ModuleSignal],
    *,
    strategy: RankingStrategy = RankingStrategy.RISK_WEIGHTED,
    coverage_threshold: float = 0.75,
    limit: int | None = None,
) -> list[RankedModule]:
    """Rank modules by refactoring priority using the specified strategy.

    Args:
        signals: Module signals loaded from analytics sources
        strategy: Ranking strategy to apply
        coverage_threshold: Target coverage for gap calculations
        limit: Maximum number of ranked modules to return

    Returns:
        List of ranked modules sorted by descending score
    """
    if not signals:
        return []

    ranked: list[tuple[str, float, str]] = []

    for path, signal in signals.items():
        if strategy == RankingStrategy.RISK_WEIGHTED:
            score, rationale = _calculate_risk_weighted_score(signal, coverage_threshold)
        elif strategy == RankingStrategy.COVERAGE_FIRST:
            score, rationale = _calculate_coverage_first_score(signal, coverage_threshold)
        elif strategy == RankingStrategy.CHURN_BASED:
            score, rationale = _calculate_churn_based_score(signal)
        elif strategy == RankingStrategy.COMPOSITE:
            score, rationale = _calculate_composite_score(signal, coverage_threshold)
        else:  # pragma: no cover - defensive guard
            msg = f"Unsupported ranking strategy: {strategy}"
            raise ValueError(msg)

        ranked.append((path, score, rationale))

    ranked.sort(key=lambda item: item[1], reverse=True)

    if limit is not None:
        ranked = ranked[:limit]

    return [
        RankedModule(
            path=path,
            score=round(score, 4),
            churn=signals[path].churn,
            coverage=signals[path].coverage,
            uncovered_lines=signals[path].uncovered_lines,
            rank=idx + 1,
            rationale=rationale,
        )
        for idx, (path, score, rationale) in enumerate(ranked)
    ]


def _calculate_risk_weighted_score(
    signal: ModuleSignal, coverage_threshold: float
) -> tuple[float, str]:
    """Calculate score emphasizing risk factors (coverage gap, churn, uncovered lines)."""
    coverage = signal.coverage if signal.coverage is not None else 0.0
    uncovered = signal.uncovered_lines or 0
    churn = signal.churn

    coverage_gap = max(0.0, coverage_threshold - coverage)
    normalized_uncovered = min(uncovered / 200.0, 1.0)
    normalized_churn = min(churn / 200.0, 1.0)

    score = (coverage_gap * 0.5) + (normalized_uncovered * 0.3) + (normalized_churn * 0.2)

    factors = []
    if coverage_gap > 0:
        factors.append(f"coverage_gap={coverage_gap:.2f}")
    if uncovered > 0:
        factors.append(f"uncovered={uncovered}")
    if churn > 0:
        factors.append(f"churn={churn}")

    rationale = f"Risk-weighted: {', '.join(factors) if factors else 'low_risk'}"
    return score, rationale


def _calculate_coverage_first_score(
    signal: ModuleSignal, coverage_threshold: float
) -> tuple[float, str]:
    """Calculate score prioritizing coverage gaps above all else."""
    coverage = signal.coverage if signal.coverage is not None else 0.0
    uncovered = signal.uncovered_lines or 0

    coverage_gap = max(0.0, coverage_threshold - coverage)
    normalized_uncovered = min(uncovered / 200.0, 1.0)

    score = (coverage_gap * 0.8) + (normalized_uncovered * 0.2)

    rationale = f"Coverage-first: gap={coverage_gap:.2f}, uncovered={uncovered}"
    return score, rationale


def _calculate_churn_based_score(signal: ModuleSignal) -> tuple[float, str]:
    """Calculate score based primarily on change frequency."""
    churn = signal.churn
    coverage = signal.coverage if signal.coverage is not None else 1.0

    normalized_churn = min(churn / 200.0, 1.0)
    coverage_penalty = (1.0 - coverage) * 0.3

    score = normalized_churn + coverage_penalty

    rationale = f"Churn-based: churn={churn}, coverage={coverage:.2f}"
    return score, rationale


def _calculate_composite_score(
    signal: ModuleSignal, coverage_threshold: float
) -> tuple[float, str]:
    """Calculate balanced score considering all factors with embedding boost."""
    coverage = signal.coverage if signal.coverage is not None else 0.0
    uncovered = signal.uncovered_lines or 0
    churn = signal.churn
    has_embedding = signal.embedding is not None

    coverage_gap = max(0.0, coverage_threshold - coverage)
    normalized_uncovered = min(uncovered / 200.0, 1.0)
    normalized_churn = min(churn / 200.0, 1.0)

    base_score = (coverage_gap * 0.35) + (normalized_uncovered * 0.25) + (normalized_churn * 0.25)

    if has_embedding:
        base_score += 0.15

    score = base_score

    factors = [f"coverage_gap={coverage_gap:.2f}", f"uncovered={uncovered}", f"churn={churn}"]
    if has_embedding:
        factors.append("embedding_available")

    rationale = f"Composite: {', '.join(factors)}"
    return score, rationale
