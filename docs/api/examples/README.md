# gRPC API Examples

This directory contains example client code for the Hephaestus gRPC API.

## Overview

The Hephaestus gRPC API provides high-performance, strongly-typed access to quality gates, cleanup operations, and analytics. It supports:

- **Three Services**: QualityService, CleanupService, AnalyticsService
- **Streaming RPCs**: Real-time progress updates for long-running operations
- **Protocol Buffers**: Type-safe message definitions
- **gRPC Reflection**: Service discovery and debugging support

## Prerequisites

```bash
# Install gRPC dependencies
uv sync --extra grpc

# Or with pip
pip install grpcio grpcio-tools grpcio-reflection
```

## Starting the Server

```bash
# Start gRPC server on default port (50051)
uv run python -m hephaestus.api.grpc.server

# Or with custom port
uv run python -m hephaestus.api.grpc.server --port 50052
```

## Running Examples

### Quality Service Examples

```bash
# Run all quality service examples
uv run python docs/api/examples/grpc_quality_client.py
```

Examples include:
- **RunGuardRails**: Execute quality pipeline (blocking)
- **RunGuardRailsStream**: Execute with streaming progress updates
- **CheckDrift**: Detect tool version drift

### Cleanup Service Examples

```bash
# Run cleanup service examples
uv run python docs/api/examples/grpc_cleanup_client.py
```

Examples include:
- **PreviewCleanup**: Preview cleanup without executing
- **Clean**: Execute cleanup operation

### Analytics Service Examples

```bash
# Run analytics service examples
uv run python docs/api/examples/grpc_analytics_client.py
```

Examples include:
- **GetRankings**: Get refactoring priority rankings
- **GetHotspots**: Identify high-risk code areas

## Client Integration

### Python

```python
import asyncio
import grpc
from hephaestus.api.grpc.protos import hephaestus_pb2, hephaestus_pb2_grpc

async def main():
    async with grpc.aio.insecure_channel('localhost:50051') as channel:
        stub = hephaestus_pb2_grpc.QualityServiceStub(channel)
        
        # Create request
        request = hephaestus_pb2.GuardRailsRequest(
            no_format=False,
            workspace=".",
            drift_check=True,
        )
        
        # Call service
        response = await stub.RunGuardRails(request)
        print(f"Success: {response.success}")

if __name__ == "__main__":
    asyncio.run(main())
```

### Other Languages

The protocol buffer definitions can be used to generate clients in any language supported by gRPC:

```bash
# Generate Go client
protoc --go_out=. --go-grpc_out=. hephaestus.proto

# Generate Java client
protoc --java_out=. --grpc-java_out=. hephaestus.proto

# Generate TypeScript client
protoc --ts_out=. --grpc-web_out=import_style=typescript:. hephaestus.proto
```

## Service Reference

### QualityService

- `RunGuardRails(GuardRailsRequest) → GuardRailsResponse`
  - Execute complete quality pipeline
  - Returns summary of all quality gates
  
- `RunGuardRailsStream(GuardRailsRequest) → stream GuardRailsProgress`
  - Execute with streaming progress updates
  - Yields progress for each stage
  
- `CheckDrift(DriftRequest) → DriftResponse`
  - Detect tool version drift
  - Returns drift status and remediation commands

### CleanupService

- `Clean(CleanupRequest) → CleanupResponse`
  - Execute workspace cleanup
  - Returns files deleted and space freed
  
- `PreviewCleanup(CleanupRequest) → CleanupPreview`
  - Preview cleanup without executing
  - Returns what would be cleaned

### AnalyticsService

- `GetRankings(RankingsRequest) → RankingsResponse`
  - Get refactoring priority rankings
  - Supports multiple ranking strategies
  
- `GetHotspots(HotspotsRequest) → HotspotsResponse`
  - Identify high-risk code areas
  - Returns change frequency, complexity, risk scores

## Protocol Buffers

The complete protocol buffer definitions are in `src/hephaestus/api/grpc/protos/hephaestus.proto`.

To recompile after changes:

```bash
uv run python scripts/compile_protos.py
```

## Debugging with grpcurl

```bash
# Install grpcurl
go install github.com/fullstorydev/grpcurl/cmd/grpcurl@latest

# List available services
grpcurl -plaintext localhost:50051 list

# Describe a service
grpcurl -plaintext localhost:50051 describe hephaestus.v1.QualityService

# Call a method
grpcurl -plaintext -d '{"no_format": false}' \
  localhost:50051 hephaestus.v1.QualityService/RunGuardRails
```

## Error Handling

All gRPC methods use standard gRPC status codes:

- `OK` (0): Success
- `INVALID_ARGUMENT` (3): Invalid request parameters
- `NOT_FOUND` (5): Resource not found
- `INTERNAL` (13): Server error
- `UNAVAILABLE` (14): Service unavailable

Example error handling:

```python
try:
    response = await stub.RunGuardRails(request)
except grpc.RpcError as e:
    print(f"Error: {e.code()} - {e.details()}")
```

## Performance

- **Connection Pooling**: Reuse channels for multiple requests
- **Streaming**: Use streaming RPCs for long-running operations
- **Compression**: Enable gzip compression for large payloads
- **Timeouts**: Set appropriate timeouts for operations

```python
# Enable compression
channel = grpc.aio.insecure_channel(
    'localhost:50051',
    options=[('grpc.default_compression_algorithm', 'gzip')]
)

# Set timeout
response = await stub.RunGuardRails(request, timeout=300)
```

## Security

**Current Implementation**: Insecure channels (development only)

**Production Recommendations**:
- Use TLS/SSL encryption
- Implement authentication (API keys, JWT, mTLS)
- Add authorization checks
- Enable rate limiting
- Log security events

See ADR-0004 Sprint 4 for planned production hardening.

## Related Documentation

- [ADR-0004: REST/gRPC API](../../adr/0004-rest-grpc-api.md)
- [Protocol Buffer Definition](../../../src/hephaestus/api/grpc/protos/hephaestus.proto)
- [gRPC Server Implementation](../../../src/hephaestus/api/grpc/server.py)
