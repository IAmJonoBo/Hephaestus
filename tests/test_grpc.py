from __future__ import annotations

import json
from collections.abc import AsyncIterator
from pathlib import Path
from typing import Any

import pytest

from hephaestus.api import auth as auth_module

try:
    import grpc

    from hephaestus.api import service as service_module
    from hephaestus.api.grpc import server as server_module
    from hephaestus.api.grpc.protos import hephaestus_pb2
    from hephaestus.api.grpc.services import (
        AnalyticsServiceServicer,
        CleanupServiceServicer,
        QualityServiceServicer,
    )
except ModuleNotFoundError as exc:  # pragma: no cover - skip when grpc unavailable
    missing_module = exc.name or ""
    if missing_module in {"grpc", "google"} or missing_module.startswith(("grpc.", "google.")):
        pytest.skip("could not import 'grpc': module unavailable", allow_module_level=True)
    raise

from conftest import ServiceAccountContext


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


class AbortError(Exception):
    """Raised when the mock gRPC context aborts the request."""

    def __init__(self, code: grpc.StatusCode, details: str) -> None:
        super().__init__(details)
        self._code = code
        self._details = details

    def code(self) -> grpc.StatusCode:
        return self._code

    def details(self) -> str:
        return self._details


class MockContext:
    """Minimal async ServicerContext stub for testing."""

    def __init__(self, principal: auth_module.AuthenticatedPrincipal) -> None:
        self.principal = principal

    async def abort(self, code: grpc.StatusCode, details: str) -> None:
        raise AbortError(code, details)

    def invocation_metadata(self) -> tuple[Any, ...]:  # pragma: no cover - interface parity
        return ()

    for path in sorted(audit_dir.glob("*.jsonl")):
        for line in path.read_text(encoding="utf-8").splitlines():
            if not line.strip():
                continue
            entries.append(json.loads(line))
    return entries

@pytest.mark.asyncio
async def test_quality_service_guard_rails_success(
    service_account_environment: ServiceAccountContext,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    verifier = auth_module.get_default_verifier()
    principal = verifier.verify_bearer_token(service_account_environment.guard_token)

    async def fake_guard_rails(**kwargs: Any) -> service_module.GuardRailExecution:
        return service_module.GuardRailExecution(
            success=True,
            duration=0.2,
            gates=[],
            remediation_commands=[],
            remediation_results=[],
        )

    monkeypatch.setattr(service_module, "evaluate_guard_rails_async", fake_guard_rails)

    service = QualityServiceServicer()
    context = MockContext(principal)

    request = hephaestus_pb2.GuardRailsRequest(no_format=False, drift_check=False)
    response = await service.RunGuardRails(request, context)

    assert isinstance(response, hephaestus_pb2.GuardRailsResponse)
    assert response.success is True

    def details(self) -> str:
        return self._details

@pytest.mark.asyncio
async def test_quality_service_guard_rails_permission_denied(
    service_account_environment: ServiceAccountContext,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    verifier = auth_module.get_default_verifier()
    principal = verifier.verify_bearer_token(service_account_environment.analytics_token)

    async def fake_guard_rails(**kwargs: Any) -> service_module.GuardRailExecution:
        raise AssertionError("should not run when authorization fails")

    monkeypatch.setattr(service_module, "evaluate_guard_rails_async", fake_guard_rails)

    service = QualityServiceServicer()
    context = MockContext(principal)

    request = hephaestus_pb2.GuardRailsRequest(no_format=False)

    with pytest.raises(AbortError) as exc:
        await service.RunGuardRails(request, context)

    assert exc.value.code() == grpc.StatusCode.PERMISSION_DENIED


@pytest.mark.asyncio
async def test_cleanup_service_enforces_roles(
    service_account_environment: ServiceAccountContext,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    verifier = auth_module.get_default_verifier()
    principal = verifier.verify_bearer_token(service_account_environment.cleanup_token)

    def fake_cleanup(**kwargs: Any) -> dict[str, Any]:
        return {"files": 1, "bytes": 10, "manifest": {"removed_count": 1}}

    monkeypatch.setattr(service_module, "run_cleanup_summary", fake_cleanup)

    service = CleanupServiceServicer()
    context = MockContext(principal)

    request = hephaestus_pb2.CleanupRequest(dry_run=True)
    response = await service.Clean(request, context)

    assert response.files_deleted == 1

    forbidden_principal = verifier.verify_bearer_token(service_account_environment.guard_token)
    context_forbidden = MockContext(forbidden_principal)

    with pytest.raises(AbortError) as exc:
        await service.Clean(request, context_forbidden)

    assert exc.value.code() == grpc.StatusCode.PERMISSION_DENIED


@pytest.mark.asyncio
async def test_analytics_service_rankings_requires_role(
    service_account_environment: ServiceAccountContext,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    verifier = auth_module.get_default_verifier()
    analytics_principal = verifier.verify_bearer_token(service_account_environment.analytics_token)
    guard_principal = verifier.verify_bearer_token(service_account_environment.guard_token)

    def fake_rankings(**kwargs: Any) -> list[dict[str, Any]]:
        return [{"path": "src/module.py", "score": 1.0, "churn": 10, "coverage": 0.8, "uncovered_lines": 5, "rationale": "test"}]

    monkeypatch.setattr(service_module, "compute_rankings", fake_rankings)

    service = AnalyticsServiceServicer()

    allowed_context = MockContext(analytics_principal)
    response = await service.GetRankings(
        hephaestus_pb2.RankingsRequest(strategy="risk_weighted", limit=5),
        allowed_context,
    )
    assert len(response.rankings) == 1

    forbidden_context = MockContext(guard_principal)
    with pytest.raises(AbortError) as exc:
        await service.GetRankings(
            hephaestus_pb2.RankingsRequest(strategy="risk_weighted", limit=5),
            forbidden_context,
        )

    assert exc.value.code() == grpc.StatusCode.PERMISSION_DENIED


@pytest.mark.asyncio
async def test_analytics_service_stream_ingest_audit(
    service_account_environment: ServiceAccountContext,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    verifier = auth_module.get_default_verifier()
    principal = verifier.verify_bearer_token(service_account_environment.omni_token)

    monkeypatch.setattr(service_module, "compute_rankings", fake_rankings)

    async def event_generator() -> AsyncIterator[hephaestus_pb2.AnalyticsEvent]:
        yield hephaestus_pb2.AnalyticsEvent(source="ci", kind="coverage", value=0.95)
        yield hephaestus_pb2.AnalyticsEvent(source="ci", kind="latency", value=120.0)

    service = AnalyticsServiceServicer()
    context = MockContext(principal)
    response = await service.StreamIngest(event_generator(), context)

    assert response.accepted == 2

    entries = _load_audit_entries(service_account_environment.audit_dir)
    assert any(
        entry.get("operation") == "grpc.analytics.stream_ingest"
        and entry.get("principal") == "svc-omni@example.com"
        and entry.get("status") == "success"
        for entry in entries
    )


@pytest.mark.asyncio
async def test_analytics_service_stream_ingest_requires_role(
    service_account_environment: ServiceAccountContext,
) -> None:
    verifier = auth_module.get_default_verifier()
    guard_principal = verifier.verify_bearer_token(service_account_environment.guard_token)

    service = AnalyticsServiceServicer()
    context = MockContext(guard_principal)

    async def event_generator() -> AsyncIterator[hephaestus_pb2.AnalyticsEvent]:
        yield hephaestus_pb2.AnalyticsEvent(source="ci", kind="coverage", value=0.95)

    with pytest.raises(AbortError) as exc:
        await service.StreamIngest(event_generator(), context)

    assert exc.value.code() == grpc.StatusCode.PERMISSION_DENIED

    entries = _load_audit_entries(service_account_environment.audit_dir)
    assert any(
        entry.get("operation") == "grpc.analytics.stream_ingest"
        and entry.get("principal") == "svc-guard@example.com"
        and entry.get("status") == "denied"
        for entry in entries
    )


@pytest.mark.asyncio
async def test_service_account_interceptor_missing_header() -> None:
    interceptor = server_module.ServiceAccountAuthInterceptor()

    class EmptyContext:
        async def abort(self, code: grpc.StatusCode, details: str) -> None:
            raise AbortError(code, details)

        def invocation_metadata(self) -> tuple[Any, ...]:
            return ()

    with pytest.raises(AbortError) as exc:
        await interceptor._authenticate(EmptyContext())

    assert exc.value.code() == grpc.StatusCode.UNAUTHENTICATED
