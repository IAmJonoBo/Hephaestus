"""Tests for tool version drift detection."""

from __future__ import annotations

from pathlib import Path
from unittest import mock

import pytest

from hephaestus.drift import (
    DriftDetectionError,
    ToolVersion,
    detect_drift,
    generate_remediation_commands,
)


def test_tool_version_no_drift() -> None:
    """Test that matching versions show no drift."""
    tool = ToolVersion(name="ruff", expected="0.14.0", actual="0.14.5")
    assert not tool.has_drift
    assert not tool.is_missing


def test_tool_version_has_drift() -> None:
    """Test that different versions show drift."""
    tool = ToolVersion(name="ruff", expected="0.14.0", actual="0.13.5")
    assert tool.has_drift
    assert not tool.is_missing


def test_tool_version_missing() -> None:
    """Test that missing tools are detected."""
    tool = ToolVersion(name="ruff", expected="0.14.0", actual=None)
    assert tool.is_missing
    assert not tool.has_drift  # Missing tools don't count as drift


def test_tool_version_minor_difference_ok() -> None:
    """Test that patch version differences are acceptable."""
    tool = ToolVersion(name="ruff", expected="0.14.0", actual="0.14.9")
    assert not tool.has_drift


def test_detect_drift_missing_pyproject(tmp_path: Path) -> None:
    """Test that missing pyproject.toml raises error."""
    with pytest.raises(DriftDetectionError, match="not found"):
        detect_drift(tmp_path)


def test_detect_drift_invalid_pyproject(tmp_path: Path) -> None:
    """Test that invalid pyproject.toml raises error."""
    pyproject = tmp_path / "pyproject.toml"
    pyproject.write_text("invalid toml [[", encoding="utf-8")
    
    with pytest.raises(DriftDetectionError, match="Failed to parse"):
        detect_drift(tmp_path)


def test_detect_drift_with_mock_versions(tmp_path: Path) -> None:
    """Test drift detection with mocked tool versions."""
    pyproject = tmp_path / "pyproject.toml"
    pyproject.write_text(
        """
[project]
name = "test-project"

[project.optional-dependencies]
dev = [
    "ruff>=0.14.0",
    "black>=25.9.0",
    "mypy>=1.18.0",
    "pip-audit>=2.9.0",
]
""",
        encoding="utf-8",
    )
    
    with mock.patch("hephaestus.drift._get_installed_version") as mock_version:
        # Simulate all tools installed with correct versions
        mock_version.side_effect = lambda tool: {
            "ruff": "0.14.5",
            "black": "25.9.1",
            "mypy": "1.18.2",
            "pip-audit": "2.9.0",
        }.get(tool)
        
        results = detect_drift(tmp_path)
        
        assert len(results) == 4
        assert all(not tool.has_drift for tool in results)
        assert all(not tool.is_missing for tool in results)


def test_detect_drift_with_missing_tool(tmp_path: Path) -> None:
    """Test drift detection when a tool is missing."""
    pyproject = tmp_path / "pyproject.toml"
    pyproject.write_text(
        """
[project]
name = "test-project"

[project.optional-dependencies]
dev = ["ruff>=0.14.0"]
""",
        encoding="utf-8",
    )
    
    with mock.patch("hephaestus.drift._get_installed_version") as mock_version:
        mock_version.return_value = None  # Tool not installed
        
        results = detect_drift(tmp_path)
        
        ruff = next((t for t in results if t.name == "ruff"), None)
        assert ruff is not None
        assert ruff.is_missing


def test_detect_drift_with_version_mismatch(tmp_path: Path) -> None:
    """Test drift detection with version mismatch."""
    pyproject = tmp_path / "pyproject.toml"
    pyproject.write_text(
        """
[project]
name = "test-project"

[project.optional-dependencies]
dev = ["ruff>=0.14.0"]
""",
        encoding="utf-8",
    )
    
    with mock.patch("hephaestus.drift._get_installed_version") as mock_version:
        mock_version.return_value = "0.13.0"  # Old version
        
        results = detect_drift(tmp_path)
        
        ruff = next((t for t in results if t.name == "ruff"), None)
        assert ruff is not None
        assert ruff.has_drift


def test_generate_remediation_commands_for_missing() -> None:
    """Test remediation commands for missing tools."""
    tools = [
        ToolVersion(name="ruff", expected="0.14.0", actual=None),
    ]
    
    commands = generate_remediation_commands(tools)
    
    assert any("pip install ruff>=0.14.0" in cmd for cmd in commands)


def test_generate_remediation_commands_for_drift() -> None:
    """Test remediation commands for drifted versions."""
    tools = [
        ToolVersion(name="ruff", expected="0.14.0", actual="0.13.0"),
    ]
    
    commands = generate_remediation_commands(tools)
    
    assert any("pip install --upgrade ruff>=0.14.0" in cmd for cmd in commands)


def test_generate_remediation_commands_with_uv_lock(tmp_path: Path) -> None:
    """Test that uv sync is suggested when uv.lock exists."""
    # Create a mock uv.lock
    uv_lock = tmp_path / "uv.lock"
    uv_lock.write_text("", encoding="utf-8")
    
    tools = [
        ToolVersion(name="ruff", expected="0.14.0", actual=None),
    ]
    
    with mock.patch("hephaestus.drift.Path") as mock_path:
        mock_path.return_value.exists.return_value = True
        
        commands = generate_remediation_commands(tools)
        
        assert any("uv sync" in cmd for cmd in commands)


def test_generate_remediation_commands_empty() -> None:
    """Test that no commands are generated for no drift."""
    tools = [
        ToolVersion(name="ruff", expected="0.14.0", actual="0.14.5"),
    ]
    
    commands = generate_remediation_commands(tools)
    
    # Only no-drift tools, so no pip commands
    assert not any("pip install" in cmd for cmd in commands)
