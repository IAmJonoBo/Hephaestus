"""Helpers for consuming wheelhouse archives published to GitHub releases.

The goal of this module is to make Hephaestus' release artefacts easy to reuse from
any project.  All interactions rely solely on the Python standard library so the
helpers work on Linux, macOS, and Windows runners without extra dependencies.
"""

from __future__ import annotations

import base64
import binascii
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

from cryptography import x509
from cryptography.x509.oid import ExtensionOID

from hephaestus import events as telemetry, resource_forks
from hephaestus.logging import log_context

__all__ = [
    "DEFAULT_ASSET_PATTERN",
    "DEFAULT_REPOSITORY",
    "DEFAULT_DOWNLOAD_DIRECTORY",
    "DEFAULT_MANIFEST_PATTERN",
    "DEFAULT_SIGSTORE_BUNDLE_PATTERN",
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
DEFAULT_SIGSTORE_BUNDLE_PATTERN = os.environ.get(
    "HEPHAESTUS_RELEASE_SIGSTORE_PATTERN", "*wheelhouse*.sigstore"
)


_GITHUB_API = "https://api.github.com"
_USER_AGENT = "hephaestus-wheelhouse-client"
_BACKOFF_INITIAL = 0.5
_BACKOFF_FACTOR = 2.0

_CHECKSUM_LINE = re.compile(r"^(?P<digest>[0-9a-fA-F]{64})[ \t]+[*]?(?P<name>.+)$")

# GitHub token patterns (classic and fine-grained)
_GITHUB_TOKEN_PATTERNS = (
    re.compile(r"^gh[ps]_[A-Za-z0-9]{36,255}$"),  # Fine-grained and classic tokens
    re.compile(r"^github_pat_[A-Za-z0-9_]{82}$"),  # Personal access tokens (new format)
)

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
    sigstore_path: Path | None = None

    @property
    def wheel_directory(self) -> Path:
        """Directory containing wheel files."""

        if self.extracted_path is not None:
            return self.extracted_path
        return self.archive_path.parent


@dataclass(slots=True)
class SigstoreVerification:
    """Outcome of verifying a Sigstore bundle."""

    bundle_path: Path
    certificate_subject: str
    certificate_issuer: str
    identities: tuple[str, ...]


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
        telemetry.emit_event(
            logger,
            telemetry.RELEASE_ASSET_SANITISED,
            level=logging.WARNING,
            message=(
                f"Sanitised asset name from {name!r} to {candidate!r} to prevent path traversal."
            ),
            original_name=name,
            sanitised_name=candidate,
        )

    return candidate


def _sanitize_release_path(root: Path, *, action: str) -> None:
    """Sanitise *root* and fail if resource fork artefacts remain."""

    telemetry.emit_event(
        logger,
        telemetry.RELEASE_SANITIZE_START,
        message=f"Sanitising {action}.",
        root=str(root),
    )
    report = resource_forks.sanitize_path(root)
    if report.errors:
        failing_path, reason = report.errors[0]
        telemetry.emit_event(
            logger,
            telemetry.RELEASE_SANITIZE_FAILED,
            level=logging.ERROR,
            message=f"Failed to remove resource fork artefact during {action}.",
            root=str(root),
            artefacts=[str(path) for path, _ in report.errors],
            error=reason,
        )
        raise ReleaseError(
            f"Failed to remove resource fork artefact {failing_path} in {action}: {reason}"
        )

    remaining = resource_forks.verify_clean(root)
    if remaining:
        telemetry.emit_event(
            logger,
            telemetry.RELEASE_SANITIZE_FAILED,
            level=logging.ERROR,
            message=f"Resource fork artefacts detected after sanitising {action}.",
            root=str(root),
            artefacts=[str(path) for path in remaining],
        )
        formatted = ", ".join(str(path) for path in remaining)
        raise ReleaseError(f"Resource fork artefacts remain in {action}: {formatted}")

    telemetry.emit_event(
        logger,
        telemetry.RELEASE_SANITIZE_COMPLETE,
        message=f"Resource fork sanitisation completed for {action}.",
        root=str(root),
        removed=len(report.removed_paths),
    )


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
                telemetry.emit_event(
                    logger,
                    telemetry.RELEASE_HTTP_RETRY,
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
            telemetry.emit_event(
                logger,
                telemetry.RELEASE_NETWORK_RETRY,
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


def _validate_github_token(token: str | None) -> None:
    """Validate GitHub token format before use.

    Args:
        token: GitHub token to validate (can be None for public repos)

    Raises:
        ReleaseError: If token is provided but has invalid format
    """
    if token is None:
        # Token is optional for public repos
        return

    if not token.strip():
        raise ReleaseError(
            "GitHub token cannot be empty. "
            "Provide a valid token or omit it for public repositories."
        )

    # Check if token matches known GitHub token patterns
    if not any(pattern.match(token) for pattern in _GITHUB_TOKEN_PATTERNS):
        telemetry.emit_event(
            logger,
            telemetry.RELEASE_TOKEN_VALIDATION,
            level=logging.WARNING,
            message=(
                "GitHub token format does not match expected patterns. "
                "This may indicate an invalid or legacy token format."
            ),
        )


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

    # Validate token format before making API calls
    _validate_github_token(token)

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
        if exc.code == 401:
            raise ReleaseError(
                "GitHub authentication failed (HTTP 401). "
                "The provided token may be expired, invalid, or lack required permissions. "
                "Please verify your GITHUB_TOKEN environment variable or --token parameter."
            ) from exc
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


def _decode_sigstore_digest(value: str) -> bytes:
    try:
        return base64.b64decode(value, validate=True)
    except binascii.Error:
        try:
            return bytes.fromhex(value)
        except ValueError as exc:
            raise ReleaseError("Sigstore bundle contained an invalid digest encoding.") from exc


def _load_certificate(raw_bytes: str) -> x509.Certificate:
    try:
        decoded = base64.b64decode(raw_bytes, validate=True)
    except binascii.Error as exc:
        raise ReleaseError("Sigstore bundle certificate was not valid base64 data.") from exc

    try:
        return x509.load_der_x509_certificate(decoded)
    except ValueError as exc:  # pragma: no cover - defensive
        raise ReleaseError("Unable to parse Sigstore bundle certificate bytes.") from exc


def _verify_sigstore_bundle(
    bundle_path: Path,
    artifact_path: Path,
    *,
    identity_patterns: Sequence[str] | None = None,
) -> SigstoreVerification:
    try:
        payload = json.loads(bundle_path.read_text(encoding="utf-8"))
    except json.JSONDecodeError as exc:
        raise ReleaseError("Sigstore bundle was not valid JSON.") from exc

    if not isinstance(payload, dict):
        raise ReleaseError("Sigstore bundle did not contain the expected structure.")

    media_type = str(payload.get("mediaType", ""))
    if "application/vnd.dev.sigstore.bundle+json" not in media_type:
        raise ReleaseError("Sigstore bundle media type was not recognised.")

    message_signature = payload.get("messageSignature")
    if not isinstance(message_signature, dict):
        raise ReleaseError("Sigstore bundle missing messageSignature section.")

    digest_info = message_signature.get("messageDigest")
    if not isinstance(digest_info, dict):
        raise ReleaseError("Sigstore bundle missing messageDigest information.")

    algorithm = str(digest_info.get("algorithm", "")).lower()
    if algorithm not in {"sha2_256", "sha256"}:
        raise ReleaseError(f"Unsupported Sigstore digest algorithm: {algorithm or 'unknown'}")

    digest_value = digest_info.get("digest")
    if not isinstance(digest_value, str) or not digest_value:
        raise ReleaseError("Sigstore bundle missing digest value.")

    expected_digest = _decode_sigstore_digest(digest_value).hex()
    actual_digest = _hash_file(artifact_path)
    if expected_digest != actual_digest:
        raise ReleaseError("Sigstore bundle digest did not match the downloaded archive.")

    verification_material = payload.get("verificationMaterial", {})
    if not isinstance(verification_material, dict):
        raise ReleaseError("Sigstore bundle missing verification material.")

    chain = verification_material.get("x509CertificateChain", {})
    if not isinstance(chain, dict):
        raise ReleaseError("Sigstore bundle missing certificate chain information.")

    certificates = chain.get("certificates", [])
    if not isinstance(certificates, list) or not certificates:
        raise ReleaseError("Sigstore bundle did not include any certificates.")

    certificate_entry = certificates[0]
    if not isinstance(certificate_entry, dict):
        raise ReleaseError("Sigstore certificate entry was malformed.")

    raw_bytes = certificate_entry.get("rawBytes")
    if not isinstance(raw_bytes, str) or not raw_bytes:
        raise ReleaseError("Sigstore certificate entry missing rawBytes field.")

    certificate = _load_certificate(raw_bytes)

    subject = certificate.subject.rfc4514_string()
    issuer = certificate.issuer.rfc4514_string()
    identities: list[str] = [subject]

    try:
        san_ext = certificate.extensions.get_extension_for_oid(
            ExtensionOID.SUBJECT_ALTERNATIVE_NAME
        )
    except x509.ExtensionNotFound:
        san_ext = None

    if san_ext is not None:
        san = cast(x509.SubjectAlternativeName, san_ext.value)
        identities.extend(san.get_values_for_type(x509.UniformResourceIdentifier))
        identities.extend(san.get_values_for_type(x509.RFC822Name))

    deduped_identities = tuple(dict.fromkeys(identities))

    if identity_patterns:
        if not any(
            fnmatch(identity, pattern)
            for identity in deduped_identities
            for pattern in identity_patterns
        ):
            raise ReleaseError("Sigstore identity mismatch for downloaded archive.")

    return SigstoreVerification(
        bundle_path=bundle_path,
        certificate_subject=subject,
        certificate_issuer=issuer,
        identities=deduped_identities,
    )


def _parse_checksum_manifest(manifest_text: str) -> dict[str, str]:
    checksums: dict[str, str] = {}
    for idx, raw_line in enumerate(manifest_text.splitlines(), start=1):
        line = raw_line.strip()
        if not line or line.startswith("#"):
            continue

        match = _CHECKSUM_LINE.match(line)
        if not match:
            raise ReleaseError(f"Invalid checksum manifest entry on line {idx}: {raw_line!r}.")

        digest = match.group("digest").lower()
        asset_name = match.group("name").strip()
        sanitized_name = _sanitize_asset_name(asset_name)
        if sanitized_name in checksums and checksums[sanitized_name] != digest:
            raise ReleaseError(f"Conflicting checksum entries for {sanitized_name!r} in manifest.")
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

    _sanitize_release_path(destination, action="the extracted wheelhouse directory")
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

    _sanitize_release_path(wheel_directory, action="the wheel directory prior to installation")

    wheels = sorted(wheel_directory.glob("*.whl"))
    if not wheels:
        raise ReleaseError(f"No wheel files were found in {wheel_directory}.")

    telemetry.emit_event(
        logger,
        telemetry.RELEASE_INSTALL_START,
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

    telemetry.emit_event(
        logger,
        telemetry.RELEASE_INSTALL_INVOKE,
        message="Running pip install command",
        command=cmd,
    )
    subprocess.check_call(cmd)
    telemetry.emit_event(
        logger,
        telemetry.RELEASE_INSTALL_COMPLETE,
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
    sigstore_bundle_pattern: str | None = DEFAULT_SIGSTORE_BUNDLE_PATTERN,
    token: str | None = None,
    overwrite: bool = False,
    extract: bool = True,
    allow_unsigned: bool = False,
    require_sigstore: bool = False,
    sigstore_identities: Sequence[str] | None = None,
    extract_dir: Path | None = None,
    timeout: float = DEFAULT_TIMEOUT,
    max_retries: int = DEFAULT_MAX_RETRIES,
) -> ReleaseDownload:
    """Download a wheelhouse archive from a GitHub release."""

    if allow_unsigned and require_sigstore:
        raise ReleaseError(
            "Sigstore attestation cannot be required when allow_unsigned is enabled."
        )

    with log_context(repository=repository, tag=tag or "latest"):
        telemetry.emit_event(
            logger,
            telemetry.RELEASE_METADATA_FETCH,
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
        telemetry.emit_event(
            logger,
            telemetry.RELEASE_ASSET_SELECTED,
            message=f"Selected asset: {asset.name} (size={asset.size} bytes)",
            asset=asset.name,
            size=asset.size,
        )

    destination_dir = destination_dir.resolve()
    destination_dir.mkdir(parents=True, exist_ok=True)
    archive_path = destination_dir / asset.name

    telemetry.emit_event(
        logger,
        telemetry.RELEASE_DOWNLOAD_START,
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
    telemetry.emit_event(
        logger,
        telemetry.RELEASE_DOWNLOAD_COMPLETE,
        message="Download completed successfully",
        asset=asset.name,
        destination=str(archive_path),
    )

    manifest_path: Path | None = None
    sigstore_path: Path | None = None
    if not allow_unsigned:
        if not manifest_pattern:
            raise ReleaseError(
                "Checksum verification requires a manifest pattern when allow_unsigned is False."
            )
        telemetry.emit_event(
            logger,
            telemetry.RELEASE_MANIFEST_LOCATE,
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
        telemetry.emit_event(
            logger,
            telemetry.RELEASE_MANIFEST_DOWNLOAD,
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

        manifest_checksums = _parse_checksum_manifest(manifest_path.read_text(encoding="utf-8"))

        expected_digest = manifest_checksums.get(asset.name)
        if expected_digest is None:
            raise ReleaseError(f"Checksum manifest does not include an entry for {asset.name!r}.")

        actual_digest = _hash_file(archive_path)
        if actual_digest != expected_digest:
            raise ReleaseError(
                "Checksum verification failed for asset "
                f"{asset.name!r}: expected {expected_digest}, got {actual_digest}."
            )

        telemetry.emit_event(
            logger,
            telemetry.RELEASE_MANIFEST_VERIFIED,
            message=f"Checksum verified for {asset.name}",
            asset=asset.name,
            digest=actual_digest,
        )

        if sigstore_bundle_pattern is not None:
            telemetry.emit_event(
                logger,
                telemetry.RELEASE_SIGSTORE_LOCATE,
                message=f"Locating Sigstore bundle matching {sigstore_bundle_pattern}",
                pattern=sigstore_bundle_pattern,
            )
            try:
                sigstore_asset = _pick_asset(release_data, sigstore_bundle_pattern)
            except ReleaseError as exc:
                if require_sigstore:
                    raise ReleaseError(
                        "Sigstore attestation required but not found; rerun with --allow-unsigned "
                        "if you explicitly trust the source."
                    ) from exc
                telemetry.emit_event(
                    logger,
                    telemetry.RELEASE_SIGSTORE_MISSING,
                    level=logging.WARNING,
                    message=(
                        "Sigstore bundle not published for this release; continuing after checksum "
                        "verification."
                    ),
                    pattern=sigstore_bundle_pattern,
                )
            else:
                sigstore_path = destination_dir / sigstore_asset.name
                telemetry.emit_event(
                    logger,
                    telemetry.RELEASE_SIGSTORE_DOWNLOAD,
                    message=f"Downloading Sigstore bundle to {sigstore_path}",
                    bundle=sigstore_asset.name,
                    destination=str(sigstore_path),
                )
                _download_asset(
                    sigstore_asset,
                    sigstore_path,
                    token,
                    overwrite=True,
                    timeout=timeout,
                    max_retries=max_retries,
                )

                verification = _verify_sigstore_bundle(
                    sigstore_path,
                    archive_path,
                    identity_patterns=sigstore_identities,
                )
                telemetry.emit_event(
                    logger,
                    telemetry.RELEASE_SIGSTORE_VERIFIED,
                    message="Sigstore attestation verified",
                    subject=verification.certificate_subject,
                    issuer=verification.certificate_issuer,
                    identities=list(verification.identities),
                )
        elif require_sigstore:
            raise ReleaseError("Sigstore attestation required but no bundle pattern was provided.")
    else:
        telemetry.emit_event(
            logger,
            telemetry.RELEASE_MANIFEST_SKIPPED,
            level=logging.WARNING,
            message=(f"Checksum verification disabled for {asset.name}; accepting unsigned asset."),
            asset=asset.name,
        )

    extracted: Path | None = None
    if extract:
        telemetry.emit_event(
            logger,
            telemetry.RELEASE_EXTRACT_START,
            message=f"Extracting archive to {extract_dir or destination_dir}",
            destination=str(extract_dir or destination_dir),
            overwrite=overwrite,
        )
        extracted = extract_archive(archive_path, destination=extract_dir, overwrite=overwrite)
        telemetry.emit_event(
            logger,
            telemetry.RELEASE_EXTRACT_COMPLETE,
            message=f"Extraction completed: {extracted}",
            destination=str(extracted),
        )

    return ReleaseDownload(
        asset=asset,
        archive_path=archive_path,
        extracted_path=extracted,
        manifest_path=manifest_path,
        sigstore_path=sigstore_path,
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
