"""Plugin architecture for extensible quality gates (ADR-0002).

This module provides the foundation for a plugin-based quality gate system,
allowing custom quality checks to be added without modifying Hephaestus core.

Phase 1 (Complete): API specification and registry
Phase 2 (Complete): Built-in plugins
Phase 3 (This update): Plugin discovery and configuration loading
"""

from __future__ import annotations

import importlib
import importlib.util
import logging
import sys
from abc import ABC, abstractmethod
from dataclasses import dataclass
from pathlib import Path
from typing import Any

try:
    import tomli as tomllib  # type: ignore  # Python < 3.11
except ImportError:
    import tomllib

__all__ = [
    "PluginMetadata",
    "PluginResult",
    "QualityGatePlugin",
    "PluginRegistry",
    "PluginConfig",
    "discover_plugins",
    "load_plugin_config",
]

logger = logging.getLogger(__name__)


@dataclass
class PluginMetadata:
    """Metadata about a quality gate plugin."""

    name: str
    version: str
    description: str
    author: str
    category: str  # "linting", "testing", "security", "custom"
    requires: list[str]  # Dependencies
    order: int = 100  # Execution order (lower = earlier)


@dataclass
class PluginResult:
    """Result of running a plugin."""

    success: bool
    message: str
    details: dict[str, Any] | None = None
    exit_code: int = 0


class QualityGatePlugin(ABC):
    """Base class for quality gate plugins.

    Example:
        class MyPlugin(QualityGatePlugin):
            @property
            def metadata(self) -> PluginMetadata:
                return PluginMetadata(
                    name="my-plugin",
                    version="1.0.0",
                    description="My custom quality check",
                    author="Me",
                    category="custom",
                    requires=[],
                    order=100,
                )

            def validate_config(self, config: dict) -> bool:
                return True

            def run(self, config: dict) -> PluginResult:
                return PluginResult(success=True, message="Check passed")
    """

    @property
    @abstractmethod
    def metadata(self) -> PluginMetadata:
        """Return plugin metadata."""
        pass

    @abstractmethod
    def validate_config(self, config: dict[str, Any]) -> bool:
        """Validate plugin configuration.

        Args:
            config: Configuration dictionary for this plugin

        Returns:
            True if configuration is valid

        Raises:
            ValueError: If configuration is invalid
        """
        pass

    @abstractmethod
    def run(self, config: dict[str, Any]) -> PluginResult:
        """Execute the quality gate check.

        Args:
            config: Configuration dictionary for this plugin

        Returns:
            Result of the quality gate execution
        """
        pass

    def setup(self) -> None:  # noqa: B027 - intentional hook with default no-op implementation
        """Optional: Setup before running.

        Override this method if your plugin needs to perform setup
        operations before executing the quality check.

        Default implementation does nothing.
        """

    def teardown(self) -> None:  # noqa: B027 - intentional hook with default no-op implementation
        """Optional: Cleanup after running.

        Override this method if your plugin needs to perform cleanup
        operations after executing the quality check.

        Default implementation does nothing.
        """


@dataclass
class PluginConfig:
    """Configuration for a plugin from config file."""

    name: str
    enabled: bool = True
    config: dict[str, Any] | None = None
    module: str | None = None  # For importable plugins
    path: str | None = None  # For file-based plugins


class PluginRegistry:
    """Registry for quality gate plugins with discovery support."""

    def __init__(self) -> None:
        self._plugins: dict[str, QualityGatePlugin] = {}

    def register(self, plugin: QualityGatePlugin) -> None:
        """Register a quality gate plugin.

        Args:
            plugin: Plugin instance to register

        Raises:
            ValueError: If plugin name is already registered
        """
        name = plugin.metadata.name
        if name in self._plugins:
            raise ValueError(f"Plugin {name!r} already registered")
        self._plugins[name] = plugin

    def get(self, name: str) -> QualityGatePlugin:
        """Retrieve a registered plugin by name.

        Args:
            name: Plugin name to look up

        Returns:
            The registered plugin

        Raises:
            KeyError: If plugin name is not registered
        """
        try:
            return self._plugins[name]
        except KeyError as exc:
            raise KeyError(f"Plugin {name!r} not registered") from exc

    def all_plugins(self) -> list[QualityGatePlugin]:
        """Return all registered plugins.

        Returns:
            List of all registered plugins, sorted by execution order
        """
        return sorted(self._plugins.values(), key=lambda p: p.metadata.order)

    def is_registered(self, name: str) -> bool:
        """Check if a plugin is registered.

        Args:
            name: Plugin name to check

        Returns:
            True if plugin is registered
        """
        return name in self._plugins

    def clear(self) -> None:
        """Clear all registered plugins.

        Useful for testing and reloading plugins.
        """
        self._plugins.clear()


def load_plugin_config(config_path: Path | None = None) -> list[PluginConfig]:
    """Load plugin configuration from TOML file.

    Args:
        config_path: Path to plugin configuration file.
                    Defaults to .hephaestus/plugins.toml in current directory.

    Returns:
        List of plugin configurations

    Raises:
        FileNotFoundError: If config file doesn't exist
        ValueError: If config file is invalid
    """
    if config_path is None:
        config_path = Path.cwd() / ".hephaestus" / "plugins.toml"

    if not config_path.exists():
        logger.debug("No plugin config file found", extra={"path": str(config_path)})
        return []

    logger.debug("Loading plugin config", extra={"path": str(config_path)})

    try:
        with open(config_path, "rb") as f:
            data = tomllib.load(f)
    except Exception as e:
        raise ValueError(f"Failed to parse plugin config: {e}") from e

    plugins = []

    # Load built-in plugins config
    builtin = data.get("builtin", {})
    for name, config in builtin.items():
        if not isinstance(config, dict):
            config = {"enabled": config}
        plugins.append(
            PluginConfig(
                name=name,
                enabled=config.get("enabled", True),
                config=config.get("config", {}),
            )
        )

    # Load external plugins config
    external = data.get("external", [])
    for plugin_data in external:
        if not isinstance(plugin_data, dict):
            raise ValueError(f"Invalid plugin config: {plugin_data}")

        plugins.append(
            PluginConfig(
                name=plugin_data.get("name", ""),
                enabled=plugin_data.get("enabled", True),
                config=plugin_data.get("config", {}),
                module=plugin_data.get("module"),
                path=plugin_data.get("path"),
            )
        )

    return plugins


def discover_plugins(
    config_path: Path | None = None, registry_instance: PluginRegistry | None = None
) -> PluginRegistry:
    """Discover and load plugins from configuration.

    This function:
    1. Loads plugin configuration from file
    2. Loads built-in plugins
    3. Discovers and loads external plugins
    4. Registers all enabled plugins

    Args:
        config_path: Path to plugin configuration file
        registry_instance: Registry to use. If None, uses global registry.

    Returns:
        Registry with discovered plugins

    Raises:
        ValueError: If plugin loading fails
    """
    if registry_instance is None:
        registry_instance = registry

    # Ensure we always honour the latest configuration by starting from a clean
    # registry snapshot. This prevents previously enabled plugins from
    # remaining registered after being disabled in configuration files.
    registry_instance.clear()

    # Load plugin configurations
    configs = load_plugin_config(config_path)

    # Load built-in plugins
    try:
        from hephaestus.plugins.builtin import (
            MypyPlugin,
            PipAuditPlugin,
            PytestPlugin,
            RuffCheckPlugin,
            RuffFormatPlugin,
        )

        builtin_plugins: dict[str, type[QualityGatePlugin]] = {
            "ruff-check": RuffCheckPlugin,
            "ruff-format": RuffFormatPlugin,
            "mypy": MypyPlugin,
            "pytest": PytestPlugin,
            "pip-audit": PipAuditPlugin,
        }

        # Register built-in plugins based on config
        for plugin_name, plugin_class in builtin_plugins.items():
            # Check if explicitly disabled in config
            plugin_config = next(
                (c for c in configs if c.name == plugin_name),
                PluginConfig(name=plugin_name, enabled=True),
            )

            if plugin_config.enabled:
                try:
                    plugin_instance = plugin_class()
                    if not registry_instance.is_registered(plugin_name):
                        registry_instance.register(plugin_instance)
                        logger.debug("Registered built-in plugin", extra={"plugin": plugin_name})
                except Exception as e:
                    logger.warning(
                        "Failed to load built-in plugin",
                        extra={"plugin": plugin_name, "error": str(e)},
                    )

    except ImportError as e:
        logger.debug("Built-in plugins not available", extra={"error": str(e)})

    # Load external plugins
    for plugin_config in configs:
        if plugin_config.module or plugin_config.path:
            try:
                _load_external_plugin(plugin_config, registry_instance)
            except Exception as e:
                logger.warning(
                    "Failed to load external plugin",
                    extra={"plugin": plugin_config.name, "error": str(e)},
                )

    return registry_instance


def _load_external_plugin(config: PluginConfig, registry_instance: PluginRegistry) -> None:
    """Load an external plugin from module or file path.

    Args:
        config: Plugin configuration
        registry_instance: Registry to register plugin in

    Raises:
        ValueError: If plugin cannot be loaded
    """
    if not config.enabled:
        return

    # Edge case: neither module nor path specified
    if not config.module and not config.path:
        raise ValueError(f"Plugin {config.name} has neither 'module' nor 'path' specified")

    plugin_class = None

    # Try loading from module
    if config.module:
        try:
            module = importlib.import_module(config.module)
            # Look for a class that inherits from QualityGatePlugin
            for attr_name in dir(module):
                attr = getattr(module, attr_name)
                if (
                    isinstance(attr, type)
                    and issubclass(attr, QualityGatePlugin)
                    and attr is not QualityGatePlugin
                ):
                    plugin_class = attr
                    break
        except ImportError as e:
            raise ValueError(f"Failed to import plugin module {config.module}: {e}") from e

    # Try loading from file path
    elif config.path:
        # Edge case: path doesn't exist
        path_obj = Path(config.path)
        if not path_obj.exists():
            raise ValueError(f"Plugin path does not exist: {config.path}")

        try:
            spec = importlib.util.spec_from_file_location(config.name, config.path)
            if spec is None or spec.loader is None:
                raise ValueError(f"Failed to load plugin from {config.path}")

            module = importlib.util.module_from_spec(spec)
            sys.modules[config.name] = module
            spec.loader.exec_module(module)

            # Look for a class that inherits from QualityGatePlugin
            for attr_name in dir(module):
                attr = getattr(module, attr_name)
                if (
                    isinstance(attr, type)
                    and issubclass(attr, QualityGatePlugin)
                    and attr is not QualityGatePlugin
                ):
                    plugin_class = attr
                    break
        except Exception as e:
            raise ValueError(f"Failed to load plugin from {config.path}: {e}") from e

    if plugin_class is None:
        raise ValueError(f"No QualityGatePlugin class found for plugin {config.name}")

    # Instantiate and register the plugin
    try:
        plugin_instance = plugin_class()
        if not registry_instance.is_registered(config.name):
            registry_instance.register(plugin_instance)
            logger.info("Loaded external plugin", extra={"plugin": config.name})
    except Exception as e:
        raise ValueError(f"Failed to instantiate plugin {config.name}: {e}") from e


# Global registry instance
registry = PluginRegistry()
