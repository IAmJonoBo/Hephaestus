"""Async task management for long-running operations."""

from __future__ import annotations

import asyncio
import logging
import time
from dataclasses import dataclass, field
from enum import Enum
from typing import Any, Callable
from uuid import uuid4

logger = logging.getLogger(__name__)

# Constants for task management
DEFAULT_TASK_TIMEOUT = 300  # 5 minutes
MAX_TASKS = 100
MAX_TASK_AGE = 3600  # 1 hour


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
    created_at: float = field(default_factory=time.time)
    completed_at: float | None = None


class TaskManager:
    """Manages async task execution and tracking."""

    def __init__(self, max_tasks: int = MAX_TASKS) -> None:
        """Initialize task manager.

        Args:
            max_tasks: Maximum number of concurrent tasks to track
        """
        self._tasks: dict[str, Task] = {}
        self._max_tasks = max_tasks

    async def create_task(
        self,
        name: str,
        func: Callable[..., Any],
        *args: Any,
        timeout: float | None = DEFAULT_TASK_TIMEOUT,
        **kwargs: Any,
    ) -> str:
        """Create and start a new async task.

        Args:
            name: Task name for tracking
            func: Async function to execute
            *args: Positional arguments for func
            timeout: Task timeout in seconds (None for no timeout)
            **kwargs: Keyword arguments for func

        Returns:
            Task ID

        Raises:
            ValueError: If max tasks exceeded or invalid parameters
        """
        # Validate name
        if not name or not isinstance(name, str):
            raise ValueError("Task name must be a non-empty string")

        # Check task limit
        if len(self._tasks) >= self._max_tasks:
            # Auto-cleanup old tasks
            self.cleanup_completed_tasks()
            if len(self._tasks) >= self._max_tasks:
                raise ValueError(f"Maximum number of tasks ({self._max_tasks}) exceeded")

        task_id = str(uuid4())
        task = Task(
            id=task_id,
            name=name,
            status=TaskStatus.PENDING,
            progress=0.0,
        )
        self._tasks[task_id] = task

        # Start task in background with timeout
        asyncio.create_task(self._execute_task(task_id, func, *args, timeout=timeout, **kwargs))

        logger.info("Created task", extra={"task_id": task_id, "name": name})
        return task_id

    async def _execute_task(
        self,
        task_id: str,
        func: Callable[..., Any],
        *args: Any,
        timeout: float | None = None,
        **kwargs: Any,
    ) -> None:
        """Execute a task and update its status.

        Args:
            task_id: Task identifier
            func: Function to execute
            *args: Positional arguments
            timeout: Timeout in seconds
            **kwargs: Keyword arguments
        """
        task = self._tasks[task_id]
        task.status = TaskStatus.RUNNING

        try:
            # Execute with timeout if specified
            if timeout:
                result = await asyncio.wait_for(func(*args, **kwargs), timeout=timeout)
            else:
                result = await func(*args, **kwargs)

            task.status = TaskStatus.COMPLETED
            task.progress = 1.0
            task.result = result
            task.completed_at = time.time()

            logger.info("Task completed", extra={"task_id": task_id, "task_name": task.name})

        except asyncio.TimeoutError:
            task.status = TaskStatus.FAILED
            task.error = f"Task timed out after {timeout} seconds"
            task.completed_at = time.time()

            logger.error(
                "Task timed out",
                extra={"task_id": task_id, "task_name": task.name, "timeout": timeout},
            )

        except Exception as e:
            task.status = TaskStatus.FAILED
            task.error = str(e)
            task.completed_at = time.time()

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
            ValueError: If progress value is invalid
        """
        if task_id not in self._tasks:
            raise KeyError(f"Task {task_id} not found")

        if not 0.0 <= progress <= 1.0:
            raise ValueError(f"Progress must be between 0.0 and 1.0, got {progress}")

        self._tasks[task_id].progress = progress

    def list_tasks(self) -> list[Task]:
        """List all tasks.

        Returns:
            List of all tasks
        """
        return list(self._tasks.values())

    def cleanup_completed_tasks(self, max_age_seconds: int = MAX_TASK_AGE) -> int:
        """Clean up old completed/failed tasks.

        Args:
            max_age_seconds: Maximum age of completed tasks to keep

        Returns:
            Number of tasks cleaned up
        """
        current_time = time.time()
        initial_count = len(self._tasks)

        # Remove old completed/failed tasks
        tasks_to_remove = []
        for task_id, task in self._tasks.items():
            if task.status in [TaskStatus.COMPLETED, TaskStatus.FAILED]:
                if task.completed_at and (current_time - task.completed_at) > max_age_seconds:
                    tasks_to_remove.append(task_id)

        for task_id in tasks_to_remove:
            del self._tasks[task_id]

        cleaned = initial_count - len(self._tasks)
        if cleaned > 0:
            logger.info(
                "Cleaned up old tasks",
                extra={"cleaned": cleaned, "remaining": len(self._tasks)},
            )

        return cleaned
