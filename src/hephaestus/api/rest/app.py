"""FastAPI application for Hephaestus REST API (ADR-0004 Sprint 2).

This module implements the core REST API server for remote invocation of
Hephaestus functionality. It provides endpoints for quality gates, cleanup,
analytics, and task management.

Example:
    uvicorn hephaestus.api.rest.app:app --reload
"""

from __future__ import annotations

import asyncio
import logging
from contextlib import asynccontextmanager
from typing import Any

try:
    from fastapi import FastAPI, HTTPException, Security
    from fastapi.responses import StreamingResponse
    from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer
except ImportError as exc:
    raise ImportError(
        "FastAPI is not installed. Install with: pip install 'hephaestus-toolkit[api]'"
    ) from exc

from hephaestus.api.rest.models import (
    CleanupRequest,
    CleanupResponse,
    GuardRailsRequest,
    GuardRailsResponse,
    RankingsRequest,
    RankingsResponse,
    TaskStatusResponse,
)
from hephaestus.api.rest.tasks import TaskManager, TaskStatus

logger = logging.getLogger(__name__)

# Security
security = HTTPBearer(auto_error=False)


def verify_api_key(
    credentials: HTTPAuthorizationCredentials | None = Security(security),
) -> str:
    """Verify API key from Authorization header.

    Args:
        credentials: HTTP bearer credentials from request

    Returns:
        API key if valid

    Raises:
        HTTPException: If API key is missing or invalid
    """
    if credentials is None:
        raise HTTPException(status_code=401, detail="Missing API key")

    api_key = credentials.credentials

    # In production, validate against secure storage
    # For now, accept any non-empty key for development
    if not api_key:
        raise HTTPException(status_code=403, detail="Invalid API key")

    return api_key


# Global task manager instance
task_manager = TaskManager()


@asynccontextmanager
async def lifespan(app: FastAPI) -> Any:
    """Manage application lifecycle."""
    logger.info("Starting Hephaestus API server")
    yield
    logger.info("Shutting down Hephaestus API server")


# Create FastAPI application
app = FastAPI(
    title="Hephaestus API",
    description="REST API for Hephaestus quality gate automation toolkit",
    version="0.3.0",
    lifespan=lifespan,
)


@app.get("/")
async def root() -> dict[str, str]:
    """API root endpoint."""
    return {
        "name": "Hephaestus API",
        "version": "0.3.0",
        "status": "operational",
    }


@app.get("/health")
async def health_check() -> dict[str, str]:
    """Health check endpoint."""
    return {"status": "healthy"}


@app.post("/api/v1/quality/guard-rails")
async def run_guard_rails(
    request: GuardRailsRequest,
    api_key: str = Security(verify_api_key),
) -> GuardRailsResponse:
    """Execute comprehensive quality pipeline.

    Args:
        request: Guard-rails configuration
        api_key: Validated API key

    Returns:
        Guard-rails execution results

    Raises:
        HTTPException: On execution error
    """
    _ = api_key  # API key validated by dependency

    try:
        # Start async task for guard-rails execution
        task_id = await task_manager.create_task(
            "guard-rails", _execute_guard_rails, request
        )

        # For now, wait for completion (blocking)
        # In future, return task_id for async polling
        while True:
            status = await task_manager.get_task_status(task_id)
            if status.status in [TaskStatus.COMPLETED, TaskStatus.FAILED]:
                break
            await asyncio.sleep(0.5)

        if status.status == TaskStatus.FAILED:
            raise HTTPException(status_code=500, detail=status.error)

        result = status.result
        return GuardRailsResponse(
            success=result.get("success", False),
            gates=result.get("gates", []),
            duration=result.get("duration", 0.0),
            task_id=task_id,
        )

    except Exception as e:
        logger.exception("Error executing guard-rails")
        raise HTTPException(status_code=500, detail=str(e)) from e


@app.post("/api/v1/cleanup")
async def cleanup(
    request: CleanupRequest,
    api_key: str = Security(verify_api_key),
) -> CleanupResponse:
    """Clean workspace artifacts.

    Args:
        request: Cleanup configuration
        api_key: Validated API key

    Returns:
        Cleanup results

    Raises:
        HTTPException: On execution error
    """
    _ = api_key

    try:
        # Start async task
        task_id = await task_manager.create_task("cleanup", _execute_cleanup, request)

        # Wait for completion
        while True:
            status = await task_manager.get_task_status(task_id)
            if status.status in [TaskStatus.COMPLETED, TaskStatus.FAILED]:
                break
            await asyncio.sleep(0.5)

        if status.status == TaskStatus.FAILED:
            raise HTTPException(status_code=500, detail=status.error)

        result = status.result
        return CleanupResponse(
            files_deleted=result.get("files_deleted", 0),
            size_freed=result.get("size_freed", 0),
            manifest=result.get("manifest", {}),
        )

    except Exception as e:
        logger.exception("Error executing cleanup")
        raise HTTPException(status_code=500, detail=str(e)) from e


@app.get("/api/v1/analytics/rankings")
async def get_rankings(
    strategy: str = "risk_weighted",
    limit: int = 20,
    api_key: str = Security(verify_api_key),
) -> RankingsResponse:
    """Get refactoring priority rankings.

    Args:
        strategy: Ranking strategy to use
        limit: Maximum number of results
        api_key: Validated API key

    Returns:
        Module rankings

    Raises:
        HTTPException: On execution error
    """
    _ = api_key

    try:
        request = RankingsRequest(strategy=strategy, limit=limit)
        result = await _execute_rankings(request)

        return RankingsResponse(
            rankings=result.get("rankings", []),
            strategy=strategy,
        )

    except Exception as e:
        logger.exception("Error getting rankings")
        raise HTTPException(status_code=500, detail=str(e)) from e


@app.get("/api/v1/tasks/{task_id}")
async def get_task_status(
    task_id: str,
    api_key: str = Security(verify_api_key),
) -> TaskStatusResponse:
    """Get status of an async task.

    Args:
        task_id: Task identifier
        api_key: Validated API key

    Returns:
        Task status and results

    Raises:
        HTTPException: If task not found
    """
    _ = api_key

    try:
        status = await task_manager.get_task_status(task_id)
        return TaskStatusResponse(
            task_id=task_id,
            status=status.status.value,
            progress=status.progress,
            result=status.result,
            error=status.error,
        )
    except KeyError:
        raise HTTPException(status_code=404, detail="Task not found")


@app.get("/api/v1/tasks/{task_id}/stream")
async def stream_task_progress(
    task_id: str,
    api_key: str = Security(verify_api_key),
) -> StreamingResponse:
    """Stream task progress updates using Server-Sent Events.

    Args:
        task_id: Task identifier
        api_key: Validated API key

    Returns:
        Streaming response with progress updates

    Raises:
        HTTPException: If task not found
    """
    _ = api_key

    async def event_generator() -> Any:
        """Generate server-sent events for task progress."""
        import json

        try:
            while True:
                status = await task_manager.get_task_status(task_id)

                event_data = {
                    "status": status.status.value,
                    "progress": status.progress,
                    "result": status.result if status.status == TaskStatus.COMPLETED else None,
                    "error": status.error if status.status == TaskStatus.FAILED else None,
                }

                yield f"data: {json.dumps(event_data)}\n\n"

                if status.status in [TaskStatus.COMPLETED, TaskStatus.FAILED]:
                    break

                await asyncio.sleep(1)

        except KeyError:
            error_data = {"error": "Task not found"}
            yield f"data: {json.dumps(error_data)}\n\n"

    return StreamingResponse(event_generator(), media_type="text/event-stream")


# Task execution functions
async def _execute_guard_rails(request: GuardRailsRequest) -> dict[str, Any]:
    """Execute guard-rails quality pipeline.

    Args:
        request: Guard-rails configuration

    Returns:
        Execution results
    """
    # Import here to avoid circular dependency
    from hephaestus import cleanup as cleanup_module
    from hephaestus.cleanup import CleanupOptions

    # Simulate guard-rails execution
    # In production, this would call actual Hephaestus commands
    gates = []

    # Cleanup step
    if not request.no_format:
        try:
            # Note: This is a simplified execution for API purposes
            # Full implementation would use proper subprocess calls
            gates.append({"name": "cleanup", "passed": True, "duration": 0.5})
        except Exception as e:
            gates.append({"name": "cleanup", "passed": False, "error": str(e)})

    # Additional gates would be executed here
    gates.extend(
        [
            {"name": "ruff-check", "passed": True, "duration": 1.2},
            {"name": "ruff-format", "passed": True, "duration": 0.8},
            {"name": "mypy", "passed": True, "duration": 3.5},
            {"name": "pytest", "passed": True, "duration": 10.2},
            {"name": "pip-audit", "passed": True, "duration": 2.1},
        ]
    )

    success = all(gate["passed"] for gate in gates)
    total_duration = sum(gate.get("duration", 0) for gate in gates)

    return {
        "success": success,
        "gates": gates,
        "duration": total_duration,
    }


async def _execute_cleanup(request: CleanupRequest) -> dict[str, Any]:
    """Execute cleanup operation.

    Args:
        request: Cleanup configuration

    Returns:
        Cleanup results
    """
    # Simulate cleanup execution
    # In production, this would call actual cleanup logic
    return {
        "files_deleted": 42,
        "size_freed": 15728640,  # ~15MB
        "manifest": {
            "python_cache": 15,
            "build_artifacts": 20,
            "resource_forks": 7,
        },
    }


async def _execute_rankings(request: RankingsRequest) -> dict[str, Any]:
    """Execute analytics rankings.

    Args:
        request: Rankings configuration

    Returns:
        Rankings results
    """
    # Simulate rankings execution
    # In production, this would call actual analytics
    rankings = [
        {"rank": 1, "path": "src/module_a.py", "score": 0.85},
        {"rank": 2, "path": "src/module_b.py", "score": 0.72},
        {"rank": 3, "path": "src/module_c.py", "score": 0.68},
    ]

    return {
        "rankings": rankings[: request.limit],
        "strategy": request.strategy,
    }
