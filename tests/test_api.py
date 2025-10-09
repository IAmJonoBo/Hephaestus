"""Tests for API module structure and REST endpoints (ADR-0004 Sprint 2)."""

from __future__ import annotations

import pytest

from hephaestus import api


def test_api_version_defined() -> None:
    """API module should define version constant."""
    assert hasattr(api, "API_VERSION")
    assert api.API_VERSION == "v1"


def test_api_module_imports() -> None:
    """API module should be importable."""
    # Should not raise ImportError
    from hephaestus import api
    from hephaestus.api import rest

    assert api is not None
    assert rest is not None


def test_rest_api_imports() -> None:
    """Test that REST API can be imported when FastAPI is available."""
    pytest.importorskip("fastapi")

    from hephaestus.api.rest import app

    assert app is not None
    assert hasattr(app, "routes")


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
    guard_rails_resp = GuardRailsResponse(success=True, gates=[], duration=5.0, task_id="test-123")
    assert guard_rails_resp.success is True

    cleanup_resp = CleanupResponse(files_deleted=10, size_freed=1024, manifest={})
    assert cleanup_resp.files_deleted == 10

    rankings_resp = RankingsResponse(rankings=[], strategy="risk_weighted")
    assert rankings_resp.strategy == "risk_weighted"

    task_status_resp = TaskStatusResponse(task_id="test-123", status="completed", progress=1.0)
    assert task_status_resp.progress == 1.0


def test_task_manager() -> None:
    """Test task manager functionality."""
    pytest.importorskip("fastapi")

    import asyncio

    from hephaestus.api.rest.tasks import TaskManager, TaskStatus

    manager = TaskManager()

    # Test task creation
    async def test_async() -> None:
        async def dummy_task() -> dict[str, str]:
            await asyncio.sleep(0.1)
            return {"result": "success"}

        task_id = await manager.create_task("test", dummy_task)
        assert task_id is not None

        # Wait for completion
        for _ in range(10):
            await asyncio.sleep(0.1)
            status = await manager.get_task_status(task_id)
            if status.status == TaskStatus.COMPLETED:
                break

        status = await manager.get_task_status(task_id)
        assert status.status == TaskStatus.COMPLETED
        assert status.result == {"result": "success"}

    asyncio.run(test_async())


def test_api_endpoints_exist() -> None:
    """Test that API endpoints are properly registered."""
    pytest.importorskip("fastapi")

    from hephaestus.api.rest import app

    routes = [route.path for route in app.routes]

    # Check core endpoints exist
    assert "/" in routes
    assert "/health" in routes
    assert "/api/v1/quality/guard-rails" in routes
    assert "/api/v1/cleanup" in routes
    assert "/api/v1/analytics/rankings" in routes


@pytest.mark.asyncio
async def test_health_endpoint() -> None:
    """Test the health check endpoint."""
    pytest.importorskip("fastapi")
    httpx = pytest.importorskip("httpx")

    from hephaestus.api.rest import app

    transport = httpx.ASGITransport(app=app)
    async with httpx.AsyncClient(transport=transport, base_url="http://test") as client:
        response = await client.get("/health")
        assert response.status_code == 200
        data = response.json()
        assert data["status"] == "healthy"


@pytest.mark.asyncio
async def test_root_endpoint() -> None:
    """Test the root endpoint."""
    pytest.importorskip("fastapi")
    httpx = pytest.importorskip("httpx")

    from hephaestus.api.rest import app

    transport = httpx.ASGITransport(app=app)
    async with httpx.AsyncClient(transport=transport, base_url="http://test") as client:
        response = await client.get("/")
        assert response.status_code == 200
        data = response.json()
        assert data["name"] == "Hephaestus API"
        assert data["version"] == "0.3.0"


@pytest.mark.asyncio
async def test_guard_rails_endpoint_requires_auth() -> None:
    """Test that guard-rails endpoint requires authentication."""
    pytest.importorskip("fastapi")
    httpx = pytest.importorskip("httpx")

    from hephaestus.api.rest import app

    transport = httpx.ASGITransport(app=app)
    async with httpx.AsyncClient(transport=transport, base_url="http://test") as client:
        response = await client.post("/api/v1/quality/guard-rails", json={})
        assert response.status_code == 401  # Unauthorized


@pytest.mark.asyncio
async def test_guard_rails_endpoint_with_auth() -> None:
    """Test guard-rails endpoint with authentication."""
    pytest.importorskip("fastapi")
    httpx = pytest.importorskip("httpx")

    from hephaestus.api.rest import app

    headers = {"Authorization": "Bearer test-api-key"}

    transport = httpx.ASGITransport(app=app)
    async with httpx.AsyncClient(transport=transport, base_url="http://test") as client:
        response = await client.post(
            "/api/v1/quality/guard-rails",
            json={"no_format": False, "drift_check": False},
            headers=headers,
        )
        assert response.status_code == 200
        data = response.json()
        assert "success" in data
        assert "gates" in data
        assert "duration" in data
        assert "task_id" in data


@pytest.mark.asyncio
async def test_cleanup_endpoint_with_auth() -> None:
    """Test cleanup endpoint with authentication."""
    pytest.importorskip("fastapi")
    httpx = pytest.importorskip("httpx")

    from hephaestus.api.rest import app

    headers = {"Authorization": "Bearer test-api-key"}

    transport = httpx.ASGITransport(app=app)
    async with httpx.AsyncClient(transport=transport, base_url="http://test") as client:
        response = await client.post(
            "/api/v1/cleanup",
            json={"deep_clean": False, "dry_run": True},
            headers=headers,
        )
        assert response.status_code == 200
        data = response.json()
        assert "files_deleted" in data
        assert "size_freed" in data
        assert "manifest" in data


@pytest.mark.asyncio
async def test_rankings_endpoint_with_auth() -> None:
    """Test rankings endpoint with authentication."""
    pytest.importorskip("fastapi")
    httpx = pytest.importorskip("httpx")

    from hephaestus.api.rest import app

    headers = {"Authorization": "Bearer test-api-key"}

    transport = httpx.ASGITransport(app=app)
    async with httpx.AsyncClient(transport=transport, base_url="http://test") as client:
        response = await client.get(
            "/api/v1/analytics/rankings",
            params={"strategy": "coverage_first", "limit": 5},
            headers=headers,
        )
        assert response.status_code == 200
        data = response.json()
        assert "rankings" in data
        assert "strategy" in data
        assert data["strategy"] == "coverage_first"
