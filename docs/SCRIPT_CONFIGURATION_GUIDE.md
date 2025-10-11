# Script Configuration Guide

This guide provides quick reference for all configuration flags available in Hephaestus validation and setup scripts.

## Quick Start

### Most Common Use Cases

```bash
# 1. First-time setup (auto-fix everything)
./scripts/validate-dependency-orchestration.sh

# 2. See what would be fixed without changing anything
DRY_RUN=1 ./scripts/validate-dependency-orchestration.sh

# 3. Interactive mode (approve each change)
INTERACTIVE=1 ./scripts/validate-dependency-orchestration.sh

# 4. Make changes persistent across shell sessions
PERSIST_CONFIG=1 ./scripts/validate-dependency-orchestration.sh

# 5. Validation only (no auto-fixes)
AUTO_REMEDIATE=0 ./scripts/validate-dependency-orchestration.sh
```

## Configuration Flags Reference

### validate-dependency-orchestration.sh

| Flag               | Default | Description                     | Use When                           |
| ------------------ | ------- | ------------------------------- | ---------------------------------- |
| `AUTO_REMEDIATE`   | 1       | Automatically fix issues        | You want hands-free setup          |
| `DRY_RUN`          | 0       | Show actions without doing them | Testing or preview mode            |
| `INTERACTIVE`      | 0       | Prompt before each change       | You want control over each action  |
| `PERSIST_CONFIG`   | 0       | Add env vars to shell profile   | You want permanent configuration   |
| `LOG_REMEDIATION`  | 1       | Log all actions to file         | You want audit trail (recommended) |
| `PRE_FLIGHT_CHECK` | 0       | Run health checks first         | You want to validate system state  |

### bump_version.sh

| Flag        | Default | Description                            | Use When             |
| ----------- | ------- | -------------------------------------- | -------------------- |
| `AUTO_LOCK` | 1       | Regenerate lockfile after version bump | Normal version bumps |

## Usage Examples

### Example 1: Conservative First-Time Setup

For users who want to see what will happen before making changes:

```bash
# Step 1: Preview changes
DRY_RUN=1 ./scripts/validate-dependency-orchestration.sh

# Step 2: Apply changes with confirmation
INTERACTIVE=1 ./scripts/validate-dependency-orchestration.sh

# Step 3: Make configuration persistent
PERSIST_CONFIG=1 ./scripts/validate-dependency-orchestration.sh
```

### Example 2: Automated CI/CD

For continuous integration environments:

```bash
# No interaction, no logging to disk
AUTO_REMEDIATE=1 LOG_REMEDIATION=0 ./scripts/validate-dependency-orchestration.sh
```

### Example 3: Troubleshooting

When debugging issues:

```bash
# Enable all checks and logging
PRE_FLIGHT_CHECK=1 LOG_REMEDIATION=1 ./scripts/validate-dependency-orchestration.sh

# Check the log file
cat ~/.hephaestus/logs/remediation-*.log
```

### Example 4: macOS Setup with Persistent Configuration

For macOS users who want permanent environment variable setup:

```bash
# Set environment variables and persist to shell profile
PERSIST_CONFIG=1 ./scripts/validate-dependency-orchestration.sh

# Verify variables are in profile
grep -E "COPYFILE_DISABLE|UV_LINK_MODE" ~/.zshrc  # or ~/.bashrc
```

### Example 5: Multiple Flags Combined

```bash
# Dry-run with interactive prompts (useful for learning)
DRY_RUN=1 INTERACTIVE=1 ./scripts/validate-dependency-orchestration.sh

# Full setup with persistence and logging
INTERACTIVE=1 PERSIST_CONFIG=1 LOG_REMEDIATION=1 ./scripts/validate-dependency-orchestration.sh

# Paranoid mode (see everything, approve everything, log everything)
DRY_RUN=1 INTERACTIVE=1 LOG_REMEDIATION=1 PRE_FLIGHT_CHECK=1 ./scripts/validate-dependency-orchestration.sh
```

## Flag Combinations Guide

### Recommended Combinations

#### 🟢 For Beginners

```bash
INTERACTIVE=1 ./scripts/validate-dependency-orchestration.sh
```

> See what's happening and approve each step

#### 🟢 For Experienced Users

```bash
./scripts/validate-dependency-orchestration.sh
```

> Default auto-remediation, works out of the box

#### 🟢 For Paranoid Users

```bash
INTERACTIVE=1 DRY_RUN=1 ./scripts/validate-dependency-orchestration.sh
```

> See what would happen, approve before actual run

#### 🟢 For CI/CD

```bash
AUTO_REMEDIATE=1 LOG_REMEDIATION=0 ./scripts/validate-dependency-orchestration.sh
```

> Automated, no logs to clean up

#### 🟢 For Production Setup

```bash
PERSIST_CONFIG=1 LOG_REMEDIATION=1 ./scripts/validate-dependency-orchestration.sh
```

> Make it permanent, keep audit trail

### Discouraged Combinations

#### 🔴 Don't Do This

```bash
AUTO_REMEDIATE=0 DRY_RUN=1
```

> Pointless: nothing will be done or shown

```bash
DRY_RUN=1 PERSIST_CONFIG=1
```

> Conflicting: dry-run won't persist anything

```bash
INTERACTIVE=0 AUTO_REMEDIATE=0
```

> Pointless: just validation with no action

## Log Files

### Location

```bash
~/.hephaestus/logs/remediation-YYYYMMDD-HHMMSS.log
```

### Viewing Logs

```bash
# View latest log
cat ~/.hephaestus/logs/remediation-*.log | tail -50

# View all logs
ls -lh ~/.hephaestus/logs/

# Search logs
grep "REMEDIATE" ~/.hephaestus/logs/remediation-*.log

# Clean old logs (keep last 10)
cd ~/.hephaestus/logs && ls -t remediation-*.log | tail -n +11 | xargs rm -f
```

### Log Format

```text
[YYYY-MM-DD HH:MM:SS] LEVEL: Message
```

**Levels:**

- `STATUS`: Informational message
- `SUCCESS`: Operation succeeded
- `WARNING`: Issue detected
- `ERROR`: Operation failed
- `REMEDIATE`: Auto-fix applied
- `DRY-RUN`: Would execute (dry-run mode)
- `CONFIRMED`: User approved (interactive mode)
- `SKIPPED`: User declined (interactive mode)
- `PRE_FLIGHT`: Health check result
- `ENV_PERSIST`: Environment variable persisted

## Environment Variables for Shell Profiles

### What Gets Added

When using `PERSIST_CONFIG=1`, these variables are added to your shell profile:

**For macOS:**

```bash
# Added by Hephaestus dependency orchestration validator
export COPYFILE_DISABLE=1
export UV_LINK_MODE=copy
```

**For all platforms:**

- Only variables that are missing are added
- Existing variables are not duplicated
- Variables are appended to the end of the file
- Clear comments identify Hephaestus additions

### Shell Profile Detection

The script automatically detects:

- `.zshrc` for zsh users
- `.bashrc` for bash users
- Falls back to `$SHELL` environment variable

### Manual Addition

If auto-detection fails, add manually:

```bash
# For zsh
echo 'export COPYFILE_DISABLE=1' >> ~/.zshrc
echo 'export UV_LINK_MODE=copy' >> ~/.zshrc

# For bash
echo 'export COPYFILE_DISABLE=1' >> ~/.bashrc
echo 'export UV_LINK_MODE=copy' >> ~/.bashrc
```

## Troubleshooting

### Issue: Script hangs during pre-flight check

**Solution:** Disable pre-flight checks (they're off by default)

```bash
PRE_FLIGHT_CHECK=0 ./scripts/validate-dependency-orchestration.sh
```

### Issue: Don't want logs created

**Solution:** Disable logging

```bash
LOG_REMEDIATION=0 ./scripts/validate-dependency-orchestration.sh
```

### Issue: Want to undo shell profile changes

**Solution:** Edit your profile manually

```bash
# Remove Hephaestus additions
nano ~/.zshrc  # or ~/.bashrc
# Delete the lines added by Hephaestus
```

### Issue: Want to see what changed

**Solution:** Check the log file

```bash
cat ~/.hephaestus/logs/remediation-*.log
```

### Issue: Auto-remediation not working

**Solution:** Check if it's disabled

```bash
# Make sure AUTO_REMEDIATE is 1
AUTO_REMEDIATE=1 ./scripts/validate-dependency-orchestration.sh
```

## Advanced Usage

### Custom Log Location

```bash
# Set custom log directory
LOG_DIR=/tmp/hephaestus-logs LOG_REMEDIATION=1 ./scripts/validate-dependency-orchestration.sh
```

### Chain Commands

```bash
# Preview, then execute if approved
DRY_RUN=1 ./scripts/validate-dependency-orchestration.sh && \
INTERACTIVE=1 ./scripts/validate-dependency-orchestration.sh
```

### Script in Background

```bash
# Run with logging, check logs later
LOG_REMEDIATION=1 ./scripts/validate-dependency-orchestration.sh &
tail -f ~/.hephaestus/logs/remediation-*.log
```

## Best Practices

### ✅ Do

1. **First time:** Run with `DRY_RUN=1` to see what will happen
2. **Production:** Use `PERSIST_CONFIG=1` to make settings permanent
3. **Keep logs:** Default `LOG_REMEDIATION=1` provides audit trail
4. **Review logs:** Check logs after auto-remediation
5. **Test changes:** Verify setup after running script

### ❌ Don't

1. Don't run with `sudo` unless specifically needed
2. Don't disable logging in production environments
3. Don't use `PRE_FLIGHT_CHECK=1` without testing first
4. Don't combine conflicting flags (e.g., `DRY_RUN=1 PERSIST_CONFIG=1`)
5. Don't ignore warnings - review and address them

## See Also

- [scripts/README.md](../scripts/README.md) - Full script documentation
- [GAP_ANALYSIS.md](../GAP_ANALYSIS.md) - Edge cases and recommendations
- [IMPLEMENTATION_SUMMARY.md](../IMPLEMENTATION_SUMMARY.md) - Implementation details
