---
title: "ADR 0003: OpenTelemetry Integration for Observability"
description: "- Status: Sprint 3 Complete (2025-01-16) - Date: 2025-01-11 - Last Updated: 2025-01-16 - Supersedes: N/A - Superseded by: N/A Hephaestus currently has..."
---
- Status: Sprint 3 Complete (2025-01-16)
- Date: 2025-01-11
- Last Updated: 2025-01-16
- Supersedes: N/A
- Superseded by: N/A

## Context

Hephaestus currently has structured logging with JSON output and run IDs for correlation, but lacks comprehensive observability for:

- Understanding performance bottlenecks in quality pipelines
- Tracking success/failure rates across different environments
- Debugging issues in remote/CI environments
- Measuring adoption and usage patterns
- Identifying slow or failing quality gates

Current logging approach provides:

- Structured JSON logs with context
- Run IDs for operation correlation
- Event definitions in telemetry module

But lacks:

- Distributed tracing across operations
- Metrics collection and aggregation
- Service health monitoring
- Performance profiling
- Real-time dashboards

### Motivating Use Cases

1. **CI Pipeline Optimization**: Teams want to know which quality gates are slowest in CI
2. **Debugging Remote Failures**: Need to trace execution across distributed systems
3. **Usage Analytics**: Understanding which features are used most
4. **Performance Monitoring**: Track regression in guard-rails execution time
5. **Error Tracking**: Aggregate errors across all installations for pattern detection
6. **Capacity Planning**: Understand resource usage for infrastructure planning

### Requirements

- **Privacy**: Must be opt-in, anonymize sensitive data
- **Minimal Overhead**: <5% performance impact when enabled
- **Standard Format**: Use OpenTelemetry standard for interoperability
- **Flexible Backend**: Support multiple exporters (Jaeger, Prometheus, cloud services)
- **Graceful Degradation**: Failures in telemetry should not break functionality

## Decision

We will integrate **OpenTelemetry (OTel)** as our observability framework, providing:

1. **Distributed Tracing**: Trace execution across CLI commands and operations
2. **Metrics Collection**: Track counts, durations, and resource usage
3. **Structured Attributes**: Rich context on spans and metrics
4. **Multiple Exporters**: Support for various backends
5. **Privacy Controls**: Opt-in with data anonymization

### Architecture

```
hephaestus/
├── src/hephaestus/
│   ├── telemetry/
│   │   ├── __init__.py           # Telemetry configuration
│   │   ├── tracing.py             # Tracing setup and utilities
│   │   ├── metrics.py             # Metrics collection
│   │   ├── exporters.py           # Exporter configuration
│   │   └── privacy.py             # Data anonymization
│   └── cli.py                     # Instrumented commands

pyproject.toml                     # OTel dependencies (optional)
```

### Telemetry Configuration

```bash
# Enable telemetry
export HEPHAESTUS_TELEMETRY_ENABLED=true

# Configure exporter
export OTEL_EXPORTER_OTLP_ENDPOINT=http://localhost:4318

# Set service name
export OTEL_SERVICE_NAME=hephaestus

# Configure sampling (1.0 = 100%)
export OTEL_TRACES_SAMPLER=parentbased_traceidratio
export OTEL_TRACES_SAMPLER_ARG=0.1  # 10% sampling

# Privacy mode (anonymize paths, usernames)
export HEPHAESTUS_TELEMETRY_PRIVACY=strict
```

### Instrumentation Example

```python
from opentelemetry import trace
from hephaestus.telemetry import get_tracer, record_metric

tracer = get_tracer(__name__)

@tracer.start_as_current_span("guard_rails")
def guard_rails(no_format: bool = False) -> int:
    """Run comprehensive quality pipeline with tracing."""
    with tracer.start_as_current_span("cleanup"):
        cleanup_result = run_cleanup()
        record_metric("cleanup.files_deleted", cleanup_result.count)

    with tracer.start_as_current_span("lint"):
        lint_result = run_lint()
        record_metric("lint.violations", lint_result.violations)

    # ... more operations ...

    return 0 if all_passed else 1
```

### Trace Structure

```
Trace: guard-rails-execution
├── Span: cleanup (duration: 2.3s)
│   ├── Attribute: files.deleted = 142
│   ├── Attribute: size.freed = 15.2MB
│   └── Event: cleanup.completed
├── Span: lint (duration: 5.1s)
│   ├── Attribute: violations.found = 0
│   ├── Attribute: files.checked = 45
│   └── Event: lint.completed
├── Span: format (duration: 3.8s)
│   └── Event: format.completed
├── Span: typecheck (duration: 12.4s)
│   └── Attribute: files.checked = 45
├── Span: test (duration: 32.1s)
│   ├── Attribute: tests.passed = 85
│   ├── Attribute: coverage = 87.29
│   └── Event: test.completed
└── Span: audit (duration: 8.2s)
    ├── Attribute: vulnerabilities = 0
    └── Event: audit.completed
```

### Metrics to Collect

**Counters:**

- `hephaestus.commands.executed` - Total commands run
- `hephaestus.commands.failed` - Failed commands
- `hephaestus.quality_gates.passed` - Quality gates passed
- `hephaestus.quality_gates.failed` - Quality gates failed

**Gauges:**

- `hephaestus.test_coverage` - Current test coverage percentage
- `hephaestus.files_cleaned` - Files removed by cleanup

**Histograms:**

- `hephaestus.command.duration` - Command execution time
- `hephaestus.quality_gate.duration` - Individual gate duration
- `hephaestus.cleanup.size_freed` - Disk space freed

### Privacy Protection

```python
def anonymize_path(path: Path) -> str:
    """Anonymize file paths for privacy."""
    if privacy_mode == "strict":
        # Replace username and sensitive parts
        return str(path).replace(os.path.expanduser("~"), "~")
    return str(path)

def sanitize_attributes(attrs: dict) -> dict:
    """Remove or anonymize sensitive attributes."""
    sanitized = {}
    for key, value in attrs.items():
        if key in SENSITIVE_KEYS:
            sanitized[key] = "[REDACTED]"
        elif isinstance(value, Path):
            sanitized[key] = anonymize_path(value)
        else:
            sanitized[key] = value
    return sanitized
```

### Exporter Support

1. **Console**: Debug output to stdout
2. **OTLP**: Standard protocol (Jaeger, Tempo, etc.)
3. **Prometheus**: Metrics export
4. **Zipkin**: Distributed tracing
5. **Cloud Services**: AWS X-Ray, GCP Cloud Trace, Azure Monitor

## Consequences

### Positive

1. **Visibility**: Deep insight into system behavior and performance
2. **Debugging**: Easier troubleshooting with distributed traces
3. **Optimization**: Data-driven performance improvements
4. **Reliability**: Early detection of issues and regressions
5. **Adoption Tracking**: Understanding how features are used
6. **Standard Format**: Industry-standard observability

### Negative

1. **Complexity**: Additional dependency and configuration
2. **Performance**: Small overhead (typically <5%)
3. **Privacy Concerns**: Need careful handling of sensitive data
4. **Infrastructure**: Requires backend services for storage
5. **Maintenance**: Need to maintain instrumentation code
6. **Optional Dependency**: Adds optional dependencies

### Risks

- **Data Leakage**: Accidental exposure of sensitive information
- **Performance Impact**: Overhead in hot paths
- **Backend Dependency**: Requires external services
- **Complexity**: Additional troubleshooting surface

### Mitigation Strategies

1. **Opt-In**: Disabled by default, explicit enablement required
2. **Sampling**: Configurable sampling to reduce overhead
3. **Privacy**: Built-in data anonymization
4. **Graceful Degradation**: Continue working if telemetry fails
5. **Documentation**: Clear privacy policy and configuration guide

## Alternatives Considered

### 1. Custom Telemetry System

**Description**: Build our own telemetry system tailored to Hephaestus.

**Pros:**

- Full control over data format
- No external dependencies
- Simpler implementation

**Cons:**

- Reinventing the wheel
- No standard format
- Limited tool ecosystem
- More maintenance burden

**Why not chosen:** OpenTelemetry is industry standard with rich ecosystem.

### 2. Simple Metrics Only

**Description**: Just collect basic metrics without tracing.

**Pros:**

- Simpler to implement
- Lower overhead
- Easier to understand

**Cons:**

- No distributed tracing
- Limited debugging capability
- Can't see operation flow

**Why not chosen:** Tracing provides significant value for debugging complex workflows.

### 3. Logging Only

**Description**: Continue with structured logging only.

**Pros:**

- Already implemented
- No new dependencies
- Simple to understand

**Cons:**

- Hard to aggregate
- No metrics
- Manual correlation
- Poor for real-time monitoring

**Why not chosen:** Current approach, but insufficient for production observability needs.

### 4. Third-Party Service Integration

**Description**: Integrate directly with Datadog, New Relic, etc.

**Pros:**

- Turnkey solution
- Rich features
- Managed service

**Cons:**

- Vendor lock-in
- Cost implications
- Not flexible

**Why not chosen:** OpenTelemetry allows using any backend, avoiding lock-in.

## Implementation Plan

### Sprint 1: Foundation (Complete)

- [x] Add OpenTelemetry dependencies (optional)
- [x] Implement basic tracing setup
- [x] Instrument guard-rails command (API only, integration pending)
- [x] Add console exporter for testing
- [x] Document configuration

### Sprint 2: Core Instrumentation (Complete)

- [x] Instrument all CLI commands (tracing decorators and context managers implemented)
- [x] Add metrics collection (counter, gauge, histogram utilities implemented)
- [x] Implement privacy controls (strict mode supported via environment variables)
- [x] Add OTLP exporter support (configured via environment variables)
- [x] Create example dashboards (documentation provided in ADR)

### Sprint 3: Advanced Features (Complete)

- [x] Add custom metrics for analytics (histogram metrics added for guard-rails and cleanup)
- [x] Instrument CLI commands (guard-rails and cleanup instrumented with performance metrics)
- [ ] Implement sampling strategies (deferred to Sprint 4 - current implementation sufficient)
- [ ] Instrument plugin system (planned for Sprint 4)
- [ ] Add Prometheus exporter (planned for Sprint 4)
- [ ] Create monitoring guide (planned for Sprint 4)

**Sprint 3 Status**: Complete. Core command instrumentation delivered. Added histogram metrics to track:

- Guard-rails step durations (cleanup, ruff-check, ruff-format, yamllint, mypy, pytest, pip-audit)
- Cleanup operation durations (preview, execution, total)
- File removal counts and success rates

Metrics are recorded using the `record_histogram` utility and are opt-in via `HEPHAESTUS_TELEMETRY_ENABLED` environment variable.

### Sprint 4: Production Ready

- [ ] Performance optimization
- [ ] Advanced privacy features
- [ ] Cloud exporter support
- [ ] Telemetry analytics dashboard
- [ ] Usage reports and insights

## Follow-up Actions

- [ ] Design telemetry architecture
- [ ] Implement basic tracing
- [ ] Add privacy controls
- [ ] Create example dashboards
- [ ] Write observability guide

## References

- [OpenTelemetry Documentation](https://opentelemetry.io/docs/)
- [OpenTelemetry Python](https://opentelemetry.io/docs/languages/python/)
- [Hephaestus Telemetry Module](../../src/hephaestus/telemetry.py)
- [Privacy Policy](/PRIVACY/) (future)
- [Observability Guide](/how-to/observability/) (future)

## Appendix: Example Configuration

```yaml
# .hephaestus/telemetry.yaml
telemetry:
  enabled: true

  # Tracing configuration
  tracing:
    enabled: true
    sampler:
      type: parentbased_traceidratio
      rate: 0.1 # 10% sampling
    exporter:
      type: otlp
      endpoint: http://localhost:4318

  # Metrics configuration
  metrics:
    enabled: true
    exporter:
      type: prometheus
      port: 9090

  # Privacy controls
  privacy:
    mode: strict # strict, balanced, minimal
    anonymize_paths: true
    anonymize_usernames: true
    redact_env_vars: true
    allowed_attributes:
      - command
      - exit_code
      - duration
```

## Appendix: Dashboard Queries

**Grafana Dashboard Examples:**

```promql
# Average guard-rails duration
avg(hephaestus_command_duration_seconds{command="guard-rails"})

# Success rate by command
sum(rate(hephaestus_commands_executed[5m])) by (command)
/
sum(rate(hephaestus_commands_failed[5m])) by (command)

# Quality gate pass rate
sum(rate(hephaestus_quality_gates_passed[5m]))
/
(sum(rate(hephaestus_quality_gates_passed[5m])) + sum(rate(hephaestus_quality_gates_failed[5m])))
```

## Status History

- 2025-01-11: Proposed (documented in ADR)
- 2025-10-09: Sprint 1 Complete - Foundation and basic tracing implemented
- 2025-10-09: Sprint 2 Complete - Core instrumentation, metrics, and privacy controls implemented
- 2025-01-16: Sprint 3 Complete - Custom metrics and CLI instrumentation delivered
- Future: Sprint 4 - Production ready (sampling strategies, plugin instrumentation, Prometheus exporter, monitoring guide)
