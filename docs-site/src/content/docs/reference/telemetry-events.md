---
title: "Telemetry Events Reference"
description: "This document describes all structured telemetry events emitted by Hephaestus. Events are used for observability, debugging, and operational metrics..."
---

This document describes all structured telemetry events emitted by Hephaestus. Events are used for observability, debugging, and operational metrics collection.

## Event Architecture

Hephaestus uses a **structured telemetry system** with:

- **Event Registry**: Central registry of all defined events with validation
- **Required Fields**: Fields that must be present in every event emission
- **Optional Fields**: Fields that may be included for additional context
- **Validation**: Automatic validation of event payloads against schemas
- **Correlation**: Run IDs and operation IDs for distributed tracing

## Event Categories

### CLI Events

Events emitted by CLI command handlers.

#### `cli.cleanup.start`

**Description:** Cleanup CLI invocation started.

**Required Fields:**

- `include_git` (bool): Whether to clean .git directories
- `include_poetry_env` (bool): Whether to clean Poetry environments
- `python_cache` (bool): Whether to clean Python cache
- `build_artifacts` (bool): Whether to clean build artifacts
- `node_modules` (bool): Whether to clean node_modules
- `deep_clean` (bool): Whether deep clean mode is enabled
- `extra_paths` (list): Additional paths to clean
- `dry_run` (bool): Whether this is a dry run

**Optional Fields:**

- `root` (Path): Project root directory
- `audit_manifest` (Path): Path to audit manifest

**Example:**

```json
{
  "event": "cli.cleanup.start",
  "include_git": false,
  "include_poetry_env": false,
  "python_cache": true,
  "build_artifacts": true,
  "node_modules": false,
  "deep_clean": false,
  "extra_paths": [],
  "dry_run": false,
  "root": "/project"
}
```

#### `cli.cleanup.complete`

**Description:** Cleanup CLI invocation completed successfully.

**Required Fields:**

- `removed` (int): Number of paths removed
- `skipped` (int): Number of paths skipped
- `errors` (int): Number of errors encountered

**Optional Fields:**

- `audit_manifest` (Path): Path where audit manifest was written

#### `cli.cleanup.failed`

**Description:** Cleanup CLI invocation aborted with errors.

**Required Fields:**

- `errors` (int): Number of errors that caused failure

#### `cli.guard-rails.start`

**Description:** Guard-rails pipeline started.

**Required Fields:**

- `skip_format` (bool): Whether formatting step is skipped

#### `cli.guard-rails.complete`

**Description:** Guard-rails pipeline completed successfully.

**Required Fields:**

- `skip_format` (bool): Whether formatting step was skipped

#### `cli.guard-rails.failed`

**Description:** Guard-rails pipeline failed.

**Required Fields:**

- `step` (str): Which step failed (e.g., "ruff check", "mypy", "pytest")
- `returncode` (int): Exit code from failed step

**Optional Fields:**

- `level` (str): Log level for the failure

#### `cli.guard-rails.drift`

**Description:** Tool version drift detected.

**Required Fields:**

- `drifted_tools` (list[str]): Names of tools with version drift

**Example:**

```json
{
  "event": "cli.guard-rails.drift",
  "drifted_tools": ["ruff", "mypy"]
}
```

#### `cli.guard-rails.drift.ok`

**Description:** No tool version drift detected.

#### `cli.release.install.start`

**Description:** Release installation command invoked.

**Required Fields:**

- `repository` (str): GitHub repository (owner/repo)
- `tag` (str): Release tag to install
- `destination` (Path): Download destination
- `allow_unsigned` (bool): Whether unsigned releases are allowed
- `asset_pattern` (str): Pattern for matching assets
- `manifest_pattern` (str): Pattern for checksum manifests
- `sigstore_pattern` (str): Pattern for Sigstore bundles
- `require_sigstore` (bool): Whether Sigstore verification is required
- `timeout` (float): Network timeout in seconds
- `max_retries` (int): Maximum retry attempts

**Optional Fields:**

- `sigstore_identity` (str): Expected Sigstore identity pattern

#### `cli.release.install.complete`

**Description:** Release installation command completed.

**Required Fields:**

- `repository` (str): GitHub repository
- `tag` (str): Release tag installed
- `asset` (str): Asset name installed
- `allow_unsigned` (bool): Whether unsigned was allowed

#### `cli.release.install.archive-removed`

**Description:** Temporary release archive removed after installation.

**Required Fields:**

- `archive` (Path): Path to removed archive

### Cleanup Engine Events

Events emitted by the cleanup engine during workspace cleaning.

#### `cleanup.run.start`

**Description:** Cleanup engine starting sweep across search roots.

**Required Fields:**

- `search_roots` (list[Path]): Directories to search
- `include_git` (bool): Clean .git directories
- `include_poetry_env` (bool): Clean Poetry environments
- `python_cache` (bool): Clean Python cache
- `build_artifacts` (bool): Clean build artifacts
- `node_modules` (bool): Clean node_modules
- `extra_paths` (list[Path]): Additional paths
- `dry_run` (bool): Dry run mode

#### `cleanup.run.complete`

**Description:** Cleanup engine completed sweep.

**Required Fields:**

- `removed` (int): Paths removed
- `skipped` (int): Paths skipped
- `errors` (int): Errors encountered
- `dry_run` (bool): Was dry run

**Optional Fields:**

- `audit_manifest` (Path): Audit manifest location

#### `cleanup.path.skipped`

**Description:** Cleanup skipped a root path.

**Required Fields:**

- `path` (Path): Path that was skipped
- `reason` (str): Why it was skipped

#### `cleanup.path.error`

**Description:** Cleanup encountered an error while removing a path.

**Required Fields:**

- `path` (Path): Path that caused error
- `reason` (str): Error description

#### `cleanup.path.preview`

**Description:** Cleanup previewed removing a path (dry run).

**Required Fields:**

- `path` (Path): Path to be removed
- `dry_run` (bool): Always true for preview

#### `cleanup.path.removed`

**Description:** Cleanup removed a path.

**Required Fields:**

- `path` (Path): Path that was removed
- `dry_run` (bool): Was this a dry run

### Release Pipeline Events

Events emitted during release asset download and installation.

#### `release.metadata.fetch`

**Description:** Fetching release metadata from GitHub.

#### `release.asset.selected`

**Description:** Release asset selected for download.

**Required Fields:**

- `asset` (str): Asset name
- `size` (int): Asset size in bytes

#### `release.asset.sanitised`

**Description:** Release asset name sanitised before download.

**Required Fields:**

- `original_name` (str): Original asset name from GitHub
- `sanitised_name` (str): Sanitised filename for filesystem

**Example:**

```json
{
  "event": "release.asset.sanitised",
  "original_name": "../../../etc/passwd",
  "sanitised_name": "passwd"
}
```

#### `release.manifest.locate`

**Description:** Locating checksum manifest for release asset.

**Required Fields:**

- `pattern` (str): Glob pattern used to find manifest

#### `release.manifest.download`

**Description:** Downloading checksum manifest for release asset.

**Required Fields:**

- `manifest` (str): Manifest filename
- `destination` (Path): Download location

#### `release.manifest.verified`

**Description:** Checksum manifest verified against downloaded asset.

**Required Fields:**

- `asset` (str): Asset filename
- `digest` (str): SHA-256 digest that was verified

#### `release.manifest.skipped`

**Description:** Checksum verification intentionally skipped.

**Required Fields:**

- `asset` (str): Asset for which verification was skipped

#### `release.download.start`

**Description:** Starting download of release asset.

**Required Fields:**

- `asset` (str): Asset to download
- `destination` (Path): Download location

**Optional Fields:**

- `overwrite` (bool): Whether existing file will be overwritten

#### `release.download.complete`

**Description:** Release asset downloaded successfully.

**Required Fields:**

- `asset` (str): Downloaded asset
- `destination` (Path): Final location

#### `release.network.retry`

**Description:** Network retry triggered while fetching release metadata.

**Required Fields:**

- `url` (str): URL being fetched
- `attempt` (int): Current attempt number
- `max_retries` (int): Maximum attempts allowed

**Optional Fields:**

- `reason` (str): Reason for retry
- `backoff_seconds` (float): Backoff delay
- `description` (str): Additional context

#### `release.http.retry`

**Description:** HTTP retry triggered during asset download.

**Required Fields:**

- `url` (str): URL being downloaded
- `attempt` (int): Current attempt
- `max_retries` (int): Maximum attempts

**Optional Fields:**

- `http_status` (int): HTTP status code
- `backoff_seconds` (float): Backoff delay
- `description` (str): Additional context

#### `release.sigstore.locate`

**Description:** Locating Sigstore bundle for attestation verification.

**Required Fields:**

- `pattern` (str): Glob pattern for bundle

#### `release.sigstore.download`

**Description:** Downloading Sigstore bundle for attestation verification.

**Required Fields:**

- `bundle` (str): Bundle filename
- `destination` (Path): Download location

#### `release.sigstore.missing`

**Description:** Sigstore bundle missing from release.

**Required Fields:**

- `pattern` (str): Pattern that didn't match any bundles

#### `release.sigstore.verified`

**Description:** Sigstore attestation verified successfully.

**Required Fields:**

- `subject` (str): Certificate subject
- `issuer` (str): Certificate issuer
- `identities` (tuple[str]): Verified identities

**Example:**

```json
{
  "event": "release.sigstore.verified",
  "subject": "https://github.com/user/repo/.github/workflows/release.yml@refs/heads/main",
  "issuer": "https://token.actions.githubusercontent.com",
  "identities": ["https://github.com/user/repo"]
}
```

#### `release.extract.start`

**Description:** Extracting downloaded release archive.

**Required Fields:**

- `destination` (Path): Extraction destination

**Optional Fields:**

- `overwrite` (bool): Whether to overwrite existing files

#### `release.extract.complete`

**Description:** Extraction of release archive completed.

**Required Fields:**

- `destination` (Path): Where archive was extracted

#### `release.install.start`

**Description:** Starting installation of wheels from directory.

**Required Fields:**

- `wheels` (int): Number of wheel files found
- `directory` (Path): Directory containing wheels
- `upgrade` (bool): Whether to upgrade existing packages

**Optional Fields:**

- `python_executable` (str): Python interpreter being used

#### `release.install.invoke`

**Description:** Invoking pip install command.

**Required Fields:**

- `command` (list[str]): Full pip command being executed

#### `release.install.complete`

**Description:** Completed installation of wheels from directory.

**Required Fields:**

- `wheels` (int): Number of wheels installed
- `directory` (Path): Source directory

## Using Telemetry Events

### Emitting Events

Events are emitted using the `telemetry.emit_event()` function:

```python
from hephaestus import telemetry
import logging

logger = logging.getLogger(__name__)

telemetry.emit_event(
    logger,
    telemetry.CLEANUP_PATH_REMOVED,
    message="Removed Python cache",
    path="/project/__pycache__",
    dry_run=False,
)
```

### Event Validation

All events are automatically validated against their schema:

```python
# This will raise ValueError if required fields are missing
telemetry.emit_event(
    logger,
    telemetry.RELEASE_ASSET_SELECTED,
    # Missing required field "size" - will raise ValueError
    asset="wheelhouse.tar.gz",
)
```

### Operation Context

Use operation contexts to correlate related events:

```python
from hephaestus import telemetry

operation_id = telemetry.generate_operation_id()

with telemetry.operation_context(
    "release.download",
    operation_id=operation_id,
    repository="owner/repo",
    tag="v1.0.0",
):
    # All events emitted here will include operation metadata
    telemetry.emit_event(logger, telemetry.RELEASE_DOWNLOAD_START, ...)
    # ... download logic ...
    telemetry.emit_event(logger, telemetry.RELEASE_DOWNLOAD_COMPLETE, ...)
```

### Log Formats

Events can be output in text or JSON format:

**Text format** (human-readable):

```
INFO hephaestus.release: Downloading release asset | event=release.download.start asset=wheelhouse.tar.gz destination=/cache/wheelhouse.tar.gz
```

**JSON format** (machine-parseable):

```json
{
  "timestamp": "2025-01-11T12:34:56.789Z",
  "level": "INFO",
  "logger": "hephaestus.release",
  "message": "Downloading release asset",
  "event": "release.download.start",
  "payload": {
    "asset": "wheelhouse.tar.gz",
    "destination": "/cache/wheelhouse.tar.gz",
    "operation": "release.download",
    "operation_id": "op-abc123"
  }
}
```

## Event Registry API

### Registering Custom Events

While not typically needed, you can register custom events:

```python
from hephaestus.telemetry import TelemetryEvent, registry

MY_CUSTOM_EVENT = registry.register(
    TelemetryEvent(
        name="my.custom.event",
        description="Description of what this event represents",
        required_fields=("field1", "field2"),
        optional_fields=("field3",),
    )
)
```

### Querying the Registry

```python
from hephaestus import telemetry

# Get a specific event
event = telemetry.registry.get("cli.cleanup.start")

# List all registered events
for event in telemetry.registry.all_events():
    print(f"{event.name}: {event.description}")
```

## Best Practices

### 1. Always Use Defined Events

Don't emit arbitrary log events - use the defined telemetry events:

```python
# ❌ Bad: Arbitrary log message
logger.info("Cleaning up build artifacts")

# ✅ Good: Structured telemetry event
telemetry.emit_event(
    logger,
    telemetry.CLEANUP_PATH_REMOVED,
    message="Cleaning up build artifacts",
    path=build_dir,
    dry_run=False,
)
```

### 2. Include Context in Operation Blocks

Use operation contexts for multi-step workflows:

```python
# ✅ Good: All events correlated with operation ID
with telemetry.operation_context("cli.guard-rails", operation_id=op_id):
    emit_event(logger, telemetry.CLI_GUARD_RAILS_START, ...)
    # ... pipeline steps ...
    emit_event(logger, telemetry.CLI_GUARD_RAILS_COMPLETE, ...)
```

### 3. Handle Required vs Optional Fields

Be explicit about which fields are required:

```python
# ✅ Good: All required fields present
telemetry.emit_event(
    logger,
    telemetry.RELEASE_NETWORK_RETRY,
    url="https://api.github.com/repos/...",
    attempt=2,
    max_retries=3,
    # Optional fields can be omitted or included
    reason="Connection timeout",
    backoff_seconds=1.0,
)
```

### 4. Use Meaningful Messages

Provide human-readable messages alongside structured data:

```python
telemetry.emit_event(
    logger,
    telemetry.CLEANUP_PATH_ERROR,
    message=f"Failed to remove {path}: Permission denied",  # ✅ Good
    path=path,
    reason="Permission denied",
)
```

## Troubleshooting

### Event Validation Errors

If you see `ValueError: Event 'xxx' missing required fields...`:

1. Check the event definition for required fields
2. Ensure all required fields are passed to `emit_event()`
3. Verify field types match expectations

### Missing Events in Logs

If events aren't appearing:

1. Check log level - events emit at INFO level by default
2. Verify logging is configured: `configure_logging()`
3. Ensure you're using `emit_event()` not plain `logger.info()`

### JSON Parsing Errors

If JSON logs are malformed:

1. Verify log format is set to "json"
2. Check for custom log handlers that may interfere
3. Ensure all payload values are JSON-serializable

## See Also

- [Structured Logging](../how-to/operating-safely.md#structured-logging)
- [Quality Gates](/how-to/quality-gates/)
- [Architecture Overview](/explanation/architecture/)
- [Telemetry Source Code](../../src/hephaestus/telemetry.py)
