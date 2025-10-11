"""Wheelhouse maintenance commands for the Hephaestus CLI."""

from __future__ import annotations

from pathlib import Path
from typing import Annotated

import typer
from rich.console import Console

from hephaestus import events as telemetry
from hephaestus import resource_forks

console = Console()

wheelhouse_app = typer.Typer(
    name="wheelhouse", help="Wheelhouse maintenance commands.", no_args_is_help=True
)


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


__all__ = ["wheelhouse_app", "wheelhouse_sanitize", "wheelhouse_verify"]
