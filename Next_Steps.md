# Next Steps Tracker

Last updated: 2025-10-13 (Service auth gating restored + guard-rail suite green locally)

## Tasks

- [ ] Restore guard-rail baselines for release pipeline work (tests, lint, typecheck, security scan) _(Owner: Agent, Due: 2025-10-13)_
  - [x] Address API service principal argument regressions blocking pytest. _(Owner: Agent)_
  - [x] Reformat `tests/test_plugins_marketplace.py` per Ruff. _(Owner: Agent)_
  - [x] Resolve lint/type failures triggered by new auth signature expectations. _(Owner: Agent)_
  - [ ] Document pip-audit limitation (package absent on PyPI until publish). _(Owner: Agent)_
- [ ] Implement PyPI/Test PyPI publication automation per ADR-0005. _(Owner: Agent, Due: 2025-10-14)_
  - [x] Extend `hephaestus release install` to support PyPI/Test PyPI sources. _(Owner: Agent)_
  - [x] Add smoke test harness for Test PyPI installs (env-gated). _(Owner: Agent)_
  - [x] Update `.github/workflows/publish-pypi.yml` with Trusted Publisher slug + smoke verification. _(Owner: Agent)_
  - [x] Refresh ADR-0005 + README install docs with publisher + 2FA details. _(Owner: Agent)_
  - [ ] Capture workflow log references once GitHub run completes (post-environment). _(Owner: Agent)_
- [ ] Register `hephaestus-toolkit` on PyPI/Test PyPI, enable 2FA, and approve Trusted Publisher (`pypi:project/hephaestus-toolkit`). _(Owner: Maintainer, Blocked: requires PyPI org access)_

## Steps

- [x] Draft unit tests covering `release install --source {github,pypi,test-pypi}` and PyPI installer helpers before implementation.
- [x] Implement CLI + `release` module changes to satisfy new tests.
- [x] Author Test PyPI smoke script (pytest gated + standalone entrypoint) and wire into workflow.
- [x] Update docs/ADR + README to document publisher configuration, 2FA, and install flows.
- [x] Validate guard-rail tooling locally (pytest, Ruff, mypy) after auth hardening; prerelease tag execution still pending external access.
- [ ] Record GitHub Actions log links + Test PyPI artifact references post-run.

## Deliverables

- Updated `docs/adr/0005-pypi-publication.md` reflecting Trusted Publisher + 2FA posture.
- Hardened `.github/workflows/publish-pypi.yml` with Test PyPI smoke verification + Sigstore bundle upload.
- Extended CLI/`release` module supporting PyPI/Test PyPI installs.
- Test harness (`tests/smoke/test_testpypi_install.py`) gating real Test PyPI installs behind env var.
- README/docs refresh covering PyPI installation and verification steps.

## Quality Gates

- [x] `uv run --extra qa --extra dev pytest --cov=src` (pass: 400 passed, coverage 85.30%).【7dee58†L1-L61】
- [x] `uv run --extra qa --extra dev ruff check .` (pass).【78ed7a†L1-L2】
- [x] `uv run --extra qa --extra dev ruff format --check .` (pass).【53663b†L1-L2】
- [x] `uv run --extra qa --extra dev mypy src tests` (pass).【283f4e†L1-L2】
- [ ] `uv run --extra qa --extra dev pip-audit --strict --ignore-vuln GHSA-4xh5-x5gv-qwph` (fails: package not yet on PyPI).【85d439†L1-L2】
- [x] `uv build` (pass).【78c9c0†L1-L3】

## Links

- `.github/workflows/publish-pypi.yml`
- `docs/adr/0005-pypi-publication.md`
- `README.md`
- `src/hephaestus/cli.py`
- `src/hephaestus/release.py`
- `tests/test_release.py`
- `tests/smoke/test_testpypi_install.py` _(planned)_

## Risks/Notes

- Guard-rail suite now passes locally (tests/coverage/lint/type); ensure future changes maintain ≥85% coverage before tagging releases.
- PyPI registration + 2FA require external maintainer action; document completion steps once access is available.
- pip-audit will fail until package exists on PyPI/Test PyPI; treat as expected until first publish.
- Test PyPI smoke test requires network + credentials; gate via env var to avoid local CI failures.
- Sigstore attestation tooling must remain consistent with ADR-0006; ensure workflow retains tarball uploads.
