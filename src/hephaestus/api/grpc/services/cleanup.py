"""Cleanup Service implementation for gRPC."""

from __future__ import annotations

import logging

import grpc

from hephaestus.api.grpc.protos import hephaestus_pb2, hephaestus_pb2_grpc
from hephaestus.api.service import run_cleanup_summary

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

        summary = run_cleanup_summary(
            root=request.root or None,
            deep_clean=request.deep_clean,
            dry_run=request.dry_run,
        )

        deleted_paths = summary["removed_paths"] if not request.dry_run else summary["preview_paths"]

        manifest = {
            key: int(value)
            for key, value in summary["manifest"].items()
            if isinstance(value, (int, float))
        }

        return hephaestus_pb2.CleanupResponse(
            files_deleted=summary["files"],
            size_freed=summary["bytes"],
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

        summary = run_cleanup_summary(
            root=request.root or None,
            deep_clean=request.deep_clean,
            dry_run=True,
        )

        manifest = {
            key: int(value)
            for key, value in summary["manifest"].items()
            if isinstance(value, (int, float))
        }

        return hephaestus_pb2.CleanupPreview(
            files_to_delete=summary["files"],
            size_to_free=summary["bytes"],
            paths=summary["preview_paths"],
            preview_manifest=manifest,
        )
