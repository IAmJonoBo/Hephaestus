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
3. Ruff format
4. Mypy
5. Pytest
6. pip-audit

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
