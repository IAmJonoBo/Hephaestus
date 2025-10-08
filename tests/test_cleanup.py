"""Tests for the workspace cleanup helpers."""

from __future__ import annotations

import json
from pathlib import Path

import pytest

from hephaestus.cleanup import (
    CleanupOptions,
    CleanupResult,
    _matches_any,
    _remove_path,
    _should_skip_venv_site_packages,
    gather_search_roots,
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


def test_run_cleanup_dry_run_preserves_files(sample_workspace: Path) -> None:
    cache = sample_workspace / "__pycache__"
    assert cache.exists()

    options = CleanupOptions(root=sample_workspace, python_cache=True, dry_run=True)
    result = run_cleanup(options)

    assert cache.exists()
    assert result.removed_paths == []
    preview_names = {path.name for path in result.preview_paths}
    assert "__pycache__" in preview_names


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
    roots = gather_search_roots(normalized)

    assert poetry_env.resolve() in roots
    assert (root / ".venv").resolve() in roots


def test_remove_path_handles_missing_files(tmp_path: Path) -> None:
    result = run_cleanup(CleanupOptions(root=tmp_path))
    missing = tmp_path / "missing"
    _remove_path(missing, result, None, dry_run=False)
    assert missing not in result.removed_paths


def test_remove_path_unlocks_and_retries(monkeypatch: pytest.MonkeyPatch, tmp_path: Path) -> None:
    target = tmp_path / "locked-file"
    target.write_text("data", encoding="utf-8")

    result = CleanupResult()

    original_unlink = Path.unlink
    attempts: dict[str, int] = {"count": 0}

    def fake_unlink(self: Path, *, missing_ok: bool = False) -> None:
        if self == target:
            attempts["count"] += 1
            if attempts["count"] == 1:
                raise PermissionError("locked")
        original_unlink(self, missing_ok=missing_ok)

    monkeypatch.setattr(Path, "unlink", fake_unlink)

    unlock_called: dict[str, bool] = {"value": False}

    def fake_unlock(path: Path) -> bool:
        if path == target:
            unlock_called["value"] = True
            return True
        return False

    monkeypatch.setattr("hephaestus.cleanup._unlock_path", fake_unlock)

    _remove_path(target, result, None, dry_run=False)

    assert unlock_called["value"] is True
    assert attempts["count"] == 2
    assert not target.exists()
    assert target in result.removed_paths


def test_remove_path_records_error_when_unlock_fails(
    monkeypatch: pytest.MonkeyPatch, tmp_path: Path
) -> None:
    target = tmp_path / "locked-file"
    target.write_text("data", encoding="utf-8")

    result = CleanupResult()

    original_unlink = Path.unlink

    def always_locked(self: Path, *, missing_ok: bool = False) -> None:
        if self == target:
            raise PermissionError("locked")
        original_unlink(self, missing_ok=missing_ok)

    monkeypatch.setattr(Path, "unlink", always_locked)
    monkeypatch.setattr("hephaestus.cleanup._unlock_path", lambda _path: False)

    _remove_path(target, result, None, dry_run=False)

    assert target.exists()
    assert any(entry[0] == target for entry in result.errors)


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


def test_run_cleanup_writes_audit_manifest(tmp_path: Path) -> None:
    root = tmp_path / "workspace"
    root.mkdir()
    target = root / ".DS_Store"
    target.write_text("metadata", encoding="utf-8")

    manifest = tmp_path / "audit.json"

    result = run_cleanup(CleanupOptions(root=root, audit_manifest=manifest))

    assert not target.exists()
    assert manifest.exists()
    assert result.errors == []

    payload = json.loads(manifest.read_text(encoding="utf-8"))
    assert payload["root"] == str(root)
    assert str(target) in payload["removed_paths"]
    assert payload["errors"] == []
    assert payload["skipped_roots"] == []


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


def test_extra_paths_validation_refuses_dangerous_paths(tmp_path: Path) -> None:
    """Test that extra_paths are validated against dangerous paths during normalization."""
    # Create a safe root directory
    safe_root = tmp_path / "safe_project"
    safe_root.mkdir()

    # Attempt to add dangerous path as extra_path should raise ValueError
    with pytest.raises(ValueError, match="Refusing to include dangerous path"):
        options = CleanupOptions(root=safe_root, extra_paths=(Path("/"),))
        options.normalize()

    with pytest.raises(ValueError, match="Refusing to include dangerous path"):
        options = CleanupOptions(root=safe_root, extra_paths=(Path("/usr"),))
        options.normalize()

    with pytest.raises(ValueError, match="Refusing to include dangerous path"):
        options = CleanupOptions(root=safe_root, extra_paths=(Path.home(),))
        options.normalize()

    # Safe extra_paths should work fine
    safe_extra = tmp_path / "safe_extra"
    safe_extra.mkdir()
    options = CleanupOptions(root=safe_root, extra_paths=(safe_extra,))
    normalized = options.normalize()
    assert safe_extra.resolve() in normalized.extra_paths
