"""Quality Service implementation for gRPC."""

from __future__ import annotations

import asyncio
import logging
from collections.abc import AsyncIterator

import grpc

from hephaestus.api.grpc.protos import hephaestus_pb2, hephaestus_pb2_grpc

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

        # Simulate guard-rails execution
        gates = []

        # Cleanup step
        if not request.no_format:
            gates.append(
                hephaestus_pb2.QualityGateResult(
                    name="cleanup", passed=True, message="Cleanup successful", duration=0.5
                )
            )

        # Add other gates
        gates.extend(
            [
                hephaestus_pb2.QualityGateResult(
                    name="ruff-check",
                    passed=True,
                    message="No issues found",
                    duration=1.2,
                ),
                hephaestus_pb2.QualityGateResult(
                    name="ruff-format",
                    passed=True,
                    message="Formatting complete",
                    duration=0.8,
                ),
                hephaestus_pb2.QualityGateResult(
                    name="mypy", passed=True, message="Type checking passed", duration=3.5
                ),
                hephaestus_pb2.QualityGateResult(
                    name="pytest",
                    passed=True,
                    message="All tests passed",
                    duration=10.2,
                ),
                hephaestus_pb2.QualityGateResult(
                    name="pip-audit",
                    passed=True,
                    message="No vulnerabilities found",
                    duration=2.1,
                ),
            ]
        )

        success = all(gate.passed for gate in gates)
        total_duration = sum(gate.duration for gate in gates)

        return hephaestus_pb2.GuardRailsResponse(
            success=success,
            gates=gates,
            duration=total_duration,
            task_id="guard-rails-001",
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

        stages = [
            ("cleanup", 16),
            ("ruff-check", 33),
            ("ruff-format", 50),
            ("mypy", 66),
            ("pytest", 83),
            ("pip-audit", 100),
        ]

        for stage_name, progress in stages:
            # Simulate work
            await asyncio.sleep(0.5)

            yield hephaestus_pb2.GuardRailsProgress(
                stage=stage_name,
                progress=progress,
                message=f"Executing {stage_name}...",
                completed=False,
            )

        # Final completion message
        yield hephaestus_pb2.GuardRailsProgress(
            stage="complete",
            progress=100,
            message="All quality gates passed",
            completed=True,
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

        # Simulate drift detection
        drifts = [
            hephaestus_pb2.ToolDrift(
                tool="ruff",
                expected_version="0.14.0",
                installed_version="0.13.9",
                status="minor_drift",
            )
        ]

        remediation = ["uv sync --upgrade-package ruff"]

        return hephaestus_pb2.DriftResponse(
            has_drift=True,
            drifts=drifts,
            remediation_commands=remediation,
        )
