"""CLI smoke tests for the Hephaestus toolkit."""

from __future__ import annotations

import sys
from importlib import import_module
from pathlib import Path
from types import ModuleType

from typer.testing import CliRunner

ROOT = Path(__file__).resolve().parents[1]
SRC = ROOT / "src"
if str(SRC) not in sys.path:
    sys.path.insert(0, str(SRC))

runner = CliRunner()


def _load_modules() -> tuple[ModuleType, ModuleType]:
    toolkit = import_module("hephaestus")
    cli = import_module("hephaestus.cli")
    return toolkit, cli


def test_version_command_displays_version() -> None:
    toolkit, cli = _load_modules()
    result = runner.invoke(cli.app, ["version"])
    assert result.exit_code == 0
    assert toolkit.__version__ in result.stdout


def test_hotspots_command_uses_default_config() -> None:
    _, cli = _load_modules()
    result = runner.invoke(cli.app, ["tools", "refactor", "hotspots", "--limit", "2"])
    assert result.exit_code == 0
    assert "Refactor Hotspots" in result.stdout


def test_qa_profile_command_lists_profile_data() -> None:
    _, cli = _load_modules()
    result = runner.invoke(cli.app, ["tools", "qa", "profile", "quick"])
    assert result.exit_code == 0
    assert "QA Profile: quick" in result.stdout


def test_plan_command_renders_execution_plan() -> None:
    _, cli = _load_modules()
    result = runner.invoke(cli.app, ["plan"])
    assert result.exit_code == 0
    assert "Execution Plan" in result.stdout
    assert "Gather Evidence" in result.stdout


def test_qa_coverage_command_displays_gaps() -> None:
    _, cli = _load_modules()
    result = runner.invoke(cli.app, ["tools", "qa", "coverage"])
    assert result.exit_code == 0
    assert "Coverage Gaps" in result.stdout
    assert "Uncovered Lines" in result.stdout
