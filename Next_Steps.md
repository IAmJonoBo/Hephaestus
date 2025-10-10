# Next Steps Tracker

Last updated: 2025-10-10 (Documentation refresh, gap analysis, release readiness)

## Current Status Summary
- ✅ Frontier feature set implemented: FastAPI + gRPC parity, streaming analytics ingestion, auto-remediation, Sigstore-gated releases, and plugin discovery resets.
- ✅ Quality gates enforced via CI (lint, type-check, tests with ≥85% coverage, drift detection, build verification).
- 🔄 Focus now shifts to production hardening: telemetry sampling/exporters, Sigstore backfill execution, API authentication, and marketplace ecosystem work.
Last updated: 2025-02-XX (API streaming + remediation automation)

## Current Status Summary

### All Critical Infrastructure: ✅ COMPLETE

The Hephaestus project has successfully delivered all high-priority features and infrastructure:

- ✅ Security hardening (checksums, Sigstore, dangerous path protection, SECURITY.md, STRIDE threat model)
- ✅ Quality gates (guard-rails, drift detection, CodeQL, comprehensive test coverage)
- ✅ AI integration (schema export, agent guide, ranking API, structured logging)
- ✅ Documentation (MkDocs site, Diátaxis structure, comprehensive how-tos)
- ✅ Developer experience (cleanup safety, dry-run previews, audit manifests)

### Future Work: Planned & Scheduled

Remaining work is focused on advanced features with clear ADRs and sprint-based timelines:

- 🔄 ADR-0006: Sigstore bundle backfill Sprint 2 (execution ready, pending manual trigger)
- 🔄 ADR-0005: PyPI publication Sprint 3 (workflow complete, pending account registration)
- ⏳ ADR-0003: OpenTelemetry Sprint 4 (sampling strategies, plugin instrumentation, Prometheus exporter)
- ⏳ ADR-0004: REST/gRPC API Sprint 2+ (FastAPI implementation, authentication, gRPC service)
- ⏳ ADR-0002: Plugin architecture Sprint 4 (marketplace, dependency resolution, versioning)

## Recent Improvements (Latest Session)

**API Service Hardening (2025-02-XX):**

- ✅ Replaced REST and gRPC guard-rails and cleanup stubs with shared execution helpers exposing real cleanup manifests, plugin readiness, and drift summaries.
- ✅ Unified analytics rankings and hotspot outputs across REST and gRPC by routing through the toolkit analytics pipeline with synthetic fallbacks when no datasets are configured.
- ✅ Regenerated protobuf definitions to add `auto_remediate` support and aligned CI-safe cleanup previews between HTTP and gRPC flows.
- 🔄 Follow-up: persist streaming analytics snapshots for ranking inputs and emit remediation telemetry for API consumers.
- ✅ Guard-rails helpers now fail closed when required plugin tooling is missing and surface the missing inventory in both REST helpers and unit coverage.

**API Streaming & Remediation Automation (2025-02-XX):**

- ✅ Implemented FastAPI analytics streaming ingestion with NDJSON parsing, bounded buffering, and shared ingestion telemetry for REST and gRPC surfaces.
- ✅ Extended gRPC analytics service with client-streaming ingestion RPC and regression coverage for acceptance/rejection flows.
- ✅ Added automated drift remediation path (`--auto-remediate`) with command execution telemetry, plus CI drift gate (`uv run hephaestus guard-rails --drift`).
- ✅ Introduced shared streaming analytics ingestor with snapshot API and reset hooks for deterministic testing.
- 🔄 Follow-up: expand analytics streaming persistence/retention policies and surface ingestion metrics over OpenTelemetry exporters.

**Release & Plugin Hardening (2025-02-XX):**

- ✅ Expanded CLI coverage to exercise `release install --remove-archive` cleanup and Sigstore backfill flows, lifting overall coverage to 86.95% (338 passed, 4 skipped).
- ✅ Added regression tests for Ruff plugin failure handling and gRPC optional dependencies, ensuring modules skip cleanly when toolchains are absent.
- ✅ Tightened lint gates by excluding generated protobuf stubs, modernising typing usage, and fixing import ordering across telemetry/plugin scaffolding.
- ✅ Documented security scan limitations (pip-audit SSL chain) and kept build pipeline (`uv build`) green for release packaging.
- 🔄 Follow-up: extend CLI cleanup pipeline tests to cover confirmation prompts/out-of-root warnings and plug remaining uncovered branches.

**Telemetry Fallback Hardening (2025-02-XX):**

- ✅ Rebuilt `hephaestus.telemetry` shims to provide typed fallbacks with deterministic no-op behaviour when OpenTelemetry is absent.
- ✅ Re-ran type checking (`uv run mypy src tests`) to confirm the TaskManager and REST changes compile cleanly.
- ✅ Re-validated REST regression suites (`uv run pytest`) to ensure SSE/task polling updates remain green (345 passed, 3 skipped, 85.51% coverage).
- ✅ Targeted lint pass for the touched telemetry module (`uv run ruff check src/hephaestus/telemetry/__init__.py`).
- ⚠️ `uv run pip-audit` blocked by container SSL trust chain; document waiver and retry once trust store is patched.
- 🔄 Follow-up: reconcile repository-wide Ruff violations in generated gRPC assets without regressing proto sync (coordinate with tooling owner).

**E2E Testing & Validation (2025-10-09):**

- ✅ Comprehensive E2E test suite (8 tests) covering setup, cleanup, and Renovate workflows
- ✅ Critical bug fix: Cleanup now preserves site-packages in virtual environments
- ✅ Yamllint configuration fix: Removed hardcoded non-existent config path
- ✅ E2E testing documentation guide (docs/how-to/e2e-testing.md)
- ✅ Regression tests for site-packages preservation
- ✅ Renovate compatibility tests for dependency updates
- ✅ All tests passing (185 passed, 86.76% coverage)
- ✅ Setup-dev-env.sh validated E2E with guard-rails pipeline

**Authentication & Authorization Hardening (2025-01-XX):**

- ✅ Token validation before GitHub API calls with format validation
- ✅ Support for classic, fine-grained, and PAT GitHub token formats
- ✅ Token expiration detection with clear HTTP 401 error messages
- ✅ Added telemetry event for token validation warnings
- ✅ Comprehensive test coverage (7 new tests)

**AI-Native Workflows & Analytics (2025-01-XX):**

- ✅ Analytics ranking API: 4 strategies (risk_weighted, coverage_first, churn_based, composite)
- ✅ CLI command: `hephaestus tools refactor rankings` with strategy selection
- ✅ Command schema export: `hephaestus schema` for AI agent integration
- ✅ AI integration guide: Comprehensive docs for Copilot/Cursor/Claude
- ✅ Guard-rails drift detection: `hephaestus guard-rails --drift` with remediation
- ✅ Tool version management: Automatic detection and fix suggestions
- ✅ Telemetry events: Added drift detection events to registry

**Security & Safety Enhancements:**

- ✅ Extra paths validation: Added dangerous path checks for `--extra-path` arguments
- ✅ Parameter validation: Added timeout and max_retries validation in release functions
- ✅ Status updates: Marked completed red team findings as Complete in tracker
- ✅ Sanitisation hardening: Asset name sanitiser now rejects bare `.`/`..` inputs and logs rewrites
- ✅ Checksum enforcement: Wheelhouse downloads now require SHA-256 manifests unless explicitly opted out
- ✅ Sigstore attestation verification: Wheelhouse installs now validate Sigstore bundles with optional identity pinning and fail-closed controls
- ✅ Cleanup UX guard rails: Mandatory dry-run previews, typed confirmation for out-of-root targets, and JSON audit manifests shipped

**Observability & Intelligence Improvements:**

- ✅ Enhanced logging: Added info-level logging for release download/install operations
- ✅ Error handling: Improved guard-rails error reporting with clear failure messages
- ✅ Frontier audit doc: Authored comprehensive red team & gap analysis and published via MkDocs nav
- ✅ Structured logging: Introduced run ID-aware JSON/text emitters with CLI switches and release/cleanup event coverage
- ✅ Telemetry schema: Standardised event definitions and CLI operation correlation with operation/run identifiers
- ✅ Analytics ingestion: Added pluggable churn/coverage/embedding adapters and data-backed hotspot/refactor planning defaults

**Testing:**

- ✅ Added tests for extra_paths dangerous path validation
- ✅ Added tests for timeout and max_retries parameter validation
- ✅ Added release retry propagation, sanitisation edge cases, and timeout coverage tests
- ✅ Added checksum manifest happy-path, mismatch, bypass, and missing-manifest coverage
- ✅ Added structured logging regression tests covering JSON/text output and context binding
- ✅ Added CLI regression coverage for release install Sigstore flags and multi-pattern identity matching

## Baseline Validation (current session)

- ✅ `uv run --extra qa --extra dev pytest --cov=src` (345 passed, 4 skipped, 86.43% coverage)【e8df50†L1-L34】
- ✅ `uv run --extra qa --extra dev ruff check .`【8fce87†L1-L2】
- ✅ `uv run --extra qa --extra dev mypy src tests`【eac22d†L1-L2】
- ⚠️ `uv run --extra qa --extra dev pip-audit` (fails: SSL certificate verification error against pypi.org; trust store remediation still required)【fc475e†L1-L41】
- ✅ `uv build`【b30d96†L1-L4】

## Implementation Status Summary

**High Priority (Security & Safety):**

- ✅ SECURITY.md published with disclosure process
- ✅ STRIDE threat model completed (ADR-0001)
- ✅ Guard-rails command implemented at module scope
- ✅ Cleanup safety rails with dangerous path protection
- ✅ Cleanup dry-run previews, confirmations, and audit manifests implemented and documented
- ✅ Operating Safely guide created
- ✅ Rollback procedures documented
- ✅ Test order independence (pytest-randomly added)
- ✅ Release networking with timeout/backoff enhancements
- ✅ Release checksum verification complete (checksums + Sigstore verification)

**Medium Priority (Quality & Observability):**

- ✅ Dependency versions refreshed (ruff, black, mypy, pip-audit)
- ✅ Documentation comprehensive and up-to-date
- ✅ Asset name sanitization implemented and tested
- ✅ Basic logging added for release operations (fetch, download, install)
- 🔄 Structured JSON logging shipped; telemetry spans planned for Q2

**Low Priority (Operational Excellence):**

- ✅ Rollback documentation complete with templates
- ✅ CI lint for nested decorators (automated)

Legend: ✅ Complete | 🔄 In Progress | ⏳ Planned

---

## Red Team Findings

| Priority | Area                    | Observation                                                                                                                                                                                                                       | Impact                                                                             | Recommendation                                                                                                                                                                                                                                      | Owner   | Status      |
| -------- | ----------------------- | --------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------- | ---------------------------------------------------------------------------------- | --------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------- | ------- | ----------- |
| High     | Release supply chain    | Wheelhouse installs now fail closed without matching SHA-256 manifests and validate Sigstore bundles when they are published.                                                                                                     | Supply-chain compromise risk narrows to unsigned archives and unpinned identities. | Backfill Sigstore bundles for historical releases, require identities via `--sigstore-identity`, and enable `--require-sigstore` in automation to block unsigned installs.                                                                          | Tooling | In Progress |
| High     | Cleanup ergonomics      | `cleanup` will happily scrub any `--extra-path` (even `/`), and when invoked outside a git repo it treats the CWD as root. A typo can wipe unrelated directories.                                                                 | Catastrophic operator error / accidental data loss.                                | Refuse to operate on paths outside the repo unless `--allow-outside-root` (with confirmation), disallow `/` and home directory targets, and emit a dry-run summary before deletion.                                                                 | DX      | Complete    |
| Medium   | Guard rail availability | The `guard_rails` command is defined inside the `cleanup` function, so it is only registered after the cleanup command runs once per process. Fresh shells cannot invoke guard rails and therefore skip automated security scans. | Guard rails silently unavailable -> reduced local/AppSec coverage.                 | Hoist `_format_command` and `guard_rails` to module scope, add a regression test that `cli.app.registered_commands` includes `guard-rails` pre-execution, and document expected usage. Current local edits regressed command wiring—needs re-hoist. | DX      | Complete    |
| Low      | Asset name sanitisation | Release assets are written to disk using the server-provided filename without validating path separators. GitHub currently rejects `/`, but defensive sanitisation is advisable.                                                  | Future path traversal if upstream validation changes.                              | Strip `..`/path separators from asset names before joining paths and log when sanitisation occurs.                                                                                                                                                  | Tooling | Complete    |

## Engineering Gaps & Opportunities

| Priority | Theme                        | Gap                                                                                                                       | Recommendation                                                                                                                                                                                              |
| -------- | ---------------------------- | ------------------------------------------------------------------------------------------------------------------------- | ----------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------- |
| High     | Secure development lifecycle | No `SECURITY.md` or published disclosure process; threat models live implicitly in docs.                                  | Add a `SECURITY.md`, document contact channels, expected SLAs, and link it from README & docs. Run a lightweight STRIDE-style threat model for the CLI + release pipeline and archive it under `docs/adr/`. |
| High     | Test reliability             | Pytest suites rely on running `cleanup` before `guard-rails`; this masks the registration bug and could regress silently. | Make tests order-independent (use pytest-randomly), restructure fixtures, and add explicit coverage for command registration.                                                                               |
| Medium   | Dependency hygiene           | Tooling pins (ruff 0.6.8, black 24.8.0, pip-audit ignore) are several releases behind as of Oct 2025.                     | Refresh `pyproject.toml` and `.pre-commit-config.yaml`, drop stale ignores once upstream patches land, and automate monthly dependency health checks beyond Dependabot (e.g., uv lockfile freshness).       |
| Medium   | Operational observability    | No telemetry around CLI/network failures; troubleshooting remote release installs is guesswork.                           | Emit structured logs/metrics (JSON events) for fetch/install stages and capture anonymised stats in CI (e.g., using OpenTelemetry exporters guarded behind env flags).                                      |
| Medium   | Documentation                | Cleanup safeguards, guard rail expectations, and release hardening steps are undocumented.                                | Add "Operating Safely" guide under `docs/how-to/` explaining cleanup constraints, guard-rail workflows, and release verification steps for contributors.                                                    |
| Low      | Incident readiness           | No documented rollback or release revocation procedure if a bad wheelhouse ships.                                         | Extend `docs/pre-release-checklist.md` with rollback guidance and automate revocation (delete releases, publish advisory).                                                                                  |

## Action Queue

1. **Secure the release channel** – land checksum/signature verification and timeout/backoff handling, then backfill signed artefacts for historical releases.
   - [x] Implement SHA-256 checksum verification for wheelhouse downloads
   - [x] Add Sigstore attestation support
   - [x] Enhance timeout/backoff handling with exponential backoff (Complete)
2. **Ship cleanup safety rails** – introduce protective defaults and update docs/tests to demonstrate safe usage.
   - [x] Implemented dangerous path blocklist (/, /home, /usr, /etc)
   - [x] Added is_dangerous_path() validation in resolve_root()
   - [x] Created tests for dangerous path protection
   - [x] Documented safety features in Operating Safely guide
   - [x] Added dry-run preview, typed confirmation, and audit manifest support with regression coverage
3. **Unblock guard rails everywhere** – move the command registration to module scope, randomise pytest order, and add CI lint to prevent nested decorators.
   - [x] Guard-rails command registered at module scope with full pipeline (`src/hephaestus/cli.py`).
   - [x] Regression test validates command registration (`tests/test_cli.py`).
   - [x] Added pytest-randomly to dependencies for test order independence
   - [x] CLI wiring restored and documented in README
   - [x] Add CI lint to prevent nested decorators (script created, CI updated)
4. **Formalise AppSec posture** – publish `SECURITY.md`, threat model notes, and operational runbooks (rollback, telemetry, disclosure).
   - [x] Published SECURITY.md with disclosure process, contact channels, and SLAs
   - [x] Created STRIDE threat model (docs/adr/0001-stride-threat-model.md)
   - [x] Documented rollback procedures in pre-release-checklist.md
   - [x] Created Operating Safely guide with operational runbooks
   - [x] Linked security documentation from README
5. **Refresh automation dependencies** – bump pre-commit hooks and revisit the pip-audit CVE waiver once patched.
   - [x] Updated ruff from 0.6.8 to 0.8.6
   - [x] Updated black from 24.8.0 to 25.1.0
   - [x] Updated mypy from 1.11.2 to 1.14.1
   - [x] Updated pip-audit from 2.7.3 to 2.9.2
   - [x] Updated pyupgrade from 3.19.0 to 3.19.3
   - [ ] Revisit GHSA-4xh5-x5gv-qwph waiver once upstream patches
6. **Resynchronise with upstream** – fetch and merge `origin/main` to reconcile CLI and release command divergences before landing further changes.
   - [x] Working from grafted main branch
   - [ ] Final sync before merge
7. **Operational telemetry & AI readiness** – execute follow-ups from the frontier red team gap analysis.

- [x] Publish frontier red team & gap analysis doc (docs/explanation/frontier-red-team-gap-analysis.md)
- [x] Ship structured JSON logging + run IDs across CLI, release, and cleanup
- [x] Add cleanup dry-run previews, confirmations, and audit manifests
- [x] Define telemetry event registry with operation/run correlation contexts across CLI + release flows
- [x] Replace synthetic analytics with pluggable churn/coverage/embedding adapters
- [ ] Expose an API surface (REST/gRPC) for AI/automation clients with policy guard rails

1. **Telemetry shim hardening** – keep typed fallbacks aligned with OTEL integrations and tooling gates.

- [x] Rebuild telemetry shims with typed no-op paths and cached module resolution.
- [x] Verify mypy + pytest green against updated shims.
- [ ] Update Ruff configuration or proto generation pipeline to silence deterministic lint noise for gRPC artefacts.
- [ ] Re-run `pip-audit` once container trust store is refreshed; capture waiver scope if issues persist.

---

## Tasks
- [ ] Execute Sigstore bundle backfill runbook and capture attestation inventory (Release Engineering – due 2025-11-01).
- [ ] Register PyPI publisher account and dry-run publication workflow (Release Engineering – due 2025-10-24).
- [ ] Implement OpenTelemetry sampling strategies and Prometheus exporter (Observability – due 2025-11-15).
- [ ] Add API authentication/authorization with service accounts and audit logging (API Team – due 2025-11-08).
- [ ] Design plugin marketplace metadata (discovery, dependency resolution, version pinning) (Ecosystem – due 2025-11-30).
- [ ] Ship streaming analytics retention policy and ingestion metrics surfaced via telemetry (Analytics – due 2025-11-22).
- [ ] Automate drift remediation playbooks for top CI failure signatures (QA – due 2025-11-12).

## Steps
- [ ] Finalise Sigstore backfill dry-run against staging artifacts, validate manifests, and document rollback.
- [ ] Draft API auth ADR covering token formats, RBAC, and secret storage requirements.
- [ ] Prototype OTEL span sampling knobs with CLI + API instrumentation smoke tests.
- [ ] Document ingestion retention/metrics plan and update analytics configuration schema.

## Deliverables
- 📄 Updated ADRs: 0002 (Marketplace), 0003 (Telemetry Sprint 4), 0004 (API Sprint 2+), 0005 (PyPI release), 0006 (Sigstore backfill execution).
- 📦 Release candidate with enforced Sigstore backfill, drift gate, and telemetry exporters enabled by default.
- 📊 Analytics observability dashboard (latency, acceptance rate, remediation outcomes).
- 🔐 Authenticated API deployment guide with operational runbooks.

## Quality Gates
- ✅ Test coverage ≥ 85% (current: 86.46%).
- ✅ Lint (ruff), type-check (mypy), build (uv build) must pass pre-merge.
- ⚠️ Pip-audit blocked by container SSL trust chain; mitigation tracked in Risks/Notes.
- 🔄 OTEL sampling + Prometheus exporter to add latency/error SLOs before general release.

## Links
- README overview refresh【F:README.md†L1-L120】
- Frontier red-team gap analysis (updated)【F:docs/explanation/frontier-red-team-gap-analysis.md†L1-L200】
- Sigstore & release automation code【F:src/hephaestus/release.py†L1-L200】
- API service parity tests【F:tests/test_api.py†L1-L200】

## Risks/Notes
- Pip-audit fails due to missing trust anchor in the container; rerun once trust store is patched or proxy provided.
- API lacks first-party auth; short-term mitigation relies on network isolation and short-lived tokens.
- Telemetry exporters absent; downstream observability limited to logs until sampling/export landed.
- Streaming ingestion stores snapshots in-memory; persistence is required before multi-tenant rollout.

## Gap Analysis Highlights
- **Telemetry:** Command spans exist but sampling/export strategies remain manual; need Prometheus + OTLP exporters.
- **Supply Chain:** Sigstore metadata ready but historical releases still require bundle backfill before GA.
- **API Security:** FastAPI service lacks auth/RBAC; gRPC lacks channel credentials; need consistent secret rotation story.
- **Analytics:** Streaming ingestion online yet retention + metrics missing; CLI/API should surface ingestion health and quotas.
- **Ecosystem:** Plugin discovery resets state but marketplace semantics (versioning, dependency resolution) remain unsolved.

## Red Team Observations
- Attack simulations confirm guard-rails fail closed when tooling missing, but API endpoints still trust inbound requests implicitly.
- Cleanup manifests deter destructive misuse; next escalation involves tampered Sigstore bundles—backfill execution and identity enforcement mitigate.
- Drift remediation automation needs rate limits and audit trails to prevent runaway fixes triggered by noisy signals.

## Baseline Validation (current session)
- ✅ `uv run --extra qa --extra dev pytest --cov=src` (345 passed, 4 skipped, 86.46% coverage)【2bb7ae†L1-L34】
- ✅ `uv run --extra qa --extra dev ruff check .`【34de62†L1-L2】
- ✅ `uv run --extra qa --extra dev mypy src tests`【06ed06†L1-L2】
- ⚠️ `uv run --extra qa --extra dev pip-audit` (fails: SSL certificate verification error against pypi.org)【e8840c†L1-L41】
- ✅ `uv build`【18f179†L1-L4】
