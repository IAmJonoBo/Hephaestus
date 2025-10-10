"""Telemetry schema and helpers for structured logging events."""

from __future__ import annotations

import contextlib
import logging
import uuid
from collections.abc import Iterable, Iterator
from dataclasses import dataclass
from typing import Any

from hephaestus.logging import log_context, log_event

__all__ = [
    "TelemetryEvent",
    "TelemetryRegistry",
    "registry",
    "emit_event",
    "operation_context",
    "generate_run_id",
    "generate_operation_id",
    # Event definitions
    "API_AUDIT_EVENT",
    "CLI_CLEANUP_START",
    "CLI_CLEANUP_COMPLETE",
    "CLI_CLEANUP_FAILED",
    "CLI_GUARD_RAILS_START",
    "CLI_GUARD_RAILS_COMPLETE",
    "CLI_GUARD_RAILS_FAILED",
    "CLI_GUARD_RAILS_DRIFT",
    "CLI_GUARD_RAILS_DRIFT_OK",
    "CLI_RELEASE_INSTALL_START",
    "CLI_RELEASE_INSTALL_COMPLETE",
    "CLI_RELEASE_INSTALL_ARCHIVE_REMOVED",
    "CLEANUP_RUN_START",
    "CLEANUP_RUN_COMPLETE",
    "CLEANUP_PATH_SKIPPED",
    "CLEANUP_PATH_ERROR",
    "CLEANUP_PATH_PREVIEW",
    "CLEANUP_PATH_REMOVED",
    "RESOURCE_FORK_SANITIZE_SKIPPED",
    "RESOURCE_FORK_SANITIZE_PREVIEW",
    "RESOURCE_FORK_SANITIZE_ERROR",
    "RESOURCE_FORK_SANITIZE_REMOVED",
    "RELEASE_METADATA_FETCH",
    "RELEASE_TOKEN_VALIDATION",
    "RELEASE_ASSET_SELECTED",
    "RELEASE_ASSET_SANITISED",
    "RELEASE_MANIFEST_LOCATE",
    "RELEASE_MANIFEST_DOWNLOAD",
    "RELEASE_MANIFEST_VERIFIED",
    "RELEASE_MANIFEST_SKIPPED",
    "RELEASE_DOWNLOAD_START",
    "RELEASE_DOWNLOAD_COMPLETE",
    "RELEASE_NETWORK_RETRY",
    "RELEASE_HTTP_RETRY",
    "RELEASE_SIGSTORE_LOCATE",
    "RELEASE_SIGSTORE_DOWNLOAD",
    "RELEASE_SIGSTORE_MISSING",
    "RELEASE_SIGSTORE_VERIFIED",
    "RELEASE_EXTRACT_START",
    "RELEASE_EXTRACT_COMPLETE",
    "RELEASE_SANITIZE_START",
    "RELEASE_SANITIZE_COMPLETE",
    "RELEASE_SANITIZE_FAILED",
    "RELEASE_INSTALL_START",
    "RELEASE_INSTALL_INVOKE",
    "RELEASE_INSTALL_COMPLETE",
]


@dataclass(frozen=True)
class TelemetryEvent:
    """Structured description of an emitted log event."""

    name: str
    description: str
    required_fields: tuple[str, ...] = ()
    optional_fields: tuple[str, ...] = ()

    def validate(self, payload: dict[str, Any]) -> None:
        """Validate *payload* against the event schema."""

        missing: list[str] = [field for field in self.required_fields if field not in payload]
        if missing:
            raise ValueError(
                f"Event {self.name!r} missing required fields: {', '.join(sorted(missing))}"
            )

        allowed: set[str] = set(self.required_fields) | set(self.optional_fields)
        unexpected = sorted(set(payload) - allowed)
        if unexpected:
            raise ValueError(
                f"Event {self.name!r} received unexpected fields: {', '.join(unexpected)}"
            )


class TelemetryRegistry:
    """Registry that tracks available telemetry events."""

    def __init__(self) -> None:
        self._events: dict[str, TelemetryEvent] = {}

    def register(self, event: TelemetryEvent) -> TelemetryEvent:
        """Register a new telemetry event definition.

        Args:
            event: Event to register

        Returns:
            The registered event

        Raises:
            ValueError: If event name is already registered
        """
        if event.name in self._events:
            raise ValueError(f"Event {event.name!r} already registered")
        self._events[event.name] = event
        return event

    def get(self, name: str) -> TelemetryEvent:
        """Retrieve a registered event by name.

        Args:
            name: Event name to look up

        Returns:
            The registered event

        Raises:
            KeyError: If event name is not registered
        """
        try:
            return self._events[name]
        except KeyError as exc:  # pragma: no cover - defensive fallback
            raise KeyError(f"Telemetry event {name!r} not defined") from exc

    def all_events(self) -> Iterable[TelemetryEvent]:
        """Return all registered telemetry events.

        Returns:
            Iterable of all registered events
        """
        return self._events.values()


registry = TelemetryRegistry()


def _register(event: TelemetryEvent) -> TelemetryEvent:
    return registry.register(event)


def generate_run_id() -> str:
    """Return a unique run identifier suitable for correlating CLI sessions."""

    return f"run-{uuid.uuid4().hex}"


def generate_operation_id() -> str:
    """Return a unique identifier that scopes an individual operation."""

    return f"op-{uuid.uuid4().hex}"


@contextlib.contextmanager
def operation_context(
    name: str,
    *,
    operation_id: str | None = None,
    **fields: Any,
) -> Iterator[None]:
    """Bind operation metadata to subsequent telemetry events."""

    payload = {"operation": name}
    if operation_id is not None:
        payload["operation_id"] = operation_id
    payload.update({key: value for key, value in fields.items() if value is not None})

    with log_context(**payload):
        yield


def emit_event(
    logger: logging.Logger,
    event: TelemetryEvent,
    *,
    level: int = logging.INFO,
    message: str | None = None,
    **payload: Any,
) -> None:
    """Validate and emit a structured telemetry event."""

    event.validate(payload)
    log_event(logger, event.name, level=level, message=message, **payload)


# API telemetry events
API_AUDIT_EVENT = _register(
    TelemetryEvent(
        "api.audit",
        "Audit log emitted from REST or gRPC API surfaces.",
        required_fields=("principal", "operation", "status", "key_id"),
        optional_fields=("parameters", "outcome", "protocol"),
    )
)


# CLI telemetry events
CLI_CLEANUP_START = _register(
    TelemetryEvent(
        "cli.cleanup.start",
        "Cleanup CLI invocation started.",
        required_fields=(
            "include_git",
            "include_poetry_env",
            "python_cache",
            "build_artifacts",
            "node_modules",
            "deep_clean",
            "extra_paths",
            "dry_run",
        ),
        optional_fields=("root", "audit_manifest"),
    )
)

CLI_CLEANUP_COMPLETE = _register(
    TelemetryEvent(
        "cli.cleanup.complete",
        "Cleanup CLI invocation completed successfully.",
        required_fields=("removed", "skipped", "errors"),
        optional_fields=("audit_manifest",),
    )
)

CLI_CLEANUP_FAILED = _register(
    TelemetryEvent(
        "cli.cleanup.failed",
        "Cleanup CLI invocation aborted with errors.",
        required_fields=("errors",),
    )
)

CLI_GUARD_RAILS_START = _register(
    TelemetryEvent(
        "cli.guard-rails.start",
        "Guard-rails pipeline started.",
        required_fields=("skip_format",),
    )
)

CLI_GUARD_RAILS_COMPLETE = _register(
    TelemetryEvent(
        "cli.guard-rails.complete",
        "Guard-rails pipeline completed successfully.",
        required_fields=("skip_format",),
    )
)

CLI_GUARD_RAILS_FAILED = _register(
    TelemetryEvent(
        "cli.guard-rails.failed",
        "Guard-rails pipeline failed.",
        required_fields=("step", "returncode"),
        optional_fields=("level",),
    )
)

CLI_GUARD_RAILS_DRIFT = _register(
    TelemetryEvent(
        "cli.guard-rails.drift",
        "Tool version drift detected.",
        required_fields=("drifted_tools",),
    )
)

CLI_GUARD_RAILS_DRIFT_OK = _register(
    TelemetryEvent(
        "cli.guard-rails.drift.ok",
        "No tool version drift detected.",
    )
)

CLI_GUARD_RAILS_REMEDIATED = _register(
    TelemetryEvent(
        "cli.guard-rails.drift.remediated",
        "Tool version drift remediated automatically.",
        required_fields=("commands",),
    )
)

CLI_RELEASE_INSTALL_START = _register(
    TelemetryEvent(
        "cli.release.install.start",
        "Release installation command invoked.",
        required_fields=(
            "repository",
            "tag",
            "destination",
            "allow_unsigned",
            "asset_pattern",
            "manifest_pattern",
            "sigstore_pattern",
            "require_sigstore",
            "timeout",
            "max_retries",
        ),
        optional_fields=("sigstore_identity",),
    )
)

CLI_RELEASE_INSTALL_COMPLETE = _register(
    TelemetryEvent(
        "cli.release.install.complete",
        "Release installation command completed.",
        required_fields=("repository", "tag", "asset", "allow_unsigned"),
    )
)

CLI_RELEASE_INSTALL_ARCHIVE_REMOVED = _register(
    TelemetryEvent(
        "cli.release.install.archive-removed",
        "Temporary release archive removed after installation.",
        required_fields=("archive",),
    )
)


# Cleanup engine telemetry events
CLEANUP_RUN_START = _register(
    TelemetryEvent(
        "cleanup.run.start",
        "Cleanup engine starting sweep across search roots.",
        required_fields=(
            "search_roots",
            "include_git",
            "include_poetry_env",
            "python_cache",
            "build_artifacts",
            "node_modules",
            "extra_paths",
            "dry_run",
        ),
    )
)

CLEANUP_RUN_COMPLETE = _register(
    TelemetryEvent(
        "cleanup.run.complete",
        "Cleanup engine completed sweep.",
        required_fields=("removed", "skipped", "errors", "dry_run"),
        optional_fields=("audit_manifest",),
    )
)

CLEANUP_PATH_SKIPPED = _register(
    TelemetryEvent(
        "cleanup.path.skipped",
        "Cleanup skipped a root path.",
        required_fields=("path", "reason"),
    )
)

CLEANUP_PATH_ERROR = _register(
    TelemetryEvent(
        "cleanup.path.error",
        "Cleanup encountered an error while removing a path.",
        required_fields=("path", "reason"),
    )
)

CLEANUP_PATH_PREVIEW = _register(
    TelemetryEvent(
        "cleanup.path.preview",
        "Cleanup previewed removing a path.",
        required_fields=("path", "dry_run"),
    )
)

CLEANUP_PATH_REMOVED = _register(
    TelemetryEvent(
        "cleanup.path.removed",
        "Cleanup removed a path.",
        required_fields=("path", "dry_run"),
    )
)

RESOURCE_FORK_SANITIZE_SKIPPED = _register(
    TelemetryEvent(
        "resource_fork.sanitize.skipped",
        "Resource fork sanitisation skipped because the target path is missing.",
        required_fields=("path",),
    )
)

RESOURCE_FORK_SANITIZE_PREVIEW = _register(
    TelemetryEvent(
        "resource_fork.sanitize.preview",
        "Resource fork artefact identified during dry run.",
        required_fields=("path",),
    )
)

RESOURCE_FORK_SANITIZE_ERROR = _register(
    TelemetryEvent(
        "resource_fork.sanitize.error",
        "Removing a resource fork artefact failed.",
        required_fields=("path", "reason"),
    )
)

RESOURCE_FORK_SANITIZE_REMOVED = _register(
    TelemetryEvent(
        "resource_fork.sanitize.removed",
        "Resource fork artefact removed successfully.",
        required_fields=("path",),
    )
)


# Release pipeline telemetry events
RELEASE_METADATA_FETCH = _register(
    TelemetryEvent(
        "release.metadata.fetch",
        "Fetching release metadata from GitHub.",
    )
)

RELEASE_TOKEN_VALIDATION = _register(
    TelemetryEvent(
        "release.token.validation",
        "GitHub token validation warning.",
    )
)

RELEASE_ASSET_SELECTED = _register(
    TelemetryEvent(
        "release.asset.selected",
        "Release asset selected for download.",
        required_fields=("asset", "size"),
    )
)

RELEASE_ASSET_SANITISED = _register(
    TelemetryEvent(
        "release.asset.sanitised",
        "Release asset name sanitised before download.",
        required_fields=("original_name", "sanitised_name"),
    )
)

RELEASE_MANIFEST_LOCATE = _register(
    TelemetryEvent(
        "release.manifest.locate",
        "Locating checksum manifest for release asset.",
        required_fields=("pattern",),
    )
)

RELEASE_MANIFEST_DOWNLOAD = _register(
    TelemetryEvent(
        "release.manifest.download",
        "Downloading checksum manifest for release asset.",
        required_fields=("manifest", "destination"),
    )
)

RELEASE_MANIFEST_VERIFIED = _register(
    TelemetryEvent(
        "release.manifest.verified",
        "Checksum manifest verified against downloaded asset.",
        required_fields=("asset", "digest"),
    )
)

RELEASE_MANIFEST_SKIPPED = _register(
    TelemetryEvent(
        "release.manifest.skipped",
        "Checksum verification intentionally skipped.",
        required_fields=("asset",),
    )
)

RELEASE_DOWNLOAD_START = _register(
    TelemetryEvent(
        "release.download.start",
        "Starting download of release asset.",
        required_fields=("asset", "destination"),
        optional_fields=("overwrite",),
    )
)

RELEASE_DOWNLOAD_COMPLETE = _register(
    TelemetryEvent(
        "release.download.complete",
        "Release asset downloaded successfully.",
        required_fields=("asset", "destination"),
    )
)

RELEASE_NETWORK_RETRY = _register(
    TelemetryEvent(
        "release.network.retry",
        "Network retry triggered while fetching release metadata.",
        required_fields=("url", "attempt", "max_retries"),
        optional_fields=("reason", "backoff_seconds", "description"),
    )
)

RELEASE_HTTP_RETRY = _register(
    TelemetryEvent(
        "release.http.retry",
        "HTTP retry triggered during asset download.",
        required_fields=("url", "attempt", "max_retries"),
        optional_fields=("http_status", "backoff_seconds", "description"),
    )
)

RELEASE_SIGSTORE_LOCATE = _register(
    TelemetryEvent(
        "release.sigstore.locate",
        "Locating Sigstore bundle for attestation verification.",
        required_fields=("pattern",),
    )
)

RELEASE_SIGSTORE_DOWNLOAD = _register(
    TelemetryEvent(
        "release.sigstore.download",
        "Downloading Sigstore bundle for attestation verification.",
        required_fields=("bundle", "destination"),
    )
)

RELEASE_SIGSTORE_MISSING = _register(
    TelemetryEvent(
        "release.sigstore.missing",
        "Sigstore bundle missing from release.",
        required_fields=("pattern",),
    )
)

RELEASE_SIGSTORE_VERIFIED = _register(
    TelemetryEvent(
        "release.sigstore.verified",
        "Sigstore attestation verified successfully.",
        required_fields=("subject", "issuer", "identities"),
    )
)

RELEASE_EXTRACT_START = _register(
    TelemetryEvent(
        "release.extract.start",
        "Extracting downloaded release archive.",
        required_fields=("destination",),
        optional_fields=("overwrite",),
    )
)

RELEASE_EXTRACT_COMPLETE = _register(
    TelemetryEvent(
        "release.extract.complete",
        "Extraction of release archive completed.",
        required_fields=("destination",),
    )
)

RELEASE_SANITIZE_START = _register(
    TelemetryEvent(
        "release.sanitize.start",
        "Starting resource fork sanitisation for extracted wheelhouse directories.",
        required_fields=("root",),
    )
)

RELEASE_SANITIZE_COMPLETE = _register(
    TelemetryEvent(
        "release.sanitize.complete",
        "Completed resource fork sanitisation for extracted wheelhouse directories.",
        required_fields=("root",),
        optional_fields=("removed",),
    )
)

RELEASE_SANITIZE_FAILED = _register(
    TelemetryEvent(
        "release.sanitize.failed",
        "Resource fork sanitisation failed to complete.",
        required_fields=("root",),
        optional_fields=("artefacts", "error"),
    )
)

RELEASE_INSTALL_START = _register(
    TelemetryEvent(
        "release.install.start",
        "Starting installation of wheels from directory.",
        required_fields=("wheels", "directory", "upgrade"),
        optional_fields=("python_executable",),
    )
)

RELEASE_INSTALL_INVOKE = _register(
    TelemetryEvent(
        "release.install.invoke",
        "Invoking pip install command.",
        required_fields=("command",),
    )
)

RELEASE_INSTALL_COMPLETE = _register(
    TelemetryEvent(
        "release.install.complete",
        "Completed installation of wheels from directory.",
        required_fields=("wheels", "directory"),
    )
)
