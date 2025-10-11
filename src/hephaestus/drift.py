"""Tool version drift detection for guard rails."""

from __future__ import annotations

import logging
import os
import re
import subprocess
import tomllib
from dataclasses import dataclass
from pathlib import Path

logger = logging.getLogger(__name__)


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


@dataclass(slots=True)
class RemediationResult:
    """Result of executing a remediation command."""

    command: str
    exit_code: int
    stdout: str
    stderr: str


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
        logger.error("pyproject.toml not found", extra={"path": str(pyproject_path)})
        raise DriftDetectionError(f"pyproject.toml not found at {pyproject_path}")

    logger.debug("Loading pyproject.toml", extra={"path": str(pyproject_path)})

    # Load expected versions from pyproject.toml
    try:
        with open(pyproject_path, "rb") as f:
            pyproject = tomllib.load(f)
    except Exception as exc:
        logger.error(
            "Failed to parse pyproject.toml", extra={"path": str(pyproject_path), "error": str(exc)}
        )
        raise DriftDetectionError(f"Failed to parse pyproject.toml: {exc}") from exc

    dev_deps = pyproject.get("project", {}).get("optional-dependencies", {}).get("dev", [])

    tools = {
        "ruff": _extract_version_spec(dev_deps, "ruff"),
        "black": _extract_version_spec(dev_deps, "black"),
        "mypy": _extract_version_spec(dev_deps, "mypy"),
        "pip-audit": _extract_version_spec(dev_deps, "pip-audit"),
    }

    logger.info("Checking tool versions", extra={"tools": list(tools.keys())})

    results: list[ToolVersion] = []

    for tool_name, expected_version in tools.items():
        actual_version = _get_installed_version(tool_name)
        tool_version = ToolVersion(
            name=tool_name,
            expected=expected_version,
            actual=actual_version,
        )
        results.append(tool_version)

        if tool_version.is_missing:
            logger.warning("Tool not installed", extra={"tool": tool_name})
        elif tool_version.has_drift:
            logger.warning(
                "Tool version drift detected",
                extra={
                    "tool": tool_name,
                    "expected": expected_version,
                    "actual": actual_version,
                },
            )
        else:
            logger.debug(
                "Tool version OK",
                extra={
                    "tool": tool_name,
                    "expected": expected_version,
                    "actual": actual_version,
                },
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
        logger.debug("Checking installed version", extra={"tool": tool_name})
        # Try to get version via --version flag
        result = subprocess.run(
            [tool_name, "--version"],
            capture_output=True,
            text=True,
            timeout=5,
            check=False,
        )

        if result.returncode != 0:
            logger.debug(
                "Tool version check failed",
                extra={"tool": tool_name, "returncode": result.returncode},
            )
            return None

        # Extract version from output
        output = result.stdout + result.stderr
        version_match = re.search(r"(\d+\.\d+\.\d+)", output)
        if version_match:
            version = version_match.group(1)
            logger.debug("Found tool version", extra={"tool": tool_name, "version": version})
            return version

        logger.debug("Could not extract version", extra={"tool": tool_name, "output": output[:100]})
        return None
    except FileNotFoundError:
        logger.debug("Tool not found", extra={"tool": tool_name})
        return None
    except subprocess.TimeoutExpired:
        logger.warning("Tool version check timed out", extra={"tool": tool_name})
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


def apply_remediation_commands(
    commands: list[str], *, env: dict[str, str] | None = None
) -> list[RemediationResult]:
    """Execute remediation commands and return their results."""

    results: list[RemediationResult] = []

    for command in commands:
        if not command.strip() or command.strip().startswith("#"):
            continue

        logger.info("Applying remediation command", extra={"command": command})
        merged_env = os.environ.copy()
        if env:
            merged_env.update(env)

        result = subprocess.run(  # noqa: S602 - commands are generated by Hephaestus
            command,
            shell=True,
            capture_output=True,
            text=True,
            check=False,
            env=merged_env,
        )

        results.append(
            RemediationResult(
                command=command,
                exit_code=result.returncode,
                stdout=result.stdout,
                stderr=result.stderr,
            )
        )

        if result.returncode != 0:
            logger.warning(
                "Remediation command failed",
                extra={"command": command, "exit_code": result.returncode},
            )

    return results
