from __future__ import annotations

import json
from collections.abc import AsyncIterator
from pathlib import Path
from typing import Any

import pytest

from conftest import ServiceAccountContext
from hephaestus.api import auth as auth_module
from hephaestus.api.rest import tasks as tasks_module
from hephaestus.api.rest.tasks import Task, TaskStatus


def _load_audit_entries(audit_dir: Path) -> list[dict[str, Any]]:
    entries: list[dict[str, Any]] = []
    if not audit_dir.exists():
        return entries

    for path in sorted(audit_dir.glob("*.jsonl")):
        for line in path.read_text(encoding="utf-8").splitlines():
            if not line.strip():
                continue
            entries.append(json.loads(line))
    return entries


@pytest.mark.asyncio
async def test_guard_rails_endpoint_requires_auth(
    rest_app_client: tuple[Any, Any],
) -> None:
    client, _ = rest_app_client

    response = await client.post("/api/v1/quality/guard-rails", json={})

    assert response.status_code == 401


@pytest.mark.asyncio
async def test_guard_rails_endpoint_success(
    rest_app_client: tuple[Any, Any],
    service_account_environment: ServiceAccountContext,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    client, rest_module = rest_app_client

    class StubTaskManager:
        async def create_task(
            self,
            name: str,
            func: Any,
            *args: Any,
            timeout: float | None = None,
            principal: auth_module.AuthenticatedPrincipal | None = None,
            required_roles: frozenset[str] | None = None,
            **kwargs: Any,
        ) -> str:
            assert name == "guard-rails"
            assert principal is not None
            assert required_roles == frozenset({"guard-rails"})
            assert func is rest_module._execute_guard_rails
            assert args
            return "task-123"

        async def wait_for_completion(
            self,
            task_id: str,
            *,
            poll_interval: float = 0.1,
            timeout: float | None = None,
            principal: auth_module.AuthenticatedPrincipal | None = None,
        ) -> Task:
            assert task_id == "task-123"
            assert principal is not None
            return Task(
                id=task_id,
                name="guard-rails",
                status=TaskStatus.COMPLETED,
                progress=1.0,
                result={
                    "success": True,
                    "gates": [{"name": "pytest", "passed": True, "duration": 0.5}],
                    "duration": 0.5,
                },
            )

    monkeypatch.setattr(rest_module, "task_manager", StubTaskManager())

    response = await client.post(
        "/api/v1/quality/guard-rails",
        json={"no_format": True},
        headers={"Authorization": f"Bearer {service_account_environment.guard_token}"},
    )

    assert response.status_code == 200
    payload = response.json()
    assert payload["success"] is True
    assert payload["task_id"] == "task-123"

    entries = _load_audit_entries(service_account_environment.audit_dir)
    assert any(
        entry.get("operation") == "rest.guard-rails.run"
        and entry.get("principal") == "svc-guard@example.com"
        and entry.get("status") == "success"
        for entry in entries
    )


@pytest.mark.asyncio
async def test_task_manager_executes_real_task(
    service_account_environment: ServiceAccountContext,
) -> None:
    verifier = auth_module.get_default_verifier()
    principal = verifier.verify_bearer_token(service_account_environment.guard_token)

    manager = tasks_module.TaskManager()

    async def _task(*, principal: auth_module.AuthenticatedPrincipal) -> dict[str, Any]:
        assert principal.principal == "svc-guard@example.com"
        return {"success": True}

    task_id = await manager.create_task(
        "integration",
        _task,
        principal=principal,
        required_roles={auth_module.Role.GUARD_RAILS.value},
    )

    status = await manager.wait_for_completion(task_id, principal=principal)
    assert status.status == TaskStatus.COMPLETED
    assert status.result == {"success": True}


@pytest.mark.asyncio
async def test_guard_rails_endpoint_forbidden_without_role(
    rest_app_client: tuple[Any, Any],
    service_account_environment: ServiceAccountContext,
) -> None:
    client, _ = rest_app_client

    response = await client.post(
        "/api/v1/quality/guard-rails",
        json={},
        headers={"Authorization": f"Bearer {service_account_environment.analytics_token}"},
    )

    assert response.status_code == 403

    entries = _load_audit_entries(service_account_environment.audit_dir)
    assert any(
        entry.get("operation") == "rest.guard-rails.run"
        and entry.get("status") == "denied"
        for entry in entries
    )


@pytest.mark.asyncio
async def test_guard_rails_endpoint_invalid_token(
    rest_app_client: tuple[Any, Any],
    service_account_environment: ServiceAccountContext,
) -> None:
    client, _ = rest_app_client

    response = await client.post(
        "/api/v1/quality/guard-rails",
        json={},
        headers={"Authorization": "Bearer invalid"},
    )

    assert response.status_code == 401

    entries = _load_audit_entries(service_account_environment.audit_dir)
    assert entries == []


@pytest.mark.asyncio
async def test_cleanup_endpoint_requires_role(
    rest_app_client: tuple[Any, Any],
    service_account_environment: ServiceAccountContext,
) -> None:
    client, _ = rest_app_client

    response = await client.post(
        "/api/v1/cleanup",
        json={"dry_run": True},
        headers={"Authorization": f"Bearer {service_account_environment.cleanup_token}"},
    )

    assert response.status_code == 200
    payload = response.json()
    assert "files_deleted" in payload


@pytest.mark.asyncio
async def test_cleanup_endpoint_denies_missing_role(
    rest_app_client: tuple[Any, Any],
    service_account_environment: ServiceAccountContext,
) -> None:
    client, _ = rest_app_client

    response = await client.post(
        "/api/v1/cleanup",
        json={"dry_run": True},
        headers={"Authorization": f"Bearer {service_account_environment.analytics_token}"},
    )

    assert response.status_code == 403


@pytest.mark.asyncio
async def test_rankings_endpoint_requires_analytics_role(
    rest_app_client: tuple[Any, Any],
    service_account_environment: ServiceAccountContext,
) -> None:
    client, _ = rest_app_client

    forbidden = await client.get(
        "/api/v1/analytics/rankings",
        headers={"Authorization": f"Bearer {service_account_environment.guard_token}"},
    )
    assert forbidden.status_code == 403

    response = await client.get(
        "/api/v1/analytics/rankings",
        headers={"Authorization": f"Bearer {service_account_environment.analytics_token}"},
    )

    assert response.status_code == 200
    payload = response.json()
    assert payload["strategy"]
    assert isinstance(payload["rankings"], list)


@pytest.mark.asyncio
async def test_analytics_ingest_records_audit_events(
    rest_app_client: tuple[Any, Any],
    service_account_environment: ServiceAccountContext,
) -> None:
    client, _ = rest_app_client

    from hephaestus.analytics_streaming import global_ingestor

    global_ingestor.reset()

    payload = "\n".join(
        [
            json.dumps({"source": "ci", "kind": "coverage", "value": 0.98}),
            json.dumps({"source": "ci", "kind": "latency", "value": 125.0}),
        ]
    )

    response = await client.post(
        "/api/v1/analytics/ingest",
        content=payload,
        headers={"Authorization": f"Bearer {service_account_environment.omni_token}"},
    )

    assert response.status_code == 200
    body = response.json()
    assert body["accepted"] == 2
    assert body["rejected"] == 0

    entries = _load_audit_entries(service_account_environment.audit_dir)
    assert any(
        entry.get("operation") == "rest.analytics.ingest"
        and entry.get("principal") == "svc-omni@example.com"
        and entry.get("status") == "success"
        for entry in entries
    )


@pytest.mark.asyncio
async def test_analytics_ingest_denies_missing_role(
    rest_app_client: tuple[Any, Any],
    service_account_environment: ServiceAccountContext,
) -> None:
    client, _ = rest_app_client

    response = await client.post(
        "/api/v1/analytics/ingest",
        content="{}",
        headers={"Authorization": f"Bearer {service_account_environment.guard_token}"},
    )

    assert response.status_code == 403

    entries = _load_audit_entries(service_account_environment.audit_dir)
    assert any(
        entry.get("operation") == "rest.analytics.ingest"
        and entry.get("principal") == "svc-guard@example.com"
        and entry.get("status") == "denied"
        for entry in entries
    )


@pytest.mark.asyncio
async def test_analytics_ingest_handles_chunk_boundaries(
    rest_app_client: tuple[Any, Any],
    service_account_environment: ServiceAccountContext,
) -> None:
    client, _ = rest_app_client

    from hephaestus.analytics_streaming import global_ingestor

    global_ingestor.reset()

    async def byte_stream() -> AsyncIterator[bytes]:
        payload = (
            json.dumps({"source": "ci", "kind": "coverage", "value": 0.9})
            + "\n"
            + json.dumps({"source": "ci", "kind": "latency", "value": 110.0})
        )
        # Emit bytes in uneven chunks to exercise buffering logic.
        for index in range(0, len(payload), 7):
            yield payload[index : index + 7].encode("utf-8")

    response = await client.post(
        "/api/v1/analytics/ingest",
        content=byte_stream(),
        headers={"Authorization": f"Bearer {service_account_environment.omni_token}"},
    )

    assert response.status_code == 200
    body = response.json()
    assert body["accepted"] == 2
    assert body["rejected"] == 0
