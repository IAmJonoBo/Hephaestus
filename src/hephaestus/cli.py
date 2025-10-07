"""Typer-based command line interface for the Hephaestus toolkit."""

from __future__ import annotations

from pathlib import Path
from typing import Annotated

import typer
from rich.console import Console
from rich.table import Table

from . import __version__
from . import cleanup as cleanup_module
from . import planning as planning_module
from . import release as release_module
from . import toolbox

console = Console()
app = typer.Typer(help="Automation helpers for refactoring and quality rollouts.")

tools_app = typer.Typer(help="Evidence-based refactoring workflows and QA helpers.")
refactor_app = typer.Typer(help="Refactoring oriented commands.")
qa_app = typer.Typer(help="Coverage, quality, and gate orchestration commands.")
release_app = typer.Typer(help="Release artefact helpers.")

app.add_typer(tools_app, name="tools")
tools_app.add_typer(refactor_app, name="refactor")
tools_app.add_typer(qa_app, name="qa")
app.add_typer(release_app, name="release")


@app.callback()
def main_callback() -> None:
    """Executed before any command is run."""


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

    def _on_remove(path: Path) -> None:
        removal_log.append(path)
        console.print(f"[green]- removed[/green] {path}")

    def _on_skip(path: Path, reason: str) -> None:
        console.print(f"[yellow]! skipped[/yellow] {path} ({reason})")

    result = cleanup_module.run_cleanup(options, on_remove=_on_remove, on_skip=_on_skip)

    if result.errors:
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
) -> None:
    """Download the Hephaestus wheelhouse and install it into the current environment."""

    destination = (
        destination.expanduser() if destination else release_module.DEFAULT_DOWNLOAD_DIRECTORY
    )
    download = release_module.download_wheelhouse(
        repository=repository,
        destination_dir=destination,
        tag=tag,
        asset_pattern=asset_pattern,
        token=token,
        overwrite=overwrite,
        extract=False,
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

    console.print(
        "[green]Installed wheelhouse[/green] "
        f"{download.asset.name} from [cyan]{repository}[/cyan] (tag: {tag or 'latest'})."
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


if __name__ == "__main__":  # pragma: no cover
    app()
