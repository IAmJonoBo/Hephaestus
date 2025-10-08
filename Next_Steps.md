# Next Steps Tracker

Last updated: 2025-01-08

## Recent Improvements (Latest Session)

**Security & Safety Enhancements:**

- ✅ Extra paths validation: Added dangerous path checks for `--extra-path` arguments
- ✅ Parameter validation: Added timeout and max_retries validation in release functions
- ✅ Status updates: Marked completed red team findings as Complete in tracker

**Observability Improvements:**

- ✅ Enhanced logging: Added info-level logging for release download/install operations
- ✅ Error handling: Improved guard-rails error reporting with clear failure messages

**Testing:**

- ✅ Added tests for extra_paths dangerous path validation
- ✅ Added tests for timeout and max_retries parameter validation

## Implementation Status Summary

**High Priority (Security & Safety):**

- ✅ SECURITY.md published with disclosure process
- ✅ STRIDE threat model completed (ADR-0001)
- ✅ Guard-rails command implemented at module scope
- ✅ Cleanup safety rails with dangerous path protection
- ✅ Operating Safely guide created
- ✅ Rollback procedures documented
- ✅ Test order independence (pytest-randomly added)
- ✅ Release networking with timeout/backoff enhancements
- 🔄 Release checksum verification (planned)

**Medium Priority (Quality & Observability):**

- ✅ Dependency versions refreshed (ruff, black, mypy, pip-audit)
- ✅ Documentation comprehensive and up-to-date
- ✅ Asset name sanitization implemented and tested
- ✅ Basic logging added for release operations (fetch, download, install)
- 🔄 Structured JSON logging/telemetry (planned for Q2)

**Low Priority (Operational Excellence):**

- ✅ Rollback documentation complete with templates
- 🔄 CI lint for nested decorators (planned)

Legend: ✅ Complete | 🔄 In Progress | ⏳ Planned

---

## Red Team Findings

| Priority | Area                    | Observation                                                                                                                                                                                                                       | Impact                                                                  | Recommendation                                                                                                                                                                                                                                      | Owner   | Status   |
| -------- | ----------------------- | --------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------- | ----------------------------------------------------------------------- | --------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------- | ------- | -------- |
| High     | Release supply chain    | `hephaestus release install` downloads wheelhouse archives over HTTPS but never verifies signatures or even checksums. A compromised GitHub release or CDN node could silently deliver poisoned wheels.                           | Supply-chain compromise risk for every consumer invoking the installer. | Publish a manifest with SHA-256/Sigstore attestations for each wheelhouse and verify before install; fail closed on mismatch. Pin the allowed repository/asset pattern and surface overrides behind an explicit `--allow-unsigned` escape hatch.    | Tooling | Open     |
| Medium   | Release networking      | `download_wheelhouse` performs blocking `urllib.request.urlopen` calls with default timeouts and zero retry logic. A slow or hostile endpoint can hang the CLI indefinitely.                                                      | Denial-of-service against CI pipelines and operators.                   | Add configurable timeouts, bounded retries with exponential backoff, and telemetry for repeated failures. Work-in-progress branch introduces retry helpers—needs completion and validation.                                                         | Tooling | Complete |
| High     | Cleanup ergonomics      | `cleanup` will happily scrub any `--extra-path` (even `/`), and when invoked outside a git repo it treats the CWD as root. A typo can wipe unrelated directories.                                                                 | Catastrophic operator error / accidental data loss.                     | Refuse to operate on paths outside the repo unless `--allow-outside-root` (with confirmation), disallow `/` and home directory targets, and emit a dry-run summary before deletion.                                                                 | DX      | Complete |
| Medium   | Guard rail availability | The `guard_rails` command is defined inside the `cleanup` function, so it is only registered after the cleanup command runs once per process. Fresh shells cannot invoke guard rails and therefore skip automated security scans. | Guard rails silently unavailable -> reduced local/AppSec coverage.      | Hoist `_format_command` and `guard_rails` to module scope, add a regression test that `cli.app.registered_commands` includes `guard-rails` pre-execution, and document expected usage. Current local edits regressed command wiring—needs re-hoist. | DX      | Complete |
| Low      | Asset name sanitisation | Release assets are written to disk using the server-provided filename without validating path separators. GitHub currently rejects `/`, but defensive sanitisation is advisable.                                                  | Future path traversal if upstream validation changes.                   | Strip `..`/path separators from asset names before joining paths and log when sanitisation occurs.                                                                                                                                                  | Tooling | Complete |

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
   - [ ] Implement SHA-256 checksum verification for wheelhouse downloads
   - [ ] Add Sigstore attestation support
   - [x] Enhance timeout/backoff handling with exponential backoff (Complete)
2. **Ship cleanup safety rails** – introduce protective defaults and update docs/tests to demonstrate safe usage.
   - [x] Implemented dangerous path blocklist (/, /home, /usr, /etc)
   - [x] Added is_dangerous_path() validation in resolve_root()
   - [x] Created tests for dangerous path protection
   - [x] Documented safety features in Operating Safely guide
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
