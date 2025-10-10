"""Analytics Service implementation for gRPC."""

from __future__ import annotations

import logging
from collections.abc import AsyncIterator

import grpc

from hephaestus.analytics import RankingStrategy
from hephaestus.analytics_streaming import global_ingestor
from hephaestus.api.grpc.protos import hephaestus_pb2, hephaestus_pb2_grpc
from hephaestus.api.service import compute_hotspots, compute_rankings

logger = logging.getLogger(__name__)


class AnalyticsServiceServicer(hephaestus_pb2_grpc.AnalyticsServiceServicer):
    """Implementation of AnalyticsService gRPC service."""

    async def GetRankings(
        self,
        request: hephaestus_pb2.RankingsRequest,
        context: grpc.aio.ServicerContext,
    ) -> hephaestus_pb2.RankingsResponse:
        """Get refactoring rankings.

        Args:
            request: Rankings request configuration
            context: gRPC context

        Returns:
            File rankings
        """
        logger.info(
            "GetRankings called", extra={"strategy": request.strategy, "limit": request.limit}
        )

        strategy_value = request.strategy or RankingStrategy.RISK_WEIGHTED.value
        strategy = RankingStrategy(strategy_value)

        rankings = compute_rankings(strategy=strategy, limit=request.limit or 20)

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
        """Get code hotspots.

        Args:
            request: Hotspots request configuration
            context: gRPC context

        Returns:
            Code hotspots
        """
        logger.info("GetHotspots called", extra={"limit": request.limit})

        hotspots = compute_hotspots(limit=request.limit or 20)

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
        """Stream analytics events into the shared ingestor."""

        accepted = 0
        rejected = 0

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

        return hephaestus_pb2.AnalyticsIngestResponse(accepted=accepted, rejected=rejected)
