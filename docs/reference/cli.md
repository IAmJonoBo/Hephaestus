# CLI Reference

This reference documents the top-level `hephaestus` commands and their most important options. Run
`uv run hephaestus --help` for the canonical source of truth and subcommand details.

## Global Usage

```bash
uv run hephaestus [OPTIONS] COMMAND [ARGS]...
```

- `--install-completion`, `--show-completion`: Manage shell completions.
- `--help`: Display help text for any command.

## Commands

### `version`

Print the installed toolkit version.

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

### `tools refactor hotspots`

List the highest churn modules. Options include:

- `--limit INTEGER`: Number of hotspots to display.
- `--config PATH`: Load alternate configuration.

### `tools refactor opportunities`

Summarise advisory refactor opportunities with estimated effort.

### `tools qa profile NAME`

Display thresholds and switches for a specific QA profile (e.g., `quick`, `full`).

### `tools qa coverage`

Highlight uncovered lines and risk scores. Accepts `--config PATH` to override defaults.

### `release install`

Download and install a wheelhouse archive. Important options:

| Option                    | Description                                                         |
| ------------------------- | ------------------------------------------------------------------- |
| `--repository OWNER/REPO` | Source repository for releases (default: `IAmJonoBo/Hephaestus`).   |
| `--tag TAG`               | Release tag to download (defaults to latest).                       |
| `--asset-pattern GLOB`    | Glob pattern used to locate the wheelhouse asset.                   |
| `--destination PATH`      | Directory for downloaded archives (defaults to the platform cache). |
| `--token TEXT`            | GitHub token for private releases (falls back to `GITHUB_TOKEN`).   |
| `--python PATH`           | Python executable used to invoke `pip install`.                     |
| `--pip-arg ARG`           | Additional arguments forwarded to pip (repeatable).                 |
| `--no-upgrade`            | Do not pass `--upgrade` to pip.                                     |
| `--overwrite`             | Replace existing files when downloading or extracting.              |
| `--cleanup`               | Remove the extracted wheelhouse after installation completes.       |
| `--remove-archive`        | Delete the downloaded archive after successful install.             |

## Environment Variables

| Variable                           | Description                                                    |
| ---------------------------------- | -------------------------------------------------------------- |
| `HEPHAESTUS_RELEASE_REPOSITORY`    | Default repository override for release downloads.             |
| `HEPHAESTUS_RELEASE_ASSET_PATTERN` | Default asset glob for wheelhouse selection.                   |
| `HEPHAESTUS_RELEASE_CACHE`         | Override the destination directory for downloaded wheelhouses. |
| `GITHUB_TOKEN`                     | Bearer token used for authenticated release downloads.         |

## Exit Codes

- `0`: Command succeeded.
- Non-zero: An error occurred. For example, `cleanup` raises exit code 1 when cleanup errors are
  encountered, and `release install` re-raises failures from the download or pip install steps.
