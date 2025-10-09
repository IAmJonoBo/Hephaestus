# Copilot Instructions

## Quick orientation

- Hephaestus is a Typer-based CLI plus refactoring toolkit; the main package lives in `src/hephaestus/`, while automation assets and configs sit under `hephaestus-toolkit/refactoring/`.
- CLI behaviour is exhaustively documented in `docs/reference/cli.md` and covered by `tests/test_cli.py`; use those fixtures when extending commands.
- Docs follow Diátaxis, with architecture context in `docs/explanation/architecture.md` and AI usage patterns in `docs/how-to/ai-agent-integration.md`.

## Architecture essentials

- `cli.py` centralises command wiring (`cleanup`, `guard-rails`, `tools`, `plan`, `release`, `schema`) and shares a single `rich.Console` for consistent tables/logs.
- `toolbox.py` and `schema.py` expose deterministic synthetic analytics so tests stay stable; introduce new data via `ToolkitSettings` models instead of ad-hoc dicts.
- `cleanup.py` wraps all filesystem operations with `CleanupOptions` guards (path normalisation, deny-list, audit callbacks). Reuse `run_cleanup` rather than shelling out.
- `release.py` handles wheelhouse downloads with retry/backoff, checksum + Sigstore verification, and cache management (`HEPHAESTUS_RELEASE_CACHE`).
- `telemetry.py` defines structured events used across commands; respect the schema when logging so guard-rail correlation IDs propagate.

## Workflow shortcuts

- Bootstrap with UV: `uv sync --extra dev --extra qa`, then always run commands through `uv run hephaestus …` to pick up the managed env.
- `uv run hephaestus guard-rails` performs the entire quality pipeline (cleanup → ruff check → ruff isort → ruff format → mypy on `src` + `tests` → pytest with ≥85% coverage → `pip-audit --strict --ignore-vuln GHSA-4xh5-x5gv-qwph`).
- For focused checks, use the same tooling individually: `uv run ruff check .`, `uv run ruff check --select I --fix .`, `uv run ruff format .`, `uv run mypy src tests`, `uv run pytest`, `uv run pip-audit --strict`.
- Build docs via `uv run mkdocs serve` and keep navigation wired in `mkdocs.yml`.
- Analytics demos live in `tests/test_analytics.py`; mirror those patterns when adding ranking strategies or schema fields.

## Implementation patterns

- Prefer Typer command functions that return `int | None` and print via the shared console; table layouts in `cli.py` show the expected Rich API usage.
- Tests rely on `typer.testing.CliRunner` and patching utilities (see `tests/test_guard_rails_runs_expected_commands`); keep command ordering stable or update assertions.
- Synthetic datasets come from `toolbox.py`; extend via Pydantic models and update `tests/test_toolbox.py` to keep determinism.
- Drift detection is orchestrated in `drift.py` and surfaced through `guard-rails --drift`; reuse helpers instead of invoking subprocesses directly.
- Release automation expects SHA and Sigstore checks through `ReleaseVerifier`; raise `ReleaseError` for all user-facing failures.

## Safety rails & pitfalls

- Never skip `CleanupOptions.normalize`; it prevents wiping virtualenvs or system paths. Out-of-root targets require explicit confirmation.
- `guard-rails` already embeds a cleanup step—avoid nesting manual cleanup calls to prevent duplicate prompts and log spam.
- Wheelhouse installers assume HTTPS URLs only; tests enforce this via `tests/test_release.py`.
- Coverage artefacts must land in `coverage.xml`; CI and the guard-rails command read that file directly.

## Quick references

- Quality gates + troubleshooting: `docs/how-to/quality-gates.md`, `docs/how-to/troubleshooting.md`.
- Refactoring playbooks and default knobs: `hephaestus-toolkit/refactoring/docs/`, `hephaestus-toolkit/refactoring/config/refactor.config.yaml`.
- Ops automation touchpoints: `.github/workflows/`, `ops/turborepo-release.json`, and `scripts/validate_quality_gates.py`.
