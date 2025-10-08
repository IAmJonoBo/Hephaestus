# Tutorial: Getting Started with Hephaestus

This tutorial walks through the minimum steps required to install the toolkit, explore the CLI, and
ship your first refactoring workflow using the bundled wheelhouse distribution.

## What You'll Learn

By the end of this tutorial, you'll know how to:
- Install and verify Hephaestus
- Run comprehensive quality checks with a single command
- Clean build artifacts safely
- Check for tool version drift
- Get data-driven refactoring recommendations
- Integrate Hephaestus with your development workflow

## 1. Prepare Your Environment

### Install Prerequisites

1. **Install uv** (recommended package manager):
   ```bash
   curl -LsSf https://astral.sh/uv/install.sh | sh
   ```
   Or use pip: `pip install uv`

2. **Python 3.12+** is required:
   ```bash
   python3 --version  # Should show 3.12 or higher
   ```

### Get Hephaestus

Choose one of these installation methods:

**Method A: Clone from Source (for development)**
```bash
git clone https://github.com/IAmJonoBo/Hephaestus.git
cd Hephaestus
uv sync --extra dev --extra qa
```

**Method B: Install Wheelhouse (for usage)**
```bash
# Install latest stable release
hephaestus release install --repository IAmJonoBo/Hephaestus

# Or install specific version
hephaestus release install --repository IAmJonoBo/Hephaestus --tag v0.2.0
```

**Method C: Direct pip install (from source)**
```bash
pip install -e ".[dev,qa]"
```

### Verify Installation

Check that Hephaestus is properly installed:

```bash
# Check version
hephaestus --version

# View available commands
hephaestus --help

# Verify your environment matches expected tool versions
hephaestus guard-rails --drift
```

If drift is detected, run the suggested remediation command:
```bash
uv sync --extra dev --extra qa
```

## 2. Explore the CLI

### View Available Commands

List the top-level commands and review built-in help:

```bash
hephaestus --help
```

You'll see these main command groups:
- **cleanup**: Scrub development cruft (build artifacts, caches)
- **guard-rails**: Run comprehensive quality pipeline
- **plan**: Generate refactoring plans
- **tools**: Access refactoring toolkit and QA utilities
- **release**: Install wheelhouse distributions
- **schema**: Export command schemas for AI integration

### Try Key Commands

**Check code quality** (most important command):
```bash
hephaestus guard-rails
```

This runs the full quality pipeline:
1. Deep cleanup of build artifacts
2. Lint code with ruff
3. Auto-format code
4. Type-check with mypy
5. Run tests with coverage
6. Audit dependencies for security issues

**Get refactoring recommendations**:
```bash
# View hotspots (frequently changed, low coverage areas)
hephaestus tools refactor hotspots --limit 5

# Get prioritized rankings (requires analytics data)
hephaestus tools refactor rankings --strategy risk_weighted --limit 10

# Quick QA profile
hephaestus tools qa profile quick
```

**Generate a refactoring plan**:
```bash
hephaestus plan
```

**Export command schemas for AI agents**:
```bash
hephaestus schema --output schemas.json
```

## 3. Clean Up Your Workspace

Before you start editing, remove local cruft so rollouts stay reproducible.

### Basic Cleanup

```bash
# Clean from current directory (or git root if detected)
hephaestus cleanup
```

This removes:
- Build artifacts (`dist/`, `build/`, `*.egg-info`)
- Python caches (`__pycache__`, `.pyc` files)
- Test caches (`.pytest_cache`)
- macOS metadata (`.DS_Store`)

### Deep Clean

For a more thorough cleanup including virtual environments and coverage reports:

```bash
hephaestus cleanup --deep-clean
```

### Preview Before Deleting

Always review what will be deleted:

```bash
# Dry-run mode (shows preview without deleting)
hephaestus cleanup --dry-run

# Or use interactive mode (default)
# You'll see a preview table and can confirm before proceeding
hephaestus cleanup
```

### Safety Features

Hephaestus cleanup includes multiple safety rails:

- **Automatic Preview**: Shows what will be deleted before proceeding
- **Dangerous Path Protection**: Refuses to clean `/`, `/home`, `/usr`, etc.
- **Virtual Environment Protection**: Preserves `.venv/site-packages` during build cleanup
- **Typed Confirmation**: Requires typing "CONFIRM" for out-of-root targets
- **Audit Manifests**: Optionally generates JSON manifests of deleted files

### Automate with Pre-commit Hooks

Install pre-commit hooks to automate cleanup and quality checks:

```bash
pre-commit install
```

This runs cleanup and quality gates automatically before each commit.

## 4. Run the Refactoring Toolkit

The toolkit ships advisory scripts you can customize for your repository.

### Scan for Hotspots

Hotspots are areas of code that change frequently and have low test coverage:

```bash
# Run the hotspot scanner
python hephaestus-toolkit/refactoring/scripts/scan_hotspots.py --limit 10
```

This analyzes your codebase and identifies:
- High-churn files (changed frequently)
- Low-coverage modules
- Complex functions needing refactoring

### Get Prioritized Rankings

If you have analytics data configured, use the ranking command:

```bash
# Risk-weighted rankings (default strategy)
hephaestus tools refactor rankings

# Focus on coverage gaps
hephaestus tools refactor rankings --strategy coverage_first --limit 10

# Focus on high-churn files
hephaestus tools refactor rankings --strategy churn_based

# Composite approach with embedding bonus
hephaestus tools refactor rankings --strategy composite
```

### Configure Analytics Data Sources

To use rankings, configure data sources in `pyproject.toml`:

```toml
[tool.hephaestus.analytics]
churn_file = "analytics/churn.json"
coverage_file = "coverage.xml"
embeddings_file = "analytics/embeddings.json"
```

Or use a separate config file:

```bash
hephaestus tools refactor rankings --config path/to/config.yaml
```

Review the generated report and copy any candidate issues into your backlog.

## 5. Validate Changes with Quality Gates

As you prototype a refactor, continuously validate your changes.

### Run Comprehensive Quality Checks

The guard-rails command is your one-stop validation:

```bash
hephaestus guard-rails
```

This runs all quality gates in order:
1. **Cleanup**: Removes build artifacts
2. **Lint**: Checks code style and errors (ruff)
3. **Format**: Auto-formats code (ruff format)
4. **Type Check**: Validates type annotations (mypy)
5. **Test**: Runs pytest with coverage reporting
6. **Security Audit**: Scans for vulnerabilities (pip-audit)

### Skip Formatting

If you want to review changes before auto-formatting:

```bash
hephaestus guard-rails --no-format
```

### Run Individual Quality Gates

You can also run specific checks:

```bash
# Tests with coverage
pytest

# Linting
ruff check .

# Type checking
mypy src tests

# Security audit
pip-audit --strict --ignore-vuln GHSA-4xh5-x5gv-qwph

# Architecture check (nested decorators)
python3 scripts/lint_nested_decorators.py src/hephaestus
```

### Coverage Threshold

Aim to keep total coverage above **85%** (the default gate enforced by CI):

```bash
# Check coverage
hephaestus tools qa coverage

# Run tests with coverage report
pytest --cov=src/hephaestus --cov-report=term-missing
```

### Validate All Gates at Once

Use the comprehensive validation script:

```bash
python3 scripts/validate_quality_gates.py
```

This provides categorized reporting of all quality standards.

## 6. Package and Share

When you're ready to share the toolkit with another repository:

### Build a Wheelhouse

1. Build the distribution:

   ```bash
   # Using uv (recommended)
   uv build
   
   # Or using standard tools
   python3 -m build
   ```

2. Create a wheelhouse archive:

   ```bash
   tar -czf hephaestus-wheelhouse.tar.gz dist/
   ```

3. Calculate checksums for verification:

   ```bash
   sha256sum dist/*.whl dist/*.tar.gz > SHA256SUMS
   ```

### Share with Others

**Option A: GitHub Release**
1. Upload the archive as a GitHub Release asset
2. Include the SHA256SUMS file
3. Users can install with:
   ```bash
   hephaestus release install --repository IAmJonoBo/Hephaestus --tag v0.2.0
   ```

**Option B: Direct Distribution**
1. Pass the archive directly to collaborators
2. They can extract and install:
   ```bash
   tar -xzf hephaestus-wheelhouse.tar.gz
   pip install dist/*.whl
   ```

### Security Best Practices

- Always include SHA-256 checksums
- Consider using Sigstore for attestation
- Verify checksums before installation:
  ```bash
  hephaestus release install --verify-checksum
  ```

## Next Steps

### Learn More

- **[Operating Safely Guide](../how-to/operating-safely.md)**: Understand safety features and best practices
- **[Quality Gates Guide](../how-to/quality-gates.md)**: Deep dive into quality validation
- **[AI Agent Integration](../how-to/ai-agent-integration.md)**: Integrate Hephaestus with AI assistants
- **[Architecture Overview](../explanation/architecture.md)**: Understand internal modules and design
- **[CLI Reference](../reference/cli.md)**: Complete command and option details

### Common Workflows

**Daily Development**:
```bash
# Check environment
hephaestus guard-rails --drift

# Make changes
# ... code ...

# Validate before commit
hephaestus guard-rails
git commit -am "Your changes"
```

**Preparing a Pull Request**:
```bash
hephaestus cleanup --deep-clean
hephaestus guard-rails
git push
```

**Responding to CI Failures**:
```bash
# Check for drift
hephaestus guard-rails --drift

# Sync if needed
uv sync --extra dev --extra qa

# Validate
hephaestus guard-rails
```

### Tips for Success

1. **Run guard-rails early and often** - Catch issues before they compound
2. **Use drift detection** - Prevent environment inconsistencies
3. **Preview before cleanup** - Always review what will be deleted
4. **Configure analytics** - Get the most value from rankings
5. **Install pre-commit hooks** - Automate quality checks
6. **Read safety guides** - Understand protections before using cleanup
7. **Export schemas for AI** - Enable AI assistant integration

### Get Help

- **Documentation**: Browse the `docs/` directory
- **GitHub Issues**: Report bugs or request features
- **Security Reports**: See [SECURITY.md](../../SECURITY.md)
- **Discussions**: Ask questions on GitHub Discussions

### Key Takeaways

✅ Hephaestus provides a comprehensive quality pipeline in a single command  
✅ Safety features protect against accidental data loss  
✅ AI-native design enables seamless integration with assistants  
✅ Data-driven recommendations help prioritize refactoring work  
✅ Frontier-level quality standards are automatically enforced

You're now ready to use Hephaestus to maintain high-quality codebases! 🔨
