# Next Steps Tracker

Last updated: 2025-10-10 (Marketplace manifest + telemetry instrumentation implemented)

## Tasks

- [x] Expand ADR-0002 with marketplace schema (metadata, trust policies) _(Owner: Agent, Due: 2025-10-12)_
- [x] Implement marketplace discovery with dependency resolution, signatures, telemetry _(Owner: Agent, Due: 2025-10-12)_
- [x] Update plugin development docs with publishing/consumption flows & rollback _(Owner: Agent, Due: 2025-10-12)_
- [ ] Restore guard-rail baselines (tests, lint, typecheck, security scan) after marketplace changes _(Owner: Agent, Due: 2025-10-12)_

## Steps

- [x] Design marketplace manifest schema covering compatibility, dependencies, and signature/trust metadata.
- [x] Author integration tests for marketplace manifest loading and telemetry before implementing loader changes.
- [x] Implement dependency resolution, version pinning, and signature verification in plugin discovery.
- [x] Surface curated registry assets under `plugin-templates/registry/` and wire discovery.
- [x] Document publishing, review, rollback, and telemetry workflows for marketplace adoption.

## Deliverables

- ADR-0002 appendix detailing marketplace schema and trust model.
- Marketplace registry assets with curated manifest + Sigstore bundle samples.
- Enhanced plugin discovery with dependency resolution, signature enforcement, and telemetry counters.
- Updated how-to guide describing publish/consume workflows and rollback procedures.
- Integration tests verifying manifest loading, dependency enforcement, and telemetry hooks.

## Quality Gates

- [ ] `uv run --extra qa --extra dev pytest --cov=src` (fails: SyntaxError in `tests/test_grpc.py` pre-existing)【302a5d†L1-L26】
- [ ] `uv run --extra qa --extra dev ruff check .` (fails: legacy undefined names in tests)【6f1cce†L1-L32】
- [ ] `uv run --extra qa --extra dev ruff format --check .` (fails: repository still contains unformatted legacy files)【52a697†L1-L21】
- [ ] `uv run --extra qa --extra dev mypy src tests` (fails: legacy undefined names in tests)【975be9†L1-L9】
- [⚠️] `uv run --extra qa --extra dev pip-audit --strict --ignore-vuln GHSA-4xh5-x5gv-qwph` (blocked: SSL certificate verification failure to pypi.org)【6ee461†L1-L39】
- [x] `uv build`【f3c827†L1-L4】

## Links

- `docs/adr/0002-plugin-architecture.md`
- `src/hephaestus/plugins/__init__.py`
- `plugin-templates/example-plugin/example_plugin.py`
- `docs/how-to/plugin-development.md`
- `tests/test_plugins_integration.py`

## Risks/Notes

- Baseline guard-rail suite currently red due to legacy test fixture regressions; resolve alongside marketplace implementation.
- pip-audit blocked by SSL trust failure in this environment—treat as infrastructure limitation and document in final report.
- Signature verification logic must remain deterministic/offline to ensure tests run without external network calls.
- Marketplace registry should preserve backwards compatibility for existing `.hephaestus/plugins.toml` configurations.
