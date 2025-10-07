"""Tests for the workspace cleanup helpers."""

from __future__ import annotations

from pathlib import Path

import pytest

from hephaestus.cleanup import (
    CleanupOptions,
    _gather_search_roots,
    _matches_any,
    _remove_path,
    _should_skip_venv_site_packages,
    run_cleanup,
)


@pytest.fixture()
def sample_workspace(tmp_path: Path) -> Path:
    root = tmp_path / "workspace"
    root.mkdir()

    (root / ".DS_Store").write_text("metadata", encoding="utf-8")
    (root / "._icon").write_text("hfsp", encoding="utf-8")
    (root / ".AppleDesktop").mkdir()
    (root / ".DocumentRevisions-V100").mkdir()
    (root / ".apdisk").write_text("disk", encoding="utf-8")

    pycache = root / "__pycache__"
    pycache.mkdir()
    (pycache / "module.cpython-312.pyc").write_bytes(b"\x00\x00")

    (root / "coverage.xml").write_text("<coverage></coverage>", encoding="utf-8")

    return root


def test_run_cleanup_removes_macos_cruft(sample_workspace: Path) -> None:
    options = CleanupOptions(root=sample_workspace)
    result = run_cleanup(options)

    assert not (sample_workspace / ".DS_Store").exists()
    assert not (sample_workspace / "._icon").exists()
    assert not (sample_workspace / ".AppleDesktop").exists()
    assert not (sample_workspace / ".DocumentRevisions-V100").exists()
    assert not (sample_workspace / ".apdisk").exists()
    assert any(path.name == ".DS_Store" for path in result.removed_paths)
    assert sample_workspace.resolve() in result.search_roots


def test_run_cleanup_removes_python_cache(sample_workspace: Path) -> None:
    options = CleanupOptions(root=sample_workspace, python_cache=True)
    result = run_cleanup(options)

    assert not (sample_workspace / "__pycache__").exists()
    assert any(path.name == "__pycache__" for path in result.removed_paths)


def test_run_cleanup_records_missing_extra_paths(sample_workspace: Path, tmp_path: Path) -> None:
    missing = tmp_path / "missing"
    options = CleanupOptions(root=sample_workspace, extra_paths=(missing,))
    result = run_cleanup(options)

    expected = (missing.resolve(), "missing")
    assert expected in result.skipped_roots


def test_deep_clean_enables_all_flags(sample_workspace: Path) -> None:
    options = CleanupOptions(root=sample_workspace, deep_clean=True)
    normalized = options.normalize()

    assert normalized.python_cache
    assert normalized.build_artifacts
    assert normalized.node_modules
    assert normalized.include_git
    assert normalized.include_poetry_env


def test_gather_search_roots_includes_virtualenv(
    monkeypatch: pytest.MonkeyPatch, tmp_path: Path
) -> None:
    root = tmp_path / "repo"
    root.mkdir()
    (root / ".venv").mkdir()
    poetry_env = tmp_path / "poetry-env"
    poetry_env.mkdir()

    def _fake_poetry_env() -> Path:
        return poetry_env

    monkeypatch.setattr(
        "hephaestus.cleanup._discover_poetry_environment", lambda: _fake_poetry_env()
    )

    options = CleanupOptions(root=root, include_poetry_env=True)
    normalized = options.normalize()
    roots = _gather_search_roots(normalized)

    assert poetry_env.resolve() in roots
    assert (root / ".venv").resolve() in roots


def test_remove_path_handles_missing_files(tmp_path: Path) -> None:
    result = run_cleanup(CleanupOptions(root=tmp_path))
    missing = tmp_path / "missing"
    _remove_path(missing, result, None)
    assert missing not in result.removed_paths


def test_matches_any_supports_glob_patterns() -> None:
    assert _matches_any("example.tmp", ["*.tmp"])
    assert not _matches_any("example.txt", ["*.tmp"])


def test_should_skip_venv_site_packages(tmp_path: Path) -> None:
    root = tmp_path / "repo"
    root.mkdir()
    site_packages = root / ".venv" / "lib" / "python3.12" / "site-packages"
    site_packages.mkdir(parents=True)

    skip = _should_skip_venv_site_packages(site_packages, root)
    assert skip is True

    other_dir = root / "build"
    other_dir.mkdir()
    assert _should_skip_venv_site_packages(other_dir, root) is False


def test_run_cleanup_removes_extended_build_artifacts(tmp_path: Path) -> None:
    root = tmp_path / "build-target"
    root.mkdir()

    cache_dirs = [
        root / ".turbo",
        root / ".parcel-cache",
        root / ".rollup.cache",
        root / ".nyc_output",
    ]
    for cache_dir in cache_dirs:
        cache_dir.mkdir()

    eslint_cache = root / ".eslintcache"
    eslint_cache.write_text("lint", encoding="utf-8")

    tsbuild = root / "app.tsbuildinfo"
    tsbuild.write_text("tsc", encoding="utf-8")

    site_packages = root / ".venv" / "lib" / "python3.12" / "site-packages"
    site_packages.mkdir(parents=True)
    sentinel = site_packages / "keep.txt"
    sentinel.write_text("keep", encoding="utf-8")

    result = run_cleanup(CleanupOptions(root=root, build_artifacts=True))

    for cache_dir in cache_dirs:
        assert not cache_dir.exists()
    assert not eslint_cache.exists()
    assert not tsbuild.exists()

    assert site_packages.exists()
    assert sentinel.exists()

    removed_names = {path.name for path in result.removed_paths}
    expected = {
        ".turbo",
        ".parcel-cache",
        ".rollup.cache",
        ".nyc_output",
        ".eslintcache",
        "app.tsbuildinfo",
    }
    assert expected.issubset(removed_names)


def test_dangerous_path_detection() -> None:
    """Test that dangerous paths are correctly identified."""
    from hephaestus.cleanup import is_dangerous_path

    assert is_dangerous_path(Path("/"))
    assert is_dangerous_path(Path("/home"))
    assert is_dangerous_path(Path("/usr"))
    assert is_dangerous_path(Path("/etc"))
    assert is_dangerous_path(Path.home())

    # Safe paths should not be flagged
    assert not is_dangerous_path(Path("/home/user/project"))
    assert not is_dangerous_path(Path.cwd())


def test_resolve_root_refuses_dangerous_paths() -> None:
    """Test that resolve_root refuses to clean dangerous paths."""
    from hephaestus.cleanup import resolve_root

    with pytest.raises(ValueError, match="Refusing to clean dangerous path"):
        resolve_root(Path("/"))

    with pytest.raises(ValueError, match="Refusing to clean dangerous path"):
        resolve_root(Path("/usr"))

    with pytest.raises(ValueError, match="Refusing to clean dangerous path"):
        resolve_root(Path.home())
