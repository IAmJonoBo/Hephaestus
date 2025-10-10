# Next Steps Tracker

Last updated: 2025-10-10 (Documentation refresh, gap analysis, release readiness)

## Current Status Summary
- ✅ Frontier feature set implemented: FastAPI + gRPC parity, streaming analytics ingestion, auto-remediation, Sigstore-gated releases, and plugin discovery resets.
- ✅ Quality gates enforced via CI (lint, type-check, tests with ≥85% coverage, drift detection, build verification).
- 🔄 Focus now shifts to production hardening: telemetry sampling/exporters, Sigstore backfill execution, API authentication, and marketplace ecosystem work.

## Tasks
- [ ] Execute Sigstore bundle backfill runbook and capture attestation inventory (Release Engineering – due 2025-11-01).
- [ ] Register PyPI publisher account and dry-run publication workflow (Release Engineering – due 2025-10-24).
- [ ] Implement OpenTelemetry sampling strategies and Prometheus exporter (Observability – due 2025-11-15).
- [ ] Add API authentication/authorization with service accounts and audit logging (API Team – due 2025-11-08).
- [ ] Design plugin marketplace metadata (discovery, dependency resolution, version pinning) (Ecosystem – due 2025-11-30).
- [ ] Ship streaming analytics retention policy and ingestion metrics surfaced via telemetry (Analytics – due 2025-11-22).
- [ ] Automate drift remediation playbooks for top CI failure signatures (QA – due 2025-11-12).

## Steps
- [ ] Finalise Sigstore backfill dry-run against staging artifacts, validate manifests, and document rollback.
- [ ] Draft API auth ADR covering token formats, RBAC, and secret storage requirements.
- [ ] Prototype OTEL span sampling knobs with CLI + API instrumentation smoke tests.
- [ ] Document ingestion retention/metrics plan and update analytics configuration schema.

## Deliverables
- 📄 Updated ADRs: 0002 (Marketplace), 0003 (Telemetry Sprint 4), 0004 (API Sprint 2+), 0005 (PyPI release), 0006 (Sigstore backfill execution).
- 📦 Release candidate with enforced Sigstore backfill, drift gate, and telemetry exporters enabled by default.
- 📊 Analytics observability dashboard (latency, acceptance rate, remediation outcomes).
- 🔐 Authenticated API deployment guide with operational runbooks.

## Quality Gates
- ✅ Test coverage ≥ 85% (current: 86.46%).
- ✅ Lint (ruff), type-check (mypy), build (uv build) must pass pre-merge.
- ⚠️ Pip-audit blocked by container SSL trust chain; mitigation tracked in Risks/Notes.
- 🔄 OTEL sampling + Prometheus exporter to add latency/error SLOs before general release.

## Links
- README overview refresh【F:README.md†L1-L120】
- Frontier red-team gap analysis (updated)【F:docs/explanation/frontier-red-team-gap-analysis.md†L1-L200】
- Sigstore & release automation code【F:src/hephaestus/release.py†L1-L200】
- API service parity tests【F:tests/test_api.py†L1-L200】

## Risks/Notes
- Pip-audit fails due to missing trust anchor in the container; rerun once trust store is patched or proxy provided.
- API lacks first-party auth; short-term mitigation relies on network isolation and short-lived tokens.
- Telemetry exporters absent; downstream observability limited to logs until sampling/export landed.
- Streaming ingestion stores snapshots in-memory; persistence is required before multi-tenant rollout.

## Gap Analysis Highlights
- **Telemetry:** Command spans exist but sampling/export strategies remain manual; need Prometheus + OTLP exporters.
- **Supply Chain:** Sigstore metadata ready but historical releases still require bundle backfill before GA.
- **API Security:** FastAPI service lacks auth/RBAC; gRPC lacks channel credentials; need consistent secret rotation story.
- **Analytics:** Streaming ingestion online yet retention + metrics missing; CLI/API should surface ingestion health and quotas.
- **Ecosystem:** Plugin discovery resets state but marketplace semantics (versioning, dependency resolution) remain unsolved.

## Red Team Observations
- Attack simulations confirm guard-rails fail closed when tooling missing, but API endpoints still trust inbound requests implicitly.
- Cleanup manifests deter destructive misuse; next escalation involves tampered Sigstore bundles—backfill execution and identity enforcement mitigate.
- Drift remediation automation needs rate limits and audit trails to prevent runaway fixes triggered by noisy signals.

## Baseline Validation (current session)
- ✅ `uv run --extra qa --extra dev pytest --cov=src` (345 passed, 4 skipped, 86.46% coverage)【2bb7ae†L1-L34】
- ✅ `uv run --extra qa --extra dev ruff check .`【34de62†L1-L2】
- ✅ `uv run --extra qa --extra dev mypy src tests`【06ed06†L1-L2】
- ⚠️ `uv run --extra qa --extra dev pip-audit` (fails: SSL certificate verification error against pypi.org)【e8840c†L1-L41】
- ✅ `uv build`【18f179†L1-L4】
