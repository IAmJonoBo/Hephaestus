"""E2E tests for development environment setup and workflows."""

from __future__ import annotations

import subprocess
from pathlib import Path

import pytest


def test_setup_dev_env_script_exists() -> None:
    """Verify setup-dev-env.sh script exists and is executable."""
    script = Path("scripts/setup-dev-env.sh")
    assert script.exists(), "setup-dev-env.sh script should exist"
    assert script.stat().st_mode & 0o111, "setup-dev-env.sh should be executable"


def test_setup_dev_env_script_syntax() -> None:
    """Verify setup-dev-env.sh has valid bash syntax."""
    result = subprocess.run(
        ["bash", "-n", "scripts/setup-dev-env.sh"],
        capture_output=True,
        text=True,
        timeout=10,
    )
    assert result.returncode == 0, f"setup-dev-env.sh has syntax errors: {result.stderr}"


def test_guard_rails_preserves_site_packages(tmp_path: Path) -> None:
    """Regression test: guard-rails cleanup should preserve site-packages in .venv."""
    from hephaestus.cleanup import CleanupOptions, run_cleanup

    # Create a fake repo with .venv structure
    repo_root = tmp_path / "test-repo"
    repo_root.mkdir()

    venv_path = repo_root / ".venv"
    site_packages = venv_path / "lib" / "python3.12" / "site-packages"
    site_packages.mkdir(parents=True)

    # Add a fake package in site-packages
    fake_package = site_packages / "pytest"
    fake_package.mkdir()
    (fake_package / "__init__.py").write_text("# pytest stub", encoding="utf-8")

    # Add __pycache__ directories that should be removed
    pycache1 = repo_root / "__pycache__"
    pycache1.mkdir()
    (pycache1 / "test.pyc").write_bytes(b"\x00\x00")

    pycache2 = site_packages / "__pycache__"
    pycache2.mkdir()
    (pycache2 / "module.pyc").write_bytes(b"\x00\x00")

    # Run cleanup with deep_clean (as guard-rails does)
    options = CleanupOptions(root=repo_root, deep_clean=True)
    run_cleanup(options)

    # Verify __pycache__ directories were removed
    assert not pycache1.exists(), "Root __pycache__ should be removed"
    assert not pycache2.exists(), "site-packages __pycache__ should be removed"

    # Verify site-packages directory itself was preserved
    assert site_packages.exists(), "site-packages directory must be preserved"
    assert fake_package.exists(), "Packages in site-packages must be preserved"
    assert (fake_package / "__init__.py").exists(), "Package files must be preserved"


def test_cleanup_with_venv_in_search_roots(tmp_path: Path) -> None:
    """Test cleanup when .venv is explicitly added as a search root (include_poetry_env=True)."""
    from hephaestus.cleanup import CleanupOptions, gather_search_roots, run_cleanup

    # Create a fake repo with .venv structure
    repo_root = tmp_path / "test-repo"
    repo_root.mkdir()

    venv_path = repo_root / ".venv"
    site_packages = venv_path / "lib" / "python3.12" / "site-packages"
    site_packages.mkdir(parents=True)

    # Add content in site-packages
    fake_lib = site_packages / "mylib"
    fake_lib.mkdir()
    (fake_lib / "core.py").write_text("def main(): pass", encoding="utf-8")

    # Add __pycache__ that should be removed
    pycache = site_packages / "__pycache__"
    pycache.mkdir()

    # Create options with include_poetry_env (which adds .venv to search roots)
    options = CleanupOptions(root=repo_root, include_poetry_env=True, python_cache=True)
    normalized = options.normalize()

    # Verify .venv is in search roots
    search_roots = gather_search_roots(normalized)
    assert venv_path in search_roots, ".venv should be in search roots when include_poetry_env=True"

    # Run cleanup
    run_cleanup(options)

    # Verify __pycache__ was removed but site-packages and its contents preserved
    assert not pycache.exists(), "__pycache__ should be removed"
    assert site_packages.exists(), "site-packages must be preserved"
    assert fake_lib.exists(), "Library in site-packages must be preserved"
    assert (fake_lib / "core.py").exists(), "Library files must be preserved"


@pytest.mark.skipif(
    not Path(".venv/bin/yamllint").exists() and not Path(".venv/Scripts/yamllint.exe").exists(),
    reason="yamllint not installed in .venv",
)
def test_guard_rails_yamllint_works() -> None:
    """Verify yamllint can run after cleanup (site-packages preserved)."""
    # Run a simple yamllint check to verify it's functional
    result = subprocess.run(
        ["yamllint", "--version"],
        capture_output=True,
        text=True,
        timeout=10,
    )
    assert result.returncode == 0, f"yamllint should work after cleanup: {result.stderr}"
    assert "yamllint" in result.stdout.lower(), "yamllint should report its version"


def test_renovate_config_exists() -> None:
    """Verify Renovate configuration exists for automated dependency updates."""
    renovate_config = Path("renovate.json")
    assert renovate_config.exists(), "renovate.json should exist for dependency automation"

    # Verify it's valid JSON
    import json

    with open(renovate_config, encoding="utf-8") as f:
        config = json.load(f)

    # Verify key Renovate settings
    assert "$schema" in config, "renovate.json should have $schema"
    assert "extends" in config, "renovate.json should have extends"
    assert "packageRules" in config, "renovate.json should have packageRules"


def test_uv_lock_exists_for_renovate() -> None:
    """Verify uv.lock exists so Renovate can update Python dependencies."""
    uv_lock = Path("uv.lock")
    assert uv_lock.exists(), "uv.lock should exist for Renovate to manage Python dependencies"

    # Verify it's not empty
    assert uv_lock.stat().st_size > 0, "uv.lock should not be empty"


def test_setup_script_handles_dependency_updates() -> None:
    """Test that setup-dev-env.sh can handle dependency updates (like Renovate PRs)."""
    # The setup script should use uv sync --locked which will work with updated uv.lock
    script = Path("scripts/setup-dev-env.sh")
    with open(script, encoding="utf-8") as f:
        content = f.read()

    # Verify the script uses locked sync for reproducible builds
    assert "uv sync --locked" in content, "setup script should use --locked for reproducibility"

    # Verify fallback for when lock is out of sync (after Renovate updates)
    assert (
        "uv sync --extra dev --extra qa" in content
    ), "setup script should have fallback without --locked"
