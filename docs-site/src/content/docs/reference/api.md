---
title: "REST API Reference (ADR-0004)"
description: "Status: Phase 1 (Foundation) - OpenAPI specification only Hephaestus provides a REST API for remote invocation of quality gates, cleanup operations, and..."
---

**Status**: Phase 1 (Foundation) - OpenAPI specification only

## Overview

Hephaestus provides a REST API for remote invocation of quality gates, cleanup operations, and analytics. This enables integration with CI/CD systems, dashboards, and AI agents.

## Base URL

```text
http://localhost:8000/api/v1
```

## Authentication

All endpoints require API key authentication:

```bash
curl -H "Authorization: Bearer YOUR_API_KEY" \
  http://localhost:8000/api/v1/quality/guard-rails
```

## Endpoints

### Quality Gates

#### POST /quality/guard-rails

Run comprehensive quality pipeline.

**Request Body:**

```json
{
  "no_format": false,
  "workspace": "/path/to/project",
  "drift_check": true
}
```

**Response:**

```json
{
  "success": true,
  "gates": [
    {
      "name": "lint",
      "passed": true,
      "message": "Linting passed",
      "duration": 5.2,
      "metadata": {}
    }
  ],
  "duration": 45.3,
  "task_id": "task-abc123"
}
```

### Cleanup

#### POST /cleanup

Clean workspace artifacts.

**Request Body:**

```json
{
  "root": "/path/to/project",
  "deep_clean": false,
  "dry_run": false
}
```

**Response:**

```json
{
  "files_deleted": 142,
  "size_freed": 15728640,
  "manifest": {}
}
```

### Analytics

#### GET /analytics/rankings

Get refactoring rankings.

**Query Parameters:**

- `strategy`: Ranking strategy (risk_weighted, coverage_first, churn_based, composite)
- `limit`: Max results (1-100, default: 20)

**Response:**

```json
{
  "rankings": [
    {
      "path": "src/module.py",
      "score": 0.85,
      "metrics": {
        "churn": 15,
        "coverage": 0.45,
        "complexity": 25
      }
    }
  ],
  "strategy": "composite"
}
```

### Tasks

#### GET /tasks/{task_id}

Get async task status.

**Response:**

```json
{
  "task_id": "task-abc123",
  "status": "running",
  "progress": 0.65,
  "result": null,
  "error": null
}
```

## OpenAPI Specification

Full OpenAPI 3.0 specification available at:

**[docs/api/openapi.yaml](../../api/openapi.yaml)**

## Phase 1 Implementation Status

The current Phase 1 release includes:

- ✅ OpenAPI specification (available)
- ✅ API module structure (available)
- 🚧 FastAPI implementation (in progress, not yet available)
- 🚧 Authentication (planned for future phase)
- 🚧 Async task management (planned for future phase)
- 🚧 gRPC support (planned for future phase)

## Future Phases

- **Phase 1** (v0.4.0): REST API core endpoints, authentication
- **Phase 2** (v0.5.0): Async task management, progress streaming
- **Phase 3** (v0.6.0): gRPC service, streaming RPCs
- **Phase 4** (v0.7.0): Production-ready with rate limiting, versioning

## Client Examples

### Python

```python
import requests

response = requests.post(
    "http://localhost:8000/api/v1/quality/guard-rails",
    headers={"Authorization": "Bearer YOUR_API_KEY"},
    json={"no_format": False, "drift_check": True}
)

result = response.json()
print(f"Success: {result['success']}")
```

### cURL

```bash
curl -X POST http://localhost:8000/api/v1/quality/guard-rails \
  -H "Authorization: Bearer YOUR_API_KEY" \
  -H "Content-Type: application/json" \
  -d '{"no_format": false, "drift_check": true}'
```

## Related Documentation

- [ADR-0004: REST/gRPC API](/adr/0004-rest-grpc-api/)
- [AI Agent Integration](/reference/ai-agent-integration/)
- [Architecture Overview](/explanation/architecture/)
