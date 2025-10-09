"""Async task management for long-running operations."""

from __future__ import annotations

import asyncio
import logging
from dataclasses import dataclass
from enum import Enum
from typing import Any, Callable
from uuid import uuid4

logger = logging.getLogger(__name__)


class TaskStatus(Enum):
    """Status of an async task."""

    PENDING = "pending"
    RUNNING = "running"
    COMPLETED = "completed"
    FAILED = "failed"


@dataclass
class Task:
    """Represents an async task."""

    id: str
    name: str
    status: TaskStatus
    progress: float = 0.0
    result: dict[str, Any] | None = None
    error: str | None = None


class TaskManager:
    """Manages async task execution and tracking."""

    def __init__(self) -> None:
        """Initialize task manager."""
        self._tasks: dict[str, Task] = {}

    async def create_task(
        self,
        name: str,
        func: Callable[..., Any],
        *args: Any,
        **kwargs: Any,
    ) -> str:
        """Create and start a new async task.

        Args:
            name: Task name for tracking
            func: Async function to execute
            *args: Positional arguments for func
            **kwargs: Keyword arguments for func

        Returns:
            Task ID
        """
        task_id = str(uuid4())
        task = Task(
            id=task_id,
            name=name,
            status=TaskStatus.PENDING,
            progress=0.0,
        )
        self._tasks[task_id] = task

        # Start task in background
        asyncio.create_task(self._execute_task(task_id, func, *args, **kwargs))

        logger.info("Created task", extra={"task_id": task_id, "name": name})
        return task_id

    async def _execute_task(
        self,
        task_id: str,
        func: Callable[..., Any],
        *args: Any,
        **kwargs: Any,
    ) -> None:
        """Execute a task and update its status.

        Args:
            task_id: Task identifier
            func: Function to execute
            *args: Positional arguments
            **kwargs: Keyword arguments
        """
        task = self._tasks[task_id]
        task.status = TaskStatus.RUNNING

        try:
            # Execute the task function
            result = await func(*args, **kwargs)

            task.status = TaskStatus.COMPLETED
            task.progress = 1.0
            task.result = result

            logger.info("Task completed", extra={"task_id": task_id, "task_name": task.name})

        except Exception as e:
            task.status = TaskStatus.FAILED
            task.error = str(e)

            logger.error(
                "Task failed",
                extra={"task_id": task_id, "task_name": task.name, "error": str(e)},
                exc_info=True,
            )

    async def get_task_status(self, task_id: str) -> Task:
        """Get status of a task.

        Args:
            task_id: Task identifier

        Returns:
            Task object

        Raises:
            KeyError: If task not found
        """
        if task_id not in self._tasks:
            raise KeyError(f"Task {task_id} not found")

        return self._tasks[task_id]

    async def update_progress(self, task_id: str, progress: float) -> None:
        """Update task progress.

        Args:
            task_id: Task identifier
            progress: Progress value (0.0 to 1.0)

        Raises:
            KeyError: If task not found
        """
        if task_id not in self._tasks:
            raise KeyError(f"Task {task_id} not found")

        self._tasks[task_id].progress = max(0.0, min(1.0, progress))

    def list_tasks(self) -> list[Task]:
        """List all tasks.

        Returns:
            List of all tasks
        """
        return list(self._tasks.values())

    def cleanup_completed_tasks(self, max_age_seconds: int = 3600) -> None:
        """Clean up old completed/failed tasks.

        Args:
            max_age_seconds: Maximum age of tasks to keep
        """
        # Simple implementation - just keep the last N tasks
        # In production, would track timestamps and clean based on age
        if len(self._tasks) > 100:
            # Keep only the 50 most recent
            tasks_by_id = sorted(self._tasks.items(), key=lambda x: x[0])[-50:]
            self._tasks = dict(tasks_by_id)
            logger.info("Cleaned up old tasks", extra={"remaining": len(self._tasks)})
