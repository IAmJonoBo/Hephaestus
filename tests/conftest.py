from __future__ import annotations

import base64
import json
import os
from collections.abc import AsyncIterator, Generator
from dataclasses import dataclass
from datetime import UTC, datetime, timedelta
from pathlib import Path
from typing import Any

import pytest
import pytest_asyncio


@dataclass(slots=True, frozen=True)
class ServiceAccountContext:
    """Fixture payload containing generated service account tokens."""

    guard_token: str
    cleanup_token: str
    analytics_token: str
    omni_token: str
    audit_dir: Path


@pytest.fixture()
def service_account_environment(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> Generator[ServiceAccountContext]:
    """Provision temporary service account credentials for API tests."""

    import importlib

    from hephaestus.api import auth as auth_module

    guard_secret = os.urandom(32)
    cleanup_secret = os.urandom(32)
    analytics_secret = os.urandom(32)
    omni_secret = os.urandom(32)

    keys_payload = {
        "keys": [
            {
                "key_id": "guard-key",
                "principal": "svc-guard@example.com",
                "roles": ["guard-rails", "cleanup"],
                "secret": base64.urlsafe_b64encode(guard_secret).decode("ascii"),
            },
            {
                "key_id": "cleanup-key",
                "principal": "svc-cleanup@example.com",
                "roles": ["cleanup"],
                "secret": base64.urlsafe_b64encode(cleanup_secret).decode("ascii"),
            },
            {
                "key_id": "analytics-key",
                "principal": "svc-analytics@example.com",
                "roles": ["analytics"],
                "secret": base64.urlsafe_b64encode(analytics_secret).decode("ascii"),
            },
            {
                "key_id": "omni-key",
                "principal": "svc-omni@example.com",
                "roles": ["guard-rails", "cleanup", "analytics"],
                "secret": base64.urlsafe_b64encode(omni_secret).decode("ascii"),
            },
        ]
    }

    key_file = tmp_path / "service-accounts.json"
    key_file.write_text(json.dumps(keys_payload), encoding="utf-8")

    audit_dir = tmp_path / "audit"
    monkeypatch.setenv("HEPHAESTUS_SERVICE_ACCOUNT_KEYS_PATH", str(key_file))
    monkeypatch.setenv("HEPHAESTUS_AUDIT_LOG_DIR", str(audit_dir))
    monkeypatch.delenv("HEPHAESTUS_API_KEYS", raising=False)

    importlib.reload(auth_module)
    auth_module.reset_default_verifier()

    guard_key = auth_module.ServiceAccountKey(
        key_id="guard-key",
        principal="svc-guard@example.com",
        roles=frozenset({"guard-rails", "cleanup"}),
        secret=guard_secret,
        expires_at=None,
    )
    cleanup_key = auth_module.ServiceAccountKey(
        key_id="cleanup-key",
        principal="svc-cleanup@example.com",
        roles=frozenset({"cleanup"}),
        secret=cleanup_secret,
        expires_at=None,
    )
    analytics_key = auth_module.ServiceAccountKey(
        key_id="analytics-key",
        principal="svc-analytics@example.com",
        roles=frozenset({"analytics"}),
        secret=analytics_secret,
        expires_at=None,
    )
    omni_key = auth_module.ServiceAccountKey(
        key_id="omni-key",
        principal="svc-omni@example.com",
        roles=frozenset({"guard-rails", "cleanup", "analytics"}),
        secret=omni_secret,
        expires_at=None,
    )

    guard_token = auth_module.generate_service_account_token(
        guard_key,
        roles={"guard-rails"},
        issued_at=datetime.now(UTC) - timedelta(seconds=5),
        expires_at=datetime.now(UTC) + timedelta(hours=1),
    )
    cleanup_token = auth_module.generate_service_account_token(
        cleanup_key,
        roles={"cleanup"},
        expires_at=datetime.now(UTC) + timedelta(hours=1),
    )
    analytics_token = auth_module.generate_service_account_token(
        analytics_key,
        roles={"analytics"},
        expires_at=datetime.now(UTC) + timedelta(hours=1),
    )
    omni_token = auth_module.generate_service_account_token(
        omni_key,
        roles=omni_key.roles,
        expires_at=datetime.now(UTC) + timedelta(hours=1),
    )

    yield ServiceAccountContext(
        guard_token=guard_token,
        cleanup_token=cleanup_token,
        analytics_token=analytics_token,
        omni_token=omni_token,
        audit_dir=audit_dir,
    )

    auth_module.reset_default_verifier()


@pytest_asyncio.fixture
async def rest_app_client(
    service_account_environment: ServiceAccountContext,
) -> AsyncIterator[tuple[Any, Any]]:
    """Provide an HTTPX async client bound to the FastAPI app."""

    pytest.importorskip("fastapi")
    httpx = pytest.importorskip("httpx")

    import importlib

    rest_module = importlib.import_module("hephaestus.api.rest.app")
    rest_module = importlib.reload(rest_module)
    fastapi_app = rest_module.app

    transport = httpx.ASGITransport(app=fastapi_app)
    try:
        async with httpx.AsyncClient(transport=transport, base_url="http://test") as client:
            yield client, rest_module
    finally:
        await transport.aclose()
