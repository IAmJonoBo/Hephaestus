"""Tests for Sigstore backfill metadata (ADR-0006 Phase 1)."""

from __future__ import annotations

from datetime import datetime, timezone

import pytest

from hephaestus.backfill import BackfillMetadata, BackfillVerificationStatus


def test_backfill_metadata_creation():
    """Backfill metadata should be created with correct fields."""
    original_date = datetime(2025, 1, 10, 12, 0, 0, tzinfo=timezone.utc)
    backfill_date = datetime(2025, 1, 20, 15, 30, 0, tzinfo=timezone.utc)

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


def test_backfill_metadata_to_dict():
    """Backfill metadata should serialize to dictionary."""
    original_date = datetime(2025, 1, 10, 12, 0, 0, tzinfo=timezone.utc)
    backfill_date = datetime(2025, 1, 20, 15, 30, 0, tzinfo=timezone.utc)

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


def test_backfill_metadata_from_dict():
    """Backfill metadata should deserialize from dictionary."""
    original_date = datetime(2025, 1, 10, 12, 0, 0, tzinfo=timezone.utc)
    backfill_date = datetime(2025, 1, 20, 15, 30, 0, tzinfo=timezone.utc)

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


def test_backfill_metadata_roundtrip():
    """Backfill metadata should roundtrip through dict serialization."""
    original_date = datetime(2025, 1, 10, 12, 0, 0, tzinfo=timezone.utc)
    backfill_date = datetime(2025, 1, 20, 15, 30, 0, tzinfo=timezone.utc)

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


def test_backfill_verification_status_constants():
    """Backfill verification status should have expected constants."""
    assert BackfillVerificationStatus.ORIGINAL == "original"
    assert BackfillVerificationStatus.BACKFILLED == "backfilled"
    assert BackfillVerificationStatus.UNKNOWN == "unknown"
