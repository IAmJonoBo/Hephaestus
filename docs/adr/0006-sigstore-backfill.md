# ADR 0006: Sigstore Bundle Backfill for Historical Releases

- Status: Phase 1 Implemented
- Date: 2025-01-15
- Supersedes: N/A
- Superseded by: N/A
- Related: ADR-0001 (STRIDE Threat Model)

## Context

Hephaestus currently supports Sigstore attestation verification for wheelhouse installs, providing cryptographic proof of provenance and supply chain security. However, historical releases (prior to Sigstore implementation) lack these attestation bundles.

Current state:

- **New releases** (v0.2.4+): Include Sigstore bundles with attestations
- **Historical releases** (v0.1.0-v0.2.3): No Sigstore bundles available
- **Verification**: Optional via `--require-sigstore` flag
- **Identity pinning**: Supported via `--sigstore-identity` flag

The Red Team findings identify this as a high-priority gap:

> "Supply-chain compromise risk narrows to unsigned archives and unpinned identities. Backfill Sigstore bundles for historical releases, require identities via `--sigstore-identity`, and enable `--require-sigstore` in automation to block unsigned installs."

### Motivating Requirements

1. **Supply Chain Security**: Historical releases should have same security guarantees as new ones
2. **Audit Compliance**: Organizations need complete provenance for all installed versions
3. **Zero-Trust Automation**: CI/CD pipelines should enforce attestation verification
4. **Version Flexibility**: Users should be able to safely install any historical version
5. **Rollback Safety**: Emergency rollbacks to older versions should maintain security posture

### Current Limitations

- Users installing historical versions via `hephaestus release install` cannot verify provenance
- Automated pipelines cannot enforce `--require-sigstore` if supporting older versions
- Audit tools cannot verify the complete supply chain for deployed versions
- Rollback procedures lack cryptographic verification

### Technical Challenges

1. **Retroactive Signing**: Historical artifacts cannot be signed with current keys
2. **Timestamp Integrity**: Backdating signatures violates transparency logs
3. **Trust Chain**: How to establish trust for retroactive attestations
4. **Archive Immutability**: GitHub release assets should not be modified post-publication
5. **Rekor Transparency**: Sigstore Rekor log requires valid timestamps

## Decision

We will implement a **transparent backfill strategy** that creates Sigstore attestations for historical releases without modifying original archives:

1. **Separate Attestation Assets**: Publish `.sigstore` bundles as additional release assets
2. **Verification Policy**: Document that backfilled attestations use current signing identity
3. **Transparency Metadata**: Include backfill metadata (original release date, backfill date)
4. **Optional Verification**: Users can verify backfilled bundles but enforcement remains optional
5. **CI Enforcement**: New releases require Sigstore; historical backfills improve security but don't block

### Architecture

```
Historical Release Backfill Process:
1. Enumerate all historical releases (v0.1.0-v0.2.3)
2. Download existing wheelhouse archives
3. Verify SHA-256 checksums match published manifests
4. Generate Sigstore attestations using current signing identity
5. Add backfill metadata to attestation
6. Upload .sigstore bundles as new release assets
7. Update release notes with backfill notice
```

### Backfill Metadata Format

```json
{
  "version": "v0.2.3",
  "original_release_date": "2025-01-10T12:00:00Z",
  "backfill_date": "2025-01-20T15:30:00Z",
  "backfill_identity": "https://github.com/IAmJonoBo/Hephaestus/.github/workflows/release.yml@refs/heads/main",
  "verification_status": "backfilled",
  "checksum_verified": true,
  "notes": "Sigstore bundle backfilled for historical release. Original archive verified against published SHA-256 checksum."
}
```

### Verification Workflow

```python
# Future enhancement to release.py
def verify_wheelhouse_with_backfill(
    archive_path: Path,
    sigstore_bundle: Path,
    require_original: bool = False
) -> VerificationResult:
    """Verify wheelhouse with support for backfilled bundles."""
    
    # Load bundle and check for backfill metadata
    bundle = load_sigstore_bundle(sigstore_bundle)
    metadata = bundle.get("backfill_metadata", {})
    
    if metadata and require_original:
        raise VerificationError(
            "Release uses backfilled Sigstore bundle. "
            "Use --allow-backfill to accept retroactive attestations."
        )
    
    # Verify checksum first
    if not verify_checksum(archive_path, bundle["checksum"]):
        raise VerificationError("Checksum mismatch")
    
    # Verify Sigstore signature
    verify_sigstore(archive_path, sigstore_bundle)
    
    # Log backfill status
    if metadata:
        logger.info(
            f"Verified backfilled bundle: "
            f"Original release {metadata['original_release_date']}, "
            f"Backfilled {metadata['backfill_date']}"
        )
    
    return VerificationResult(
        verified=True,
        backfilled=bool(metadata),
        identity=bundle["identity"]
    )
```

### CLI Flags

```bash
# Install with backfill verification
hephaestus release install --require-sigstore --allow-backfill

# Reject backfilled bundles (only accept original attestations)
hephaestus release install --require-sigstore --no-backfill

# Default behavior (accepts backfilled and original)
hephaestus release install --require-sigstore
```

### Automation Script

```python
# scripts/backfill_sigstore_bundles.py
"""Backfill Sigstore bundles for historical releases."""

import requests
import subprocess
from pathlib import Path
from datetime import datetime

REPO = "IAmJonoBo/Hephaestus"
HISTORICAL_VERSIONS = [
    "v0.1.0", "v0.1.1", "v0.1.2",
    "v0.2.0", "v0.2.1", "v0.2.2", "v0.2.3"
]

def backfill_release(version: str, token: str):
    """Backfill Sigstore bundle for a historical release."""
    print(f"Processing {version}...")
    
    # Get release metadata
    release = get_release_by_tag(REPO, version, token)
    
    # Find wheelhouse asset
    wheelhouse = next(
        asset for asset in release["assets"]
        if asset["name"].endswith(".tar.gz")
    )
    
    # Download archive
    archive_path = download_asset(wheelhouse["url"], token)
    
    # Verify checksum against published manifest
    checksum = get_published_checksum(release, wheelhouse["name"])
    if not verify_checksum(archive_path, checksum):
        raise ValueError(f"Checksum mismatch for {version}")
    
    # Generate Sigstore bundle
    bundle_path = sign_with_sigstore(archive_path)
    
    # Add backfill metadata
    add_backfill_metadata(
        bundle_path,
        version=version,
        original_date=release["published_at"],
        backfill_date=datetime.utcnow().isoformat()
    )
    
    # Upload bundle as release asset
    upload_release_asset(
        release["upload_url"],
        bundle_path,
        f"{wheelhouse['name']}.sigstore",
        token
    )
    
    # Update release notes
    add_backfill_notice(release["id"], version, token)
    
    print(f"✓ Backfilled {version}")

def main():
    token = os.getenv("GITHUB_TOKEN")
    for version in HISTORICAL_VERSIONS:
        try:
            backfill_release(version, token)
        except Exception as e:
            print(f"✗ Failed to backfill {version}: {e}")
            continue

if __name__ == "__main__":
    main()
```

## Consequences

### Positive

1. **Improved Security Posture**: All releases have cryptographic attestation
2. **Audit Compliance**: Complete provenance chain for audit requirements
3. **CI/CD Enforcement**: Pipelines can enforce `--require-sigstore` for all versions
4. **Rollback Safety**: Emergency rollbacks maintain security guarantees
5. **Transparency**: Clear metadata distinguishes backfilled from original attestations
6. **Non-Breaking**: Users without verification enabled are unaffected

### Negative

1. **Retroactive Trust**: Backfilled attestations don't prove historical provenance
2. **Timestamp Discrepancy**: Signing timestamp differs from release timestamp
3. **Maintenance Effort**: Requires one-time backfill operation
4. **Documentation Burden**: Need to explain backfill vs. original attestations
5. **Verification Complexity**: Additional logic for handling backfilled bundles
6. **Transparency Log**: Rekor entries show current timestamp, not original date

### Risks

- **False Security**: Users might not understand difference between backfilled and original
- **Key Compromise**: If current signing key is compromised, backfilled bundles are invalid
- **Rekor Rejection**: Transparency log might reject retroactive timestamps
- **Archive Tampering**: Original archives could have been modified before backfill
- **Policy Confusion**: Organizations might incorrectly trust backfilled attestations

### Mitigation Strategies

1. **Clear Documentation**: Explain limitations of backfilled attestations
2. **Metadata Transparency**: Include backfill metadata in all bundles
3. **Checksum Verification**: Always verify against published SHA-256 first
4. **Policy Flags**: Allow organizations to reject backfilled bundles
5. **Audit Trail**: Log all backfill operations with timestamps
6. **Release Notes**: Add backfill notices to historical releases

## Alternatives Considered

### 1. No Backfill (Status Quo)

**Description**: Accept that historical releases lack Sigstore attestation.

**Pros:**
- No effort required
- No retroactive trust concerns
- Clear distinction between old and new

**Cons:**
- Security gap remains
- Can't enforce verification on all versions
- Audit compliance issues
- Rollback safety concerns

**Why not chosen:** Security gap is unacceptable per Red Team findings.

### 2. Re-release Historical Versions

**Description**: Create new releases with same code but new attestations.

**Pros:**
- Attestations use correct timestamps
- Clear provenance chain
- No retroactive trust issues

**Cons:**
- Version confusion (v0.2.3 vs v0.2.3-resigned)
- Breaks semantic versioning
- Confuses users and tools
- Duplicate release entries

**Why not chosen:** Causes version management chaos and breaks conventions.

### 3. Detached Signature Repository

**Description**: Maintain separate repository with Sigstore bundles.

**Pros:**
- Doesn't modify original releases
- Clear separation of concerns
- Easier to update signatures

**Cons:**
- Complex discovery mechanism
- Additional infrastructure
- Synchronization challenges
- Users might not find bundles

**Why not chosen:** Increases complexity and reduces discoverability.

### 4. In-Place Modification

**Description**: Modify existing release assets to include Sigstore bundles.

**Pros:**
- Single source of truth
- No separate assets
- Simpler verification

**Cons:**
- Violates archive immutability
- Changes release checksums
- Breaks existing installations
- Loses historical accuracy

**Why not chosen:** Violates immutability principles and breaks existing users.

## Implementation Plan

### Phase 1: Preparation (Week 1)

- [x] Review historical releases (v0.1.0-v0.2.3)
- [x] Verify all releases have SHA-256 checksums
- [x] Design backfill metadata schema
- [ ] Write backfill automation script
- [ ] Test backfill process on staging

### Phase 2: Execution (Week 2)

- [ ] Run backfill script for all historical releases
- [ ] Verify uploaded bundles
- [ ] Update release notes with backfill notices
- [ ] Update documentation to explain backfilled attestations
- [ ] Test verification with backfilled bundles

### Phase 3: Enforcement (Week 3)

- [ ] Add `--allow-backfill` and `--no-backfill` CLI flags
- [ ] Update verification logic to handle backfilled bundles
- [ ] Write tests for backfill verification
- [ ] Update CI/CD documentation
- [ ] Announce backfill completion

### Phase 4: Documentation (Week 4)

- [ ] Update SECURITY.md with backfill policy
- [ ] Add backfill section to Operating Safely guide
- [ ] Create FAQ for backfilled attestations
- [ ] Update audit compliance documentation
- [ ] Announce in CHANGELOG

## Follow-up Actions

- [ ] @IAmJonoBo/2025-01-20 — Design backfill metadata schema
- [ ] @IAmJonoBo/2025-01-22 — Implement backfill automation script
- [ ] @IAmJonoBo/2025-01-25 — Execute backfill for historical releases
- [ ] @IAmJonoBo/2025-01-27 — Add verification flags to CLI
- [ ] @IAmJonoBo/2025-01-30 — Update documentation and announce completion

## References

- [Sigstore Documentation](https://docs.sigstore.dev/)
- [Rekor Transparency Log](https://docs.sigstore.dev/rekor/overview/)
- [ADR-0001: STRIDE Threat Model](./0001-stride-threat-model.md)
- [SECURITY.md](../../SECURITY.md)
- [Operating Safely Guide](../how-to/operating-safely.md)

## Appendix: Backfill Verification Example

```bash
# Install historical release with backfilled verification
$ hephaestus release install \
    --repository IAmJonoBo/Hephaestus \
    --tag v0.2.3 \
    --require-sigstore \
    --allow-backfill

INFO: Downloading release v0.2.3...
INFO: Verifying SHA-256 checksum... ✓
INFO: Verifying Sigstore bundle... ✓
WARN: Sigstore bundle is backfilled (original: 2025-01-10, backfilled: 2025-01-20)
INFO: Identity: https://github.com/IAmJonoBo/Hephaestus/.github/workflows/release.yml@refs/heads/main
INFO: Installation complete

# Reject backfilled bundles
$ hephaestus release install \
    --repository IAmJonoBo/Hephaestus \
    --tag v0.2.3 \
    --require-sigstore \
    --no-backfill

ERROR: Release v0.2.3 uses backfilled Sigstore bundle
ERROR: Use --allow-backfill to accept retroactive attestations
```

## Status History

- 2025-01-15: Proposed (documented in ADR)
- Future: Accepted after backfill metadata schema review
- Future: Implemented in Q1 2025 (backfill execution target: 2025-01-31)
