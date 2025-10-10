# Next Steps Tracker

Last updated: 2025-10-12 (Restored coverage gate with focused marketplace helper tests)

## Tasks

- [x] Expand ADR-0002 with marketplace schema (metadata, trust policies) _(Owner: Agent, Due: 2025-10-12)_
- [x] Implement marketplace discovery with dependency resolution, signatures, telemetry _(Owner: Agent, Due: 2025-10-12)_
- [x] Update plugin development docs with publishing/consumption flows & rollback _(Owner: Agent, Due: 2025-10-12)_
- [ ] Restore guard-rail baselines (tests, lint, typecheck, security scan) after marketplace changes _(Owner: Agent, Due: 2025-10-12)_
  - [x] Tighten coverage on `plugins/__init__.py` marketplace helpers via targeted unit tests
  - [ ] Resolve repository-wide Ruff formatting drift (21 files outstanding)
  - [⚠️] Unblock SSL trust chain for pip-audit in constrained environments

## Upcoming Steps

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

- [x] `uv run --extra qa --extra dev pytest --cov=src` (pass: coverage 85.06%)【04036a†L1-L33】
- [x] `uv run --extra qa --extra dev ruff check .`【7ae325†L1-L2】
- [ ] `uv run --extra qa --extra dev ruff format --check .` (fails: repository still contains legacy formatting drift)【041318†L1-L22】
- [x] `uv run --extra qa --extra dev mypy src tests`【b130f4†L1-L2】
- [⚠️] `uv run --extra qa --extra dev pip-audit --strict --ignore-vuln GHSA-4xh5-x5gv-qwph` (blocked: SSL certificate verification failure to pypi.org)【4aa95e†L1-L36】
- [x] `uv build`【8059b2†L1-L4】

## Links

- `docs/adr/0002-plugin-architecture.md`
- `src/hephaestus/plugins/__init__.py`
- `plugin-templates/example-plugin/example_plugin.py`
- `docs/how-to/plugin-development.md`
- `tests/test_plugins_integration.py`
- `tests/test_plugins_marketplace.py`

## Risks/Notes

- Baseline guard-rail suite currently red due to legacy test fixture regressions; resolve alongside marketplace implementation.
- pip-audit blocked by SSL trust failure in this environment—treat as infrastructure limitation and document in final report.
- Signature verification logic must remain deterministic/offline to ensure tests run without external network calls; new unit tests assert both success and failure paths without external services.
- Marketplace registry should preserve backwards compatibility for existing `.hephaestus/plugins.toml` configurations.
