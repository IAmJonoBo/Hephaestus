from __future__ import annotations

import logging
from collections.abc import AsyncIterator
from typing import cast

import grpc

from hephaestus.api import auth
from hephaestus.api.grpc.protos import hephaestus_pb2, hephaestus_pb2_grpc
from hephaestus.api.service import detect_drift_summary, evaluate_guard_rails_async
from hephaestus.audit import AuditStatus, record_audit_event

logger = logging.getLogger(__name__)


async def _require_principal(
    context: grpc.aio.ServicerContext,
) -> auth.AuthenticatedPrincipal:
    principal = cast(
        auth.AuthenticatedPrincipal | None, getattr(context, "principal", None)
    )
    if principal is None:
        await context.abort(
            grpc.StatusCode.UNAUTHENTICATED, "Missing authentication principal"
        )
        raise RuntimeError("unreachable")
    return principal


class QualityServiceServicer(hephaestus_pb2_grpc.QualityServiceServicer):
    """Implementation of QualityService gRPC service."""

    async def RunGuardRails(
        self,
        request: hephaestus_pb2.GuardRailsRequest,
        context: grpc.aio.ServicerContext,
    ) -> hephaestus_pb2.GuardRailsResponse:
        principal = await _require_principal(context)
        operation = "grpc.guard-rails.run"
        parameters = {
            "no_format": request.no_format,
            "workspace": request.workspace or "",
            "drift_check": request.drift_check,
            "auto_remediate": request.auto_remediate,
        }

        try:
            execution = await evaluate_guard_rails_async(
                principal=principal,
                no_format=request.no_format,
                workspace=request.workspace or None,
                drift_check=request.drift_check,
                auto_remediate=request.auto_remediate,
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
            logger.exception("RunGuardRails failed")
            await context.abort(grpc.StatusCode.INTERNAL, str(exc))

        gates = [
            hephaestus_pb2.QualityGateResult(
                name=gate.name,
                passed=gate.passed,
                message=gate.message or "",
                duration=gate.duration,
                metadata={key: str(value) for key, value in gate.metadata.items()},
            )
            for gate in execution.gates
        ]

        record_audit_event(
            principal,
            operation=operation,
            parameters=parameters,
            outcome={"success": execution.success},
            status=AuditStatus.SUCCESS,
            protocol="grpc",
        )

        return hephaestus_pb2.GuardRailsResponse(
            success=execution.success,
            gates=gates,
            duration=execution.duration,
            task_id=f"guard-rails-{int(execution.duration * 1000)}",
        )

    async def RunGuardRailsStream(
        self,
        request: hephaestus_pb2.GuardRailsRequest,
        context: grpc.aio.ServicerContext,
    ) -> AsyncIterator[hephaestus_pb2.GuardRailsProgress]:
        principal = await _require_principal(context)
        operation = "grpc.guard-rails.stream"
        parameters = {
            "no_format": request.no_format,
            "workspace": request.workspace or "",
            "drift_check": request.drift_check,
            "auto_remediate": request.auto_remediate,
        }

        try:
            execution = await evaluate_guard_rails_async(
                principal=principal,
                no_format=request.no_format,
                workspace=request.workspace or None,
                drift_check=request.drift_check,
                auto_remediate=request.auto_remediate,
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
            logger.exception("RunGuardRailsStream failed")
            await context.abort(grpc.StatusCode.INTERNAL, str(exc))

        total = max(len(execution.gates), 1)
        for index, gate in enumerate(execution.gates, start=1):
            progress = int((index / total) * 100)
            yield hephaestus_pb2.GuardRailsProgress(
                stage=gate.name,
                progress=progress,
                message=gate.message or "",
                completed=False,
            )

        yield hephaestus_pb2.GuardRailsProgress(
            stage="complete",
            progress=100,
            message="Guard rails completed",
            completed=execution.success,
        )

        record_audit_event(
            principal,
            operation=operation,
            parameters=parameters,
            outcome={"success": execution.success},
            status=AuditStatus.SUCCESS,
            protocol="grpc",
        )

    async def CheckDrift(
        self,
        request: hephaestus_pb2.DriftRequest,
        context: grpc.aio.ServicerContext,
    ) -> hephaestus_pb2.DriftResponse:
        principal = await _require_principal(context)
        operation = "grpc.guard-rails.drift"
        parameters = {"workspace": request.workspace or ""}

        try:
            summary = detect_drift_summary(
                principal=principal, workspace=request.workspace or None
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
            logger.exception("CheckDrift failed")
            await context.abort(grpc.StatusCode.INTERNAL, str(exc))

        record_audit_event(
            principal,
            operation=operation,
            parameters=parameters,
            outcome={"has_drift": summary["has_drift"]},
            status=AuditStatus.SUCCESS,
            protocol="grpc",
        )

        return hephaestus_pb2.DriftResponse(
            has_drift=summary["has_drift"],
            drifts=[
                hephaestus_pb2.ToolDrift(
                    tool=entry["tool"],
                    expected_version=entry["expected"] or "",
                    installed_version=entry["actual"] or "",
                    status=entry["status"],
                )
                for entry in summary["drifts"]
            ],
            remediation_commands=summary["commands"],
        )
