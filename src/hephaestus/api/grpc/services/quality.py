"""Quality Service implementation for gRPC."""

from __future__ import annotations

import logging
from collections.abc import AsyncIterator

import grpc

from hephaestus.api.grpc.protos import hephaestus_pb2, hephaestus_pb2_grpc
from hephaestus.api.service import detect_drift_summary, evaluate_guard_rails_async

logger = logging.getLogger(__name__)


class QualityServiceServicer(hephaestus_pb2_grpc.QualityServiceServicer):
    """Implementation of QualityService gRPC service."""

    async def RunGuardRails(
        self,
        request: hephaestus_pb2.GuardRailsRequest,
        context: grpc.aio.ServicerContext,
    ) -> hephaestus_pb2.GuardRailsResponse:
        """Run guard-rails quality pipeline (blocking).

        Args:
            request: Guard-rails configuration
            context: gRPC context

        Returns:
            Guard-rails execution results
        """
        logger.info(f"RunGuardRails called: no_format={request.no_format}")

        execution = await evaluate_guard_rails_async(
            no_format=request.no_format,
            workspace=request.workspace or None,
            drift_check=request.drift_check,
            auto_remediate=request.auto_remediate,
        )

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
        """Run guard-rails with streaming progress updates.

        Args:
            request: Guard-rails configuration
            context: gRPC context

        Yields:
            Progress updates for each stage
        """
        logger.info(f"RunGuardRailsStream called: no_format={request.no_format}")

        execution = await evaluate_guard_rails_async(
            no_format=request.no_format,
            workspace=request.workspace or None,
            drift_check=request.drift_check,
            auto_remediate=request.auto_remediate,
        )

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

    async def CheckDrift(
        self,
        request: hephaestus_pb2.DriftRequest,
        context: grpc.aio.ServicerContext,
    ) -> hephaestus_pb2.DriftResponse:
        """Check for tool version drift.

        Args:
            request: Drift check configuration
            context: gRPC context

        Returns:
            Drift detection results
        """
        logger.info(f"CheckDrift called: workspace={request.workspace}")

        summary = detect_drift_summary(request.workspace or None)

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
