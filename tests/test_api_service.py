"""Tests for the shared API service helpers."""

from __future__ import annotations

from pathlib import Path

import pytest

from hephaestus.api import service
from hephaestus.plugins import PluginMetadata, PluginRegistry, PluginResult, QualityGatePlugin


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

    def _fake_cleanup_summary(*args: object, **kwargs: object) -> dict[str, object]:
        return {
            "files": 0,
            "bytes": 0,
            "manifest": {"search_roots": 0, "preview_count": 0, "removed_count": 0, "skipped": 0, "errors": 0},
            "preview_paths": [],
            "removed_paths": [],
        }

    monkeypatch.setattr(service, "run_cleanup_summary", _fake_cleanup_summary)


def _setup_registry(plugin: QualityGatePlugin) -> PluginRegistry:
    registry = PluginRegistry()
    registry.register(plugin)
    return registry


def test_evaluate_guard_rails_flags_missing_plugin_requirements(monkeypatch: pytest.MonkeyPatch) -> None:
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
    )

    assert result.success is False
    plugin_gate = next(g for g in result.gates if g.name == "stub-plugin")
    assert plugin_gate.passed is False
    assert "tool-that-does-not-exist" in plugin_gate.metadata["missing"]


def test_evaluate_guard_rails_succeeds_when_requirements_present(monkeypatch: pytest.MonkeyPatch) -> None:
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
    )

    assert result.success is True
    plugin_gate = next(g for g in result.gates if g.name == "stub-plugin")
    assert plugin_gate.passed is True
    assert plugin_gate.metadata["missing"] == ""
