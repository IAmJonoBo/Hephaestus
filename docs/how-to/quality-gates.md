# Quality Gate Validation

This guide explains how to use Hephaestus's comprehensive quality gate validation system to ensure frontier-level code quality.

## Overview

The Hephaestus project enforces strict quality standards through automated checks that run locally and in CI. These checks catch issues early and ensure consistent quality across all contributions.

## Quick Start

### Validate All Quality Gates

Run all quality checks with a single command:

```bash
python3 scripts/validate_quality_gates.py
```

This runs:

- Pytest with coverage ≥85%
- Ruff linting
- Ruff formatting checks
- YAML linting with yamllint
- Mypy type checking
- Nested decorator linting
- Workflow validation with actionlint
- Build artifact generation
- Security auditing (when available)

### Use Guard Rails Command

The `guard-rails` command provides an integrated workflow with **enhanced visual feedback**:

```bash
uv run hephaestus guard-rails
```

**New Features:**

- 🎨 **Progress indicators** showing completion percentage
- ⏱️ **Time elapsed** tracking for the entire pipeline
- 📊 **Step counters** (e.g., `[2/9] Running ruff lint...`)
- ✅ **Visual status** with color-coded messages
- 🔄 **Real-time updates** during long-running operations

This performs:

1. Deep cleanup of build artifacts (with progress bar)
2. Ruff linting with auto-fix
3. Import sorting (ruff isort)
4. Code formatting (ruff format)
5. YAML linting with yamllint (using .yamllint config)
6. Workflow validation with actionlint
7. Mypy type checking
8. Full test suite with coverage
9. Security audit with pip-audit

## Individual Quality Gates

### Testing

Run the test suite with coverage:

```bash
uv run pytest
```

Requirements:

- All tests must pass
- Coverage must be ≥85%
- No warnings allowed (treated as errors)

### Linting

Check code style:

```bash
uv run ruff check .
```

Auto-sort imports:

```bash
uv run ruff check --select I --fix .
```

Auto-fix other lint issues:

```bash
uv run ruff check --fix .
```

Ruff's import sorter (`--select I`) is chained into every formatting run; keep it handy before running
`ruff format` (below) to avoid import drift.

### Formatting

Check formatting:

```bash
uv run ruff format --check .
```

Apply formatting:

```bash
uv run ruff check --select I --fix .
uv run ruff format .
```

### YAML Linting

Lint YAML files for consistency and correctness:

```bash
uv run yamllint -c .yamllint .github/ .pre-commit-config.yaml hephaestus-toolkit/
```

Requirements:

- Uses custom configuration from `.yamllint` (in project root)
- Checks workflow files, configuration files, and documentation
- Enforces document start markers (`---`)
- Allows GitHub Actions `'on':` syntax for triggers
- Line length relaxed to 120 characters for readability

### Type Checking

Verify type annotations:

```bash
uv run mypy src tests
```

Requirements:

- Strict mode enabled
- All functions must have type annotations
- No `Any` types unless explicitly justified

### Nested Decorator Check

Prevent command registration bugs:

```bash
python3 scripts/lint_nested_decorators.py src/hephaestus
```

This ensures Typer commands are defined at module scope, not nested inside other functions. See the red team findings in `Next_Steps.md` for context on the guard-rails availability bug this prevents.

### Workflow Validation (actionlint)

Validate GitHub Actions workflows (required in guard-rails):

```bash
bash scripts/run_actionlint.sh
```

This check:

- Automatically installs actionlint if not present
- Validates workflow syntax and structure
- Checks for deprecated actions
- Reports shellcheck issues in workflow scripts

The script will download actionlint on first run and is now part of the default guard-rails pipeline.

### Security Audit

Audit dependencies for vulnerabilities:

```bash
uv run pip-audit --strict --ignore-vuln GHSA-4xh5-x5gv-qwph
```

Note: This check may fail in containerized environments without proper SSL certificate chains.

### Build Artifacts

Verify the package builds correctly:

```bash
uv run uv build
```

Or with standard tooling:

```bash
python3 -m build
```

## CI Integration

All quality gates run automatically in CI on:

- Pull requests
- Pushes to main

The CI pipeline matrix tests against:

- Python 3.12
- Python 3.13

## Pre-commit Hooks

Install pre-commit hooks for local validation:

```bash
uv run pre-commit install
```

This runs on every commit:

- Ruff linting and formatting
- Black formatting
- Pyupgrade modernization
- Mypy type checking
- pip-audit security scanning
- Nested decorator linting
- Hephaestus cleanup

## Quality Standards

### Frontier-Level Requirements

- **Zero Tolerance**: No linting errors, type errors, or test failures
- **High Coverage**: ≥85% test coverage maintained
- **Security First**: All dependencies audited, vulnerabilities addressed
- **Type Safety**: Full type coverage with strict Mypy
- **Documentation**: All features documented following Diátaxis

### Progressive Enhancement

While all gates are enforced, some are optional in certain environments:

- **pip-audit**: May fail in containers without SSL certificates (non-blocking)
- **Nested decorator check**: Critical - blocks merges if violations found

## Troubleshooting

### Coverage Below Threshold

```bash
# See which lines need coverage
uv run pytest --cov-report=term-missing

# Generate HTML report for detailed analysis
uv run pytest --cov-report=html
open htmlcov/index.html
```

### Type Check Failures

```bash
# Check specific file
uv run mypy src/hephaestus/file.py

# Show error codes for targeted fixes
uv run mypy --show-error-codes src
```

### Nested Decorator Violations

If the linter reports nested decorators:

1. Move the command function to module scope
2. Remove it from inside any parent function
3. Ensure it's defined at the top level of the module

Example fix:

```python
# ❌ Bad - nested inside function
def parent_function():
    @app.command()
    def nested_command():
        pass

# ✅ Good - at module scope
@app.command()
def module_level_command():
    pass
```

## Best Practices

1. **Run locally first**: Always validate before pushing
2. **Fix incrementally**: Address issues as they appear
3. **Watch test order**: Use `pytest-randomly` to catch order dependencies
4. **Review coverage**: Don't just meet the threshold, aim for meaningful tests
5. **Update docs**: Document new features as you build them

## Related Documentation

- [Operating Safely](operating-safely.md): Safety features and best practices
- [Architecture](../explanation/architecture.md): Component design and boundaries
- [Frontier Analysis](../explanation/frontier-red-team-gap-analysis.md): Security assessment
- [Pre-release Checklist](../../docs/pre-release-checklist.md): Release validation steps
