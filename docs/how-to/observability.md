# OpenTelemetry Integration Guide (ADR-0003)

**Status**: Phase 1 (Foundation) - Optional observability support

## Overview

Hephaestus supports optional OpenTelemetry integration for distributed tracing and observability. This is fully opt-in and disabled by default.

## Quick Start

### Installation

Install Hephaestus with telemetry support:

```bash
pip install hephaestus[telemetry]
```

### Basic Configuration

Enable telemetry via environment variables:

```bash
export HEPHAESTUS_TELEMETRY_ENABLED=true
export OTEL_EXPORTER_OTLP_ENDPOINT=http://localhost:4318
export OTEL_SERVICE_NAME=hephaestus
```

### Running with Telemetry

Once configured, run any Hephaestus command normally:

```bash
hephaestus guard-rails
```

Telemetry data will be exported to your configured OTLP endpoint.

## Configuration

### Environment Variables

| Variable | Description | Default |
|----------|-------------|---------|
| `HEPHAESTUS_TELEMETRY_ENABLED` | Enable/disable telemetry | `false` |
| `OTEL_EXPORTER_OTLP_ENDPOINT` | OTLP collector endpoint | None |
| `OTEL_SERVICE_NAME` | Service name for traces | `hephaestus` |
| `HEPHAESTUS_TELEMETRY_PRIVACY` | Privacy mode (strict/balanced/minimal) | `strict` |

### Privacy Modes

- **strict**: Maximum anonymization, minimal data collection
- **balanced**: Anonymize sensitive paths and usernames
- **minimal**: Minimal anonymization, maximum visibility

## Architecture

The telemetry module provides:

1. **No-op fallback**: Works without OpenTelemetry installed
2. **Graceful degradation**: Errors don't break functionality
3. **Environment-driven**: All configuration via environment variables
4. **Privacy-first**: Opt-in with anonymization support

## Phase 1 Limitations

Current Phase 1 implementation provides:
- ✅ Module structure and API
- ✅ No-op tracer fallback
- ✅ Basic configuration
- ❌ Not yet: Actual instrumentation of commands
- ❌ Not yet: Metrics collection
- ❌ Not yet: Advanced privacy controls

## Future Phases

- **Phase 2** (v0.4.0): Instrument all CLI commands, add metrics
- **Phase 3** (v0.5.0): Advanced sampling, custom metrics, plugin support
- **Phase 4** (v0.6.0): Production-ready with analytics dashboard

## Related Documentation

- [ADR-0003: OpenTelemetry Integration](../adr/0003-opentelemetry-integration.md)
- [Architecture Overview](../explanation/architecture.md)
