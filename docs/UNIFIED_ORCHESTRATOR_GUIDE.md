# Unified Orchestrator Guide

## Overview

The Hephaestus Unified Orchestrator (`hephaestus-orchestrator.sh`) is an intelligent, context-aware automation tool that unifies all validation and setup operations into a single, seamless workflow.

## Key Benefits

### 🧠 Context-Aware Intelligence

- Caches validation results to avoid redundant checks
- Detects what actually needs to run based on environment changes
- Maintains state between runs for smart decision-making

### ⚡ Performance Optimized

- **Fast Mode**: Uses cached validations (10x faster for frequent runs)
- Skip recently validated checks automatically
- Configurable cache durations for each check type

### 🔗 Unified Workflow

- Runs all validation and setup scripts in optimal order
- Handles dependencies automatically
- Single command replaces multiple manual steps

### 🔒 Production-Ready

- File locking prevents concurrent execution conflicts
- Automatic stale lock detection and cleanup
- Log rotation (keeps last 20 logs)
- Disk space checking before operations
- Comprehensive error handling

## Usage

### Basic Commands

```bash
# First-time setup (runs all checks and fixes everything)
./scripts/hephaestus-orchestrator.sh

# Fast mode (uses cached validations)
./scripts/hephaestus-orchestrator.sh --fast

# Skip quality checks (for rapid iteration)
./scripts/hephaestus-orchestrator.sh --fast --skip-tests

# Dry-run mode
DRY_RUN=1 ./scripts/hephaestus-orchestrator.sh

# Interactive mode
INTERACTIVE=1 ./scripts/hephaestus-orchestrator.sh

# Get help
./scripts/hephaestus-orchestrator.sh --help
```

### Recommended Workflows

#### First Clone

```bash
# Complete setup with all validations
./scripts/hephaestus-orchestrator.sh
```

#### During Development (Run Frequently)

```bash
# Fast, skips tests, uses cache
./scripts/hephaestus-orchestrator.sh --fast --skip-tests
```

#### After Adding a Dependency

```bash
# Fast mode automatically detects lockfile changes
./scripts/hephaestus-orchestrator.sh --fast
```

#### Before Commit

```bash
# Full validation with quality checks
./scripts/hephaestus-orchestrator.sh --fast
```

#### Before Pull Request

```bash
# Complete validation (no cache)
./scripts/hephaestus-orchestrator.sh
```

## Orchestration Phases

### Phase 1: Environment Validation

- Python version check (≥3.12)
- UV package manager installation
- Basic environment setup

**Cache Duration**: 1 hour

### Phase 2: Dependency Orchestration

- Lockfile sync status
- Virtual environment existence
- Dependency synchronization
- Auto-remediation of issues

**Cache Duration**: 5-30 minutes (depending on check)

### Phase 3: Code Quality Validation

- Fast mode: Ruff linting only
- Full mode: All quality gates
- Skippable with `--skip-tests`

**Cache Duration**: 10 minutes

### Phase 4: Platform-Specific Validation

- macOS setup checks (if on macOS)
- Platform-specific configurations

**Cache Duration**: 1 hour

## Configuration

### Environment Variables

| Variable          | Default | Description                       |
| ----------------- | ------- | --------------------------------- |
| `AUTO_REMEDIATE`  | 1       | Enable automatic fixes            |
| `DRY_RUN`         | 0       | Show actions without executing    |
| `INTERACTIVE`     | 0       | Prompt before each change         |
| `PERSIST_CONFIG`  | 0       | Persist settings to shell profile |
| `FAST_MODE`       | 0       | Use cached validations            |
| `SKIP_TESTS`      | 0       | Skip quality checks               |
| `LOG_REMEDIATION` | 1       | Enable logging                    |

### Examples

```bash
# Dry-run with fast mode
DRY_RUN=1 FAST_MODE=1 ./scripts/hephaestus-orchestrator.sh

# Interactive with persistence
INTERACTIVE=1 PERSIST_CONFIG=1 ./scripts/hephaestus-orchestrator.sh

# Minimal validation (fastest)
FAST_MODE=1 SKIP_TESTS=1 ./scripts/hephaestus-orchestrator.sh
```

## Cache System

### Cache Durations

| Check Type          | Default Cache | Rationale                 |
| ------------------- | ------------- | ------------------------- |
| Python version      | 1 hour        | Rarely changes            |
| UV installation     | 1 hour        | Rarely changes            |
| Virtual environment | 10 minutes    | May be deleted during dev |
| Lockfile sync       | 5 minutes     | Changes with dependencies |
| Dependency sync     | 30 minutes    | Expensive operation       |
| Quality checks      | 10 minutes    | Fast to run again         |
| macOS setup         | 1 hour        | Platform-specific, stable |

### Cache Location

- **State file**: `~/.hephaestus/state.json`
- **Log files**: `~/.hephaestus/logs/orchestrator-*.log`

### Cache Management

```bash
# View current state
cat ~/.hephaestus/state.json

# Clear cache (force full validation)
rm ~/.hephaestus/state.json

# View logs
ls -lh ~/.hephaestus/logs/

# Clean old logs (automatic after 20 logs)
rm ~/.hephaestus/logs/orchestrator-*.log
```

## Concurrent Execution Safety

### File Locking

The orchestrator uses file locking to prevent conflicts:

```
~/.hephaestus/orchestrator.lock
```

Features:

- Automatically detects stale locks
- Waits up to 30 seconds for other instances
- Cleans up locks on exit (including crashes)

### Multiple Instances

If you try to run multiple instances:

```bash
# Terminal 1
./scripts/hephaestus-orchestrator.sh

# Terminal 2
./scripts/hephaestus-orchestrator.sh
# Output: "Another orchestrator instance is running (PID 12345), waiting..."
```

## Log Management

### Automatic Log Rotation

- Keeps last 20 log files automatically
- Older logs deleted on each run
- No manual cleanup required

### Log Format

```
[YYYY-MM-DD HH:MM:SS] LEVEL: Message
```

**Levels:**

- `HEADER`: Major phase transitions
- `SECTION`: Sub-phase starts
- `STATUS`: Operation in progress
- `SUCCESS`: Operation succeeded
- `ERROR`: Operation failed
- `WARNING`: Issue detected
- `INFO`: Informational message
- `SKIP`: Check skipped due to cache
- `LOCK_ACQUIRED`: Concurrency management
- `LOCK_RELEASED`: Concurrency management
- `STATE_SAVED`: Cache persisted
- `CACHE_HIT`: Using cached result
- `LOG_ROTATION`: Old logs removed

### Viewing Logs

```bash
# View latest log
cat ~/.hephaestus/logs/orchestrator-*.log | tail -100

# Search for errors
grep ERROR ~/.hephaestus/logs/orchestrator-*.log

# View all operations
grep -E "STATUS|SUCCESS|ERROR" ~/.hephaestus/logs/orchestrator-*.log
```

## Performance Comparison

### Without Orchestrator

```bash
# Manual process (5-10 minutes)
./scripts/validate-dependency-orchestration.sh
./scripts/validate_quality_gates.py
./scripts/run_actionlint.sh
./scripts/validate-macos-setup.sh  # if on macOS
```

### With Orchestrator (First Run)

```bash
# Unified process (3-5 minutes)
./scripts/hephaestus-orchestrator.sh
```

### With Orchestrator (Fast Mode)

```bash
# Cached validation (5-15 seconds)
./scripts/hephaestus-orchestrator.sh --fast --skip-tests
```

**Speedup**: ~20-40x faster for frequent runs!

## Troubleshooting

### Lock File Issues

**Problem**: Script hangs waiting for lock

**Solution**: Clean stale locks manually

```bash
rm ~/.hephaestus/orchestrator.lock
./scripts/hephaestus-orchestrator.sh
```

### Cache Issues

**Problem**: Validation seems stale

**Solution**: Clear cache and run full validation

```bash
rm ~/.hephaestus/state.json
./scripts/hephaestus-orchestrator.sh
```

### Log Directory Full

**Problem**: Too many logs

**Solution**: Logs auto-rotate, but can manually clean

```bash
rm ~/.hephaestus/logs/orchestrator-*.log
```

### Disk Space Errors

**Problem**: "Insufficient disk space" error

**Solution**: Free up disk space (need at least 1GB)

```bash
# Clean Python caches
find . -type d -name __pycache__ -exec rm -rf {} +

# Clean build artifacts
rm -rf dist/ build/ *.egg-info

# Clean logs
rm ~/.hephaestus/logs/orchestrator-*.log
```

## Integration Examples

### Git Pre-Commit Hook

```bash
#!/bin/bash
# .git/hooks/pre-commit
./scripts/hephaestus-orchestrator.sh --fast --skip-tests
```

### CI/CD Pipeline

```yaml
# .github/workflows/ci.yml
- name: Validate Environment
  run: |
    ./scripts/hephaestus-orchestrator.sh
  env:
    FAST_MODE: "1"
    SKIP_TESTS: "0"
```

### Development Alias

```bash
# Add to ~/.zshrc or ~/.bashrc
alias hephaestus-dev='cd /path/to/repo && ./scripts/hephaestus-orchestrator.sh --fast --skip-tests'
alias hephaestus-check='cd /path/to/repo && ./scripts/hephaestus-orchestrator.sh --fast'
```

### VS Code Task

```json
{
  "label": "Hephaestus: Validate",
  "type": "shell",
  "command": "./scripts/hephaestus-orchestrator.sh --fast --skip-tests",
  "problemMatcher": [],
  "presentation": {
    "reveal": "always",
    "panel": "dedicated"
  }
}
```

## Advanced Usage

### Custom Cache Durations

Edit the script and modify cache duration parameters in `should_run_check()` calls:

```bash
# Example: Increase Python check cache to 4 hours
if should_run_check "Python version" "last_python_check" 14400; then
```

### Selective Phase Execution

The orchestrator runs all phases by default. To skip phases, modify the `main()` function or use flags:

```bash
# Skip quality checks
SKIP_TESTS=1 ./scripts/hephaestus-orchestrator.sh
```

### Debug Mode

View detailed execution with logging enabled:

```bash
LOG_REMEDIATION=1 ./scripts/hephaestus-orchestrator.sh
tail -f ~/.hephaestus/logs/orchestrator-*.log
```

## Best Practices

### ✅ Do

1. **Use fast mode for frequent runs** - Saves time during development
2. **Run full validation before PR** - Ensures nothing is missed
3. **Check logs after auto-remediation** - Understand what changed
4. **Clear cache if environment changes** - When switching branches or major updates
5. **Use `--skip-tests` during active development** - Faster iteration

### ❌ Don't

1. **Don't disable auto-remediation without reason** - It's the core feature
2. **Don't run multiple instances manually** - Use the built-in locking
3. **Don't ignore warnings** - They indicate potential issues
4. **Don't delete state.json during operation** - Can cause inconsistencies
5. **Don't skip disk space checks** - Can cause hard-to-debug failures

## Comparison with Individual Scripts

| Aspect            | Individual Scripts | Unified Orchestrator    |
| ----------------- | ------------------ | ----------------------- |
| Setup Time        | 5-10 minutes       | 3-5 minutes (first run) |
| Validation Time   | 5-10 minutes       | 5-15 seconds (cached)   |
| Commands Needed   | 3-5 separate       | 1 unified               |
| State Management  | None               | Intelligent caching     |
| Concurrent Safe   | No                 | Yes (file locking)      |
| Log Rotation      | Manual             | Automatic               |
| Disk Space Check  | No                 | Automatic               |
| Context Awareness | None               | Full                    |

## Future Enhancements

Planned improvements:

- [ ] Parallel phase execution where safe
- [ ] Webhook notifications on completion
- [ ] JSON output mode for CI integration
- [ ] Custom phase configuration file
- [ ] Rollback capability
- [ ] Performance metrics dashboard

## See Also

- [scripts/README.md](../scripts/README.md) - Individual script documentation
- [GAP_ANALYSIS.md](../GAP_ANALYSIS.md) - Edge cases and mitigations
- [docs/SCRIPT_CONFIGURATION_GUIDE.md](SCRIPT_CONFIGURATION_GUIDE.md) - Detailed configuration guide
