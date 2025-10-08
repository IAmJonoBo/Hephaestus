"""Plugin architecture for extensible quality gates (ADR-0002 Phase 1).

This module provides the foundation for a plugin-based quality gate system,
allowing custom quality checks to be added without modifying Hephaestus core.

Note: This is Phase 1 (Foundation) - plugin discovery and built-in plugins
are not yet implemented. This provides the API specification.
"""

from __future__ import annotations

from abc import ABC, abstractmethod
from dataclasses import dataclass
from typing import Any

__all__ = [
    "PluginMetadata",
    "PluginResult",
    "QualityGatePlugin",
    "PluginRegistry",
]


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

    def setup(self) -> None:
        """Optional: Setup before running.

        Override this method if your plugin needs to perform setup
        operations before executing the quality check.
        """
        pass

    def teardown(self) -> None:
        """Optional: Cleanup after running.

        Override this method if your plugin needs to perform cleanup
        operations after executing the quality check.
        """
        pass


class PluginRegistry:
    """Registry for quality gate plugins.

    Note: Phase 1 implementation - discovery and loading not yet implemented.
    This provides the registry structure for future phases.
    """

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


# Global registry instance
registry = PluginRegistry()
