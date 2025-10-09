"""Example quality gate plugin for Hephaestus.

This is a template for creating custom quality gate plugins. It demonstrates
best practices for plugin development, including metadata, validation, and execution.
"""

from __future__ import annotations

import subprocess
from typing import Any

from hephaestus.plugins import PluginMetadata, PluginResult, QualityGatePlugin


class ExamplePlugin(QualityGatePlugin):
    """Example custom quality gate plugin.

    This plugin demonstrates how to create a custom quality check that
    integrates with Hephaestus's guard-rails command.

    Configuration Options:
        severity (str): Minimum severity level to check (low, medium, high)
        paths (list[str]): Paths to check (default: ["."])
        args (list[str]): Additional command arguments
    """

    @property
    def metadata(self) -> PluginMetadata:
        """Return plugin metadata."""
        return PluginMetadata(
            name="example-plugin",
            version="1.0.0",
            description="Example quality gate plugin",
            author="Your Name",
            category="custom",
            requires=[],  # List Python package dependencies here
            order=100,  # Execution order (lower runs earlier)
        )

    def validate_config(self, config: dict[str, Any]) -> bool:
        """Validate plugin configuration.

        Args:
            config: Configuration dictionary for this plugin

        Returns:
            True if configuration is valid

        Raises:
            ValueError: If configuration is invalid
        """
        # Example: Validate severity option
        if "severity" in config:
            severity = config["severity"]
            valid_severities = ["low", "medium", "high"]
            if severity not in valid_severities:
                raise ValueError(
                    f"Invalid severity '{severity}'. Must be one of: {valid_severities}"
                )

        # Example: Validate paths option
        if "paths" in config and not isinstance(config["paths"], list):
            raise ValueError("'paths' must be a list of strings")

        # Example: Validate args option
        if "args" in config and not isinstance(config["args"], list):
            raise ValueError("'args' must be a list of strings")

        return True

    def run(self, config: dict[str, Any]) -> PluginResult:
        """Execute the quality gate check.

        Args:
            config: Configuration dictionary for this plugin

        Returns:
            Result of the quality gate execution
        """
        # Extract configuration options with defaults
        severity = config.get("severity", "medium")
        paths = config.get("paths", ["."])
        extra_args = config.get("args", [])

        # Example: Build command to run
        # Replace this with your actual quality check logic
        cmd = ["echo", f"Running quality check with severity={severity}"]
        cmd.extend(extra_args)
        cmd.extend(paths)

        try:
            # Execute the check
            result = subprocess.run(
                cmd,
                capture_output=True,
                text=True,
                check=False,
                timeout=300,  # 5 minute timeout
            )

            # Determine success
            success = result.returncode == 0

            # Return result with details
            return PluginResult(
                success=success,
                message=f"Example check: {'passed' if success else 'failed'}",
                details={
                    "stdout": result.stdout,
                    "stderr": result.stderr,
                    "returncode": result.returncode,
                    "severity": severity,
                    "paths": paths,
                },
                exit_code=result.returncode,
            )

        except subprocess.TimeoutExpired:
            return PluginResult(
                success=False,
                message="Example check timed out after 300 seconds",
                details={"error": "timeout"},
                exit_code=124,
            )
        except FileNotFoundError as e:
            return PluginResult(
                success=False,
                message=f"Command not found: {e}",
                details={"error": str(e)},
                exit_code=127,
            )
        except Exception as e:
            return PluginResult(
                success=False,
                message=f"Example check failed with error: {e}",
                details={"error": str(e)},
                exit_code=1,
            )

    def setup(self) -> None:
        """Optional: Setup before running.

        Override this method if your plugin needs to perform setup
        operations before executing the quality check.

        Examples:
        - Create temporary directories
        - Download resources
        - Initialize connections
        """
        # Example setup (remove if not needed)
        pass

    def teardown(self) -> None:
        """Optional: Cleanup after running.

        Override this method if your plugin needs to perform cleanup
        operations after executing the quality check.

        Examples:
        - Remove temporary files
        - Close connections
        - Archive logs
        """
        # Example teardown (remove if not needed)
        pass
