"""Built-in quality gate plugins for Hephaestus (ADR-0002 Sprint 2).

This module contains refactored versions of existing quality gates
as plugins, maintaining backward compatibility while enabling extensibility.
"""

from __future__ import annotations

import subprocess
from typing import Any

from hephaestus.plugins import PluginMetadata, PluginResult, QualityGatePlugin

__all__ = [
    "RuffCheckPlugin",
    "RuffFormatPlugin",
    "MypyPlugin",
    "PytestPlugin",
    "PipAuditPlugin",
]


class RuffCheckPlugin(QualityGatePlugin):
    """Ruff linting quality gate plugin."""

    @property
    def metadata(self) -> PluginMetadata:
        return PluginMetadata(
            name="ruff-check",
            version="1.0.0",
            description="Ruff linting for Python code",
            author="Hephaestus Team",
            category="linting",
            requires=["ruff>=0.8.0"],
            order=10,  # Run early
        )

    def validate_config(self, config: dict[str, Any]) -> bool:
        """Validate configuration."""
        if "paths" in config and not isinstance(config["paths"], list):
            raise ValueError("'paths' must be a list of strings")
        if "args" in config and not isinstance(config["args"], list):
            raise ValueError("'args' must be a list of strings")
        return True

    def run(self, config: dict[str, Any]) -> PluginResult:
        """Execute Ruff linting."""
        paths = config.get("paths", ["."])
        extra_args = config.get("args", [])

        cmd = ["ruff", "check"] + extra_args + paths

        try:
            result = subprocess.run(
                cmd,
                capture_output=True,
                text=True,
                check=False,
            )

            return PluginResult(
                success=result.returncode == 0,
                message=f"Ruff check: {'passed' if result.returncode == 0 else 'failed'}",
                details={
                    "stdout": result.stdout,
                    "stderr": result.stderr,
                    "returncode": result.returncode,
                },
                exit_code=result.returncode,
            )
        except FileNotFoundError:
            return PluginResult(
                success=False,
                message="Ruff not installed",
                details={"error": "ruff command not found"},
                exit_code=127,
            )


class RuffFormatPlugin(QualityGatePlugin):
    """Ruff formatting quality gate plugin."""

    @property
    def metadata(self) -> PluginMetadata:
        return PluginMetadata(
            name="ruff-format",
            version="1.0.0",
            description="Ruff code formatting check",
            author="Hephaestus Team",
            category="formatting",
            requires=["ruff>=0.8.0"],
            order=20,  # Run after linting
        )

    def validate_config(self, config: dict[str, Any]) -> bool:
        """Validate configuration."""
        if "paths" in config and not isinstance(config["paths"], list):
            raise ValueError("'paths' must be a list of strings")
        if "check" in config and not isinstance(config["check"], bool):
            raise ValueError("'check' must be a boolean")
        return True

    def run(self, config: dict[str, Any]) -> PluginResult:
        """Execute Ruff formatting check."""
        paths = config.get("paths", ["."])
        check_mode = config.get("check", True)

        cmd = ["ruff", "format"]
        if check_mode:
            cmd.append("--check")
        cmd.extend(paths)

        try:
            result = subprocess.run(
                cmd,
                capture_output=True,
                text=True,
                check=False,
            )

            return PluginResult(
                success=result.returncode == 0,
                message=f"Ruff format: {'passed' if result.returncode == 0 else 'failed'}",
                details={
                    "stdout": result.stdout,
                    "stderr": result.stderr,
                    "returncode": result.returncode,
                },
                exit_code=result.returncode,
            )
        except FileNotFoundError:
            return PluginResult(
                success=False,
                message="Ruff not installed",
                details={"error": "ruff command not found"},
                exit_code=127,
            )


class MypyPlugin(QualityGatePlugin):
    """Mypy type checking quality gate plugin."""

    @property
    def metadata(self) -> PluginMetadata:
        return PluginMetadata(
            name="mypy",
            version="1.0.0",
            description="Static type checking with Mypy",
            author="Hephaestus Team",
            category="type-checking",
            requires=["mypy>=1.14.0"],
            order=30,  # Run after formatting
        )

    def validate_config(self, config: dict[str, Any]) -> bool:
        """Validate configuration."""
        if "paths" in config and not isinstance(config["paths"], list):
            raise ValueError("'paths' must be a list of strings")
        if "args" in config and not isinstance(config["args"], list):
            raise ValueError("'args' must be a list of strings")
        return True

    def run(self, config: dict[str, Any]) -> PluginResult:
        """Execute Mypy type checking."""
        paths = config.get("paths", ["src", "tests"])
        extra_args = config.get("args", [])

        cmd = ["mypy"] + extra_args + paths

        try:
            result = subprocess.run(
                cmd,
                capture_output=True,
                text=True,
                check=False,
            )

            return PluginResult(
                success=result.returncode == 0,
                message=f"Mypy: {'passed' if result.returncode == 0 else 'failed'}",
                details={
                    "stdout": result.stdout,
                    "stderr": result.stderr,
                    "returncode": result.returncode,
                },
                exit_code=result.returncode,
            )
        except FileNotFoundError:
            return PluginResult(
                success=False,
                message="Mypy not installed",
                details={"error": "mypy command not found"},
                exit_code=127,
            )


class PytestPlugin(QualityGatePlugin):
    """Pytest testing quality gate plugin."""

    @property
    def metadata(self) -> PluginMetadata:
        return PluginMetadata(
            name="pytest",
            version="1.0.0",
            description="Test execution with pytest",
            author="Hephaestus Team",
            category="testing",
            requires=["pytest>=8.0.0", "pytest-cov>=7.0.0"],
            order=40,  # Run after type checking
        )

    def validate_config(self, config: dict[str, Any]) -> bool:
        """Validate configuration."""
        if "args" in config and not isinstance(config["args"], list):
            raise ValueError("'args' must be a list of strings")
        if "min_coverage" in config and not isinstance(config["min_coverage"], (int, float)):
            raise ValueError("'min_coverage' must be a number")
        return True

    def run(self, config: dict[str, Any]) -> PluginResult:
        """Execute pytest."""
        extra_args = config.get("args", [])
        min_coverage = config.get("min_coverage", 85.0)

        # Default pytest args with coverage
        cmd = [
            "pytest",
            f"--cov-fail-under={min_coverage}",
        ] + extra_args

        try:
            result = subprocess.run(
                cmd,
                capture_output=True,
                text=True,
                check=False,
            )

            return PluginResult(
                success=result.returncode == 0,
                message=f"Pytest: {'passed' if result.returncode == 0 else 'failed'}",
                details={
                    "stdout": result.stdout,
                    "stderr": result.stderr,
                    "returncode": result.returncode,
                    "min_coverage": min_coverage,
                },
                exit_code=result.returncode,
            )
        except FileNotFoundError:
            return PluginResult(
                success=False,
                message="Pytest not installed",
                details={"error": "pytest command not found"},
                exit_code=127,
            )


class PipAuditPlugin(QualityGatePlugin):
    """Pip-audit security scanning quality gate plugin."""

    @property
    def metadata(self) -> PluginMetadata:
        return PluginMetadata(
            name="pip-audit",
            version="1.0.0",
            description="Security audit of Python dependencies",
            author="Hephaestus Team",
            category="security",
            requires=["pip-audit>=2.9.0"],
            order=50,  # Run after tests
        )

    def validate_config(self, config: dict[str, Any]) -> bool:
        """Validate configuration."""
        if "args" in config and not isinstance(config["args"], list):
            raise ValueError("'args' must be a list of strings")
        if "ignore_vulns" in config and not isinstance(config["ignore_vulns"], list):
            raise ValueError("'ignore_vulns' must be a list of strings")
        return True

    def run(self, config: dict[str, Any]) -> PluginResult:
        """Execute pip-audit."""
        extra_args = config.get("args", ["--strict"])
        ignore_vulns = config.get("ignore_vulns", [])

        cmd = ["pip-audit"] + extra_args

        # Add ignore flags for specific vulnerabilities
        for vuln in ignore_vulns:
            cmd.extend(["--ignore-vuln", vuln])

        try:
            result = subprocess.run(
                cmd,
                capture_output=True,
                text=True,
                check=False,
            )

            return PluginResult(
                success=result.returncode == 0,
                message=f"Pip-audit: {'passed' if result.returncode == 0 else 'failed'}",
                details={
                    "stdout": result.stdout,
                    "stderr": result.stderr,
                    "returncode": result.returncode,
                    "ignored_vulns": ignore_vulns,
                },
                exit_code=result.returncode,
            )
        except FileNotFoundError:
            return PluginResult(
                success=False,
                message="Pip-audit not installed",
                details={"error": "pip-audit command not found"},
                exit_code=127,
            )
