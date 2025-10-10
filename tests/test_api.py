from __future__ import annotations

import json
from typing import Any

import pytest

from hephaestus import api


def test_api_version_defined() -> None:
    """API module should define version constant."""
    assert hasattr(api, "API_VERSION")
    assert api.API_VERSION == "v1"


def test_api_module_imports() -> None:
    """API module should be importable."""
    # Should not raise ImportError
    from hephaestus import api as api_module
    from hephaestus.api import rest

    assert api_module is not None
    assert rest is not None


def test_rest_api_imports() -> None:
    """Test that REST API can be imported when FastAPI is available."""
    pytest.importorskip("fastapi")

    from hephaestus.api.rest import app as fastapi_app

    assert fastapi_app is not None
    assert hasattr(fastapi_app, "routes")


def test_rest_api_models() -> None:
    """Test that API models are properly defined."""
    pytest.importorskip("fastapi")

    from hephaestus.api.rest.models import (
        CleanupRequest,
        CleanupResponse,
        GuardRailsRequest,
        GuardRailsResponse,
        RankingsRequest,
        RankingsResponse,
        TaskStatusResponse,
    )

    # Test request models
    guard_rails_req = GuardRailsRequest(no_format=True, drift_check=False)
    assert guard_rails_req.no_format is True

    cleanup_req = CleanupRequest(deep_clean=True, dry_run=False)
    assert cleanup_req.deep_clean is True

    rankings_req = RankingsRequest(strategy="coverage_first", limit=10)
    assert rankings_req.limit == 10

    # Test response models
    guard_rails_resp = GuardRailsResponse(
        success=True,
        gates=[],
        duration=5.0,
        task_id="test-123",
    )
    assert guard_rails_resp.success is True

    cleanup_resp = CleanupResponse(
        files_deleted=10,
        size_freed=1024,
        manifest={},
    )
    assert cleanup_resp.files_deleted == 10

    rankings_resp = RankingsResponse(rankings=[], strategy="risk_weighted")
    assert rankings_resp.strategy == "risk_weighted"

    task_status_resp = TaskStatusResponse(
        task_id="test-123",
        status="completed",
        progress=1.0,
    )
    assert task_status_resp.progress == 1.0


@pytest.mark.asyncio
async def test_api_endpoints_exist(rest_app_client: tuple[Any, Any]) -> None:
    """Core REST routes should be registered on the FastAPI app."""
    _, rest_module = rest_app_client

    routes = {route.path for route in rest_module.app.routes}
    assert "/" in routes
    assert "/health" in routes
    assert "/api/v1/quality/guard-rails" in routes
    assert "/api/v1/cleanup" in routes
    assert "/api/v1/analytics/rankings" in routes
    assert "/api/v1/analytics/ingest" in routes


@pytest.mark.asyncio
async def test_analytics_streaming_ingest(rest_app_client: tuple[Any, Any]) -> None:
    """Analytics streaming ingestion should accept NDJSON payloads."""

    from hephaestus.analytics_streaming import global_ingestor

    client, _ = rest_app_client
    global_ingestor.reset()

    payload = "\n".join(
        [
            json.dumps(
                {
                    "source": "ci", "kind": "coverage", "value": 0.91, "unit": "ratio"
                }
            ),
            json.dumps({"source": "ci", "kind": "latency", "value": 120.5, "unit": "ms"}),
            "{\"source\": \"ci\"}",
        ]
    )

    response = await client.post(
        "/api/v1/analytics/ingest",
        content=payload,
        headers={"Authorization": "Bearer test-key"},
    )

    assert response.status_code == 200
    body = response.json()
    assert body["accepted"] == 2
    assert body["rejected"] == 1
    assert body["summary"]["total_events"] >= 2

    snapshot = global_ingestor.snapshot()
    assert snapshot.total_events >= 2
    assert snapshot.accepted >= 2


@pytest.mark.asyncio
async def test_guard_rails_endpoint_requires_auth(rest_app_client: tuple[Any, Any]) -> None:
    """Guard-rails endpoint should reject unauthenticated requests."""
    client, _ = rest_app_client

    response = await client.post("/api/v1/quality/guard-rails", json={})
    assert response.status_code == 401


@pytest.mark.asyncio
async def test_guard_rails_endpoint_with_auth(
    rest_app_client: tuple[Any, Any], monkeypatch: pytest.MonkeyPatch
) -> None:
    """Guard-rails endpoint should use the task manager to execute work."""
    client, rest_module = rest_app_client

    from hephaestus.api.rest.models import GuardRailsRequest
    from hephaestus.api.rest.tasks import Task, TaskStatus

    class StubTaskManager:
        def __init__(self) -> None:
            self.created: list[tuple[str, tuple[Any, ...], dict[str, Any]]] = []

        async def create_task(
            self,
            name: str,
            func: Any,
            *args: Any,
            timeout: float | None = None,
            **kwargs: Any,
        ) -> str:
            self.created.append((name, args, kwargs))
            assert func is rest_module._execute_guard_rails
            # Ensure request payload is passed through
            assert isinstance(args[0], GuardRailsRequest)
            return "task-123"

        async def wait_for_completion(
            self,
            task_id: str,
            poll_interval: float = 0.1,
            timeout: float | None = None,
        ) -> Task:
            assert task_id == "task-123"
            return Task(
                id=task_id,
                name="guard-rails",
                status=TaskStatus.COMPLETED,
                progress=1.0,
                result={
                    "success": True,
                    "gates": [{"name": "pytest", "passed": True, "duration": 1.0}],
                    "duration": 1.0,
                },
            )

        async def get_task_status(self, task_id: str) -> Task:
            return await self.wait_for_completion(task_id)

    stub = StubTaskManager()
    monkeypatch.setattr(rest_module, "task_manager", stub)

    headers = {"Authorization": "Bearer test-api-key"}
    response = await client.post(
        "/api/v1/quality/guard-rails",
        json={"no_format": False, "drift_check": False},
        headers=headers,
    )
    assert response.status_code == 200
    data = response.json()
    assert data["success"] is True
    assert data["gates"][0]["name"] == "pytest"
    assert any(call[0] == "guard-rails" for call in stub.created)


@pytest.mark.asyncio
async def test_guard_rails_endpoint_timeout(
    rest_app_client: tuple[Any, Any], monkeypatch: pytest.MonkeyPatch
) -> None:
    """Guard-rails endpoint should surface task timeouts as HTTP 504."""
    client, rest_module = rest_app_client

    class StubTaskManager:
        async def create_task(self, *args: Any, **kwargs: Any) -> str:
            return "task-timeout"

        async def wait_for_completion(
            self,
            task_id: str,
            poll_interval: float = 0.1,
            timeout: float | None = None,
        ) -> Any:
            raise TimeoutError

        async def get_task_status(self, task_id: str) -> Any:
            raise TimeoutError

    monkeypatch.setattr(rest_module, "task_manager", StubTaskManager())

    headers = {"Authorization": "Bearer test-api-key"}
    response = await client.post(
        "/api/v1/quality/guard-rails",
        json={"no_format": False, "drift_check": False},
        headers=headers,
    )
    assert response.status_code == 504


@pytest.mark.asyncio
async def test_guard_rails_endpoint_failure(
    rest_app_client: tuple[Any, Any], monkeypatch: pytest.MonkeyPatch
) -> None:
    """Guard-rails endpoint should propagate task failures."""
    client, rest_module = rest_app_client

    from hephaestus.api.rest.tasks import Task, TaskStatus

    class StubTaskManager:
        async def create_task(self, *args: Any, **kwargs: Any) -> str:
            return "task-failure"

        async def wait_for_completion(
            self,
            task_id: str,
            poll_interval: float = 0.1,
            timeout: float | None = None,
        ) -> Task:
            return Task(
                id=task_id,
                name="guard-rails",
                status=TaskStatus.FAILED,
                error="boom",
            )

        async def get_task_status(self, task_id: str) -> Task:
            return await self.wait_for_completion(task_id)

    monkeypatch.setattr(rest_module, "task_manager", StubTaskManager())

    headers = {"Authorization": "Bearer test-api-key"}
    response = await client.post(
        "/api/v1/quality/guard-rails",
        json={"no_format": False, "drift_check": False},
        headers=headers,
    )
    assert response.status_code == 500
    assert response.json()["detail"] == "boom"


@pytest.mark.asyncio
async def test_cleanup_endpoint_with_auth(
    rest_app_client: tuple[Any, Any], monkeypatch: pytest.MonkeyPatch
) -> None:
    """Cleanup endpoint should return results from the task manager."""
    client, rest_module = rest_app_client

    from hephaestus.api.rest.tasks import Task, TaskStatus

    class StubTaskManager:
        async def create_task(self, *args: Any, **kwargs: Any) -> str:
            return "cleanup-task"

        async def wait_for_completion(
            self,
            task_id: str,
            poll_interval: float = 0.1,
            timeout: float | None = None,
        ) -> Task:
            return Task(
                id=task_id,
                name="cleanup",
                status=TaskStatus.COMPLETED,
                progress=1.0,
                result={
                    "files_deleted": 5,
                    "size_freed": 1024,
                    "manifest": {"cache": 5},
                },
            )

        async def get_task_status(self, task_id: str) -> Task:
            return await self.wait_for_completion(task_id)

    monkeypatch.setattr(rest_module, "task_manager", StubTaskManager())

    headers = {"Authorization": "Bearer test-api-key"}
    response = await client.post(
        "/api/v1/cleanup",
        json={"deep_clean": False, "dry_run": True},
        headers=headers,
    )
    assert response.status_code == 200
    data = response.json()
    assert data["files_deleted"] == 5
    assert data["manifest"] == {"cache": 5}


@pytest.mark.asyncio
async def test_cleanup_endpoint_failure(
    rest_app_client: tuple[Any, Any], monkeypatch: pytest.MonkeyPatch
) -> None:
    """Cleanup endpoint should convert task failures into HTTP errors."""
    client, rest_module = rest_app_client

    from hephaestus.api.rest.tasks import Task, TaskStatus

    class StubTaskManager:
        async def create_task(self, *args: Any, **kwargs: Any) -> str:
            return "cleanup-failure"

        async def wait_for_completion(
            self,
            task_id: str,
            poll_interval: float = 0.1,
            timeout: float | None = None,
        ) -> Task:
            return Task(
                id=task_id,
                name="cleanup",
                status=TaskStatus.FAILED,
                error="cleanup boom",
            )

        async def get_task_status(self, task_id: str) -> Task:
            return await self.wait_for_completion(task_id)

    monkeypatch.setattr(rest_module, "task_manager", StubTaskManager())

    headers = {"Authorization": "Bearer test-api-key"}
    response = await client.post(
        "/api/v1/cleanup",
        json={"deep_clean": False, "dry_run": True},
        headers=headers,
    )
    assert response.status_code == 500
    assert response.json()["detail"] == "cleanup boom"


@pytest.mark.asyncio
async def test_rankings_endpoint_with_auth(rest_app_client: tuple[Any, Any]) -> None:
    """Rankings endpoint should return strategy metadata."""
    client, _ = rest_app_client

    headers = {"Authorization": "Bearer test-api-key"}
    response = await client.get(
        "/api/v1/analytics/rankings",
        params={"strategy": "coverage_first", "limit": 5},
        headers=headers,
    )
    assert response.status_code == 200
    data = response.json()
    assert data["strategy"] == "coverage_first"
    assert isinstance(data["rankings"], list)


@pytest.mark.asyncio
async def test_get_task_status_success(
    rest_app_client: tuple[Any, Any], monkeypatch: pytest.MonkeyPatch
) -> None:
    """Task status endpoint should expose task metadata."""
    client, rest_module = rest_app_client

    from hephaestus.api.rest.tasks import Task, TaskStatus

    class StubTaskManager:
        async def get_task_status(self, task_id: str) -> Task:
            return Task(
                id=task_id,
                name="guard-rails",
                status=TaskStatus.RUNNING,
                progress=0.5,
                result=None,
                error=None,
            )

    monkeypatch.setattr(rest_module, "task_manager", StubTaskManager())

    headers = {"Authorization": "Bearer test-api-key"}
    response = await client.get("/api/v1/tasks/sample", headers=headers)
    assert response.status_code == 200
    data = response.json()
    assert data["status"] == "running"
    assert data["progress"] == 0.5


@pytest.mark.asyncio
async def test_get_task_status_not_found(
    rest_app_client: tuple[Any, Any], monkeypatch: pytest.MonkeyPatch
) -> None:
    """Task status endpoint should return 404 when task is missing."""
    client, rest_module = rest_app_client

    class StubTaskManager:
        async def get_task_status(self, task_id: str) -> Any:
            raise KeyError(task_id)

    monkeypatch.setattr(rest_module, "task_manager", StubTaskManager())

    headers = {"Authorization": "Bearer test-api-key"}
    response = await client.get("/api/v1/tasks/missing", headers=headers)
    assert response.status_code == 404


@pytest.mark.asyncio
async def test_stream_task_progress_success(
    rest_app_client: tuple[Any, Any], monkeypatch: pytest.MonkeyPatch
) -> None:
    """Streaming endpoint should emit progress updates until completion."""
    client, rest_module = rest_app_client

    from hephaestus.api.rest.tasks import Task, TaskStatus

    class SequenceTaskManager:
        def __init__(self) -> None:
            self._calls = 0

        async def get_task_status(self, task_id: str) -> Task:
            self._calls += 1
            if self._calls == 1:
                return Task(
                    id=task_id,
                    name="guard-rails",
                    status=TaskStatus.RUNNING,
                    progress=0.25,
                )
            return Task(
                id=task_id,
                name="guard-rails",
                status=TaskStatus.COMPLETED,
                progress=1.0,
                result={"ok": True},
            )

    monkeypatch.setattr(rest_module, "task_manager", SequenceTaskManager())

    headers = {"Authorization": "Bearer test-api-key"}
    payloads: list[dict[str, Any]] = []
    async with client.stream("GET", "/api/v1/tasks/sample/stream", headers=headers) as response:
        async for chunk in response.aiter_bytes():
            for block in filter(None, chunk.decode().strip().split("\n\n")):
                if block.startswith("data: "):
                    payloads.append(json.loads(block.split("data: ", 1)[1]))

    assert response.status_code == 200
    assert payloads[-1]["status"] == "completed"
    assert payloads[-1]["result"] == {"ok": True}


@pytest.mark.asyncio
async def test_stream_task_progress_missing_task(
    rest_app_client: tuple[Any, Any], monkeypatch: pytest.MonkeyPatch
) -> None:
    """Streaming endpoint should emit an error message when task is missing."""
    client, rest_module = rest_app_client

    class MissingTaskManager:
        async def get_task_status(self, task_id: str) -> Any:
            raise KeyError(task_id)

    monkeypatch.setattr(rest_module, "task_manager", MissingTaskManager())

    headers = {"Authorization": "Bearer test-api-key"}
    payloads: list[dict[str, Any]] = []
    async with client.stream("GET", "/api/v1/tasks/missing/stream", headers=headers) as response:
        async for chunk in response.aiter_bytes():
            for block in filter(None, chunk.decode().strip().split("\n\n")):
                if block.startswith("data: "):
                    payloads.append(json.loads(block.split("data: ", 1)[1]))

    assert response.status_code == 200
    assert payloads[0]["error"] == "Task not found"


def test_verify_api_key_validation() -> None:
    """verify_api_key should enforce presence of credentials."""
    pytest.importorskip("fastapi")
    from fastapi import HTTPException
    from fastapi.security import HTTPAuthorizationCredentials

    from hephaestus.api.rest.app import verify_api_key

    with pytest.raises(HTTPException) as excinfo:
        verify_api_key(None)
    assert excinfo.value.status_code == 401

    credentials = HTTPAuthorizationCredentials(scheme="Bearer", credentials="")
    with pytest.raises(HTTPException) as excinfo:
        verify_api_key(credentials)
    assert excinfo.value.status_code == 403

    credentials = HTTPAuthorizationCredentials(scheme="Bearer", credentials="valid")
    assert verify_api_key(credentials) == "valid"


@pytest.mark.asyncio
async def test_stream_task_progress_timeout(
    rest_app_client: tuple[Any, Any], monkeypatch: pytest.MonkeyPatch
) -> None:
    """Streaming endpoint should surface timeout events when tasks never finish."""
    client, rest_module = rest_app_client

    from hephaestus.api.rest.tasks import Task, TaskStatus

    class HangingTaskManager:
        async def get_task_status(self, task_id: str) -> Task:
            return Task(
                id=task_id,
                name="guard-rails",
                status=TaskStatus.RUNNING,
                progress=0.0,
            )

    monkeypatch.setattr(rest_module, "task_manager", HangingTaskManager())
    monkeypatch.setattr(rest_module, "DEFAULT_TASK_TIMEOUT", 0.05)

    original_sleep = rest_module.asyncio.sleep

    async def tiny_sleep(_: float) -> None:
        await original_sleep(0)

    monkeypatch.setattr(rest_module.asyncio, "sleep", tiny_sleep)

    headers = {"Authorization": "Bearer test-api-key"}
    payloads: list[dict[str, Any]] = []
    async with client.stream("GET", "/api/v1/tasks/slow/stream", headers=headers) as response:
        async for chunk in response.aiter_bytes():
            for block in filter(None, chunk.decode().strip().split("\n\n")):
                if block.startswith("data: "):
                    payloads.append(json.loads(block.split("data: ", 1)[1]))

    assert response.status_code == 200
    assert payloads[-1]["status"] == "timeout"
    assert payloads[-1]["error"] == "Task stream timed out"


@pytest.mark.asyncio
async def test_execute_guard_rails_synthesises_gates() -> None:
    """Direct guard-rails execution helper should return structured gates."""
    pytest.importorskip("fastapi")

    from hephaestus.api.rest.app import _execute_guard_rails
    from hephaestus.api.rest.models import GuardRailsRequest

    result = await _execute_guard_rails(GuardRailsRequest())
    assert result["success"] is True
    assert any(gate["name"] == "cleanup" for gate in result["gates"])
    assert any(gate["name"] == "pytest" for gate in result["gates"])


@pytest.mark.asyncio
async def test_execute_cleanup_returns_manifest() -> None:
    """Cleanup helper should return manifest payload."""
    pytest.importorskip("fastapi")

    from hephaestus.api.rest.app import _execute_cleanup
    from hephaestus.api.rest.models import CleanupRequest

    result = await _execute_cleanup(CleanupRequest(dry_run=True))
    assert result["files_deleted"] >= 0
    assert "manifest" in result


def test_execute_rankings_limits_results() -> None:
    """Rankings helper should respect request limit."""
    pytest.importorskip("fastapi")

    from hephaestus.api.rest.app import _execute_rankings
    from hephaestus.api.rest.models import RankingsRequest

    result = _execute_rankings(RankingsRequest(limit=2))
    assert len(result["rankings"]) == 2
    assert result["strategy"] == "risk_weighted"
