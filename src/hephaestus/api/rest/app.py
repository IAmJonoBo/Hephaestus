"""FastAPI application for Hephaestus REST API (ADR-0004 Sprint 2).

This module implements the core REST API server for remote invocation of
Hephaestus functionality. It provides endpoints for quality gates, cleanup,
analytics, and task management.

Example:
    uvicorn hephaestus.api.rest.app:app --reload
"""

from __future__ import annotations

import asyncio
import json
import logging
import time
from collections.abc import AsyncIterator
from contextlib import asynccontextmanager
from typing import Any

try:
    from fastapi import FastAPI, HTTPException, Request, Security
    from fastapi.responses import StreamingResponse
    from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer
except ImportError as exc:
    raise ImportError(
        "FastAPI is not installed. Install with: pip install 'hephaestus-toolkit[api]'"
    ) from exc

from hephaestus.analytics_streaming import global_ingestor
from hephaestus.api import auth
from hephaestus.api.rest.models import (
    AnalyticsEventPayload,
    AnalyticsIngestResponse,
    CleanupRequest,
    CleanupResponse,
    GuardRailsRequest,
    GuardRailsResponse,
    RankingsRequest,
    RankingsResponse,
    TaskStatusResponse,
)
from hephaestus.api.rest.tasks import DEFAULT_TASK_TIMEOUT, TaskManager, TaskStatus
from hephaestus.api.service import (
    compute_rankings,
    evaluate_guard_rails_async,
    run_cleanup_summary,
)
from hephaestus.audit import AuditStatus, record_audit_event

logger = logging.getLogger(__name__)

# Security
security = HTTPBearer(auto_error=False)


def get_authenticated_principal(
    credentials: HTTPAuthorizationCredentials | None = Security(security),  # noqa: B008
) -> auth.AuthenticatedPrincipal:
    """Return the authenticated principal for the current request."""

    if credentials is None or not credentials.credentials:
        raise HTTPException(status_code=401, detail="Missing bearer token")

    verifier = auth.get_default_verifier()
    try:
        return verifier.verify_bearer_token(credentials.credentials)
    except auth.AuthenticationError as exc:
        raise HTTPException(status_code=401, detail=str(exc)) from exc


# Global task manager instance
task_manager = TaskManager()


@asynccontextmanager
async def lifespan(app: FastAPI) -> AsyncIterator[None]:
    """Manage application lifecycle."""
    logger.info("Starting Hephaestus API server")
    try:
        yield
    finally:
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
    principal: auth.AuthenticatedPrincipal = Security(  # noqa: B008
        get_authenticated_principal
    ),
) -> GuardRailsResponse:
    """Execute comprehensive quality pipeline."""

    operation = "rest.guard-rails.run"
    parameters = request.model_dump(exclude_none=True)

    try:
        task_id = await task_manager.create_task(
            "guard-rails",
            _execute_guard_rails,
            request,
            principal=principal,
            required_roles={auth.Role.GUARD_RAILS.value},
        )

        try:
            status = await task_manager.wait_for_completion(
                task_id,
                poll_interval=0.5,
                timeout=DEFAULT_TASK_TIMEOUT,
                principal=principal,
            )
        except TimeoutError as exc:
            record_audit_event(
                principal,
                operation=operation,
                parameters=parameters,
                outcome={"task_id": task_id, "error": "timeout"},
                status=AuditStatus.FAILED,
                protocol="rest",
            )
            logger.error("Guard-rails task timed out", extra={"task_id": task_id})
            raise HTTPException(status_code=504, detail="Guard-rails execution timed out") from exc

        if status.status == TaskStatus.FAILED:
            error_detail = status.error or "Guard-rails execution failed"
            record_audit_event(
                principal,
                operation=operation,
                parameters=parameters,
                outcome={"task_id": task_id, "error": error_detail},
                status=AuditStatus.FAILED,
                protocol="rest",
            )
            raise HTTPException(status_code=500, detail=error_detail)

        result = status.result
        if not isinstance(result, dict):
            record_audit_event(
                principal,
                operation=operation,
                parameters=parameters,
                outcome={"task_id": task_id, "error": "invalid-result"},
                status=AuditStatus.FAILED,
                protocol="rest",
            )
            raise HTTPException(status_code=500, detail="Invalid task result")

        response = GuardRailsResponse(
            success=result.get("success", False),
            gates=result.get("gates", []),
            duration=result.get("duration", 0.0),
            task_id=task_id,
        )
        record_audit_event(
            principal,
            operation=operation,
            parameters=parameters,
            outcome={"task_id": task_id, "success": response.success},
            status=AuditStatus.SUCCESS,
            protocol="rest",
        )
        return response

    except (auth.AuthorizationError, PermissionError) as exc:
        record_audit_event(
            principal,
            operation=operation,
            parameters=parameters,
            outcome={"error": str(exc)},
            status=AuditStatus.DENIED,
            protocol="rest",
        )
        raise HTTPException(status_code=403, detail=str(exc)) from exc
    except HTTPException:
        raise
    except Exception as exc:  # pragma: no cover - defensive guard
        record_audit_event(
            principal,
            operation=operation,
            parameters=parameters,
            outcome={"error": str(exc)},
            status=AuditStatus.FAILED,
            protocol="rest",
        )
        logger.exception("Error executing guard-rails")
        raise HTTPException(status_code=500, detail=str(exc)) from exc


@app.post("/api/v1/cleanup")
async def cleanup(
    request: CleanupRequest,
    principal: auth.AuthenticatedPrincipal = Security(  # noqa: B008
        get_authenticated_principal
    ),
) -> CleanupResponse:
    """Clean workspace artifacts."""

    operation = "rest.cleanup.run"
    parameters = request.model_dump(exclude_none=True)

    try:
        task_id = await task_manager.create_task(
            "cleanup",
            _execute_cleanup,
            request,
            principal=principal,
            required_roles={auth.Role.CLEANUP.value},
        )

        try:
            status = await task_manager.wait_for_completion(
                task_id,
                poll_interval=0.5,
                timeout=DEFAULT_TASK_TIMEOUT,
                principal=principal,
            )
        except TimeoutError as exc:
            record_audit_event(
                principal,
                operation=operation,
                parameters=parameters,
                outcome={"task_id": task_id, "error": "timeout"},
                status=AuditStatus.FAILED,
                protocol="rest",
            )
            logger.error("Cleanup task timed out", extra={"task_id": task_id})
            raise HTTPException(status_code=504, detail="Cleanup execution timed out") from exc

        if status.status == TaskStatus.FAILED:
            error_detail = status.error or "Cleanup execution failed"
            record_audit_event(
                principal,
                operation=operation,
                parameters=parameters,
                outcome={"task_id": task_id, "error": error_detail},
                status=AuditStatus.FAILED,
                protocol="rest",
            )
            raise HTTPException(status_code=500, detail=error_detail)

        result = status.result
        if not isinstance(result, dict):
            record_audit_event(
                principal,
                operation=operation,
                parameters=parameters,
                outcome={"task_id": task_id, "error": "invalid-result"},
                status=AuditStatus.FAILED,
                protocol="rest",
            )
            raise HTTPException(status_code=500, detail="Invalid task result")

        response = CleanupResponse(**result)
        record_audit_event(
            principal,
            operation=operation,
            parameters=parameters,
            outcome={"task_id": task_id, "files_deleted": response.files_deleted},
            status=AuditStatus.SUCCESS,
            protocol="rest",
        )
        return response

    except (auth.AuthorizationError, PermissionError) as exc:
        record_audit_event(
            principal,
            operation=operation,
            parameters=parameters,
            outcome={"error": str(exc)},
            status=AuditStatus.DENIED,
            protocol="rest",
        )
        raise HTTPException(status_code=403, detail=str(exc)) from exc
    except HTTPException:
        raise
    except Exception as exc:  # pragma: no cover - defensive guard
        record_audit_event(
            principal,
            operation=operation,
            parameters=parameters,
            outcome={"error": str(exc)},
            status=AuditStatus.FAILED,
            protocol="rest",
        )
        logger.exception("Error executing cleanup")
        raise HTTPException(status_code=500, detail=str(exc)) from exc


@app.post("/api/v1/analytics/ingest", response_model=AnalyticsIngestResponse)
async def ingest_analytics_stream(
    request: Request,
    principal: auth.AuthenticatedPrincipal = Security(  # noqa: B008
        get_authenticated_principal
    ),
) -> AnalyticsIngestResponse:
    """Ingest analytics events via NDJSON streaming."""

    operation = "rest.analytics.ingest"
    content_length = request.headers.get("content-length", "unknown")
    accepted = 0
    rejected = 0
    buffer = ""

    try:
        auth.ServiceAccountVerifier.require_role(principal, auth.Role.ANALYTICS.value)

        async for chunk in request.stream():
            buffer += chunk.decode("utf-8")
            *lines, buffer = buffer.split("\n")
            for line in lines:
                if not line.strip():
                    continue
                try:
                    payload_raw = json.loads(line)
                except json.JSONDecodeError:
                    global_ingestor.mark_rejected()
                    rejected += 1
                    continue

                try:
                    payload = AnalyticsEventPayload.model_validate(payload_raw)
                except Exception as exc:  # noqa: BLE001 - convert validation errors to rejection
                    logger.debug("Rejected analytics event", extra={"error": str(exc)})
                    global_ingestor.mark_rejected()
                    rejected += 1
                    continue

                if global_ingestor.ingest_mapping(payload.model_dump()):
                    accepted += 1
                else:
                    rejected += 1

        if buffer.strip():
            try:
                payload_raw = json.loads(buffer)
            except json.JSONDecodeError:
                global_ingestor.mark_rejected()
                rejected += 1
            else:
                try:
                    payload = AnalyticsEventPayload.model_validate(payload_raw)
                except Exception as exc:  # noqa: BLE001 - convert validation errors to rejection
                    logger.debug("Rejected trailing analytics event", extra={"error": str(exc)})
                    global_ingestor.mark_rejected()
                    rejected += 1
                else:
                    if global_ingestor.ingest_mapping(payload.model_dump()):
                        accepted += 1
                    else:
                        rejected += 1
    except auth.AuthorizationError as exc:
        record_audit_event(
            principal,
            operation=operation,
            parameters={"content_length": content_length},
            outcome={"error": str(exc)},
            status=AuditStatus.DENIED,
            protocol="rest",
        )
        raise HTTPException(status_code=403, detail=str(exc)) from exc
    except HTTPException:
        raise
    except Exception as exc:  # pragma: no cover - defensive guard
        record_audit_event(
            principal,
            operation=operation,
            parameters={"content_length": content_length},
            outcome={"error": str(exc)},
            status=AuditStatus.FAILED,
            protocol="rest",
        )
        logger.exception("Error ingesting analytics stream")
        raise HTTPException(status_code=500, detail=str(exc)) from exc

    snapshot = global_ingestor.snapshot()
    summary = {
        "total_events": snapshot.total_events,
        "accepted": snapshot.accepted,
        "rejected": snapshot.rejected,
        "kinds": snapshot.kinds,
        "sources": snapshot.sources,
    }

    record_audit_event(
        principal,
        operation=operation,
        parameters={
            "events_received": accepted + rejected,
            "content_length": content_length,
        },
        outcome={"accepted": accepted, "rejected": rejected},
        status=AuditStatus.SUCCESS,
        protocol="rest",
    )

    return AnalyticsIngestResponse(accepted=accepted, rejected=rejected, summary=summary)


@app.get("/api/v1/analytics/rankings")
async def get_rankings(
    strategy: str = "risk_weighted",
    limit: int = 20,
    principal: auth.AuthenticatedPrincipal = Security(  # noqa: B008
        get_authenticated_principal
    ),
) -> RankingsResponse:
    """Get refactoring priority rankings."""

    operation = "rest.analytics.rankings"

    from hephaestus.api.rest.models import RankingStrategy

    try:
        try:
            strategy_enum = RankingStrategy(strategy)
        except ValueError:
            raise HTTPException(status_code=400, detail=f"Invalid strategy: {strategy}") from None

        request = RankingsRequest(strategy=strategy_enum, limit=limit)
        result = _execute_rankings(request, principal=principal)

        response = RankingsResponse(
            rankings=result.get("rankings", []),
            strategy=strategy,
        )
        record_audit_event(
            principal,
            operation=operation,
            parameters={"strategy": strategy, "limit": limit},
            outcome={"count": len(response.rankings)},
            status=AuditStatus.SUCCESS,
            protocol="rest",
        )
        return response

    except auth.AuthorizationError as exc:
        record_audit_event(
            principal,
            operation=operation,
            parameters={"strategy": strategy, "limit": limit},
            outcome={"error": str(exc)},
            status=AuditStatus.DENIED,
            protocol="rest",
        )
        raise HTTPException(status_code=403, detail=str(exc)) from exc
    except HTTPException:
        raise
    except Exception as exc:  # pragma: no cover - defensive guard
        record_audit_event(
            principal,
            operation=operation,
            parameters={"strategy": strategy, "limit": limit},
            outcome={"error": str(exc)},
            status=AuditStatus.FAILED,
            protocol="rest",
        )
        logger.exception("Error getting rankings")
        raise HTTPException(status_code=500, detail=str(exc)) from exc


@app.get("/api/v1/tasks/{task_id}")
async def get_task_status(
    task_id: str,
    principal: auth.AuthenticatedPrincipal = Security(  # noqa: B008
        get_authenticated_principal
    ),
) -> TaskStatusResponse:
    """Get status of an async task."""

    try:
        status = await task_manager.get_task_status(task_id, principal=principal)
        return TaskStatusResponse(
            task_id=task_id,
            status=status.status.value,
            progress=status.progress,
            result=status.result,
            error=status.error,
        )
    except KeyError:
        raise HTTPException(status_code=404, detail="Task not found") from None
    except PermissionError as exc:
        raise HTTPException(status_code=403, detail=str(exc)) from exc


@app.get("/api/v1/tasks/{task_id}/stream")
async def stream_task_progress(
    task_id: str,
    principal: auth.AuthenticatedPrincipal = Security(  # noqa: B008
        get_authenticated_principal
    ),
) -> StreamingResponse:
    """Stream task progress updates using Server-Sent Events."""

    async def event_generator() -> AsyncIterator[bytes]:
        """Generate server-sent events for task progress."""
        import json

        try:
            deadline = time.monotonic() + DEFAULT_TASK_TIMEOUT
            while True:
                status = await task_manager.get_task_status(
                    task_id, principal=principal
                )

                event_data = {
                    "status": status.status.value,
                    "progress": status.progress,
                    "result": status.result if status.status == TaskStatus.COMPLETED else None,
                    "error": status.error if status.status == TaskStatus.FAILED else None,
                }

                json_str = json.dumps(event_data)
                yield f"data: {json_str}\n\n".encode()

                if status.status in [TaskStatus.COMPLETED, TaskStatus.FAILED]:
                    break

                if time.monotonic() >= deadline:
                    timeout_data = {"status": "timeout", "error": "Task stream timed out"}
                    yield f"data: {json.dumps(timeout_data)}\n\n".encode()
                    break

                await asyncio.sleep(1)

        except KeyError:
            error_data = {"error": "Task not found"}
            yield f"data: {json.dumps(error_data)}\n\n".encode()
        except PermissionError as exc:
            error_data = {"error": str(exc)}
            yield f"data: {json.dumps(error_data)}\n\n".encode()

    return StreamingResponse(event_generator(), media_type="text/event-stream")


# Task execution functions
async def _execute_guard_rails(
    request: GuardRailsRequest, *, principal: auth.AuthenticatedPrincipal
) -> dict[str, Any]:
    """Execute guard-rails quality pipeline using shared helpers."""

    execution = await evaluate_guard_rails_async(
        principal=principal,
        no_format=request.no_format,
        workspace=request.workspace,
        drift_check=request.drift_check,
        auto_remediate=request.auto_remediate,
    )

    gates = [
        {
            "name": gate.name,
            "passed": gate.passed,
            "message": gate.message,
            "duration": gate.duration,
            "metadata": gate.metadata,
        }
        for gate in execution.gates
    ]

    if execution.remediation_results:
        gates.append(
            {
                "name": "remediation-results",
                "passed": all(result.exit_code == 0 for result in execution.remediation_results),
                "message": "Recorded remediation outcomes",
                "duration": 0.0,
                "metadata": {
                    "commands": execution.remediation_commands,
                },
            }
        )

    return {
        "success": execution.success,
        "gates": gates,
        "duration": execution.duration,
    }


async def _execute_cleanup(
    request: CleanupRequest, *, principal: auth.AuthenticatedPrincipal
) -> dict[str, Any]:
    """Execute cleanup operation via the toolkit cleanup module."""

    summary = await asyncio.to_thread(
        run_cleanup_summary,
        principal=principal,
        root=request.root,
        deep_clean=request.deep_clean,
        dry_run=request.dry_run,
    )

    return {
        "files_deleted": summary["files"],
        "size_freed": summary["bytes"],
        "manifest": summary["manifest"],
    }


def _execute_rankings(
    request: RankingsRequest, *, principal: auth.AuthenticatedPrincipal
) -> dict[str, Any]:
    """Execute analytics rankings using toolkit analytics."""

    strategy = request.strategy
    rankings = compute_rankings(
        principal=principal,
        strategy=strategy,
        limit=request.limit,
    )

    return {
        "rankings": rankings,
        "strategy": strategy.value,
    }
