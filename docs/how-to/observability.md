# OpenTelemetry Integration Guide (ADR-0003)

**Status**: Phase 2 (Instrumented) - Optional observability support with sampling and metrics

## Overview

Hephaestus ships with optional OpenTelemetry instrumentation for tracing, metrics, and plugin analytics. The stack is fully opt-in and disabled by default. When enabled, the toolkit now emits:

- Distributed spans for CLI commands, guard-rails, and plugin execution
- Prometheus-compatible metrics exported over HTTP
- Structured counters and histograms that capture plugin health and timings

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
export OTEL_SERVICE_NAME=hephaestus-dev
export OTEL_EXPORTER_OTLP_ENDPOINT=http://localhost:4318

# Optional: adjust sampling and Prometheus endpoint
export OTEL_TRACES_SAMPLER=parentbased_traceidratio
export OTEL_TRACES_SAMPLER_ARG=0.2
export HEPHAESTUS_PROMETHEUS_HOST=0.0.0.0
export HEPHAESTUS_PROMETHEUS_PORT=9464
```

### Running with Telemetry

Once configured, run any Hephaestus command normally:

```bash
hephaestus guard-rails
```

Telemetry data will be exported to your configured OTLP endpoint.

## Configuration

### Environment Variables

| Variable                       | Description                                 | Default                    |
| ------------------------------ | ------------------------------------------- | -------------------------- |
| `HEPHAESTUS_TELEMETRY_ENABLED` | Enable/disable telemetry                    | `false`                    |
| `OTEL_EXPORTER_OTLP_ENDPOINT`  | OTLP collector endpoint                     | None                       |
| `OTEL_SERVICE_NAME`            | Service name for traces                     | `hephaestus`               |
| `OTEL_TRACES_SAMPLER`          | Trace sampler (always_on/parentbased\*)     | `parentbased_traceidratio` |
| `OTEL_TRACES_SAMPLER_ARG`      | Sampler argument (ratio for `traceidratio`) | `0.2`                      |
| `HEPHAESTUS_PROMETHEUS_HOST`   | Prometheus exporter bind host               | `0.0.0.0`                  |
| `HEPHAESTUS_PROMETHEUS_PORT`   | Prometheus exporter bind port               | `9464`                     |
| `HEPHAESTUS_TELEMETRY_PRIVACY` | Privacy mode (strict/balanced/minimal)      | `strict`                   |

### Privacy Modes

- **strict**: Maximum anonymization, minimal data collection
- **balanced**: Anonymize sensitive paths and usernames
- **minimal**: Minimal anonymization, maximum visibility

## Architecture Highlights

- **No-op fallbacks** keep the toolkit safe to run without extra dependencies.
- **Parent-based sampling** is enabled by default with a 20% trace ratio. Adjust the ratio via `OTEL_TRACES_SAMPLER_ARG` (0.0–1.0).
- **Prometheus exporter** is embedded directly in `hephaestus.telemetry.metrics` and automatically binds to `http://0.0.0.0:9464/metrics` when telemetry is enabled.
- **Plugin instrumentation** wraps every quality gate execution with spans and counters so that failures, durations, and retries are visible in dashboards.

## Sampling Strategies

| Sampler Value              | Description                                           |
| -------------------------- | ----------------------------------------------------- |
| `always_on`                | Capture every span regardless of parent context       |
| `always_off`               | Disable tracing but keep metrics active               |
| `traceidratio`             | Sample root spans at a fixed ratio (0.0–1.0)          |
| `parentbased_always_on`    | Follow parent sampling decisions, default to on       |
| `parentbased_traceidratio` | **Default.** Parent-aware sampling with ratio control |

Recommended production posture:

```bash
export OTEL_TRACES_SAMPLER=parentbased_traceidratio
export OTEL_TRACES_SAMPLER_ARG=0.1  # 10% sample rate in production
```

## Prometheus Metrics

When telemetry is enabled, Hephaestus exposes a Prometheus scrape endpoint:

```bash
curl http://localhost:9464/metrics
```

Key metric families:

- `hephaestus_plugins_invocations_total` — Number of plugin executions
- `hephaestus_plugins_success_total` — Successful plugin runs
- `hephaestus_plugins_failures_total` — Plugin runs that returned `success=False`
- `hephaestus_plugins_errors_total` — Plugin crashes or unexpected exceptions
- `hephaestus_plugins_duration_bucket` — Histogram of execution times per plugin
- `hephaestus_guard_rails_plugin_duration_bucket` — Guard-rails step durations (existing metric)

All metrics include an `attributes` label containing a sorted key/value string. Example output:

```text
hephaestus_plugins_success_total{attributes="category=testing,plugin=pytest,version=1.0.0"} 5.0
```

### Scrape Configuration Example

```yaml
# prometheus.yml
scrape_configs:
  - job_name: "hephaestus"
    metrics_path: /metrics
    static_configs:
      - targets: ["hephaestus-host:9464"]
```

### Grafana Dashboard Starters

Create panels using queries such as:

- **Plugin Error Rate**: `rate(hephaestus_plugins_errors_total[5m])`
- **Plugin Duration (95th Percentile)**: `histogram_quantile(0.95, sum(rate(hephaestus_plugins_duration_bucket[5m])) by (le))`
- **Guard-Rails Throughput**: `increase(hephaestus_plugins_invocations_total{plugin="pytest"}[1h])`

## Plugin Telemetry

Each plugin execution now emits both traces and metrics:

- Span name: `plugins.execute`
- Span attributes: `plugin`, `version`, `category`
- Counters: `hephaestus.plugins.invocations`, `success`, `failures`, `errors`
- Histogram: `hephaestus.plugins.duration`

Use these signals to diagnose flaky quality gates, identify slow steps, or alert on recurring crashes.

## Configuration Bundles

Combine tracing and metrics into a single environment profile:

```bash
export HEPHAESTUS_TELEMETRY_ENABLED=true
export OTEL_SERVICE_NAME=hephaestus-ci
export OTEL_EXPORTER_OTLP_ENDPOINT=https://otel-collector.internal:4318
export OTEL_TRACES_SAMPLER=parentbased_traceidratio
export OTEL_TRACES_SAMPLER_ARG=0.05
export HEPHAESTUS_PROMETHEUS_HOST=0.0.0.0
export HEPHAESTUS_PROMETHEUS_PORT=9464
```

## Related Documentation

- [ADR-0003: OpenTelemetry Integration](../adr/0003-opentelemetry-integration.md)
- [Architecture Overview](../explanation/architecture.md)
- [Quality Gates Guide](quality-gates.md)
