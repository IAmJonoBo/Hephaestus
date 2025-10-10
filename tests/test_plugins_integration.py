import shutil
import textwrap
from pathlib import Path
from typing import Any, NoReturn

import pytest

from hephaestus import telemetry
from hephaestus.plugins import PluginResult

PROJECT_ROOT = Path(__file__).resolve().parent.parent
DEFAULT_MARKETPLACE_ROOT = PROJECT_ROOT / "plugin-templates" / "registry"


def test_plugin_system_imports() -> None:
    """Test that plugin system can be imported."""
    from hephaestus.plugins import (
        PluginConfig,
        PluginMetadata,
        PluginRegistry,
        PluginResult,
        QualityGatePlugin,
        discover_plugins,
        load_plugin_config,
    )

    assert PluginMetadata is not None
    assert PluginResult is not None
    assert QualityGatePlugin is not None
    assert PluginRegistry is not None
    assert PluginConfig is not None
    assert discover_plugins is not None
    assert load_plugin_config is not None


def test_builtin_plugins_available() -> None:
    """Test that built-in plugins are available."""
    from hephaestus.plugins.builtin import (
        MypyPlugin,
        PipAuditPlugin,
        PytestPlugin,
        RuffCheckPlugin,
        RuffFormatPlugin,
    )

    # Should be able to instantiate
    ruff_check = RuffCheckPlugin()
    assert ruff_check.metadata.name == "ruff-check"
    assert ruff_check.metadata.category == "linting"

    ruff_format = RuffFormatPlugin()
    assert ruff_format.metadata.name == "ruff-format"

    mypy = MypyPlugin()
    assert mypy.metadata.name == "mypy"

    pytest_plugin = PytestPlugin()
    assert pytest_plugin.metadata.name == "pytest"

    pip_audit = PipAuditPlugin()
    assert pip_audit.metadata.name == "pip-audit"


def test_plugin_config_validation() -> None:
    """Test plugin configuration validation."""
    from hephaestus.plugins.builtin import RuffCheckPlugin

    plugin = RuffCheckPlugin()

    # Valid config
    assert plugin.validate_config({"paths": ["src", "tests"]}) is True

    # Empty config should be valid
    assert plugin.validate_config({}) is True

    # Invalid paths type - should raise ValueError
    with pytest.raises(ValueError, match="paths"):
        plugin.validate_config({"paths": "not-a-list"})


def test_plugin_execution_with_missing_tool(monkeypatch: pytest.MonkeyPatch) -> None:
    """Test that plugins handle missing tools gracefully."""
    from hephaestus.plugins import PluginResult
    from hephaestus.plugins.builtin import RuffCheckPlugin

    plugin = RuffCheckPlugin()

    def raise_missing(*_args: Any, **_kwargs: Any) -> NoReturn:
        raise FileNotFoundError("ruff command not found")

    monkeypatch.setattr("subprocess.run", raise_missing)

    result = plugin.run({})

    assert isinstance(result, PluginResult)
    assert result.success is False
    assert result.exit_code == 127
    assert "not" in result.message.lower()


def test_plugin_discovery_with_no_config() -> None:
    """Test plugin discovery when no config file exists."""
    from hephaestus.plugins import PluginRegistry, discover_plugins

    registry = PluginRegistry()

    # Discover with non-existent config path
    result_registry = discover_plugins(
        config_path=Path("/nonexistent/config.toml"),
        registry_instance=registry,
        marketplace_root=DEFAULT_MARKETPLACE_ROOT,
    )

    # Should still load built-in plugins
    assert result_registry is not None
    plugins = result_registry.all_plugins()
    assert len(plugins) >= 5  # At least the 5 built-in plugins


def test_plugin_registry_ordering() -> None:
    """Test that plugins are sorted by execution order."""
    from hephaestus.plugins import PluginMetadata, PluginRegistry, QualityGatePlugin

    class EarlyPlugin(QualityGatePlugin):
        @property
        def metadata(self) -> PluginMetadata:
            return PluginMetadata(
                name="early",
                version="1.0",
                description="Early plugin",
                author="test",
                category="test",
                requires=[],
                order=10,
            )

        def validate_config(self, config: dict[str, Any]) -> bool:
            return True

        def run(self, config: dict[str, Any]) -> PluginResult:
            from hephaestus.plugins import PluginResult

            return PluginResult(success=True, message="ok")

    class LatePlugin(QualityGatePlugin):
        @property
        def metadata(self) -> PluginMetadata:
            return PluginMetadata(
                name="late",
                version="1.0",
                description="Late plugin",
                author="test",
                category="test",
                requires=[],
                order=100,
            )

        def validate_config(self, config: dict[str, Any]) -> bool:
            return True

        def run(self, config: dict[str, Any]) -> PluginResult:
            from hephaestus.plugins import PluginResult

            return PluginResult(success=True, message="ok")

    registry = PluginRegistry()
    registry.register(LatePlugin())
    registry.register(EarlyPlugin())

    plugins = registry.all_plugins()
    assert plugins[0].metadata.name == "early"
    assert plugins[1].metadata.name == "late"


def test_plugin_lifecycle_hooks() -> None:
    """Test plugin setup and teardown hooks."""
    from hephaestus.plugins import PluginMetadata, PluginResult, QualityGatePlugin

    setup_called: list[bool] = []
    teardown_called: list[bool] = []

    class LifecyclePlugin(QualityGatePlugin):
        @property
        def metadata(self) -> PluginMetadata:
            return PluginMetadata(
                name="lifecycle",
                version="1.0",
                description="Test lifecycle",
                author="test",
                category="test",
                requires=[],
            )

        def validate_config(self, config: dict[str, Any]) -> bool:
            return True

        def run(self, config: dict[str, Any]) -> PluginResult:
            return PluginResult(success=True, message="ok")

        def setup(self) -> None:
            setup_called.append(True)

        def teardown(self) -> None:
            teardown_called.append(True)

    plugin = LifecyclePlugin()

    # Setup and teardown should be callable
    plugin.setup()
    assert len(setup_called) == 1

    plugin.run({})

    plugin.teardown()
    assert len(teardown_called) == 1


def _write_plugin_config(tmp_path: Path, version: str = "1.0.0") -> Path:
    config_dir = tmp_path / ".hephaestus"
    config_dir.mkdir()
    config_path = config_dir / "plugins.toml"
    config_path.write_text(
        textwrap.dedent(
            f"""
            [builtin]
            [builtin.ruff-check]
            enabled = true

            [[marketplace]]
            name = "example-plugin"
            version = "{version}"
            registry = "default"
            enabled = true

            [marketplace.config]
            severity = "high"
            """
        ).strip()
        + "\n",
        encoding="utf-8",
    )
    return config_path


def _capture_counters(monkeypatch: pytest.MonkeyPatch) -> list[tuple[str, int, dict[str, Any]]]:
    captured: list[tuple[str, int, dict[str, Any]]] = []

    def fake_counter(name: str, value: int = 1, attributes: dict[str, Any] | None = None) -> None:
        captured.append((name, value, attributes or {}))

    monkeypatch.setattr(telemetry, "record_counter", fake_counter)
    return captured


def _copy_registry(tmp_path: Path) -> Path:
    registry_root = tmp_path / "registry"
    shutil.copytree(DEFAULT_MARKETPLACE_ROOT, registry_root)
    example_source = PROJECT_ROOT / "plugin-templates" / "example-plugin"
    shutil.copytree(example_source, tmp_path / "example-plugin")
    return registry_root


def test_marketplace_discovery_validates_signature_and_dependencies(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    from hephaestus.plugins import PluginRegistry, discover_plugins

    config_path = _write_plugin_config(tmp_path)
    captured = _capture_counters(monkeypatch)

    registry = PluginRegistry()
    discover_plugins(
        config_path=config_path,
        registry_instance=registry,
        marketplace_root=DEFAULT_MARKETPLACE_ROOT,
    )

    plugin = registry.get("example-plugin")
    assert plugin.metadata.version == "1.0.0"

    counter_names = {name for name, _, _ in captured}
    assert "hephaestus.plugins.marketplace.fetch" in counter_names
    assert "hephaestus.plugins.marketplace.verified" in counter_names
    assert "hephaestus.plugins.marketplace.dependencies_resolved" in counter_names


def test_marketplace_version_mismatch_raises(tmp_path: Path) -> None:
    from hephaestus.plugins import PluginRegistry, discover_plugins

    config_path = _write_plugin_config(tmp_path, version="9.9.9")
    registry = PluginRegistry()

    with pytest.raises(ValueError, match="version 9.9.9"):
        discover_plugins(
            config_path=config_path,
            registry_instance=registry,
            marketplace_root=DEFAULT_MARKETPLACE_ROOT,
        )


def test_marketplace_dependency_resolution_blocks_missing_python(tmp_path: Path) -> None:
    from hephaestus.plugins import PluginRegistry, discover_plugins

    registry_root = _copy_registry(tmp_path)

    manifest_path = registry_root / "example-plugin.toml"
    manifest_path.write_text(
        textwrap.dedent(
            """
            [plugin]
            name = "example-plugin"
            version = "1.0.0"
            description = "Example quality gate plugin"
            category = "custom"
            author = "Hephaestus Maintainers"

            [plugin.compatibility]
            hephaestus = ">=0.2.0"
            python = ">=3.12"

            [[plugin.dependencies]]
            type = "python"
            name = "totally-uninstalled-package"
            version = ">=99.0"

            [plugin.entrypoint]
            path = "../example-plugin/example_plugin.py"

            [plugin.signature]
            bundle = "example-plugin.sigstore"
            """
        ).strip()
        + "\n",
        encoding="utf-8",
    )

    config_path = _write_plugin_config(tmp_path)
    registry = PluginRegistry()

    with pytest.raises(ValueError, match="totally-uninstalled-package"):
        discover_plugins(
            config_path=config_path,
            registry_instance=registry,
            marketplace_root=registry_root,
        )


def test_marketplace_trust_policy_enforced(tmp_path: Path) -> None:
    from hephaestus.plugins import PluginRegistry, discover_plugins

    registry_root = _copy_registry(tmp_path)

    trust_policy = registry_root / "trust-policy.toml"
    trust_policy.write_text(
        textwrap.dedent(
            """
            [trust]
            require_signature = true
            allowed_identities = ["mailto:other@hephaestus.dev"]
            """
        ).strip()
        + "\n",
        encoding="utf-8",
    )

    config_path = _write_plugin_config(tmp_path)
    registry = PluginRegistry()

    with pytest.raises(ValueError, match="trust policy"):
        discover_plugins(
            config_path=config_path,
            registry_instance=registry,
            marketplace_root=registry_root,
        )


def test_plugin_result_with_details() -> None:
    """Test that plugin results can include detailed information."""
    from hephaestus.plugins import PluginResult

    result = PluginResult(
        success=True,
        message="Check passed",
        details={
            "files_checked": 42,
            "violations": 0,
            "duration": 2.5,
        },
        exit_code=0,
    )

    assert result.success is True
    assert result.details is not None
    assert result.details["files_checked"] == 42
    assert result.exit_code == 0
