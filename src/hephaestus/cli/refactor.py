"""Refactor analytics commands for the Hephaestus CLI."""

from __future__ import annotations

from pathlib import Path
from typing import Annotated

import typer
from rich.console import Console
from rich.table import Table

from hephaestus import toolbox
from hephaestus.analytics import RankingStrategy, load_module_signals, rank_modules

console = Console()

refactor_app = typer.Typer(
    name="refactor", help="Refactor analysis commands.", no_args_is_help=True
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
        table.add_row(
            opportunity.identifier,
            opportunity.summary,
            opportunity.estimated_effort,
        )

    console.print(table)


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
            f"{module.score:.2f}",
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


__all__ = [
    "refactor_app",
    "refactor_hotspots",
    "refactor_opportunities",
    "refactor_rankings",
]
