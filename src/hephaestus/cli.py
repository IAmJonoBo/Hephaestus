"""Typer-based command line interface for the Hephaestus toolkit."""

from __future__ import annotations

import logging
import os
from dataclasses import dataclass, replace
from pathlib import Path
from typing import Annotated, cast

import typer
from rich.console import Console
from rich.table import Table

from hephaestus import (
    __version__,
    cleanup as cleanup_module,
    drift as drift_module,
    events as telemetry,
    logging as logging_utils,
    planning as planning_module,
    release as release_module,
    resource_forks,
    schema as schema_module,
    toolbox,
)
from hephaestus.analytics import RankingStrategy, load_module_signals, rank_modules
from hephaestus.logging import LogFormat
from hephaestus.telemetry import record_histogram, trace_command, trace_operation

app = typer.Typer(name="hephaestus", help="Hephaestus developer toolkit.", no_args_is_help=True)
tools_app = typer.Typer(name="tools", help="Toolkit command groups.", no_args_is_help=True)
refactor_app = typer.Typer(
    name="refactor", help="Refactor analysis commands.", no_args_is_help=True
)
qa_app = typer.Typer(name="qa", help="Quality assurance commands.", no_args_is_help=True)
release_app = typer.Typer(name="release", help="Release management commands.", no_args_is_help=True)
wheelhouse_app = typer.Typer(
    name="wheelhouse", help="Wheelhouse maintenance commands.", no_args_is_help=True
)

tools_app.add_typer(refactor_app)
tools_app.add_typer(qa_app)
app.add_typer(tools_app)
app.add_typer(release_app)
app.add_typer(wheelhouse_app)

console = Console()


logger = logging.getLogger(__name__)


LOG_FORMAT_CHOICES = ("text", "json")
LOG_LEVEL_CHOICES = ("CRITICAL", "ERROR", "WARNING", "INFO", "DEBUG")


def _is_within_root(path: Path, root: Path) -> bool:
    try:
        path.resolve().relative_to(root.resolve())
        return True
    except ValueError:
        return False


@app.callback()
def main(
    ctx: typer.Context,
    log_format: Annotated[
        str,
        typer.Option(
            "--log-format",
            help="Output format for logs emitted by the toolkit.",
            show_default=True,
            case_sensitive=False,
            rich_help_panel="Observability",
        ),
    ] = "text",
    log_level: Annotated[
        str,
        typer.Option(
            "--log-level",
            help="Minimum severity for log output.",
            show_default=True,
            case_sensitive=False,
            rich_help_panel="Observability",
        ),
    ] = "INFO",
    run_id: Annotated[
        str | None,
        typer.Option(
            "--run-id",
            help="Identifier used to correlate logs across distributed runs.",
            rich_help_panel="Observability",
        ),
    ] = None,
) -> None:
    """Initialise structured logging before executing subcommands."""

    normalized_format = log_format.lower()
    if normalized_format not in LOG_FORMAT_CHOICES:
        raise typer.BadParameter(
            f"Invalid log format {log_format!r}. Choose from: {', '.join(LOG_FORMAT_CHOICES)}."
        )

    normalized_level = log_level.upper()
    if normalized_level not in LOG_LEVEL_CHOICES:
        raise typer.BadParameter(
            f"Invalid log level {log_level!r}. Choose from: {', '.join(LOG_LEVEL_CHOICES)}."
        )

    normalized_format_literal = cast(LogFormat, normalized_format)

    final_run_id = run_id or telemetry.generate_run_id()

    logging_utils.configure_logging(
        log_format=normalized_format_literal, level=normalized_level, run_id=final_run_id
    )
    ctx.obj = {"run_id": final_run_id}


@dataclass
class ReleaseInstallOptions:
    repository: str = release_module.DEFAULT_REPOSITORY
    tag: str | None = None
    asset_pattern: str = release_module.DEFAULT_ASSET_PATTERN
    manifest_pattern: str = release_module.DEFAULT_MANIFEST_PATTERN
    sigstore_pattern: str | None = release_module.DEFAULT_SIGSTORE_BUNDLE_PATTERN
    destination: Path | None = None
    token: str | None = None
    timeout: float = release_module.DEFAULT_TIMEOUT
    max_retries: int = release_module.DEFAULT_MAX_RETRIES
    python_executable: str | None = None
    pip_args: list[str] | None = None
    no_upgrade: bool = False
    overwrite: bool = False
    cleanup: bool = False
    remove_archive: bool = False
    allow_unsigned: bool = False
    require_sigstore: bool = False
    sigstore_identity: list[str] | None = None


@release_app.command("install")
def release_install(  # NOSONAR
    repository: Annotated[
        str,
        typer.Option(
            "--repository",
            "-r",
            help="GitHub repository in owner/name form to fetch wheelhouses from.",
            show_default=True,
        ),
    ] = release_module.DEFAULT_REPOSITORY,
    tag: Annotated[
        str | None,
        typer.Option("--tag", "-t", help="Release tag to download (defaults to latest)."),
    ] = None,
    asset_pattern: Annotated[
        str,
        typer.Option(
            "--asset-pattern",
            help="Glob used to select the wheelhouse asset.",
            show_default=True,
        ),
    ] = release_module.DEFAULT_ASSET_PATTERN,
    manifest_pattern: Annotated[
        str,
        typer.Option(
            "--manifest-pattern",
            help="Glob used to locate the checksum manifest for verification.",
            show_default=True,
        ),
    ] = release_module.DEFAULT_MANIFEST_PATTERN,
    sigstore_pattern: Annotated[
        str | None,
        typer.Option(
            "--sigstore-pattern",
            help="Glob used to locate Sigstore bundles for attestation verification.",
            show_default=True,
        ),
    ] = release_module.DEFAULT_SIGSTORE_BUNDLE_PATTERN,
    destination: Annotated[
        Path | None,
        typer.Option(
            "--destination",
            "-d",
            help="Directory used to cache downloaded wheelhouse archives.",
            exists=False,
            file_okay=False,
            dir_okay=True,
            writable=True,
            readable=True,
            resolve_path=True,
        ),
    ] = None,
    token: Annotated[
        str | None,
        typer.Option(
            "--token",
            envvar="GITHUB_TOKEN",
            help="GitHub token (falls back to the GITHUB_TOKEN environment variable).",
        ),
    ] = None,
    timeout: Annotated[
        float,
        typer.Option(
            "--timeout",
            min=0.1,
            help="Network timeout in seconds for release API calls and downloads.",
            show_default=True,
        ),
    ] = release_module.DEFAULT_TIMEOUT,
    max_retries: Annotated[
        int,
        typer.Option(
            "--max-retries",
            min=1,
            help="Maximum retry attempts for release API calls and downloads.",
            show_default=True,
        ),
    ] = release_module.DEFAULT_MAX_RETRIES,
    python_executable: Annotated[
        str | None,
        typer.Option("--python", help="Python executable used to invoke pip."),
    ] = None,
    pip_arg: Annotated[
        list[str] | None,
        typer.Option(
            "--pip-arg",
            help="Additional arguments forwarded to pip install.",
            metavar="ARG",
            show_default=False,
        ),
    ] = None,
    no_upgrade: Annotated[
        bool,
        typer.Option("--no-upgrade", help="Do not pass --upgrade to pip.", show_default=False),
    ] = False,
    overwrite: Annotated[
        bool,
        typer.Option(
            "--overwrite", help="Overwrite existing archives if present.", show_default=False
        ),
    ] = False,
    cleanup: Annotated[
        bool,
        typer.Option(
            "--cleanup", help="Remove the extracted wheelhouse after install.", show_default=False
        ),
    ] = False,
    remove_archive: Annotated[
        bool,
        typer.Option(
            "--remove-archive",
            help="Delete the downloaded archive once installation succeeds.",
            show_default=False,
        ),
    ] = False,
    allow_unsigned: Annotated[
        bool,
        typer.Option(
            "--allow-unsigned",
            help="Skip checksum verification (not recommended).",
            show_default=False,
        ),
    ] = False,
    require_sigstore: Annotated[
        bool,
        typer.Option(
            "--require-sigstore",
            help="Fail if a Sigstore attestation bundle is not published.",
            show_default=False,
        ),
    ] = False,
    sigstore_identity: Annotated[
        list[str] | None,
        typer.Option(
            "--sigstore-identity",
            help=(
                "Expected Sigstore identity (URI or email). Repeat for multiple allowed identities; "
                "supports shell-style globs."
            ),
            show_default=False,
        ),
    ] = None,
    # noqa: PLR0913  # NOSONAR(S107) - CLI surface requires explicit options
) -> None:
    """Download the Hephaestus wheelhouse and install it into the current environment."""

    options = ReleaseInstallOptions(
        repository=repository,
        tag=tag,
        asset_pattern=asset_pattern,
        manifest_pattern=manifest_pattern,
        sigstore_pattern=sigstore_pattern,
        destination=destination,
        token=token,
        timeout=timeout,
        max_retries=max_retries,
        python_executable=python_executable,
        pip_args=list(pip_arg) if pip_arg else None,
        no_upgrade=no_upgrade,
        overwrite=overwrite,
        cleanup=cleanup,
        remove_archive=remove_archive,
        allow_unsigned=allow_unsigned,
        require_sigstore=require_sigstore,
        sigstore_identity=list(sigstore_identity) if sigstore_identity else None,
    )

    destination_path = (
        options.destination.expanduser()
        if options.destination
        else release_module.DEFAULT_DOWNLOAD_DIRECTORY
    )
    operation_id = telemetry.generate_operation_id()
    with telemetry.operation_context(
        "cli.release.install",
        operation_id=operation_id,
        command="release.install",
        repository=options.repository,
        tag=options.tag or "latest",
    ):
        telemetry.emit_event(
            logger,
            telemetry.CLI_RELEASE_INSTALL_START,
            message="Starting release install",
            repository=options.repository,
            tag=options.tag or "latest",
            destination=str(destination_path),
            allow_unsigned=options.allow_unsigned,
            asset_pattern=options.asset_pattern,
            manifest_pattern=options.manifest_pattern,
            sigstore_pattern=options.sigstore_pattern,
            require_sigstore=options.require_sigstore,
            sigstore_identity=(
                list(options.sigstore_identity) if options.sigstore_identity else None
            ),
            timeout=options.timeout,
            max_retries=options.max_retries,
        )
        download = release_module.download_wheelhouse(
            repository=options.repository,
            destination_dir=destination_path,
            tag=options.tag,
            asset_pattern=options.asset_pattern,
            manifest_pattern=options.manifest_pattern,
            sigstore_bundle_pattern=options.sigstore_pattern,
            token=options.token,
            overwrite=options.overwrite,
            extract=False,
            allow_unsigned=options.allow_unsigned,
            require_sigstore=options.require_sigstore,
            sigstore_identities=(
                list(options.sigstore_identity) if options.sigstore_identity else None
            ),
            timeout=options.timeout,
            max_retries=options.max_retries,
        )

        release_module.install_from_archive(
            download.archive_path,
            python_executable=options.python_executable,
            pip_args=list(options.pip_args) if options.pip_args else None,
            upgrade=not options.no_upgrade,
            cleanup=options.cleanup,
        )

        if options.remove_archive:
            download.archive_path.unlink(missing_ok=True)
            telemetry.emit_event(
                logger,
                telemetry.CLI_RELEASE_INSTALL_ARCHIVE_REMOVED,
                message="Removed downloaded archive",
                archive=str(download.archive_path),
            )

        console.print(
            "[green]Installed wheelhouse[/green] "
            f"{download.asset.name} from [cyan]{options.repository}[/cyan] (tag: {options.tag or 'latest'})."
        )
        telemetry.emit_event(
            logger,
            telemetry.CLI_RELEASE_INSTALL_COMPLETE,
            message="Release install completed",
            repository=options.repository,
            tag=options.tag or "latest",
            asset=download.asset.name,
            allow_unsigned=options.allow_unsigned,
        )


# --- Cleanup pipeline extraction ---


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


@release_app.command("backfill")
@trace_command("release.backfill")
def release_backfill(
    version: Annotated[
        str | None,
        typer.Option(
            "--version",
            "-v",
            help="Specific version to backfill (default: all historical versions)",
        ),
    ] = None,
    dry_run: Annotated[
        bool,
        typer.Option(
            "--dry-run",
            help="Perform all steps except uploads (for testing)",
        ),
    ] = False,
) -> None:
    """Backfill Sigstore bundles for historical releases (ADR-0006).

    This command generates Sigstore attestations for historical releases that
    predate Sigstore integration. It downloads existing wheelhouse archives,
    verifies checksums, generates attestations, and uploads .sigstore bundles.

    Requires GITHUB_TOKEN environment variable with repo write access.
    """
    import subprocess

    console.print("[cyan]Starting Sigstore bundle backfill...[/cyan]")

    # Check for GITHUB_TOKEN
    token = os.environ.get("GITHUB_TOKEN")
    if not token:
        console.print("[red]✗ GITHUB_TOKEN environment variable not set[/red]")
        console.print("\nSet your GitHub token:")
        console.print("  export GITHUB_TOKEN=<your-token>")
        raise typer.Exit(code=1)

    # Build command
    import sys

    script_path = Path(__file__).parent.parent.parent / "scripts" / "backfill_sigstore_bundles.py"

    cmd = [sys.executable, str(script_path)]

    if version:
        cmd.extend(["--version", version])

    if dry_run:
        cmd.append("--dry-run")
        console.print("[yellow]DRY RUN MODE - No actual uploads will be performed[/yellow]")

    # Execute backfill script
    console.print(f"\nExecuting: {' '.join(cmd)}\n")

    try:
        result = subprocess.run(
            cmd,
            check=False,
            env=os.environ.copy(),
        )

        if result.returncode == 0:
            console.print("\n[green]✓ Backfill completed successfully![/green]")
        else:
            console.print("\n[red]✗ Backfill failed - see output above[/red]")
            raise typer.Exit(code=result.returncode)

    except FileNotFoundError as exc:
        console.print(f"[red]✗ Backfill script not found: {script_path}[/red]")
        raise typer.Exit(code=1) from exc
    except Exception as exc:
        console.print(f"[red]✗ Unexpected error: {exc}[/red]")
        raise typer.Exit(code=1) from exc


@refactor_app.command("hotspots")
def refactor_hotspots(
    limit: Annotated[int, typer.Option(help="Maximum number of hotspots to report.")] = 10,
    config: Annotated[Path | None, typer.Option(help="Path to override configuration.")] = None,
) -> None:
    """List the highest churn modules that merit refactoring."""

    settings = toolbox.load_settings(config)
    hotspots = toolbox.analyze_hotspots(settings, limit=limit)

    table = Table(title="Refactor Hotspots")
    table.add_column("Path", style="cyan")
    table.add_column("Churn", justify="right", style="magenta")
    table.add_column("Coverage", justify="right", style="green")

    for hotspot in hotspots:
        table.add_row(hotspot.path, str(hotspot.churn), f"{hotspot.coverage:.0%}")

    console.print(table)


@refactor_app.command("opportunities")
def refactor_opportunities(
    config: Annotated[Path | None, typer.Option(help="Path to override configuration.")] = None,
) -> None:
    """Summarise advisory refactor opportunities."""

    settings = toolbox.load_settings(config)
    opportunities = toolbox.enumerate_refactor_opportunities(settings)

    table = Table(title="Refactor Opportunities")
    table.add_column("Identifier", style="cyan")
    table.add_column("Summary", style="white")
    table.add_column("Effort", style="magenta")

    for opportunity in opportunities:
        table.add_row(
            opportunity.identifier,
            opportunity.summary,
            opportunity.estimated_effort,
        )

    console.print(table)


@wheelhouse_app.command("sanitize")
def wheelhouse_sanitize(
    wheelhouse: Annotated[
        Path,
        typer.Argument(
            help="Directory containing extracted wheels or archives to sanitise.",
            exists=False,
            file_okay=False,
            dir_okay=True,
            writable=True,
            readable=True,
        ),
    ],
    dry_run: Annotated[
        bool,
        typer.Option(
            "--dry-run",
            help="Preview resource fork artefacts without removing them.",
            show_default=False,
        ),
    ] = False,
) -> None:
    """Remove macOS resource fork artefacts from a wheelhouse directory."""

    NO_RESOURCE_FORK_MSG = "[green]No resource fork artefacts detected.[/green]"

    operation_id = telemetry.generate_operation_id()
    with telemetry.operation_context(
        "cli.wheelhouse.sanitize",
        operation_id=operation_id,
        command="wheelhouse.sanitize",
        root=str(wheelhouse),
        dry_run=dry_run,
    ):
        report = resource_forks.sanitize_path(wheelhouse, dry_run=dry_run)

        if report.errors:
            console.print("[red]Failed to remove resource fork artefacts:[/red]")
            for candidate, reason in report.errors:
                console.print(f"[red]- {candidate}: {reason}[/red]")
            raise typer.Exit(code=1)

        if dry_run:
            console.print("[cyan]Resource fork artefacts (dry run):[/cyan]")
            if report.preview_paths:
                for candidate in report.preview_paths:
                    console.print(f" - {candidate}")
            else:
                console.print(NO_RESOURCE_FORK_MSG)
            return

        if report.removed_paths:
            for candidate in report.removed_paths:
                console.print(f"[green]Removed resource fork artefact[/green] {candidate}")
        else:
            console.print(NO_RESOURCE_FORK_MSG)


@wheelhouse_app.command("verify")
def wheelhouse_verify(
    wheelhouse: Annotated[
        Path,
        typer.Argument(
            help="Directory containing extracted wheels or archives to inspect.",
            exists=False,
            file_okay=False,
            dir_okay=True,
            readable=True,
        ),
    ],
    strict: Annotated[
        bool,
        typer.Option(
            "--strict/--no-strict",
            help="Exit with an error if artefacts are detected.",
            show_default=True,
        ),
    ] = True,
) -> None:
    """Report macOS resource fork artefacts within a wheelhouse directory."""

    NO_RESOURCE_FORK_MSG = "[green]No resource fork artefacts detected.[/green]"

    operation_id = telemetry.generate_operation_id()
    with telemetry.operation_context(
        "cli.wheelhouse.verify",
        operation_id=operation_id,
        command="wheelhouse.verify",
        root=str(wheelhouse),
        strict=strict,
    ):
        findings = resource_forks.verify_clean(wheelhouse)

        if not findings:
            console.print(NO_RESOURCE_FORK_MSG)
            return

        console.print("[red]Resource fork artefacts detected:[/red]")
        for candidate in findings:
            console.print(f" - {candidate}")

        if strict:
            raise typer.Exit(code=1)


@refactor_app.command("rankings")
def refactor_rankings(
    strategy: Annotated[
        RankingStrategy,
        typer.Option(
            help="Ranking strategy to apply.",
            show_default=True,
            case_sensitive=False,
        ),
    ] = RankingStrategy.RISK_WEIGHTED,
    limit: Annotated[
        int | None,
        typer.Option(help="Maximum number of ranked modules to display."),
    ] = 20,
    config: Annotated[Path | None, typer.Option(help="Path to override configuration.")] = None,
) -> None:
    """Rank modules by refactoring priority using analytics data."""

    settings = toolbox.load_settings(config)

    if settings.analytics is None or not settings.analytics.is_configured:
        console.print(
            "[yellow]No analytics sources configured. "
            "Configure churn_file, coverage_file, or embeddings_file in your settings.[/yellow]"
        )
        raise typer.Exit(code=1)

    signals = load_module_signals(settings.analytics)

    if not signals:
        console.print(
            "[yellow]No module signals loaded from analytics sources. "
            "Check your analytics configuration.[/yellow]"
        )
        raise typer.Exit(code=1)

    ranked = rank_modules(
        signals,
        strategy=strategy,
        coverage_threshold=settings.coverage_threshold,
        limit=limit,
    )

    table = Table(title=f"Module Rankings ({strategy.value})")
    table.add_column("Rank", justify="right", style="bold")
    table.add_column("Path", style="cyan")
    table.add_column("Score", justify="right", style="magenta")
    table.add_column("Churn", justify="right", style="yellow")
    table.add_column("Coverage", justify="right", style="green")
    table.add_column("Uncovered", justify="right", style="red")
    table.add_column("Rationale", style="white")

    for module in ranked:
        coverage_display = f"{module.coverage:.0%}" if module.coverage is not None else "N/A"
        uncovered_display = str(module.uncovered_lines) if module.uncovered_lines else "0"

        table.add_row(
            str(module.rank),
            module.path,
            f"{module.score:.4f}",
            str(module.churn),
            coverage_display,
            uncovered_display,
            module.rationale,
        )

    console.print(table)
    console.print(
        f"\n[dim]Ranked {len(ranked)} modules using {strategy.value} strategy "
        f"with coverage threshold {settings.coverage_threshold:.0%}[/dim]"
    )


@qa_app.command("coverage")
def qa_coverage(
    config: Annotated[Path | None, typer.Option(help="Path to override configuration.")] = None,
) -> None:
    """Display coverage gaps against the configured threshold."""

    settings = toolbox.load_settings(config)
    gaps = toolbox.find_coverage_gaps(settings)

    table = Table(title="Coverage Gaps")
    table.add_column("Module", style="cyan")
    table.add_column("Uncovered Lines", justify="right", style="magenta")
    table.add_column("Risk Score", justify="right", style="red")

    for gap in gaps:
        table.add_row(gap.module, str(gap.uncovered_lines), f"{gap.risk_score:.0%}")

    console.print(table)


@qa_app.command("profile")
def qa_profile(
    profile: Annotated[str, typer.Argument(help="Profile name, e.g. quick or full.")],
    config: Annotated[Path | None, typer.Option(help="Path to override configuration.")] = None,
) -> None:
    """Inspect a QA profile defined in the toolkit configuration."""

    settings = toolbox.load_settings(config)
    data = toolbox.qa_profile_summary(settings, profile)

    table = Table(title=f"QA Profile: {profile}")
    table.add_column("Key", style="cyan")
    table.add_column("Value", style="white")

    for key, value in data.items():
        table.add_row(str(key), str(value))

    console.print(table)


@app.command()
def version() -> None:
    """Show the toolkit version."""

    console.print(f"Hephaestus v{__version__}")


@app.command()
def schema(
    output: Annotated[
        Path | None,
        typer.Option(
            "--output",
            "-o",
            help="Write schemas to JSON file instead of stdout.",
            writable=True,
        ),
    ] = None,
    format: Annotated[
        str,
        typer.Option(
            "--format",
            help="Output format for schemas.",
            show_default=True,
        ),
    ] = "json",
) -> None:
    """Export command schemas for AI agent integration.

    Generates machine-readable schemas describing all CLI commands,
    their parameters, examples, and expected outputs. Designed for
    consumption by AI agents like GitHub Copilot, Cursor, or Claude.
    """
    import json

    # Extract schemas from the app
    registry = schema_module.CommandRegistry()
    registry.commands = schema_module.extract_command_schemas(app)

    # Convert to JSON
    schema_dict = registry.to_json_dict()

    if format.lower() == "json":
        output_text = json.dumps(schema_dict, indent=2, ensure_ascii=False)
    else:
        raise typer.BadParameter(f"Unsupported format: {format}")

    # Write to file or stdout
    if output:
        output.write_text(output_text, encoding="utf-8")
        console.print(f"[green]Schemas exported to {output}[/green]")
    else:
        console.print(output_text)


@app.command()
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
            show_default=False,
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


# --- Guard rails helpers ---


def _run_drift_detection() -> None:
    """Detect tool version drift and exit with status if drift is found."""
    console.print("[cyan]Checking for tool version drift...[/cyan]")
    with trace_operation("drift-detection", check_drift=True):
        try:
            tool_versions = drift_module.detect_drift()

            drift_table = Table(title="Tool Version Drift")
            drift_table.add_column("Tool", style="cyan")
            drift_table.add_column("Expected", style="yellow")
            drift_table.add_column("Actual", style="green")
            drift_table.add_column("Status", style="white")

            drifted = []
            for tool in tool_versions:
                if tool.is_missing:
                    status = "[red]Missing[/red]"
                    drifted.append(tool)
                elif tool.has_drift:
                    status = "[yellow]Drift[/yellow]"
                    drifted.append(tool)
                else:
                    status = "[green]OK[/green]"

                drift_table.add_row(
                    tool.name,
                    tool.expected or "N/A",
                    tool.actual or "Not installed",
                    status,
                )

            console.print(drift_table)

            if drifted:
                console.print("\n[yellow]Tool version drift detected![/yellow]")
                commands = drift_module.generate_remediation_commands(drifted)

                console.print("\n[cyan]Remediation commands:[/cyan]")
                for cmd in commands:
                    if cmd.startswith("#"):
                        console.print(f"[dim]{cmd}[/dim]")
                    else:
                        console.print(f"  {cmd}")

                telemetry.emit_event(
                    logger,
                    telemetry.CLI_GUARD_RAILS_DRIFT,
                    message="Tool version drift detected",
                    drifted_tools=[t.name for t in drifted],
                )
                raise typer.Exit(code=1)
            else:
                console.print("\n[green]✓ All tools are up to date.[/green]")
                telemetry.emit_event(
                    logger,
                    telemetry.CLI_GUARD_RAILS_DRIFT_OK,
                    message="No tool version drift detected",
                )
        except drift_module.DriftDetectionError as exc:
            console.print(f"[red]✗ Drift detection failed: {exc}[/red]")
            raise typer.Exit(code=1) from exc


def _run_guard_rails_plugin_mode(no_format: bool) -> bool:  # NOSONAR(S3776)
    """Run experimental plugin-based pipeline. Returns True if completed, False to fall back."""
    console.print("[cyan]Running guard rails using plugin system (experimental)...[/cyan]")
    from hephaestus.plugins import discover_plugins

    try:
        import time

        start_time = time.perf_counter()
        cleanup(deep_clean=True)
        record_histogram(
            "hephaestus.guard_rails.cleanup.duration",
            time.perf_counter() - start_time,
            attributes={"step": "cleanup", "plugin_mode": "true"},
        )

        plugin_registry = discover_plugins()
        plugins = plugin_registry.all_plugins()

        if not plugins:
            console.print(
                "[yellow]Warning: No plugins loaded. Falling back to standard pipeline.[/yellow]"
            )
            return False

        console.print(f"[cyan]Loaded {len(plugins)} quality gate plugins[/cyan]")

        failed_plugins: list[str] = []
        for plugin in plugins:
            if no_format and plugin.metadata.name == "ruff-format":
                console.print(f"[dim]Skipping {plugin.metadata.name} (--no-format)[/dim]")
                continue

            console.print(
                f"[cyan]→ Running {plugin.metadata.name} ({plugin.metadata.description})...[/cyan]"
            )
            start_time = time.perf_counter()

            try:
                result = plugin.run({})
                record_histogram(
                    "hephaestus.guard_rails.plugin.duration",
                    time.perf_counter() - start_time,
                    attributes={
                        "plugin": plugin.metadata.name,
                        "success": str(result.success).lower(),
                    },
                )

                if not result.success:
                    console.print(f"[red]✗ {plugin.metadata.name}: {result.message}[/red]")
                    failed_plugins.append(plugin.metadata.name)
                    if result.details and "stdout" in result.details:
                        console.print(result.details["stdout"])
                else:
                    console.print(f"[green]✓ {plugin.metadata.name}: {result.message}[/green]")
            except Exception as exc:  # noqa: BLE001 - keep wide to isolate plugin crashes
                console.print(f"[red]✗ {plugin.metadata.name} crashed: {exc}[/red]")
                failed_plugins.append(plugin.metadata.name)

        if failed_plugins:
            console.print(
                f"\n[red]✗ Guard rails failed. {len(failed_plugins)} plugin(s) failed:[/red]"
            )
            for plugin_name in failed_plugins:
                console.print(f"  - {plugin_name}")
            telemetry.emit_event(
                logger,
                telemetry.CLI_GUARD_RAILS_FAILED,
                message="Guard rails failed in plugin mode",
                failed_plugins=failed_plugins,
            )
            raise typer.Exit(code=1)

        console.print("\n[green]✓ Guard rails completed successfully (plugin mode).[/green]")
        telemetry.emit_event(
            logger,
            telemetry.CLI_GUARD_RAILS_COMPLETE,
            message="Guard rails completed successfully in plugin mode",
            skip_format=no_format,
        )
        return True
    except Exception as exc:  # noqa: BLE001 - convert any plugin infra errors to fallback
        console.print(f"[red]✗ Plugin system error: {exc}[/red]")
        console.print("[yellow]Falling back to standard pipeline...[/yellow]")
        return False


def _run_guard_rails_standard(no_format: bool) -> None:  # NOSONAR(S3776)
    """Run the default guard-rails pipeline with metrics and error handling."""
    import subprocess
    import time

    GUARD_RAILS_STEP_DURATION = "hephaestus.guard_rails.step.duration"
    start_time = time.perf_counter()
    try:
        # Step 1: Deep clean workspace
        cleanup(deep_clean=True)
        record_histogram(
            "hephaestus.guard_rails.cleanup.duration",
            time.perf_counter() - start_time,
            attributes={"step": "cleanup"},
        )

        # Step 2: Lint with ruff
        console.print("\n[cyan]→ Running ruff check...[/cyan]")
        subprocess.run(["uv", "run", "ruff", "check", "."], check=True)
        record_histogram(
            GUARD_RAILS_STEP_DURATION,
            time.perf_counter() - start_time,
            attributes={"step": "ruff-check"},
        )

        # Step 3: Sort imports and format with ruff (unless skipped)
        if not no_format:
            console.print("[cyan]→ Running ruff isort...[/cyan]")
            subprocess.run(
                [
                    "uv",
                    "run",
                    "ruff",
                    "check",
                    "--select",
                    "I",
                    "--fix",
                    ".",
                ],
                check=True,
            )
            record_histogram(
                GUARD_RAILS_STEP_DURATION,
                time.perf_counter() - start_time,
                attributes={"step": "ruff-isort"},
            )

            console.print("[cyan]→ Running ruff format...[/cyan]")
            subprocess.run(["uv", "run", "ruff", "format", "."], check=True)
            record_histogram(
                GUARD_RAILS_STEP_DURATION,
                time.perf_counter() - start_time,
                attributes={"step": "ruff-format"},
            )

        # Step 4: Yamllint
        console.print("[cyan]→ Running yamllint...[/cyan]")
        subprocess.run(
            [
                "uv",
                "run",
                "yamllint",
                ".github/",
                ".pre-commit-config.yaml",
                "mkdocs.yml",
                "hephaestus-toolkit/",
            ],
            check=True,
        )
        record_histogram(
            GUARD_RAILS_STEP_DURATION,
            time.perf_counter() - start_time,
            attributes={"step": "yamllint"},
        )

        console.print("[cyan]→ Running actionlint...[/cyan]")
        subprocess.run(["bash", "scripts/run_actionlint.sh"], check=True)
        record_histogram(
            GUARD_RAILS_STEP_DURATION,
            time.perf_counter() - start_time,
            attributes={"step": "actionlint"},
        )

        # Step 5: Mypy
        console.print("[cyan]→ Running mypy...[/cyan]")
        subprocess.run(["uv", "run", "mypy", "src", "tests"], check=True)
        record_histogram(
            GUARD_RAILS_STEP_DURATION,
            time.perf_counter() - start_time,
            attributes={"step": "mypy"},
        )

        # Step 6: Pytest
        console.print("[cyan]→ Running pytest...[/cyan]")
        subprocess.run(["uv", "run", "pytest"], check=True)
        record_histogram(
            GUARD_RAILS_STEP_DURATION,
            time.perf_counter() - start_time,
            attributes={"step": "pytest"},
        )

        # Step 7: pip-audit
        console.print("[cyan]→ Running pip-audit...[/cyan]")
        subprocess.run(
            [
                "uv",
                "run",
                "pip-audit",
                "--strict",
                "--ignore-vuln",
                "GHSA-4xh5-x5gv-qwph",
            ],
            check=True,
        )
        record_histogram(
            GUARD_RAILS_STEP_DURATION,
            time.perf_counter() - start_time,
            attributes={"step": "pip-audit"},
        )

        console.print("\n[green]✓ Guard rails completed successfully.[/green]")
        telemetry.emit_event(
            logger,
            telemetry.CLI_GUARD_RAILS_COMPLETE,
            message="Guard rails completed successfully",
            skip_format=no_format,
        )

    except subprocess.TimeoutExpired as exc:
        record_histogram(
            GUARD_RAILS_STEP_DURATION,
            time.perf_counter() - start_time,
            attributes={"step": "pip-audit", "timeout": True},
        )
        console.print(f"\n[red]✗ Guard rails timed out: {exc.cmd[0]}[/red]")
        console.print(f"[yellow]Timeout: {exc.timeout}s[/yellow]")
        telemetry.emit_event(
            logger,
            telemetry.CLI_GUARD_RAILS_FAILED,
            level=logging.ERROR,
            message="Guard rails timed out",
            step=exc.cmd[0],
            returncode=124,  # Standard timeout exit code
        )
        raise typer.Exit(code=124) from exc

    except subprocess.CalledProcessError as exc:
        console.print(f"\n[red]✗ Guard rails failed at: {exc.cmd[0]}[/red]")
        console.print(f"[yellow]Exit code: {exc.returncode}[/yellow]")
        telemetry.emit_event(
            logger,
            telemetry.CLI_GUARD_RAILS_FAILED,
            level=logging.ERROR,
            message="Guard rails failed",
            step=exc.cmd[0],
            returncode=exc.returncode,
        )
        raise typer.Exit(code=exc.returncode) from exc


@app.command()
def plan() -> None:
    """Render the default execution plan for a Hephaestus rollout."""

    plan_steps = planning_module.build_plan(
        [
            planning_module.PlanStep("Gather Evidence", "Collect churn and coverage analytics"),
            planning_module.PlanStep(
                "Codemod",
                "Run the selected refactor automation",
                planning_module.StepStatus.RUNNING,
            ),
            planning_module.PlanStep("Verify", "Execute characterization and regression suites"),
        ]
    )
    planning_module.display_plan(plan_steps, console=console)


@app.command("guard-rails")
@trace_command("guard-rails")
def guard_rails(
    no_format: Annotated[
        bool,
        typer.Option("--no-format", help="Skip the formatting step.", show_default=False),
    ] = False,
    drift: Annotated[
        bool,
        typer.Option(
            "--drift", help="Check for tool version drift and show remediation.", show_default=False
        ),
    ] = False,
    use_plugins: Annotated[
        bool,
        typer.Option(
            "--use-plugins",
            help="Use plugin system for quality gates (ADR-002 experimental).",
            show_default=False,
        ),
    ] = False,
) -> None:
    """Run the full guard-rail pipeline: cleanup, lint, format, typecheck, test, and audit."""

    operation_id = telemetry.generate_operation_id()
    with telemetry.operation_context(
        "cli.guard-rails",
        operation_id=operation_id,
        command="guard-rails",
        skip_format=no_format,
        check_drift=drift,
    ):
        telemetry.emit_event(
            logger,
            telemetry.CLI_GUARD_RAILS_START,
            message="Running guard rails",
            skip_format=no_format,
        )

        if drift:
            _run_drift_detection()
            return

        if use_plugins and _run_guard_rails_plugin_mode(no_format):
            return

        _run_guard_rails_standard(no_format)
