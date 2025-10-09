# Changelog

All notable changes to Hephaestus will be documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.0.0/),
and this project adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

## [Unreleased]

### Added

- **Authentication & Authorization Hardening (ADR-0001 Phase 3+)**:
  - Token validation before GitHub API calls with pattern matching
  - Support for classic (`ghp_*`), fine-grained (`ghs_*`), and PAT (`github_pat_*`) token formats
  - Token expiration detection with clear error messages for HTTP 401 responses
  - `RELEASE_TOKEN_VALIDATION` telemetry event for monitoring token issues
  - Comprehensive test coverage for token validation scenarios (7 new tests)
- **Phase 1 ADR Implementations**: Foundation for major architectural features
  - **ADR-0002 (Plugin Architecture)**: Plugin API specification and base classes
    - `QualityGatePlugin` abstract base class for custom quality gates
    - `PluginRegistry` for managing plugin instances
    - `PluginMetadata` and `PluginResult` data models
  - **ADR-0003 (OpenTelemetry)**: Optional distributed tracing support
    - Environment-based configuration (`HEPHAESTUS_TELEMETRY_ENABLED`)
    - No-op tracer fallback when OpenTelemetry not installed
    - Graceful degradation on configuration errors
  - **ADR-0004 (REST/gRPC API)**: API module structure and OpenAPI specification
    - OpenAPI 3.0 spec in `docs/api/openapi.yaml`
    - Module structure for future FastAPI implementation
    - Endpoints for quality gates, cleanup, analytics, and tasks
  - **ADR-0006 (Sigstore Backfill)**: Metadata schema for historical releases
    - `BackfillMetadata` dataclass with JSON serialization
    - Verification status constants for distinguishing backfilled bundles
- **Documentation Updates**:
  - Observability guide for OpenTelemetry usage
  - Plugin development guide with examples
  - REST API reference documentation
  - Architecture overview updated with new modules
- **Optional Dependencies**: `telemetry` and `api` extras in `pyproject.toml`

### Changed

- **Module Reorganization**: Renamed `telemetry.py` to `events.py` for clarity
  - Existing telemetry event definitions moved to `events.py`
  - New `telemetry/` package for OpenTelemetry integration
  - All imports updated (`from hephaestus import events as telemetry`)

### Planned

- REST/gRPC API Phase 2: FastAPI implementation (Q2 2025)
- Plugin architecture Phase 2: Plugin discovery and built-in plugins (Q2 2025)
- OpenTelemetry Phase 2: Actual command instrumentation (Q2 2025)
- Advanced remediation automation (Q2 2025)
- Streaming ingestion for analytics (Q1 2025)
- Drift detection in CI pipeline (Q1 2025)

## [0.2.0] - 2025-01-11

### Added - AI & Intelligence Features

- **Analytics Ranking API**: Four ranking strategies for prioritizing refactoring work
  - `risk_weighted`: Balances coverage gaps, uncovered lines, and churn (default)
  - `coverage_first`: Prioritizes modules with largest coverage gaps
  - `churn_based`: Focuses on high-change-frequency modules
  - `composite`: Balanced approach with bonus for modules with embeddings
- **AI-Native Command Schemas**: `hephaestus schema` command exports structured schemas
  - Complete command metadata (parameters, types, defaults, help text)
  - Usage examples and expected outputs for each command
  - Retry hints for common failures
  - Enables AI agents (Copilot, Cursor, Claude) to invoke Hephaestus safely
- **Guard-Rails Drift Detection**: `hephaestus guard-rails --drift` command
  - Detects tool version drift between pyproject.toml and installed environment
  - Automatic remediation suggestions (uv sync, pip install commands)
  - Clear status reporting (OK, Drift, Missing)
- **Pluggable Analytics Adapters**: Support for churn, coverage, and embedding data sources
  - Data-backed hotspot and refactor planning defaults
  - Configurable via pyproject.toml or config files
- **Telemetry Events**: Standardized event definitions for drift detection
  - Operation and run identifier correlation across CLI flows

### Added - Security & Safety

- **SECURITY.md**: Published security policy with disclosure process
  - Contact channels and expected SLAs
  - Security best practices for users
  - Threat categories and scope
- **STRIDE Threat Model**: Comprehensive security analysis (ADR-0001)
  - Attack surface analysis for CLI, network, filesystem, subprocess
  - Security requirements and mitigation roadmap
- **Cleanup Safety Rails**: Dangerous path protection
  - Blocklist prevents wiping /, /home, /usr, /etc, /var, /bin, /sbin, /lib, /opt, /boot, /root, /sys, /proc, /dev
  - Home directory protection
  - Virtual environment site-packages preservation
  - Clear error messages for dangerous operations
- **Cleanup UX Enhancements**:
  - Mandatory dry-run previews before deletion
  - Typed confirmation for out-of-root targets
  - JSON audit manifests for cleanup operations
- **Release Verification**:
  - SHA-256 checksum verification for wheelhouse downloads
  - Sigstore attestation support with identity pinning
  - Fail-closed controls for unsigned artifacts
- **Asset Name Sanitization**: Path traversal prevention in release downloads
  - Strips path separators and validates filenames
  - Logs when sanitization occurs

### Added - Quality & Tooling

- **Guard-Rails Command**: Comprehensive quality pipeline at module scope
  - Single command runs: cleanup → lint → format → typecheck → test → audit
  - `--no-format` flag for skipping auto-format step
  - Proper command registration (not nested in other functions)
- **Nested Decorator Linting**: AST-based linter prevents command registration bugs
  - Script: `scripts/lint_nested_decorators.py`
  - Integrated into CI and pre-commit hooks
  - Zero-tolerance enforcement
- **Quality Gate Validation**: Single-command validation of all standards
  - Script: `scripts/validate_quality_gates.py`
  - Categorized reporting (testing, linting, typing, security, build)
  - Distinguishes required vs optional gates
- **Test Order Independence**: Added pytest-randomly to catch hidden dependencies
- **Structured Logging**: Run ID-aware JSON/text emitters
  - CLI switches for log format selection
  - Coverage for release and cleanup operations
  - Context binding with log_context

### Added - Documentation

- **Operating Safely Guide**: Comprehensive operational runbooks
  - Cleanup safety features and best practices
  - Guard-rails workflow documentation
  - Release verification procedures
  - Incident response and rollback guidance
- **AI Agent Integration Guide**: Complete integration patterns
  - Schema format and usage examples
  - Language-agnostic patterns (Python, JavaScript, shell)
  - Best practices for AI agents
- **Quality Gates Guide**: Complete validation documentation
  - Individual quality gate usage
  - CI/CD integration patterns
  - Troubleshooting guides
- **Frontier Red Team & Gap Analysis**: Security assessment document
- **Pre-release Checklist**: Enhanced with rollback procedures
  - Step-by-step rollback guidance
  - Release revocation procedures
  - Security advisory templates
  - Post-incident review process

### Changed

- **Dependency Updates**: Refreshed to latest stable versions
  - ruff: 0.6.8 → 0.8.6
  - black: 24.8.0 → 25.1.0
  - mypy: 1.11.2 → 1.14.1
  - pip-audit: 2.7.3 → 2.9.2
  - pyupgrade: 3.19.0 → 3.19.3
- **Release Networking**: Enhanced timeout/backoff with exponential backoff
- **Error Reporting**: Improved guard-rails error messages with clear failure context

### Fixed

- **Guard-Rails Availability**: Command now properly registered at module scope
  - Prevents silent unavailability in fresh shells
  - Regression test ensures command registration pre-execution
- **Cleanup Safety**: Virtual environment protection during build artifact cleanup
  - Preserves .venv/site-packages unless explicitly cleaning virtual environment

### Security

- **Dangerous Path Validation**: Cleanup refuses to operate on system paths
- **Checksum Enforcement**: Wheelhouse downloads require SHA-256 manifests
- **Sigstore Support**: Attestation verification with optional identity policies
- **Parameter Validation**: Timeout and max_retries validation in release functions
- **Extra Paths Validation**: Dangerous path checks for --extra-path arguments

### Developer Experience

- **CLI Reference**: Complete documentation of all commands and options
- **Scripts Documentation**: README for quality automation tools
- **MkDocs Navigation**: All guides properly organized in documentation site
- **Pre-commit Integration**: All quality gates available as pre-commit hooks

### Testing

- **Test Coverage**: Maintained at 87.29% (exceeds 85% threshold)
- **New Test Suites**:
  - `tests/test_analytics.py`: Ranking strategies and edge cases
  - `tests/test_schema.py`: Schema extraction and JSON export
  - `tests/test_drift.py`: Version comparison and remediation
  - `tests/test_logging.py`: Structured logging regression tests
- **Enhanced Coverage**:
  - Release retry propagation and sanitization edge cases
  - Checksum manifest validation (happy-path, mismatch, bypass, missing)
  - Sigstore verification with multi-pattern identity matching
  - Dangerous path protection for cleanup and extra-paths
  - Tool version drift detection and remediation

### Infrastructure

- **Frontier Quality Standards**: Established and enforced
  - Zero-tolerance linting (Ruff with strict rules)
  - Type safety (Mypy strict mode, full coverage)
  - High test coverage (≥85% enforced)
  - Security auditing (pip-audit in CI)
  - Architecture linting (nested decorator prevention)
- **CI Integration**: All quality gates run on PR and main pushes
- **Telemetry Schema**: Operation correlation contexts for observability

## [0.1.0] - Initial Release

### Added

- **Core CLI Framework**: Typer-based command-line interface
- **Cleanup Command**: Development artifact removal
  - Build artifacts (dist/, build/, .pyc files)
  - Python caches (**pycache**, .pytest_cache)
  - macOS metadata (.DS_Store)
  - Coverage reports
- **Release Command**: Wheelhouse installation from GitHub releases
  - Download and extract release archives
  - Install dependencies via pip
  - Caching support
- **Tools Command**: Refactoring toolkit integration
  - Plan generation
  - Hotspot analysis
- **Planning Module**: Refactoring plan generation
  - Priority-based recommendations
  - Risk assessment
- **Toolbox Module**: Synthetic data for testing
  - Deterministic analytics
  - Predictable outputs for AI agents
- **Rich CLI Output**: Formatted tables and progress indicators
- **Documentation**: Diátaxis-structured guides
  - Architecture explanation
  - CLI reference
  - Refactoring toolkit guide
- **Testing Infrastructure**:
  - pytest with coverage reporting
  - Type checking with mypy
  - Linting with ruff
  - Security auditing with pip-audit

[Unreleased]: https://github.com/IAmJonoBo/Hephaestus/compare/v0.2.0...HEAD
[0.2.0]: https://github.com/IAmJonoBo/Hephaestus/compare/v0.1.0...v0.2.0
[0.1.0]: https://github.com/IAmJonoBo/Hephaestus/releases/tag/v0.1.0
