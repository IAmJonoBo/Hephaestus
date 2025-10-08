"""Tool version drift detection for guard rails."""

from __future__ import annotations

import re
import subprocess
from dataclasses import dataclass
from pathlib import Path
from typing import Any

try:
    import tomllib  # Python 3.11+
except ImportError:
    import tomli as tomllib  # type: ignore[import,no-redef]


@dataclass(frozen=True)
class ToolVersion:
    """Version information for a development tool."""

    name: str
    expected: str | None
    actual: str | None

    @property
    def has_drift(self) -> bool:
        """Check if actual version differs from expected."""
        if self.expected is None or self.actual is None:
            return False
        return not self._versions_match(self.expected, self.actual)

    @property
    def is_missing(self) -> bool:
        """Check if tool is not installed."""
        return self.actual is None

    @staticmethod
    def _versions_match(expected: str, actual: str) -> bool:
        """Check if versions match, ignoring patch differences."""
        expected_parts = expected.split(".")[:2]  # Compare major.minor only
        actual_parts = actual.split(".")[:2]
        return expected_parts == actual_parts


class DriftDetectionError(RuntimeError):
    """Raised when drift detection cannot be performed."""


def detect_drift(project_root: Path | None = None) -> list[ToolVersion]:
    """Detect version drift between pyproject.toml and installed tools.

    Args:
        project_root: Project root directory containing pyproject.toml

    Returns:
        List of tool versions with drift status

    Raises:
        DriftDetectionError: If pyproject.toml cannot be read
    """
    if project_root is None:
        project_root = Path.cwd()

    pyproject_path = project_root / "pyproject.toml"
    if not pyproject_path.exists():
        raise DriftDetectionError(f"pyproject.toml not found at {pyproject_path}")

    # Load expected versions from pyproject.toml
    try:
        with open(pyproject_path, "rb") as f:
            pyproject = tomllib.load(f)
    except Exception as exc:
        raise DriftDetectionError(f"Failed to parse pyproject.toml: {exc}") from exc

    dev_deps = pyproject.get("project", {}).get("optional-dependencies", {}).get("dev", [])

    tools = {
        "ruff": _extract_version_spec(dev_deps, "ruff"),
        "black": _extract_version_spec(dev_deps, "black"),
        "mypy": _extract_version_spec(dev_deps, "mypy"),
        "pip-audit": _extract_version_spec(dev_deps, "pip-audit"),
    }

    results: list[ToolVersion] = []

    for tool_name, expected_version in tools.items():
        actual_version = _get_installed_version(tool_name)
        results.append(
            ToolVersion(
                name=tool_name,
                expected=expected_version,
                actual=actual_version,
            )
        )

    return results


def _extract_version_spec(deps: list[str], package_name: str) -> str | None:
    """Extract version specification from dependency list."""
    for dep in deps:
        # Handle various formats: "pkg>=1.0", "pkg[extra]>=1.0", etc.
        match = re.match(rf"{package_name}(\[.*?\])?>=([0-9.]+)", dep)
        if match:
            return match.group(2)
    return None


def _get_installed_version(tool_name: str) -> str | None:
    """Get installed version of a tool."""
    try:
        # Try to get version via --version flag
        result = subprocess.run(
            [tool_name, "--version"],
            capture_output=True,
            text=True,
            timeout=5,
            check=False,
        )

        if result.returncode != 0:
            return None

        # Extract version from output
        output = result.stdout + result.stderr
        version_match = re.search(r"(\d+\.\d+\.\d+)", output)
        if version_match:
            return version_match.group(1)

        return None
    except (FileNotFoundError, subprocess.TimeoutExpired):
        return None


def generate_remediation_commands(drifted: list[ToolVersion]) -> list[str]:
    """Generate commands to fix version drift.

    Args:
        drifted: List of tools with version drift

    Returns:
        List of shell commands to remediate drift
    """
    commands: list[str] = []

    for tool in drifted:
        if tool.is_missing:
            # Tool not installed
            if tool.expected:
                commands.append(f"pip install {tool.name}>={tool.expected}")
            else:
                commands.append(f"pip install {tool.name}")
        elif tool.has_drift:
            # Version mismatch
            if tool.expected:
                commands.append(f"pip install --upgrade {tool.name}>={tool.expected}")
            else:
                commands.append(f"pip install --upgrade {tool.name}")

    # If using uv, suggest uv sync instead
    if commands and Path("uv.lock").exists():
        return [
            "# Recommended: Use uv to sync dependencies",
            "uv sync --extra dev --extra qa",
            "",
            "# Or manually update individual tools:",
        ] + commands

    return commands
