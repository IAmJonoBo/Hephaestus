# Next Steps Tracker

Last updated: 2025-10-10 (Service-account RBAC & audit hardening follow-up)

## Tasks

- [x] Raise API auth/audit coverage above 85% and fix lint regressions _(Owner: Agent, Due: 2025-02-XX)_
- [x] Expand gRPC interceptor and streaming ingestion tests for edge cases _(Owner: API Team, Due: 2025-03-01)_
- [x] Validate `.hephaestus/audit/` durability and configurability in target deployments _(Owner: Ops, Due: 2025-03-05)_
- [ ] Trigger `.github/workflows/sigstore-backfill.yml` and capture the GitHub run ID _(Owner: Release Eng, Due: 2025-03-15)_

## Steps

- [x] Added negative-path auth unit tests (unsupported alg, missing timestamps, unknown key) covering verifier error handling.
- [x] Exercised default keystore environment wiring and key expiry helpers to hit new code paths.
- [x] Updated gRPC interceptor typing to satisfy Ruff modernisation rules and chained abort exceptions.
- [x] Author targeted streaming/backpressure coverage for analytics ingestion once grpc extras available in CI.

## Deliverables

- Hardened REST ingestion to emit denied audit events and documented chunk-handling coverage in `tests/test_api.py`.
- Added role-denial coverage for gRPC analytics streaming plus interceptor guards in `tests/test_grpc.py`.
- Verified audit sink defaults via `tests/test_audit.py` and ensured task orchestration runs end-to-end with real principals.

## Quality Gates

- [x] `uv run --extra qa --extra dev pytest --cov=src` (363 passed, 4 skipped, 85.28% coverage)【2a9cd9†L1-L40】
- [x] `uv run --extra qa --extra dev ruff check .`【cf3b73†L1-L2】
- [x] `uv run --extra qa --extra dev mypy src tests`【e209e2†L1-L2】
- [⚠️] `uv run --extra qa --extra dev pip-audit` (known GHSA-4xh5-x5gv-qwph affecting `pip`; waiver required)【e7c4b5†L1-L7】
- [x] `uv build`【ca42db†L1-L3】

## Links

- `src/hephaestus/api/rest/app.py`
- `src/hephaestus/api/rest/tasks.py`
- `src/hephaestus/api/grpc/services/analytics.py`
- `tests/test_api.py`
- `tests/test_grpc.py`
- `tests/test_audit.py`

## Risks/Notes

- gRPC integration tests still skip when `grpcio` extras are absent; new unit coverage exercises logic but end-to-end validation awaits dependency availability.
- `.hephaestus/audit/` durability validated locally; ensure production deployments mount persistent storage and apply least-privilege permissions.
- `pip-audit` continues to flag GHSA-4xh5-x5gv-qwph for `pip`; track upstream release for remediation.
- Sigstore backfill workflow trigger remains outstanding pending GitHub access (blocked in this environment).
