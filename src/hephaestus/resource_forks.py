"""Utilities for detecting and removing macOS resource fork artefacts.

These helpers focus on the AppleDouble files (prefixed with ``._``) and other
macOS-specific metadata that frequently appear when archives are produced or
expanded on APFS/HFS filesystems. The additional files are harmless on macOS but
can break reproducible builds and deterministic installers on other platforms as
they are not listed in wheel manifests.
"""

from __future__ import annotations

import logging
import os
import shutil
from collections.abc import Iterable, Iterator
from dataclasses import dataclass, field
from pathlib import Path

from hephaestus import events as telemetry

logger = logging.getLogger(__name__)

# AppleDouble/resource fork patterns that must never ship in wheel artefacts.
RESOURCE_FORK_PATTERNS: tuple[str, ...] = (
    "._*",
    ".DS_Store",
    "__MACOSX",
    ".AppleDouble",
    ".AppleDesktop",
    ".AppleDB",
    ".Spotlight-V100",
    ".Trashes",
    ".fseventsd",
    ".TemporaryItems",
    ".DocumentRevisions-V100",
    ".LSOverride",
    ".apdisk",
    "Icon?",
)


@dataclass(slots=True)
class SanitizationReport:
    """Summary from a resource fork sanitization run."""

    scanned_roots: list[Path] = field(default_factory=list)
    removed_paths: list[Path] = field(default_factory=list)
    preview_paths: list[Path] = field(default_factory=list)
    errors: list[tuple[Path, str]] = field(default_factory=list)

    def merge(self, other: SanitizationReport) -> SanitizationReport:
        self.scanned_roots.extend(other.scanned_roots)
        self.removed_paths.extend(other.removed_paths)
        self.preview_paths.extend(other.preview_paths)
        self.errors.extend(other.errors)
        return self


def iter_resource_forks(root: Path) -> Iterator[Path]:
    """Yield resource fork candidates below *root*.

    The iteration order is stable (sorted) and removes duplicates if a path
    matches multiple patterns. Directories are yielded after their contents so
    that recursive deletion succeeds without additional checks.
    """

    if not root.exists():
        return iter(())

    candidates: set[Path] = set()
    for pattern in RESOURCE_FORK_PATTERNS:
        for candidate in root.rglob(pattern):
            candidates.add(candidate.resolve())

    # Sort depth-first (files before directories) for safe deletion.
    ordered = sorted(
        candidates,
        key=lambda path: (path.is_dir(), len(path.as_posix())),
    )
    return iter(ordered)


def sanitize_path(root: Path, *, dry_run: bool = False) -> SanitizationReport:
    """Remove resource fork artefacts beneath *root*.

    Args:
            root: Directory to sanitise.
            dry_run: When set, do not modify the filesystem and record paths that
                    would have been removed.
    """

    os.environ.setdefault("COPYFILE_DISABLE", "1")

    search_root = root.expanduser()
    normalized_root = _resolve_for_report(search_root)
    report = SanitizationReport(scanned_roots=[normalized_root])
    if not search_root.exists():
        telemetry.emit_event(
            logger,
            telemetry.RESOURCE_FORK_SANITIZE_SKIPPED,
            message="Skip sanitisation for missing path",
            path=str(normalized_root),
        )
        return report

    for candidate in iter_resource_forks(search_root):
        if dry_run:
            report.preview_paths.append(candidate)
            telemetry.emit_event(
                logger,
                telemetry.RESOURCE_FORK_SANITIZE_PREVIEW,
                message="Would remove resource fork artefact",
                path=str(candidate),
            )
            continue

        try:
            _remove_path(candidate)
        except OSError as exc:  # pragma: no cover - hard to trigger reliably.
            report.errors.append((candidate, str(exc)))
            telemetry.emit_event(
                logger,
                telemetry.RESOURCE_FORK_SANITIZE_ERROR,
                level=logging.ERROR,
                message="Failed to remove resource fork artefact",
                path=str(candidate),
                reason=str(exc),
            )
        else:
            report.removed_paths.append(candidate)
            telemetry.emit_event(
                logger,
                telemetry.RESOURCE_FORK_SANITIZE_REMOVED,
                message="Removed resource fork artefact",
                path=str(candidate),
            )

    return report


def sanitize_many(paths: Iterable[Path], *, dry_run: bool = False) -> SanitizationReport:
    """Sanitise multiple roots and combine the results."""

    final_report = SanitizationReport()
    for root in paths:
        final_report.merge(sanitize_path(root, dry_run=dry_run))
    return final_report


def verify_clean(root: Path) -> list[Path]:
    """Return a list of resource fork artefacts that still exist beneath *root*."""

    search_root = root.expanduser()
    if not search_root.exists():
        return []
    return list(iter_resource_forks(search_root))


def _remove_path(path: Path) -> None:
    if path.is_dir():
        shutil.rmtree(path, ignore_errors=False)
    else:
        path.unlink(missing_ok=False)

    # Ensure AppleDouble extended attributes are not recreated during
    # subsequent copies on macOS. ``COPYFILE_DISABLE`` prevents ``cp`` from
    # emitting ``._`` files when the receiving filesystem lacks resource fork
    # support.
    os.environ.setdefault("COPYFILE_DISABLE", "1")


def _resolve_for_report(path: Path) -> Path:
    expanded = path.expanduser()
    try:
        return expanded.resolve()
    except FileNotFoundError:
        return expanded
