"""Typer-based command line interface for the Hephaestus toolkit."""
from __future__ import annotations

from pathlib import Path
from typing import Annotated, Optional

import typer
from rich.console import Console
from rich.table import Table

from . import __version__
from . import planning as planning_module
from . import toolbox

console = Console()
app = typer.Typer(help="Automation helpers for refactoring and quality rollouts.")

tools_app = typer.Typer(help="Evidence-based refactoring workflows and QA helpers.")
refactor_app = typer.Typer(help="Refactoring oriented commands.")
qa_app = typer.Typer(help="Coverage, quality, and gate orchestration commands.")

app.add_typer(tools_app, name="tools")
tools_app.add_typer(refactor_app, name="refactor")
tools_app.add_typer(qa_app, name="qa")


@app.callback()
def main_callback() -> None:
    """Executed before any command is run."""


@app.command()
def version() -> None:
    """Show the toolkit version."""

    console.print(f"Hephaestus v{__version__}")


@refactor_app.command("hotspots")
def refactor_hotspots(
    limit: Annotated[int, typer.Option(help="Maximum number of hotspots to report.")] = 10,
    config: Annotated[Optional[Path], typer.Option(help="Path to override configuration.")] = None,
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
    config: Annotated[Optional[Path], typer.Option(help="Path to override configuration.")] = None,
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
    config: Annotated[Optional[Path], typer.Option(help="Path to override configuration.")] = None,
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
    config: Annotated[Optional[Path], typer.Option(help="Path to override configuration.")] = None,
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
            planning_module.PlanStep("Codemod", "Run the selected refactor automation", planning_module.StepStatus.RUNNING),
            planning_module.PlanStep("Verify", "Execute characterization and regression suites"),
        ]
    )
    planning_module.display_plan(plan_steps, console=console)


if __name__ == "__main__":  # pragma: no cover
    app()
