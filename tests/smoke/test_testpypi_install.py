"""Smoke test for installing from Test PyPI via the Hephaestus CLI.

The test is skipped by default and is only exercised when the
``HEPHAESTUS_TESTPYPI_SMOKE`` environment variable is set. This allows the
release workflow to opt-in while keeping local development runs fast and
offline-friendly.
"""

from __future__ import annotations

import os
import subprocess
import sys
import venv
from pathlib import Path

import pytest

PROJECT_ROOT = Path(__file__).resolve().parents[2]
SRC = PROJECT_ROOT / "src"
TEST_ENV_FLAG = "HEPHAESTUS_TESTPYPI_SMOKE"
VERSION_ENV = "HEPHAESTUS_TESTPYPI_VERSION"

pytestmark = pytest.mark.skipif(
    not os.getenv(TEST_ENV_FLAG),
    reason="Test PyPI smoke test only runs when HEPHAESTUS_TESTPYPI_SMOKE is set.",
)


def _python_in_venv(venv_dir: Path) -> Path:
    if os.name == "nt":  # pragma: no cover - Windows path handling
        return venv_dir / "Scripts" / "python.exe"
    return venv_dir / "bin" / "python"


def test_release_install_from_test_pypi(tmp_path: Path) -> None:
    """Install the published package into an isolated virtual environment."""

    version = os.getenv(VERSION_ENV)
    cache_dir = tmp_path / "wheel-cache"
    cache_dir.mkdir()

    venv_dir = tmp_path / "venv"
    builder = venv.EnvBuilder(with_pip=True, clear=True)
    builder.create(venv_dir)
    venv_python = _python_in_venv(venv_dir)

    env = os.environ.copy()
    env.setdefault("PYTHONPATH", str(SRC))
    env["HEPHAESTUS_RELEASE_CACHE"] = str(cache_dir)

    cli_cmd = [
        sys.executable,
        "-m",
        "hephaestus.cli",
        "release",
        "install",
        "--source",
        "test-pypi",
        "--python",
        str(venv_python),
        "--pip-arg",
        "--no-cache-dir",
        "--no-upgrade",
    ]
    if version:
        cli_cmd.extend(["--tag", version])

    subprocess.check_call(cli_cmd, env=env)

    version_check = subprocess.check_output(
        [venv_python, "-m", "hephaestus", "--version"],
        env=env,
        text=True,
    ).strip()

    if version:
        expected = version.lstrip("v")
        assert expected in version_check
    else:
        assert "Hephaestus" in version_check


if __name__ == "__main__":  # pragma: no cover - manual invocation hook
    pytest.main([__file__])
