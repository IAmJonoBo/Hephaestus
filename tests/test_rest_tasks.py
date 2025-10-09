from __future__ import annotations

import asyncio
import time

import pytest

from hephaestus.api.rest.tasks import (
    DEFAULT_TASK_TIMEOUT,
    MAX_TASK_AGE,
    MAX_TASKS,
    TaskManager,
    TaskStatus,
)


@pytest.mark.asyncio
async def test_create_task_and_wait_for_completion() -> None:
    manager = TaskManager()

    async def sample() -> dict[str, str]:
        await asyncio.sleep(0.01)
        return {"result": "success"}

    task_id = await manager.create_task("sample", sample)
    status = await manager.wait_for_completion(task_id, poll_interval=0.005, timeout=1.0)

    assert status.status is TaskStatus.COMPLETED
    assert status.result == {"result": "success"}


@pytest.mark.asyncio
async def test_wait_for_completion_times_out() -> None:
    manager = TaskManager()
    event = asyncio.Event()

    async def never_complete(evt: asyncio.Event) -> None:
        await evt.wait()

    task_id = await manager.create_task("timeout", never_complete, event, timeout=None)

    with pytest.raises(asyncio.TimeoutError):
        await manager.wait_for_completion(task_id, poll_interval=0.005, timeout=0.05)

    # Unblock the task to avoid leaking background work
    event.set()
    status = await manager.wait_for_completion(task_id, poll_interval=0.005, timeout=1.0)
    assert status.status in {TaskStatus.COMPLETED, TaskStatus.FAILED}


@pytest.mark.asyncio
async def test_execute_task_records_timeout() -> None:
    manager = TaskManager()

    async def slow_task() -> None:
        await asyncio.sleep(0.2)

    task_id = await manager.create_task("slow", slow_task, timeout=0.01)
    status = await manager.wait_for_completion(task_id, poll_interval=0.005, timeout=0.2)

    assert status.status is TaskStatus.FAILED
    assert status.error is not None and "timed out" in status.error


@pytest.mark.asyncio
async def test_execute_task_records_exception() -> None:
    manager = TaskManager()

    async def boom() -> None:
        raise RuntimeError("boom")

    task_id = await manager.create_task("boom", boom)
    status = await manager.wait_for_completion(task_id, poll_interval=0.005, timeout=0.2)

    assert status.status is TaskStatus.FAILED
    assert status.error == "boom"


@pytest.mark.asyncio
async def test_update_progress_validation() -> None:
    manager = TaskManager()

    async def noop() -> None:
        return None

    task_id = await manager.create_task("progress", noop)

    with pytest.raises(KeyError):
        await manager.update_progress("missing", 0.5)

    with pytest.raises(ValueError):
        await manager.update_progress(task_id, 1.5)

    await manager.update_progress(task_id, 0.25)
    status = await manager.get_task_status(task_id)
    assert status.progress == 0.25


@pytest.mark.asyncio
async def test_cleanup_completed_tasks_removes_old_entries(monkeypatch: pytest.MonkeyPatch) -> None:
    manager = TaskManager()

    async def sample() -> None:
        return None

    task_id = await manager.create_task("cleanup", sample)
    status = await manager.wait_for_completion(task_id, poll_interval=0.005, timeout=1.0)
    assert status.completed_at is not None

    old_timestamp = time.time() - (MAX_TASK_AGE + 10)
    status.completed_at = old_timestamp

    cleaned = manager.cleanup_completed_tasks(max_age_seconds=MAX_TASK_AGE)
    assert cleaned == 1
    with pytest.raises(KeyError):
        await manager.get_task_status(task_id)


@pytest.mark.asyncio
async def test_create_task_validates_input() -> None:
    manager = TaskManager(max_tasks=1)

    async def noop() -> None:
        return None

    with pytest.raises(ValueError):
        await manager.create_task("", noop)

    first = await manager.create_task("ok", noop)
    await manager.wait_for_completion(first, poll_interval=0.005, timeout=1.0)

    with pytest.raises(ValueError):
        await manager.create_task("second", noop)


@pytest.mark.asyncio
async def test_cancel_task_marks_failure() -> None:
    manager = TaskManager()
    event = asyncio.Event()

    async def never_complete(evt: asyncio.Event) -> None:
        await evt.wait()

    task_id = await manager.create_task("cancel", never_complete, event, timeout=None)
    await manager.cancel_task(task_id)
    await asyncio.sleep(0)

    status = await manager.get_task_status(task_id)
    assert status.status is TaskStatus.FAILED
    assert status.error == "Task cancelled"


@pytest.mark.asyncio
async def test_wait_for_completion_uses_default_timeout(monkeypatch: pytest.MonkeyPatch) -> None:
    manager = TaskManager()
    event = asyncio.Event()

    async def never_complete(evt: asyncio.Event) -> None:
        await evt.wait()

    task_id = await manager.create_task("default-timeout", never_complete, event, timeout=None)

    # Force a very small default timeout to avoid slow tests
    monkeypatch.setattr("hephaestus.api.rest.tasks.DEFAULT_TASK_TIMEOUT", 0.05)

    with pytest.raises(asyncio.TimeoutError):
        await manager.wait_for_completion(task_id)

    event.set()
    await manager.wait_for_completion(task_id, poll_interval=0.005, timeout=1.0)


@pytest.mark.asyncio
async def test_list_tasks_returns_copy() -> None:
    manager = TaskManager()

    async def sample() -> None:
        return None

    task_id = await manager.create_task("list", sample)
    tasks = manager.list_tasks()
    assert tasks[0].id == task_id
    tasks.append(tasks[0])

    # Original task list should remain unaffected
    assert len(manager.list_tasks()) == 1


@pytest.mark.asyncio
async def test_get_task_status_missing() -> None:
    manager = TaskManager()
    with pytest.raises(KeyError):
        await manager.get_task_status("missing")


def test_constants_exposed() -> None:
    assert isinstance(DEFAULT_TASK_TIMEOUT, (int, float))
    assert isinstance(MAX_TASKS, int)
    assert isinstance(MAX_TASK_AGE, int)
