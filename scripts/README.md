# Hephaestus Quality Automation Scripts

This directory contains automation scripts for quality validation and enforcement.

## Scripts

### validate_quality_gates.py

Comprehensive quality gate validation script that runs all project quality checks.

**Usage:**

```bash
python3 scripts/validate_quality_gates.py
```

**What it checks:**

- Pytest with coverage ≥85%
- Ruff linting
- Ruff import sorting (Ruff isort)
- Ruff formatting
- Mypy type checking
- Nested decorator linting
- Build artifact generation
- Security auditing (pip-audit)

**Exit codes:**

- 0: All required gates passed
- 1: One or more required gates failed

**Features:**

- Clear pass/fail reporting
- Category-based organization
- Required vs optional gate distinction
- Verbose output with command execution details

### lint_nested_decorators.py

AST-based linter to detect Typer command decorators defined inside functions, which causes registration bugs.

**Usage:**

```bash
# Check specific files
python3 scripts/lint_nested_decorators.py src/hephaestus/cli.py

# Check entire directory (default: src/hephaestus)
python3 scripts/lint_nested_decorators.py

# Check multiple paths
python3 scripts/lint_nested_decorators.py src/hephaestus tests
```

**What it detects:**

- `@app.command()` decorators inside function bodies
- `@tools_app.command()`, `@refactor_app.command()`, etc.
- Nested at any depth (detects deeply nested cases)
- Both sync and async function definitions

**Exit codes:**

- 0: No violations found
- 1: Violations detected or error occurred

**Background:**

This linter prevents regression of the "guard-rails availability bug" where the `guard_rails` command was accidentally defined inside the `cleanup` function, making it unavailable until cleanup ran first. See `Next_Steps.md` red team findings for full context.

### run_actionlint.sh

Installs and runs actionlint for GitHub Actions workflow validation. **Features automatic installation and resilient error handling.**

**Usage:**

```bash
bash scripts/run_actionlint.sh
```

**What it does:**

- **Auto-downloads and installs actionlint v1.7.7** if not present or wrong version
- Validates all workflow files in `.github/workflows/` (both .yml and .yaml)
- Checks for syntax errors, deprecated actions, and common mistakes
- Reports shellcheck issues in workflow scripts
- Provides clear error messages and troubleshooting guidance

**Features:**

- **🔧 Automatic installation** - Downloads and installs actionlint automatically
- Automatic installation to `~/.local/bin`
- Version pinning for reproducibility
- Comprehensive workflow validation
- Platform detection (Linux, macOS)
- Architecture detection (amd64, arm64)
- Resilient error handling

**Exit codes:**

- 0: All workflows valid
- 1: Validation errors found or installation failed

**Example output:**

```bash
$ bash scripts/run_actionlint.sh
→ Checking for actionlint...
→ actionlint not found, installing...
→ Installing actionlint 1.7.7 for linux/amd64...
✓ actionlint installed to /home/user/.local/bin/actionlint
→ Running actionlint on workflow files...
✓ All 15 workflow file(s) passed actionlint validation
```

### bump_version.sh

Interactive version bumping script that updates version numbers across the project. **Features automatic lockfile regeneration.**

**Usage:**

```bash
# Bump to a new version (auto-regenerates lockfile)
./scripts/bump_version.sh 0.3.0

# Bump without auto-regenerating lockfile
AUTO_LOCK=0 ./scripts/bump_version.sh 0.3.0
```

**What it does:**

1. Validates version format (semantic versioning)
2. Checks version is actually increasing
3. Determines release type (MAJOR, MINOR, PATCH)
4. Updates `pyproject.toml`
5. Updates `src/hephaestus/__init__.py` (if version present)
6. **Auto-regenerates lockfile via `uv lock`** (if `AUTO_LOCK=1`, default)
7. Generates CHANGELOG template
8. Provides next steps guidance

**Features:**

- **🔧 Auto-regeneration** - Automatically updates lockfile after version bump
- Semantic versioning validation
- Prevents version downgrades
- Interactive confirmation
- Color-coded output
- Context-aware next steps
- CHANGELOG template generation

**Exit codes:**

- 0: Success
- 1: Validation error or user cancellation

**Example output:**

```bash
$ ./scripts/bump_version.sh 0.3.0
Current version: 0.2.0
New version: 0.3.0
Release type: MINOR

This will:
  1. Update version in pyproject.toml: 0.2.0 → 0.3.0
  2. Update version in src/hephaestus/__init__.py (if present)

Continue? [y/N] y
✓ Version bumped to 0.3.0

→ Regenerating lockfile...
✓ Lockfile regenerated (uv.lock)

CHANGELOG template for version 0.3.0:
...
```

**See also:**

- [Release Process Guide](../docs/how-to/release-process.md)

### validate-dependency-orchestration.sh

Comprehensive dependency orchestration validation script that ensures all dependency management components are properly configured. **Features automatic remediation of common issues.**

**Usage:**

```bash
# Run with auto-remediation (default)
./scripts/validate-dependency-orchestration.sh

# Run without auto-remediation (validation only)
AUTO_REMEDIATE=0 ./scripts/validate-dependency-orchestration.sh

# Dry-run mode - show what would be done without doing it
DRY_RUN=1 ./scripts/validate-dependency-orchestration.sh

# Interactive mode - prompt before each change
INTERACTIVE=1 ./scripts/validate-dependency-orchestration.sh

# Persist environment variables to shell profile
PERSIST_CONFIG=1 ./scripts/validate-dependency-orchestration.sh

# Disable logging
LOG_REMEDIATION=0 ./scripts/validate-dependency-orchestration.sh

# Combined flags (dry-run + interactive + persist)
DRY_RUN=1 INTERACTIVE=1 PERSIST_CONFIG=1 ./scripts/validate-dependency-orchestration.sh
```

**Configuration Flags:**

| Flag | Default | Description |
|------|---------|-------------|
| `AUTO_REMEDIATE` | 1 | Enable/disable auto-remediation |
| `DRY_RUN` | 0 | Show what would be done without doing it |
| `INTERACTIVE` | 0 | Prompt before each change |
| `PERSIST_CONFIG` | 0 | Add environment variables to shell profile |
| `LOG_REMEDIATION` | 1 | Log all actions to `~/.hephaestus/logs/` |
| `PRE_FLIGHT_CHECK` | 0 | Run health checks before operations |

**What it checks and auto-remediates:**

- **Python version ≥3.12** - Auto-installs via `uv python install 3.12` if missing
- **uv installation** - Auto-installs from https://astral.sh/uv if not found
- **pyproject.toml existence** - Validation only
- **uv.lock sync status** - Auto-regenerates lockfile if out of sync
- **Workflow Python version consistency** - Validation only
- **Workflow --locked flag usage** - Validation only
- **setup-uv python-version specifications** - Validation only
- **Dependabot configuration** - Validation only
- **Dependency sync functionality** - Auto-syncs dependencies if needed
- **Environment isolation (.venv usage)** - Auto-creates virtual environment
- **macOS environment variables** - Auto-sets `COPYFILE_DISABLE=1` and `UV_LINK_MODE=copy`

**Exit codes:**

- 0: All checks passed
- 1: One or more checks failed (even after auto-remediation)

**Features:**

- **🔧 Auto-remediation** - Automatically fixes common issues
- **📝 Remediation Logs** - Tracks all actions in timestamped log files
- **🤖 Interactive Mode** - Prompts before making changes (for paranoid users)
- **👀 Dry-Run Mode** - Shows what would be done without doing it
- **💾 Persistent Config** - Auto-adds environment variables to shell profile
- **🏥 Health Checks** - Pre-flight validation (optional, off by default)
- Color-coded output (✓ success, ✗ error, ⚠ warning, ⚙ remediated)
- Comprehensive validation across all components
- Detects common misconfigurations
- Can be run locally or in CI
- Guards against drift during repo sync
- Intelligent and foolproof - works without manual intervention

**Auto-remediation examples:**

```bash
# If Python 3.12 is missing, the script will:
# 1. Detect the issue
# 2. Run: uv python install 3.12
# 3. Run: uv python pin 3.12
# 4. Continue validation

# If uv is missing, the script will:
# 1. Detect the issue
# 2. Download and run: curl -LsSf https://astral.sh/uv/install.sh | sh
# 3. Add to PATH for the session
# 4. Continue validation

# If lockfile is out of sync, the script will:
# 1. Detect the issue
# 2. Run: uv lock
# 3. Continue validation
```

**Example output:**

```bash
$ ./scripts/validate-dependency-orchestration.sh
==================================================================
Hephaestus Dependency Orchestration Validator
==================================================================

→ Checking Python version...
⚠ Python 3.12+ required, found 3.9.6
⚙ Attempting to install Python 3.12 via uv...
✓ Python 3.12 installed via uv
✓ Python 3.12 pinned for this project
✓ Python 3.12.8 now available
→ Checking uv installation...
✓ uv detected: uv 0.9.1
...
==================================================================
✓ All dependency orchestration checks passed
⚙ 3 issue(s) were auto-remediated
```

**See also:**

- [CI/CD Setup Guide](../docs/how-to/ci-setup.md)
- [Dependency Management Best Practices](../docs/how-to/ci-setup.md#dependency-management-best-practices)

### backfill_sigstore_bundles.py

Automated Sigstore bundle backfill for historical releases (ADR-0006 Sprint 2).

**Usage:**

```bash
# Dry run (recommended first)
GITHUB_TOKEN=<token> python scripts/backfill_sigstore_bundles.py --dry-run

# Backfill all historical versions
GITHUB_TOKEN=<token> python scripts/backfill_sigstore_bundles.py

# Backfill specific version
GITHUB_TOKEN=<token> python scripts/backfill_sigstore_bundles.py --version v0.2.3
```

**What it does:**

1. Enumerates historical releases (v0.1.0-v0.2.3)
2. Downloads existing wheelhouse archives
3. Verifies SHA-256 checksums against published manifests
4. Generates Sigstore attestations using current signing identity
5. Adds backfill metadata to attestations
6. Uploads .sigstore bundles as new release assets
7. Updates release notes with backfill notices

**Requirements:**

- `GITHUB_TOKEN` environment variable with repo write access
- `sigstore-python` installed (`pip install sigstore`)
- GitHub Actions OIDC authentication (for production use)
- `requests` library

**Features:**

- Dry run mode for testing
- Automatic checksum verification
- Backfill metadata tracking
- Idempotent (skips already-backfilled releases)
- Comprehensive error handling and logging
- GitHub Actions workflow integration

**Exit codes:**

- 0: Success (all versions backfilled)
- 1: One or more versions failed

**GitHub Actions Integration:**

The script is integrated into a manual workflow (`.github/workflows/sigstore-backfill.yml`):

```bash
# Trigger via GitHub Actions UI with:
# - Optional version filter
# - Dry run toggle
# - Automatic artifact uploads
```

**Historical Versions:**

- v0.1.0, v0.1.1, v0.1.2
- v0.2.0, v0.2.1, v0.2.2, v0.2.3

**Backfill Metadata Format:**

```json
{
  "version": "v0.2.3",
  "original_release_date": "2025-01-10T12:00:00Z",
  "backfill_date": "2025-01-20T15:30:00Z",
  "backfill_identity": "https://github.com/IAmJonoBo/Hephaestus/.github/workflows/backfill.yml@refs/heads/main",
  "verification_status": "backfilled",
  "checksum_verified": true,
  "notes": "Sigstore bundle backfilled for historical release..."
}
```

**See also:**

- [ADR-0006: Sigstore Bundle Backfill](../docs/adr/0006-sigstore-backfill.md)
- [Security Policy](../SECURITY.md)
- [Operating Safely Guide](../docs/how-to/operating-safely.md)

## Integration

### CI Pipeline

Both scripts are integrated into the CI workflow (`.github/workflows/ci.yml`):

```yaml
- name: Check for nested decorators
  run: python3 scripts/lint_nested_decorators.py src/hephaestus
```

### Pre-commit Hooks

The nested decorator linter runs as a pre-commit hook (`.pre-commit-config.yaml`):

```yaml
- id: lint-nested-decorators
  name: Check for nested Typer decorators
  entry: python3 scripts/lint_nested_decorators.py
  language: system
  types: [python]
```

### Guard Rails Command

The quality gates are also enforced by the `hephaestus guard-rails` command:

```bash
uv run hephaestus guard-rails
```

This runs:

1. Deep cleanup
2. Ruff check
3. Actionlint workflow validation
4. Ruff isort (`ruff check --select I --fix`)
5. Ruff format
6. Mypy
7. Pytest
8. pip-audit

## Development

### Running Tests

Tests for the nested decorator linter are in `tests/test_lint_nested_decorators.py`:

```bash
uv run pytest tests/test_lint_nested_decorators.py -v
```

### Adding New Quality Gates

To add a new quality gate to `validate_quality_gates.py`:

1. Add a `QualityGate` instance to the `QUALITY_GATES` list
2. Specify the command, description, category, and whether it's required
3. The script will automatically include it in validation runs

Example:

```python
QualityGate(
    name="Bandit Security Scan",
    command=["bandit", "-r", "src"],
    required=True,
    description="Security linting with Bandit",
    category="security",
)
```

### Extending the Nested Decorator Linter

To check for additional decorator patterns:

1. Add the decorator name pattern to `COMMAND_DECORATORS` set in the checker class
2. Add test cases to `tests/test_lint_nested_decorators.py`
3. Update documentation if the check scope changes

## Documentation

- [Quality Gate Validation Guide](../docs/how-to/quality-gates.md)
- [Operating Safely Guide](../docs/how-to/operating-safely.md)
- [Next Steps Tracker](../Next_Steps.md)
- [Frontier Red Team Analysis](../docs/explanation/frontier-red-team-gap-analysis.md)

## Troubleshooting

### Script Not Found

Ensure you're running from the project root:

```bash
cd /path/to/Hephaestus
python3 scripts/lint_nested_decorators.py
```

### Permission Denied

Make scripts executable:

```bash
chmod +x scripts/*.py
```

### Import Errors

The scripts use only standard library modules and should work with Python 3.12+. If you see import errors, ensure you're using the correct Python version:

```bash
python3 --version  # Should be 3.12 or higher
```

## Contributing

When adding new quality automation:

1. Follow the existing script patterns
2. Add comprehensive tests
3. Update this README
4. Update the how-to documentation
5. Integrate into CI and pre-commit if appropriate
