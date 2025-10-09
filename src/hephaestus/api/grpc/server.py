"""gRPC server for Hephaestus API."""

from __future__ import annotations

import asyncio
import logging
from typing import Any

import grpc
from grpc_reflection.v1alpha import reflection

from hephaestus.api.grpc.protos import hephaestus_pb2, hephaestus_pb2_grpc
from hephaestus.api.grpc.services import (
    AnalyticsServiceServicer,
    CleanupServiceServicer,
    QualityServiceServicer,
)

logger = logging.getLogger(__name__)


async def serve(
    port: int = 50051,
    max_workers: int = 10,
    reflection_enabled: bool = True,
    tls_cert_path: str | None = None,
    tls_key_path: str | None = None,
) -> None:
    """Start gRPC server.

    Args:
        port: Port to listen on
        max_workers: Maximum number of worker threads
        reflection_enabled: Enable gRPC reflection for debugging
        tls_cert_path: Path to TLS certificate file (Sprint 4 - production hardening)
        tls_key_path: Path to TLS private key file (Sprint 4 - production hardening)

    Note:
        TLS/SSL support is planned for Sprint 4 (ADR-0004).
        Currently only insecure channels are supported for development.
    """
    server = grpc.aio.server()

    # Add services
    hephaestus_pb2_grpc.add_QualityServiceServicer_to_server(QualityServiceServicer(), server)
    hephaestus_pb2_grpc.add_CleanupServiceServicer_to_server(CleanupServiceServicer(), server)
    hephaestus_pb2_grpc.add_AnalyticsServiceServicer_to_server(AnalyticsServiceServicer(), server)

    # Enable reflection for debugging
    if reflection_enabled:
        service_names = (
            hephaestus_pb2.DESCRIPTOR.services_by_name["QualityService"].full_name,
            hephaestus_pb2.DESCRIPTOR.services_by_name["CleanupService"].full_name,
            hephaestus_pb2.DESCRIPTOR.services_by_name["AnalyticsService"].full_name,
            reflection.SERVICE_NAME,
        )
        reflection.enable_server_reflection(service_names, server)
        logger.info("gRPC reflection enabled")

    # Bind to port
    # TODO(Sprint 4): Add TLS/SSL support when tls_cert_path and tls_key_path are provided
    # See ADR-0004 Sprint 4 for production hardening requirements
    if tls_cert_path and tls_key_path:
        logger.warning(
            "TLS/SSL configuration provided but not yet implemented. "
            "Using insecure channel. TLS support is planned for Sprint 4 (ADR-0004)."
        )
    server.add_insecure_port(f"[::]:{port}")

    logger.info(f"Starting gRPC server on port {port}")
    await server.start()

    try:
        await server.wait_for_termination()
    except KeyboardInterrupt:
        logger.info("Shutting down gRPC server...")
        await server.stop(grace=5)


def run_server(**kwargs: Any) -> None:
    """Run gRPC server (blocking).

    Args:
        **kwargs: Arguments passed to serve()
    """
    asyncio.run(serve(**kwargs))


if __name__ == "__main__":
    logging.basicConfig(
        level=logging.INFO,
        format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
    )
    run_server()
