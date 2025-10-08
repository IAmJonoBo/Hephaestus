# Architecture Overview

Hephaestus packages a set of CLI workflows, automation helpers, and refactoring scripts that can be
adopted project by project. The repository is organised to reflect the separation between the
Python package (distributed as wheels) and the supporting toolkit assets.

## High-Level Components

| Component                         | Purpose                                                                                |
| --------------------------------- | -------------------------------------------------------------------------------------- |
| `src/hephaestus/`                 | Python package containing the Typer CLI, release helpers, planning utilities, and API. |
| `hephaestus-toolkit/refactoring/` | Scripts, configuration, and docs for advisory refactoring workflows.                   |
| `.github/workflows/`              | CI and release automation, including the Build Wheelhouse pipeline.                    |
| `docs/`                           | Diátaxis-aligned documentation published via MkDocs.                                   |
| `tests/`                          | Pytest suite covering CLI behaviours, release helpers, planning logic, and cleanup.    |

## Package Layout

The `src/hephaestus/` directory is structured as a standard Python package:

- `cli.py`: Typer entrypoint exposing `cleanup`, `plan`, `tools`, and `release` commands.
- `cleanup.py`: Workspace hygiene engine used by both the CLI and automation scripts.
- `release.py`: Functions for downloading, validating, and installing wheelhouse archives.
- `planning.py`: Utilities that build execution plans for refactoring rollouts.
- `toolbox.py`: Data models and helper functions consumed by CLI subcommands and scripts.
- `events.py`: Telemetry event definitions for structured logging.
- `backfill.py`: Sigstore backfill metadata schema for historical releases (ADR-0006).

### New Modules (Phase 1 Implementations)

- `telemetry/`: OpenTelemetry integration for optional distributed tracing (ADR-0003).
- `plugins/`: Plugin architecture for extensible quality gates (ADR-0002).
- `api/`: REST/gRPC API module structure for remote invocation (ADR-0004).

All CLI commands run through the same console abstraction (`rich.Console`) to ensure consistent
colourised output across shells and CI environments.

## Distribution Artefacts

The release workflow produces a wheelhouse archive consisting of:

- Wheels and source distributions built with `uv build`
- A manifest recording the version and build metadata

These artefacts live outside the repository (as GitHub Release assets) but follow a predictable
naming convention (`*wheelhouse*.tar.gz`). Consumers install them with `hephaestus release install`
without needing PyPI access.

## Runtime Dependencies

- Python 3.12+
- `typer`, `rich`, and `pytest` for CLI and testing
- Standard library networking modules for release downloads
- `uv` for reproducible environments and pip interoperability

The project intentionally avoids heavyweight dependencies so the wheelhouse can execute on GitHub
Actions runners, Codespaces, and developer laptops without extra packaging steps.

## Directory Hygiene

- Generated build artefacts (e.g., `dist/`, `build/`, coverage data) are ignored via `.gitignore`.
- The `cleanup-macos-cruft.sh` script ensures macOS metadata (`.DS_Store`, etc.) do not enter
  history.
- `uv run hephaestus cleanup` is wired into pre-commit and CI workflows to keep working trees clean
  before packaging or releasing.

## Extensibility

- Add new CLI commands by extending `src/hephaestus/cli.py` and corresponding modules.
- Create custom quality gate plugins using the `QualityGatePlugin` interface (see [Plugin Development Guide](../how-to/plugin-development.md)).
- Enable optional OpenTelemetry tracing via environment variables (see [Observability Guide](../how-to/observability.md)).
- Provide additional how-to guides under `docs/how-to/` and link them via `mkdocs.yml`.
- Customise the refactoring toolkit by editing `hephaestus-toolkit/refactoring/config/refactor.config.yaml`.

For a quick visual summary of the repository, refer to the "Project Layout" section in the
`README.md`.
