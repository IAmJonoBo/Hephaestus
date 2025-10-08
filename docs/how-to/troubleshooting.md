# Troubleshooting Guide

This guide helps you diagnose and fix common issues with Hephaestus.

## Quick Diagnostics

Start with these commands to identify issues:

```bash
# Check version
hephaestus --version

# Verify environment
hephaestus guard-rails --drift

# Run full quality checks
hephaestus guard-rails

# Check Python version
python3 --version  # Should be 3.12+

# List installed packages
pip list | grep -E "(hephaestus|ruff|mypy|pytest)"
```

## Common Issues

### Installation Issues

#### "hephaestus: command not found"

**Symptom:** Command not found when running `hephaestus`

**Causes:**

- Package not installed
- Installation directory not in PATH
- Virtual environment not activated

**Solutions:**

```bash
# Check if installed
pip show hephaestus

# If not installed, install it
pip install hephaestus
# or: pip install -e ".[dev,qa]"  # from source

# If installed but not in PATH, try:
python -m hephaestus --help

# Activate virtual environment if using one
source .venv/bin/activate  # Linux/macOS
# or: .venv\Scripts\activate  # Windows
```

#### "Module not found" errors

**Symptom:** `ModuleNotFoundError: No module named 'X'`

**Cause:** Missing dependencies

**Solution:**

```bash
# Reinstall with all extras
pip install -e ".[dev,qa]"

# Or sync with uv
uv sync --extra dev --extra qa

# Verify installation
pip list
```

#### "uv: command not found"

**Symptom:** `bash: uv: command not found`

**Cause:** uv package manager not installed

**Solutions:**

```bash
# Install uv
curl -LsSf https://astral.sh/uv/install.sh | sh

# Or use pip
pip install uv

# Or use the repo without uv
pip install -e ".[dev,qa]"
python -m hephaestus --help
```

### Guard-Rails Issues

#### Guard-rails fails immediately

**Symptom:** `hephaestus guard-rails` fails without running checks

**Diagnostic:**

```bash
# Run with verbose output
hephaestus guard-rails -v

# Check individual components
pytest
ruff check .
mypy src tests
```

**Common causes:**

- Syntax errors in code
- Missing dependencies
- Corrupted cache files

**Solutions:**

```bash
# Clean caches
hephaestus cleanup --deep-clean

# Reinstall dependencies
pip install --force-reinstall -e ".[dev,qa]"

# Fix syntax errors shown in output
```

#### "pip-audit failed" in guard-rails

**Symptom:** `pip-audit --strict` fails

**Causes:**

- SSL certificate issues (common in containers)
- Known vulnerabilities in dependencies
- Network connectivity issues

**Solutions:**

This is often non-blocking and expected in containerized environments:

```bash
# Run pip-audit separately to see details
pip-audit --strict --ignore-vuln GHSA-4xh5-x5gv-qwph

# If SSL issues, this is expected in containers
# Guard-rails will continue with other checks

# For actual vulnerabilities, update dependencies
pip install --upgrade <package>
```

#### Tests fail during guard-rails

**Symptom:** pytest fails with errors

**Diagnostic:**

```bash
# Run tests with verbose output
pytest -v

# Run specific failing test
pytest tests/test_file.py::test_name -v

# Check test dependencies
pytest --version
python --version
```

**Solutions:**

```bash
# Check for tool drift
hephaestus guard-rails --drift

# Sync dependencies
uv sync --extra dev --extra qa

# Clean and retry
hephaestus cleanup --deep-clean
pytest
```

#### Type checking fails

**Symptom:** `mypy src tests` shows errors

**Diagnostic:**

```bash
# Run mypy with verbose output
mypy src tests --show-error-codes

# Check specific file
mypy src/hephaestus/file.py
```

**Solutions:**

```bash
# Install type stubs
pip install types-PyYAML types-requests

# Check mypy configuration
cat pyproject.toml | grep -A 10 "\[tool.mypy\]"

# Fix reported type errors in code
```

### Cleanup Issues

#### "Refusing to clean dangerous path"

**Symptom:** Cleanup refuses to proceed

**Cause:** Safety feature protecting system paths

**This is expected behavior!** Cleanup protects these paths:

- `/`, `/home`, `/usr`, `/etc`, `/var`
- `/bin`, `/sbin`, `/lib`, `/opt`
- `/boot`, `/root`, `/sys`, `/proc`, `/dev`

**Solutions:**

```bash
# Use a safe project directory
cd /path/to/your/project
hephaestus cleanup

# Or specify safe root explicitly
hephaestus cleanup --root /home/user/myproject
```

#### Cleanup asks for confirmation repeatedly

**Symptom:** Cleanup prompts "Type CONFIRM to proceed"

**Cause:** Trying to clean paths outside detected root

**Solutions:**

```bash
# Clean from git repository root (auto-detected)
cd /path/to/repo
hephaestus cleanup

# Auto-confirm (skip prompts)
hephaestus cleanup --yes

# See preview first
hephaestus cleanup --dry-run
```

#### Files not being deleted

**Symptom:** Cleanup runs but files remain

**Diagnostic:**

```bash
# Use dry-run to see what would be deleted
hephaestus cleanup --dry-run

# Check if files are in excluded paths
hephaestus cleanup --deep-clean
```

**Possible causes:**

- Files are in `.git/` (excluded by default)
- Files are in `.venv/site-packages` (protected)
- Permission errors

**Solutions:**

```bash
# Include git directory (dangerous!)
hephaestus cleanup --include-git

# Check file permissions
ls -la /path/to/file

# Run with verbose output to see skip reasons
# (Future enhancement)
```

### Drift Detection Issues

#### "Tool version drift detected"

**Symptom:** `hephaestus guard-rails --drift` shows mismatches

**This is informational, not an error!**

**Solution:**

```bash
# Follow the remediation commands shown
uv sync --extra dev --extra qa

# Or update individual tools
pip install --upgrade ruff==X.Y.Z

# Verify fix
hephaestus guard-rails --drift
```

#### "Tool not installed"

**Symptom:** Drift detection shows missing tools

**Solution:**

```bash
# Install all dev tools
pip install -e ".[dev,qa]"

# Verify installation
which ruff mypy pytest
```

### Release Issues

#### "Failed to download release"

**Symptom:** `hephaestus release install` fails

**Diagnostic:**

```bash
# Check network connectivity
curl -I https://api.github.com

# Check if release exists
gh release view v0.2.0 --repo IAmJonoBo/Hephaestus

# Try with verbose output
hephaestus release install --repository IAmJonoBo/Hephaestus --tag v0.2.0 -v
```

**Solutions:**

```bash
# Check GitHub API rate limits
curl https://api.github.com/rate_limit

# If rate limited, wait or authenticate
export GITHUB_TOKEN=your_token

# Try different tag/version
hephaestus release install --repository IAmJonoBo/Hephaestus --tag v0.1.0
```

#### "Checksum verification failed"

**Symptom:** Release install fails checksum validation

**Cause:** Corrupted download or tampered file

**Solutions:**

```bash
# Try downloading again
hephaestus release install --repository IAmJonoBo/Hephaestus --tag v0.2.0

# Check release assets are intact
gh release view v0.2.0 --repo IAmJonoBo/Hephaestus --json assets

# Skip checksum (not recommended, only for testing)
hephaestus release install --no-verify-checksum
```

### Analytics Issues

#### "No analytics data found"

**Symptom:** `hephaestus tools refactor rankings` shows error

**Cause:** Analytics sources not configured

**Solution:**

Configure in `pyproject.toml`:

```toml
[tool.hephaestus.analytics]
churn_file = "analytics/churn.json"
coverage_file = "coverage.xml"
embeddings_file = "analytics/embeddings.json"
```

Or use external config:

```bash
hephaestus tools refactor rankings --config /path/to/config.yaml
```

#### "Invalid analytics format"

**Symptom:** Rankings fail with parsing errors

**Cause:** Analytics files in wrong format

**Solution:**

Ensure analytics files match expected format:

```json
// churn.json
{
  "modules": [
    {"path": "src/module.py", "churn": 100}
  ]
}

// embeddings.json
{
  "embeddings": [
    {"path": "src/module.py", "embedding": [0.1, 0.2, ...]}
  ]
}
```

Coverage file should be standard `coverage.xml` format from pytest-cov.

### Schema Export Issues

#### "Schema export fails"

**Symptom:** `hephaestus schema` shows errors

**Diagnostic:**

```bash
# Run with verbose output
hephaestus schema -v

# Check if all commands are registered
hephaestus --help
```

**Solution:**

```bash
# Reinstall package
pip install --force-reinstall -e .

# Verify schema structure
hephaestus schema | python -m json.tool
```

## Environment Issues

### "Works on my machine"

**Symptom:** Tests pass locally but fail in CI, or vice versa

**Diagnostic:**

```bash
# Compare environments
python --version
pip list

# Check for tool drift
hephaestus guard-rails --drift

# Run tests with randomization
pytest --random-order
```

**Solutions:**

```bash
# Sync to exact versions
uv sync --extra dev --extra qa

# Clean all caches
hephaestus cleanup --deep-clean
rm -rf .pytest_cache .mypy_cache .ruff_cache

# Verify Python version matches CI
# CI uses Python 3.12 and 3.13
```

### Virtual environment conflicts

**Symptom:** Strange import errors or version conflicts

**Solution:**

```bash
# Delete and recreate venv
deactivate  # if activated
rm -rf .venv
python3 -m venv .venv
source .venv/bin/activate
pip install -e ".[dev,qa]"
```

### Cache corruption

**Symptom:** Inexplicable errors that persist

**Solution:**

```bash
# Clean all caches
hephaestus cleanup --deep-clean

# Clean Python bytecode
find . -type d -name __pycache__ -exec rm -rf {} +
find . -type f -name "*.pyc" -delete

# Clean tool caches
rm -rf .pytest_cache .mypy_cache .ruff_cache

# Rebuild
pip install --force-reinstall -e ".[dev,qa]"
```

## Performance Issues

### Guard-rails is slow

**Expected behavior:** Guard-rails runs many checks and may take 1-5 minutes.

**To speed up:**

```bash
# Skip formatting (saves time)
hephaestus guard-rails --no-format

# Run individual checks
pytest  # Just tests
ruff check .  # Just linting
```

### Tests are slow

**Solution:**

```bash
# Run in parallel (if you have pytest-xdist)
pytest -n auto

# Run only fast tests
pytest -m "not slow"

# Skip integration tests
pytest -m "not integration"
```

## CI/CD Issues

### CI fails but local passes

**Diagnostic:**

1. Check CI logs for specific error
2. Compare Python versions
3. Check for network-dependent tests
4. Check for timing-dependent tests

**Solutions:**

```bash
# Replicate CI environment locally
python3.12 -m venv .venv-ci
source .venv-ci/bin/activate
pip install -e ".[dev,qa]"
pytest

# Check for test order dependencies
pytest --random-order --random-order-seed=12345

# Check for timing issues
pytest -v  # Look for flaky tests
```

### Coverage drops in CI

**Cause:** Tests not running or new uncovered code

**Solution:**

```bash
# Check which tests ran
pytest --collect-only

# Generate coverage report locally
pytest --cov=src/hephaestus --cov-report=html
open htmlcov/index.html

# Add tests for uncovered code
```

## Getting More Help

### Enable Debug Logging

```bash
# Set log level
export HEPHAESTUS_LOG_LEVEL=DEBUG

# Use JSON logging for parsing
export HEPHAESTUS_LOG_FORMAT=json

# Run command
hephaestus guard-rails
```

### Collect Diagnostic Information

When reporting issues, include:

```bash
# Version information
hephaestus --version
python --version
pip --version

# Environment information
pip list
hephaestus guard-rails --drift

# Error output
hephaestus guard-rails 2>&1 | tee error.log
```

### Check Known Issues

- Review [GitHub Issues](https://github.com/IAmJonoBo/Hephaestus/issues)
- Check [CHANGELOG.md](../../CHANGELOG.md) for recent changes
- Review [Next_Steps.md](../../Next_Steps.md) for known limitations

### Report a Bug

If you've found a bug:

1. Check if it's already reported
2. Collect diagnostic information
3. Create a minimal reproducible example
4. Open a GitHub issue with:
   - Description of the problem
   - Steps to reproduce
   - Expected behavior
   - Actual behavior
   - Environment details
   - Error messages/logs

### Security Issues

For security vulnerabilities, **do not open a public issue**. Instead:

- Follow [SECURITY.md](../../SECURITY.md) disclosure process
- Email: opensource@hephaestus.dev
- Include details and impact assessment

## Quick Reference

### Diagnostic Commands

```bash
# Check everything
hephaestus guard-rails
hephaestus guard-rails --drift

# Individual checks
pytest                                          # Tests
ruff check .                                    # Linting
ruff format --check .                           # Formatting
mypy src tests                                  # Type checking
python3 scripts/lint_nested_decorators.py       # Architecture
pip-audit --strict                              # Security
```

### Reset Commands

```bash
# Clean workspace
hephaestus cleanup --deep-clean

# Reset virtual environment
deactivate
rm -rf .venv
python3 -m venv .venv
source .venv/bin/activate
pip install -e ".[dev,qa]"

# Clear all caches
rm -rf .pytest_cache .mypy_cache .ruff_cache __pycache__
```

### Common Fixes

```bash
# Fix imports
pip install -e ".[dev,qa]"

# Fix drift
uv sync --extra dev --extra qa

# Fix permissions
chmod +x scripts/*.sh

# Fix line endings (if Windows)
dos2unix scripts/*.sh
```

## Related Documentation

- [Quality Gates Guide](quality-gates.md)
- [Operating Safely Guide](operating-safely.md)
- [Testing Guide](testing.md)
- [Release Process Guide](release-process.md)
- [Contributing Guide](../../CONTRIBUTING.md)

---

**Still stuck?** Open a [GitHub Discussion](https://github.com/IAmJonoBo/Hephaestus/discussions) or issue!
