from __future__ import annotations

import logging
from collections.abc import AsyncIterator
from typing import cast

import grpc

from hephaestus.analytics import RankingStrategy
from hephaestus.analytics_streaming import global_ingestor
from hephaestus.api import auth
from hephaestus.api.grpc.protos import hephaestus_pb2, hephaestus_pb2_grpc
from hephaestus.api.service import compute_hotspots, compute_rankings
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


class AnalyticsServiceServicer(hephaestus_pb2_grpc.AnalyticsServiceServicer):
    """Implementation of AnalyticsService gRPC service."""

    async def GetRankings(
        self,
        request: hephaestus_pb2.RankingsRequest,
        context: grpc.aio.ServicerContext,
    ) -> hephaestus_pb2.RankingsResponse:
        principal = await _require_principal(context)
        operation = "grpc.analytics.rankings"
        parameters = {
            "strategy": request.strategy or RankingStrategy.RISK_WEIGHTED.value,
            "limit": request.limit or 20,
        }

        try:
            strategy_value = request.strategy or RankingStrategy.RISK_WEIGHTED.value
            strategy = RankingStrategy(strategy_value)
            rankings = compute_rankings(
                principal=principal,
                strategy=strategy,
                limit=request.limit or 20,
            )
        except ValueError as exc:
            await context.abort(grpc.StatusCode.INVALID_ARGUMENT, str(exc))
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
            logger.exception("GetRankings failed")
            await context.abort(grpc.StatusCode.INTERNAL, str(exc))

        record_audit_event(
            principal,
            operation=operation,
            parameters=parameters,
            outcome={"count": len(rankings)},
            status=AuditStatus.SUCCESS,
            protocol="grpc",
        )

        return hephaestus_pb2.RankingsResponse(
            rankings=[
                hephaestus_pb2.FileRanking(
                    file=item["path"],
                    score=item["score"],
                    metrics={
                        "churn": float(item["churn"]),
                        "coverage": float(item["coverage"] or 0.0),
                        "uncovered_lines": float(item["uncovered_lines"] or 0.0),
                    },
                )
                for item in rankings
            ],
            strategy=strategy.value,
        )

    async def GetHotspots(
        self,
        request: hephaestus_pb2.HotspotsRequest,
        context: grpc.aio.ServicerContext,
    ) -> hephaestus_pb2.HotspotsResponse:
        principal = await _require_principal(context)
        operation = "grpc.analytics.hotspots"
        parameters = {"limit": request.limit or 20}

        try:
            hotspots = compute_hotspots(principal=principal, limit=request.limit or 20)
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
            logger.exception("GetHotspots failed")
            await context.abort(grpc.StatusCode.INTERNAL, str(exc))

        record_audit_event(
            principal,
            operation=operation,
            parameters=parameters,
            outcome={"count": len(hotspots)},
            status=AuditStatus.SUCCESS,
            protocol="grpc",
        )

        return hephaestus_pb2.HotspotsResponse(
            hotspots=[
                hephaestus_pb2.Hotspot(
                    file=item["path"],
                    change_frequency=int(item["change_frequency"]),
                    complexity=int(item["complexity"]),
                    risk_score=float(item["risk_score"]),
                )
                for item in hotspots
            ]
        )

    async def StreamIngest(
        self,
        request_iterator: AsyncIterator[hephaestus_pb2.AnalyticsEvent],
        context: grpc.aio.ServicerContext,
    ) -> hephaestus_pb2.AnalyticsIngestResponse:
        principal = await _require_principal(context)
        operation = "grpc.analytics.stream_ingest"

        accepted = 0
        rejected = 0

        try:
            auth.ServiceAccountVerifier.require_role(principal, auth.Role.ANALYTICS.value)

            async for event in request_iterator:
                payload = {
                    "source": event.source,
                    "kind": event.kind,
                    "value": event.value,
                    "unit": event.unit or None,
                    "metrics": dict(event.metrics),
                    "metadata": dict(event.metadata),
                    "timestamp": event.timestamp or None,
                }

                if global_ingestor.ingest_mapping(payload):
                    accepted += 1
                else:
                    rejected += 1
        except auth.AuthorizationError as exc:
            record_audit_event(
                principal,
                operation=operation,
                parameters={},
                outcome={"error": str(exc)},
                status=AuditStatus.DENIED,
                protocol="grpc",
            )
            await context.abort(grpc.StatusCode.PERMISSION_DENIED, str(exc))
        except Exception as exc:  # pragma: no cover - defensive guard
            record_audit_event(
                principal,
                operation=operation,
                parameters={},
                outcome={"error": str(exc)},
                status=AuditStatus.FAILED,
                protocol="grpc",
            )
            logger.exception("StreamIngest failed")
            await context.abort(grpc.StatusCode.INTERNAL, str(exc))

        record_audit_event(
            principal,
            operation=operation,
            parameters={"events_received": accepted + rejected},
            outcome={"accepted": accepted, "rejected": rejected},
            status=AuditStatus.SUCCESS,
            protocol="grpc",
        )

        return hephaestus_pb2.AnalyticsIngestResponse(accepted=accepted, rejected=rejected)
