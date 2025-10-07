"""Helpers for consuming wheelhouse archives published to GitHub releases.

The goal of this module is to make Hephaestus' release artefacts easy to reuse from
any project.  All interactions rely solely on the Python standard library so the
helpers work on Linux, macOS, and Windows runners without extra dependencies.
"""

from __future__ import annotations

import json
import logging
import os
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
from typing import IO

__all__ = [
    "DEFAULT_ASSET_PATTERN",
    "DEFAULT_REPOSITORY",
    "DEFAULT_DOWNLOAD_DIRECTORY",
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


_GITHUB_API = "https://api.github.com"
_USER_AGENT = "hephaestus-wheelhouse-client"
_BACKOFF_INITIAL = 0.5
_BACKOFF_FACTOR = 2.0


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
    candidate = PurePosixPath(normalized).name
    candidate = candidate.replace("..", "_")

    if not candidate or candidate in {".", ""}:
        raise ReleaseError("Asset name resolved to an empty or unsafe value after sanitisation.")

    if candidate != name:
        logger.warning(
            "Sanitised asset name from %r to %r to prevent path traversal.",
            name,
            candidate,
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
            return urllib.request.urlopen(  # nosec B310 - HTTPS enforced by callers
                request,
                timeout=timeout,
            )
        except urllib.error.HTTPError as exc:
            last_error = exc
            if exc.code >= 500 and attempt < max_retries:
                logger.warning(
                    "%s failed with HTTP %s on attempt %s/%s; retrying in %.1fs.",
                    description,
                    exc.code,
                    attempt,
                    max_retries,
                    delay,
                )
            else:
                raise
        except urllib.error.URLError as exc:  # pragma: no cover - network dependent
            last_error = exc
            if attempt >= max_retries:
                break
            logger.warning(
                "%s failed on attempt %s/%s: %s; retrying in %.1fs.",
                description,
                attempt,
                max_retries,
                getattr(exc, "reason", exc),
                delay,
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

    python_executable = python_executable or sys.executable
    cmd: list[str] = [python_executable, "-m", "pip", "install"]
    if upgrade:
        cmd.append("--upgrade")
    if pip_args:
        cmd.extend(pip_args)
    cmd.extend(str(wheel) for wheel in wheels)

    subprocess.check_call(cmd)


def download_wheelhouse(
    *,
    repository: str,
    destination_dir: Path,
    tag: str | None = None,
    asset_pattern: str = DEFAULT_ASSET_PATTERN,
    token: str | None = None,
    overwrite: bool = False,
    extract: bool = True,
    extract_dir: Path | None = None,
    timeout: float = DEFAULT_TIMEOUT,
    max_retries: int = DEFAULT_MAX_RETRIES,
) -> ReleaseDownload:
    """Download a wheelhouse archive from a GitHub release."""

    release_data = _fetch_release(
        repository,
        tag,
        token,
        timeout=timeout,
        max_retries=max_retries,
    )
    asset = _pick_asset(release_data, asset_pattern)

    destination_dir = destination_dir.resolve()
    destination_dir.mkdir(parents=True, exist_ok=True)
    archive_path = destination_dir / asset.name

    _download_asset(
        asset,
        archive_path,
        token,
        overwrite=overwrite,
        timeout=timeout,
        max_retries=max_retries,
    )

    extracted: Path | None = None
    if extract:
        extracted = extract_archive(archive_path, destination=extract_dir, overwrite=overwrite)

    return ReleaseDownload(asset=asset, archive_path=archive_path, extracted_path=extracted)


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
