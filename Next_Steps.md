# Next Steps Tracker

Last updated: 2025-10-15 (post-modularisation verification)

## Tasks

- [x] Modularise the CLI into dedicated submodules under `src/hephaestus/cli/`. _(Owner: Agent)_
  - [x] Extract release, cleanup, QA, refactor, and wheelhouse command groups into focused modules.
  - [x] Configure the lightweight `src/hephaestus/cli.py` entrypoint to register sub-apps and top-level commands.
- [x] Refresh test coverage and fixtures for the new CLI module layout. _(Owner: Agent)_
- [x] Update documentation references to the new CLI module structure. _(Owner: Agent)_
- [ ] Document pip-audit limitation (package absent on PyPI until publish). _(Owner: Agent)_

## Steps

- [x] Reviewed repository context (README, CONTRIBUTING, docs overview, CI workflows) to confirm guard-rail expectations and CLI ownership boundaries.
- [x] Established baseline guard-rails before modifications (tests, lint, type-check, build).
- [x] Created modular CLI package, migrated commands, and added documentation updates.
- [x] Updated and re-ran the CLI test suite plus static analysis.
- [x] Re-ran guard-rail commands after changes.
- [ ] Prepare PR summary with coverage impact and residual risks.

## Deliverables

- New modular CLI command implementations in `src/hephaestus/cli/{cleanup,qa,refactor,release,wheelhouse}.py`.
- Lightweight entrypoint `src/hephaestus/cli.py` that registers modular sub-apps and top-level commands.
- Updated CLI test suite (`tests/test_cli.py`) aligned with the new module imports.
- Documentation updates referencing the modular CLI structure (`docs/` and `docs-site/`).

## Quality Gates

- [x] `uv run --extra qa --extra dev pytest --cov=src` (pass: 404 passed, coverage 85.53%).【ed09cc†L1-L57】
- [x] `uv run --extra qa --extra dev ruff check .` (pass).【3b324e†L1-L3】
- [x] `uv run --extra qa --extra dev ruff format --check .` (pass, 82 files already formatted).【f49721†L1-L3】
- [x] `uv run --extra qa --extra dev mypy src tests` (pass).【77f9fe†L1-L3】
- [ ] `uv run --extra qa --extra dev pip-audit --strict --ignore-vuln GHSA-4xh5-x5gv-qwph` (fails: SSL certificate verification).【62ed77†L1-L36】
- [x] `uv build` (pass).【1d0e1c†L1-L4】

## Links

- `src/hephaestus/cli.py`
- `src/hephaestus/cli/cleanup.py`
- `src/hephaestus/cli/qa.py`
- `src/hephaestus/cli/refactor.py`
- `src/hephaestus/cli/release.py`
- `src/hephaestus/cli/wheelhouse.py`
- `tests/test_cli.py`
- `docs/explanation/architecture.md`
- `docs/explanation/frontier-red-team-gap-analysis.md`
- `docs-site/src/content/docs/explanation/architecture.md`
- `docs-site/src/content/docs/explanation/frontier-red-team-gap-analysis.md`
- `docs-site/src/content/docs/explanation/frontier-standards.md`
- `docs/explanation/frontier-standards.md`

## Risks/Notes

- pip-audit currently fails due to SSL certificate validation; flag the limitation in follow-up docs/PR notes.
- Ensure downstream automation and docs consumers pick up the new CLI module paths when importing commands.
- Repository uses `uv` tooling with Python 3.14 beta; guard-rail commands depend on this environment.
- Documentation and CLI schemas assume Typer-based command registration; future structural changes must preserve telemetry hooks and schema extraction compatibility.

## Assumptions & Unknowns

- CI mirrors the documented guard-rail suite; expect the same SSL limitation for `pip-audit` in this environment until CA trust is configured.
- No CODEOWNERS file detected; reviewer expectations should default to maintainers listed in `README.md` and `CONTRIBUTING.md` until confirmed otherwise.
- ADR and architecture documents under `docs/` and `docs-site/` describe plugin, telemetry, and docs migration context—no conflicting guidance identified, but confirm before expanding CLI scope.
