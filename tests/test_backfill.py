"""Tests for Sigstore backfill metadata (ADR-0006 Phase 1)."""

from __future__ import annotations

import hashlib
import json
from datetime import UTC, datetime
from pathlib import Path

import pytest

from hephaestus.backfill import (
    BackfillError,
    BackfillMetadata,
    BackfillRunSummary,
    BackfillVerificationStatus,
    compute_sha256,
    find_wheelhouse_asset,
    get_github_headers,
    get_published_checksum,
    run_backfill,
    verify_checksum,
)


def test_backfill_metadata_creation() -> None:
    """Backfill metadata should be created with correct fields."""
    original_date = datetime(2025, 1, 10, 12, 0, 0, tzinfo=UTC)
    backfill_date = datetime(2025, 1, 20, 15, 30, 0, tzinfo=UTC)

    metadata = BackfillMetadata(
        version="v0.2.3",
        original_release_date=original_date,
        backfill_date=backfill_date,
        backfill_identity="https://github.com/IAmJonoBo/Hephaestus/.github/workflows/release.yml@refs/heads/main",
        verification_status="backfilled",
        checksum_verified=True,
        notes="Sigstore bundle backfilled for historical release.",
    )

    assert metadata.version == "v0.2.3"
    assert metadata.original_release_date == original_date
    assert metadata.backfill_date == backfill_date
    assert "Hephaestus" in metadata.backfill_identity
    assert metadata.verification_status == "backfilled"
    assert metadata.checksum_verified is True
    assert "historical release" in metadata.notes


def test_backfill_metadata_to_dict() -> None:
    """Backfill metadata should serialize to dictionary."""
    original_date = datetime(2025, 1, 10, 12, 0, 0, tzinfo=UTC)
    backfill_date = datetime(2025, 1, 20, 15, 30, 0, tzinfo=UTC)

    metadata = BackfillMetadata(
        version="v0.2.3",
        original_release_date=original_date,
        backfill_date=backfill_date,
        backfill_identity="test-identity",
        verification_status="backfilled",
        checksum_verified=True,
        notes="Test notes",
    )

    data = metadata.to_dict()

    assert isinstance(data, dict)
    assert data["version"] == "v0.2.3"
    assert data["original_release_date"] == original_date.isoformat()
    assert data["backfill_date"] == backfill_date.isoformat()
    assert data["backfill_identity"] == "test-identity"
    assert data["verification_status"] == "backfilled"
    assert data["checksum_verified"] is True
    assert data["notes"] == "Test notes"


def test_backfill_metadata_from_dict() -> None:
    """Backfill metadata should deserialize from dictionary."""
    original_date = datetime(2025, 1, 10, 12, 0, 0, tzinfo=UTC)
    backfill_date = datetime(2025, 1, 20, 15, 30, 0, tzinfo=UTC)

    data = {
        "version": "v0.2.3",
        "original_release_date": original_date.isoformat(),
        "backfill_date": backfill_date.isoformat(),
        "backfill_identity": "test-identity",
        "verification_status": "backfilled",
        "checksum_verified": True,
        "notes": "Test notes",
    }

    metadata = BackfillMetadata.from_dict(data)

    assert metadata.version == "v0.2.3"
    assert metadata.original_release_date == original_date
    assert metadata.backfill_date == backfill_date
    assert metadata.backfill_identity == "test-identity"
    assert metadata.verification_status == "backfilled"
    assert metadata.checksum_verified is True
    assert metadata.notes == "Test notes"


def test_backfill_metadata_roundtrip() -> None:
    """Backfill metadata should roundtrip through dict serialization."""
    original_date = datetime(2025, 1, 10, 12, 0, 0, tzinfo=UTC)
    backfill_date = datetime(2025, 1, 20, 15, 30, 0, tzinfo=UTC)

    metadata1 = BackfillMetadata(
        version="v0.2.3",
        original_release_date=original_date,
        backfill_date=backfill_date,
        backfill_identity="test-identity",
        verification_status="backfilled",
        checksum_verified=True,
        notes="Test notes",
    )

    # Serialize and deserialize
    data = metadata1.to_dict()
    metadata2 = BackfillMetadata.from_dict(data)

    # Should be equivalent
    assert metadata1.version == metadata2.version
    assert metadata1.original_release_date == metadata2.original_release_date
    assert metadata1.backfill_date == metadata2.backfill_date
    assert metadata1.backfill_identity == metadata2.backfill_identity
    assert metadata1.verification_status == metadata2.verification_status
    assert metadata1.checksum_verified == metadata2.checksum_verified
    assert metadata1.notes == metadata2.notes


def test_backfill_verification_status_constants() -> None:
    """Backfill verification status should have expected constants."""
    assert BackfillVerificationStatus.ORIGINAL == "original"
    assert BackfillVerificationStatus.BACKFILLED == "backfilled"
    assert BackfillVerificationStatus.UNKNOWN == "unknown"


def test_compute_and_verify_checksum(tmp_path: Path) -> None:
    """Checksum utilities should report matching digests."""

    payload = b"sigstore-test"
    archive_path = tmp_path / "wheelhouse.tar.gz"
    archive_path.write_bytes(payload)

    digest = compute_sha256(archive_path)
    assert digest == hashlib.sha256(payload).hexdigest()
    assert verify_checksum(archive_path, digest) is True
    assert verify_checksum(archive_path, "deadbeef") is False


def test_get_github_headers_includes_token() -> None:
    """GitHub headers helper should include authorization token."""

    headers = get_github_headers("token-123")
    assert headers["Authorization"] == "token token-123"
    assert headers["Accept"].startswith("application/vnd.github")


def test_find_wheelhouse_asset_identifies_bundle() -> None:
    """find_wheelhouse_asset should locate non-sigstore tarballs."""

    release = {
        "assets": [
            {"name": "wheelhouse-v0.2.3.tar.gz.sigstore"},
            {"name": "wheelhouse-v0.2.3.tar.gz"},
        ]
    }

    asset = find_wheelhouse_asset(release)
    assert asset is not None
    assert asset["name"] == "wheelhouse-v0.2.3.tar.gz"


def test_get_published_checksum_without_manifest() -> None:
    """get_published_checksum should return None when manifest missing."""

    release = {
        "assets": [{"name": "wheelhouse-v0.2.3.tar.gz"}],
        "body": "Release notes",
    }

    assert get_published_checksum(release, "wheelhouse-v0.2.3.tar.gz") is None


def test_run_backfill_success(monkeypatch: pytest.MonkeyPatch, tmp_path: Path) -> None:
    """`run_backfill` should return a successful summary when all versions succeed."""

    from hephaestus import backfill as backfill_module

    captured_versions: list[tuple[str, str, bool]] = []

    def fake_backfill_release(version: str, token: str, dry_run: bool = False) -> dict[str, str]:
        captured_versions.append((version, token, dry_run))
        return {"version": version, "status": "backfilled"}

    monkeypatch.setattr(backfill_module, "backfill_release", fake_backfill_release)

    result = run_backfill(
        token="token-123",
        version="v0.2.3",
        dry_run=True,
        inventory_path=tmp_path / "inventory.json",
    )

    assert isinstance(result, BackfillRunSummary)
    assert result.ok is True
    assert result.versions == ["v0.2.3"]
    assert result.successes == [{"version": "v0.2.3", "status": "backfilled"}]
    assert result.failures == []
    assert captured_versions == [("v0.2.3", "token-123", True)]

    inventory_data = json.loads((tmp_path / "inventory.json").read_text(encoding="utf-8"))
    assert inventory_data["versions"]["v0.2.3"]["status"] == "backfilled"


def test_run_backfill_collects_failures(monkeypatch: pytest.MonkeyPatch, tmp_path: Path) -> None:
    """`run_backfill` should capture failures and surface them in the summary."""

    from hephaestus import backfill as backfill_module

    def fake_backfill_release(version: str, token: str, dry_run: bool = False) -> dict[str, str]:
        if version == "v0.1.0":
            raise BackfillError("boom")
        return {"version": version, "status": "backfilled"}

    monkeypatch.setattr(backfill_module, "backfill_release", fake_backfill_release)

    result = run_backfill(
        token="token-123",
        versions=["v0.1.0", "v0.1.1"],
        inventory_path=tmp_path / "inventory.json",
    )

    assert isinstance(result, BackfillRunSummary)
    assert result.ok is False
    assert result.versions == ["v0.1.0", "v0.1.1"]
    assert result.successes == [{"version": "v0.1.1", "status": "backfilled"}]
    assert result.failures[0]["version"] == "v0.1.0"
    assert "boom" in result.failures[0]["error"]
    inventory_data = json.loads((tmp_path / "inventory.json").read_text(encoding="utf-8"))
    failure_entry = inventory_data["versions"]["v0.1.0"]
    assert failure_entry["status"] == "error"
    assert "boom" in failure_entry["error"]
