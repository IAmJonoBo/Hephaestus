# Contributing to Hephaestus

Thanks for helping keep the toolkit evergreen! This guide captures the day-to-day workflow so you can
ship improvements with confidence.

## Prerequisites

- Python 3.12 or newer
- [`uv`](https://github.com/astral-sh/uv) for dependency management and isolated command execution
- GitHub account with access to fork the repository or create branches

Clone the repository and install the toolchain:

```bash
# Automated setup (recommended, especially on macOS)
./scripts/setup-dev-env.sh

# Or manual setup
uv sync --extra dev --extra qa --extra grpc
uv run pre-commit install
```

**macOS users**: The automated setup script handles resource fork cleanup and UV configuration automatically. If you encounter installation issues, see [troubleshooting guide](docs/how-to/troubleshooting.md#macos-appledoubleresource-fork-installation-errors).

## Branching & Commit Hygiene

- Create feature branches off `main` and keep them focused.
- Use descriptive commit messages that explain the change and its impact.
- Run the full guard rail suite before opening a pull request (see below).

## Common Workflows

Run the guard-rail tooling directly with `uv` so everything stays reproducible:

```bash
uv run hephaestus guard-rails                            # Full sweep (cleanup, lint, typecheck, tests, audit)
uv run ruff check .                                      # Lint
uv run ruff check --select I --fix .                    # Auto-sort imports (ruff isort)
uv run ruff format .                                    # Auto-format
uv run yamllint -c .trunk/configs/.yamllint.yaml .github/ .pre-commit-config.yaml hephaestus-toolkit/  # YAML lint
uv run mypy src tests                                   # Static typing
uv run pytest                                           # Unit tests with coverage
uv run hephaestus cleanup --deep-clean                  # Workspace hygiene
uv run pip-audit --strict --ignore-vuln GHSA-4xh5-x5gv-qwph  # Dependency audit
cd docs-site && npm run dev                             # Docs live preview (Astro Starlight)
cd docs-site && npm run build                           # Docs static site build
```

## Pre-Commit Guard Rails

- Pre-commit hooks execute Ruff (linting, formatting, and import sorting), Black, PyUpgrade, Mypy, YAML Lint, Pip Audit, and the cleanup sweep on every
  commit and push.
- Use `uv run pre-commit run --all-files` to refresh the entire tree before shipping larger series.

## Quality Checklist

Before requesting review:

- Run `uv run hephaestus guard-rails` for a full sweep, or execute the individual steps below.

1. `uv run hephaestus cleanup --deep-clean`
2. `uv run ruff check .`
3. `uv run ruff check --select I --fix .`
4. `uv run ruff format .`
5. `uv run yamllint -c .trunk/configs/.yamllint.yaml .github/ .pre-commit-config.yaml mkdocs.yml hephaestus-toolkit/`
6. `uv run mypy src tests`
7. `uv run pytest`
8. `uv run pip-audit --strict --ignore-vuln GHSA-4xh5-x5gv-qwph`
9. Confirm `uv run hephaestus plan` shows the change in the rollout timeline when applicable.

For releases, consult `docs/pre-release-checklist.md` for additional automation steps.

## Documentation

- The `docs-site/` folder contains the Astro Starlight documentation site with automated content generation.
- Source markdown files follow a Diátaxis-inspired layout: tutorials, how-to guides, reference, and explanations.
- Documentation is automatically updated with CLI references, API docs, changelog, and version information.
- **Local development:**

  ```bash
  cd docs-site
  npm install          # First time only
  npm run dev          # Live preview at http://localhost:4321
  npm run build        # Production build
  ```

- **Automation scripts** (run automatically in CI, but can be run manually):

  ```bash
  npm run update-all   # Update CLI reference, API docs, changelog, versions
  npm run validate-all # Validate links, examples, detect stale content
  ```

- When adding new documentation, place files in `docs-site/src/content/docs/` following the Diátaxis structure.
- The legacy `docs/` folder content has been migrated; new docs should go in `docs-site/`.
- See [ADR 0007](docs-site/src/content/docs/adr/0007-astro-starlight-migration.md) for migration details.

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
