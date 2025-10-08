"""Tests for macOS resource fork sanitation helpers."""

from __future__ import annotations

from pathlib import Path

from hephaestus import resource_forks


def test_sanitize_path_removes_known_patterns(tmp_path: Path) -> None:
    root = tmp_path / "payload"
    root.mkdir()

    artefacts = [
        root / ".DS_Store",
        root / "._shadow",
        root / "IconX",
    ]
    for path in artefacts:
        path.write_text("junk", encoding="utf-8")

    macos_dir = root / "__MACOSX"
    macos_dir.mkdir()
    (macos_dir / "._extra").write_text("junk", encoding="utf-8")

    report = resource_forks.sanitize_path(root)

    assert not any(path.exists() for path in artefacts)
    assert not macos_dir.exists()
    assert not list(resource_forks.verify_clean(root))
    removed = {candidate.name for candidate in report.removed_paths}
    assert removed.issuperset({".DS_Store", "._shadow", "IconX", "__MACOSX"})


def test_sanitize_path_dry_run_preserves_files(tmp_path: Path) -> None:
    root = tmp_path / "workspace"
    root.mkdir()
    target = root / ".DS_Store"
    target.write_text("metadata", encoding="utf-8")

    report = resource_forks.sanitize_path(root, dry_run=True)

    assert target.exists()
    assert target in report.preview_paths
    assert not report.removed_paths


def test_verify_clean_lists_remaining_artefacts(tmp_path: Path) -> None:
    root = tmp_path / "repo"
    root.mkdir()
    target = root / ".DS_Store"
    target.write_text("metadata", encoding="utf-8")

    findings = resource_forks.verify_clean(root)

    assert findings == [target]


def test_sanitize_path_skips_missing_root(tmp_path: Path) -> None:
    missing = tmp_path / "missing"
    report = resource_forks.sanitize_path(missing)
    assert report.removed_paths == []
    assert report.preview_paths == []
    assert report.errors == []
    assert missing.resolve() in report.scanned_roots


def test_sanitize_many_merges_reports(tmp_path: Path) -> None:
    root_a = tmp_path / "a"
    root_b = tmp_path / "b"
    root_a.mkdir()
    root_b.mkdir()
    (root_a / ".DS_Store").write_text("junk", encoding="utf-8")
    (root_b / "._artifact").write_text("junk", encoding="utf-8")

    report = resource_forks.sanitize_many([root_a, root_b])

    removed_names = {path.name for path in report.removed_paths}
    assert removed_names.issuperset({".DS_Store", "._artifact"})
    assert all(not list(resource_forks.verify_clean(root)) for root in (root_a, root_b))


def test_verify_clean_missing_root_returns_empty(tmp_path: Path) -> None:
    missing = tmp_path / "missing"
    assert resource_forks.verify_clean(missing) == []


def test_iter_resource_forks_missing_root(tmp_path: Path) -> None:
    missing = tmp_path / "missing"
    assert list(resource_forks.iter_resource_forks(missing)) == []
