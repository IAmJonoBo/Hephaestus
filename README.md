# Hephaestus Developer Toolkit

Hephaestus is a standalone developer experience toolkit extracted from the spirit of the Chiron codebase but maintained independently. It helps engineering teams prioritise, automate, and safely deliver large scale refactoring and quality improvements. Think of it as Chiron's sister project that focuses entirely on developer productivity.

## Features

- Quality-suite orchestration with configurable gates and monitoring
- Coverage analytics (hotspots, gaps, guard rails, focus views)
- Lifecycle-aware CLI workflows (hotspot ranking, opportunity scouting, QA profiles, rollout plans)
- Evidence-based refactoring workflows (hotspot analysis, opportunity scans)
- Pluggable analytics ingestion for churn, coverage, and embedding signals powering hotspot ranking
- Safe automation helpers (LibCST codemods, characterization test scaffolds)
- Workspace cleanup orchestrator to remove macOS cruft, caches, and build artefacts with lifecycle automation
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
uv run hephaestus cleanup --deep-clean
uv run hephaestus guard-rails
uv run hephaestus release install --help
uv run pre-commit install
uv run pre-commit run --all-files
```

Prefer a ready-to-use workspace? Open the repository in GitHub Codespaces or VS Code with Dev
Containers—`.devcontainer/devcontainer.json` installs UV, syncs dependencies, and wires pre-commit
hooks automatically.

### CLI Workflows

Use the Typer-based CLI to move quickly from discovery to delivery:

- `tools refactor hotspots`: surfaces the highest-churn modules, respecting toolkit configuration overrides.
- `tools refactor opportunities`: summarises advisory refactors with qualitative effort signals to aid prioritisation.
- `tools qa profile <name>`: inspects guard-rail thresholds and rollout toggles for an individual QA profile.
- `tools qa coverage`: highlights uncovered lines and risk scores tuned to your coverage goals.
- `release install`: downloads the latest (or specified) wheelhouse from GitHub Releases, verifies SHA-256 manifests, validates Sigstore attestation bundles when published (with `--require-sigstore`, `--sigstore-identity`, and `--sigstore-pattern` controls), installs the bundled wheels, and optionally cleans up caches when you're integrating Hephaestus into another repository.
- `cleanup`: scrubs macOS cruft and optional caches/build artefacts from the workspace with mandatory dry-run previews, typed confirmations for outside-root targets, and JSON audit manifests (also available via `./cleanup-macos-cruft.sh`).
- `guard-rails`: runs the full quality and security pipeline (cleanup, lint, format, type check, test, audit) in one command. Use `--no-format` to skip auto-formatting.
- `plan`: renders a rich execution plan so teams can visualise orchestration progress during a rollout.

All commands honour the global logging switches: `--log-format` toggles between human-friendly text and machine-readable JSON, `--log-level` adjusts verbosity, and `--run-id` stamps every log event with a correlation identifier for distributed tracing.
Events now follow the structured schema defined in `hephaestus.telemetry`, and each CLI invocation binds an operation identifier so downstream systems can correlate release, cleanup, and guard-rail activity.

#### Shell Completions

Install Typer-provided autocompletions once per shell to explore commands quickly:

```bash
uv run hephaestus --install-completion
```

See `docs/cli-completions.md` for manual installation steps and regeneration tips.

### Automation & CI

- Pre-commit hooks trigger `uv run hephaestus cleanup` on commits and pushes so macOS metadata never enters history.
- Continuous integration runs on GitHub Actions (`CI` workflow) for pushes to `main` and pull requests, exercising the pytest suite against Python 3.12 and 3.13.
- Linting and typing (Ruff + Mypy) run on every matrix job, with coverage published as artefacts and failing below 85%; each job performs a cleanup sweep immediately after dependency syncing.
- The `uv run hephaestus guard-rails` command executes the local cleanup, lint, format, typing, testing, and audit pipeline sequentially for quick validation.
- Automated release tagging (`Automated Release Tagging` workflow) cuts a `v*` tag and GitHub Release whenever the version in `pyproject.toml` advances on `main`, and performs a deep-clean sweep before tagging.
- Release wheelhouse packaging (`Build Wheelhouse` workflow) zips the built wheels and sdists for each release, uploads them as workflow artefacts, and attaches the bundle to the GitHub Release for easy download while PyPI access is pending.
- The `hephaestus release install` command fetches the latest (or a specified) wheelhouse archive from GitHub Releases, verifies checksums and Sigstore attestations by default, and installs the wheels into the current environment, making consumption trivial from any repo.
- The repository ships with the `cleanup` CLI command and `cleanup-macos-cruft.sh` wrapper for scrubbing macOS metadata, caches, and build artefacts; use them directly for ad-hoc housekeeping or leverage the built-in lifecycle automation.
- A scheduled TurboRepo monitor (`TurboRepo Release Monitor` workflow) compares the pinned version in `ops/turborepo-release.json` with upstream releases and opens an issue if an update is available.
- Weekly Dependabot scans cover Python packages and GitHub Actions while the CI pipeline executes `pip-audit --strict` on Python 3.13.

### Development-to-Deployment Flow

| Stage                  | Tooling                                                                                                                  | Purpose                                                                                              |
| ---------------------- | ------------------------------------------------------------------------------------------------------------------------ | ---------------------------------------------------------------------------------------------------- |
| Discovery & planning   | `docs/lifecycle.md`, `docs/adr/`, `plan` command                                                                         | Capture intent, align stakeholders, and visualise rollouts.                                          |
| Local analytics        | `tools refactor hotspots`, `tools refactor opportunities`                                                                | Identify high-value refactor targets with churn and qualitative signals.                             |
| Quality gates          | `guard-rails`, `scripts/validate_quality_gates.py`, `scripts/lint_nested_decorators.py`                                  | Comprehensive quality validation with frontier-level standards (coverage, linting, typing, security).|
| Automation             | `hephaestus-toolkit/refactoring/scripts/`                                                                                | Execute codemods, hotspot scans, and characterization harnesses with reproducible scripts.           |
| Developer guard rails  | `.pre-commit-config.yaml`, Ruff, Black, PyUpgrade, Mypy, Pip Audit, `uv run hephaestus cleanup`                          | Keep code style, types, security, and workspace hygiene evergreen before commits land.               |
| Continuous integration | `.github/workflows/ci.yml`, `tests/test_cli.py`                                                                          | Enforce linting, typing, cleanup sweeps, and pytest during PRs with artefact uploads.                |
| Release & monitoring   | `.github/workflows/release-tag.yml`, `.github/workflows/turborepo-monitor.yml`, `ops/turborepo-release.json`, Dependabot | Cut deep-clean releases automatically and track upstream updates while nudging dependency hygiene.   |
| Post-release hygiene   | `cleanup` command, `cleanup-macos-cruft.sh`, automated CI/release/pre-commit hooks                                       | Keep workspaces clean before packaging or mirroring artefacts and ensure future syncs stay pristine. |

### Project Layout

```text
hephaestus/
├── pyproject.toml                           # Project metadata and dependencies
├── README.md                                # This overview
├── LICENSE                                  # MIT licence
├── docs/                                    # Diátaxis-aligned documentation
│   ├── index.md                             # Documentation landing page
│   ├── tutorials/                           # Step-by-step walkthroughs
│   ├── how-to/                              # Task-oriented guides (includes editor setup)
│   ├── explanation/                         # Architecture and conceptual material
│   └── reference/                           # Command and API references
├── src/hephaestus/                          # Python package installed via wheelhouse
│   ├── __init__.py                          # Version metadata
│   ├── cli.py                               # Typer-based CLI entry point
│   ├── cleanup.py                           # Workspace hygiene engine
│   ├── planning.py                          # Execution plan rendering helpers
│   ├── release.py                           # Wheelhouse download/install helpers
│   └── toolbox.py                           # Quality, coverage, and refactor APIs
├── scripts/                                 # Quality automation and validation
│   ├── validate_quality_gates.py            # Comprehensive quality gate runner
│   └── lint_nested_decorators.py            # Prevent command registration bugs
├── hephaestus-toolkit/                      # Standalone scripts and configs
│   └── refactoring/
│       ├── config/                          # Default configuration
│       ├── docs/                            # Playbooks and implementation notes
│       ├── scripts/                         # Analysis, codemods, verification helpers
│       └── ci/                              # Workflow fragment for pipelines
├── tests/                                   # Pytest suites (CLI, release, planning, cleanup)
└── dist/                                    # Generated wheels/sdists (created by `uv build`, ignored in git)
```

## Configuration

Hephaestus reads defaults from `[tool.hephaestus.toolkit]` in `pyproject.toml`. Use the bundled configuration at `hephaestus-toolkit/refactoring/config/refactor.config.yaml` as a reference and tailor thresholds, directory mappings, and rollout policies to match your repository layout. Analytics adapters can be configured via the `analytics` block—point churn, coverage, and embedding sources at YAML/JSON exports from your data warehouse to replace the synthetic defaults used for demos.

## CI Integration

- `hephaestus-toolkit/refactoring/ci/workflow.partial.yml` provides a baseline GitHub Actions job.
- Upload churn and hotspot artefacts to keep stakeholders informed.
- Run the codemod and verification scripts in advisory mode before enabling blocking gates.

## Documentation

The documentation site follows the [Diátaxis](https://diataxis.fr/) framework:

- **Tutorials** — e.g. `docs/tutorials/getting-started.md` for first-run guidance.
- **How-to guides** — task recipes such as `docs/how-to/install-wheelhouse.md` and `docs/how-to/editor-setup.md`.
- **Explanation** — conceptual material including `docs/explanation/architecture.md` and the lifecycle playbook.
- **Reference** — factual resources such as `docs/reference/cli.md`, `docs/cli-completions.md`, and the pre-release checklist.
- **Appendix** — templates and supporting material under `docs/adr/`.

Additional playbooks for the refactoring toolkit live under `hephaestus-toolkit/refactoring/docs/`.

## Contributing

1. Fork the repository that hosts Hephaestus.
2. Enable a fresh Python 3.12+ virtual environment (`uv` or `venv`).
3. Run `uv run pytest` to execute the test suite.
4. Open a pull request with clear before/after context and updated documentation.

Hephaestus embraces incremental, evidence-based change. Use the provided tools to gather metrics, add characterization tests, and stage refactors safely.

For security concerns, please review our [Security Policy](SECURITY.md).

## Security

We take security seriously. If you discover a security vulnerability, please follow our [Security Policy](SECURITY.md) for responsible disclosure. See also:

- [STRIDE Threat Model](docs/adr/0001-stride-threat-model.md) - Comprehensive security analysis
- [Operating Safely Guide](docs/how-to/operating-safely.md) - Safe usage practices and constraints
