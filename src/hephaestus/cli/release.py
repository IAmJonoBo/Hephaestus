"""Release management commands for the Hephaestus CLI."""

from __future__ import annotations

import logging
import os
from dataclasses import dataclass
from enum import Enum
from pathlib import Path
from typing import Annotated, Any

import typer
from rich.console import Console

from hephaestus import events as telemetry, release as release_module
from hephaestus.backfill import BackfillError, run_backfill
from hephaestus.telemetry import trace_command

console = Console()
logger = logging.getLogger(__name__)

release_app = typer.Typer(name="release", help="Release management commands.", no_args_is_help=True)


class ReleaseInstallSource(str, Enum):
    """Supported release installation sources."""

    GITHUB = "github"
    PYPI = "pypi"
    TEST_PYPI = "test-pypi"


DEFAULT_PROJECT_NAME = "hephaestus-toolkit"
TEST_PYPI_SIMPLE_URL = "https://test.pypi.org/simple/"
PYPI_SIMPLE_URL = "https://pypi.org/simple/"


@dataclass
class ReleaseInstallOptions:
    repository: str = release_module.DEFAULT_REPOSITORY
    tag: str | None = None
    asset_pattern: str = release_module.DEFAULT_ASSET_PATTERN
    manifest_pattern: str = release_module.DEFAULT_MANIFEST_PATTERN
    sigstore_pattern: str | None = release_module.DEFAULT_SIGSTORE_BUNDLE_PATTERN
    destination: Path | None = None
    token: str | None = None
    timeout: float = release_module.DEFAULT_TIMEOUT
    max_retries: int = release_module.DEFAULT_MAX_RETRIES
    python_executable: str | None = None
    pip_args: list[str] | None = None
    no_upgrade: bool = False
    overwrite: bool = False
    cleanup: bool = False
    remove_archive: bool = False
    allow_unsigned: bool = False
    require_sigstore: bool = False
    sigstore_identity: list[str] | None = None
    source: ReleaseInstallSource = ReleaseInstallSource.GITHUB
    project: str = DEFAULT_PROJECT_NAME
    index_url: str | None = None
    extra_index_url: str | None = None


@release_app.command("install")
def release_install(  # NOSONAR
    repository: Annotated[
        str,
        typer.Option(
            "--repository",
            "-r",
            help="GitHub repository in owner/name form to fetch wheelhouses from.",
            show_default=True,
        ),
    ] = release_module.DEFAULT_REPOSITORY,
    tag: Annotated[
        str | None,
        typer.Option("--tag", "-t", help="Release tag to download (defaults to latest)."),
    ] = None,
    asset_pattern: Annotated[
        str,
        typer.Option(
            "--asset-pattern",
            help="Glob used to select the wheelhouse asset.",
            show_default=True,
        ),
    ] = release_module.DEFAULT_ASSET_PATTERN,
    manifest_pattern: Annotated[
        str,
        typer.Option(
            "--manifest-pattern",
            help="Glob used to locate the checksum manifest for verification.",
            show_default=True,
        ),
    ] = release_module.DEFAULT_MANIFEST_PATTERN,
    sigstore_pattern: Annotated[
        str | None,
        typer.Option(
            "--sigstore-pattern",
            help="Glob used to locate Sigstore bundles for attestation verification.",
            show_default=True,
        ),
    ] = release_module.DEFAULT_SIGSTORE_BUNDLE_PATTERN,
    destination: Annotated[
        Path | None,
        typer.Option(
            "--destination",
            "-d",
            help="Directory used to cache downloaded wheelhouse archives.",
            exists=False,
            file_okay=False,
            dir_okay=True,
            writable=True,
            readable=True,
            resolve_path=True,
        ),
    ] = None,
    token: Annotated[
        str | None,
        typer.Option(
            "--token",
            envvar="GITHUB_TOKEN",
            help="GitHub token (falls back to the GITHUB_TOKEN environment variable).",
        ),
    ] = None,
    timeout: Annotated[
        float,
        typer.Option(
            "--timeout",
            min=0.1,
            help="Network timeout in seconds for release API calls and downloads.",
            show_default=True,
        ),
    ] = release_module.DEFAULT_TIMEOUT,
    max_retries: Annotated[
        int,
        typer.Option(
            "--max-retries",
            min=1,
            help="Maximum retry attempts for release API calls and downloads.",
            show_default=True,
        ),
    ] = release_module.DEFAULT_MAX_RETRIES,
    python_executable: Annotated[
        str | None,
        typer.Option("--python", help="Python executable used to invoke pip."),
    ] = None,
    pip_arg: Annotated[
        list[str] | None,
        typer.Option(
            "--pip-arg",
            help="Additional arguments forwarded to pip install.",
            metavar="ARG",
            show_default=False,
        ),
    ] = None,
    source: Annotated[
        ReleaseInstallSource,
        typer.Option(
            "--source",
            help="Release source to install from (github, pypi, or test-pypi).",
            case_sensitive=False,
            show_default=True,
        ),
    ] = ReleaseInstallSource.GITHUB,
    project: Annotated[
        str,
        typer.Option(
            "--project",
            help="PyPI project name to install when using PyPI/Test PyPI sources.",
            show_default=True,
        ),
    ] = DEFAULT_PROJECT_NAME,
    index_url: Annotated[
        str | None,
        typer.Option(
            "--index-url",
            help="Custom index URL for PyPI/Test PyPI installs.",
        ),
    ] = None,
    extra_index_url: Annotated[
        str | None,
        typer.Option(
            "--extra-index-url",
            help="Additional index URL for dependency resolution when using PyPI sources.",
        ),
    ] = None,
    pip_args: Annotated[
        list[str] | None,
        typer.Option(
            "--pip-args",
            help="Deprecated alias for --pip-arg (multiple values supported).",
            hidden=True,
        ),
    ] = None,
    python: Annotated[
        str | None,
        typer.Option(
            "--python-executable",
            help="Deprecated alias for --python.",
            hidden=True,
        ),
    ] = None,
    allow_unsigned: Annotated[
        bool,
        typer.Option(
            "--allow-unsigned",
            help="Permit installation without checksum verification (dangerous).",
            show_default=False,
        ),
    ] = False,
    require_sigstore: Annotated[
        bool,
        typer.Option(
            "--require-sigstore",
            help="Require Sigstore bundle verification for downloads.",
            show_default=False,
        ),
    ] = False,
    sigstore_identity: Annotated[
        list[str] | None,
        typer.Option(
            "--sigstore-identity",
            help="Accepted Sigstore identities when verifying bundles (repeatable).",
        ),
    ] = None,
    overwrite: Annotated[
        bool,
        typer.Option(
            "--overwrite",
            help="Overwrite cached wheelhouse archives if they already exist.",
            show_default=False,
        ),
    ] = False,
    cleanup: Annotated[
        bool,
        typer.Option(
            "--cleanup",
            help="Remove extracted wheelhouse contents after installation.",
            show_default=False,
        ),
    ] = False,
    remove_archive: Annotated[
        bool,
        typer.Option(
            "--remove-archive",
            help="Delete the downloaded archive after successful installation.",
            show_default=False,
        ),
    ] = False,
    no_upgrade: Annotated[
        bool,
        typer.Option(
            "--no-upgrade",
            help="Do not attempt to upgrade existing installations.",
            show_default=False,
        ),
    ] = False,
) -> None:
    """Download the Hephaestus wheelhouse and install it into the environment."""

    pip_args = pip_args or pip_arg
    python_executable = python or python_executable

    options = ReleaseInstallOptions(
        repository=repository,
        tag=tag,
        asset_pattern=asset_pattern,
        manifest_pattern=manifest_pattern,
        sigstore_pattern=sigstore_pattern,
        destination=destination,
        token=token,
        timeout=timeout,
        max_retries=max_retries,
        python_executable=python_executable,
        pip_args=list(pip_args) if pip_args else None,
        no_upgrade=no_upgrade,
        overwrite=overwrite,
        cleanup=cleanup,
        remove_archive=remove_archive,
        allow_unsigned=allow_unsigned,
        require_sigstore=require_sigstore,
        sigstore_identity=list(sigstore_identity) if sigstore_identity else None,
        source=source,
        project=project,
        index_url=index_url,
        extra_index_url=extra_index_url,
    )

    destination_path = (
        options.destination.expanduser()
        if options.destination
        else release_module.DEFAULT_DOWNLOAD_DIRECTORY
    )
    resolved_index_url = options.index_url
    resolved_extra_index_url = options.extra_index_url
    if options.source is ReleaseInstallSource.TEST_PYPI:
        resolved_index_url = resolved_index_url or TEST_PYPI_SIMPLE_URL
        resolved_extra_index_url = resolved_extra_index_url or PYPI_SIMPLE_URL

    normalized_version = None
    if options.tag:
        normalized_version = options.tag[1:] if options.tag.startswith("v") else options.tag

    operation_id = telemetry.generate_operation_id()
    with telemetry.operation_context(
        "cli.release.install",
        operation_id=operation_id,
        command="release.install",
        repository=options.repository,
        tag=options.tag or "latest",
    ):
        start_payload: dict[str, Any] = {
            "source": options.source.value,
            "tag": options.tag or "latest",
            "timeout": options.timeout,
            "max_retries": options.max_retries,
        }
        if options.source is ReleaseInstallSource.GITHUB:
            start_payload.update(
                {
                    "repository": options.repository,
                    "destination": str(destination_path),
                    "allow_unsigned": options.allow_unsigned,
                    "asset_pattern": options.asset_pattern,
                    "manifest_pattern": options.manifest_pattern,
                    "sigstore_pattern": options.sigstore_pattern,
                    "require_sigstore": options.require_sigstore,
                }
            )
            if options.sigstore_identity:
                start_payload["sigstore_identity"] = list(options.sigstore_identity)
        else:
            start_payload.update(
                {
                    "project": options.project,
                    "index_url": resolved_index_url,
                    "extra_index_url": resolved_extra_index_url,
                }
            )

        telemetry.emit_event(
            logger,
            telemetry.CLI_RELEASE_INSTALL_START,
            message="Starting release install",
            **start_payload,
        )

        if options.source is not ReleaseInstallSource.GITHUB:
            release_module.install_from_pypi(
                project=options.project,
                version=normalized_version,
                python_executable=options.python_executable,
                pip_args=list(options.pip_args) if options.pip_args else None,
                upgrade=not options.no_upgrade,
                index_url=resolved_index_url,
                extra_index_url=resolved_extra_index_url,
            )

            version_label = normalized_version or "latest"
            console.print(
                "[green]Installed[/green] "
                f"{options.project} {version_label} from [cyan]{options.source.value}[/cyan]."
            )
            telemetry.emit_event(
                logger,
                telemetry.CLI_RELEASE_INSTALL_COMPLETE,
                message="Release install completed",
                source=options.source.value,
                tag=options.tag or "latest",
                project=options.project,
                version=version_label,
            )
            return

        download = release_module.download_wheelhouse(
            repository=options.repository,
            destination_dir=destination_path,
            tag=options.tag,
            asset_pattern=options.asset_pattern,
            manifest_pattern=options.manifest_pattern,
            sigstore_bundle_pattern=options.sigstore_pattern,
            token=options.token,
            overwrite=options.overwrite,
            extract=False,
            allow_unsigned=options.allow_unsigned,
            require_sigstore=options.require_sigstore,
            sigstore_identities=(
                list(options.sigstore_identity) if options.sigstore_identity else None
            ),
            timeout=options.timeout,
            max_retries=options.max_retries,
        )

        release_module.install_from_archive(
            download.archive_path,
            python_executable=options.python_executable,
            pip_args=list(options.pip_args) if options.pip_args else None,
            upgrade=not options.no_upgrade,
            cleanup=options.cleanup,
        )

        if options.remove_archive:
            download.archive_path.unlink(missing_ok=True)
            telemetry.emit_event(
                logger,
                telemetry.CLI_RELEASE_INSTALL_ARCHIVE_REMOVED,
                message="Removed downloaded archive",
                archive=str(download.archive_path),
            )

        console.print(
            "[green]Installed wheelhouse[/green] "
            f"{download.asset.name} from [cyan]{options.repository}[/cyan] (tag: {options.tag or 'latest'})."
        )
        telemetry.emit_event(
            logger,
            telemetry.CLI_RELEASE_INSTALL_COMPLETE,
            message="Release install completed",
            source=options.source.value,
            repository=options.repository,
            tag=options.tag or "latest",
            asset=download.asset.name,
            allow_unsigned=options.allow_unsigned,
        )


@release_app.command("backfill")
@trace_command("release.backfill")
def release_backfill(
    version: Annotated[
        str | None,
        typer.Option(
            "--version",
            "-v",
            help="Specific version to backfill (default: all historical versions)",
        ),
    ] = None,
    dry_run: Annotated[
        bool,
        typer.Option(
            "--dry-run",
            help="Perform all steps except uploads (for testing)",
        ),
    ] = False,
) -> None:
    """Backfill Sigstore bundles for historical releases (ADR-0006)."""

    console.print("[cyan]Starting Sigstore bundle backfill...[/cyan]")

    token = os.environ.get("GITHUB_TOKEN")
    if not token:
        console.print("[red]✗ GITHUB_TOKEN environment variable not set[/red]")
        console.print("\nSet your GitHub token:")
        console.print("  export GITHUB_TOKEN=<your-token>")
        raise typer.Exit(code=1)

    if dry_run:
        console.print("[yellow]DRY RUN MODE - No actual uploads will be performed[/yellow]")

    try:
        summary = run_backfill(
            token=token,
            version=version,
            dry_run=dry_run,
        )
    except BackfillError as exc:
        console.print(f"\n[red]✗ Backfill failed: {exc}[/red]")
        raise typer.Exit(code=1) from exc
    except Exception as exc:  # pragma: no cover - defensive
        console.print(f"\n[red]✗ Unexpected error: {exc}[/red]")
        raise typer.Exit(code=1) from exc

    if not summary.ok:
        failed_versions = ", ".join(entry["version"] for entry in summary.failures)
        console.print("\n[red]✗ Backfill failed[/red] - see logs for details")
        if failed_versions:
            console.print(f"Failed versions: {failed_versions}")
        raise typer.Exit(code=1)

    console.print("\n[green]✓ Backfill completed successfully![/green]")
    console.print(f"Inventory updated at {summary.inventory_path}")


__all__ = [
    "ReleaseInstallOptions",
    "ReleaseInstallSource",
    "release_app",
    "release_backfill",
    "release_install",
]
