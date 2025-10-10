# Next Steps Tracker

Last updated: 2025-02-XX (Service-account RBAC & audit hardening follow-up)

## Tasks

- [x] Raise API auth/audit coverage above 85% and fix lint regressions _(Owner: Agent, Due: 2025-02-XX)_
- [ ] Expand gRPC interceptor and streaming ingestion tests for edge cases _(Owner: API Team, Due: 2025-03-01)_
- [ ] Validate `.hephaestus/audit/` durability and configurability in target deployments _(Owner: Ops, Due: 2025-03-05)_
- [ ] Trigger `.github/workflows/sigstore-backfill.yml` and capture the GitHub run ID _(Owner: Release Eng, Due: 2025-03-15)_

## Steps

- [x] Added negative-path auth unit tests (unsupported alg, missing timestamps, unknown key) covering verifier error handling.
- [x] Exercised default keystore environment wiring and key expiry helpers to hit new code paths.
- [x] Updated gRPC interceptor typing to satisfy Ruff modernisation rules and chained abort exceptions.
- [ ] Author targeted streaming/backpressure coverage for analytics ingestion once grpc extras available in CI.

## Deliverables

- Strengthened `tests/test_api_auth.py` with edge-case token validation coverage.
- Updated `src/hephaestus/api/grpc/server.py` typing for Ruff compatibility and clearer exception chaining.
- Baseline docs (`docs/how-to/operating-safely.md`, `docs/adr/0004-rest-grpc-api.md`) already aligned with service-account guidance; no new doc changes required this pass.

## Quality Gates

- [x] `uv run --extra qa --extra dev pytest --cov=src` (359 passed, 4 skipped, 85.07% coverage)【677cee†L1-L37】
- [x] `uv run --extra qa --extra dev ruff check .`【87fc91†L1-L2】
- [x] `uv run --extra qa --extra dev mypy src tests`【c20811†L1-L2】
- [⚠️] `uv run --extra qa --extra dev pip-audit` (known GHSA-4xh5-x5gv-qwph affecting `pip`; waiver required)【c6bef7†L1-L7】
- [x] `uv build`【d339db†L1-L4】

## Links

- `src/hephaestus/api/auth.py`
- `src/hephaestus/api/grpc/server.py`
- `tests/test_api_auth.py`
- `docs/how-to/operating-safely.md`
- `docs/adr/0004-rest-grpc-api.md`

## Risks/Notes

- gRPC integration tests still skip because `grpcio` extra is unavailable in this environment; install extras before adding streaming coverage.
- `.hephaestus/audit/` directory permissions in production remain a deployment concern—documented in operating guide but pending field validation.
- `pip-audit` continues to flag GHSA-4xh5-x5gv-qwph for `pip`; track upstream release for remediation.
