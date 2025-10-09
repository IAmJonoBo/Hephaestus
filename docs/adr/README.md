# Architecture Decision Records (ADRs)

This directory contains Architecture Decision Records documenting significant technical decisions made in the Hephaestus project.

## ADR Index

### Accepted & Implemented

- **[ADR-0001: STRIDE Threat Model](./0001-stride-threat-model.md)**
  - Status: Accepted (2025-01-11)
  - Implementation: Phases 1-2 complete, Phase 3 partially complete
  - Summary: Comprehensive security analysis and threat mitigation strategies for Hephaestus CLI and release pipeline

- **[ADR-0002: Plugin Architecture](./0002-plugin-architecture.md)**
  - Status: Phase 1 Implemented (2025-01-15)
  - Implementation: Phase 1 (Foundation) complete - API specification and base classes
  - Summary: Extensible plugin system for custom quality gates

- **[ADR-0003: OpenTelemetry Integration](./0003-opentelemetry-integration.md)**
  - Status: Phase 1 Implemented (2025-01-15)
  - Implementation: Phase 1 (Foundation) complete - Optional telemetry module with no-op fallback
  - Summary: Integrate OpenTelemetry for distributed tracing, metrics, and observability

- **[ADR-0004: REST/gRPC API](./0004-rest-grpc-api.md)**
  - Status: Phase 1 Implemented (2025-01-15)
  - Implementation: Phase 1 (Foundation) complete - OpenAPI specification and module structure
  - Summary: Dual-protocol API for remote invocation and AI agent integration

- **[ADR-0006: Sigstore Bundle Backfill](./0006-sigstore-backfill.md)**
  - Status: Phase 1 Implemented (2025-01-15)
  - Implementation: Phase 1 (Preparation) complete - Metadata schema defined
  - Summary: Backfill Sigstore attestations for historical releases to close supply chain security gap

### Proposed - Sprint 2

- **[ADR-0005: PyPI Publication Automation](./0005-pypi-publication.md)**
  - Status: Proposed (2025-01-15)
  - Target: Next release (Sprint 1-2)
  - Summary: Automated publication to PyPI using GitHub Actions and Trusted Publishers for improved discoverability and standard installation

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

## Timeline Overview

```
Sprint 1 (Foundation - Complete)
├── ADR-0002: Plugin Architecture - API specification
├── ADR-0003: OpenTelemetry - Basic setup
├── ADR-0004: REST API - OpenAPI spec
└── ADR-0006: Sigstore Backfill - Metadata schema

Sprint 2 (Core Features)
├── ADR-0005: PyPI Publication - Registration & automation
├── ADR-0006: Sigstore Backfill - Execution
├── ADR-0003: OpenTelemetry - Instrumentation
└── ADR-0002: Plugin Architecture - Discovery & migration

Sprint 3 (Advanced Features)
├── ADR-0003: OpenTelemetry - Advanced features
├── ADR-0002: Plugin Architecture - Ecosystem
├── ADR-0004: REST API - Async & gRPC
└── ADR-0006: Sigstore Backfill - Enforcement

Sprint 4 (Production Ready)
├── ADR-0003: OpenTelemetry - Production optimization
├── ADR-0002: Plugin Architecture - Marketplace
├── ADR-0004: REST API - Security & deployment
└── ADR-0005: PyPI Publication - Optimization
```

## Maintenance

ADRs should be reviewed:

- After each sprint completion
- After major feature additions
- When technical assumptions change
- When community feedback suggests changes

Next scheduled review: Sprint 2 retrospective
