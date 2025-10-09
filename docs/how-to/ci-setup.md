# CI/CD Setup Guide

This guide explains the Hephaestus CI/CD pipeline architecture and how to ensure bulletproof dependency management for ephemeral runners.

## Architecture Overview

The Hephaestus CI pipeline uses a dual-path approach to ensure reliability in both internet-enabled and restricted network environments:

1. **Online Path** (`deps-and-tests-online`): Fast path using `uv` with direct PyPI access
2. **Offline Path** (`build-wheelhouse` + `ci-offline`): Bulletproof path using pre-built wheel archives

## Why Two Paths?

### Online Path Benefits

- **Speed**: Uses uv's built-in caching and parallel downloads
- **Simplicity**: Direct dependency resolution from PyPI
- **Latest versions**: Always uses the locked versions from `uv.lock`

### Offline Path Benefits

- **Reliability**: Works in restricted network environments
- **Reproducibility**: Guaranteed exact versions from wheelhouse
- **Security**: Reduced external dependencies during CI runs
- **Portability**: Can be used in air-gapped environments

## Pipeline Details

### Job 1: Online CI (`deps-and-tests-online`)

```yaml
- Setup uv and Python 3.12
- Sync dependencies from uv.lock with dev + qa extras
- Validate environment (Python, pytest, ruff, mypy)
- Run tests
- Run ruff lint check
- Run ruff format check
- Run mypy type check
```

**Key Features:**

- Uses `astral-sh/setup-uv@v7` for consistent uv installation
- Enables uv caching for faster subsequent runs
- Validates all tools are available before running checks

### Job 2: Build Wheelhouse (`build-wheelhouse`)

```yaml
- Setup uv and Python 3.12
- Export uv.lock to requirements.txt (with --extra dev --extra qa)
- Build wheels for all dependencies
- Build wheel for hephaestus itself
- Sanitize wheelhouse (remove macOS resource forks)
- Verify wheelhouse (check for any remaining artifacts)
- Upload wheelhouse as artifact
```

**Key Features:**

- Uses `--extra` (not `--group`) for optional-dependencies
- Includes comprehensive logging for debugging
- Validates wheelhouse integrity before upload
- Sets `COPYFILE_DISABLE=1` to prevent macOS artifacts

### Job 3: Offline CI (`ci-offline`)

```yaml
- Download wheelhouse artifact from build-wheelhouse
- Validate artifact structure and contents
- Create isolated venv
- Install dependencies from wheelhouse (no network)
- Validate all tools are available
- Run tests
- Run QA checks (ruff, mypy)
```

**Key Features:**

- Uses `--no-index` to ensure no network access
- Validates Python version matches build environment
- Comprehensive tool availability checks
- Same OS/arch as build job (ubuntu-24.04)

## Dependency Management Best Practices

### 1. Use uv.lock for Reproducibility

```bash
# Lock dependencies
uv lock

# Validate lock is in sync with pyproject.toml
uv lock --check

# Sync environment from lock
uv sync --locked --extra dev --extra qa
```

The lockfile ensures:

- Exact versions across all environments
- Transitive dependency resolution
- Consistent builds in CI and local development
- Protection against drift during repo sync

**Important:** Always run `uv lock --check` in CI to detect when `uv.lock` is out of sync with `pyproject.toml`. This guards against merge conflicts and manual edits that could break reproducibility.

### 2. Proper Extra Specification

In `pyproject.toml`, use `[project.optional-dependencies]`:

```toml
[project.optional-dependencies]
dev = [
  "ruff>=0.14.0",
  "mypy>=1.18.2",
  # ...
]
qa = [
  "pytest>=8.2",
  "pytest-cov>=5.0",
  # ...
]
```

In CI, use `--extra` (not `--group`):

```bash
# Correct ✓
uv export --locked --format requirements-txt --extra dev --extra qa

# Incorrect ✗
uv export --locked --format requirements-txt --group dev --group qa
```

### 3. Validate Environment Before Tests

Always validate that all required tools are available:

```bash
# Validate Python
uv run python --version

# Validate key packages
uv run python -c "import pytest; print(f'pytest {pytest.__version__}')"
uv run python -c "import mypy; print(f'mypy {mypy.__version__}')"

# Validate CLI tools
uv run python -m ruff --version
```

### 4. Wheelhouse Build Process

The wheelhouse build follows this pattern:

```bash
# 1. Export locked requirements
uv export --locked --format requirements-txt \
  --extra dev --extra qa \
  --all-extras \
  -o requirements.txt

# 2. Build wheels for dependencies
pip wheel -r requirements.txt -w wheelhouse

# 3. Build project wheel
uv build --wheel
cp dist/*.whl wheelhouse/

# 4. Sanitize (remove macOS artifacts)
uv run python -m hephaestus.cli wheelhouse sanitize wheelhouse

# 5. Verify (check for remaining artifacts)
uv run python -m hephaestus.cli wheelhouse verify wheelhouse
```

### 5. Offline Install Process

The offline install follows this pattern:

```bash
# 1. Create isolated environment
python -m venv .venv
. .venv/bin/activate

# 2. Upgrade pip from wheelhouse
pip install --no-index --find-links=wheelhouse pip

# 3. Install dependencies from wheelhouse
pip install --no-index \
  --find-links=wheelhouse \
  -r requirements.txt

# 4. Install project from wheelhouse
pip install --no-index \
  --find-links=wheelhouse \
  hephaestus
```

## Local Development Setup

### Quick Start

Use the provided setup script for a bulletproof local environment:

```bash
./scripts/setup-dev-env.sh
```

This script:

- Validates Python 3.12+ is installed
- Installs uv if not present
- Syncs dependencies from uv.lock
- Validates all tools are available
- Installs pre-commit hooks
- Runs a quick validation test

### Manual Setup

If you prefer manual setup:

```bash
# 1. Ensure Python 3.12+ is installed
python3 --version

# 2. Install uv
curl -LsSf https://astral.sh/uv/install.sh | sh

# 3. Sync dependencies
uv sync --locked --extra dev --extra qa

# 4. Validate environment
uv run hephaestus --version
uv run pytest --version
uv run python -m ruff --version
uv run mypy --version

# 5. Run quality checks
uv run hephaestus guard-rails
```

## Troubleshooting

### Issue: "uv export failed with unknown option --group"

**Cause**: Using `--group` instead of `--extra` for optional-dependencies.

**Solution**: Use `--extra` for optional-dependencies:

```bash
# Correct
uv export --locked --format requirements-txt --extra dev --extra qa
```

### Issue: "Module not found" errors in CI

**Cause**: Dependencies not installed or environment not activated.

**Solution**: Ensure `uv sync` or offline install completed successfully. Check validation steps.

### Issue: "Wheelhouse verification failed"

**Cause**: macOS resource fork artifacts present in wheelhouse.

**Solution**: Run sanitization:

```bash
uv run python -m hephaestus.cli wheelhouse sanitize wheelhouse
```

### Issue: "Failed to install" on macOS with AppleDouble files

**Cause**: macOS creates AppleDouble files (`._*`) during package installation, which are not listed in wheel RECORD files.

**Solution**: The `scripts/setup-dev-env.sh` script now automatically handles this. For manual setup on macOS:

```bash
# Set environment variables
export UV_LINK_MODE=copy
export COPYFILE_DISABLE=1

# Clean existing cache and venv
rm -rf ~/.cache/uv
rm -rf .venv

# Sync dependencies
uv sync --locked --extra dev --extra qa
```

See the [troubleshooting guide](troubleshooting.md#macos-appledoubleresource-fork-installation-errors) for more details.

### Issue: "Python version mismatch in offline install"

**Cause**: Wheelhouse built with different Python version than offline runner.

**Solution**: Ensure both jobs use the same Python version and OS/arch:

```yaml
build-wheelhouse:
  runs-on: ubuntu-24.04
  # ...

ci-offline:
  runs-on: ubuntu-24.04 # Must match!
  # ...
```

### Issue: "Test failures in ephemeral runners"

**Cause**: Missing dependencies or environment issues.

**Solution**:

1. Check validation step output
2. Verify uv.lock is committed and up-to-date
3. Ensure all extras are specified in export command
4. Check CI logs for specific errors

## Maintenance

### Updating Dependencies

```bash
# Update dependencies
uv lock --upgrade

# Sync environment
uv sync --locked --extra dev --extra qa

# Run quality checks
uv run hephaestus guard-rails

# Commit updated lock file
git add uv.lock
git commit -m "chore: update dependencies"
```

### Regenerating Wheelhouse

Wheelhouses are built automatically in CI, but you can build locally:

```bash
# Export requirements
uv export --locked --format requirements-txt \
  --extra dev --extra qa \
  --all-extras \
  -o requirements.txt

# Build wheelhouse
pip wheel -r requirements.txt -w wheelhouse
uv build --wheel
cp dist/*.whl wheelhouse/

# Sanitize and verify
uv run python -m hephaestus.cli wheelhouse sanitize wheelhouse
uv run python -m hephaestus.cli wheelhouse verify wheelhouse
```

## References

- [uv Documentation](https://docs.astral.sh/uv/)
- [setup-uv Action](https://github.com/astral-sh/setup-uv)
- [pip wheel](https://pip.pypa.io/en/stable/cli/pip_wheel/)
- [GitHub Actions Artifacts](https://docs.github.com/actions/using-workflows/storing-workflow-data-as-artifacts)
- [Hephaestus Quality Gates](quality-gates.md)

## Summary

The Hephaestus CI pipeline provides:

✅ **Bulletproof dependency management** through dual online/offline paths  
✅ **Reproducible builds** using uv.lock and wheelhouses  
✅ **Comprehensive validation** at every step  
✅ **Clear error messages** for quick debugging  
✅ **Portable workflows** that work in restricted environments  
✅ **Fast feedback** through parallel job execution  
✅ **Developer-friendly** setup scripts and documentation

By following these practices, ephemeral runners will always have reliable access to all required dependencies, ensuring consistent and reproducible CI/CD runs.
