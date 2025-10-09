"""Tests for gRPC services."""

from __future__ import annotations

import pytest

try:
    from hephaestus.api.grpc.protos import hephaestus_pb2
    from hephaestus.api.grpc.services import (
        AnalyticsServiceServicer,
        CleanupServiceServicer,
        QualityServiceServicer,
    )
except ModuleNotFoundError as exc:  # pragma: no cover - exercised via pytest skip
    missing_module = exc.name or ""
    if missing_module in {"grpc", "google"} or missing_module.startswith(("grpc.", "google.")):
        pytest.skip("could not import 'grpc': module unavailable", allow_module_level=True)
    raise


class MockContext:
    """Mock gRPC context for testing."""

    pass


@pytest.mark.asyncio
async def test_quality_service_run_guard_rails() -> None:
    """Test QualityService RunGuardRails RPC."""
    service = QualityServiceServicer()
    context = MockContext()

    request = hephaestus_pb2.GuardRailsRequest(
        no_format=False,
        workspace=".",
        drift_check=True,
    )

    response = await service.RunGuardRails(request, context)

    assert isinstance(response, hephaestus_pb2.GuardRailsResponse)
    assert response.success is True
    assert len(response.gates) > 0
    assert response.duration > 0
    assert response.task_id


@pytest.mark.asyncio
async def test_quality_service_run_guard_rails_stream() -> None:
    """Test QualityService RunGuardRailsStream RPC."""
    service = QualityServiceServicer()
    context = MockContext()

    request = hephaestus_pb2.GuardRailsRequest(
        no_format=False,
        workspace=".",
        drift_check=True,
    )

    progress_updates = []
    async for progress in service.RunGuardRailsStream(request, context):
        progress_updates.append(progress)
        assert isinstance(progress, hephaestus_pb2.GuardRailsProgress)
        assert 0 <= progress.progress <= 100

    # Should have multiple updates and final completion
    assert len(progress_updates) > 1
    assert progress_updates[-1].completed is True


@pytest.mark.asyncio
async def test_quality_service_check_drift() -> None:
    """Test QualityService CheckDrift RPC."""
    service = QualityServiceServicer()
    context = MockContext()

    request = hephaestus_pb2.DriftRequest(workspace=".")

    response = await service.CheckDrift(request, context)

    assert isinstance(response, hephaestus_pb2.DriftResponse)
    assert isinstance(response.has_drift, bool)
    if response.has_drift:
        assert len(response.drifts) > 0
        assert len(response.remediation_commands) > 0


@pytest.mark.asyncio
async def test_cleanup_service_clean() -> None:
    """Test CleanupService Clean RPC."""
    service = CleanupServiceServicer()
    context = MockContext()

    request = hephaestus_pb2.CleanupRequest(
        root=".",
        deep_clean=False,
        dry_run=False,
    )

    response = await service.Clean(request, context)

    assert isinstance(response, hephaestus_pb2.CleanupResponse)
    assert response.files_deleted >= 0
    assert response.size_freed >= 0
    assert len(response.manifest) > 0


@pytest.mark.asyncio
async def test_cleanup_service_preview() -> None:
    """Test CleanupService PreviewCleanup RPC."""
    service = CleanupServiceServicer()
    context = MockContext()

    request = hephaestus_pb2.CleanupRequest(
        root=".",
        deep_clean=False,
        dry_run=True,
    )

    response = await service.PreviewCleanup(request, context)

    assert isinstance(response, hephaestus_pb2.CleanupPreview)
    assert response.files_to_delete >= 0
    assert response.size_to_free >= 0
    assert len(response.preview_manifest) > 0


@pytest.mark.asyncio
async def test_analytics_service_get_rankings() -> None:
    """Test AnalyticsService GetRankings RPC."""
    service = AnalyticsServiceServicer()
    context = MockContext()

    request = hephaestus_pb2.RankingsRequest(
        strategy="composite",
        limit=5,
        workspace=".",
    )

    response = await service.GetRankings(request, context)

    assert isinstance(response, hephaestus_pb2.RankingsResponse)
    assert response.strategy
    assert len(response.rankings) > 0
    assert len(response.rankings) <= request.limit

    # Check ranking structure
    for ranking in response.rankings:
        assert ranking.file
        assert ranking.score >= 0
        assert len(ranking.metrics) > 0


@pytest.mark.asyncio
async def test_analytics_service_get_hotspots() -> None:
    """Test AnalyticsService GetHotspots RPC."""
    service = AnalyticsServiceServicer()
    context = MockContext()

    request = hephaestus_pb2.HotspotsRequest(
        workspace=".",
        limit=5,
    )

    response = await service.GetHotspots(request, context)

    assert isinstance(response, hephaestus_pb2.HotspotsResponse)
    assert len(response.hotspots) > 0
    assert len(response.hotspots) <= request.limit

    # Check hotspot structure
    for hotspot in response.hotspots:
        assert hotspot.file
        assert hotspot.change_frequency >= 0
        assert hotspot.complexity >= 0
        assert hotspot.risk_score >= 0


def test_grpc_services_import() -> None:
    """Test that gRPC services can be imported."""
    from hephaestus.api.grpc.services import (
        AnalyticsServiceServicer,
        CleanupServiceServicer,
        QualityServiceServicer,
    )

    assert QualityServiceServicer is not None
    assert CleanupServiceServicer is not None
    assert AnalyticsServiceServicer is not None


def test_grpc_protos_import() -> None:
    """Test that generated proto files can be imported."""
    from hephaestus.api.grpc.protos import hephaestus_pb2, hephaestus_pb2_grpc

    assert hephaestus_pb2 is not None
    assert hephaestus_pb2_grpc is not None


def test_proto_message_creation() -> None:
    """Test creating proto messages."""
    # GuardRailsRequest
    request = hephaestus_pb2.GuardRailsRequest(
        no_format=False,
        workspace="test",
        drift_check=True,
    )
    assert request.no_format is False
    assert request.workspace == "test"
    assert request.drift_check is True

    # CleanupRequest
    cleanup_req = hephaestus_pb2.CleanupRequest(
        root=".",
        deep_clean=True,
        dry_run=False,
    )
    assert cleanup_req.root == "."
    assert cleanup_req.deep_clean is True

    # RankingsRequest
    rankings_req = hephaestus_pb2.RankingsRequest(
        strategy="composite",
        limit=10,
    )
    assert rankings_req.strategy == "composite"
    assert rankings_req.limit == 10
