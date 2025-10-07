# Contributing to Hephaestus

Thanks for helping keep the toolkit evergreen! This guide captures the day-to-day workflow so you can
ship improvements with confidence.

## Prerequisites

- Python 3.12 or newer
- [`uv`](https://github.com/astral-sh/uv) for dependency management and command aliases
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

## Command Shortcuts

The project defines `uv` scripts for common workflows:

```bash
uv run lint           # Ruff lint checks
uv run format         # Ruff formatter
uv run typecheck      # Mypy strict mode across src/ and tests/
uv run test           # Pytest with coverage gating
uv run cleanup        # Workspace deep-clean
uv run audit          # pip-audit with the current suppression list
uv run docs-serve     # MkDocs local preview (see Documentation)
uv run docs-build     # MkDocs static site build
```

## Pre-Commit Guard Rails

- Pre-commit hooks execute Ruff, Black, PyUpgrade, Mypy, Pip Audit, and the cleanup sweep on every
  commit and push.
- Use `uv run pre-commit run --all-files` to refresh the entire tree before shipping larger series.

## Quality Checklist

Before requesting review:

1. `uv run cleanup`
2. `uv run lint`
3. `uv run format`
4. `uv run typecheck`
5. `uv run test`
6. `uv run audit`
7. Confirm `uv run hephaestus plan` shows the change in the rollout timeline when applicable.

For releases, consult `docs/pre-release-checklist.md` for additional automation steps.

## Documentation

- The `docs/` folder follows a Diátaxis-inspired layout. Keep tutorials, how-to guides, reference,
  and explanations distinct.
- Update `docs/editor-setup.md` when onboarding instructions change, and surface major updates in
  `docs/lifecycle.md`.
- Use `uv run docs-serve` while working on MkDocs content (once the site is bootstrapped).

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
