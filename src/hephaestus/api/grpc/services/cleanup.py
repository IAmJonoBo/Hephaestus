from __future__ import annotations

import logging
from typing import cast

import grpc

from hephaestus.api import auth
from hephaestus.api.grpc.protos import hephaestus_pb2, hephaestus_pb2_grpc
from hephaestus.api.service import run_cleanup_summary
from hephaestus.audit import AuditStatus, record_audit_event

logger = logging.getLogger(__name__)


async def _require_principal(
    context: grpc.aio.ServicerContext,
) -> auth.AuthenticatedPrincipal:
    principal = cast(auth.AuthenticatedPrincipal | None, getattr(context, "principal", None))
    if principal is None:
        await context.abort(grpc.StatusCode.UNAUTHENTICATED, "Missing authentication principal")
        raise RuntimeError("unreachable")
    return principal


class CleanupServiceServicer(hephaestus_pb2_grpc.CleanupServiceServicer):
    """Implementation of CleanupService gRPC service."""

    async def Clean(
        self,
        request: hephaestus_pb2.CleanupRequest,
        context: grpc.aio.ServicerContext,
    ) -> hephaestus_pb2.CleanupResponse:
        principal = await _require_principal(context)
        operation = "grpc.cleanup.run"
        parameters = {
            "root": request.root or "",
            "deep_clean": request.deep_clean,
            "dry_run": request.dry_run,
        }

        try:
            summary = run_cleanup_summary(
                principal=principal,
                root=request.root or None,
                deep_clean=request.deep_clean,
                dry_run=request.dry_run,
            )
        except auth.AuthorizationError as exc:
            record_audit_event(
                principal,
                operation=operation,
                parameters=parameters,
                outcome={"error": str(exc)},
                status=AuditStatus.DENIED,
                protocol="grpc",
            )
            await context.abort(grpc.StatusCode.PERMISSION_DENIED, str(exc))
        except Exception as exc:  # pragma: no cover - defensive guard
            record_audit_event(
                principal,
                operation=operation,
                parameters=parameters,
                outcome={"error": str(exc)},
                status=AuditStatus.FAILED,
                protocol="grpc",
            )
            logger.exception("Cleanup execution failed")
            await context.abort(grpc.StatusCode.INTERNAL, str(exc))

        deleted_paths = (
            summary["removed_paths"] if not request.dry_run else summary["preview_paths"]
        )

        manifest = {
            key: int(value)
            for key, value in summary["manifest"].items()
            if isinstance(value, (int, float))
        }

        record_audit_event(
            principal,
            operation=operation,
            parameters=parameters,
            outcome={"files": summary["files"], "bytes": summary["bytes"]},
            status=AuditStatus.SUCCESS,
            protocol="grpc",
        )

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
        principal = await _require_principal(context)
        operation = "grpc.cleanup.preview"
        parameters = {
            "root": request.root or "",
            "deep_clean": request.deep_clean,
        }

        try:
            summary = run_cleanup_summary(
                principal=principal,
                root=request.root or None,
                deep_clean=request.deep_clean,
                dry_run=True,
            )
        except auth.AuthorizationError as exc:
            record_audit_event(
                principal,
                operation=operation,
                parameters=parameters,
                outcome={"error": str(exc)},
                status=AuditStatus.DENIED,
                protocol="grpc",
            )
            await context.abort(grpc.StatusCode.PERMISSION_DENIED, str(exc))
        except Exception as exc:  # pragma: no cover - defensive guard
            record_audit_event(
                principal,
                operation=operation,
                parameters=parameters,
                outcome={"error": str(exc)},
                status=AuditStatus.FAILED,
                protocol="grpc",
            )
            logger.exception("PreviewCleanup failed")
            await context.abort(grpc.StatusCode.INTERNAL, str(exc))

        manifest = {
            key: int(value)
            for key, value in summary["manifest"].items()
            if isinstance(value, (int, float))
        }

        record_audit_event(
            principal,
            operation=operation,
            parameters=parameters,
            outcome={"files": summary["files"], "bytes": summary["bytes"]},
            status=AuditStatus.SUCCESS,
            protocol="grpc",
        )

        return hephaestus_pb2.CleanupPreview(
            files_to_delete=summary["files"],
            size_to_free=summary["bytes"],
            paths=summary["preview_paths"],
            preview_manifest=manifest,
        )
