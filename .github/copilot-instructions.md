# Copilot Instructions

## Quick Orientation

- Hephaestus is a Typer CLI plus automation runtime; core code lives in `src/hephaestus/`, packaged tooling and configs under `hephaestus-toolkit/refactoring/`.
- CLI contracts are documented in `docs/reference/cli.md` and mirrored by `tests/test_cli.py`; use them to understand required flags and console layout.
- Remote surfaces (FastAPI + gRPC) reuse the same orchestration layer in `src/hephaestus/api/service.py`, so CLI and services stay behaviourally identical.
- Diátaxis docs highlight domain context (`docs/explanation/architecture.md`) and AI playbooks (`docs/how-to/ai-agent-integration.md`).

## Architecture Map

- `cli.py` wires commands (`cleanup`, `guard-rails`, `tools`, `plan`, `release`, `schema`) and shares one `rich.Console`; follow the existing Typer patterns when adding commands.
- `guard-rails` execution funnels through `api/service.py` to evaluate cleanup, plugin gates, drift checks, and optional remediation; replicate that flow instead of inlining logic.
- Analytics ranking lives in `analytics.py` with deterministic fixtures from `toolbox.py`; streaming ingestion for APIs is handled by `analytics_streaming.py`'s thread-safe buffer.
- Plugins are discovered via the registry in `plugins/__init__.py` and surfaced through the guard-rails gate evaluation; keep metadata accurate so missing tooling is reported.
- Release automation (`release.py`) combines wheelhouse downloads, Sigstore verification, and cache management via `ReleaseVerifier` and env var `HEPHAESTUS_RELEASE_CACHE`.

## Workflow Essentials

- Sync the dev environment with `uv sync --extra dev --extra qa --extra grpc`; prefer `uv run hephaestus …` to inherit the managed interpreter.
- The happy path quality sweep is `uv run hephaestus guard-rails`, which chains cleanup → ruff lint/isort/format → mypy (`src` + `tests`) → pytest (≥85% coverage) → `pip-audit --strict --ignore-vuln GHSA-4xh5-x5gv-qwph`.
- Targeted checks use the same tooling individually: `uv run ruff check .`, `uv run ruff check --select I --fix .`, `uv run ruff format .`, `uv run mypy src tests`, `uv run pytest`, `uv run pip-audit --strict`.
- Docs are built with `uv run mkdocs serve`; keep navigation synced in `mkdocs.yml` before publishing.
- Mac-specific cleanup scripts (`cleanup-macos-cruft.sh`, `docs/how-to/troubleshooting.md`) handle resource forks—lean on them instead of reimplementing.

## Patterns & Conventions

- Command functions return `int | None`, log via the shared console, and delegate work to module helpers (`command_helpers.py` for subprocess payloads, `cleanup.run_cleanup` for filesystem ops).
- `CleanupOptions.normalize` is mandatory; it guards against accidental deletions and ships audit manifests when configured.
- Telemetry integrations sit in `telemetry/metrics.py` and `telemetry/tracing.py`; route events through `telemetry.emit_event` and the shared registry to preserve correlation IDs and no-op fallbacks.
- Analytics and schema data derive from Pydantic models in `schema.py` and `toolbox.py`; extend models before injecting new dict literals so tests remain deterministic.
- Drift detection (`drift.py`) and remediation surfaces share helpers exposed through `api/service.py`; reuse them for consistency across CLI and API flows.

## Testing Touchpoints

- CLI behaviour is asserted with `typer.testing.CliRunner` fixtures in `tests/test_cli.py`; preserve command ordering or update expectations.
- `tests/test_api_service.py` and `tests/test_api.py` ensure REST/gRPC parity and cover streaming ingestion—update both when changing orchestration.
- Analytics ranking tweaks must update `tests/test_analytics.py` plus any schema exports in `tests/test_schema.py` to keep deterministic outputs.
- Release hardening is covered by `tests/test_release.py`; maintain HTTPS-only downloads, checksum enforcement, and Sigstore bundle verification.
- Toolbox data or fixtures need mirrored assertions in `tests/test_toolbox.py` alongside any updates in `tests/conftest.py`.

## Reference Hints

- Quality gate guides live in `docs/how-to/quality-gates.md`; troubleshooting tips in `docs/how-to/troubleshooting.md`.
- Refactoring playbooks: `hephaestus-toolkit/refactoring/docs/` and default knobs in `hephaestus-toolkit/refactoring/config/refactor.config.yaml`.
- Observability setup and OpenTelemetry toggles reside in `docs/adr/0003-opentelemetry-integration.md` and code under `telemetry/`.
- Ops automation touchpoints: `.github/workflows/`, `scripts/validate_quality_gates.py`, and `ops/turborepo-release.json` for release orchestration.
