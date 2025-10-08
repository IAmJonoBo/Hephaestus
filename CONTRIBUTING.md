# Contributing to Hephaestus

Thanks for helping keep the toolkit evergreen! This guide captures the day-to-day workflow so you can
ship improvements with confidence.

## Prerequisites

- Python 3.12 or newer
- [`uv`](https://github.com/astral-sh/uv) for dependency management and isolated command execution
- GitHub account with access to fork the repository or create branches

Clone the repository and install the toolchain:

```bash
uv sync --extra dev --extra qa
uv run pre-commit install
```

## Branching & Commit Hygiene

- Create feature branches off `main` and keep them focused.
- Use descriptive commit messages that explain the change and its impact.
- Run the full guard rail suite before opening a pull request (see below).

## Common Workflows

Run the guard-rail tooling directly with `uv` so everything stays reproducible:

```bash
uv run hephaestus guard-rails                            # Full sweep (cleanup, lint, typecheck, tests, audit)
uv run ruff check .                                      # Lint
uv run ruff format .                                    # Auto-format
uv run mypy src tests                                   # Static typing
uv run pytest                                           # Unit tests with coverage
uv run hephaestus cleanup --deep-clean                  # Workspace hygiene
uv run pip-audit --strict --ignore-vuln GHSA-4xh5-x5gv-qwph  # Dependency audit
uv run mkdocs serve                                     # Docs live preview
uv run mkdocs build                                     # Docs static site build
```

## Pre-Commit Guard Rails

- Pre-commit hooks execute Ruff, Black, PyUpgrade, Mypy, Pip Audit, and the cleanup sweep on every
  commit and push.
- Use `uv run pre-commit run --all-files` to refresh the entire tree before shipping larger series.

## Quality Checklist

Before requesting review:

- Run `uv run hephaestus guard-rails` for a full sweep, or execute the individual steps below.

1. `uv run hephaestus cleanup --deep-clean`
2. `uv run ruff check .`
3. `uv run ruff format .`
4. `uv run mypy src tests`
5. `uv run pytest`
6. `uv run pip-audit --strict --ignore-vuln GHSA-4xh5-x5gv-qwph`
7. Confirm `uv run hephaestus plan` shows the change in the rollout timeline when applicable.

For releases, consult `docs/pre-release-checklist.md` for additional automation steps.

## Documentation

- The `docs/` folder follows a Diátaxis-inspired layout. Keep tutorials, how-to guides, reference,
  and explanations distinct.
- Update `docs/how-to/editor-setup.md` when onboarding instructions change, and surface major updates in
  `docs/lifecycle.md`.
- Use `uv run mkdocs serve` for live preview of the MkDocs Material site, or `uv run mkdocs build`
  to generate the static site.

## Testing Strategy

- Targeted unit tests live under `tests/`. Add regression coverage whenever behaviour changes.
- For refactoring automation, leverage scripts in `hephaestus-toolkit/refactoring/scripts/` and the
  characterization harnesses they provide.
- When adding new CLI commands, extend `tests/test_cli.py` to protect entry points.

## Release & Deployment Flow

- The GitHub Actions pipeline (`.github/workflows/ci.yml`) mirrors the local commands above.
- Version bumps in `pyproject.toml` trigger automated release tagging on `main` after passing CI.
- The deep-clean stage runs automatically during release workflows to keep artefacts pristine.

## Reporting Issues & Proposing Enhancements

- File issues with clear reproduction steps, affected commands, and the guard rails that caught the
  problem.
- For larger efforts, start an Architecture Decision Record in `docs/adr/` and link it from your
  pull request.

## Communication

- Use the `dx`, `quality`, and `automation` labels on GitHub issues to help triage.
- Share learnings by updating the lifecycle playbook and related docs when new practices emerge.

Thanks again for contributing—every improvement keeps the toolkit healthier for the next refactor!
