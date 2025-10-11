# Next Steps Tracker

Last updated: 2025-10-14 (UTC timestamp ingestion normalised and documented)

## Tasks

- [x] Normalise analytics streaming timestamp ingestion to handle UTC indicators like `Z`. _(Owner: Agent)_
  - [x] Ensure `StreamingAnalyticsIngestor.ingest_mapping` gracefully parses ISO 8601 strings with `Z` suffixes.
  - [x] Add regression test covering `Z` timestamps for REST ingestion persistence.
  - [x] Update REST/gRPC ingestion docs with accepted timestamp formats.
- [ ] Document pip-audit limitation (package absent on PyPI until publish). _(Owner: Agent)_

## Steps

- [x] Reviewed repository context (README, CONTRIBUTING, CHANGELOG, SECURITY, packaging configs, CI workflows) to confirm guard-rail expectations and analytics scope.
- [x] Established baseline guard-rails before modifications.
- [x] Design code changes and documentation updates.
- [x] Implement code + tests.
- [x] Re-run guard-rails after changes.
- [ ] Prepare PR summary with coverage impact and residual risks.

## Deliverables

- Updated `src/hephaestus/analytics_streaming.py` to normalise or fallback parse UTC timestamps.
- Regression tests (`tests/test_api.py`, `tests/test_analytics_streaming.py`) validating timestamp handling and persistence.
- Documentation updates describing accepted timestamp formats for REST and gRPC ingestion.

## Quality Gates

- [x] `uv run --extra qa --extra dev pytest --cov=src` (pass: 404 passed, coverage 85.39%).【508aef†L1-L47】
- [x] `uv run --extra qa --extra dev ruff check .` (pass).【79d040†L1-L2】
- [x] `uv run --extra qa --extra dev ruff format --check .` (pass).【74ed9c†L1-L2】
- [x] `uv run --extra qa --extra dev mypy src tests` (pass).【a93146†L1-L1】
- [ ] `uv run --extra qa --extra dev pip-audit --strict --ignore-vuln GHSA-4xh5-x5gv-qwph` (fails: package not yet on PyPI).【522b54†L1-L2】
- [x] `uv build` (pass).【dc2e89†L1-L4】

## Links

- `src/hephaestus/analytics_streaming.py`
- `tests/test_api.py`
- `tests/test_analytics_streaming.py`
- `docs/reference/api.md`
- `docs/api/examples/README.md`
- `docs-site/src/content/docs/reference/api.md`
- `docs-site/src/content/docs/api/examples/README.md`

## Risks/Notes

- pip-audit fails until `hephaestus-toolkit` is published; continue documenting this known gap.
- Ensure downstream consumers regenerate any cached client documentation to pick up updated ingestion guidance.
