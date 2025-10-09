"""Tests for API module structure (ADR-0004 Phase 1)."""

from __future__ import annotations

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
