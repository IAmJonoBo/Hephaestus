from __future__ import annotations

from datetime import UTC, datetime, timedelta
from pathlib import Path
from types import SimpleNamespace

import pytest

from hephaestus.api import auth, service
from hephaestus.plugins import (
    PluginMetadata,
    PluginRegistry,
    PluginResult,
    QualityGatePlugin,
)


class _StubPlugin(QualityGatePlugin):
    """Minimal plugin implementation for guard-rails evaluation tests."""

    def __init__(self, name: str, requires: list[str]) -> None:
        self._metadata = PluginMetadata(
            name=name,
            version="1.0.0",
            description="stub",
            author="test",
            category="custom",
            requires=requires,
            order=100,
        )

    @property
    def metadata(self) -> PluginMetadata:
        return self._metadata

    def validate_config(self, config: dict[str, object]) -> bool:
        return True

    def run(self, config: dict[str, object]) -> PluginResult:
        return PluginResult(success=True, message="ok")


@pytest.fixture(autouse=True)
def _mock_cleanup(monkeypatch: pytest.MonkeyPatch) -> None:
    """Avoid touching the filesystem during guard-rails evaluation."""

    class _CleanupResult:
        def __init__(self) -> None:
            self.removed_paths: list[Path] = []
            self.preview_paths: list[Path] = []
            self.search_roots: list[Path] = []
            self.skipped_roots: list[Path] = []
            self.errors: list[str] = []
            self.audit_manifest: Path | None = None

    monkeypatch.setattr(service, "run_cleanup", lambda options: _CleanupResult())
    monkeypatch.setattr(service, "_size_estimate", lambda paths: 0)


def _principal(*roles: str) -> auth.AuthenticatedPrincipal:
    now = datetime.now(UTC)
    return auth.AuthenticatedPrincipal(
        principal=f"svc-{'-'.join(sorted(roles)) or 'none'}@example.com",
        roles=frozenset(roles),
        key_id="test-key",
        issued_at=now - timedelta(minutes=5),
        expires_at=now + timedelta(hours=1),
    )


@pytest.fixture()
def guard_principal() -> auth.AuthenticatedPrincipal:
    return _principal(auth.Role.GUARD_RAILS.value, auth.Role.CLEANUP.value)


@pytest.fixture()
def cleanup_principal() -> auth.AuthenticatedPrincipal:
    return _principal(auth.Role.CLEANUP.value)


@pytest.fixture()
def analytics_principal() -> auth.AuthenticatedPrincipal:
    return _principal(auth.Role.ANALYTICS.value)


def _setup_registry(plugin: QualityGatePlugin) -> PluginRegistry:
    registry = PluginRegistry()
    registry.register(plugin)
    return registry


def test_evaluate_guard_rails_flags_missing_plugin_requirements(
    monkeypatch: pytest.MonkeyPatch,
    guard_principal: auth.AuthenticatedPrincipal,
) -> None:
    """Guard-rails evaluation should fail when plugin tooling requirements are missing."""

    registry = _setup_registry(_StubPlugin("stub-plugin", ["tool-that-does-not-exist>=1.0"]))
    monkeypatch.setattr(service, "discover_plugins", lambda *_, **__: registry)

    original_which = service.shutil.which

    def _fake_which(name: str) -> str | None:
        if name == "tool-that-does-not-exist":
            return None
        assert original_which is not None
        return original_which(name)

    monkeypatch.setattr(service.shutil, "which", _fake_which)

    result = service.evaluate_guard_rails(
        no_format=False,
        workspace=str(Path.cwd()),
        drift_check=False,
        auto_remediate=False,
        principal=guard_principal,
    )

    plugin_gate = next(g for g in result.gates if g.name == "stub-plugin")
    assert plugin_gate.passed is False
    assert "tool-that-does-not-exist" in plugin_gate.metadata["missing"]


def test_evaluate_guard_rails_succeeds_when_requirements_present(
    monkeypatch: pytest.MonkeyPatch,
    guard_principal: auth.AuthenticatedPrincipal,
) -> None:
    """Guard-rails evaluation should succeed when required tooling exists."""

    registry = _setup_registry(_StubPlugin("stub-plugin", ["stub-tool>=1.0"]))
    monkeypatch.setattr(service, "discover_plugins", lambda *_, **__: registry)

    def _fake_which(name: str) -> str | None:
        if name == "stub-tool":
            return "/usr/bin/stub-tool"
        return "/usr/bin/true"

    monkeypatch.setattr(service.shutil, "which", _fake_which)

    result = service.evaluate_guard_rails(
        no_format=False,
        workspace=str(Path.cwd()),
        drift_check=False,
        auto_remediate=False,
        principal=guard_principal,
    )

    assert result.success is True
    plugin_gate = next(g for g in result.gates if g.name == "stub-plugin")
    assert plugin_gate.passed is True
    assert plugin_gate.metadata["missing"] == ""


def test_run_cleanup_summary_enforces_role(
    monkeypatch: pytest.MonkeyPatch,
    cleanup_principal: auth.AuthenticatedPrincipal,
    analytics_principal: auth.AuthenticatedPrincipal,
) -> None:
    class _CleanupResult:
        def __init__(self) -> None:
            self.removed_paths = [Path("/tmp/removed.log")]
            self.preview_paths = [Path("/tmp/preview.log")]
            self.search_roots = [Path("/tmp")]
            self.skipped_roots: list[Path] = []
            self.errors: list[str] = []
            self.audit_manifest = Path("/tmp/manifest.json")

    monkeypatch.setattr(service, "run_cleanup", lambda options: _CleanupResult())
    monkeypatch.setattr(service, "_size_estimate", lambda paths: 42)

    summary = service.run_cleanup_summary(
        principal=cleanup_principal,
        root=None,
        deep_clean=False,
        dry_run=False,
    )

    assert summary["files"] == 1
    assert summary["bytes"] == 42
    assert "audit_manifest" in summary["manifest"]

    with pytest.raises(auth.AuthorizationError):
        service.run_cleanup_summary(
            principal=analytics_principal,
            root=None,
            deep_clean=False,
            dry_run=False,
        )


def test_compute_rankings_requires_analytics_role(
    monkeypatch: pytest.MonkeyPatch,
    analytics_principal: auth.AuthenticatedPrincipal,
    guard_principal: auth.AuthenticatedPrincipal,
) -> None:
    monkeypatch.setattr(service.toolbox, "load_settings", lambda: service.toolbox.ToolkitSettings())
    monkeypatch.setattr(
        service.toolbox,
        "analyze_hotspots",
        lambda settings, limit: [SimpleNamespace(path="module.py", churn=10, coverage=0.6)],
    )

    rankings = service.compute_rankings(
        principal=analytics_principal,
        strategy=service.RankingStrategy.RISK_WEIGHTED,
        limit=5,
    )

    assert rankings and rankings[0]["path"] == "module.py"

    with pytest.raises(auth.AuthorizationError):
        service.compute_rankings(
            principal=guard_principal,
            strategy=service.RankingStrategy.RISK_WEIGHTED,
            limit=5,
        )


def test_compute_hotspots_requires_analytics_role(
    monkeypatch: pytest.MonkeyPatch,
    analytics_principal: auth.AuthenticatedPrincipal,
    guard_principal: auth.AuthenticatedPrincipal,
) -> None:
    monkeypatch.setattr(service.toolbox, "load_settings", lambda: service.toolbox.ToolkitSettings())
    monkeypatch.setattr(
        service.toolbox,
        "analyze_hotspots",
        lambda settings, limit: [SimpleNamespace(path="module.py", churn=5, coverage=0.8)],
    )

    hotspots = service.compute_hotspots(principal=analytics_principal, limit=3)
    assert hotspots[0]["change_frequency"] == 5

    with pytest.raises(auth.AuthorizationError):
        service.compute_hotspots(principal=guard_principal, limit=3)


def test_detect_drift_summary_requires_guard_role(
    monkeypatch: pytest.MonkeyPatch,
    guard_principal: auth.AuthenticatedPrincipal,
    analytics_principal: auth.AuthenticatedPrincipal,
) -> None:
    tool = SimpleNamespace(
        name="ruff",
        expected="0.4.0",
        actual="0.3.0",
        has_drift=True,
        is_missing=False,
    )
    monkeypatch.setattr(service.drift_module, "detect_drift", lambda project_root: [tool])
    monkeypatch.setattr(service.drift_module, "generate_remediation_commands", lambda tools: ["pip install ruff==0.4.0"])

    summary = service.detect_drift_summary(guard_principal, workspace=None)
    assert summary["has_drift"] is True
    assert summary["commands"] == ["pip install ruff==0.4.0"]

    with pytest.raises(auth.AuthorizationError):
        service.detect_drift_summary(analytics_principal, workspace=None)
