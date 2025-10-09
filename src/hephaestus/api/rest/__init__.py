"""REST API implementation (ADR-0004 Sprint 2).

This module contains the FastAPI application and endpoints for remote
invocation of Hephaestus functionality.

Example:
    # Start the API server
    uvicorn hephaestus.api.rest.app:app --host 0.0.0.0 --port 8000

    # Or programmatically
    from hephaestus.api.rest import app
    import uvicorn
    uvicorn.run(app)
"""

from __future__ import annotations

__all__ = ["app"]

try:
    from hephaestus.api.rest.app import app
except ImportError:
    # FastAPI not installed
    app = None  # type: ignore[assignment]
