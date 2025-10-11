"""Quality assurance commands for the Hephaestus CLI."""

from __future__ import annotations

from pathlib import Path
from typing import Annotated

import typer
from rich.console import Console
from rich.table import Table

from hephaestus import toolbox

console = Console()

qa_app = typer.Typer(name="qa", help="Quality assurance commands.", no_args_is_help=True)


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


__all__ = ["qa_app", "qa_coverage", "qa_profile"]
