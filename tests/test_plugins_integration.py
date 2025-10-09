"""Integration tests for plugin system."""

from __future__ import annotations

from pathlib import Path

import pytest


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


def test_plugin_execution_with_missing_tool() -> None:
    """Test that plugins handle missing tools gracefully."""
    from hephaestus.plugins import PluginResult
    from hephaestus.plugins.builtin import RuffCheckPlugin

    plugin = RuffCheckPlugin()

    # Run with unlikely command that won't exist
    result = plugin.run({"command": "/nonexistent/ruff/binary"})

    # Should return failure, not raise exception
    assert isinstance(result, PluginResult)
    assert result.success is False
    # Check for various failure messages
    message_lower = result.message.lower()
    assert any(
        keyword in message_lower for keyword in ["not found", "failed", "not installed", "error"]
    )


def test_plugin_discovery_with_no_config() -> None:
    """Test plugin discovery when no config file exists."""
    from hephaestus.plugins import PluginRegistry, discover_plugins

    registry = PluginRegistry()

    # Discover with non-existent config path
    result_registry = discover_plugins(
        config_path=Path("/nonexistent/config.toml"), registry_instance=registry
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

        def validate_config(self, config: dict) -> bool:
            return True

        def run(self, config: dict):  # type: ignore[no-untyped-def]
            pass

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

        def validate_config(self, config: dict) -> bool:
            return True

        def run(self, config: dict):  # type: ignore[no-untyped-def]
            pass

    registry = PluginRegistry()
    registry.register(LatePlugin())
    registry.register(EarlyPlugin())

    plugins = registry.all_plugins()
    assert plugins[0].metadata.name == "early"
    assert plugins[1].metadata.name == "late"


def test_plugin_lifecycle_hooks() -> None:
    """Test plugin setup and teardown hooks."""
    from hephaestus.plugins import PluginMetadata, QualityGatePlugin

    setup_called = []
    teardown_called = []

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

        def validate_config(self, config: dict) -> bool:
            return True

        def run(self, config: dict):  # type: ignore[no-untyped-def]
            from hephaestus.plugins import PluginResult

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


def test_discover_plugins_loads_all_builtins() -> None:
    """Test that discover_plugins loads all built-in plugins by default."""
    from hephaestus.plugins import PluginRegistry, discover_plugins

    registry = PluginRegistry()
    discover_plugins(registry_instance=registry)

    plugins = registry.all_plugins()
    plugin_names = {p.metadata.name for p in plugins}

    # Should have all built-in plugins
    assert "ruff-check" in plugin_names
    assert "ruff-format" in plugin_names
    assert "mypy" in plugin_names
    assert "pytest" in plugin_names
    assert "pip-audit" in plugin_names


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
