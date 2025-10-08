"""Typer-based command line interface for the Hephaestus toolkit."""

from __future__ import annotations

import logging
import subprocess
from pathlib import Path
from typing import Annotated, cast

import typer
from rich.console import Console
from rich.table import Table

from hephaestus import __version__, toolbox
from hephaestus import cleanup as cleanup_module
from hephaestus import logging as logging_utils
from hephaestus import planning as planning_module
from hephaestus import release as release_module

app = typer.Typer(name="hephaestus", help="Hephaestus developer toolkit.", no_args_is_help=True)
tools_app = typer.Typer(name="tools", help="Toolkit command groups.", no_args_is_help=True)
refactor_app = typer.Typer(
    name="refactor", help="Refactor analysis commands.", no_args_is_help=True
)
qa_app = typer.Typer(name="qa", help="Quality assurance commands.", no_args_is_help=True)
release_app = typer.Typer(name="release", help="Release management commands.", no_args_is_help=True)

tools_app.add_typer(refactor_app)
tools_app.add_typer(qa_app)
app.add_typer(tools_app)
app.add_typer(release_app)

console = Console()


logger = logging.getLogger(__name__)


LOG_FORMAT_CHOICES = ("text", "json")
LOG_LEVEL_CHOICES = ("CRITICAL", "ERROR", "WARNING", "INFO", "DEBUG")


@app.callback()
def main(
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

    normalized_format_literal = cast(logging_utils.LogFormat, normalized_format)

    logging_utils.configure_logging(
        log_format=normalized_format_literal, level=normalized_level, run_id=run_id
    )


@release_app.command("install")
def release_install(
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
    pip_args: Annotated[
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
) -> None:
    """Download the Hephaestus wheelhouse and install it into the current environment."""

    destination = (
        destination.expanduser() if destination else release_module.DEFAULT_DOWNLOAD_DIRECTORY
    )
    logging_utils.log_event(
        logger,
        "cli.release.install.start",
        message="Starting release install",
        repository=repository,
        tag=tag or "latest",
        destination=str(destination),
        allow_unsigned=allow_unsigned,
        asset_pattern=asset_pattern,
        manifest_pattern=manifest_pattern,
        timeout=timeout,
        max_retries=max_retries,
    )
    download = release_module.download_wheelhouse(
        repository=repository,
        destination_dir=destination,
        tag=tag,
        asset_pattern=asset_pattern,
        manifest_pattern=manifest_pattern,
        token=token,
        overwrite=overwrite,
        extract=False,
        allow_unsigned=allow_unsigned,
        timeout=timeout,
        max_retries=max_retries,
    )

    release_module.install_from_archive(
        download.archive_path,
        python_executable=python_executable,
        pip_args=list(pip_args) if pip_args else None,
        upgrade=not no_upgrade,
        cleanup=cleanup,
    )

    if remove_archive:
        download.archive_path.unlink(missing_ok=True)
        logging_utils.log_event(
            logger,
            "cli.release.install.archive-removed",
            message="Removed downloaded archive",
            archive=str(download.archive_path),
        )

    console.print(
        "[green]Installed wheelhouse[/green] "
        f"{download.asset.name} from [cyan]{repository}[/cyan] (tag: {tag or 'latest'})."
    )
    logging_utils.log_event(
        logger,
        "cli.release.install.complete",
        message="Release install completed",
        repository=repository,
        tag=tag or "latest",
        asset=download.asset.name,
        allow_unsigned=allow_unsigned,
    )


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
        table.add_row(opportunity.identifier, opportunity.summary, opportunity.estimated_effort)

    console.print(table)


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
    )

    removal_log: list[Path] = []

    logging_utils.log_event(
        logger,
        "cli.cleanup.start",
        message="Starting cleanup command",
        root=str(root) if root else None,
        include_git=include_git,
        include_poetry_env=include_poetry_env,
        python_cache=python_cache,
        build_artifacts=build_artifacts,
        node_modules=node_modules,
        deep_clean=deep_clean,
        extra_paths=[str(path) for path in extra_paths or []],
    )

    def _on_remove(path: Path) -> None:
        removal_log.append(path)
        console.print(f"[green]- removed[/green] {path}")

    def _on_skip(path: Path, reason: str) -> None:
        console.print(f"[yellow]! skipped[/yellow] {path} ({reason})")

    result = cleanup_module.run_cleanup(options, on_remove=_on_remove, on_skip=_on_skip)

    if result.errors:
        logging_utils.log_event(
            logger,
            "cli.cleanup.failed",
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
    console.print(summary)

    if not removal_log:
        console.print("[blue]No files required removal; workspace already clean.[/blue]")
    else:
        console.print("[green]Cleanup completed successfully.[/green]")

    logging_utils.log_event(
        logger,
        "cli.cleanup.complete",
        message="Cleanup command finished",
        removed=len(result.removed_paths),
        skipped=len(result.skipped_roots),
        errors=len(result.errors),
    )


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
def guard_rails(
    no_format: Annotated[
        bool,
        typer.Option("--no-format", help="Skip the formatting step.", show_default=False),
    ] = False,
) -> None:
    """Run the full guard-rail pipeline: cleanup, lint, format, typecheck, test, and audit."""

    console.print("[cyan]Running guard rails...[/cyan]")
    logging_utils.log_event(
        logger,
        "cli.guard-rails.start",
        message="Running guard rails",
        skip_format=no_format,
    )

    try:
        # Step 1: Deep clean workspace
        cleanup(deep_clean=True)

        # Step 2: Lint with ruff
        console.print("\n[cyan]→ Running ruff check...[/cyan]")
        subprocess.run(["ruff", "check", "."], check=True)

        # Step 3: Format with ruff (unless skipped)
        if not no_format:
            console.print("[cyan]→ Running ruff format...[/cyan]")
            subprocess.run(["ruff", "format", "."], check=True)

        # Step 4: Type check with mypy
        console.print("[cyan]→ Running mypy...[/cyan]")
        subprocess.run(["mypy", "src", "tests"], check=True)

        # Step 5: Run tests with pytest
        console.print("[cyan]→ Running pytest...[/cyan]")
        subprocess.run(["pytest"], check=True)

        # Step 6: Security audit with pip-audit
        console.print("[cyan]→ Running pip-audit...[/cyan]")
        subprocess.run(
            ["pip-audit", "--strict", "--ignore-vuln", "GHSA-4xh5-x5gv-qwph"], check=True
        )

        console.print("\n[green]✓ Guard rails completed successfully.[/green]")
        logging_utils.log_event(
            logger,
            "cli.guard-rails.complete",
            message="Guard rails completed successfully",
            skip_format=no_format,
        )

    except subprocess.CalledProcessError as exc:
        console.print(f"\n[red]✗ Guard rails failed at: {exc.cmd[0]}[/red]")
        console.print(f"[yellow]Exit code: {exc.returncode}[/yellow]")
        logging_utils.log_event(
            logger,
            "cli.guard-rails.failed",
            level=logging.ERROR,
            message="Guard rails failed",
            step=exc.cmd[0],
            returncode=exc.returncode,
        )
        raise typer.Exit(code=exc.returncode) from exc


if __name__ == "__main__":  # pragma: no cover
    app()
