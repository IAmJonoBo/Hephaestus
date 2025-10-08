# Next Steps Tracker

Last updated: 2025-01-11 (Analytics ingestion adapters + telemetry correlation)

## Recent Improvements (Latest Session)

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

- ✅ `uv run --extra dev --extra qa pytest` (85 passed, coverage 87.29%)
- ✅ `uv run --extra dev --extra qa ruff check .`
- ✅ `uv run --extra dev --extra qa mypy src tests`
- ⚠️ `uv run --extra dev --extra qa pip-audit --strict --ignore-vuln GHSA-4xh5-x5gv-qwph` (fails: SSL trust chain unavailable in container)
- ✅ `uv run --extra dev --extra qa uv build`

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
- 🔄 CI lint for nested decorators (planned)

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
   - [ ] Add CI lint to prevent nested decorators
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

---

## Tasks

- [ ] (Tooling, due 2025-01-31) Implement SHA-256 checksum verification + fail-closed wheelhouse installs
  - Status: ✅ Delivered this pass; verification now required unless `--allow-unsigned`
- [ ] (Tooling, due 2025-02-28) Backfill Sigstore bundles for historical releases and add CI enforcement for attestations
- [x] (DX, due 2025-01-31) Add cleanup dry-run previews, confirmations, and audit manifests
- [ ] (Platform, due 2025-02-15) Ship structured JSON logging and OpenTelemetry spans across CLI/release/cleanup _(logging complete; spans pending)_
- [ ] (AI Insights, due 2025-03-01) Replace synthetic analytics with churn/coverage/embedding adapters and ranking API
  - Status: 🔄 Adapters delivered this pass (`src/hephaestus/analytics.py`); ranking API & streaming ingestion pending
- [ ] (Platform AI, due 2025-03-15) Expose secured REST/gRPC endpoints for AI/automation clients with policy guard rails

## Steps

- [x] Extend release tests to cover retry/backoff propagation and sanitisation edge cases
- [x] Add CLI regression coverage for release install Sigstore gating options
- [x] Design telemetry schema + correlation strategy for structured logging rollout _(telemetry module + CLI operation contexts shipped)_
- [x] Draft UX spec for cleanup dry-run + confirmation workflow _(implemented directly in CLI with preview/confirmation flow)_
- [x] Evaluate Sigstore tooling + release pipeline hooks for artifact attestation _(verification shipped; publishing pipeline follow-up pending)_
- [ ] Backfill Sigstore bundles for historical releases and enforce attestation publication in CI
- [x] Prototype analytics ingestion adapters against representative repositories

## Deliverables

- [x] Frontier red team & gap analysis documentation (docs/explanation/frontier-red-team-gap-analysis.md)
- [x] Strengthened release regression suite (tests/test_release.py)
- [x] Structured logging instrumentation across CLI/release/cleanup (src/hephaestus/logging.py, tests/test_logging.py)
- [x] Implementation PR for checksum verification + manifest management (includes Sigstore verification support)
- [x] Cleanup safety UX spec & implementation plan _(dry-run preview + confirmation shipped)_
- [x] Cleanup dry-run + audit manifest implementation (src/hephaestus/cleanup.py, src/hephaestus/cli.py, docs/how-to/operating-safely.md)
- [x] CLI release install regression coverage for Sigstore gating (tests/test_cli.py)
- [ ] Telemetry instrumentation plan + dashboards for guard-rail health
- [x] Analytics ingestion module + regression coverage (`src/hephaestus/analytics.py`, `tests/test_analytics.py`, `tests/test_toolbox.py`)

## Quality Gates

- [x] Tests: `uv run pytest`
- [x] Lint: `uv run ruff check .`
- [x] Types: `uv run mypy src tests`
- [ ] Security: `uv run pip-audit --strict --ignore-vuln GHSA-4xh5-x5gv-qwph` (fails: SSL trust chain unavailable in container)
- [x] Coverage ≥ 85% (enforced by pytest-cov)
- [x] Build artefacts: `uv run uv build`

## Links

- Release helpers: src/hephaestus/release.py
- Cleanup engine: src/hephaestus/cleanup.py
- CLI entrypoint: src/hephaestus/cli.py
- Logging utilities: src/hephaestus/logging.py
- Regression suites: tests/test_release.py, tests/test_cleanup.py
- Frontier analysis doc: docs/explanation/frontier-red-team-gap-analysis.md

## Risks / Notes

- pip-audit currently blocked by SSL trust chain inside container; rerun in CI or with configured cert bundle
- Attestation coverage: Backfill and enforce Sigstore bundles across historical releases to fully close the supply-chain risk
- Telemetry backlog blocks observability-driven SLOs; prioritise instrumentation once logging design is ready
- Monitor operator feedback on new cleanup preview/confirmation flow; extend with undo checkpoints if needed
