# Next Steps Tracker

Last updated: 2025-10-14 (Backfill CLI refactor implemented; guard-rails re-run)

## Tasks

- [x] Integrate Sigstore backfill into Python package for wheel distribution _(Owner: Agent, Due: 2025-10-14)_
  - [x] Move script logic into `src/hephaestus/backfill.py` callable.
  - [x] Update CLI `hephaestus release backfill` to call shared implementation.
  - [x] Maintain/rework standalone script wrapper + packaging metadata.
  - [x] Extend automated tests covering CLI invocation in installed context.
  - [ ] Refresh documentation/changelog if behaviour shifts. _(Review need post-analysis)_
- [ ] Document pip-audit limitation (package absent on PyPI until publish). _(Owner: Agent)_

## Steps

- [x] Reviewed repository context: README, CONTRIBUTING, CHANGELOG, SECURITY policy, packaging configs, and CI guidance to confirm guard-rail expectations.
- [x] Established baseline guard-rails (tests, lint, format, type-check, build, security scan noting known pip-audit limitation).
- [x] Design module integration approach and test strategy before refactor.
- [x] Implement code + tests, update packaging metadata, rerun guard-rails.
- [ ] Prepare PR summary with coverage impact and residual risks.

## Deliverables

- Updated `src/hephaestus/backfill.py` exposing reusable `run_backfill` entry point.
- Revised `src/hephaestus/cli.py` invoking the new callable.
- Maintained or replaced `scripts/backfill_sigstore_bundles.py` wrapper.
- Expanded tests (e.g., `tests/test_backfill.py` or CLI smoke) exercising installed CLI.
- Packaging metadata (`pyproject.toml`, `MANIFEST.in`) aligned with new layout.

## Quality Gates

- [x] `uv run --extra qa --extra dev pytest --cov=src` (pass: 399 passed, coverage 85.44%).【55882f†L1-L53】
- [x] `uv run --extra qa --extra dev ruff check .` (pass).【55fc7c†L1-L2】
- [x] `uv run --extra qa --extra dev ruff format --check .` (pass).【df8e1a†L1-L1】
- [x] `uv run --extra qa --extra dev mypy src tests` (pass).【438186†L1-L1】
- [ ] `uv run --extra qa --extra dev pip-audit --strict --ignore-vuln GHSA-4xh5-x5gv-qwph` (fails: package not yet on PyPI).【2da83a†L1-L1】【6b5919†L1-L1】
- [x] `uv build` (pass).【4ad6cc†L1-L2】【4fd8c0†L1-L3】

## Links

- `scripts/backfill_sigstore_bundles.py`
- `src/hephaestus/backfill.py`
- `src/hephaestus/cli.py`
- `tests/test_backfill.py`
- `pyproject.toml`
- `MANIFEST.in` (if present)

## Risks/Notes

- pip-audit fails until `hephaestus-toolkit` is published; continue documenting this gap.
- CLI invocation now delegates to library callable; monitor for behavioural regressions in environments relying on script path.
- Documentation review pending to confirm no user-facing updates required.
