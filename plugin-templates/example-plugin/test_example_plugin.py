"""Tests for example plugin."""

from __future__ import annotations

import pytest

from example_plugin import ExamplePlugin
from hephaestus.plugins import PluginMetadata, PluginResult


def test_plugin_metadata() -> None:
    """Test plugin metadata is correctly defined."""
    plugin = ExamplePlugin()
    metadata = plugin.metadata

    assert isinstance(metadata, PluginMetadata)
    assert metadata.name == "example-plugin"
    assert metadata.version == "1.0.0"
    assert metadata.description == "Example quality gate plugin"
    assert metadata.author == "Your Name"
    assert metadata.category == "custom"
    assert isinstance(metadata.requires, list)
    assert metadata.order == 100


def test_plugin_validates_valid_config() -> None:
    """Test plugin validates correct configuration."""
    plugin = ExamplePlugin()

    # Valid configuration
    valid_config = {
        "severity": "high",
        "paths": ["."],
        "args": ["--verbose"],
    }
    assert plugin.validate_config(valid_config) is True

    # Empty configuration is also valid
    assert plugin.validate_config({}) is True


def test_plugin_validates_invalid_severity() -> None:
    """Test plugin rejects invalid severity."""
    plugin = ExamplePlugin()

    invalid_config = {"severity": "invalid"}
    with pytest.raises(ValueError, match="Invalid severity"):
        plugin.validate_config(invalid_config)


def test_plugin_validates_invalid_paths_type() -> None:
    """Test plugin rejects invalid paths type."""
    plugin = ExamplePlugin()

    invalid_config = {"paths": "not-a-list"}
    with pytest.raises(ValueError, match="'paths' must be a list"):
        plugin.validate_config(invalid_config)


def test_plugin_validates_invalid_args_type() -> None:
    """Test plugin rejects invalid args type."""
    plugin = ExamplePlugin()

    invalid_config = {"args": "not-a-list"}
    with pytest.raises(ValueError, match="'args' must be a list"):
        plugin.validate_config(invalid_config)


def test_plugin_runs_successfully() -> None:
    """Test plugin runs successfully with default config."""
    plugin = ExamplePlugin()
    config = {}

    result = plugin.run(config)

    assert isinstance(result, PluginResult)
    assert result.success is True
    assert "passed" in result.message.lower()
    assert isinstance(result.exit_code, int)
    assert result.exit_code == 0
    assert result.details is not None
    assert "severity" in result.details
    assert "paths" in result.details


def test_plugin_runs_with_custom_config() -> None:
    """Test plugin runs with custom configuration."""
    plugin = ExamplePlugin()
    config = {
        "severity": "high",
        "paths": ["src", "tests"],
        "args": ["--verbose"],
    }

    result = plugin.run(config)

    assert isinstance(result, PluginResult)
    assert result.details is not None
    assert result.details["severity"] == "high"
    assert result.details["paths"] == ["src", "tests"]


def test_plugin_optional_methods() -> None:
    """Test plugin has optional methods."""
    plugin = ExamplePlugin()

    # Should not raise errors
    plugin.setup()
    plugin.teardown()


def test_plugin_handles_defaults() -> None:
    """Test plugin handles missing config options with defaults."""
    plugin = ExamplePlugin()

    # Run with empty config
    result = plugin.run({})

    # Should use default values
    assert result.details is not None
    assert result.details["severity"] == "medium"
    assert result.details["paths"] == ["."]
