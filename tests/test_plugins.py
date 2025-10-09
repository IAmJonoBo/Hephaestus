"""Tests for plugin architecture (ADR-0002)."""

from __future__ import annotations

from pathlib import Path

import pytest

from hephaestus.plugins import (
    PluginConfig,
    PluginMetadata,
    PluginRegistry,
    PluginResult,
    QualityGatePlugin,
    discover_plugins,
    load_plugin_config,
)


class MockPlugin(QualityGatePlugin):
    """Mock plugin for testing."""

    def __init__(self, name: str = "mock-plugin", order: int = 100):
        self._name = name
        self._order = order

    @property
    def metadata(self) -> PluginMetadata:
        return PluginMetadata(
            name=self._name,
            version="1.0.0",
            description="Mock plugin for testing",
            author="Test",
            category="testing",
            requires=[],
            order=self._order,
        )

    def validate_config(self, config: dict) -> bool:
        return True

    def run(self, config: dict) -> PluginResult:
        return PluginResult(
            success=True,
            message="Mock plugin executed",
            exit_code=0,
        )


def test_plugin_metadata_creation():
    """Plugin metadata should be created with correct fields."""
    metadata = PluginMetadata(
        name="test-plugin",
        version="1.0.0",
        description="Test plugin",
        author="Test Author",
        category="testing",
        requires=["dep1", "dep2"],
        order=50,
    )

    assert metadata.name == "test-plugin"
    assert metadata.version == "1.0.0"
    assert metadata.description == "Test plugin"
    assert metadata.author == "Test Author"
    assert metadata.category == "testing"
    assert metadata.requires == ["dep1", "dep2"]
    assert metadata.order == 50


def test_plugin_result_creation():
    """Plugin result should be created with correct fields."""
    result = PluginResult(
        success=True,
        message="Success",
        details={"key": "value"},
        exit_code=0,
    )

    assert result.success is True
    assert result.message == "Success"
    assert result.details == {"key": "value"}
    assert result.exit_code == 0


def test_plugin_result_defaults():
    """Plugin result should have sensible defaults."""
    result = PluginResult(success=False, message="Failed")

    assert result.success is False
    assert result.message == "Failed"
    assert result.details is None
    assert result.exit_code == 0


def test_quality_gate_plugin_interface():
    """Mock plugin should implement QualityGatePlugin interface."""
    plugin = MockPlugin()

    # Should have required methods
    assert hasattr(plugin, "metadata")
    assert hasattr(plugin, "validate_config")
    assert hasattr(plugin, "run")
    assert hasattr(plugin, "setup")
    assert hasattr(plugin, "teardown")

    # Should return expected types
    assert isinstance(plugin.metadata, PluginMetadata)
    assert isinstance(plugin.validate_config({}), bool)
    assert isinstance(plugin.run({}), PluginResult)


def test_plugin_registry_register():
    """Registry should register plugins."""
    registry = PluginRegistry()
    plugin = MockPlugin("test-plugin")

    registry.register(plugin)

    assert registry.is_registered("test-plugin")
    retrieved = registry.get("test-plugin")
    assert retrieved is plugin


def test_plugin_registry_duplicate_registration():
    """Registry should reject duplicate plugin names."""
    registry = PluginRegistry()
    plugin1 = MockPlugin("test-plugin")
    plugin2 = MockPlugin("test-plugin")

    registry.register(plugin1)

    with pytest.raises(ValueError, match="already registered"):
        registry.register(plugin2)


def test_plugin_registry_get_nonexistent():
    """Registry should raise KeyError for nonexistent plugins."""
    registry = PluginRegistry()

    with pytest.raises(KeyError, match="not registered"):
        registry.get("nonexistent")


def test_plugin_registry_all_plugins():
    """Registry should return all plugins sorted by order."""
    registry = PluginRegistry()

    plugin1 = MockPlugin("plugin1", order=100)
    plugin2 = MockPlugin("plugin2", order=50)
    plugin3 = MockPlugin("plugin3", order=150)

    registry.register(plugin1)
    registry.register(plugin2)
    registry.register(plugin3)

    all_plugins = registry.all_plugins()

    assert len(all_plugins) == 3
    # Should be sorted by order
    assert all_plugins[0].metadata.name == "plugin2"
    assert all_plugins[1].metadata.name == "plugin1"
    assert all_plugins[2].metadata.name == "plugin3"


def test_plugin_registry_is_registered():
    """Registry should correctly report registration status."""
    registry = PluginRegistry()
    plugin = MockPlugin("test-plugin")

    assert not registry.is_registered("test-plugin")

    registry.register(plugin)

    assert registry.is_registered("test-plugin")
    assert not registry.is_registered("other-plugin")


def test_plugin_optional_methods():
    """Plugin optional methods should have default implementations."""
    plugin = MockPlugin()

    # Should not raise exceptions
    plugin.setup()
    plugin.teardown()


def test_plugin_config_creation():
    """PluginConfig should be created with correct fields."""
    config = PluginConfig(
        name="test-plugin",
        enabled=True,
        config={"key": "value"},
        module="test.module",
        path="/path/to/plugin.py",
    )

    assert config.name == "test-plugin"
    assert config.enabled is True
    assert config.config == {"key": "value"}
    assert config.module == "test.module"
    assert config.path == "/path/to/plugin.py"


def test_plugin_config_defaults():
    """PluginConfig should have sensible defaults."""
    config = PluginConfig(name="test-plugin")

    assert config.name == "test-plugin"
    assert config.enabled is True
    assert config.config is None
    assert config.module is None
    assert config.path is None


def test_load_plugin_config_missing_file():
    """load_plugin_config should return empty list when file doesn't exist."""
    configs = load_plugin_config(Path("/nonexistent/path/plugins.toml"))
    assert configs == []


def test_load_plugin_config_with_builtin(tmp_path: Path):
    """load_plugin_config should parse built-in plugin configs."""
    config_file = tmp_path / "plugins.toml"
    config_file.write_text(
        """
[builtin]
ruff-check = { enabled = true, config = { paths = ["src"] } }
mypy = false
"""
    )

    configs = load_plugin_config(config_file)

    assert len(configs) == 2

    # Check ruff-check config
    ruff_config = next(c for c in configs if c.name == "ruff-check")
    assert ruff_config.enabled is True
    assert ruff_config.config == {"paths": ["src"]}

    # Check mypy config
    mypy_config = next(c for c in configs if c.name == "mypy")
    assert mypy_config.enabled is False


def test_load_plugin_config_with_external(tmp_path: Path):
    """load_plugin_config should parse external plugin configs."""
    config_file = tmp_path / "plugins.toml"
    config_file.write_text(
        """
[[external]]
name = "custom-plugin"
enabled = true
module = "custom.plugin"
config = { arg1 = "value1" }
"""
    )

    configs = load_plugin_config(config_file)

    assert len(configs) == 1
    assert configs[0].name == "custom-plugin"
    assert configs[0].enabled is True
    assert configs[0].module == "custom.plugin"
    assert configs[0].config == {"arg1": "value1"}


def test_load_plugin_config_invalid_toml(tmp_path: Path):
    """load_plugin_config should raise ValueError for invalid TOML."""
    config_file = tmp_path / "plugins.toml"
    config_file.write_text("invalid toml [")

    with pytest.raises(ValueError, match="Failed to parse plugin config"):
        load_plugin_config(config_file)


def test_discover_plugins_no_config():
    """discover_plugins should work with no config file."""
    registry_instance = PluginRegistry()
    result = discover_plugins(Path("/nonexistent/plugins.toml"), registry_instance)

    # Should return the registry instance
    assert result is registry_instance


def test_discover_plugins_loads_builtin(tmp_path: Path):
    """discover_plugins should load and register built-in plugins."""
    config_file = tmp_path / "plugins.toml"
    config_file.write_text(
        """
[builtin]
ruff-check = true
mypy = true
"""
    )

    registry_instance = PluginRegistry()
    discover_plugins(config_file, registry_instance)

    # Should have registered built-in plugins
    assert registry_instance.is_registered("ruff-check")
    assert registry_instance.is_registered("mypy")


def test_plugin_registry_clear():
    """Registry clear should remove all plugins."""
    registry = PluginRegistry()
    plugin1 = MockPlugin("plugin1")
    plugin2 = MockPlugin("plugin2")

    registry.register(plugin1)
    registry.register(plugin2)

    assert len(registry.all_plugins()) == 2

    registry.clear()

    assert len(registry.all_plugins()) == 0
    assert not registry.is_registered("plugin1")
    assert not registry.is_registered("plugin2")


def test_discover_plugins_respects_enabled_flag(tmp_path: Path):
    """discover_plugins should respect enabled flag for built-in plugins."""
    config_file = tmp_path / "plugins.toml"
    config_file.write_text(
        """
[builtin]
ruff-check = true
mypy = false
"""
    )

    registry_instance = PluginRegistry()
    discover_plugins(config_file, registry_instance)

    # ruff-check should be registered
    assert registry_instance.is_registered("ruff-check")
    # mypy should NOT be registered
    assert not registry_instance.is_registered("mypy")


def test_load_plugin_config_edge_case_empty_file(tmp_path: Path):
    """load_plugin_config should handle empty TOML files."""
    config_file = tmp_path / "plugins.toml"
    config_file.write_text("")

    configs = load_plugin_config(config_file)
    assert configs == []


def test_load_plugin_config_edge_case_no_builtin_or_external(tmp_path: Path):
    """load_plugin_config should handle files with neither builtin nor external sections."""
    config_file = tmp_path / "plugins.toml"
    config_file.write_text(
        """
[some_other_section]
key = "value"
"""
    )

    configs = load_plugin_config(config_file)
    assert configs == []

