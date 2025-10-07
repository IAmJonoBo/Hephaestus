"""Tests for the execution planning utilities."""

from __future__ import annotations

from rich.console import Console

from hephaestus import planning


def test_build_plan_returns_independent_list() -> None:
    steps_tuple = (
        planning.PlanStep("One", "First"),
        planning.PlanStep("Two", "Second"),
    )

    result = planning.build_plan(steps_tuple)

    assert isinstance(result, list)
    assert result != []
    assert result[0] is steps_tuple[0]
    # ensure the function copied the iterable rather than returning the tuple
    assert result is not steps_tuple


def test_render_plan_table_contains_steps() -> None:
    steps = [
        planning.PlanStep("Gather", "Collect signals", planning.StepStatus.RUNNING),
        planning.PlanStep("Ship", "Deliver improvements", planning.StepStatus.PENDING),
    ]

    table = planning.render_plan_table(steps)

    console = Console(record=True)
    console.print(table)

    output = console.export_text()
    assert "Gather" in output
    assert planning.StepStatus.RUNNING.value in output
    assert "Deliver improvements" in output


def test_display_plan_writes_to_provided_console() -> None:
    steps = [planning.PlanStep("One", "Only step")]
    console = Console(record=True)

    planning.display_plan(steps, console=console)

    output = console.export_text()
    assert "Execution Plan" in output
    assert "Only step" in output
