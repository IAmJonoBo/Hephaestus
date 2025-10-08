# Testing Guide

This guide explains the testing philosophy, structure, and best practices for Hephaestus.

## Overview

Hephaestus maintains high test coverage (≥85%) with comprehensive test suites covering:
- CLI commands and workflows
- Core functionality (cleanup, release, analytics)
- Edge cases and error conditions
- Integration patterns

## Test Structure

```
tests/
├── test_cli.py                  # CLI command tests
├── test_cleanup.py              # Cleanup safety and functionality
├── test_release.py              # Release verification and security
├── test_analytics.py            # Ranking strategies and adapters
├── test_schema.py               # Schema export and validation
├── test_drift.py                # Drift detection and remediation
├── test_logging.py              # Structured logging
├── test_toolbox.py              # Toolbox utilities
├── test_planning.py             # Planning module
├── test_telemetry.py            # Telemetry events
└── test_lint_nested_decorators.py  # Nested decorator linting
```

## Running Tests

### All Tests

```bash
# Using pytest directly
pytest

# With coverage report
pytest --cov=src/hephaestus --cov-report=term-missing

# Generate XML coverage report (for CI)
pytest --cov=src/hephaestus --cov-report=xml
```

### Specific Test Files

```bash
# Single file
pytest tests/test_cli.py

# Multiple files
pytest tests/test_cli.py tests/test_cleanup.py

# Verbose output
pytest tests/test_cli.py -v

# Show print statements
pytest tests/test_cli.py -s
```

### Specific Tests

```bash
# Single test function
pytest tests/test_cli.py::test_cleanup_command

# Test class
pytest tests/test_cli.py::TestCleanupCommand

# Pattern matching
pytest -k "cleanup"  # Run all tests with "cleanup" in name
pytest -k "not slow"  # Exclude slow tests
```

### Test with Random Order

```bash
# Verify test independence
pytest --random-order

# With specific seed for reproducibility
pytest --random-order-seed=12345
```

## Test Categories

### Unit Tests

Test individual functions and classes in isolation.

**Example:**
```python
def test_is_dangerous_path():
    """Test dangerous path detection."""
    assert is_dangerous_path(Path("/"))
    assert is_dangerous_path(Path("/home"))
    assert not is_dangerous_path(Path("/home/user/project"))
```

### Integration Tests

Test interactions between components.

**Example:**
```python
def test_guard_rails_command_flow(runner):
    """Test guard-rails runs full pipeline."""
    result = runner.invoke(app, ["guard-rails"])
    assert result.exit_code == 0
    assert "cleanup" in result.stdout.lower()
    assert "lint" in result.stdout.lower()
```

### CLI Tests

Test command-line interface using Typer's test runner.

**Example:**
```python
from typer.testing import CliRunner
from hephaestus.cli import app

def test_cleanup_dry_run():
    """Test cleanup in dry-run mode."""
    runner = CliRunner()
    result = runner.invoke(app, ["cleanup", "--dry-run"])
    assert result.exit_code == 0
    assert "would delete" in result.stdout.lower()
```

### Regression Tests

Prevent known bugs from recurring.

**Example:**
```python
def test_guard_rails_available_immediately():
    """Regression test for guard-rails availability bug.
    
    Ensures guard-rails command is registered at module scope,
    not nested inside cleanup function.
    """
    from hephaestus.cli import app
    command_names = [cmd.name for cmd in app.registered_commands]
    assert "guard-rails" in command_names
```

## Testing Patterns

### Fixtures

Use pytest fixtures for common setup:

```python
import pytest
from pathlib import Path
from typer.testing import CliRunner

@pytest.fixture
def runner():
    """Provide a CLI test runner."""
    return CliRunner()

@pytest.fixture
def temp_workspace(tmp_path):
    """Create a temporary workspace with test files."""
    workspace = tmp_path / "workspace"
    workspace.mkdir()
    (workspace / "test.py").write_text("print('hello')")
    return workspace

def test_cleanup_removes_pycache(runner, temp_workspace):
    """Test cleanup removes __pycache__ directories."""
    pycache = temp_workspace / "__pycache__"
    pycache.mkdir()
    
    result = runner.invoke(app, ["cleanup", str(temp_workspace)])
    assert result.exit_code == 0
    assert not pycache.exists()
```

### Mocking

Mock external dependencies:

```python
from unittest.mock import Mock, patch

def test_release_download_retry(monkeypatch):
    """Test release download retries on failure."""
    mock_response = Mock()
    mock_response.status_code = 500
    
    with patch("requests.get", return_value=mock_response):
        with pytest.raises(ReleaseError):
            download_asset("http://example.com/asset.tar.gz")
```

### Parametrized Tests

Test multiple scenarios efficiently:

```python
@pytest.mark.parametrize("path,expected", [
    ("/", True),
    ("/home", True),
    ("/usr", True),
    ("/tmp", False),
    ("/home/user/project", False),
])
def test_dangerous_path_detection(path, expected):
    """Test various paths for danger detection."""
    assert is_dangerous_path(Path(path)) == expected
```

### Temporary Files

Use pytest's tmp_path fixture:

```python
def test_cleanup_manifest_generation(tmp_path):
    """Test cleanup generates audit manifest."""
    manifest_path = tmp_path / "manifest.json"
    
    options = CleanupOptions(
        root=tmp_path,
        manifest_path=manifest_path,
    )
    
    run_cleanup(options)
    
    assert manifest_path.exists()
    manifest = json.loads(manifest_path.read_text())
    assert "deleted_paths" in manifest
```

## Coverage Guidelines

### Minimum Coverage

- **Overall**: ≥85% (enforced in CI)
- **New Code**: ≥90% (aim high for new features)
- **Critical Paths**: 100% (security, safety, data loss prevention)

### Check Coverage

```bash
# Terminal report
pytest --cov=src/hephaestus --cov-report=term-missing

# HTML report (more detailed)
pytest --cov=src/hephaestus --cov-report=html
open htmlcov/index.html

# Show uncovered lines
pytest --cov=src/hephaestus --cov-report=term-missing | grep "MISS"
```

### Coverage Exceptions

Some code may be hard to test:
- Platform-specific code (use `# pragma: no cover`)
- Error handlers for rare conditions
- Defensive programming checks

```python
if sys.platform == "win32":  # pragma: no cover
    # Windows-specific code
    pass
```

## Best Practices

### 1. Test Independence

Tests should not depend on execution order:

```python
# BAD: Depends on previous test
def test_create_file():
    Path("test.txt").write_text("data")

def test_read_file():  # Assumes test_create_file ran first
    assert Path("test.txt").read_text() == "data"

# GOOD: Self-contained
def test_read_file(tmp_path):
    test_file = tmp_path / "test.txt"
    test_file.write_text("data")
    assert test_file.read_text() == "data"
```

### 2. Clear Test Names

Use descriptive names that explain what's being tested:

```python
# BAD
def test_cleanup():
    ...

# GOOD
def test_cleanup_refuses_dangerous_paths():
    ...
```

### 3. Arrange-Act-Assert Pattern

Structure tests clearly:

```python
def test_ranking_strategy_risk_weighted():
    # Arrange
    modules = [
        AnalyticsModule(path="a.py", churn=100, coverage=0.5, uncovered_lines=50),
        AnalyticsModule(path="b.py", churn=50, coverage=0.8, uncovered_lines=20),
    ]
    
    # Act
    ranked = rank_by_risk_weighted(modules)
    
    # Assert
    assert ranked[0].path == "a.py"  # Higher risk should be first
    assert ranked[0].score > ranked[1].score
```

### 4. Test Error Conditions

Don't just test happy paths:

```python
def test_cleanup_invalid_root():
    """Test cleanup fails gracefully with invalid root."""
    with pytest.raises(ValueError, match="Invalid root path"):
        run_cleanup(CleanupOptions(root=Path("/nonexistent")))
```

### 5. Use Assertions Effectively

```python
# Be specific
assert result.exit_code == 0  # Not just assert result
assert "error" not in output.lower()

# Use pytest's rich assertions
assert actual == expected  # Shows diff on failure

# Check multiple conditions
assert all([
    result.exit_code == 0,
    "success" in output,
    not error_log.exists(),
])
```

### 6. Mock Sparingly

Prefer real implementations when possible:

```python
# PREFER: Use real filesystem with tmp_path
def test_cleanup_deletes_files(tmp_path):
    test_file = tmp_path / "test.py"
    test_file.write_text("data")
    run_cleanup(CleanupOptions(root=tmp_path))
    assert not test_file.exists()

# MOCK: Only for external services
def test_download_handles_network_error(monkeypatch):
    with patch("requests.get", side_effect=ConnectionError()):
        with pytest.raises(ReleaseError):
            download_asset("http://example.com/file")
```

## Debugging Tests

### Run with More Output

```bash
# Show print statements
pytest -s

# Verbose output
pytest -v

# Show all output including passed tests
pytest -vv

# Show local variables on failure
pytest -l
```

### Debug Individual Tests

```bash
# Drop into debugger on failure
pytest --pdb

# Drop into debugger at start of test
pytest --trace
```

### Using Python Debugger

```python
def test_complex_logic():
    result = compute_something()
    
    import pdb; pdb.set_trace()  # Pause here
    
    assert result == expected
```

## CI Integration

Tests run automatically in CI on:
- Pull requests
- Pushes to main
- Python 3.12 and 3.13 matrices

### CI Configuration

See `.github/workflows/ci.yml`:

```yaml
- name: Run tests with coverage
  run: |
    pytest --cov=src/hephaestus --cov-report=xml --cov-report=term

- name: Upload coverage to artifacts
  uses: actions/upload-artifact@v4
  with:
    name: coverage-report
    path: coverage.xml
```

### Coverage Enforcement

Coverage threshold enforced in `pyproject.toml`:

```toml
[tool.coverage.report]
fail_under = 85
show_missing = true
```

## Writing New Tests

### Checklist for New Features

When adding a new feature:

- [ ] Unit tests for core logic
- [ ] Integration tests for component interaction
- [ ] CLI tests for user-facing commands
- [ ] Edge case tests (empty input, invalid values, etc.)
- [ ] Error condition tests
- [ ] Regression tests for known bugs
- [ ] Update test documentation if needed

### Example: Testing a New Command

```python
# tests/test_cli.py

def test_new_command_help(runner):
    """Test new-command shows help text."""
    result = runner.invoke(app, ["new-command", "--help"])
    assert result.exit_code == 0
    assert "Usage:" in result.stdout

def test_new_command_basic_usage(runner, tmp_path):
    """Test new-command basic functionality."""
    result = runner.invoke(app, ["new-command", str(tmp_path)])
    assert result.exit_code == 0
    assert "success" in result.stdout.lower()

def test_new_command_invalid_input(runner):
    """Test new-command handles invalid input."""
    result = runner.invoke(app, ["new-command", "/invalid/path"])
    assert result.exit_code != 0
    assert "error" in result.stdout.lower()

@pytest.mark.parametrize("option,expected", [
    ("--verbose", "verbose output"),
    ("--quiet", "minimal output"),
])
def test_new_command_options(runner, tmp_path, option, expected):
    """Test new-command option handling."""
    result = runner.invoke(app, ["new-command", str(tmp_path), option])
    assert result.exit_code == 0
    assert expected in result.stdout.lower()
```

## Troubleshooting

### Tests Fail Locally but Pass in CI

- Check Python version: `python --version`
- Check for test order dependencies: `pytest --random-order`
- Check for uncommitted changes affecting tests
- Verify dependencies are installed: `pip list`

### Flaky Tests

Tests that pass sometimes and fail other times:

- Check for timing issues (use explicit waits, not sleeps)
- Check for order dependencies (use `pytest-randomly`)
- Check for shared state between tests
- Check for race conditions in concurrent code

### Coverage Drop

If coverage drops unexpectedly:

```bash
# See which files have low coverage
pytest --cov=src/hephaestus --cov-report=term-missing

# Generate detailed HTML report
pytest --cov=src/hephaestus --cov-report=html
open htmlcov/index.html
```

Add tests for uncovered lines shown in the report.

## Resources

- [pytest documentation](https://docs.pytest.org/)
- [pytest-cov documentation](https://pytest-cov.readthedocs.io/)
- [pytest-randomly documentation](https://github.com/pytest-dev/pytest-randomly)
- [Typer testing](https://typer.tiangolo.com/tutorial/testing/)

## Related Documentation

- [Quality Gates Guide](quality-gates.md)
- [Contributing Guide](../../CONTRIBUTING.md)
- [CI Configuration](../../.github/workflows/ci.yml)

---

**Remember:** Tests are documentation that runs. Write tests that explain what the code should do.
