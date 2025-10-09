"""Analytics Service implementation for gRPC."""

from __future__ import annotations

import logging

import grpc

from hephaestus.api.grpc.protos import hephaestus_pb2, hephaestus_pb2_grpc

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
            f"GetRankings called: strategy={request.strategy}, limit={request.limit}"
        )

        # Simulate rankings
        rankings = [
            hephaestus_pb2.FileRanking(
                file="src/main.py",
                score=8.5,
                metrics={"complexity": 45.0, "coverage": 65.0, "churn": 120.0},
            ),
            hephaestus_pb2.FileRanking(
                file="src/utils.py",
                score=7.2,
                metrics={"complexity": 38.0, "coverage": 72.0, "churn": 95.0},
            ),
            hephaestus_pb2.FileRanking(
                file="src/models.py",
                score=6.8,
                metrics={"complexity": 52.0, "coverage": 58.0, "churn": 88.0},
            ),
        ]

        # Apply limit
        if request.limit > 0:
            rankings = rankings[: request.limit]

        return hephaestus_pb2.RankingsResponse(
            rankings=rankings,
            strategy=request.strategy or "composite",
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
