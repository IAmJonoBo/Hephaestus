# ADR 0004: REST/gRPC API for Remote Invocation

- Status: Sprint 3 Complete (2025-01-16)
- Date: 2025-01-11
- Last Updated: 2025-01-16
- Supersedes: N/A
- Superseded by: N/A

## Context

Hephaestus is currently a command-line tool that runs locally. However, several use cases require remote invocation:

- **CI/CD Orchestration**: Build systems need to invoke Hephaestus programmatically
- **AI Agent Integration**: AI assistants need structured API access beyond CLI
- **Centralized Quality Dashboard**: Teams want aggregated quality metrics across projects
- **Remote Development**: Developers want to trigger quality checks on remote environments
- **Integration Testing**: Test frameworks need programmatic access to quality gates
- **Webhook Triggers**: External systems want to trigger quality checks on events

Current limitations:

- CLI-only interface requires subprocess execution
- No structured request/response beyond exit codes
- No real-time progress updates
- No concurrent execution tracking
- Difficult to integrate with non-Python systems

The `schema` command provides structured metadata, but doesn't enable remote execution.

### Motivating Use Cases

1. **AI Agents**: GitHub Copilot wants to invoke `guard-rails` and get structured results
2. **CI Dashboard**: Engineering teams want a web dashboard showing quality across all repos
3. **Automated Remediation**: Systems want to trigger cleanup when disk space is low
4. **Code Review Bots**: PR bots want to run quality checks and comment results
5. **Remote Debugging**: Developers want to trigger drift detection on production systems
6. **Multi-Repo Workflows**: Monorepo tools want to orchestrate quality checks across repos

### Requirements

- **Backward Compatible**: CLI must remain primary interface
- **Stateless**: API should not require server-side state
- **Secure**: Authentication and authorization required
- **Observable**: Integrated with OpenTelemetry (ADR-0003)
- **Async**: Support long-running operations with progress tracking
- **Multiple Protocols**: Support both REST (HTTP) and gRPC

## Decision

We will implement **dual-protocol API** with both REST and gRPC endpoints:

1. **REST API**: For web clients, AI agents, and HTTP-based integrations
2. **gRPC API**: For high-performance, strongly-typed integrations
3. **Unified Implementation**: Shared business logic with protocol adapters
4. **OpenAPI Spec**: Machine-readable REST API specification
5. **Protocol Buffers**: gRPC service definitions

### Architecture

```
hephaestus/
├── src/hephaestus/
│   ├── api/
│   │   ├── __init__.py
│   │   ├── server.py              # API server implementation
│   │   ├── rest/
│   │   │   ├── __init__.py
│   │   │   ├── app.py              # FastAPI application
│   │   │   ├── routes/
│   │   │   │   ├── quality.py      # Quality gates endpoints
│   │   │   │   ├── cleanup.py      # Cleanup endpoints
│   │   │   │   ├── analytics.py    # Analytics endpoints
│   │   │   │   └── schema.py       # Schema endpoints
│   │   │   └── models.py           # Pydantic models
│   │   ├── grpc/
│   │   │   ├── __init__.py
│   │   │   ├── server.py           # gRPC server
│   │   │   ├── services/
│   │   │   │   ├── quality.py      # Quality service
│   │   │   │   ├── cleanup.py      # Cleanup service
│   │   │   │   └── analytics.py    # Analytics service
│   │   │   └── protos/
│   │   │       └── hephaestus.proto # Protocol definitions
│   │   ├── auth.py                 # Authentication/authorization
│   │   ├── middleware.py           # Logging, telemetry, etc.
│   │   └── tasks.py                # Async task management
│   └── cli.py                      # CLI optionally starts API server

docs/
├── api/
│   ├── openapi.yaml                # OpenAPI 3.0 spec
│   ├── rest-examples.md            # REST API examples
│   └── grpc-examples.md            # gRPC examples
```

### REST API Design

**Base URL**: `http://localhost:8000/api/v1`

**Core Endpoints**:

```yaml
paths:
  /quality/guard-rails:
    post:
      summary: Run comprehensive quality pipeline
      requestBody:
        content:
          application/json:
            schema:
              type: object
              properties:
                no_format:
                  type: boolean
                workspace:
                  type: string
                drift_check:
                  type: boolean
      responses:
        200:
          content:
            application/json:
              schema:
                type: object
                properties:
                  success: boolean
                  gates: array
                  duration: number
                  task_id: string

  /cleanup:
    post:
      summary: Clean workspace artifacts
      requestBody:
        content:
          application/json:
            schema:
              type: object
              properties:
                root: string
                deep_clean: boolean
                dry_run: boolean
      responses:
        200:
          content:
            application/json:
              schema:
                type: object
                properties:
                  files_deleted: integer
                  size_freed: integer
                  manifest: object

  /analytics/rankings:
    get:
      summary: Get refactoring rankings
      parameters:
        - name: strategy
          in: query
          schema:
            type: string
            enum: [risk_weighted, coverage_first, churn_based, composite]
        - name: limit
          in: query
          schema:
            type: integer
      responses:
        200:
          content:
            application/json:
              schema:
                type: object
                properties:
                  rankings: array
                  strategy: string

  /tasks/{task_id}:
    get:
      summary: Get async task status
      responses:
        200:
          content:
            application/json:
              schema:
                type: object
                properties:
                  task_id: string
                  status: string
                  progress: number
                  result: object
```

### gRPC Service Definition

```protobuf
syntax = "proto3";

package hephaestus.v1;

service QualityService {
  rpc RunGuardRails(GuardRailsRequest) returns (GuardRailsResponse);
  rpc RunGuardRailsStream(GuardRailsRequest) returns (stream GuardRailsProgress);
  rpc CheckDrift(DriftRequest) returns (DriftResponse);
}

service CleanupService {
  rpc Clean(CleanupRequest) returns (CleanupResponse);
  rpc PreviewCleanup(CleanupRequest) returns (CleanupPreview);
}

service AnalyticsService {
  rpc GetRankings(RankingsRequest) returns (RankingsResponse);
  rpc GetHotspots(HotspotsRequest) returns (HotspotsResponse);
}

message GuardRailsRequest {
  bool no_format = 1;
  string workspace = 2;
  bool drift_check = 3;
  map<string, string> env = 4;
}

message GuardRailsResponse {
  bool success = 1;
  repeated QualityGateResult gates = 2;
  double duration = 3;
  string task_id = 4;
}

message GuardRailsProgress {
  string stage = 1;
  int32 progress = 2;
  string message = 3;
  bool completed = 4;
}

message QualityGateResult {
  string name = 1;
  bool passed = 2;
  string message = 3;
  double duration = 4;
  map<string, string> metadata = 5;
}
```

### Authentication & Authorization

- **Service Accounts**: API clients authenticate using HMAC signed bearer tokens. Keys are
  provisioned as JSON under `.hephaestus/service-accounts.json` (or via the
  `HEPHAESTUS_SERVICE_ACCOUNT_KEYS_PATH` override):

  ```json
  {
    "keys": [
      {
        "key_id": "ops-cleanup",
        "principal": "cleanup@hephaestus",
        "roles": ["cleanup"],
        "secret": "<base64-url-encoded-secret>",
        "expires_at": null
      }
    ]
  }
  ```

- **Token Format**: Tokens follow compact JWS semantics (`header.payload.signature`). Headers use
  `{"alg": "HS256", "typ": "JWT", "kid": "<key_id>"}`. Payload claims include `sub`,
  `roles`, `iat`, and `exp`. Tokens are rejected if the signature is invalid, expired, or asserts
  roles not granted to the originating key.

- **REST Enforcement**: FastAPI dependencies verify bearer tokens and inject an
  `AuthenticatedPrincipal`. Role checks are performed at the service layer before executing
  guard-rails, cleanup, or analytics operations. Unauthorized requests return 401/403 with
  structured audit trails.

- **gRPC Enforcement**: A `ServiceAccountAuthInterceptor` validates the `authorization` metadata on
  every RPC, attaches the principal to the `ServicerContext`, and aborts unauthenticated calls with
  `UNAUTHENTICATED`. Individual service methods enforce role-specific permissions and emit audit
  events on success or denial.

- **Audit Logging**: Every REST/gRPC operation records a JSONL entry under `.hephaestus/audit/` and
  emits a telemetry event (`api.audit`) with the principal, operation, parameters, and outcome. Logs
  fail closed—authorization failures are always captured prior to returning an error.

### Async Task Management

```python
from uuid import uuid4
from dataclasses import dataclass
from enum import Enum

class TaskStatus(Enum):
    PENDING = "pending"
    RUNNING = "running"
    COMPLETED = "completed"
    FAILED = "failed"

@dataclass
class Task:
    id: str
    status: TaskStatus
    progress: float
    result: Any = None
    error: str = None

task_registry: dict[str, Task] = {}

async def run_guard_rails_async(request: GuardRailsRequest) -> str:
    """Run guard-rails asynchronously and return task ID."""
    task_id = str(uuid4())
    task = Task(id=task_id, status=TaskStatus.PENDING, progress=0.0)
    task_registry[task_id] = task

    # Start background task
    asyncio.create_task(_execute_guard_rails(task_id, request))

    return task_id

async def _execute_guard_rails(task_id: str, request: GuardRailsRequest):
    """Execute guard-rails and update task status."""
    task = task_registry[task_id]
    task.status = TaskStatus.RUNNING

    try:
        # Run quality gates
        result = await run_quality_pipeline(
            no_format=request.no_format,
            progress_callback=lambda p: update_task_progress(task_id, p)
        )

        task.status = TaskStatus.COMPLETED
        task.progress = 1.0
        task.result = result
    except Exception as e:
        task.status = TaskStatus.FAILED
        task.error = str(e)
```

### Streaming Progress

```python
@router.get("/tasks/{task_id}/stream")
async def stream_task_progress(task_id: str):
    """Stream task progress using Server-Sent Events."""
    async def event_generator():
        while True:
            task = task_registry.get(task_id)
            if not task:
                yield f"data: {json.dumps({'error': 'Task not found'})}\n\n"
                break

            yield f"data: {json.dumps({
                'status': task.status.value,
                'progress': task.progress,
                'result': task.result if task.status == TaskStatus.COMPLETED else None
            })}\n\n"

            if task.status in [TaskStatus.COMPLETED, TaskStatus.FAILED]:
                break

            await asyncio.sleep(1)

    return StreamingResponse(event_generator(), media_type="text/event-stream")
```

## Consequences

### Positive

1. **Remote Access**: Enable remote invocation from any system
2. **AI Integration**: Better integration with AI agents and automation
3. **Dashboard Support**: Enable centralized quality dashboards
4. **Language Agnostic**: gRPC supports multiple languages
5. **Real-time Updates**: Streaming progress for long operations
6. **Strong Typing**: gRPC provides compile-time type safety

### Negative

1. **Complexity**: Significant architectural complexity
2. **Security Surface**: New attack surface requiring careful design
3. **Maintenance**: Need to maintain API contracts and versioning
4. **Infrastructure**: Requires running server processes
5. **Dependencies**: Additional framework dependencies (FastAPI, gRPC)
6. **Deployment**: More complex deployment scenarios

### Risks

- **Security**: API keys could be compromised
- **Performance**: Network overhead for local operations
- **Availability**: Server downtime blocks operations
- **Version Skew**: Client/server version mismatches
- **Resource Usage**: Server consumes resources

### Mitigation Strategies

1. **Security**: Strong authentication, HTTPS/TLS, rate limiting
2. **Performance**: Keep CLI as primary interface for local use
3. **Availability**: Graceful fallback to CLI mode
4. **Versioning**: API versioning with deprecation policy
5. **Resource Limits**: Request timeouts, concurrent job limits

## Alternatives Considered

### 1. CLI Wrapper Only

**Description**: Provide language-specific wrappers around CLI.

**Pros:**

- Simpler implementation
- No server needed
- Backward compatible

**Cons:**

- Subprocess overhead
- No progress streaming
- Limited to local execution

**Why not chosen:** Doesn't solve remote execution or progress tracking.

### 2. REST Only

**Description**: Implement REST API without gRPC.

**Pros:**

- Simpler implementation
- Universal HTTP support
- Good web integration

**Cons:**

- Less efficient than gRPC
- No streaming (without SSE)
- Less type safety

**Why not chosen:** gRPC provides better performance and type safety for programmatic clients.

### 3. gRPC Only

**Description**: Implement gRPC without REST.

**Pros:**

- Best performance
- Strong typing
- Built-in streaming

**Cons:**

- Harder HTTP integration
- Less accessible for web clients
- More complex debugging

**Why not chosen:** REST provides better accessibility for web and AI agents.

### 4. Message Queue

**Description**: Use message broker (RabbitMQ, Redis) for async execution.

**Pros:**

- Proven architecture
- Scalable
- Decoupled

**Cons:**

- Heavy infrastructure
- Operational complexity
- Overkill for use case

**Why not chosen:** Too complex for initial requirements.

## Implementation Plan

### Sprint 1: REST API Core (Complete)

- [x] Design OpenAPI specification
- [x] Define module structure
- [x] Create API package and REST subpackage
- [x] Implement FastAPI application
- [x] Add core endpoints (guard-rails, cleanup, analytics)
- [x] Implement authentication (Bearer token)
- [x] Write API tests (12 comprehensive async tests)

**Sprint 1 Status**: Complete. OpenAPI specification defined in `docs/api/openapi.yaml`, module structure created in `src/hephaestus/api/`, FastAPI application implemented with authentication and core endpoints.

### Sprint 2: Async & Progress (Complete)

- [x] Implement async task management
- [x] Add progress streaming (Server-Sent Events)
- [x] Add task status endpoints
- [x] Implement timeouts and limits

**Sprint 2 Status**: Complete. Full async task manager with status tracking, SSE streaming for progress updates, comprehensive error handling. All tests passing.

### Sprint 3: gRPC Service (Complete)

- [x] Define protocol buffers
- [x] Implement gRPC server
- [x] Add streaming RPCs
- [x] Create gRPC client examples

**Sprint 3 Status**: Complete. Full gRPC implementation with all three services (QualityService, CleanupService, AnalyticsService), streaming progress updates via RunGuardRailsStream, protocol buffers compiled to Python, server with reflection support, comprehensive client examples, and 10 tests all passing.

### Sprint 4: Production Ready

- [ ] Add comprehensive security
- [ ] Implement rate limiting
- [ ] Add API versioning
- [ ] Create deployment guides
- [ ] Build API client libraries

## Follow-up Actions

- [ ] Design OpenAPI specification
- [ ] Implement REST API core
- [ ] Add authentication and security
- [ ] Implement async task management
- [ ] Design gRPC protocol buffers
- [ ] Implement gRPC service

## References

- [FastAPI Documentation](https://fastapi.tiangolo.com/)
- [gRPC Python](https://grpc.io/docs/languages/python/)
- [OpenAPI Specification](https://swagger.io/specification/)
- [API Security Best Practices](https://owasp.org/www-project-api-security/)
- [Hephaestus Schema Module](../../src/hephaestus/schema.py)

## Appendix: Example API Usage

### REST API (Python)

```python
import requests

# Start guard-rails asynchronously
response = requests.post(
    "http://localhost:8000/api/v1/quality/guard-rails",
    headers={"Authorization": "Bearer YOUR_API_KEY"},
    json={"no_format": False, "drift_check": True}
)

task_id = response.json()["task_id"]

# Poll for status
while True:
    status = requests.get(
        f"http://localhost:8000/api/v1/tasks/{task_id}",
        headers={"Authorization": "Bearer YOUR_API_KEY"}
    ).json()

    if status["status"] in ["completed", "failed"]:
        break

    print(f"Progress: {status['progress']*100}%")
    time.sleep(2)

print(f"Result: {status['result']}")
```

### gRPC (Python)

```python
import grpc
from hephaestus.v1 import quality_pb2, quality_pb2_grpc

# Create channel
channel = grpc.insecure_channel('localhost:50051')
stub = quality_pb2_grpc.QualityServiceStub(channel)

# Call with streaming progress
request = quality_pb2.GuardRailsRequest(
    no_format=False,
    drift_check=True
)

for progress in stub.RunGuardRailsStream(request):
    print(f"{progress.stage}: {progress.progress}% - {progress.message}")
    if progress.completed:
        break
```

### cURL (REST)

```bash
# Start guard-rails
curl -X POST http://localhost:8000/api/v1/quality/guard-rails \
  -H "Authorization: Bearer YOUR_API_KEY" \
  -H "Content-Type: application/json" \
  -d '{"no_format": false, "drift_check": true}'

# Get task status
curl http://localhost:8000/api/v1/tasks/TASK_ID \
  -H "Authorization: Bearer YOUR_API_KEY"
```

## Status History

- 2025-01-11: Proposed (documented in ADR)
- 2025-01-15: Sprint 1 Foundation Complete - OpenAPI spec and module structure defined
- 2025-01-16: Sprint 2 Complete - FastAPI implementation with async task management, SSE streaming, authentication, and comprehensive tests
- 2025-01-16: Sprint 3 Complete - Full gRPC implementation with protocol buffers, three services, streaming RPCs, client examples, and comprehensive tests
- Future: Sprint 4 - Production hardening and deployment
