"""Cleanup Service implementation for gRPC."""

from __future__ import annotations

import logging

import grpc

from hephaestus.api.grpc.protos import hephaestus_pb2, hephaestus_pb2_grpc

logger = logging.getLogger(__name__)


class CleanupServiceServicer(hephaestus_pb2_grpc.CleanupServiceServicer):
    """Implementation of CleanupService gRPC service."""

    async def Clean(
        self,
        request: hephaestus_pb2.CleanupRequest,
        context: grpc.aio.ServicerContext,
    ) -> hephaestus_pb2.CleanupResponse:
        """Execute cleanup operation.

        Args:
            request: Cleanup configuration
            context: gRPC context

        Returns:
            Cleanup execution results
        """
        logger.info(
            f"Clean called: root={request.root}, deep={request.deep_clean}, "
            f"dry_run={request.dry_run}"
        )

        # Simulate cleanup execution
        manifest = {
            "__pycache__": 15,
            ".pytest_cache": 8,
            "*.pyc": 42,
            ".mypy_cache": 5,
        }

        deleted_paths = [
            "src/__pycache__",
            "tests/__pycache__",
            ".pytest_cache",
            ".mypy_cache",
        ]

        return hephaestus_pb2.CleanupResponse(
            files_deleted=70,
            size_freed=1024000,  # 1MB
            deleted_paths=deleted_paths,
            manifest=manifest,
        )

    async def PreviewCleanup(
        self,
        request: hephaestus_pb2.CleanupRequest,
        context: grpc.aio.ServicerContext,
    ) -> hephaestus_pb2.CleanupPreview:
        """Preview cleanup without executing.

        Args:
            request: Cleanup configuration
            context: gRPC context

        Returns:
            Cleanup preview results
        """
        logger.info(f"PreviewCleanup called: root={request.root}")

        # Simulate preview
        preview_manifest = {
            "__pycache__": 15,
            ".pytest_cache": 8,
            "*.pyc": 42,
            ".mypy_cache": 5,
        }

        paths = [
            "src/__pycache__",
            "tests/__pycache__",
            ".pytest_cache",
            ".mypy_cache",
        ]

        return hephaestus_pb2.CleanupPreview(
            files_to_delete=70,
            size_to_free=1024000,
            paths=paths,
            preview_manifest=preview_manifest,
        )
