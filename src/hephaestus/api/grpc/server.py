"""gRPC server for Hephaestus API."""

from __future__ import annotations

import asyncio
import logging
from collections.abc import Awaitable, Callable
from typing import Any

import grpc
from grpc_reflection.v1alpha import reflection

from hephaestus.api import auth
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
    server = grpc.aio.server(interceptors=[ServiceAccountAuthInterceptor()])

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


class ServiceAccountAuthInterceptor(grpc.aio.ServerInterceptor):
    """Authenticate incoming requests using service-account bearer tokens."""

    def __init__(self, verifier: auth.ServiceAccountVerifier | None = None) -> None:
        self._verifier = verifier or auth.get_default_verifier()

    async def intercept_service(
        self,
        continuation: Callable[[grpc.HandlerCallDetails], Awaitable[grpc.RpcMethodHandler | None]],
        handler_call_details: grpc.HandlerCallDetails,
    ) -> grpc.RpcMethodHandler | None:
        handler = await continuation(handler_call_details)
        if handler is None:
            return None

        if handler.unary_unary:

            async def unary_unary(request: Any, context: grpc.aio.ServicerContext) -> Any:
                principal = await self._authenticate(context)
                context.principal = principal
                return await handler.unary_unary(request, context)

            return grpc.aio.unary_unary_rpc_method_handler(
                unary_unary,
                request_deserializer=handler.request_deserializer,
                response_serializer=handler.response_serializer,
            )

        if handler.unary_stream:

            async def unary_stream(request: Any, context: grpc.aio.ServicerContext) -> Any:
                principal = await self._authenticate(context)
                context.principal = principal
                async for response in handler.unary_stream(request, context):
                    yield response

            return grpc.aio.unary_stream_rpc_method_handler(
                unary_stream,
                request_deserializer=handler.request_deserializer,
                response_serializer=handler.response_serializer,
            )

        if handler.stream_unary:

            async def stream_unary(request_iter: Any, context: grpc.aio.ServicerContext) -> Any:
                principal = await self._authenticate(context)
                context.principal = principal
                return await handler.stream_unary(request_iter, context)

            return grpc.aio.stream_unary_rpc_method_handler(
                stream_unary,
                request_deserializer=handler.request_deserializer,
                response_serializer=handler.response_serializer,
            )

        if handler.stream_stream:

            async def stream_stream(request_iter: Any, context: grpc.aio.ServicerContext) -> Any:
                principal = await self._authenticate(context)
                context.principal = principal
                async for response in handler.stream_stream(request_iter, context):
                    yield response

            return grpc.aio.stream_stream_rpc_method_handler(
                stream_stream,
                request_deserializer=handler.request_deserializer,
                response_serializer=handler.response_serializer,
            )

        return handler

    async def _authenticate(self, context: grpc.aio.ServicerContext) -> auth.AuthenticatedPrincipal:
        metadata = {md.key: md.value for md in context.invocation_metadata()}
        header = metadata.get("authorization")
        if header is None:
            await context.abort(grpc.StatusCode.UNAUTHENTICATED, "Missing authorization metadata")
            raise RuntimeError("unreachable")

        token = header.split(" ", 1)
        if len(token) != 2 or token[0].lower() != "bearer":
            await context.abort(
                grpc.StatusCode.UNAUTHENTICATED,
                "Authorization header must use Bearer scheme",
            )
            raise RuntimeError("unreachable")

        try:
            return self._verifier.verify_bearer_token(token[1])
        except auth.AuthenticationError as exc:  # pragma: no cover - defensive guard
            await context.abort(grpc.StatusCode.UNAUTHENTICATED, str(exc))
            raise RuntimeError("unreachable") from exc
