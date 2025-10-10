---
title: "Operating Safely with Hephaestus"
description: "┏━━━━━━━━━━━━┳━━━━━━━━━━┳━━━━━━━━━━━━━━━┳━━━━━━━━┓ ┃ Tool ┃ Expected ┃ Actual ┃ Status ┃ ┡━━━━━━━━━━━━╇━━━━━━━━━━╇━━━━━━━━━━━━━━━╇━━━━━━━━┩ │ ruff │ 0.14.0 │..."
---

┏━━━━━━━━━━━━┳━━━━━━━━━━┳━━━━━━━━━━━━━━━┳━━━━━━━━┓
┃ Tool ┃ Expected ┃ Actual ┃ Status ┃
┡━━━━━━━━━━━━╇━━━━━━━━━━╇━━━━━━━━━━━━━━━╇━━━━━━━━┩
│ ruff │ 0.14.0 │ 0.14.5 │ OK │
│ black │ 25.9.0 │ 25.8.0 │ Drift │
│ mypy │ 1.18.2 │ Not installed │ Missing│
│ pip-audit │ 2.9.0 │ 2.9.0 │ OK │
└────────────┴──────────┴───────────────┴────────┘

## Remediation commands

This guide explains safety constraints, guard-rail workflows, and secure operational practices when using the Hephaestus toolkit.

## Cleanup Safety

The `hephaestus cleanup` command removes files and directories from your workspace. Understanding its safety features is critical to avoiding accidental data loss.

### Built-in Safety Features

1. **Mandatory Preview**: Every invocation runs a dry-run first and renders a Rich table preview so you can inspect pending deletions before anything touches disk.

2. **Typed Confirmation Outside the Root**: If cleanup would touch paths outside the detected workspace root (e.g., `--extra-path /tmp`), the CLI pauses and requires you to type `CONFIRM` unless you pass `--yes` explicitly.

3. **Git Repository Detection**: By default, cleanup operates from the git repository root. If no git repository is detected, it uses the current working directory.

4. **Excluded Paths**: The `.git` directory is excluded by default unless you explicitly pass `--include-git`.

5. **Virtual Environment Protection**: When cleaning build artifacts, the command preserves `.venv/site-packages` unless you're cleaning the virtual environment itself with `--include-poetry-env`.

````bash

### Dangerous Operations to Avoid

⚠️ **Never use these patterns:**

```bash
# DON'T: Clean the root filesystem
hephaestus cleanup /

# DON'T: Clean your home directory
hephaestus cleanup ~
hephaestus cleanup /home/username

# DON'T: Use wildcards or shell expansion with --extra-path
hephaestus cleanup --extra-path "*"

### Safe Usage Patterns

✅ **Recommended patterns:**

```bash
# Clean current repository
hephaestus cleanup

# Clean specific subdirectory within the repo
hephaestus cleanup ./subproject

# Deep clean with all options
hephaestus cleanup --deep-clean

# Clean build artifacts only
hephaestus cleanup --build-artifacts

# Dry-run: Preview what would be removed without deleting anything
hephaestus cleanup --dry-run --deep-clean
````

### Extra Paths

The `--extra-path` flag adds directories to the cleanup scope. **Always verify paths before using this flag:**

```bash
# Safe: Relative path within repository
hephaestus cleanup --extra-path ./legacy/dist

# Safe: Absolute path within repository
hephaestus cleanup --extra-path /home/user/projects/myrepo/temp

# UNSAFE: Path outside repository
hephaestus cleanup --extra-path /tmp
```

### Future Safety Enhancements

Recently delivered features include previews, typed confirmations, and audit manifests. Remaining roadmap items:

- **Sigstore-backed manifests**: Attach signed attestations to cleanup manifests for tamper detection.
- **Undo checkpoints**: Offer reversible trash-bin moves for supported platforms instead of hard deletions.

## Guard Rails Workflow

The `hephaestus guard-rails` command runs a comprehensive quality and security pipeline. It's designed to catch issues before they reach production.

### What Guard Rails Does

The guard-rails command executes these steps in order:

1. **Deep Cleanup**: Removes all build artifacts, caches, and macOS metadata
2. **Lint**: Checks code style and common errors with `ruff check`
3. **Format**: Auto-formats code with `ruff format` (skip with `--no-format`)
4. **Type Check**: Validates type annotations with `mypy`
5. **Test**: Runs the pytest suite with coverage reporting
6. **Security Audit**: Scans dependencies for known vulnerabilities with `pip-audit`

### When to Use Guard Rails

**Before committing:**

```bash
hephaestus guard-rails
```

**Before opening a PR:**

```bash
hephaestus guard-rails
```

**After pulling changes:**

```bash
hephaestus guard-rails
```

**Skip formatting (useful for reviewing changes):**

```bash
hephaestus guard-rails --no-format
```

**Check for tool version drift:**

```bash
hephaestus guard-rails --drift
```

## Tool Version Drift Detection

The `--drift` flag enables drift detection mode, which checks if your installed development tools match the versions specified in `pyproject.toml`.

**When to check for drift:**

- After setting up a new development environment
- When CI builds start failing locally
- Before reporting "works on my machine" issues
- After system updates or Python version changes

**Example output:**
│ ruff │ 0.14.0 │ 0.14.5 │ OK │
│ black │ 25.9.0 │ 25.8.0 │ Drift │
│ mypy │ 1.18.2 │ Not installed │ Missing│
│ pip-audit │ 2.9.0 │ 2.9.0 │ OK │
└────────────┴──────────┴───────────────┴────────┘

### Tool Drift Remediation

## Recommended: Use uv to sync dependencies

uv sync --extra dev --extra qa

## Or manually update individual tools

pip install --upgrade black>=25.9.0
pip install mypy>=1.18.2

```

**Drift detection rules:**

- **OK**: Installed version matches expected major.minor (patch differences ignored)
- **Drift**: Installed version differs in major or minor version
- **Missing**: Tool not installed in environment

The command exits with code 1 if any drift or missing tools are detected.

```

## Guard Rails in CI

The CI pipeline automatically runs guard rails on every push and pull request. Local execution ensures you catch issues before pushing.

## Troubleshooting Guard Rails

If guard rails fail:

1. **Lint failures**: Run `ruff check . --fix` to auto-fix issues
2. **Format failures**: Run `ruff format .` to format code
3. **Type failures**: Review mypy output and add/fix type annotations
4. **Test failures**: Run `pytest -v` for detailed test output
5. **Audit failures**: Review CVE details and update dependencies or add waivers

## Release Verification

When using `hephaestus release install`, follow these practices:

### Verify Release Source

```bash
# Always specify the repository explicitly
hephaestus release install --repository IAmJonoBo/Hephaestus
### Verify Release Source
# Pin to a specific tag for reproducibility
hephaestus release install --tag v0.1.0
```

## Network Security

The release command includes several security features:

- **HTTPS only**: All downloads use HTTPS
- **Timeouts**: Configurable timeouts prevent hanging (default: 30s)
- **Retries**: Automatic retry with exponential backoff (default: 3 attempts)
- **Checksum verification**: SHA-256 manifests are required unless you pass `--allow-unsigned`
- **Sigstore attestation**: Sigstore bundles are downloaded and validated automatically; use `--require-sigstore` to fail closed if an attestation is missing, `--sigstore-identity` to pin trusted identities, and `--sigstore-pattern` to override bundle discovery when repositories publish custom naming schemes
- **Token security**: Use environment variables for GitHub tokens

```bash
# Set token via environment variable
export GITHUB_TOKEN=ghp_your_token_here
hephaestus release install

# Or pass it as an option
hephaestus release install --token ghp_your_token_here
```

## Future Verification Features

The following security enhancements are planned:

- **Sigstore transparency policy enforcement**: Record attestation metadata in audit logs and require identity policies per environment profile
- **Signed cleanup manifests**: Attach Sigstore attestations to cleanup JSON manifests for tamper detection
- **Automated attestation publication**: Backfill Sigstore bundles for historical releases and verify during CI before upload

## Secure Development Workflow

### Pre-commit Hooks

Install pre-commit hooks to catch issues early:

```bash
uv run pre-commit install
```

This automatically runs on every commit:

- Cleanup of macOS metadata
- Code formatting
- Linting
- Type checking
- Security audits

### Dependency Management

**Regular updates:**

```bash
# Check for outdated dependencies
pip list --outdated

# Run security audit
pip-audit --strict
```

**Review Dependabot PRs:**

- Always review dependency updates before merging
- Check changelogs for breaking changes
- Verify tests pass after updates

### Token Management

**GitHub Token Permissions:**

For `hephaestus release install`, use a fine-grained personal access token with these **read-only** permissions:

- **Contents**: Read access to download release assets
- **Metadata**: Read access (automatically included)

For classic tokens, use the minimal `public_repo` scope (or `repo` for private repositories).

**Best practices:**

- Store tokens in environment variables or password managers
- Use fine-grained GitHub tokens with minimal permissions
- Rotate tokens regularly (recommended: every 90 days)
- Never commit tokens to version control
- Set token expiration dates to limit exposure window

## CI/CD Security

**Secrets management:**

- Use GitHub Secrets for sensitive values
- Never log tokens or credentials
- Audit workflow permissions regularly

  ```bash
  hephaestus release install --tag v0.0.9
  ```

  1. **Stop**: Don't push compromised code
  2. **Identify the issue**: Review release notes and changelogs
  3. **Pin to last known good version**:

  ```bash
  hephaestus release install --tag v0.0.9
  ```

  4. **Report the issue**: Open a GitHub issue with details
  5. **Document learnings**: Update documentation and tests

## Release Revocation (Future)

The following rollback features are planned:

- Automated release deletion from GitHub
- Security advisory publication
- Coordinated disclosure timeline
- Rollback automation in CI

## Monitoring and Telemetry

### Current Logging

Hephaestus logs to stdout/stderr using Rich formatting. Key events are highlighted:

- **Green**: Successful operations
- **Yellow**: Warnings and skipped operations
- **Red**: Errors and failures
- **Cyan**: Informational messages

### Future Telemetry

Planned observability features:

- **Security**: Email [opensource@hephaestus.dev](mailto:opensource@hephaestus.dev) for security concerns
- **Community**: Check [existing issues and discussions](https://github.com/IAmJonoBo/Hephaestus/issues)
- **OpenTelemetry spans**: Distributed tracing for CLI operations
- **Anonymous metrics**: Aggregated usage statistics (opt-in)
- **Failure tracking**: Network errors, timeout counts, retry attempts

All telemetry will be:

- **Opt-in**: Disabled by default, enabled via environment flag
- **Privacy-preserving**: No sensitive data or PII
- **Transparent**: Full disclosure of what's collected

## Getting Help

- **Security**: Email [opensource@hephaestus.dev](mailto:opensource@hephaestus.dev) for security concerns

- **Community**: Check [existing issues and discussions](https://github.com/IAmJonoBo/Hephaestus/issues)

- **OpenTelemetry spans**: Distributed tracing for CLI operations
- **Anonymous metrics**: Aggregated usage statistics (opt-in)
- **Failure tracking**: Network errors, timeout counts, retry attempts

## Summary Checklist

Before running potentially destructive operations:

- [ ] Verify you're in the correct directory
- [ ] Review paths and arguments carefully
- [ ] Check for typos in path specifications
- [ ] Consider running without `--deep-clean` first
- [ ] Ensure critical work is committed to git
- **Security**: Email [opensource@hephaestus.dev](mailto:opensource@hephaestus.dev) for security concerns
- **Community**: Check [existing issues and discussions](https://github.com/IAmJonoBo/Hephaestus/issues)
  Remember: Hephaestus is a powerful tool. With power comes responsibility. Stay safe! 🛡️
