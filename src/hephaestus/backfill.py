"""Sigstore bundle backfill metadata schema (ADR-0006 Phase 1).

This module defines the metadata format for backfilled Sigstore bundles
on historical releases.
"""

from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime
from typing import Any

__all__ = [
    "BackfillMetadata",
    "BackfillVerificationStatus",
]


@dataclass
class BackfillMetadata:
    """Metadata for a backfilled Sigstore bundle.
    
    This metadata distinguishes backfilled attestations (signed retroactively)
    from original attestations (signed at release time).
    
    Attributes:
        version: Release version tag
        original_release_date: When the release was originally published
        backfill_date: When the Sigstore bundle was backfilled
        backfill_identity: Signing identity used for backfill
        verification_status: Always "backfilled" for these bundles
        checksum_verified: Whether original archive checksum was verified
        notes: Additional context about the backfill
    """
    
    version: str
    original_release_date: datetime
    backfill_date: datetime
    backfill_identity: str
    verification_status: str  # Always "backfilled"
    checksum_verified: bool
    notes: str

    def to_dict(self) -> dict[str, Any]:
        """Convert metadata to dictionary representation.
        
        Returns:
            Dictionary suitable for JSON serialization
        """
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
        """Create metadata from dictionary representation.
        
        Args:
            data: Dictionary containing metadata fields
            
        Returns:
            BackfillMetadata instance
            
        Raises:
            ValueError: If required fields are missing
        """
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
    
    ORIGINAL = "original"  # Bundle created at release time
    BACKFILLED = "backfilled"  # Bundle created retroactively
    UNKNOWN = "unknown"  # Status cannot be determined
