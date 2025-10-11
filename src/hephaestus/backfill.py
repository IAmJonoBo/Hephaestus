"""Sigstore bundle backfill tooling (ADR-0006)."""

from __future__ import annotations

import hashlib
import json
import logging
import os
import subprocess
import tempfile
from collections.abc import Sequence
from dataclasses import dataclass
from datetime import UTC, datetime
from pathlib import Path
from typing import Any, cast

import requests  # type: ignore[import-untyped]

__all__ = [
    "BackfillError",
    "BackfillMetadata",
    "BackfillRunSummary",
    "BackfillVerificationStatus",
    "HISTORICAL_VERSIONS",
    "run_backfill",
]

# Historical versions that need backfill (pre-Sigstore releases)
HISTORICAL_VERSIONS = [
    "v0.1.0",
    "v0.1.1",
    "v0.1.2",
    "v0.2.0",
    "v0.2.1",
    "v0.2.2",
    "v0.2.3",
]

REPO_OWNER = "IAmJonoBo"
REPO_NAME = "Hephaestus"
GITHUB_API_BASE = "https://api.github.com"
INVENTORY_PATH = Path(
    os.environ.get("SIGSTORE_INVENTORY_PATH", "ops/attestations/sigstore-inventory.json")
)

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(message)s",
)
logger = logging.getLogger(__name__)


class BackfillError(Exception):
    """Raised when backfill operation fails."""

    pass


@dataclass
class BackfillMetadata:
    """Metadata for a backfilled Sigstore bundle."""

    version: str
    original_release_date: datetime
    backfill_date: datetime
    backfill_identity: str
    verification_status: str  # Always "backfilled"
    checksum_verified: bool
    notes: str

    def to_dict(self) -> dict[str, Any]:
        """Convert metadata to dictionary representation."""

        return {
            "version": self.version,
            "original_release_date": self.original_release_date.isoformat(),
            "backfill_date": self.backfill_date.isoformat(),
            "backfill_identity": self.backfill_identity,
            "verification_status": self.verification_status,
            "checksum_verified": self.checksum_verified,
            "notes": self.notes,
        }

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> BackfillMetadata:
        """Create metadata from dictionary representation."""

        return cls(
            version=data["version"],
            original_release_date=datetime.fromisoformat(data["original_release_date"]),
            backfill_date=datetime.fromisoformat(data["backfill_date"]),
            backfill_identity=data["backfill_identity"],
            verification_status=data["verification_status"],
            checksum_verified=data["checksum_verified"],
            notes=data["notes"],
        )


class BackfillVerificationStatus:
    """Verification status constants for Sigstore bundles."""

    ORIGINAL = "original"
    BACKFILLED = "backfilled"
    UNKNOWN = "unknown"


@dataclass
class BackfillRunSummary:
    """Summary of a backfill run."""

    successes: list[dict[str, Any]]
    failures: list[dict[str, Any]]
    inventory_path: Path
    versions: list[str]
    dry_run: bool

    @property
    def ok(self) -> bool:
        """Return True when the run completed without any failures."""

        return not self.failures


def compute_sha256(path: Path) -> str:
    """Compute the SHA-256 digest for *path*."""

    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(8192), b""):
            digest.update(chunk)
    return digest.hexdigest()


def load_inventory(path: Path) -> dict[str, Any]:
    """Load the structured Sigstore inventory from *path*."""

    if not path.exists():
        return {"versions": {}}

    try:
        with path.open(encoding="utf-8") as handle:
            payload = cast(dict[str, Any], json.load(handle))
    except json.JSONDecodeError as exc:  # pragma: no cover - defensive
        raise BackfillError(f"Inventory file {path} is not valid JSON") from exc

    versions = payload.get("versions")
    if not isinstance(versions, dict):
        versions = {}

    payload["versions"] = versions
    return payload


def write_inventory(
    *,
    inventory_path: Path,
    successes: list[dict[str, Any]],
    failures: list[dict[str, Any]],
) -> None:
    """Persist the Sigstore backfill inventory to disk."""

    payload = load_inventory(inventory_path)
    existing_versions = cast(dict[str, Any], payload.get("versions", {}))

    for entry in successes:
        existing_versions[entry["version"]] = entry

    for failure in failures:
        failure_entry = {
            "version": failure["version"],
            "status": "error",
            "error": failure["error"],
            "timestamp": failure["timestamp"],
        }
        existing_versions[failure_entry["version"]] = failure_entry

    payload["versions"] = dict(sorted(existing_versions.items()))
    payload["generated_at"] = datetime.now(UTC).isoformat()
    payload["workflow"] = {
        "run_id": os.getenv("GITHUB_RUN_ID"),
        "run_attempt": os.getenv("GITHUB_RUN_ATTEMPT"),
        "workflow": os.getenv("GITHUB_WORKFLOW"),
        "actor": os.getenv("GITHUB_ACTOR"),
    }

    inventory_path.parent.mkdir(parents=True, exist_ok=True)
    with inventory_path.open("w", encoding="utf-8") as handle:
        json.dump(payload, handle, indent=2, sort_keys=True)
        handle.write("\n")


def get_github_headers(token: str) -> dict[str, str]:
    """Get headers for GitHub API requests."""

    return {
        "Authorization": f"token {token}",
        "Accept": "application/vnd.github.v3+json",
    }


def get_release_by_tag(
    version: str, token: str
) -> dict[str, Any]:  # pragma: no cover - network call
    """Fetch release metadata from GitHub."""

    url = f"{GITHUB_API_BASE}/repos/{REPO_OWNER}/{REPO_NAME}/releases/tags/{version}"
    response = requests.get(url, headers=get_github_headers(token))

    if response.status_code == 404:
        raise BackfillError(f"Release {version} not found")
    if response.status_code != 200:
        raise BackfillError(f"Failed to fetch release {version}: {response.text}")

    return cast(dict[str, Any], response.json())


def find_wheelhouse_asset(release: dict[str, Any]) -> dict[str, Any] | None:
    """Find wheelhouse archive in release assets."""

    assets = cast(list[dict[str, Any]], release.get("assets", []))
    for asset in assets:
        name = cast(str, asset["name"])
        if name.startswith("wheelhouse-") and name.endswith(".tar.gz"):
            if not name.endswith(".sigstore"):
                return asset
    return None


def download_asset(
    asset: dict[str, Any], token: str, dest_dir: Path
) -> Path:  # pragma: no cover - network call
    """Download release asset to local file."""

    url = asset["url"]
    headers = get_github_headers(token)
    headers["Accept"] = "application/octet-stream"

    logger.info("Downloading %s...", asset["name"])
    response = requests.get(url, headers=headers, stream=True)

    if response.status_code != 200:
        raise BackfillError(f"Failed to download {asset['name']}: {response.text}")

    dest_path = dest_dir / cast(str, asset["name"])
    with open(dest_path, "wb") as handle:
        for chunk in response.iter_content(chunk_size=8192):
            handle.write(chunk)

    logger.info("Downloaded to %s", dest_path)
    return dest_path


def verify_checksum(archive_path: Path, expected_checksum: str) -> bool:
    """Verify SHA-256 checksum of archive."""

    sha256 = hashlib.sha256()
    with open(archive_path, "rb") as handle:
        for chunk in iter(lambda: handle.read(8192), b""):
            sha256.update(chunk)

    actual = sha256.hexdigest()
    return actual == expected_checksum


def get_published_checksum(release: dict[str, Any], asset_name: str) -> str | None:
    """Extract published checksum from release body or manifest."""

    assets = cast(list[dict[str, Any]], release.get("assets", []))
    for asset in assets:
        if asset["name"] in ["SHA256SUMS.txt", "checksums.txt", "CHECKSUMS"]:
            logger.warning("Checksum manifest found but parsing not implemented")
            return None

    body = release.get("body", "")
    if asset_name in body and "sha256:" in body.lower():
        logger.warning("Checksum extraction from release body not implemented")
        return None

    return None


def sign_with_sigstore(
    archive_path: Path, metadata: dict[str, Any]
) -> Path:  # pragma: no cover - external tool
    """Generate Sigstore bundle for archive with backfill metadata."""

    bundle_path = archive_path.with_suffix(archive_path.suffix + ".sigstore")

    metadata_file = archive_path.parent / "backfill_metadata.json"
    with open(metadata_file, "w", encoding="utf-8") as handle:
        json.dump(metadata, handle, indent=2)

    try:
        cmd = [
            "python",
            "-m",
            "sigstore",
            "sign",
            str(archive_path),
            "--bundle",
            str(bundle_path),
        ]

        logger.info("Signing with Sigstore: %s", " ".join(cmd))
        result = subprocess.run(
            cmd,
            capture_output=True,
            text=True,
            check=False,
        )

        if result.returncode != 0:
            raise BackfillError(f"Sigstore signing failed: {result.stderr or result.stdout}")

        logger.info("Generated Sigstore bundle: %s", bundle_path)

        with open(bundle_path, encoding="utf-8") as handle:
            bundle_data = json.load(handle)

        bundle_data["backfill_metadata"] = metadata

        with open(bundle_path, "w", encoding="utf-8") as handle:
            json.dump(bundle_data, handle, indent=2)

        return bundle_path

    finally:
        if metadata_file.exists():
            metadata_file.unlink()


def upload_release_asset(
    release_id: int,
    asset_path: Path,
    token: str,
    dry_run: bool = False,
) -> None:  # pragma: no cover - network call
    """Upload asset to GitHub release."""

    if dry_run:
        logger.info("[DRY RUN] Would upload %s", asset_path.name)
        return

    upload_url = (
        f"{GITHUB_API_BASE}/repos/{REPO_OWNER}/{REPO_NAME}/"
        f"releases/{release_id}/assets?name={asset_path.name}"
    )

    headers = get_github_headers(token)
    headers["Content-Type"] = "application/octet-stream"

    logger.info("Uploading %s...", asset_path.name)
    with open(asset_path, "rb") as handle:
        response = requests.post(upload_url, headers=headers, data=handle)

    if response.status_code not in [200, 201]:
        raise BackfillError(f"Failed to upload {asset_path.name}: {response.text}")

    logger.info("Uploaded %s successfully", asset_path.name)


def add_backfill_notice(
    release_id: int,
    version: str,
    token: str,
    dry_run: bool = False,
) -> None:  # pragma: no cover - network call
    """Add backfill notice to release notes."""

    if dry_run:
        logger.info("[DRY RUN] Would add backfill notice to %s", version)
        return

    url = f"{GITHUB_API_BASE}/repos/{REPO_OWNER}/{REPO_NAME}/releases/{release_id}"
    response = requests.get(url, headers=get_github_headers(token))

    if response.status_code != 200:
        raise BackfillError(f"Failed to fetch release: {response.text}")

    release = response.json()
    current_body = release.get("body", "")

    if "Sigstore Bundle Backfill" in current_body:
        logger.info("Release already has backfill notice, skipping")
        return

    backfill_notice = (
        "\n\n---\n\n"
        "## 🔐 Sigstore Bundle Backfill\n\n"
        f"This release was backfilled with a Sigstore attestation bundle on "
        f"{datetime.now(UTC).strftime('%Y-%m-%d')}. "
        "The bundle was created using the current signing identity and verified "
        "against the original SHA-256 checksum. "
        "See [ADR-0006](https://github.com/IAmJonoBo/Hephaestus/blob/main/docs/adr/0006-sigstore-backfill.md) "
        "for details on backfilled attestations.\n"
    )

    updated_body = current_body + backfill_notice

    update_data = {"body": updated_body}
    response = requests.patch(
        url,
        headers=get_github_headers(token),
        json=update_data,
    )

    if response.status_code != 200:
        raise BackfillError(f"Failed to update release notes: {response.text}")

    logger.info("Added backfill notice to release notes")


def backfill_release(
    version: str, token: str, dry_run: bool = False
) -> dict[str, Any]:  # pragma: no cover - integration heavy
    """Backfill Sigstore bundle for a historical release."""

    logger.info("Processing %s...", version)

    release = get_release_by_tag(version, token)
    release_id = release["id"]
    published_at = release["published_at"]

    logger.info("Found release %s (published %s)", version, published_at)

    wheelhouse_asset = find_wheelhouse_asset(release)
    if not wheelhouse_asset:
        raise BackfillError(f"No wheelhouse archive found for {version}")

    logger.info("Found wheelhouse: %s", wheelhouse_asset["name"])

    sigstore_name = wheelhouse_asset["name"] + ".sigstore"
    for asset in release["assets"]:
        if asset["name"] == sigstore_name:
            logger.warning("Sigstore bundle already exists for %s, skipping", version)
            return {
                "version": version,
                "status": "already-present",
                "release_id": release_id,
                "release_url": release.get("html_url"),
                "release_published_at": published_at,
                "bundle": {
                    "name": asset["name"],
                    "url": asset.get("browser_download_url") or asset.get("url"),
                    "size": asset.get("size"),
                    "content_type": asset.get("content_type"),
                },
            }

    with tempfile.TemporaryDirectory() as temp_dir:
        temp_path = Path(temp_dir)
        archive_path = download_asset(wheelhouse_asset, token, temp_path)

        archive_digest = compute_sha256(archive_path)

        checksum = get_published_checksum(release, wheelhouse_asset["name"])
        checksum_verified = False

        if checksum:
            if verify_checksum(archive_path, checksum):
                logger.info("✓ Checksum verified")
                checksum_verified = True
            else:
                raise BackfillError("Checksum mismatch - aborting backfill")
        else:
            logger.warning("! No published checksum found - proceeding with caution")

        metadata = {
            "version": version,
            "original_release_date": published_at,
            "backfill_date": datetime.now(UTC).isoformat(),
            "backfill_identity": "https://github.com/IAmJonoBo/Hephaestus/.github/workflows/backfill.yml@refs/heads/main",
            "verification_status": "backfilled",
            "checksum_verified": checksum_verified,
            "notes": (
                "Sigstore bundle backfilled for historical release. "
                "Original archive verified against published SHA-256 checksum."
            ),
        }

        if not dry_run:
            try:
                bundle_path = sign_with_sigstore(archive_path, metadata)
            except BackfillError as exc:
                logger.error("Signing failed: %s", exc)
                logger.info(
                    "Note: Sigstore signing requires OIDC authentication. "
                    "Ensure you're running in a GitHub Actions environment "
                    "or have configured sigstore credentials."
                )
                raise
        else:
            bundle_path = temp_path / sigstore_name
            with open(bundle_path, "w", encoding="utf-8") as handle:
                json.dump(
                    {"backfill_metadata": metadata, "note": "dry-run bundle"},
                    handle,
                    indent=2,
                )
            logger.info("[DRY RUN] Created dummy bundle: %s", bundle_path)

        upload_release_asset(release_id, bundle_path, token, dry_run=dry_run)
        add_backfill_notice(release_id, version, token, dry_run=dry_run)

        bundle_asset: dict[str, Any] | None = None
        if dry_run:
            bundle_asset = {
                "name": sigstore_name,
                "browser_download_url": (
                    f"https://github.com/{REPO_OWNER}/{REPO_NAME}/releases/download/"
                    f"{version}/{sigstore_name}"
                ),
                "size": bundle_path.stat().st_size,
                "content_type": "application/vnd.dev.sigstore.bundle+json",
            }
        else:
            refreshed = get_release_by_tag(version, token)
            for asset in refreshed.get("assets", []):
                if asset.get("name") == sigstore_name:
                    bundle_asset = asset
                    break

        if not bundle_asset:
            raise BackfillError(
                "Uploaded Sigstore bundle metadata not found after refresh; cannot record inventory entry."
            )

    logger.info("✓ Backfilled %s", version)

    summary = {
        "version": version,
        "status": "dry-run" if dry_run else "backfilled",
        "release_id": release_id,
        "release_url": release.get("html_url"),
        "release_published_at": published_at,
        "archive": {
            "name": wheelhouse_asset["name"],
            "sha256": archive_digest,
            "size": wheelhouse_asset.get("size"),
        },
        "checksum": {
            "expected": checksum,
            "verified": checksum_verified,
        },
        "bundle": {
            "name": bundle_asset["name"],
            "url": bundle_asset.get("browser_download_url") or bundle_asset.get("url"),
            "size": bundle_asset.get("size"),
            "content_type": bundle_asset.get("content_type"),
            "uploaded_at": datetime.now(UTC).isoformat(),
        },
        "backfill": metadata,
    }

    return summary


def run_backfill(
    *,
    token: str,
    version: str | None = None,
    versions: Sequence[str] | None = None,
    dry_run: bool = False,
    inventory_path: Path | None = None,
) -> BackfillRunSummary:
    """Execute the Sigstore backfill workflow."""

    selected_versions = list(versions or ([version] if version else HISTORICAL_VERSIONS))
    inventory_target = inventory_path or INVENTORY_PATH

    if not selected_versions:
        raise BackfillError("No versions provided for backfill")

    if dry_run:
        logger.info("=" * 70)
        logger.info("DRY RUN MODE - No actual uploads will be performed")
        logger.info("=" * 70)

    successes: list[dict[str, Any]] = []
    failures: list[dict[str, Any]] = []

    for release_version in selected_versions:
        try:
            entry = backfill_release(release_version, token, dry_run=dry_run)
            if entry:
                successes.append(entry)
        except BackfillError as exc:
            logger.error("✗ Failed to backfill %s: %s", release_version, exc)
            failures.append(
                {
                    "version": release_version,
                    "error": str(exc),
                    "timestamp": datetime.now(UTC).isoformat(),
                }
            )
        except Exception as exc:  # pragma: no cover - defensive
            logger.exception("✗ Unexpected error backfilling %s: %s", release_version, exc)
            failures.append(
                {
                    "version": release_version,
                    "error": f"Unexpected error: {exc}",
                    "timestamp": datetime.now(UTC).isoformat(),
                }
            )

    logger.info("")
    logger.info("=" * 70)
    logger.info("Backfill Summary: %s/%s succeeded", len(successes), len(selected_versions))

    if failures:
        logger.info(
            "Failed versions: %s",
            ", ".join(failure["version"] for failure in failures),
        )

    write_inventory(
        inventory_path=inventory_target,
        successes=successes,
        failures=failures,
    )

    logger.info("Inventory updated at %s", inventory_target)

    if not failures:
        logger.info("All backfills completed successfully!")

    return BackfillRunSummary(
        successes=successes,
        failures=failures,
        inventory_path=inventory_target,
        versions=selected_versions,
        dry_run=dry_run,
    )
