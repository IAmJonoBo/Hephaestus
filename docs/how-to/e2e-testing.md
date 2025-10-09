# E2E Testing Guide

This guide covers end-to-end (E2E) testing for the Hephaestus development environment setup and workflows.

## Overview

E2E tests validate the complete development workflow from environment setup through quality gates, ensuring:

- Setup scripts work correctly across platforms
- Virtual environments are preserved during cleanup
- Quality gates run successfully
- Dependency updates (via Renovate) don't break the setup

## Running E2E Tests

### Full E2E Test Suite

```bash
# Run all E2E tests
uv run pytest tests/test_e2e_setup.py -v

# Run with coverage
uv run pytest tests/test_e2e_setup.py --cov=src/hephaestus
```

### Individual Test Categories

```bash
# Setup script validation
uv run pytest tests/test_e2e_setup.py::test_setup_dev_env_script_exists -v
uv run pytest tests/test_e2e_setup.py::test_setup_dev_env_script_syntax -v

# Cleanup preservation tests
uv run pytest tests/test_e2e_setup.py::test_guard_rails_preserves_site_packages -v
uv run pytest tests/test_e2e_setup.py::test_cleanup_with_venv_in_search_roots -v

# Renovate compatibility tests
uv run pytest tests/test_e2e_setup.py::test_renovate_config_exists -v
uv run pytest tests/test_e2e_setup.py::test_uv_lock_exists_for_renovate -v
uv run pytest tests/test_e2e_setup.py::test_setup_script_handles_dependency_updates -v
```

## Manual E2E Validation

### 1. Fresh Environment Setup

Test the complete setup from scratch:

```bash
# Remove existing virtual environment
rm -rf .venv

# Run setup script
bash scripts/setup-dev-env.sh

# Verify Python version
python3 --version

# Verify uv is installed
uv --version

# Verify dependencies are installed
uv run python -c "import typer, rich, pydantic; print('Dependencies OK')"
```

### 2. Guard Rails Pipeline

Test the complete quality pipeline:

```bash
# Run guard rails with all checks
uv run hephaestus guard-rails

# Verify cleanup preserved site-packages
ls -la .venv/lib/python*/site-packages/ | head -10

# Verify tools still work after cleanup
uv run yamllint --version
uv run mypy --version
uv run pytest --version
```

### 3. Renovate Simulation

Simulate a Renovate dependency update:

```bash
# Update a dependency version in pyproject.toml
# Then regenerate lock file
uv lock

# Verify setup script handles the change
bash scripts/setup-dev-env.sh

# Verify guard rails still work
uv run hephaestus guard-rails
```

## E2E Test Coverage

### Setup Script Tests

| Test                                           | Purpose                                | Status |
| ---------------------------------------------- | -------------------------------------- | ------ |
| `test_setup_dev_env_script_exists`             | Verify script exists and is executable | ✅     |
| `test_setup_dev_env_script_syntax`             | Validate bash syntax                   | ✅     |
| `test_setup_script_handles_dependency_updates` | Verify Renovate compatibility          | ✅     |

### Cleanup Preservation Tests

| Test                                       | Purpose                                 | Status |
| ------------------------------------------ | --------------------------------------- | ------ |
| `test_guard_rails_preserves_site_packages` | Verify site-packages not removed        | ✅     |
| `test_cleanup_with_venv_in_search_roots`   | Test cleanup with .venv in search roots | ✅     |
| `test_guard_rails_yamllint_works`          | Verify tools work after cleanup         | ✅     |

### Renovate Compatibility Tests

| Test                                           | Purpose                                 | Status |
| ---------------------------------------------- | --------------------------------------- | ------ |
| `test_renovate_config_exists`                  | Verify Renovate configuration           | ✅     |
| `test_uv_lock_exists_for_renovate`             | Verify lock file for dependency updates | ✅     |
| `test_setup_script_handles_dependency_updates` | Test dependency update workflow         | ✅     |

## Known Issues & Workarounds

### Issue: Pre-commit Hook Failures

**Symptom**: Pre-commit hooks fail during git commit with pyupgrade errors.

**Workaround**:

```bash
# Commit without hooks
git commit --no-verify -m "Your message"

# Or update pre-commit
pre-commit autoupdate
```

### Issue: Cleanup Too Aggressive

**Symptom**: Virtual environment breaks after cleanup.

**Solution**: Fixed in commit 143d47a. The cleanup now preserves site-packages in .venv.

**Verification**:

```bash
# Run cleanup
uv run hephaestus cleanup --deep-clean

# Verify site-packages still exists
ls -la .venv/lib/python*/site-packages/
```

### Issue: Yamllint Config Path

**Symptom**: Yamllint fails with missing config file error.

**Solution**: Fixed in commit 143d47a. Removed hardcoded `.trunk/configs/.yamllint.yaml` path.

**Verification**:

```bash
# Yamllint should use defaults
uv run yamllint --version
```

## CI/CD E2E Testing

### GitHub Actions E2E Workflow

The repository includes automated E2E testing in CI:

```yaml
# .github/workflows/e2e-tests.yml (proposed)
name: E2E Tests

on:
  push:
    branches: [main]
  pull_request:
    branches: [main]

jobs:
  e2e-setup:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v4
      - uses: actions/setup-python@v5
        with:
          python-version: "3.12"

      - name: Install uv
        run: curl -LsSf https://astral.sh/uv/install.sh | sh

      - name: Run setup script
        run: bash scripts/setup-dev-env.sh

      - name: Run guard rails
        run: uv run hephaestus guard-rails

      - name: Run E2E tests
        run: uv run pytest tests/test_e2e_setup.py -v
```

## Best Practices

### 1. Test Independence

E2E tests should be independent and idempotent:

```python
def test_something(tmp_path: Path) -> None:
    """Use tmp_path for isolated test environments."""
    test_repo = tmp_path / "repo"
    test_repo.mkdir()
    # ... test in isolation
```

### 2. Realistic Scenarios

Test real-world workflows:

```python
def test_renovate_pr_workflow(tmp_path: Path) -> None:
    """Simulate a complete Renovate PR workflow."""
    # 1. Create repo with dependencies
    # 2. Update lock file
    # 3. Run setup script
    # 4. Run guard rails
    # 5. Verify success
```

### 3. Platform Coverage

Test on multiple platforms when possible:

```python
@pytest.mark.skipif(
    platform.system() != "Darwin",
    reason="macOS-specific test"
)
def test_macos_specific_setup() -> None:
    """Test macOS-specific setup behavior."""
    # ...
```

### 4. Clear Assertions

Use descriptive assertion messages:

```python
assert site_packages.exists(), \
    "site-packages must be preserved after cleanup to avoid breaking venv"
```

## Troubleshooting

### Debug E2E Test Failures

1. **Run with verbose output**:

   ```bash
   uv run pytest tests/test_e2e_setup.py -vv -s
   ```

2. **Check logs**:

   ```bash
   # View cleanup audit logs
   cat .hephaestus/audit/cleanup-*.json | jq
   ```

3. **Inspect test artifacts**:

   ```bash
   # E2E tests use tmp_path, check pytest temp dirs
   ls -la /tmp/pytest-of-*/
   ```

4. **Run setup script manually**:
   ```bash
   # Add debug output
   bash -x scripts/setup-dev-env.sh 2>&1 | tee setup.log
   ```

### Common Failures

| Error                             | Cause                       | Solution                    |
| --------------------------------- | --------------------------- | --------------------------- |
| ModuleNotFoundError after cleanup | site-packages removed       | Fixed in v0.2.0+            |
| yamllint config not found         | Hardcoded config path       | Fixed in v0.2.0+            |
| Pre-commit hook failures          | Outdated hooks              | Run `pre-commit autoupdate` |
| uv.lock out of sync               | Dependency version mismatch | Run `uv lock`               |

## Related Documentation

- [Testing Guide](./testing.md) - General testing patterns
- [Quality Gates](./quality-gates.md) - Quality pipeline documentation
- [Troubleshooting](./troubleshooting.md) - General troubleshooting guide
- [Operating Safely](./operating-safely.md) - Safety and security practices

## References

- [E2E Test Suite](../../tests/test_e2e_setup.py)
- [Setup Script](../../scripts/setup-dev-env.sh)
- [Renovate Configuration](../../renovate.json)
