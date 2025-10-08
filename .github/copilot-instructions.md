# Copilot Instructions

## Project snapshot

- Hephaestus is a Typer CLI and toolkit in `src/hephaestus/` that orchestrates cleanup, QA, refactoring analytics, and release automation for other repos.
- The CLI mirrors docs in `docs/reference/cli.md`; tests in `tests/test_cli.py` demonstrate the expected command outputs and exit codes.
- The refactoring toolkit lives under `hephaestus-toolkit/refactoring/` with default config at `config/refactor.config.yaml` consumed by `toolbox.load_settings`.

## Core modules & patterns

- `cli.py` wires subcommands (`cleanup`, `plan`, `tools`, `release`, `guard-rails`) and always prints through a shared `rich.Console`; new commands should follow the table-driven outputs used in existing handlers.
- `toolbox.py` returns deterministic synthetic data so commands stay predictable; extend via Pydantic `ToolkitSettings` models rather than ad-hoc dicts.
- `cleanup.py` is defensive: it normalises options, forbids dangerous roots (/, $HOME), and logs removals via callbacks; reuse `CleanupOptions` + `run_cleanup` instead of shelling out.
- `release.py` speaks directly to the GitHub REST API with retry/backoff; prefer its helpers over requests-based code and respect the `DEFAULT_*` constants/env overrides.

## Local workflows

- Use UV for everything: `uv sync --extra dev --extra qa` installs tooling, and `uv run hephaestus …` executes the CLI to guarantee the right interpreter.
- `uv run hephaestus guard-rails` is the fastest parity check—it deep-cleans then runs Ruff check/format, Mypy (`src` + `tests`), Pytest, and `pip-audit --strict --ignore-vuln GHSA-4xh5-x5gv-qwph`.
- Individual quality steps match CI expectations: `uv run ruff check .`, `uv run ruff format .`, `uv run mypy src tests`, `uv run pytest`, `uv run pip-audit --strict`.
- Docs are built via MkDocs Material: `uv run mkdocs serve` for local preview, with Diátaxis structure mirrored in `docs/`.

## Testing & diagnostics

- Pytest is configured in `pyproject.toml` with coverage fail-under 85% and warnings treated as errors (`filterwarnings = error`); always run through `uv run pytest`.
- CLI tests rely on `typer.testing.CliRunner`; mimic that pattern when adding commands to keep output assertions readable.
- Coverage reports land in `coverage.xml`; the guard-rails pipeline and CI expect it for artefacts.

## Release & distribution

- `release install` downloads the prebuilt wheelhouse from GitHub Releases; respect options like `--repository`, `--asset-pattern`, and `--remove-archive` when scripting automated installs.
- Wheelhouse caching defaults to `~/.cache/hephaestus/wheelhouses` (macOS `~/Library/Caches`); override via `HEPHAESTUS_RELEASE_CACHE`.
- All network calls enforce HTTPS and retry limits—surface errors via `ReleaseError` instead of bare exceptions.

## Safety checks & gotchas

- Never bypass `CleanupOptions.normalize`; it guards against wiping virtualenv `site-packages` and refuses high-risk paths.
- `guard-rails` re-invokes `cleanup` internally; avoid calling it inside other cleanup contexts to prevent nested user prompts/log spam.
- When tests patch subprocesses (see `tests/test_guard_rails_runs_expected_commands`), assert commands exactly—order changes break expectations.
- Synthetic analytics live in `toolbox.py`; if you need realistic data, add hooks behind new model fields so existing tests stay deterministic.

## Handy references

- Architecture overview: `docs/explanation/architecture.md` for component boundaries and flows.
- Lifecycle guidance: `docs/lifecycle.md` and `docs/pre-release-checklist.md` capture rollout cadence and final checks.
- Refactoring playbooks: `hephaestus-toolkit/refactoring/docs/` for codemod strategy templates.
- Ops note: `ops/turborepo-release.json` is monitored by the scheduled TurboRepo workflow—adjust it alongside any release automation changes.
