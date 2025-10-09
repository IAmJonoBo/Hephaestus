from __future__ import annotations

from collections.abc import AsyncIterator
from typing import Any

import pytest
import pytest_asyncio


@pytest_asyncio.fixture
async def rest_app_client() -> AsyncIterator[tuple[Any, Any]]:
    """Provide an HTTPX async client bound to the FastAPI app.

    The fixture skips automatically when FastAPI/httpx are unavailable so the
    wider test suite can run in environments without the optional API extras.
    """
    pytest.importorskip("fastapi")
    httpx = pytest.importorskip("httpx")

    import importlib

    rest_module = importlib.import_module("hephaestus.api.rest.app")
    fastapi_app = rest_module.app

    transport = httpx.ASGITransport(app=fastapi_app)
    try:
        async with httpx.AsyncClient(transport=transport, base_url="http://test") as client:
            yield client, rest_module
    finally:
        await transport.aclose()
