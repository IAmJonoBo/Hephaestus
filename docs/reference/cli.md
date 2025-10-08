# CLI Reference

This reference documents the top-level `hephaestus` commands and their most important options. Run
`uv run hephaestus --help` for the canonical source of truth and subcommand details.

## Global Usage

```bash
uv run hephaestus [OPTIONS] COMMAND [ARGS]...
```

- `--log-format [text|json]`: Emit human-readable or JSON logs for automation pipelines.
- `--log-level [CRITICAL|ERROR|WARNING|INFO|DEBUG]`: Control verbosity for toolkit logs.
- `--run-id TEXT`: Attach a correlation identifier to every structured log event.
- `--install-completion`, `--show-completion`: Manage shell completions.
- `--help`: Display help text for any command.

## Commands

### `version`

Print the installed toolkit version.

### `schema`

Export command schemas for AI agent integration.

| Option            | Description                                   |
| ----------------- | --------------------------------------------- |
| `--output PATH`   | Write schemas to JSON file instead of stdout. |
| `--format [json]` | Output format for schemas (default: `json`).  |

Generates machine-readable schemas describing all CLI commands, their parameters, examples, and expected outputs. See [AI Agent Integration Guide](../how-to/ai-agent-integration.md) for usage patterns.

### `cleanup`

Scrub development cruft (macOS metadata, caches, build artefacts). Key options:

| Option              | Description                                                        |
| ------------------- | ------------------------------------------------------------------ |
| `--root PATH`       | Override the detected project root.                                |
| `--deep-clean`      | Enable all cleanup behaviours (equivalent to toggling every flag). |
| `--include-git`     | Remove files inside `.git` directories.                            |
| `--python-cache`    | Delete `__pycache__` directories and compiled bytecode.            |
| `--extra-path PATH` | Include additional directories to clean.                           |

### `plan`

Render the refactoring execution plan as a Rich table to share rollout status.

### `guard-rails`

Run the full guard-rail pipeline: cleanup, lint, format, typecheck, test, and audit.

| Option        | Description                                                 |
| ------------- | ----------------------------------------------------------- |
| `--no-format` | Skip the formatting step (useful during code review).       |
| `--drift`     | Check for tool version drift and show remediation commands. |

**Standard pipeline**:

1. Deep clean workspace
2. Lint with ruff
3. Format with ruff (unless `--no-format`)
4. Type check with mypy
5. Run tests with pytest
6. Security audit with pip-audit

**Drift detection mode** (`--drift`):

- Compares installed tool versions against `pyproject.toml`
- Reports missing or outdated tools
- Generates remediation commands (manual or via `uv sync`)
- Exits with code 1 if drift is detected

### `tools refactor hotspots`

List the highest churn modules. Options include:

- `--limit INTEGER`: Number of hotspots to display.
- `--config PATH`: Load alternate configuration.

### `tools refactor opportunities`

Summarise advisory refactor opportunities with estimated effort.

### `tools refactor rankings`

Rank modules by refactoring priority using analytics data. Requires analytics sources to be configured.

| Option                     | Description                                                |
| -------------------------- | ---------------------------------------------------------- | ----------- | ----------- | ------------------------------------------------------ |
| `--strategy [risk_weighted | coverage_first                                             | churn_based | composite]` | Ranking algorithm to apply (default: `risk_weighted`). |
| `--limit INTEGER`          | Maximum number of ranked modules to display (default: 20). |
| `--config PATH`            | Load alternate configuration.                              |

**Strategies:**

- `risk_weighted`: Balances coverage gaps, uncovered lines, and churn (recommended).
- `coverage_first`: Prioritizes modules with the largest coverage gaps.
- `churn_based`: Focuses on high-change-frequency modules.
- `composite`: Balanced approach with bonus for modules with embeddings.

### `tools qa profile NAME`

Display thresholds and switches for a specific QA profile (e.g., `quick`, `full`).

### `tools qa coverage`

Highlight uncovered lines and risk scores. Accepts `--config PATH` to override defaults.

### `release install`

Download and install a wheelhouse archive. Important options:

| Option                    | Description                                                                    |
| ------------------------- | ------------------------------------------------------------------------------ |
| `--repository OWNER/REPO` | Source repository for releases (default: `IAmJonoBo/Hephaestus`).              |
| `--tag TAG`               | Release tag to download (defaults to latest).                                  |
| `--asset-pattern GLOB`    | Glob pattern used to locate the wheelhouse asset.                              |
| `--destination PATH`      | Directory for downloaded archives (defaults to the platform cache).            |
| `--manifest-pattern GLOB` | Glob used to locate the checksum manifest (defaults to `*wheelhouse*.sha256`). |
| `--token TEXT`            | GitHub token for private releases (falls back to `GITHUB_TOKEN`).              |
| `--timeout FLOAT`         | Network timeout in seconds for API and download calls.                         |
| `--max-retries INTEGER`   | Maximum retry attempts for API and download calls.                             |
| `--python PATH`           | Python executable used to invoke `pip install`.                                |
| `--pip-arg ARG`           | Additional arguments forwarded to pip (repeatable).                            |
| `--no-upgrade`            | Do not pass `--upgrade` to pip.                                                |
| `--overwrite`             | Replace existing files when downloading or extracting.                         |
| `--cleanup`               | Remove the extracted wheelhouse after installation completes.                  |
| `--remove-archive`        | Delete the downloaded archive after successful install.                        |
| `--allow-unsigned`        | Skip checksum verification (not recommended).                                  |

## Environment Variables

| Variable                              | Description                                                    |
| ------------------------------------- | -------------------------------------------------------------- |
| `HEPHAESTUS_RELEASE_REPOSITORY`       | Default repository override for release downloads.             |
| `HEPHAESTUS_RELEASE_ASSET_PATTERN`    | Default asset glob for wheelhouse selection.                   |
| `HEPHAESTUS_RELEASE_MANIFEST_PATTERN` | Default checksum manifest glob for verification.               |
| `HEPHAESTUS_RELEASE_CACHE`            | Override the destination directory for downloaded wheelhouses. |
| `GITHUB_TOKEN`                        | Bearer token used for authenticated release downloads.         |

## Exit Codes

- `0`: Command succeeded.
- Non-zero: An error occurred. For example, `cleanup` raises exit code 1 when cleanup errors are
  encountered, and `release install` re-raises failures from the download or pip install steps.
