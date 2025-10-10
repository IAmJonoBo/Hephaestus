# Hephaestus Developer Toolkit

[![License: MIT](https://img.shields.io/badge/License-MIT-blue.svg)](LICENSE)
[![Python 3.12+](https://img.shields.io/badge/python-3.12+-blue.svg)](https://www.python.org/downloads/)
[![PyPI version](https://img.shields.io/pypi/v/hephaestus-toolkit.svg)](https://pypi.org/project/hephaestus-toolkit/)
[![Code style: ruff](https://img.shields.io/badge/code%20style-ruff-000000.svg)](https://github.com/astral-sh/ruff)
[![Type checked: mypy](https://img.shields.io/badge/type%20checked-mypy-blue.svg)](http://mypy-lang.org/)
[![Security: pip-audit](https://img.shields.io/badge/security-pip--audit-blue.svg)](https://github.com/pypa/pip-audit)

Hephaestus is a standalone developer toolkit that helps engineering teams prioritize, automate, and safely deliver large-scale refactoring and quality improvements. It provides a comprehensive suite of commands for quality validation, intelligent refactoring planning, and safe automation.

## ✨ Key Features

- **🛡️ Guard Rails with Auto-Remediation**: Run lint, format, type-check, tests, security scans, and optional drift fixes from a single command.
- **📊 Analytics & Streaming Ingestion**: Prioritise refactoring with risk-aware rankings backed by churn, coverage, embedding feeds, or live NDJSON ingestion.
- **🤖 AI-Native Workflows**: Export structured command schemas and telemetry so agents can reason over plans, guard-rails, and remediation manifests.
- **🔌 Plugin Architecture**: Discover built-in and custom quality gate plugins with registry resets, capability introspection, and fail-closed execution.
- **🌐 Remote Automation**: FastAPI + gRPC services share a hardened execution engine for guard-rails, cleanup, analytics, and remediation across fleets.
- **📈 Observability with OpenTelemetry**: Optional tracing instruments CLI, API, and remediation commands with typed fallbacks when disabled.
- **🔒 Supply-Chain Hardening**: Mandatory SHA-256 manifests, Sigstore bundle verification, and drift detection in CI pipelines.
- **📚 Operator-Grade Docs**: Diátaxis documentation with safety playbooks, AI integration guides, and red-team assessments.

## 🎯 What's New in 0.3.0 (Unreleased)

### Release Candidate Enhancements (Phase 2 Implementations)

- **Plugin Architecture (ADR-0002)**: Discovery now resets registries, honours disabled built-ins, and exposes capability metadata for AI consumers.
- **OpenTelemetry Integration (ADR-0003)**: Command instrumentation captures guard-rails, cleanup, analytics, and remediation spans with graceful no-op fallbacks.
- **REST & gRPC APIs (ADR-0004)**: FastAPI implementation, client-streaming gRPC analytics ingestion, shared task orchestration, and auto-remediation parity across surfaces.
- **Sigstore Backfill (ADR-0006)**: Backfill tooling is execution-ready with bundle manifests, CLI integration, and release gating options.
- **Advanced Remediation Automation**: Drift detection can trigger targeted fixes, emit remediation telemetry, and surface manifests through CLI/API responses.
- **Streaming Analytics**: Shared ingestor accepts NDJSON over REST or gRPC, snapshots submissions for rankings, and exposes deterministic test hooks.

### Operational Hardening

- Refreshed telemetry shims with typed no-op fallbacks and cached module resolution.
- Guard-rails services fail closed when required tooling is absent and surface actionable remediation.
- CI pipelines enforce drift detection, coverage ≥ 85%, lint/type gates, and release build validation.

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
- **Guard-Rails Command**: One-command quality pipeline (cleanup → lint → workflow lint → format → typecheck → test → audit)
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

**Standard Installation (PyPI):**

```bash
# Install from PyPI
pip install hephaestus-toolkit

# With optional dependencies
pip install hephaestus-toolkit[dev,qa]

# Specific version
pip install hephaestus-toolkit==0.2.0
```

**Pre-release validation (Test PyPI via the CLI):**

```bash
# Install the latest prerelease published to Test PyPI
hephaestus release install --source test-pypi

# Install a specific prerelease tag (leading "v" is optional)
hephaestus release install --source test-pypi --tag v0.3.0rc1

# Target a managed virtual environment for isolation
hephaestus release install --source test-pypi --python .venv/bin/python
```

**Development Installation (from source):**

```bash
# Clone and setup with uv (recommended for development)
git clone https://github.com/IAmJonoBo/Hephaestus.git
cd Hephaestus

# Quick setup with automated script
./scripts/setup-dev-env.sh

# Or manual setup
uv sync --extra dev --extra qa --extra grpc
```

**Note for macOS users on external drives (exFAT, NTFS, FAT32):** The setup script automatically detects non-xattr filesystems and relocates the virtual environment to `$HOME/.uvenvs/<repo-name>` on your internal disk, creating a symlink at `.venv`. This prevents AppleDouble file issues. See [troubleshooting guide](https://iamjonobo.github.io/Hephaestus/how-to/troubleshooting/#working-on-externalusb-drives-exfat-ntfs-fat32) for details.

The setup script ensures a bulletproof development environment with:

- Python 3.12+ validation
- uv package manager installation (if needed)
- All dependencies synced from lockfile
- Pre-commit hooks configured
- Environment validation
- **macOS compatibility**: Automatic cleanup of resource fork files and proper UV configuration

> **Note for macOS users**: The setup script automatically configures UV to avoid reflink issues and cleans up AppleDouble files (`._*`) that can cause installation failures. If you encounter issues, see the [troubleshooting guide](https://iamjonobo.github.io/Hephaestus/how-to/troubleshooting/#macos-appledoubleresource-fork-installation-errors).

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
# Full pipeline: cleanup → lint → workflow lint → import-sort → format → typecheck → test → audit
hephaestus guard-rails

# Skip auto-formatting to review changes first
hephaestus guard-rails --no-format

# Check for tool version drift
hephaestus guard-rails --drift
```

**What it does:**

1. Deep cleanup of build artifacts
2. Lint code with ruff (auto-fix enabled)
3. Validate GitHub Actions workflows with actionlint
4. Auto-sort imports with ruff isort (`ruff check --select I --fix`)
5. Format code with ruff format
6. Type-check with mypy (strict mode)
7. Run pytest with coverage ≥85%
8. Security audit with pip-audit

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

See [CLI Autocompletion documentation](https://iamjonobo.github.io/Hephaestus/reference/cli-completions/) for manual installation steps and regeneration tips.

### Automation & CI

- Pre-commit hooks trigger `uv run hephaestus cleanup` on commits and pushes so macOS metadata never enters history.
- Continuous integration runs on GitHub Actions (`CI` workflow) for pushes to `main` and pull requests, exercising the pytest suite against Python 3.12 and 3.13.
- Linting and typing (Ruff + Mypy) run on every matrix job, with coverage published as artefacts and failing below 85%; each job performs a cleanup sweep immediately after dependency syncing.
- The `uv run hephaestus guard-rails` command executes the local cleanup, lint, workflow lint, format, typing, testing, and audit pipeline sequentially for quick validation.
- Automated release tagging (`Automated Release Tagging` workflow) cuts a `v*` tag and GitHub Release whenever the version in `pyproject.toml` advances on `main`, and performs a deep-clean sweep before tagging.
- Release wheelhouse packaging (`Build Wheelhouse` workflow) zips the built wheels and sdists for each release, uploads them as workflow artefacts, and attaches the bundle to the GitHub Release for easy download while PyPI access is pending.
- The `hephaestus release install` command fetches the latest (or a specified) wheelhouse archive from GitHub Releases, verifies checksums and Sigstore attestations by default, and installs the wheels into the current environment, making consumption trivial from any repo.
- The repository ships with the `cleanup` CLI command and `cleanup-macos-cruft.sh` wrapper for scrubbing macOS metadata, caches, and build artefacts; use them directly for ad-hoc housekeeping or leverage the built-in lifecycle automation.
- A scheduled TurboRepo monitor (`TurboRepo Release Monitor` workflow) compares the pinned version in `ops/turborepo-release.json` with upstream releases and opens an issue if an update is available.
- Weekly Dependabot scans cover Python packages and GitHub Actions while the CI pipeline executes `pip-audit --strict` on Python 3.13.

### CI Dependency Provisioning

- `deps-and-tests-online` runs on ubuntu-24.04, sets up Python 3.12 via `astral-sh/setup-uv@v7`, and relies on its cache-backed `uv sync --locked --extra dev --extra qa` install.
- All hosted-runner quality gates execute with `uv run` (pytest, Ruff lint + format, Mypy) so tests share the synced environment and cached wheels.
- `build-wheelhouse` exports `uv.lock` with `uv export --format requirements-txt` and builds every dependency wheel before adding the project wheel through `uv build --wheel`.
- The job publishes a `wheelhouse` artifact containing `wheelhouse/` and `requirements.txt`; rerun it whenever `uv.lock` changes to refresh offline bundles.
- `ci-offline` downloads that artifact, checks for Python 3.12 parity, and refuses to continue if the expected files are missing.
- Offline installation uses `pip install --no-index --find-links=wheelhouse/wheelhouse` for both dependencies and the project wheel.
- The same offline venv replays pytest plus Ruff lint/format and Mypy, proving the cache suffices without external network access.
- Keep offline runners on ubuntu-24.04 (or match the build job’s OS/arch) to avoid ABI or manylinux mismatches.
- Update `uv.lock` locally with `uv lock`, commit it, and CI will regenerate and attach the refreshed wheelhouse automatically.

### Development-to-Deployment Flow

| Stage                  | Tooling                                                                                                                                      | Purpose                                                                                               |
| ---------------------- | -------------------------------------------------------------------------------------------------------------------------------------------- | ----------------------------------------------------------------------------------------------------- |
| Discovery & planning   | [Lifecycle Playbook](https://iamjonobo.github.io/Hephaestus/lifecycle/), [ADRs](https://iamjonobo.github.io/Hephaestus/adr/), `plan` command | Capture intent, align stakeholders, and visualise rollouts.                                           |
| Local analytics        | `tools refactor hotspots`, `tools refactor opportunities`                                                                                    | Identify high-value refactor targets with churn and qualitative signals.                              |
| Quality gates          | `guard-rails`, `scripts/validate_quality_gates.py`, `scripts/lint_nested_decorators.py`                                                      | Comprehensive quality validation with frontier-level standards (coverage, linting, typing, security). |
| Automation             | `hephaestus-toolkit/refactoring/scripts/`                                                                                                    | Execute codemods, hotspot scans, and characterization harnesses with reproducible scripts.            |
| Developer guard rails  | `.pre-commit-config.yaml`, Ruff (linting, formatting, import sorting), Black, PyUpgrade, Mypy, Pip Audit, `uv run hephaestus cleanup`        | Keep code style, types, security, and workspace hygiene evergreen before commits land.                |
| Continuous integration | `.github/workflows/ci.yml`, `tests/test_cli.py`                                                                                              | Enforce linting, typing, cleanup sweeps, and pytest during PRs with artefact uploads.                 |
| Release & monitoring   | `.github/workflows/release-tag.yml`, `.github/workflows/turborepo-monitor.yml`, `ops/turborepo-release.json`, Dependabot                     | Cut deep-clean releases automatically and track upstream updates while nudging dependency hygiene.    |
| Post-release hygiene   | `cleanup` command, `cleanup-macos-cruft.sh`, automated CI/release/pre-commit hooks                                                           | Keep workspaces clean before packaging or mirroring artefacts and ensure future syncs stay pristine.  |

### Project Layout

```text
hephaestus/
├── pyproject.toml                           # Project metadata and dependencies
├── README.md                                # This overview
├── CHANGELOG.md                             # Version history and release notes
├── LICENSE                                  # MIT licence
├── SECURITY.md                              # Security policy and disclosure process
├── docs-site/                               # Astro Starlight documentation (frontier-grade automation)
│   ├── src/content/docs/                   # Documentation markdown files (Diátaxis-aligned)
│   │   ├── index.md                        # Documentation landing page
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
- **Formatting**: Ruff isort + Ruff format with 100-character line length
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

📖 **[View full documentation site →](https://iamjonobo.github.io/Hephaestus/)**

The documentation is built with [Astro Starlight](https://starlight.astro.build/) and features:

- **Self-Updating Content**: CLI reference, API docs, and version info auto-generated daily
- **Automated Quality**: Link validation, example testing, and stale content detection
- **Diátaxis Structure**: Tutorials, How-To guides, Explanations, and Reference sections
- **Full-Text Search**: Powered by Pagefind for instant results

### Documentation Categories

- **Tutorials** — [Getting Started](/tutorials/getting-started/) for first-run guidance
- **How-To Guides** — Task recipes like [Install from Wheelhouse](/how-to/install-wheelhouse/) and [Editor Setup](/how-to/editor-setup/)
- **Explanation** — Conceptual material including [Architecture](/explanation/architecture/) and [Lifecycle Playbook](/lifecycle/)
- **Reference** — [CLI Reference](/reference/cli/), [API Reference](/reference/api/), and [Pre-Release Checklist](/reference/pre-release-checklist/)
- **ADRs** — Architecture Decision Records under [ADR Index](/adr/)

### Local Documentation Development

```bash
cd docs-site
npm install          # First time only
npm run dev          # Live preview at http://localhost:4321
npm run update-all   # Update auto-generated content
npm run validate-all # Run quality checks
```

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

- [STRIDE Threat Model](https://iamjonobo.github.io/Hephaestus/adr/0001-stride-threat-model/) - Comprehensive security analysis
- [Operating Safely Guide](docs/how-to/operating-safely.md) - Safe usage practices and constraints
