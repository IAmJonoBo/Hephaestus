"""Typer-based command line interface for the Hephaestus toolkit."""

from __future__ import annotations

import importlib.util
import logging
from importlib import import_module
from pathlib import Path
from typing import Annotated, cast

import typer
from rich.console import Console
from rich.table import Table

from hephaestus import (
    __version__,
    drift as drift_module,
    events as telemetry,
    logging as logging_utils,
    planning as planning_module,
    schema as schema_module,
)
from hephaestus.command_helpers import build_pip_audit_command
from hephaestus.logging import LogFormat
from hephaestus.telemetry import record_histogram, trace_command, trace_operation

_spec = importlib.util.spec_from_loader(__name__, loader=None, origin=__file__, is_package=True)
if _spec is None:
    raise RuntimeError("Failed to create module spec")
__spec__ = _spec
__path__ = [str(Path(__file__).with_name("cli"))]

app = typer.Typer(name="hephaestus", help="Hephaestus developer toolkit.", no_args_is_help=True)
tools_app = typer.Typer(name="tools", help="Toolkit command groups.", no_args_is_help=True)

cleanup_cli = import_module("hephaestus.cli.cleanup")
release_cli = import_module("hephaestus.cli.release")
refactor_cli = import_module("hephaestus.cli.refactor")
qa_cli = import_module("hephaestus.cli.qa")
wheelhouse_cli = import_module("hephaestus.cli.wheelhouse")

# Backwards compatible aliases
cleanup = cleanup_cli.cleanup
release_module = release_cli.release_module

tools_app.add_typer(refactor_cli.refactor_app)
tools_app.add_typer(qa_cli.qa_app)
app.add_typer(tools_app)
app.add_typer(release_cli.release_app)
app.add_typer(wheelhouse_cli.wheelhouse_app)
app.command()(cleanup_cli.cleanup)

console = Console()


logger = logging.getLogger(__name__)


LOG_FORMAT_CHOICES = ("text", "json")
LOG_LEVEL_CHOICES = ("CRITICAL", "ERROR", "WARNING", "INFO", "DEBUG")


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


# --- Guard rails helpers ---


def _run_drift_detection(*, auto_remediate: bool = False) -> None:
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

                remediation_results = []
                if auto_remediate:
                    console.print("\n[cyan]Applying remediation commands...[/cyan]")
                    with trace_operation("drift-remediation", auto=True):
                        remediation_results = drift_module.apply_remediation_commands(commands)

                    for result in remediation_results:
                        status = "green" if result.exit_code == 0 else "red"
                        console.print(f"[{status}]• {result.command} (exit {result.exit_code})[/]")
                        if result.stdout.strip():
                            console.print(result.stdout.strip())
                        if result.stderr.strip():
                            console.print(f"[red]{result.stderr.strip()}[/red]")

                    if remediation_results and all(r.exit_code == 0 for r in remediation_results):
                        console.print(
                            "\n[green]✓ Applied remediation commands successfully.[/green]"
                        )
                        telemetry.emit_event(
                            logger,
                            telemetry.CLI_GUARD_RAILS_REMEDIATED,
                            message="Drift remediated automatically",
                            commands=[r.command for r in remediation_results],
                        )
                        return

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
        cleanup_cli.cleanup(deep_clean=True)
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

    from rich.progress import Progress, SpinnerColumn, TextColumn, TimeElapsedColumn

    GUARD_RAILS_STEP_DURATION = "hephaestus.guard_rails.step.duration"

    steps = [
        ("cleanup", "Deep clean workspace", True),
        ("ruff-check", "Run ruff lint", True),
        ("ruff-isort", "Sort imports", not no_format),
        ("ruff-format", "Format code", not no_format),
        ("yamllint", "Lint YAML files", True),
        ("actionlint", "Validate workflows", True),
        ("mypy", "Type checking", True),
        ("pytest", "Run tests", True),
        ("pip-audit", "Security audit", True),
    ]

    active_steps = [s for s in steps if s[2]]

    with Progress(
        SpinnerColumn(),
        TextColumn("[progress.description]{task.description}"),
        TimeElapsedColumn(),
        console=console,
    ) as progress:
        task = progress.add_task("[cyan]Running guard rails pipeline...", total=len(active_steps))

        start_time = time.perf_counter()
        step_num = 0

        try:
            # Step 1: Deep clean workspace
            step_num += 1
            progress.update(
                task,
                description=f"[cyan][{step_num}/{len(active_steps)}] Deep cleaning workspace...",
            )
            cleanup_cli.cleanup(deep_clean=True)
            record_histogram(
                "hephaestus.guard_rails.cleanup.duration",
                time.perf_counter() - start_time,
                attributes={"step": "cleanup"},
            )
            progress.advance(task)

            # Step 2: Lint with ruff
            step_num += 1
            progress.update(
                task, description=f"[cyan][{step_num}/{len(active_steps)}] Running ruff lint..."
            )
            subprocess.run(["uv", "run", "ruff", "check", "."], check=True)
            record_histogram(
                GUARD_RAILS_STEP_DURATION,
                time.perf_counter() - start_time,
                attributes={"step": "ruff-check"},
            )
            progress.advance(task)

            # Step 3: Sort imports and format with ruff (unless skipped)
            if not no_format:
                step_num += 1
                progress.update(
                    task, description=f"[cyan][{step_num}/{len(active_steps)}] Sorting imports..."
                )
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
                progress.advance(task)

                step_num += 1
                progress.update(
                    task, description=f"[cyan][{step_num}/{len(active_steps)}] Formatting code..."
                )
                subprocess.run(["uv", "run", "ruff", "format", "."], check=True)
                record_histogram(
                    GUARD_RAILS_STEP_DURATION,
                    time.perf_counter() - start_time,
                    attributes={"step": "ruff-format"},
                )
                progress.advance(task)

            # Step 4: Yamllint
            step_num += 1
            progress.update(
                task, description=f"[cyan][{step_num}/{len(active_steps)}] Linting YAML files..."
            )
            subprocess.run(
                [
                    "uv",
                    "run",
                    "yamllint",
                    "-c",
                    ".yamllint",
                    ".github/",
                    ".pre-commit-config.yaml",
                    "hephaestus-toolkit/",
                ],
                check=True,
            )
            record_histogram(
                GUARD_RAILS_STEP_DURATION,
                time.perf_counter() - start_time,
                attributes={"step": "yamllint"},
            )
            progress.advance(task)

            step_num += 1
            progress.update(
                task, description=f"[cyan][{step_num}/{len(active_steps)}] Validating workflows..."
            )
            subprocess.run(["bash", "scripts/run_actionlint.sh"], check=True)
            record_histogram(
                GUARD_RAILS_STEP_DURATION,
                time.perf_counter() - start_time,
                attributes={"step": "actionlint"},
            )
            progress.advance(task)

            # Step 5: Mypy
            step_num += 1
            progress.update(
                task,
                description=f"[cyan][{step_num}/{len(active_steps)}] Type checking with mypy...",
            )
            subprocess.run(["uv", "run", "mypy", "src", "tests"], check=True)
            record_histogram(
                GUARD_RAILS_STEP_DURATION,
                time.perf_counter() - start_time,
                attributes={"step": "mypy"},
            )
            progress.advance(task)

            # Step 6: Pytest
            step_num += 1
            progress.update(
                task, description=f"[cyan][{step_num}/{len(active_steps)}] Running tests..."
            )
            subprocess.run(["uv", "run", "pytest"], check=True)
            record_histogram(
                GUARD_RAILS_STEP_DURATION,
                time.perf_counter() - start_time,
                attributes={"step": "pytest"},
            )
            progress.advance(task)

            # Step 7: pip-audit
            step_num += 1
            progress.update(
                task, description=f"[cyan][{step_num}/{len(active_steps)}] Security audit..."
            )
            subprocess.run(
                build_pip_audit_command(
                    ignore_vulns=["GHSA-4xh5-x5gv-qwph"],
                    prefer_uv_run=True,
                ),
                check=True,
            )
            record_histogram(
                GUARD_RAILS_STEP_DURATION,
                time.perf_counter() - start_time,
                attributes={"step": "pip-audit"},
            )
            progress.advance(task)

            progress.update(task, description="[green]✓ All checks passed!")

        except subprocess.TimeoutExpired as exc:
            progress.stop()
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
            progress.stop()
            console.print(f"\n[red]✗ Guard rails failed at step {step_num}: {exc.cmd[0]}[/red]")
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

    total_duration = time.perf_counter() - start_time
    console.print(f"\n[green]✓ Guard rails completed successfully in {total_duration:.1f}s[/green]")
    telemetry.emit_event(
        logger,
        telemetry.CLI_GUARD_RAILS_COMPLETE,
        message="Guard rails completed successfully",
        skip_format=no_format,
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
    auto_remediate: Annotated[
        bool,
        typer.Option(
            "--auto-remediate",
            help="Automatically apply remediation commands when drift is detected.",
            show_default=False,
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
        auto_remediate=auto_remediate,
    ):
        telemetry.emit_event(
            logger,
            telemetry.CLI_GUARD_RAILS_START,
            message="Running guard rails",
            skip_format=no_format,
        )

        if drift:
            _run_drift_detection(auto_remediate=auto_remediate)
            return

        if use_plugins and _run_guard_rails_plugin_mode(no_format):
            return

        _run_guard_rails_standard(no_format)
