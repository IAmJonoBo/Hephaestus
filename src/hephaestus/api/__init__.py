"""REST/gRPC API for remote invocation (ADR-0004 Phase 1).

This module provides the foundation for remote API access to Hephaestus
functionality, supporting both REST and gRPC protocols.

Note: This is Phase 1 (Foundation) - only module structure and OpenAPI spec.
Full implementation in future phases.
"""

from __future__ import annotations

__all__ = ["API_VERSION"]

API_VERSION = "v1"
