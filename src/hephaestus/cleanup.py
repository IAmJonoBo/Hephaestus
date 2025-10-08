"""Workspace cleanup helpers that scrub macOS metadata and development cruft."""

from __future__ import annotations

import fnmatch
import json
import logging
import os
import platform
import shutil
import subprocess
from collections.abc import Callable, Iterable, Iterator
from dataclasses import dataclass, field
from datetime import UTC, datetime
from pathlib import Path

from hephaestus import telemetry
from hephaestus.logging import log_context

__all__ = [
    "CleanupOptions",
    "CleanupResult",
    "gather_search_roots",
    "run_cleanup",
    "resolve_root",
    "is_dangerous_path",
]

GIT_DIR = ".git"
VENV_DIR = ".venv"
NODE_MODULES_DIR = "node_modules"
SITE_PACKAGES_DIR = "site-packages"

RemovalCallback = Callable[[Path], None]
SkipCallback = Callable[[Path, str], None]


logger = logging.getLogger(__name__)


@dataclass(slots=True, frozen=True)
class CleanupOptions:
    """User-provided cleanup configuration.

    The options mirror the flags exposed by the shell script bundled with the toolkit
    and can be combined freely. Use ``deep_clean`` to enable all optional behaviours.
    """

    root: Path | None = None
    include_git: bool = False
    include_poetry_env: bool = False
    python_cache: bool = False
    build_artifacts: bool = False
    node_modules: bool = False
    deep_clean: bool = False
    extra_paths: tuple[Path, ...] = field(default_factory=tuple)
    dry_run: bool = False
    audit_manifest: Path | None = None

    def normalize(self) -> NormalizedCleanupOptions:
        """Return a normalised set of options with defaults applied."""

        root = resolve_root(self.root)
        include_git = self.include_git or self.deep_clean
        include_poetry_env = self.include_poetry_env or self.deep_clean
        python_cache = self.python_cache or self.deep_clean
        build_artifacts = self.build_artifacts or self.deep_clean
        node_modules = self.node_modules or self.deep_clean

        # Validate and resolve extra paths
        validated_paths: list[Path] = []
        for path in self.extra_paths:
            resolved_path = Path(path).resolve()
            if is_dangerous_path(resolved_path):
                raise ValueError(
                    f"Refusing to include dangerous path in cleanup: {resolved_path}. "
                    "Dangerous paths include system directories like /, /home, /usr, /etc, and your home directory."
                )
            validated_paths.append(resolved_path)

        audit_manifest: Path | None = None
        if self.audit_manifest is not None:
            candidate = Path(self.audit_manifest)
            if not candidate.is_absolute():
                candidate = (root / candidate).resolve()
            audit_manifest = candidate

        return NormalizedCleanupOptions(
            root=root,
            include_git=include_git,
            include_poetry_env=include_poetry_env,
            python_cache=python_cache,
            build_artifacts=build_artifacts,
            node_modules=node_modules,
            extra_paths=tuple(validated_paths),
            dry_run=self.dry_run,
            audit_manifest=audit_manifest,
        )


@dataclass(slots=True, frozen=True)
class NormalizedCleanupOptions:
    """Concrete options with defaults resolved."""

    root: Path
    include_git: bool
    include_poetry_env: bool
    python_cache: bool
    build_artifacts: bool
    node_modules: bool
    extra_paths: tuple[Path, ...] = field(default_factory=tuple)
    dry_run: bool = False
    audit_manifest: Path | None = None


@dataclass(slots=True)
class CleanupResult:
    """Summary of cleanup execution."""

    search_roots: list[Path] = field(default_factory=list)
    removed_paths: list[Path] = field(default_factory=list)
    preview_paths: list[Path] = field(default_factory=list)
    skipped_roots: list[tuple[Path, str]] = field(default_factory=list)
    errors: list[tuple[Path, str]] = field(default_factory=list)
    audit_manifest: Path | None = None

    def record_removal(
        self,
        path: Path,
        callback: RemovalCallback | None,
        *,
        dry_run: bool,
    ) -> None:
        if dry_run:
            self.preview_paths.append(path)
            message = f"Would remove {path}"
        else:
            self.removed_paths.append(path)
            message = f"Removed {path}"
        if callback:
            callback(path)
        event = telemetry.CLEANUP_PATH_PREVIEW if dry_run else telemetry.CLEANUP_PATH_REMOVED
        telemetry.emit_event(
            logger,
            event,
            message=message,
            path=str(path),
            dry_run=dry_run,
        )

    def record_skip(self, path: Path, reason: str, callback: SkipCallback | None) -> None:
        self.skipped_roots.append((path, reason))
        if callback:
            callback(path, reason)
        telemetry.emit_event(
            logger,
            telemetry.CLEANUP_PATH_SKIPPED,
            message=f"Skipped {path}",
            path=str(path),
            reason=reason,
        )

    def record_error(self, path: Path, message: str) -> None:
        self.errors.append((path, message))
        telemetry.emit_event(
            logger,
            telemetry.CLEANUP_PATH_ERROR,
            level=logging.ERROR,
            message=f"Cleanup error for {path}: {message}",
            path=str(path),
            reason=message,
        )


MACOS_PATTERNS: tuple[str, ...] = (
    ".DS_Store",
    "._*",
    ".AppleDouble",
    ".AppleDesktop",
    ".AppleDB",
    "Icon?",
    "__MACOSX",
    ".DocumentRevisions-V100",
    ".Spotlight-V100",
    ".Trashes",
    ".fseventsd",
    ".TemporaryItems",
    ".LSOverride",
    ".apdisk",
)

PYTHON_CACHE_DIRS: tuple[str, ...] = ("__pycache__",)
PYTHON_CACHE_FILES: tuple[str, ...] = ("*.pyc", "*.pyo")

BUILD_ARTIFACT_PATTERNS: tuple[str, ...] = (
    "*.egg-info",
    "*.tsbuildinfo",
    "build",
    "dist",
    ".tox",
    ".pytest_cache",
    ".coverage",
    "coverage.xml",
    ".mypy_cache",
    ".ruff_cache",
    "htmlcov",
    "*.whl",
    ".trunk",
    SITE_PACKAGES_DIR,
    ".turbo",
    ".parcel-cache",
    ".rollup.cache",
    ".nyc_output",
    ".eslintcache",
    "*.tmp",
    "*.temp",
    "*~",
)

IPYNB_CHECKPOINT_DIR = ".ipynb_checkpoints"

# Dangerous paths that should never be cleaned
DANGEROUS_PATHS: tuple[str, ...] = (
    "/",
    "/home",
    "/usr",
    "/etc",
    "/var",
    "/bin",
    "/sbin",
    "/lib",
    "/lib64",
    "/opt",
    "/boot",
    "/root",
    "/sys",
    "/proc",
    "/dev",
)


def is_dangerous_path(path: Path) -> bool:
    """Check if a path is in the dangerous paths list."""
    original = str(path)
    if original in DANGEROUS_PATHS:
        return True

    resolved = path.resolve()
    str_path = str(resolved)

    # Check exact match
    if str_path in DANGEROUS_PATHS:
        return True

    # Check if it's home directory
    home = Path.home()
    if resolved == home:
        return True

    return False


def resolve_root(root: Path | None) -> Path:
    """Return the workspace root or the git repository root if available."""

    if root is not None:
        resolved = Path(root).resolve()

        # Safety check: refuse dangerous paths
        if is_dangerous_path(resolved):
            raise ValueError(
                f"Refusing to clean dangerous path: {resolved}. "
                "If you really need to clean this path, use a tool specifically "
                "designed for system administration."
            )

        return resolved

    try:
        completed = subprocess.run(
            ["git", "rev-parse", "--show-toplevel"],
            check=True,
            capture_output=True,
            text=True,
            timeout=10,
        )
        output = completed.stdout.strip()
        if output:
            return Path(output)
    except (subprocess.SubprocessError, FileNotFoundError, subprocess.TimeoutExpired):
        pass

    return Path.cwd().resolve()


def run_cleanup(
    options: CleanupOptions,
    *,
    on_remove: RemovalCallback | None = None,
    on_skip: SkipCallback | None = None,
) -> CleanupResult:
    """Execute cleanup with the provided options and return a summary."""

    normalized = options.normalize()
    search_roots = gather_search_roots(normalized)

    result = CleanupResult(search_roots=list(search_roots))

    with log_context(command="cleanup", root=str(normalized.root), dry_run=normalized.dry_run):
        telemetry.emit_event(
            logger,
            telemetry.CLEANUP_RUN_START,
            message="Starting cleanup sweep",
            search_roots=[str(path) for path in result.search_roots],
            include_git=normalized.include_git,
            include_poetry_env=normalized.include_poetry_env,
            python_cache=normalized.python_cache,
            build_artifacts=normalized.build_artifacts,
            node_modules=normalized.node_modules,
            extra_paths=[str(path) for path in normalized.extra_paths],
            dry_run=normalized.dry_run,
        )

        for root in search_roots:
            if not root.exists():
                result.record_skip(root, "missing", on_skip)
                continue
            with log_context(root=str(root), dry_run=normalized.dry_run):
                _cleanup_root(root, normalized, result, on_remove)

        manifest_path: Path | None = None
        if not normalized.dry_run:
            manifest_path = _write_audit_manifest(result, normalized)
            result.audit_manifest = manifest_path

        telemetry.emit_event(
            logger,
            telemetry.CLEANUP_RUN_COMPLETE,
            message="Cleanup sweep completed",
            removed=len(result.removed_paths),
            skipped=len(result.skipped_roots),
            errors=len(result.errors),
            dry_run=normalized.dry_run,
            audit_manifest=str(manifest_path) if manifest_path else None,
        )

    return result


def gather_search_roots(options: NormalizedCleanupOptions) -> list[Path]:
    """Return the ordered list of search roots for the provided options."""

    return _gather_search_roots(options)


def _gather_search_roots(options: NormalizedCleanupOptions) -> list[Path]:
    roots: list[Path] = []
    seen: set[Path] = set()

    def _add(path: Path) -> None:
        candidate = path.resolve()
        if candidate not in seen:
            seen.add(candidate)
            roots.append(candidate)

    _add(options.root)

    for extra in options.extra_paths:
        _add(extra)

    if options.include_poetry_env:
        poetry_root = _discover_poetry_environment()
        if poetry_root is not None:
            _add(poetry_root)

        venv_path = options.root / VENV_DIR
        if venv_path.exists():
            _add(venv_path)

    return roots


def _discover_poetry_environment() -> Path | None:
    try:
        completed = subprocess.run(
            ["poetry", "env", "info", "--no-ansi", "--path"],
            check=True,
            capture_output=True,
            text=True,
            timeout=10,
        )
        candidate = completed.stdout.strip()
        if candidate:
            path = Path(candidate)
            if path.exists():
                return path.resolve()
    except (subprocess.SubprocessError, FileNotFoundError, subprocess.TimeoutExpired):
        return None
    return None


def _cleanup_root(
    root: Path,
    options: NormalizedCleanupOptions,
    result: CleanupResult,
    on_remove: RemovalCallback | None,
) -> None:
    _remove_matches(
        root,
        options.include_git,
        MACOS_PATTERNS,
        result,
        on_remove,
        dry_run=options.dry_run,
    )

    if options.python_cache:
        _remove_python_cache(
            root,
            options.include_git,
            result,
            on_remove,
            dry_run=options.dry_run,
        )

    if options.build_artifacts:
        _remove_build_artifacts(
            root,
            options.include_git,
            result,
            on_remove,
            dry_run=options.dry_run,
        )

    if options.node_modules:
        _remove_directory_pattern(
            root,
            options.include_git,
            NODE_MODULES_DIR,
            result,
            on_remove,
            dry_run=options.dry_run,
        )


def _walk_workspace(root: Path, include_git: bool) -> Iterator[tuple[Path, list[str], list[str]]]:
    for current_dir, dirnames, filenames in os.walk(root, topdown=True):
        if not include_git:
            dirnames[:] = [name for name in dirnames if name != GIT_DIR]
        yield Path(current_dir), dirnames, filenames


def _remove_directory_entries(
    current: Path,
    dirnames: list[str],
    patterns: Iterable[str],
    *,
    result: CleanupResult,
    on_remove: RemovalCallback | None,
    skip: Callable[[Path], bool] | None = None,
    dry_run: bool,
) -> None:
    for name in tuple(dirnames):
        if not _matches_any(name, patterns):
            continue
        target = current / name
        if skip and skip(target):
            continue
        _remove_path(target, result, on_remove, dry_run=dry_run)
        dirnames.remove(name)


def _remove_file_entries(
    current: Path,
    filenames: list[str],
    patterns: Iterable[str],
    *,
    result: CleanupResult,
    on_remove: RemovalCallback | None,
    skip: Callable[[Path], bool] | None = None,
    dry_run: bool,
) -> None:
    for name in tuple(filenames):
        if not _matches_any(name, patterns):
            continue
        target = current / name
        if skip and skip(target):
            continue
        _remove_path(target, result, on_remove, dry_run=dry_run)
        filenames.remove(name)


def _remove_matches(
    root: Path,
    include_git: bool,
    patterns: Iterable[str],
    result: CleanupResult,
    on_remove: RemovalCallback | None,
    *,
    dry_run: bool,
) -> None:
    for current, dirnames, filenames in _walk_workspace(root, include_git):
        _remove_directory_entries(
            current,
            dirnames,
            patterns,
            result=result,
            on_remove=on_remove,
            dry_run=dry_run,
        )
        _remove_file_entries(
            current,
            filenames,
            patterns,
            result=result,
            on_remove=on_remove,
            dry_run=dry_run,
        )


def _remove_python_cache(
    root: Path,
    include_git: bool,
    result: CleanupResult,
    on_remove: RemovalCallback | None,
    *,
    dry_run: bool,
) -> None:
    for current, dirnames, filenames in _walk_workspace(root, include_git):
        _remove_directory_entries(
            current,
            dirnames,
            PYTHON_CACHE_DIRS,
            result=result,
            on_remove=on_remove,
            dry_run=dry_run,
        )
        _remove_file_entries(
            current,
            filenames,
            PYTHON_CACHE_FILES,
            result=result,
            on_remove=on_remove,
            dry_run=dry_run,
        )


def _remove_build_artifacts(
    root: Path,
    include_git: bool,
    result: CleanupResult,
    on_remove: RemovalCallback | None,
    *,
    dry_run: bool,
) -> None:
    patterns = BUILD_ARTIFACT_PATTERNS + (IPYNB_CHECKPOINT_DIR,)

    def _skip(target: Path) -> bool:
        return _should_skip_venv_site_packages(target, root)

    for current, dirnames, filenames in _walk_workspace(root, include_git):
        _remove_directory_entries(
            current,
            dirnames,
            patterns,
            result=result,
            on_remove=on_remove,
            skip=_skip,
            dry_run=dry_run,
        )
        _remove_file_entries(
            current,
            filenames,
            BUILD_ARTIFACT_PATTERNS,
            result=result,
            on_remove=on_remove,
            skip=_skip,
            dry_run=dry_run,
        )


def _remove_directory_pattern(
    root: Path,
    include_git: bool,
    directory_name: str,
    result: CleanupResult,
    on_remove: RemovalCallback | None,
    *,
    dry_run: bool,
) -> None:
    for current, dirnames, _filenames in _walk_workspace(root, include_git):
        _remove_directory_entries(
            current,
            dirnames,
            (directory_name,),
            result=result,
            on_remove=on_remove,
            dry_run=dry_run,
        )


def _matches_any(name: str, patterns: Iterable[str]) -> bool:
    return any(fnmatch.fnmatch(name, pattern) for pattern in patterns)


def _should_skip_venv_site_packages(target: Path, root: Path) -> bool:
    if SITE_PACKAGES_DIR not in target.parts:
        return False
    return VENV_DIR in target.parts and root.name != VENV_DIR and VENV_DIR not in root.parts


def _remove_path(
    path: Path,
    result: CleanupResult,
    on_remove: RemovalCallback | None,
    *,
    dry_run: bool,
) -> None:
    if dry_run:
        result.record_removal(path, on_remove, dry_run=True)
        return

    attempts = 0
    while True:
        try:
            if path.is_symlink() or path.is_file():
                path.unlink(missing_ok=True)
            else:
                shutil.rmtree(path, ignore_errors=False)
        except FileNotFoundError:
            return
        except PermissionError as exc:  # pragma: no cover - unlikely in tmp based tests
            if attempts == 0 and _unlock_path(path):
                attempts += 1
                continue
            result.record_error(path, f"permission denied: {exc}")
            return
        break

    result.record_removal(path, on_remove, dry_run=False)


def _unlock_path(path: Path) -> bool:
    if platform.system() != "Darwin":
        return False

    unlocked = False

    try:
        completed = subprocess.run(
            ["chflags", "-R", "nouchg,noschg", str(path)],
            check=False,
            stdout=subprocess.DEVNULL,
            stderr=subprocess.DEVNULL,
            timeout=30,
        )
        unlocked = unlocked or completed.returncode == 0
    except FileNotFoundError:  # pragma: no cover - chflags missing on non-macOS platforms
        return False
    except subprocess.TimeoutExpired:  # pragma: no cover - defensive timeout
        return False

    try:
        subprocess.run(
            ["xattr", "-rc", str(path)],
            check=False,
            stdout=subprocess.DEVNULL,
            stderr=subprocess.DEVNULL,
            timeout=30,
        )
    except FileNotFoundError:  # pragma: no cover - xattr missing on some macOS installs
        pass
    except subprocess.TimeoutExpired:  # pragma: no cover - defensive timeout
        pass

    return unlocked


def _resolve_manifest_path(options: NormalizedCleanupOptions) -> Path:
    if options.audit_manifest is not None:
        return options.audit_manifest
    timestamp = datetime.now(UTC).strftime("%Y%m%dT%H%M%SZ")
    directory = options.root / ".hephaestus" / "audit"
    return directory / f"cleanup-{timestamp}.json"


def _write_audit_manifest(result: CleanupResult, options: NormalizedCleanupOptions) -> Path:
    manifest_path = _resolve_manifest_path(options)
    manifest_path.parent.mkdir(parents=True, exist_ok=True)

    payload = {
        "generated_at": datetime.now(UTC).isoformat(),
        "root": str(options.root),
        "include_git": options.include_git,
        "include_poetry_env": options.include_poetry_env,
        "python_cache": options.python_cache,
        "build_artifacts": options.build_artifacts,
        "node_modules": options.node_modules,
        "extra_paths": [str(path) for path in options.extra_paths],
        "removed_paths": [str(path) for path in result.removed_paths],
        "skipped_roots": [
            {"path": str(path), "reason": reason} for path, reason in result.skipped_roots
        ],
        "errors": [{"path": str(path), "reason": reason} for path, reason in result.errors],
    }

    manifest_path.write_text(json.dumps(payload, indent=2, sort_keys=True), encoding="utf-8")
    return manifest_path
