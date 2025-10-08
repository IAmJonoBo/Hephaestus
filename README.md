# Hephaestus Developer Toolkit

[![License: MIT](https://img.shields.io/badge/License-MIT-blue.svg)](LICENSE)
[![Python 3.12+](https://img.shields.io/badge/python-3.12+-blue.svg)](https://www.python.org/downloads/)
[![Code style: ruff](https://img.shields.io/badge/code%20style-ruff-000000.svg)](https://github.com/astral-sh/ruff)
[![Type checked: mypy](https://img.shields.io/badge/type%20checked-mypy-blue.svg)](http://mypy-lang.org/)
[![Security: pip-audit](https://img.shields.io/badge/security-pip--audit-blue.svg)](https://github.com/pypa/pip-audit)

Hephaestus is a standalone developer toolkit that helps engineering teams prioritize, automate, and safely deliver large-scale refactoring and quality improvements. It provides a comprehensive suite of commands for quality validation, intelligent refactoring planning, and safe automation.

## ✨ Key Features

- **🛡️ Guard Rails**: One-command quality pipeline (lint, format, type-check, test, audit)
- **📊 Analytics-Driven Rankings**: Data-backed prioritization for refactoring work
- **🤖 AI-Native**: Export command schemas for seamless AI agent integration
- **🔒 Safety First**: Dangerous path protection, dry-run previews, audit manifests
- **🔍 Drift Detection**: Automatic environment validation and remediation
- **📦 Secure Release**: SHA-256 verification and Sigstore attestation support
- **📚 Comprehensive Docs**: Diátaxis-structured guides for every use case

## 🎯 What's New in 0.2.0

### AI & Intelligence

- **Analytics Ranking API**: Four strategies for prioritizing refactoring work (risk_weighted, coverage_first, churn_based, composite)
- **AI-Native Schemas**: `hephaestus schema` command exports structured metadata for AI agents (Copilot, Cursor, Claude)
- **Pluggable Analytics**: Support for churn, coverage, and embedding data sources

### Security & Safety

- **Enhanced Verification**: SHA-256 checksums + Sigstore attestation support
- **Cleanup Safety Rails**: Dangerous path protection, dry-run previews, typed confirmations, audit manifests
- **STRIDE Threat Model**: Comprehensive security analysis documented in ADR-0001
- **Published Security Policy**: Clear disclosure process and SLAs

### Quality & Tooling

- **Drift Detection**: `hephaestus guard-rails --drift` validates environment and suggests fixes
- **Guard-Rails Command**: One-command quality pipeline (cleanup → lint → format → typecheck → test → audit)
- **Nested Decorator Linting**: AST-based prevention of command registration bugs
- **Quality Gate Validation**: Single script validates all frontier-level standards

### Documentation

- **AI Agent Integration Guide**: Complete patterns for AI assistant integration
- **Operating Safely Guide**: Comprehensive safety features and best practices
- **Quality Gates Guide**: Deep dive into validation and troubleshooting
- **Frontier Red Team Analysis**: Security assessment and gap analysis

See [CHANGELOG.md](CHANGELOG.md) for complete details.

## 🚀 Quick Start

### Installation

```bash
# Using pip
pip install hephaestus

# Or from source with uv (recommended for development)
git clone https://github.com/IAmJonoBo/Hephaestus.git
cd Hephaestus
uv sync --extra dev --extra qa
```

### Essential Commands

```bash
# Run comprehensive quality checks (most important!)
hephaestus guard-rails

# Check for tool version drift
hephaestus guard-rails --drift

# Clean build artifacts safely
hephaestus cleanup

# Get refactoring recommendations
hephaestus tools refactor rankings --strategy risk_weighted

# Export schemas for AI agents
hephaestus schema --output schemas.json

# View all commands
hephaestus --help
```

### Your First Workflow

```bash
# 1. Verify environment
hephaestus guard-rails --drift

# 2. Make changes
# ... edit code ...

# 3. Validate before commit
hephaestus guard-rails

# 4. Commit and push
git add .
git commit -m "Your changes"
git push
```

## 📋 Command Reference

### Core Commands

#### guard-rails

Run comprehensive quality and security pipeline in one command:

```bash
# Full pipeline: cleanup → lint → format → typecheck → test → audit
hephaestus guard-rails

# Skip auto-formatting to review changes first
hephaestus guard-rails --no-format

# Check for tool version drift
hephaestus guard-rails --drift
```

**What it does:**

1. Deep cleanup of build artifacts
2. Lint code with ruff (auto-fix enabled)
3. Format code with ruff format
4. Type-check with mypy (strict mode)
5. Run pytest with coverage ≥85%
6. Security audit with pip-audit

#### cleanup

Safely remove development cruft with multiple safety rails:

```bash
# Interactive cleanup with preview (default)
hephaestus cleanup

# Deep clean (includes venvs, coverage)
hephaestus cleanup --deep-clean

# Preview only (no deletion)
hephaestus cleanup --dry-run
```

**Safety features:**

- Mandatory dry-run preview
- Dangerous path protection (refuses /, /home, /usr, etc.)
- Typed confirmation for out-of-root targets
- Virtual environment protection
- JSON audit manifests

#### tools refactor

Get intelligent refactoring recommendations:

```bash
# View hotspots (high churn + low coverage)
hephaestus tools refactor hotspots --limit 10

# Prioritized rankings (requires analytics data)
hephaestus tools refactor rankings --strategy risk_weighted
hephaestus tools refactor rankings --strategy coverage_first --limit 20
hephaestus tools refactor rankings --strategy churn_based
hephaestus tools refactor rankings --strategy composite

# View opportunities
hephaestus tools refactor opportunities
```

**Ranking strategies:**

- `risk_weighted`: Balances coverage, churn, and complexity (default)
- `coverage_first`: Prioritizes coverage gaps
- `churn_based`: Focuses on frequently changed files
- `composite`: Balanced with embedding bonus

#### release

Install wheelhouse distributions with security verification:

```bash
# Install latest release
hephaestus release install --repository IAmJonoBo/Hephaestus

# Install specific version
hephaestus release install --repository IAmJonoBo/Hephaestus --tag v0.2.0

# With signature verification
hephaestus release install --verify-checksum --require-sigstore

# View help
hephaestus release install --help
```

**Security features:**

- SHA-256 checksum verification
- Sigstore attestation validation
- Identity pinning support
- Path traversal prevention

#### schema

Export command schemas for AI agent integration:

```bash
# Export to stdout
hephaestus schema

# Export to file
hephaestus schema --output schemas.json
```

Enables AI assistants (Copilot, Cursor, Claude) to invoke Hephaestus with:

- Complete parameter specifications
- Usage examples
- Expected outputs
- Retry hints

#### plan

Generate refactoring execution plans:

```bash
hephaestus plan
```

Visualize orchestration progress during rollouts.

### QA Tools

```bash
# Check coverage
hephaestus tools qa coverage

# View QA profile
hephaestus tools qa profile quick --dry-run
```

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

### CI Dependency Provisioning

- `deps-and-tests-online` runs on ubuntu-24.04 with `astral-sh/setup-uv@v7`, caching Python 3.12 and executing `uv sync --locked --extra dev --extra qa`.
- Quality checks execute through `uv run` (pytest, Ruff lint + format, Mypy) so tests reuse the synced virtual environment.
- `build-wheelhouse` exports `uv.lock` to `requirements.txt`, builds wheels for every dependency, and adds the project wheel via `uv build --wheel`.
- Wheels and the exported requirements file upload as the `wheelhouse` artefact; re-run this job after updating `uv.lock` to refresh the bundle.
- `ci-offline` downloads the artefact, validates Python 3.12 parity, and installs strictly with `pip --no-index --find-links=wheelhouse/wheelhouse`.
- Offline QA replays pytest and Ruff/Mypy entirely from the wheelhouse to ensure zero network reliance.
- Keep the offline runner on ubuntu-24.04 (or match whichever OS builds the wheels) to avoid ABI drift.
- When dependencies change, run `uv lock` locally, commit the updated lock, and let CI regenerate the wheelhouse on the next push.
- Missing or stale artefacts trigger explicit failures so teams can rebuild the wheelhouse before retrying restricted runs.

### Development-to-Deployment Flow

| Stage                  | Tooling                                                                                                                  | Purpose                                                                                               |
| ---------------------- | ------------------------------------------------------------------------------------------------------------------------ | ----------------------------------------------------------------------------------------------------- |
| Discovery & planning   | `docs/lifecycle.md`, `docs/adr/`, `plan` command                                                                         | Capture intent, align stakeholders, and visualise rollouts.                                           |
| Local analytics        | `tools refactor hotspots`, `tools refactor opportunities`                                                                | Identify high-value refactor targets with churn and qualitative signals.                              |
| Quality gates          | `guard-rails`, `scripts/validate_quality_gates.py`, `scripts/lint_nested_decorators.py`                                  | Comprehensive quality validation with frontier-level standards (coverage, linting, typing, security). |
| Automation             | `hephaestus-toolkit/refactoring/scripts/`                                                                                | Execute codemods, hotspot scans, and characterization harnesses with reproducible scripts.            |
| Developer guard rails  | `.pre-commit-config.yaml`, Ruff, Black, PyUpgrade, Mypy, Pip Audit, `uv run hephaestus cleanup`                          | Keep code style, types, security, and workspace hygiene evergreen before commits land.                |
| Continuous integration | `.github/workflows/ci.yml`, `tests/test_cli.py`                                                                          | Enforce linting, typing, cleanup sweeps, and pytest during PRs with artefact uploads.                 |
| Release & monitoring   | `.github/workflows/release-tag.yml`, `.github/workflows/turborepo-monitor.yml`, `ops/turborepo-release.json`, Dependabot | Cut deep-clean releases automatically and track upstream updates while nudging dependency hygiene.    |
| Post-release hygiene   | `cleanup` command, `cleanup-macos-cruft.sh`, automated CI/release/pre-commit hooks                                       | Keep workspaces clean before packaging or mirroring artefacts and ensure future syncs stay pristine.  |

### Project Layout

```text
hephaestus/
├── pyproject.toml                           # Project metadata and dependencies
├── README.md                                # This overview
├── CHANGELOG.md                             # Version history and release notes
├── LICENSE                                  # MIT licence
├── SECURITY.md                              # Security policy and disclosure process
├── docs/                                    # Diátaxis-aligned documentation
│   ├── index.md                             # Documentation landing page
│   ├── tutorials/                           # Step-by-step walkthroughs
│   │   └── getting-started.md               # Complete getting started guide
│   ├── how-to/                              # Task-oriented guides
│   │   ├── ai-agent-integration.md          # AI assistant integration patterns
│   │   ├── operating-safely.md              # Safety features and best practices
│   │   ├── quality-gates.md                 # Quality validation guide
│   │   ├── install-wheelhouse.md            # Wheelhouse installation
│   │   └── editor-setup.md                  # IDE configuration
│   ├── explanation/                         # Architecture and conceptual material
│   │   ├── architecture.md                  # Component design and boundaries
│   │   └── frontier-red-team-gap-analysis.md # Security assessment
│   ├── reference/                           # Command and API references
│   │   └── cli.md                           # Complete CLI reference
│   └── adr/                                 # Architecture Decision Records
│       └── 0001-stride-threat-model.md      # STRIDE security analysis
├── src/hephaestus/                          # Python package installed via wheelhouse
│   ├── __init__.py                          # Version metadata
│   ├── cli.py                               # Typer-based CLI entry point
│   ├── cleanup.py                           # Workspace hygiene engine with safety rails
│   ├── planning.py                          # Execution plan rendering helpers
│   ├── release.py                           # Wheelhouse download/install with verification
│   ├── toolbox.py                           # Quality, coverage, and refactor APIs
│   ├── analytics.py                         # Ranking strategies and pluggable adapters
│   ├── schema.py                            # AI-native command schema export
│   ├── drift.py                             # Tool version drift detection
│   ├── logging.py                           # Structured logging utilities
│   └── telemetry.py                         # Event definitions and correlation
├── scripts/                                 # Quality automation and validation
│   ├── README.md                            # Scripts documentation
│   ├── validate_quality_gates.py            # Comprehensive quality gate runner
│   └── lint_nested_decorators.py            # Prevent command registration bugs
├── hephaestus-toolkit/                      # Standalone scripts and configs
│   └── refactoring/
│       ├── config/                          # Default configuration
│       │   └── refactor.config.yaml         # Refactoring toolkit settings
│       ├── docs/                            # Playbooks and implementation notes
│       ├── scripts/                         # Analysis, codemods, verification helpers
│       └── ci/                              # Workflow fragment for pipelines
├── tests/                                   # Pytest suites with 87%+ coverage
│   ├── test_cli.py                          # CLI command tests
│   ├── test_cleanup.py                      # Cleanup safety tests
│   ├── test_release.py                      # Release verification tests
│   ├── test_analytics.py                    # Ranking strategy tests
│   ├── test_schema.py                       # Schema export tests
│   ├── test_drift.py                        # Drift detection tests
│   └── test_logging.py                      # Structured logging tests
└── dist/                                    # Generated wheels/sdists (created by `uv build`, ignored in git)
```

## Configuration

Hephaestus reads defaults from `[tool.hephaestus.toolkit]` in `pyproject.toml`. Use the bundled configuration at `hephaestus-toolkit/refactoring/config/refactor.config.yaml` as a reference and tailor thresholds, directory mappings, and rollout policies to match your repository layout. Analytics adapters can be configured via the `analytics` block—point churn, coverage, and embedding sources at YAML/JSON exports from your data warehouse to replace the synthetic defaults used for demos.

### Example Configuration

```toml
[tool.hephaestus.toolkit]
default_config = "hephaestus-toolkit/refactoring/config/refactor.config.yaml"
workspace_root = "."

[tool.hephaestus.analytics]
churn_file = "analytics/churn.json"
coverage_file = "coverage.xml"
embeddings_file = "analytics/embeddings.json"
```

### Environment Variables

```bash
# Release caching directory
export HEPHAESTUS_RELEASE_CACHE="$HOME/.cache/hephaestus/wheelhouses"

# Logging format (text or json)
export HEPHAESTUS_LOG_FORMAT="json"

# Log level
export HEPHAESTUS_LOG_LEVEL="INFO"
```

## 🎯 Frontier Quality Standards

Hephaestus enforces frontier-level quality through automated gates:

### Code Quality

- **Linting**: Ruff with strict configuration (E, F, I, UP, B, C4 rules)
- **Formatting**: Ruff format with 100-character line length
- **Type Safety**: Mypy strict mode with full coverage of src and tests
- **Architecture**: Nested decorator linting prevents command registration bugs

### Testing

- **Coverage**: Minimum 85% test coverage enforced by pytest-cov
- **Randomization**: pytest-randomly ensures test independence
- **Warnings**: All warnings treated as errors to prevent degradation

### Security

- **Dependency Auditing**: pip-audit with strict mode in CI
- **Dangerous Path Protection**: Cleanup command guards against data loss
- **Release Verification**: SHA-256 checksums + Sigstore attestation support

### Automation

- **CI Pipeline**: All checks run on every PR and push to main
- **Pre-commit Hooks**: Local validation before commits
- **Guard Rails**: One-command validation via `hephaestus guard-rails`

### Validate All Standards

```bash
# One command to rule them all
hephaestus guard-rails

# Or use the comprehensive validator
python3 scripts/validate_quality_gates.py
```

## CI Integration

- `hephaestus-toolkit/refactoring/ci/workflow.partial.yml` provides a baseline GitHub Actions job.
- Upload churn and hotspot artefacts to keep stakeholders informed.
- Run the codemod and verification scripts in advisory mode before enabling blocking gates.

## Project Documentation

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

## Security Disclosure

We take security seriously. If you discover a security vulnerability, please follow our [Security Policy](SECURITY.md) for responsible disclosure. See also:

- [STRIDE Threat Model](docs/adr/0001-stride-threat-model.md) - Comprehensive security analysis
- [Operating Safely Guide](docs/how-to/operating-safely.md) - Safe usage practices and constraints
