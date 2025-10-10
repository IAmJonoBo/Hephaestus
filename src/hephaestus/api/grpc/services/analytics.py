"""Analytics Service implementation for gRPC."""

from __future__ import annotations

import logging
from collections.abc import AsyncIterator

import grpc

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
        logger.info(f"GetHotspots called: limit={request.limit}")

        # Simulate hotspot detection
        hotspots = [
            hephaestus_pb2.Hotspot(
                file="src/main.py",
                change_frequency=120,
                complexity=45,
                risk_score=8.5,
            ),
            hephaestus_pb2.Hotspot(
                file="src/utils.py",
                change_frequency=95,
                complexity=38,
                risk_score=7.2,
            ),
            hephaestus_pb2.Hotspot(
                file="src/models.py",
                change_frequency=88,
                complexity=52,
                risk_score=6.8,
            ),
        ]

        # Apply limit
        if request.limit > 0:
            hotspots = hotspots[: request.limit]

        return hephaestus_pb2.HotspotsResponse(hotspots=hotspots)

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
