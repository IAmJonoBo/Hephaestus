# Hephaestus Developer Toolkit

Hephaestus is a standalone developer experience toolkit extracted from the spirit of the Chiron codebase but maintained independently. It helps engineering teams prioritise, automate, and safely deliver large scale refactoring and quality improvements. Think of it as Chiron's sister project that focuses entirely on developer productivity.

## Features

- Quality-suite orchestration with configurable gates and monitoring
- Coverage analytics (hotspots, gaps, guard rails, focus views)
- Lifecycle-aware CLI workflows (hotspot ranking, opportunity scouting, QA profiles, rollout plans)
- Evidence-based refactoring workflows (hotspot analysis, opportunity scans)
- Safe automation helpers (LibCST codemods, characterization test scaffolds)
- Pre-commit guardrails (Ruff, Black, PyUpgrade, Mypy, Pip Audit)
- Documentation synchronisation utilities for Diátaxis style guides
- Portable scripts and CI fragments for churn analysis and rollout planning

## Getting Started

```bash
uv sync --extra dev --extra qa
uv run hephaestus --help
uv run hephaestus tools refactor hotspots --limit 10
uv run hephaestus tools qa --profile quick --dry-run
uv run hephaestus tools qa coverage
uv run hephaestus plan
uv run pre-commit install
uv run pre-commit run --all-files
```

### CLI Workflows

Use the Typer-based CLI to move quickly from discovery to delivery:

- `tools refactor hotspots`: surfaces the highest-churn modules, respecting toolkit configuration overrides.
- `tools refactor opportunities`: summarises advisory refactors with qualitative effort signals to aid prioritisation.
- `tools qa profile <name>`: inspects guard-rail thresholds and rollout toggles for an individual QA profile.
- `tools qa coverage`: highlights uncovered lines and risk scores tuned to your coverage goals.
- `plan`: renders a rich execution plan so teams can visualise orchestration progress during a rollout.

### Automation & CI

- Continuous integration runs on GitHub Actions (`CI` workflow) for pushes to `main` and pull requests, exercising the pytest suite against Python 3.12 and 3.13.
- Linting and typing (Ruff + Mypy) run on every matrix job, with coverage published as artefacts and failing below 85%.
- Automated release tagging (`Automated Release Tagging` workflow) cuts a `v*` tag and GitHub Release whenever the version in `pyproject.toml` advances on `main`.
- The repository ships with `cleanup-macos-cruft.sh` for scrubbing macOS metadata, caches, and build artefacts; run it with `--deep-clean` before creating archives or syncing workspaces.
- A scheduled TurboRepo monitor (`TurboRepo Release Monitor` workflow) compares the pinned version in `ops/turborepo-release.json` with upstream releases and opens an issue if an update is available.
- Weekly Dependabot scans cover Python packages and GitHub Actions while the CI pipeline executes `pip-audit --strict` on Python 3.13.

### Development-to-Deployment Flow

| Stage                  | Tooling                                                                                                                  | Purpose                                                                                    |
| ---------------------- | ------------------------------------------------------------------------------------------------------------------------ | ------------------------------------------------------------------------------------------ |
| Discovery & planning   | `docs/lifecycle.md`, `docs/adr/`, `plan` command                                                                         | Capture intent, align stakeholders, and visualise rollouts.                                |
| Local analytics        | `tools refactor hotspots`, `tools refactor opportunities`                                                                | Identify high-value refactor targets with churn and qualitative signals.                   |
| Quality gates          | `tools qa profile`, `tools qa coverage`, `pyproject.toml` thresholds                                                     | Inspect guard rails, coverage gaps, and tighten criteria before shipping changes.          |
| Automation             | `hephaestus-toolkit/refactoring/scripts/`                                                                                | Execute codemods, hotspot scans, and characterization harnesses with reproducible scripts. |
| Developer guard rails  | `.pre-commit-config.yaml`, Ruff, Black, PyUpgrade, Mypy, Pip Audit                                                       | Keep code style, types, and security evergreen before commits land.                        |
| Continuous integration | `.github/workflows/ci.yml`, `tests/test_cli.py`                                                                          | Enforce linting, typing, coverage, and pytest during PRs with artefact uploads.            |
| Release & monitoring   | `.github/workflows/release-tag.yml`, `.github/workflows/turborepo-monitor.yml`, `ops/turborepo-release.json`, Dependabot | Cut releases automatically and track upstream updates while nudging dependency hygiene.    |
| Post-release hygiene   | `cleanup-macos-cruft.sh`                                                                                                 | Keep workspaces clean before packaging or mirroring artefacts.                             |

### Project Layout

```text
hephaestus/
├── pyproject.toml                           # Project metadata and dependencies
├── README.md                                # This overview
├── LICENSE                                  # MIT licence
├── src/hephaestus/                          # Python package
│   ├── __init__.py                          # Version metadata
│   ├── cli.py                               # Typer-based CLI entry point
│   ├── planning.py                          # Execution plan rendering helpers
│   └── toolbox.py                           # Quality, coverage, and refactor APIs
├── hephaestus-toolkit/                      # Standalone scripts and configs
│   └── refactoring/
│       ├── config/                          # Default configuration
│       ├── docs/                            # Playbooks and implementation notes
│       ├── scripts/                         # Analysis, codemods, verification helpers
│       └── ci/                              # Workflow fragment for pipelines
└── tests/                                   # Pytest suites (see below)
```

## Configuration

Hephaestus reads defaults from `[tool.hephaestus.toolkit]` in `pyproject.toml`. Use the bundled configuration at `hephaestus-toolkit/refactoring/config/refactor.config.yaml` as a reference and tailor thresholds, directory mappings, and rollout policies to match your repository layout.

## CI Integration

- `hephaestus-toolkit/refactoring/ci/workflow.partial.yml` provides a baseline GitHub Actions job.
- Upload churn and hotspot artefacts to keep stakeholders informed.
- Run the codemod and verification scripts in advisory mode before enabling blocking gates.

## Documentation

- `docs/lifecycle.md` — Evergreen lifecycle playbook that ties tooling to each development stage.
- `docs/adr/` — Architecture Decision Records for capturing context and choices.
- `hephaestus-toolkit/refactoring/docs/` — Playbooks and implementation notes specific to the refactoring toolkit.

## Contributing

1. Fork the repository that hosts Hephaestus.
2. Enable a fresh Python 3.12+ virtual environment (`uv` or `venv`).
3. Run `uv run pytest` to execute the test suite.
4. Open a pull request with clear before/after context and updated documentation.

Hephaestus embraces incremental, evidence-based change. Use the provided tools to gather metrics, add characterization tests, and stage refactors safely.
