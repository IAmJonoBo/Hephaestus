"""Tests for plugin architecture (ADR-0002 Phase 1)."""

from __future__ import annotations

import pytest

from hephaestus.plugins import (
    PluginMetadata,
    PluginRegistry,
    PluginResult,
    QualityGatePlugin,
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
