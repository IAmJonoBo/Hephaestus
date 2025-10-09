# Architecture Decision Records (ADRs)

This directory contains Architecture Decision Records documenting significant technical decisions made in the Hephaestus project.

## ADR Index

### Accepted & Implemented

- **[ADR-0001: STRIDE Threat Model](./0001-stride-threat-model.md)**
  - Status: Implemented (2025-01-16)
  - Implementation: All three phases complete (Critical Security, Hardening, Advanced Features)
  - Summary: Comprehensive security analysis and threat mitigation strategies for Hephaestus CLI and release pipeline

- **[ADR-0002: Plugin Architecture](./0002-plugin-architecture.md)**
  - Status: Sprint 2-3 Partial (2025-10-09)
  - Implementation: Sprint 1-2 complete (foundation, built-in plugins, discovery); Sprint 3 partial (experimental guard-rails integration)
  - Summary: Extensible plugin system for custom quality gates

- **[ADR-0003: OpenTelemetry Integration](./0003-opentelemetry-integration.md)**
  - Status: Sprint 3 Complete (2025-01-16)
  - Implementation: Sprint 1-3 complete (foundation, tracing utilities, metrics instrumentation, privacy controls, custom analytics metrics)
  - Summary: Integrate OpenTelemetry for distributed tracing, metrics, and observability

- **[ADR-0004: REST/gRPC API](./0004-rest-grpc-api.md)**
  - Status: Sprint 1 Foundation Complete (2025-01-16)
  - Implementation: Module structure and OpenAPI specification defined; full implementation deferred pending prioritization
  - Summary: Dual-protocol API for remote invocation and AI agent integration

- **[ADR-0005: PyPI Publication Automation](./0005-pypi-publication.md)**
  - Status: Sprint 2 Workflow Complete (2025-01-16)
  - Implementation: Workflow automation complete; execution pending PyPI account registration and Trusted Publisher setup
  - Summary: Automated publication to PyPI using GitHub Actions and Trusted Publishers for improved discoverability and standard installation

- **[ADR-0006: Sigstore Bundle Backfill](./0006-sigstore-backfill.md)**
  - Status: Sprint 1 Complete (2025-10-09)
  - Implementation: Metadata schema and backfill script implemented; execution pending
  - Summary: Backfill Sigstore attestations for historical releases to close supply chain security gap

## ADR Lifecycle

```
Proposed → Accepted → Implemented → Superseded/Deprecated
```

### Status Definitions

- **Proposed**: Decision documented, awaiting review and acceptance
- **Accepted**: Decision approved, implementation scheduled
- **Implemented**: Decision fully implemented in codebase
- **Superseded**: Decision replaced by a newer ADR
- **Deprecated**: Decision no longer applicable

## Creating a New ADR

1. Copy `0000-template.md` to `NNNN-title.md` (use next sequential number)
2. Fill in the template sections:
   - Context: Why this decision is needed
   - Decision: What we're deciding to do
   - Consequences: Positive, negative, and risks
   - Alternatives: What else we considered
   - Implementation Plan: Phased rollout timeline
3. Submit as PR for review
4. Update this index when accepted

## ADR Format

All ADRs follow a consistent structure:

- **Metadata**: Status, date, relationships
- **Context**: Problem statement and motivating forces
- **Decision**: The architectural decision being made
- **Consequences**: Positive, negative, risks, and mitigations
- **Alternatives Considered**: Other approaches evaluated
- **Implementation Plan**: Phased rollout with milestones
- **Follow-up Actions**: Specific tasks with owners and dates
- **References**: Related documentation and resources

## Related Documentation

- [Architecture Overview](../explanation/architecture.md) - System architecture and component interactions
- [STRIDE Threat Model Details](./0001-stride-threat-model.md) - Complete security analysis
- [Operating Safely Guide](../how-to/operating-safely.md) - Safety features and best practices
- [Next Steps Tracker](../../Next_Steps.md) - Implementation status and roadmap

## Decision Framework

When prioritizing ADR implementation, consider:

- **Impact**: How many users/workflows benefit?
- **Effort**: Implementation complexity and maintenance burden
- **Dependencies**: What foundational work is required?
- **Community**: Is there external demand or contribution interest?
- **Security**: Does this address threat model findings?
- **Stability**: Is the technical landscape mature enough?

## Implementation Status

### Completed

- ✅ ADR-0001: STRIDE Threat Model (all three phases complete - Critical Security, Hardening, Advanced Features)
- ✅ ADR-0002: Plugin Architecture Sprint 1-3 (foundation, built-in plugins, discovery, guard-rails integration)
- ✅ ADR-0003: OpenTelemetry Integration Sprint 1-3 (foundation, tracing, metrics, instrumentation, custom analytics)
- ✅ ADR-0004: REST/gRPC API Sprint 1 Foundation (OpenAPI spec, module structure)
- ✅ ADR-0006: Sigstore Backfill Sprint 1 (metadata schema and backfill script)

### In Progress

- 🔄 ADR-0005: PyPI Publication Sprint 2 (workflow complete, pending account setup)
- 🔄 ADR-0006: Sigstore Backfill Sprint 2 (execution pending manual trigger)

### Planned

- ⏳ ADR-0003: Sprint 4 (sampling strategies, plugin instrumentation, Prometheus exporter, monitoring guide)
- ⏳ ADR-0004: Sprint 2+ (FastAPI implementation, authentication, async tasks, gRPC service)
- ⏳ ADR-0005: Sprint 3 (PyPI account setup, first publication)
- ⏳ ADR-0006: Sprint 3 (CLI verification flags, documentation updates)
- ⏳ ADR-0002: Sprint 4 (marketplace, dependency resolution, versioning)

## Maintenance

ADRs should be reviewed:

- After each sprint completion
- After major feature additions
- When technical assumptions change
- When community feedback suggests changes

Last reviewed: 2025-01-16 (ADR status consolidation and implementation updates)
