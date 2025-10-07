"""Utilities for constructing and rendering execution plans."""
from __future__ import annotations

from dataclasses import dataclass
from enum import Enum
from typing import Iterable, List

from rich.console import Console
from rich.table import Table


class StepStatus(str, Enum):
    """Lifecycle for a plan step."""

    PENDING = "pending"
    RUNNING = "running"
    COMPLETE = "complete"
    BLOCKED = "blocked"


@dataclass(slots=True)
class PlanStep:
    """Container for a single execution step."""

    name: str
    description: str
    status: StepStatus = StepStatus.PENDING


def build_plan(steps: Iterable[PlanStep]) -> List[PlanStep]:
    """Return a normalized list of plan steps.

    The function defensively copies the iterable so that downstream consumers can mutate
    the plan without affecting the caller's data structures.
    """

    return list(steps)


def render_plan_table(steps: Iterable[PlanStep]) -> Table:
    """Create a rich table for the provided plan steps."""

    table = Table(title="Execution Plan", caption="Status overview of orchestrated tasks")
    table.add_column("Step", style="cyan", no_wrap=True)
    table.add_column("Status", style="magenta")
    table.add_column("Description", style="white")

    for step in steps:
        table.add_row(step.name, step.status.value, step.description)

    return table


def display_plan(steps: Iterable[PlanStep], *, console: Console | None = None) -> None:
    """Render the plan directly to a console."""

    console = console or Console()
    console.print(render_plan_table(steps))
