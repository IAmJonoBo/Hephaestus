"""Helpers for consuming wheelhouse archives published to GitHub releases.

The goal of this module is to make Hephaestus' release artefacts easy to reuse from
any project.  All interactions rely solely on the Python standard library so the
helpers work on Linux, macOS, and Windows runners without extra dependencies.
"""

from __future__ import annotations

import hashlib
import json
import logging
import os
import re
import shutil
import subprocess
import sys
import tarfile
import time
import urllib.error
import urllib.request
from collections.abc import Sequence
from dataclasses import dataclass
from fnmatch import fnmatch
from pathlib import Path, PurePosixPath
from typing import IO, cast

from hephaestus.logging import log_context, log_event

__all__ = [
    "DEFAULT_ASSET_PATTERN",
    "DEFAULT_REPOSITORY",
    "DEFAULT_DOWNLOAD_DIRECTORY",
    "DEFAULT_MANIFEST_PATTERN",
    "DEFAULT_TIMEOUT",
    "DEFAULT_MAX_RETRIES",
    "ReleaseDownload",
    "ReleaseError",
    "default_download_dir",
    "download_wheelhouse",
    "extract_archive",
    "install_from_directory",
]


DEFAULT_REPOSITORY = os.environ.get("HEPHAESTUS_RELEASE_REPOSITORY", "IAmJonoBo/Hephaestus")
DEFAULT_ASSET_PATTERN = os.environ.get("HEPHAESTUS_RELEASE_ASSET_PATTERN", "*wheelhouse*.tar.gz")
DEFAULT_MANIFEST_PATTERN = os.environ.get(
    "HEPHAESTUS_RELEASE_MANIFEST_PATTERN", "*wheelhouse*.sha256"
)


_GITHUB_API = "https://api.github.com"
_USER_AGENT = "hephaestus-wheelhouse-client"
_BACKOFF_INITIAL = 0.5
_BACKOFF_FACTOR = 2.0

_CHECKSUM_LINE = re.compile(r"^(?P<digest>[0-9a-fA-F]{64})[ \t]+[*]?(?P<name>.+)$")


DEFAULT_TIMEOUT = 10.0
DEFAULT_MAX_RETRIES = 3


logger = logging.getLogger(__name__)


class ReleaseError(RuntimeError):
    """Raised when a release asset cannot be located or downloaded."""


@dataclass(slots=True)
class ReleaseAsset:
    """Metadata for a release asset."""

    name: str
    download_url: str
    size: int


@dataclass(slots=True)
class ReleaseDownload:
    """Details about a downloaded wheelhouse archive."""

    asset: ReleaseAsset
    archive_path: Path
    extracted_path: Path | None
    manifest_path: Path | None = None

    @property
    def wheel_directory(self) -> Path:
        """Directory containing wheel files."""

        if self.extracted_path is not None:
            return self.extracted_path
        return self.archive_path.parent


def default_download_dir() -> Path:
    """Return a cross-platform cache directory for wheelhouse downloads."""

    env_override = os.environ.get("HEPHAESTUS_RELEASE_CACHE")
    if env_override:
        return Path(env_override).expanduser().resolve()

    if sys.platform.startswith("win"):
        base = Path(os.environ.get("LOCALAPPDATA", Path.home() / "AppData" / "Local"))
    elif sys.platform == "darwin":
        base = Path.home() / "Library" / "Caches"
    else:
        base = Path(os.environ.get("XDG_CACHE_HOME", Path.home() / ".cache"))

    return base / "hephaestus" / "wheelhouses"


DEFAULT_DOWNLOAD_DIRECTORY = default_download_dir()


def _sanitize_asset_name(name: str) -> str:
    """Return a filesystem-safe asset name and log when modifications occur."""

    normalized = name.replace("\\", "/")
    base_name = PurePosixPath(normalized).name
    if base_name in {"", ".", ".."}:
        raise ReleaseError("Asset name resolved to an empty or unsafe value after sanitisation.")

    candidate = base_name.replace("..", "_")

    if not candidate or candidate in {".", ""}:
        raise ReleaseError("Asset name resolved to an empty or unsafe value after sanitisation.")

    if candidate != name:
        log_event(
            logger,
            "release.asset.sanitised",
            level=logging.WARNING,
            message=(
                f"Sanitised asset name from {name!r} to {candidate!r} to prevent path traversal."
            ),
            original_name=name,
            sanitised_name=candidate,
        )

    return candidate


def _open_with_retries(
    request: urllib.request.Request,
    *,
    timeout: float,
    max_retries: int,
    description: str,
) -> IO[bytes]:
    attempt = 0
    delay = _BACKOFF_INITIAL
    last_error: Exception | None = None

    while attempt < max_retries:
        attempt += 1
        try:
            response = urllib.request.urlopen(  # nosec B310 - HTTPS enforced by callers
                request,
                timeout=timeout,
            )
            return cast(IO[bytes], response)
        except urllib.error.HTTPError as exc:
            last_error = exc
            if exc.code >= 500 and attempt < max_retries:
                log_event(
                    logger,
                    "release.http.retry",
                    level=logging.WARNING,
                    message=(
                        f"{description} failed with HTTP {exc.code} on attempt "
                        f"{attempt}/{max_retries}; retrying in {delay:.1f}s."
                    ),
                    description=description,
                    http_status=exc.code,
                    attempt=attempt,
                    max_retries=max_retries,
                    backoff_seconds=delay,
                    url=request.full_url,
                )
            else:
                raise
        except urllib.error.URLError as exc:  # pragma: no cover - network dependent
            last_error = exc
            if attempt >= max_retries:
                break
            log_event(
                logger,
                "release.network.retry",
                level=logging.WARNING,
                message=(
                    f"{description} failed on attempt {attempt}/{max_retries}: "
                    f"{getattr(exc, 'reason', exc)}; retrying in {delay:.1f}s."
                ),
                description=description,
                attempt=attempt,
                max_retries=max_retries,
                backoff_seconds=delay,
                reason=str(getattr(exc, "reason", exc)),
                url=request.full_url,
            )

        time.sleep(delay)
        delay *= _BACKOFF_FACTOR

    if last_error:
        raise last_error
    raise ReleaseError(f"Failed to complete {description} after {max_retries} attempts.")


def _build_request(
    url: str, token: str | None, accept: str = "application/vnd.github+json"
) -> urllib.request.Request:
    request = urllib.request.Request(url)
    request.add_header("Accept", accept)
    request.add_header("User-Agent", _USER_AGENT)
    if token:
        request.add_header("Authorization", f"Bearer {token}")
    return request


def _fetch_release(
    repository: str,
    tag: str | None,
    token: str | None,
    *,
    timeout: float = DEFAULT_TIMEOUT,
    max_retries: int = DEFAULT_MAX_RETRIES,
) -> dict:
    owner_repo = repository.strip()
    if not owner_repo or "/" not in owner_repo:
        raise ReleaseError(
            "Repository must be provided as 'owner/repository'. Received: " + repr(repository)
        )

    if timeout <= 0:
        raise ReleaseError(f"Timeout must be positive, got {timeout}")

    if max_retries < 1:
        raise ReleaseError(f"Max retries must be at least 1, got {max_retries}")

    if tag:
        url = f"{_GITHUB_API}/repos/{owner_repo}/releases/tags/{tag}"
    else:
        url = f"{_GITHUB_API}/repos/{owner_repo}/releases/latest"

    if not url.startswith("https://"):
        raise ReleaseError(f"Unsupported release URL scheme: {url}")

    try:
        with _open_with_retries(
            _build_request(url, token),
            timeout=timeout,
            max_retries=max_retries,
            description="GitHub release metadata",
        ) as response:
            payload = response.read()
    except urllib.error.HTTPError as exc:  # pragma: no cover - network failures vary
        if exc.code == 404:
            raise ReleaseError(
                f"Release not found for repository {owner_repo!r} (tag={tag!r})."
            ) from exc
        raise ReleaseError(f"GitHub API responded with HTTP {exc.code}: {exc.reason}") from exc
    except urllib.error.URLError as exc:  # pragma: no cover
        raise ReleaseError(f"Failed to contact GitHub: {exc.reason}") from exc

    try:
        data = json.loads(payload)
    except json.JSONDecodeError as exc:  # pragma: no cover - defensive
        raise ReleaseError("Unable to decode GitHub API response as JSON.") from exc

    if not isinstance(data, dict) or "assets" not in data:
        raise ReleaseError("GitHub API response did not include assets metadata.")
    return data


def _pick_asset(release_data: dict, asset_pattern: str) -> ReleaseAsset:
    assets = release_data.get("assets", [])
    for asset in assets:
        name = asset.get("name", "")
        sanitized = _sanitize_asset_name(name)
        if asset_pattern and not fnmatch(name, asset_pattern):
            continue
        download_url = asset.get("browser_download_url") or asset.get("url")
        if not download_url:
            continue
        size = int(asset.get("size", 0))
        return ReleaseAsset(name=sanitized, download_url=str(download_url), size=size)
    available = ", ".join(asset.get("name", "<unnamed>") for asset in assets)
    raise ReleaseError(
        "Could not find asset matching pattern"
        f" {asset_pattern!r}. Available assets: {available or 'none found.'}"
    )


def _download_asset(
    asset: ReleaseAsset,
    destination: Path,
    token: str | None,
    overwrite: bool,
    *,
    timeout: float = DEFAULT_TIMEOUT,
    max_retries: int = DEFAULT_MAX_RETRIES,
) -> Path:
    if timeout <= 0:
        raise ReleaseError(f"Timeout must be positive, got {timeout}")

    if max_retries < 1:
        raise ReleaseError(f"Max retries must be at least 1, got {max_retries}")

    destination.parent.mkdir(parents=True, exist_ok=True)
    if destination.exists() and not overwrite:
        raise ReleaseError(
            f"Destination file {destination} already exists. Use overwrite=True to replace it."
        )

    if not asset.download_url.startswith("https://"):
        raise ReleaseError(f"Unsupported download URL scheme: {asset.download_url}")

    request = _build_request(asset.download_url, token, accept="application/octet-stream")
    try:
        with (
            _open_with_retries(
                request,
                timeout=timeout,
                max_retries=max_retries,
                description=f"Download of {asset.name}",
            ) as response,
            destination.open("wb") as fh,
        ):
            shutil.copyfileobj(response, fh)
    except urllib.error.HTTPError as exc:  # pragma: no cover - network dependent
        raise ReleaseError(f"Failed to download asset: HTTP {exc.code} {exc.reason}") from exc
    except urllib.error.URLError as exc:  # pragma: no cover
        raise ReleaseError(f"Failed to download asset: {exc.reason}") from exc
    return destination


def _hash_file(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as fh:
        for chunk in iter(lambda: fh.read(65536), b""):
            digest.update(chunk)
    return digest.hexdigest()


def _parse_checksum_manifest(manifest_text: str) -> dict[str, str]:
    checksums: dict[str, str] = {}
    for idx, raw_line in enumerate(manifest_text.splitlines(), start=1):
        line = raw_line.strip()
        if not line or line.startswith("#"):
            continue

        match = _CHECKSUM_LINE.match(line)
        if not match:
            raise ReleaseError(
                f"Invalid checksum manifest entry on line {idx}: {raw_line!r}."
            )

        digest = match.group("digest").lower()
        asset_name = match.group("name").strip()
        sanitized_name = _sanitize_asset_name(asset_name)
        if sanitized_name in checksums and checksums[sanitized_name] != digest:
            raise ReleaseError(
                f"Conflicting checksum entries for {sanitized_name!r} in manifest."
            )
        checksums[sanitized_name] = digest

    if not checksums:
        raise ReleaseError("Checksum manifest did not contain any entries.")

    return checksums


def extract_archive(
    archive_path: Path, destination: Path | None = None, overwrite: bool = False
) -> Path:
    """Extract a wheelhouse archive (tar.gz) and return the directory containing wheels."""

    archive_path = archive_path.resolve()
    if destination is None:
        destination = archive_path.parent / archive_path.stem.replace(".tar", "")
    destination = destination.resolve()

    if destination.exists():
        if not overwrite:
            raise ReleaseError(f"Destination directory {destination} already exists.")
        if destination.is_dir():
            shutil.rmtree(destination)
        else:  # pragma: no cover - defensive
            destination.unlink()

    destination.mkdir(parents=True, exist_ok=True)

    if not tarfile.is_tarfile(archive_path):
        raise ReleaseError(f"Archive {archive_path} is not a valid tar file.")

    def _is_within_directory(directory: Path, target: Path) -> bool:
        try:
            directory = directory.resolve(strict=False)
            target = target.resolve(strict=False)
        except FileNotFoundError:
            return False
        return str(target).startswith(str(directory))

    with tarfile.open(archive_path, "r:gz") as archive:
        for member in archive.getmembers():
            member_path = destination / member.name
            if not _is_within_directory(destination, member_path):
                raise ReleaseError(
                    f"Refusing to extract {member.name!r} outside destination {destination}."
                )
            archive.extract(  # nosec - safe members validated above
                member,
                destination,
                set_attrs=False,
                filter="data",
            )

    return destination


def install_from_directory(
    wheel_directory: Path,
    *,
    python_executable: str | None = None,
    pip_args: Sequence[str] | None = None,
    upgrade: bool = True,
) -> None:
    """Install all wheel files in *wheel_directory* using pip."""

    wheel_directory = wheel_directory.resolve()
    if not wheel_directory.exists() or not wheel_directory.is_dir():
        raise ReleaseError(f"Wheel directory {wheel_directory} does not exist.")

    wheels = sorted(wheel_directory.glob("*.whl"))
    if not wheels:
        raise ReleaseError(f"No wheel files were found in {wheel_directory}.")

    log_event(
        logger,
        "release.install.start",
        message=f"Installing {len(wheels)} wheel(s) from {wheel_directory}",
        wheels=len(wheels),
        directory=str(wheel_directory),
        python_executable=python_executable,
        upgrade=upgrade,
    )

    python_executable = python_executable or sys.executable
    cmd: list[str] = [python_executable, "-m", "pip", "install"]
    if upgrade:
        cmd.append("--upgrade")
    if pip_args:
        cmd.extend(pip_args)
    cmd.extend(str(wheel) for wheel in wheels)

    log_event(
        logger,
        "release.install.invoke",
        message="Running pip install command",
        command=cmd,
    )
    subprocess.check_call(cmd)
    log_event(
        logger,
        "release.install.complete",
        message="Installation completed successfully",
        wheels=len(wheels),
        directory=str(wheel_directory),
    )


def download_wheelhouse(
    *,
    repository: str,
    destination_dir: Path,
    tag: str | None = None,
    asset_pattern: str = DEFAULT_ASSET_PATTERN,
    manifest_pattern: str | None = DEFAULT_MANIFEST_PATTERN,
    token: str | None = None,
    overwrite: bool = False,
    extract: bool = True,
    allow_unsigned: bool = False,
    extract_dir: Path | None = None,
    timeout: float = DEFAULT_TIMEOUT,
    max_retries: int = DEFAULT_MAX_RETRIES,
) -> ReleaseDownload:
    """Download a wheelhouse archive from a GitHub release."""

    with log_context(repository=repository, tag=tag or "latest"):
        log_event(
            logger,
            "release.metadata.fetch",
            message=(
                f"Fetching release metadata for repository {repository} (tag={tag or 'latest'})"
            ),
        )
        release_data = _fetch_release(
            repository,
            tag,
            token,
            timeout=timeout,
            max_retries=max_retries,
        )
        asset = _pick_asset(release_data, asset_pattern)
        log_event(
            logger,
            "release.asset.selected",
            message=f"Selected asset: {asset.name} (size={asset.size} bytes)",
            asset=asset.name,
            size=asset.size,
        )

    destination_dir = destination_dir.resolve()
    destination_dir.mkdir(parents=True, exist_ok=True)
    archive_path = destination_dir / asset.name

    log_event(
        logger,
        "release.download.start",
        message=f"Downloading asset to {archive_path}",
        asset=asset.name,
        destination=str(archive_path),
        overwrite=overwrite,
    )
    _download_asset(
        asset,
        archive_path,
        token,
        overwrite=overwrite,
        timeout=timeout,
        max_retries=max_retries,
    )
    log_event(
        logger,
        "release.download.complete",
        message="Download completed successfully",
        asset=asset.name,
        destination=str(archive_path),
    )

    manifest_path: Path | None = None
    if not allow_unsigned:
        if not manifest_pattern:
            raise ReleaseError(
                "Checksum verification requires a manifest pattern when allow_unsigned is False."
            )
        log_event(
            logger,
            "release.manifest.locate",
            message=f"Locating checksum manifest matching {manifest_pattern}",
            pattern=manifest_pattern,
        )
        try:
            manifest_asset = _pick_asset(release_data, manifest_pattern)
        except ReleaseError as exc:
            raise ReleaseError(
                "Required checksum manifest could not be found; rerun with --allow-unsigned to "
                "bypass verification if you explicitly trust the source."
            ) from exc

        manifest_path = destination_dir / manifest_asset.name
        log_event(
            logger,
            "release.manifest.download",
            message=f"Downloading checksum manifest to {manifest_path}",
            manifest=manifest_asset.name,
            destination=str(manifest_path),
        )
        _download_asset(
            manifest_asset,
            manifest_path,
            token,
            overwrite=True,
            timeout=timeout,
            max_retries=max_retries,
        )

        manifest_checksums = _parse_checksum_manifest(
            manifest_path.read_text(encoding="utf-8")
        )

        expected_digest = manifest_checksums.get(asset.name)
        if expected_digest is None:
            raise ReleaseError(
                f"Checksum manifest does not include an entry for {asset.name!r}."
            )

        actual_digest = _hash_file(archive_path)
        if actual_digest != expected_digest:
            raise ReleaseError(
                "Checksum verification failed for asset "
                f"{asset.name!r}: expected {expected_digest}, got {actual_digest}."
            )

        log_event(
            logger,
            "release.manifest.verified",
            message=f"Checksum verified for {asset.name}",
            asset=asset.name,
        )
    else:
        log_event(
            logger,
            "release.manifest.skipped",
            level=logging.WARNING,
            message=(
                f"Checksum verification disabled for {asset.name}; accepting unsigned asset."
            ),
            asset=asset.name,
        )

    extracted: Path | None = None
    if extract:
        log_event(
            logger,
            "release.extract.start",
            message=f"Extracting archive to {extract_dir or destination_dir}",
            destination=str(extract_dir or destination_dir),
            overwrite=overwrite,
        )
        extracted = extract_archive(archive_path, destination=extract_dir, overwrite=overwrite)
        log_event(
            logger,
            "release.extract.complete",
            message=f"Extraction completed: {extracted}",
            destination=str(extracted),
        )

    return ReleaseDownload(
        asset=asset,
        archive_path=archive_path,
        extracted_path=extracted,
        manifest_path=manifest_path,
    )


def install_from_archive(
    archive_path: Path,
    *,
    python_executable: str | None = None,
    pip_args: Sequence[str] | None = None,
    upgrade: bool = True,
    cleanup: bool = False,
) -> Path:
    """Extract *archive_path* and install all contained wheel files."""

    extracted_dir = extract_archive(archive_path, overwrite=True)
    try:
        install_from_directory(
            extracted_dir,
            python_executable=python_executable,
            pip_args=pip_args,
            upgrade=upgrade,
        )
    finally:
        if cleanup:
            shutil.rmtree(extracted_dir, ignore_errors=True)
    return extracted_dir


__all__ += ["install_from_archive"]
