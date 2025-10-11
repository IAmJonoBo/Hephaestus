"""Workspace cleanup commands for the Hephaestus CLI."""

from __future__ import annotations

import logging
from dataclasses import replace
from pathlib import Path
from typing import Annotated

import typer
from rich.console import Console
from rich.table import Table

from hephaestus import cleanup as cleanup_module
from hephaestus import events as telemetry
from hephaestus.telemetry import record_histogram, trace_command

console = Console()
logger = logging.getLogger(__name__)


def _is_within_root(path: Path, root: Path) -> bool:
    try:
        path.resolve().relative_to(root.resolve())
        return True
    except ValueError:
        return False


def _run_cleanup_pipeline(  # NOSONAR(S3776)
    options: cleanup_module.CleanupOptions,
    assume_yes: bool,
    dry_run: bool,
    deep_clean: bool,
) -> None:
    """Preview, confirm, execute, and summarise cleanup with telemetry."""
    import time

    # Preview
    start_time = time.perf_counter()
    normalized = options.normalize()
    search_roots = cleanup_module.gather_search_roots(normalized)

    preview_start = time.perf_counter()
    preview_result = cleanup_module.run_cleanup(
        replace(options, dry_run=True),
        on_remove=None,
        on_skip=None,
    )
    record_histogram(
        "hephaestus.cleanup.preview.duration",
        time.perf_counter() - preview_start,
        attributes={"dry_run": True},
    )

    # Show preview
    if preview_result.preview_paths:
        preview_table = Table(title="Cleanup Preview")
        preview_table.add_column("Action", style="cyan")
        preview_table.add_column("Path", style="magenta")
        for path in preview_result.preview_paths[:10]:
            preview_table.add_row("remove", str(path))
        remaining = len(preview_result.preview_paths) - min(10, len(preview_result.preview_paths))
        if remaining > 0:
            preview_table.add_row("…", f"+{remaining} more paths")
        console.print(preview_table)
    else:
        console.print("[blue]No files would be removed by cleanup.[/blue]")

    if preview_result.skipped_roots:
        skipped_table = Table(title="Skipped Roots (Preview)")
        skipped_table.add_column("Path", style="yellow")
        skipped_table.add_column("Reason", style="white")
        for path, reason in preview_result.skipped_roots:
            skipped_table.add_row(str(path), reason)
        console.print(skipped_table)

    if dry_run:
        console.print("[blue]Dry-run complete; no changes were made.[/blue]")
        return

    # Confirmation for out-of-root operations
    outside_root = [path for path in search_roots if not _is_within_root(path, normalized.root)]
    if outside_root and not assume_yes:
        warning_table = Table(title="Confirmation Required")
        warning_table.add_column("Target", style="yellow")
        for path in outside_root:
            warning_table.add_row(str(path))
        console.print(warning_table)
        console.print(
            "[red]Cleanup will touch paths outside the workspace root. Type CONFIRM to proceed.[/red]"
        )
        confirmation = typer.prompt("Confirmation", default="")
        if confirmation.strip().upper() != "CONFIRM":
            console.print("[blue]Cleanup aborted before removing any files.[/blue]")
            return

    # Execute
    removal_log: list[Path] = []

    def _on_remove(path: Path) -> None:
        removal_log.append(path)
        console.print(f"[green]- removed[/green] {path}")

    def _on_skip(path: Path, reason: str) -> None:
        console.print(f"[yellow]! skipped[/yellow] {path} ({reason})")

    cleanup_start = time.perf_counter()
    result = cleanup_module.run_cleanup(options, on_remove=_on_remove, on_skip=_on_skip)
    cleanup_duration = time.perf_counter() - cleanup_start

    record_histogram(
        "hephaestus.cleanup.execution.duration",
        cleanup_duration,
        attributes={"dry_run": False, "success": len(result.errors) == 0},
    )
    record_histogram(
        "hephaestus.cleanup.files_removed",
        len(result.removed_paths),
        attributes={"deep_clean": deep_clean},
    )

    if result.errors:
        telemetry.emit_event(
            logger,
            telemetry.CLI_CLEANUP_FAILED,
            level=logging.ERROR,
            message="Cleanup encountered errors",
            errors=[{"path": str(path), "reason": message} for path, message in result.errors],
        )
        error_table = Table(title="Cleanup Errors")
        error_table.add_column("Path", style="red")
        error_table.add_column("Reason", style="white")
        for path, message in result.errors:
            error_table.add_row(str(path), message)
        console.print(error_table)
        raise typer.Exit(code=1)

    summary = Table(title="Cleanup Summary")
    summary.add_column("Metric", style="cyan")
    summary.add_column("Value", justify="right", style="magenta")
    summary.add_row("Search roots", str(len(result.search_roots)))
    summary.add_row("Removed paths", str(len(result.removed_paths)))
    summary.add_row("Skipped roots", str(len(result.skipped_roots)))
    if result.audit_manifest:
        summary.add_row("Audit manifest", str(result.audit_manifest))
    console.print(summary)

    if not removal_log:
        console.print("[blue]No files required removal; workspace already clean.[/blue]")
    else:
        console.print("[green]Cleanup completed successfully.[/green]")

    telemetry.emit_event(
        logger,
        telemetry.CLI_CLEANUP_COMPLETE,
        message="Cleanup command finished",
        removed=len(result.removed_paths),
        skipped=len(result.skipped_roots),
        errors=len(result.errors),
        audit_manifest=str(result.audit_manifest) if result.audit_manifest else None,
    )

    total_duration = time.perf_counter() - start_time
    record_histogram(
        "hephaestus.cleanup.total.duration",
        total_duration,
        attributes={"deep_clean": deep_clean, "dry_run": dry_run},
    )


@trace_command("cleanup")
def cleanup(
    root: Annotated[
        Path | None,
        typer.Argument(help="Workspace root to clean. Defaults to the git repository root or CWD."),
    ] = None,
    include_git: Annotated[
        bool,
        typer.Option(
            "--include-git", help="Also scrub files within .git directories.", show_default=False
        ),
    ] = False,
    include_poetry_env: Annotated[
        bool,
        typer.Option(
            "--include-poetry-env",
            help="Include the Poetry or uv virtual environment if present.",
            show_default=False,
        ),
    ] = False,
    python_cache: Annotated[
        bool,
        typer.Option(
            "--python-cache",
            help="Remove Python __pycache__ folders and bytecode.",
            show_default=False,
        ),
    ] = False,
    build_artifacts: Annotated[
        bool,
        typer.Option(
            "--build-artifacts",
            help="Remove build outputs (dist/, build/, coverage, .tox, etc).",
            show_default=False,
        ),
    ] = False,
    node_modules: Annotated[
        bool,
        typer.Option("--node-modules", help="Remove node_modules directories.", show_default=False),
    ] = False,
    deep_clean: Annotated[
        bool,
        typer.Option(
            "--deep-clean",
            help="Enable all cleanup behaviours (equivalent to enabling every flag).",
            show_default=False,
        ),
    ] = False,
    extra_paths: Annotated[
        list[Path] | None,
        typer.Option(
            "--extra-path",
            help="Additional directories to include in the cleanup.",
            show_default=False,
        ),
    ] = None,
    dry_run: Annotated[
        bool,
        typer.Option(
            "--dry-run",
            help="Preview cleanup without deleting files.",
            show_default=False,
        ),
    ] = False,
    assume_yes: Annotated[
        bool,
        typer.Option(
            "--yes",
            "-y",
            help="Skip confirmation prompts (use with caution).",
        ),
    ] = False,
    audit_manifest: Annotated[
        Path | None,
        typer.Option(
            "--audit-manifest",
            help="Write the cleanup manifest to this path (defaults to .hephaestus/audit/).",
            show_default=False,
        ),
    ] = None,
    max_depth: Annotated[
        int | None,
        typer.Option(
            "--max-depth",
            help="Maximum directory depth to traverse (DoS mitigation, default: unlimited).",
            show_default=False,
        ),
    ] = None,
) -> None:
    """Scrub macOS metadata and development cruft from the workspace."""

    options = cleanup_module.CleanupOptions(
        root=root,
        include_git=include_git,
        include_poetry_env=include_poetry_env,
        python_cache=python_cache,
        build_artifacts=build_artifacts,
        node_modules=node_modules,
        deep_clean=deep_clean,
        extra_paths=tuple(extra_paths or ()),
        dry_run=dry_run,
        audit_manifest=audit_manifest,
        max_depth=max_depth,
    )

    operation_id = telemetry.generate_operation_id()
    with telemetry.operation_context(
        "cli.cleanup",
        operation_id=operation_id,
        command="cleanup",
        root=str(root) if root else None,
    ):
        telemetry.emit_event(
            logger,
            telemetry.CLI_CLEANUP_START,
            message="Starting cleanup command",
            root=str(root) if root else None,
            include_git=include_git,
            include_poetry_env=include_poetry_env,
            python_cache=python_cache,
            build_artifacts=build_artifacts,
            node_modules=node_modules,
            deep_clean=deep_clean,
            extra_paths=[str(path) for path in extra_paths or []],
            dry_run=dry_run,
            audit_manifest=str(audit_manifest) if audit_manifest else None,
        )

        _run_cleanup_pipeline(
            options, assume_yes=assume_yes, dry_run=dry_run, deep_clean=deep_clean
        )


__all__ = ["cleanup", "_run_cleanup_pipeline"]
