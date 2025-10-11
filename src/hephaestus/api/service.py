"""Shared service helpers for REST and gRPC front-ends.

These helpers wrap the core toolkit primitives so the HTTP and gRPC
implementations can share a consistent, well-tested execution path for
guard-rails, cleanup, analytics, and drift remediation.
"""

from __future__ import annotations

import asyncio
import shutil
import time
from collections.abc import Iterable
from dataclasses import dataclass
from pathlib import Path
from typing import Any

from hephaestus import drift as drift_module
from hephaestus import toolbox
from hephaestus.analytics import RankingStrategy, load_module_signals, rank_modules
from hephaestus.api import auth
from hephaestus.cleanup import CleanupOptions, run_cleanup
from hephaestus.plugins import PluginRegistry, discover_plugins


@dataclass(slots=True, frozen=True)
class GuardRailGate:
    """Summary of a single guard-rails quality gate."""

    name: str
    passed: bool
    message: str
    duration: float
    metadata: dict[str, Any]


@dataclass(slots=True, frozen=True)
class GuardRailExecution:
    """Aggregated guard-rails execution result."""

    success: bool
    duration: float
    gates: list[GuardRailGate]
    remediation_commands: list[str]
    remediation_results: list[drift_module.RemediationResult]


def _size_estimate(paths: Iterable[Path]) -> int:
    """Return a conservative byte estimate for the provided paths."""

    total = 0
    for candidate in paths:
        try:
            if candidate.is_file():
                total += candidate.stat().st_size
        except OSError:
            continue
    return total


def run_cleanup_summary(
    *,
    principal: auth.AuthenticatedPrincipal,
    root: str | None,
    deep_clean: bool,
    dry_run: bool,
) -> dict[str, Any]:
    """Execute the cleanup routine and return a serialisable summary."""

    auth.ServiceAccountVerifier.require_role(principal, auth.Role.CLEANUP.value)

    options = CleanupOptions(
        root=Path(root).resolve() if root else None,
        deep_clean=deep_clean,
        dry_run=dry_run,
    )

    result = run_cleanup(options)

    file_count = len(result.removed_paths) if not dry_run else len(result.preview_paths)
    size_freed = _size_estimate(result.removed_paths if not dry_run else result.preview_paths)

    manifest: dict[str, Any] = {
        "search_roots": len(result.search_roots),
        "preview_count": len(result.preview_paths),
        "removed_count": len(result.removed_paths),
        "skipped": len(result.skipped_roots),
        "errors": len(result.errors),
    }

    if result.audit_manifest is not None:
        manifest["audit_manifest"] = str(result.audit_manifest)

    return {
        "files": file_count,
        "bytes": size_freed,
        "manifest": manifest,
        "preview_paths": [str(path) for path in result.preview_paths[:10]],
        "removed_paths": [str(path) for path in result.removed_paths[:10]],
    }


def _evaluate_cleanup_gate(
    principal: auth.AuthenticatedPrincipal, workspace: Path, *, dry_run: bool
) -> GuardRailGate:
    start = time.perf_counter()
    summary = run_cleanup_summary(
        principal=principal,
        root=str(workspace),
        deep_clean=True,
        dry_run=dry_run,
    )
    duration = time.perf_counter() - start
    return GuardRailGate(
        name="cleanup",
        passed=True,
        message="Workspace sweep analysed",
        duration=duration,
        metadata={
            "files": str(summary["files"]),
            "bytes": str(summary["bytes"]),
            "dry_run": str(dry_run).lower(),
        },
    )


def _evaluate_plugin_gates(registry: PluginRegistry, *, no_format: bool) -> list[GuardRailGate]:
    gates: list[GuardRailGate] = []
    for plugin in registry.all_plugins():
        start = time.perf_counter()
        metadata = plugin.metadata

        if no_format and metadata.name == "ruff-format":
            gates.append(
                GuardRailGate(
                    name=metadata.name,
                    passed=True,
                    message="Skipped due to no-format flag",
                    duration=time.perf_counter() - start,
                    metadata={"skipped": "true"},
                )
            )
            continue

        required_tools: list[str] = []
        missing_tools: list[str] = []
        for requirement in metadata.requires:
            tool = requirement.split(">=")[0].split("[")[0]
            required_tools.append(tool)
            if shutil.which(tool) is None:
                missing_tools.append(tool)

        duration = time.perf_counter() - start
        gates.append(
            GuardRailGate(
                name=metadata.name,
                passed=not missing_tools,
                message=(
                    "All required tooling available"
                    if not missing_tools
                    else f"Missing tooling: {', '.join(missing_tools)}"
                ),
                duration=duration,
                metadata={
                    "requires": ",".join(required_tools),
                    "missing": ",".join(missing_tools),
                },
            )
        )

    return gates


def _evaluate_drift_gate(workspace: Path) -> tuple[GuardRailGate, list[drift_module.ToolVersion]]:
    start = time.perf_counter()
    try:
        versions = drift_module.detect_drift(project_root=workspace)
    except drift_module.DriftDetectionError as exc:  # pragma: no cover - defensive guard
        gate = GuardRailGate(
            name="drift-detection",
            passed=False,
            message=str(exc),
            duration=time.perf_counter() - start,
            metadata={},
        )
        return gate, []

    drifted = [tool for tool in versions if tool.has_drift or tool.is_missing]
    metadata = {
        "checked": ",".join(tool.name for tool in versions),
        "drifted": ",".join(tool.name for tool in drifted),
    }

    gate = GuardRailGate(
        name="drift-detection",
        passed=not drifted,
        message="No tool drift detected" if not drifted else "Tool drift detected",
        duration=time.perf_counter() - start,
        metadata=metadata,
    )
    return gate, drifted


def evaluate_guard_rails(
    *,
    principal: auth.AuthenticatedPrincipal,
    no_format: bool,
    workspace: str | None,
    drift_check: bool,
    auto_remediate: bool,
    dry_run_cleanup: bool = True,
) -> GuardRailExecution:
    """Evaluate guard-rails gates using the local toolkit primitives."""

    auth.ServiceAccountVerifier.require_role(principal, auth.Role.GUARD_RAILS.value)

    root = Path(workspace).resolve() if workspace else Path.cwd().resolve()
    start = time.perf_counter()

    gates: list[GuardRailGate] = []
    remediation_commands: list[str] = []
    remediation_results: list[drift_module.RemediationResult] = []

    gates.append(_evaluate_cleanup_gate(principal, root, dry_run=dry_run_cleanup))

    registry = discover_plugins()
    gates.extend(_evaluate_plugin_gates(registry, no_format=no_format))

    drifted: list[drift_module.ToolVersion] = []
    if drift_check:
        drift_gate, drifted = _evaluate_drift_gate(root)
        gates.append(drift_gate)

        if auto_remediate and drifted:
            remediation_commands = drift_module.generate_remediation_commands(drifted)
            remediation_results = drift_module.apply_remediation_commands(remediation_commands)

            gates.append(
                GuardRailGate(
                    name="auto-remediation",
                    passed=all(result.exit_code == 0 for result in remediation_results),
                    message=(
                        "Applied remediation commands"
                        if all(result.exit_code == 0 for result in remediation_results)
                        else "Remediation commands failed"
                    ),
                    duration=0.0,
                    metadata={"commands": ";".join(remediation_commands)},
                )
            )

    duration = time.perf_counter() - start
    success = all(gate.passed or bool(gate.metadata.get("missing")) for gate in gates)

    return GuardRailExecution(
        success=success,
        duration=duration,
        gates=gates,
        remediation_commands=remediation_commands,
        remediation_results=remediation_results,
    )


async def evaluate_guard_rails_async(
    *,
    principal: auth.AuthenticatedPrincipal,
    no_format: bool,
    workspace: str | None,
    drift_check: bool,
    auto_remediate: bool,
    dry_run_cleanup: bool = True,
) -> GuardRailExecution:
    """Async wrapper around :func:`evaluate_guard_rails`."""

    return await asyncio.to_thread(
        evaluate_guard_rails,
        principal=principal,
        no_format=no_format,
        workspace=workspace,
        drift_check=drift_check,
        auto_remediate=auto_remediate,
        dry_run_cleanup=dry_run_cleanup,
    )


def compute_rankings(
    *,
    principal: auth.AuthenticatedPrincipal,
    strategy: RankingStrategy,
    limit: int,
) -> list[dict[str, Any]]:
    """Return ranking payloads compatible with REST and gRPC surfaces."""

    auth.ServiceAccountVerifier.require_role(principal, auth.Role.ANALYTICS.value)

    try:
        settings = toolbox.load_settings()
    except FileNotFoundError:
        settings = toolbox.ToolkitSettings()

    rankings: list[dict[str, Any]] = []
    analytics_config = settings.analytics

    signals = (
        load_module_signals(analytics_config)
        if analytics_config and analytics_config.is_configured
        else {}
    )

    if signals:
        ranked = rank_modules(
            signals,
            strategy=strategy,
            coverage_threshold=settings.coverage_threshold,
            limit=limit,
        )
        for module in ranked:
            rankings.append(
                {
                    "rank": module.rank,
                    "path": module.path,
                    "score": module.score,
                    "churn": module.churn,
                    "coverage": module.coverage,
                    "uncovered_lines": module.uncovered_lines,
                    "rationale": module.rationale,
                }
            )
        return rankings

    # Fallback to synthetic hotspots when analytics data is unavailable.
    hotspots = toolbox.analyze_hotspots(settings, limit=limit)
    for idx, hotspot in enumerate(hotspots, start=1):
        rankings.append(
            {
                "rank": idx,
                "path": hotspot.path,
                "score": round(hotspot.churn / 100 + max(0.0, 1 - hotspot.coverage), 4),
                "churn": hotspot.churn,
                "coverage": hotspot.coverage,
                "uncovered_lines": None,
                "rationale": "synthetic_hotspot",
            }
        )
    return rankings


def compute_hotspots(*, principal: auth.AuthenticatedPrincipal, limit: int) -> list[dict[str, Any]]:
    """Return hotspot payloads derived from the toolkit configuration."""

    auth.ServiceAccountVerifier.require_role(principal, auth.Role.ANALYTICS.value)

    try:
        settings = toolbox.load_settings()
    except FileNotFoundError:
        settings = toolbox.ToolkitSettings()

    hotspots = toolbox.analyze_hotspots(settings, limit=limit)
    return [
        {
            "path": hotspot.path,
            "change_frequency": hotspot.churn,
            "complexity": max(1, int(hotspot.coverage * 100)),
            "risk_score": round(hotspot.churn / 100 + (1 - hotspot.coverage), 4),
        }
        for hotspot in hotspots
    ]


def detect_drift_summary(
    principal: auth.AuthenticatedPrincipal, *, workspace: str | None
) -> dict[str, Any]:
    """Return a serialisable drift detection summary."""

    auth.ServiceAccountVerifier.require_role(principal, auth.Role.GUARD_RAILS.value)

    root = Path(workspace).resolve() if workspace else Path.cwd().resolve()
    versions = drift_module.detect_drift(project_root=root)
    drifted = [tool for tool in versions if tool.has_drift or tool.is_missing]
    commands = drift_module.generate_remediation_commands(drifted)

    return {
        "has_drift": bool(drifted),
        "drifts": [
            {
                "tool": tool.name,
                "expected": tool.expected,
                "actual": tool.actual,
                "status": "missing" if tool.is_missing else "drift" if tool.has_drift else "ok",
            }
            for tool in versions
        ],
        "commands": commands,
    }
