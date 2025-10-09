# AI Agent Integration Guide

This guide helps AI agents (GitHub Copilot, Cursor, Claude, etc.) integrate with Hephaestus CLI commands and REST API safely and predictably.

## Integration Options

Hephaestus provides two integration paths:

1. **CLI Integration**: Direct command-line execution (existing)
2. **REST API Integration**: Remote HTTP/HTTPS invocation (new in v0.3.0)

## Getting Command Schemas

Export all command schemas as JSON for programmatic consumption:

```bash
hephaestus schema --output schemas.json
```

This generates a JSON file with:

- Command names and descriptions
- Parameter specifications (types, defaults, help text)
- Usage examples
- Expected output formats
- Retry hints for common failures

## Schema Format

```json
{
  "version": "1.0",
  "commands": [
    {
      "name": "cleanup",
      "help": "Scrub development cruft...",
      "parameters": [
        {
          "name": "root",
          "type": "path",
          "required": false,
          "help": "Workspace root to clean"
        }
      ],
      "examples": ["hephaestus cleanup", "hephaestus cleanup --deep-clean"],
      "expected_output": "Table showing cleaned paths and sizes",
      "retry_hints": [
        "If cleanup fails with permission errors, check file permissions"
      ]
    }
  ]
}
```

## Common Integration Patterns

### 1. Command Discovery

Use the schema to discover available commands and their capabilities:

```python
import json

with open("schemas.json") as f:
    schemas = json.load(f)

for cmd in schemas["commands"]:
    print(f"{cmd['name']}: {cmd['help']}")
```

### 2. Parameter Validation

Validate parameters before invoking commands:

```python
def validate_params(command_name, user_params):
    cmd = next(c for c in schemas["commands"] if c["name"] == command_name)

    for param in cmd["parameters"]:
        if param["required"] and param["name"] not in user_params:
            raise ValueError(f"Missing required parameter: {param['name']}")
```

### 3. Error Recovery

Use retry hints to guide error recovery:

```python
def execute_with_retry(command, max_attempts=3):
    for attempt in range(max_attempts):
        result = subprocess.run(command, capture_output=True)
        if result.returncode == 0:
            return result

        # Check retry hints from schema
        cmd_schema = get_schema(command[0])
        print(f"Retry hint: {cmd_schema['retry_hints'][0]}")
```

## Command-Specific Guidance

### Cleanup

**When to use**: Before running quality checks, during CI cleanup stages, or when disk space is low.

**Safe patterns**:

```bash
# Always run with default safety checks
hephaestus cleanup

# Add dry-run for verification
hephaestus cleanup --dry-run

# Deep clean for CI environments
hephaestus cleanup --deep-clean
```

**Avoid**:

- Running cleanup on system directories (/, /home, /usr)
- Using `--extra-path` without verification
- Running outside git repositories without `--allow-outside-root`

### Guard-Rails

**When to use**: Before committing, as part of CI/CD, or after making code changes.

**Recommended workflow**:

```bash
# Full check with auto-format
hephaestus guard-rails

# Check only (no format) during review
hephaestus guard-rails --no-format
```

**Expected failures**:

- Lint errors: Fix reported issues in code
- Type errors: Address mypy complaints
- Test failures: Fix failing tests
- Security issues: Review and address vulnerabilities

### Analytics Rankings

**When to use**: Planning refactoring work, prioritizing technical debt, understanding codebase health.

**Strategies**:

```bash
# Risk-weighted (recommended for general use)
hephaestus tools refactor rankings

# Coverage-first (when improving test coverage)
hephaestus tools refactor rankings --strategy coverage_first

# Churn-based (for identifying hotspots)
hephaestus tools refactor rankings --strategy churn_based

# Composite (balanced with embeddings)
hephaestus tools refactor rankings --strategy composite
```

**Prerequisites**:

- Analytics sources configured in settings
- churn_file, coverage_file, or embeddings_file paths set
- Data files exist and are readable

### Release Install

**When to use**: Installing pre-built wheelhouse distributions, setting up environments.

**Safe patterns**:

```bash
# Standard install (with signature verification)
hephaestus release install

# Specific version
hephaestus release install --tag v1.0.0

# With authentication for private repos
GITHUB_TOKEN=xxx hephaestus release install --repository owner/private-repo
```

**Network considerations**:

- Set `--timeout` higher for slow networks
- Use `--max-retries` for flaky connections
- Cache downloads with `--destination` to avoid re-downloading

## Deterministic Outputs

All commands produce structured, predictable outputs:

### Table Outputs

Commands like `rankings`, `hotspots`, and `guard-rails` emit Rich tables with consistent columns:

```
┏━━━━━┳━━━━━━━━━━━━━━━━━┳━━━━━━━━┓
┃ Rank┃ Path            ┃ Score  ┃
┡━━━━━╇━━━━━━━━━━━━━━━━━╇━━━━━━━━┩
│  1  │ module_a.py     │ 0.8234 │
│  2  │ module_b.py     │ 0.7156 │
└─────┴─────────────────┴────────┘
```

Parse these by:

1. Capturing stdout
2. Extracting table rows
3. Parsing columns by position or header

### JSON Logs

Enable structured logging for machine parsing:

```bash
hephaestus --log-format json guard-rails
```

Produces:

```json
{
  "timestamp": "2025-01-01T12:00:00Z",
  "level": "INFO",
  "message": "Starting cleanup",
  "run_id": "abc123"
}
```

### Exit Codes

- `0`: Success
- `1`: Command-specific failure (see stderr for details)
- `2`: Invalid arguments

## Best Practices for AI Agents

### 1. Always Use Schemas

Regenerate schemas when Hephaestus is updated:

```bash
hephaestus schema --output /path/to/agent/schemas.json
```

### 2. Validate Before Execution

Check parameters against schema before invoking commands to avoid unnecessary failures.

### 3. Handle Errors Gracefully

Use retry hints from schemas to guide recovery:

- Network timeouts → increase `--timeout`
- Permission errors → check file ownership
- Missing data → verify configuration paths

### 4. Use Structured Logging

Request JSON logs for easier parsing:

```bash
hephaestus --log-format json <command>
```

### 5. Respect Safety Guardrails

Never bypass safety features like:

- Dangerous path validation in cleanup
- Checksum verification in release install
- Required parameters in commands

### 6. Context-Aware Invocation

Choose commands based on context:

- **During development**: `guard-rails`, `cleanup`
- **Planning refactors**: `rankings`, `opportunities`, `hotspots`
- **CI/CD**: `guard-rails`, `release install`
- **Post-mortem analysis**: `rankings --strategy composite`

## Testing AI Agent Integration

Validate your integration with these test cases:

```bash
# 1. Schema export works
hephaestus schema --output test-schemas.json
test -f test-schemas.json

# 2. Commands execute successfully
hephaestus version
hephaestus plan

# 3. Error handling works
hephaestus cleanup / 2>&1 | grep "dangerous path"

# 4. JSON logs parse correctly
hephaestus --log-format json version | jq .message
```

## Support

For issues with AI integration:

1. Check command schemas for updated parameters
2. Review retry hints in schema output
3. Enable debug logging: `hephaestus --log-level DEBUG <command>`
4. Report integration issues with schema version and agent details

## REST API Integration (v0.3.0+)

Hephaestus provides a REST API for remote invocation, ideal for web-based AI agents and distributed systems.

### Starting the API Server

```bash
# Install API dependencies
pip install 'hephaestus-toolkit[api]'

# Start the server
uvicorn hephaestus.api.rest.app:app --host 0.0.0.0 --port 8000

# With auto-reload for development
uvicorn hephaestus.api.rest.app:app --reload
```

### API Endpoints

All API endpoints require authentication via Bearer token:

```bash
# Set your API key
export HEPHAESTUS_API_KEY="your-api-key"

# Make authenticated request
curl -X POST http://localhost:8000/api/v1/quality/guard-rails \
  -H "Authorization: Bearer your-api-key" \
  -H "Content-Type: application/json" \
  -d '{"no_format": false, "drift_check": true}'
```

### Example: Guard-Rails Execution

```python
import httpx

api_url = "http://localhost:8000"
headers = {"Authorization": "Bearer your-api-key"}

async with httpx.AsyncClient() as client:
    # Execute guard-rails
    response = await client.post(
        f"{api_url}/api/v1/quality/guard-rails",
        headers=headers,
        json={"no_format": False, "drift_check": True}
    )
    
    result = response.json()
    print(f"Success: {result['success']}")
    print(f"Duration: {result['duration']}s")
    
    for gate in result['gates']:
        status = "✓" if gate['passed'] else "✗"
        print(f"{status} {gate['name']}")
```

### Example: Cleanup with Dry-Run

```python
import httpx

async with httpx.AsyncClient() as client:
    response = await client.post(
        "http://localhost:8000/api/v1/cleanup",
        headers={"Authorization": "Bearer your-api-key"},
        json={"deep_clean": True, "dry_run": True}
    )
    
    result = response.json()
    print(f"Would delete {result['files_deleted']} files")
    print(f"Would free {result['size_freed']} bytes")
```

### Example: Analytics Rankings

```python
import httpx

async with httpx.AsyncClient() as client:
    response = await client.get(
        "http://localhost:8000/api/v1/analytics/rankings",
        headers={"Authorization": "Bearer your-api-key"},
        params={"strategy": "coverage_first", "limit": 10}
    )
    
    result = response.json()
    for item in result['rankings']:
        print(f"#{item['rank']} {item['path']} - Score: {item['score']}")
```

### Streaming Progress Updates

For long-running operations, use Server-Sent Events to stream progress:

```python
import httpx

async with httpx.AsyncClient() as client:
    # Start operation
    response = await client.post(
        "http://localhost:8000/api/v1/quality/guard-rails",
        headers={"Authorization": "Bearer your-api-key"},
        json={"no_format": False}
    )
    task_id = response.json()['task_id']
    
    # Stream progress updates
    async with client.stream(
        "GET",
        f"http://localhost:8000/api/v1/tasks/{task_id}/stream",
        headers={"Authorization": "Bearer your-api-key"}
    ) as stream:
        async for line in stream.aiter_lines():
            if line.startswith("data: "):
                data = json.loads(line[6:])
                print(f"Progress: {data['progress'] * 100}%")
                if data['status'] in ['completed', 'failed']:
                    break
```

### Error Handling

All API endpoints return structured error responses:

```python
try:
    response = await client.post(url, headers=headers, json=data)
    response.raise_for_status()
except httpx.HTTPStatusError as e:
    if e.response.status_code == 401:
        print("Authentication failed - check API key")
    elif e.response.status_code == 500:
        error = e.response.json()
        print(f"Server error: {error['detail']}")
```

### API Documentation

Full OpenAPI specification available at:

- Interactive docs: `http://localhost:8000/docs`
- OpenAPI JSON: `http://localhost:8000/openapi.json`
- OpenAPI YAML: `docs/api/openapi.yaml`

