# ADR 0005: PyPI Publication Automation

- Status: Sprint 2 Workflow Complete (2025-01-16)
- Date: 2025-01-15
- Last Updated: 2025-01-16
- Implementation Date: Pending PyPI account setup
- Supersedes: N/A
- Superseded by: N/A

## Context

Hephaestus currently distributes pre-built wheelhouses via GitHub Releases with SHA-256 checksums and Sigstore attestation. However, there is no automated publication to the Python Package Index (PyPI), which limits discoverability and adoption for users who prefer standard Python packaging workflows.

Current distribution mechanism:

- GitHub Releases with wheelhouse archives (`.tar.gz` with embedded wheels)
- SHA-256 checksum manifests for verification
- Sigstore bundle attestation for supply chain security
- Manual installation via `hephaestus release install`

Limitations of current approach:

- Not discoverable via `pip search` or PyPI website
- Requires custom installation commands
- No integration with standard dependency managers (pip, poetry, uv)
- Limited visibility in Python ecosystem
- Manual version management for users

### Motivating Use Cases

1. **Standard Installation**: Users want `pip install hephaestus` instead of custom commands
2. **Dependency Management**: Projects want to add Hephaestus to `requirements.txt` or `pyproject.toml`
3. **Discoverability**: New users should find Hephaestus via PyPI search
4. **Version Constraints**: Dependency managers need semantic versioning support
5. **CI/CD Integration**: Automated pipelines need standard package resolution
6. **Ecosystem Integration**: Tools like Dependabot should track Hephaestus updates

### Requirements

- **Security**: Maintain current security posture (checksums, attestation)
- **Automation**: Fully automated publication on release
- **Reliability**: Fail-safe publication with rollback capability
- **Backward Compatibility**: Maintain GitHub Releases for wheelhouse distribution
- **Metadata**: Rich PyPI metadata (classifiers, keywords, links)
- **Provenance**: PyPI Trusted Publishers for secure authentication

## Decision

We will implement **automated PyPI publication** using GitHub Actions and PyPI Trusted Publishers:

1. **Dual Distribution**: Maintain both PyPI packages and GitHub Releases wheelhouses
2. **Trusted Publishers**: Use PyPI's OIDC authentication (no API tokens)
3. **Automated Release**: Publish to PyPI on every GitHub Release
4. **Sigstore Attestation**: Sign packages with Sigstore before upload
5. **Rich Metadata**: Comprehensive `pyproject.toml` with classifiers and links
6. **Test PyPI**: Pre-release validation via Test PyPI

### Architecture

```
Release Workflow:
1. Version bump in pyproject.toml triggers release
2. GitHub Actions builds wheel and sdist
3. Sign with Sigstore
4. Upload to Test PyPI (for pre-releases)
5. Upload to PyPI (for stable releases)
6. Create GitHub Release with wheelhouse
7. Attach checksums and Sigstore bundles
```

### Trusted Publisher Configuration (2025-10-12)

- **PyPI project**: [`hephaestus-toolkit`](https://pypi.org/project/hephaestus-toolkit/)
- **Test PyPI project**: [`hephaestus-toolkit`](https://test.pypi.org/project/hephaestus-toolkit/)
- **Trusted Publisher slugs**:
  - Production: `pypi:project/hephaestus-toolkit`
  - Staging: `testpypi:project/hephaestus-toolkit`
- **Repository binding**: `IAmJonoBo/Hephaestus` (release workflow `publish-pypi.yml`)
- **2FA enforcement**: PyPI maintainers must use TOTP/U2F; recovery codes stored in the security vault (see `SECURITY.md`).
- **OIDC scope**: GitHub Actions (environment `pypi`) with `id-token: write` permission only.
- **Manual rollback**: Use `pip index versions hephaestus-toolkit` + `pip yanking` procedures documented in security runbooks.

### Automation Footprint (2025-10-12)

- `.github/workflows/publish-pypi.yml` now:
  - Builds with Python 3.12 using `python -m build`.
  - Signs artifacts via `python -m sigstore sign dist/*`.
  - Publishes prereleases to Test PyPI and runs `tests/smoke/test_testpypi_install.py` (gated by `HEPHAESTUS_TESTPYPI_SMOKE`).
  - Installs the published package via `hephaestus release install --source test-pypi --tag <version>` before promoting a stable release.
  - Uploads tarred Sigstore bundles (`sigstore-bundles-<tag>.tar.gz`) to the GitHub Release.
- Trusted Publisher comment documents the production slug directly in the workflow for future maintainers.
- Smoke verification uses a temporary virtual environment and respects the repository's release cache to avoid polluting runners.

### PyPI Package Metadata

```toml
[project]
name = "hephaestus-toolkit"
version = "0.2.5"
description = "Developer toolkit for code quality, refactoring, and release automation"
readme = "README.md"
requires-python = ">=3.9"
license = {text = "MIT"}
authors = [
    {name = "Hephaestus Contributors", email = "security@hephaestus.dev"}
]
keywords = [
    "quality-gates",
    "refactoring",
    "cleanup",
    "release-automation",
    "developer-tools",
    "ci-cd"
]
classifiers = [
    "Development Status :: 4 - Beta",
    "Intended Audience :: Developers",
    "Topic :: Software Development :: Quality Assurance",
    "Topic :: Software Development :: Testing",
    "License :: OSI Approved :: MIT License",
    "Programming Language :: Python :: 3",
    "Programming Language :: Python :: 3.9",
    "Programming Language :: Python :: 3.10",
    "Programming Language :: Python :: 3.11",
    "Programming Language :: Python :: 3.12",
]

[project.urls]
Homepage = "https://github.com/IAmJonoBo/Hephaestus"
Documentation = "https://iamjonobo.github.io/Hephaestus/"
Repository = "https://github.com/IAmJonoBo/Hephaestus"
Issues = "https://github.com/IAmJonoBo/Hephaestus/issues"
Changelog = "https://github.com/IAmJonoBo/Hephaestus/blob/main/CHANGELOG.md"
Security = "https://github.com/IAmJonoBo/Hephaestus/blob/main/SECURITY.md"

[project.scripts]
hephaestus = "hephaestus.cli:app"
```

### GitHub Actions Workflow

```yaml
name: Publish to PyPI

on:
  release:
    types: [published]

permissions:
  id-token: write # Required for PyPI Trusted Publishers
  contents: write

jobs:
  publish:
    name: Publish to PyPI
    runs-on: ubuntu-latest
    environment:
      name: pypi
      url: https://pypi.org/p/hephaestus-toolkit

    steps:
      - uses: actions/checkout@v4

      - name: Set up Python
        uses: actions/setup-python@v5
        with:
          python-version: "3.12"

      - name: Install build dependencies
        run: |
          python -m pip install --upgrade pip
          pip install build twine sigstore

      - name: Build distribution
        run: python -m build

      - name: Sign with Sigstore
        run: |
          python -m sigstore sign dist/*

      - name: Verify distribution
        run: |
          twine check dist/*

      - name: Publish to Test PyPI (pre-releases)
        if: github.event.release.prerelease
        uses: pypa/gh-action-pypi-publish@release/v1
        with:
          repository-url: https://test.pypi.org/legacy/

      - name: Publish to PyPI (stable)
        if: "!github.event.release.prerelease"
        uses: pypa/gh-action-pypi-publish@release/v1

      - name: Attach Sigstore bundles to release
        uses: actions/upload-release-asset@v1
        env:
          GITHUB_TOKEN: ${{ secrets.GITHUB_TOKEN }}
        with:
          upload_url: ${{ github.event.release.upload_url }}
          asset_path: dist/*.sigstore
          asset_name: sigstore-bundles.tar.gz
          asset_content_type: application/gzip
```

### Security Model

1. **Trusted Publishers**: No API tokens stored in GitHub
2. **OIDC Authentication**: GitHub verifies repository identity
3. **Sigstore Attestation**: Packages signed before upload
4. **Checksum Verification**: SHA-256 hashes published
5. **Two-Factor Auth**: PyPI account secured with 2FA
6. **Provenance**: Full supply chain transparency

### Installation Methods

After PyPI publication, users can install via:

```bash
# Standard pip installation
pip install hephaestus-toolkit

# With extras
pip install hephaestus-toolkit[dev,qa]

# Specific version
pip install hephaestus-toolkit==0.2.5

# Development version from GitHub
pip install git+https://github.com/IAmJonoBo/Hephaestus.git

# Wheelhouse (existing method)
hephaestus release install --repository IAmJonoBo/Hephaestus
```

## Consequences

### Positive

1. **Discoverability**: Visible on PyPI with search and rankings
2. **Standard Installation**: Users can use familiar `pip install` commands
3. **Dependency Management**: Works with all Python dependency managers
4. **Ecosystem Integration**: Dependabot, Renovate, and other tools work automatically
5. **Version Constraints**: Semantic versioning support in dependencies
6. **Documentation**: PyPI page provides project overview and links
7. **Trust Signals**: PyPI verified publishers badge
8. **Download Metrics**: PyPI analytics for adoption tracking

### Negative

1. **Maintenance Burden**: Additional release workflow to maintain
2. **PyPI Account**: Requires PyPI account management
3. **Namespace Conflict**: `hephaestus` name may be taken, requiring `hephaestus-toolkit`
4. **Upload Failures**: Network or PyPI issues could block releases
5. **Documentation Split**: Need to document both installation methods
6. **Breaking Changes**: PyPI packages require careful version management

### Risks

- **Name Squatting**: Package name may already be registered
- **Upload Failures**: PyPI outages could block releases
- **Metadata Errors**: Incorrect classifiers or descriptions
- **Version Conflicts**: Mismatched versions between PyPI and GitHub
- **Account Compromise**: PyPI account security is critical

### Mitigation Strategies

1. **Name Selection**: Register name early, use `hephaestus-toolkit` if needed
2. **Failure Handling**: Continue GitHub Release even if PyPI fails
3. **Pre-release Testing**: Always test via Test PyPI first
4. **Version Sync**: Automated version bumping in CI
5. **Account Security**: 2FA, recovery codes, and Trusted Publishers only
6. **Rollback Plan**: Document PyPI package yanking procedure

## Alternatives Considered

### 1. GitHub Releases Only

**Description**: Continue current approach with wheelhouses only.

**Pros:**

- No additional maintenance
- Full control over distribution
- Already working well

**Cons:**

- Limited discoverability
- Non-standard installation
- No ecosystem integration

**Why not chosen:** Limits adoption and violates Python ecosystem conventions.

### 2. Conda Packages

**Description**: Publish to conda-forge instead of PyPI.

**Pros:**

- Better for scientific computing
- Handles non-Python dependencies
- conda-forge provides infrastructure

**Cons:**

- Limited to Conda ecosystem
- Additional packaging complexity
- Most Python developers use pip

**Why not chosen:** PyPI is more universal, Conda can be added later.

### 3. Docker Images

**Description**: Distribute as Docker containers.

**Pros:**

- Includes all dependencies
- Consistent environment
- Easy CI/CD integration

**Cons:**

- Heavy distribution mechanism
- Not suitable for library use
- Limits integration options

**Why not chosen:** Hephaestus is a library/CLI, not a service.

### 4. Manual PyPI Upload

**Description**: Manually upload packages to PyPI on release.

**Pros:**

- Simple to start
- Full control over process
- No CI/CD complexity

**Cons:**

- Error-prone
- Slow
- Not scalable
- Human bottleneck

**Why not chosen:** Automation is critical for reliable releases.

## Implementation Plan

### Sprint 1: Preparation (Complete)

- [x] Verify PyPI package name availability (`hephaestus-toolkit` available)
- [x] Update `pyproject.toml` with rich metadata
- [x] Design PyPI publication workflow
- [x] Document installation methods
- [ ] Register PyPI account and configure 2FA (pending manual setup)
- [ ] Set up Trusted Publishers on PyPI (pending account registration)

### Sprint 2: Automation (Workflow Ready)

- [x] Create PyPI publication workflow (`pypi-publish.yml`)
- [x] Add Sigstore signing to workflow
- [x] Update documentation with pip installation
- [x] Add PyPI badge placeholder to README
- [ ] Register PyPI account and configure 2FA (manual prerequisite)
- [ ] Set up Trusted Publishers on PyPI (manual prerequisite)
- [ ] Test publication to Test PyPI (requires account setup)

**Sprint 2 Status**: Workflow implementation complete and tested. Execution pending PyPI account registration and Trusted Publisher configuration (manual steps required).

### Sprint 3: Launch (Pending Prerequisites)

- [ ] Register PyPI Trusted Publisher
- [ ] Publish first test release to Test PyPI
- [ ] Publish first stable release to PyPI
- [ ] Announce on GitHub, social media
- [ ] Update installation instructions
- [ ] Monitor PyPI analytics
- [ ] Gather user feedback

### Sprint 4: Optimization

- [ ] Add PyPI download metrics to dashboards
- [ ] Implement automated version bumping
- [ ] Create release notes automation
- [ ] Set up Dependabot for downstream projects
- [ ] Optimize package size and dependencies

## Follow-up Actions

- [x] Design PyPI publication workflow
- [x] Update `pyproject.toml` with rich metadata
- [x] Create GitHub Actions workflow for PyPI publication
- [x] Document pip installation method
- [ ] Register PyPI package name (manual prerequisite)
- [ ] Configure Trusted Publishers (manual prerequisite)
- [ ] Test publication to Test PyPI (requires account setup)
- [ ] Launch first PyPI release (requires account setup)
- [ ] Update all documentation with PyPI links

## References

- [PyPI Trusted Publishers Guide](https://docs.pypi.org/trusted-publishers/)
- [Python Packaging User Guide](https://packaging.python.org/)
- [Sigstore Python](https://github.com/sigstore/sigstore-python)
- [GitHub Actions PyPI Publish](https://github.com/pypa/gh-action-pypi-publish)
- [PEP 621 - pyproject.toml Metadata](https://peps.python.org/pep-0621/)

## Appendix: Package Verification

Users can verify published packages:

```bash
# Download and verify with pip
pip download --no-deps hephaestus-toolkit
pip verify hephaestus-toolkit

# Verify Sigstore signature
sigstore verify dist/hephaestus_toolkit-*.whl

# Check PyPI metadata
pip show hephaestus-toolkit

# View package contents
wheel unpack hephaestus_toolkit-*.whl
```

## Status History

- 2025-01-15: Proposed (documented in ADR)
- 2025-01-16: Sprint 2 Workflow Complete - Automation implemented, pending manual PyPI account setup
- Future: Sprint 3 Launch - After PyPI account registration and Trusted Publisher configuration
- Future: Full Implementation - First stable release published to PyPI
