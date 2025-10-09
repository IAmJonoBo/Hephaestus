---
title: "Release Process Guide"
description: "This guide explains how to release new versions of Hephaestus. Hephaestus uses automated release workflows with manual preparation steps. The release process..."
---
This guide explains how to release new versions of Hephaestus.

## Overview

Hephaestus uses automated release workflows with manual preparation steps. The release process is designed to be safe, repeatable, and auditable.

### Release Types

- **Major (X.0.0)**: Breaking changes, incompatible API changes
- **Minor (0.X.0)**: New features, backward compatible
- **Patch (0.0.X)**: Bug fixes, backward compatible

### Automated vs Manual

**Automated (via GitHub Actions):**

- Tag creation and pushing
- GitHub Release creation
- Wheelhouse building and packaging
- Asset attachment to releases

**Manual (requires human):**

- Version number decision
- CHANGELOG updates
- Code changes and commits
- Quality validation
- PR review and merge

## Quick Release (Patch)

For simple patch releases with bug fixes:

```bash
# 1. Update version
vim pyproject.toml  # Change version to X.Y.Z

# 2. Update CHANGELOG
vim CHANGELOG.md  # Add new version section

# 3. Commit and push to main
git add pyproject.toml CHANGELOG.md
git commit -m "chore: Prepare release vX.Y.Z"
git push origin main

# 4. Automation takes over (tag, release, wheelhouse)
```

## Full Release Process (Minor/Major)

### Phase 1: Planning

1. **Review completed work:**
   - Check closed PRs since last release
   - Review `Next_Steps.md` for completed items
   - Identify breaking changes (major) vs new features (minor)

2. **Choose version number:**
   - Follow [Semantic Versioning](https://semver.org/)
   - Check current version: `grep version pyproject.toml`
   - Decide: Major? Minor? Patch?

3. **Create milestone/project board:**
   - Group related issues/PRs
   - Track completion status

### Phase 2: Preparation

1. **Create release branch (for major/minor):**

   ```bash
   git checkout main
   git pull origin main
   git checkout -b release/vX.Y.Z
   ```

2. **Update version number:**

   ```bash
   # Edit pyproject.toml
   vim pyproject.toml

   # Change version field
   [project]
   version = "X.Y.Z"
   ```

3. **Update CHANGELOG.md:**

   ```markdown
   ## [X.Y.Z] - YYYY-MM-DD

   ### Added

   - New feature descriptions

   ### Changed

   - Breaking changes (if major)
   - Non-breaking changes

   ### Fixed

   - Bug fixes

   ### Security

   - Security improvements
   ```

4. **Update documentation:**
   - README.md "What's New" section
   - Getting started guide (if needed)
   - Migration guide (if breaking changes)
   - API reference (if API changes)

5. **Run quality gates:**

   ```bash
   # Clean workspace
   hephaestus cleanup --deep-clean

   # Check for drift
   hephaestus guard-rails --drift

   # Run all quality checks
   hephaestus guard-rails

   # Validate all gates
   python3 scripts/validate_quality_gates.py
   ```

6. **Commit changes:**

   ```bash
   git add .
   git commit -m "chore: Prepare release vX.Y.Z

   - Update version to X.Y.Z
   - Update CHANGELOG with release notes
   - Update documentation
   - [Additional changes]
   "
   ```

### Phase 3: Review

1. **Push release branch:**

   ```bash
   git push origin release/vX.Y.Z
   ```

2. **Create Pull Request:**
   - Title: `Release vX.Y.Z`
   - Description: Copy highlights from CHANGELOG
   - Labels: `release`, `documentation`
   - Assignees: Release manager + reviewer

3. **PR Review checklist:**
   - [ ] Version number correct
   - [ ] CHANGELOG complete and accurate
   - [ ] Documentation updated
   - [ ] All CI checks pass
   - [ ] Test coverage maintained (≥85%)
   - [ ] No security vulnerabilities
   - [ ] Breaking changes documented (if major)

4. **Address feedback:**
   - Make requested changes
   - Push updates to release branch
   - Re-request review

5. **Merge PR:**
   - Use "Squash and merge" or "Merge commit"
   - Ensure commit message is clean
   - Delete release branch after merge

### Phase 4: Automated Release

Once merged to main, automation triggers:

1. **Automated Release Tagging workflow:**
   - Detects version change in `pyproject.toml`
   - Runs cleanup
   - Creates git tag `vX.Y.Z`
   - Pushes tag to GitHub
   - Creates GitHub Release with auto-generated notes

2. **Build Wheelhouse workflow:**
   - Triggers on release publication
   - Builds package with `uv build`
   - Creates wheelhouse archive
   - Uploads as workflow artifact
   - Attaches to GitHub Release

### Phase 5: Post-Release

1. **Verify release:**

   ```bash
   # Check tag exists
   git fetch --tags
   git tag | grep vX.Y.Z

   # Check GitHub Release
   gh release view vX.Y.Z

   # Check wheelhouse attached
   gh release view vX.Y.Z --json assets
   ```

2. **Test installation:**

   ```bash
   # In a fresh environment
   hephaestus release install --repository IAmJonoBo/Hephaestus --tag vX.Y.Z

   # Verify version
   hephaestus --version

   # Smoke test
   hephaestus --help
   hephaestus guard-rails --drift
   ```

3. **Update tracking:**
   - Close milestone
   - Update project board
   - Mark issues as released

4. **Communicate:**
   - Post release announcement
   - Update team/stakeholders
   - Tweet/blog (if appropriate)

## Hotfix Process

For urgent bug fixes that can't wait for next planned release:

1. **Create hotfix branch from tag:**

   ```bash
   git checkout -b hotfix/vX.Y.Z+1 vX.Y.Z
   ```

2. **Apply fix:**
   - Make minimal changes
   - Add regression test
   - Update CHANGELOG

3. **Fast-track review:**
   - Create PR to main
   - Mark as urgent
   - Get expedited review

4. **Release immediately:**
   - Follow normal release process
   - Communicate urgency in release notes

## Emergency Rollback

If critical issues discovered after release:

1. **Assess severity:**
   - Data loss/corruption: CRITICAL
   - Security vulnerability: CRITICAL
   - Broken functionality: HIGH
   - Performance degradation: MEDIUM

2. **For CRITICAL issues:**

   ```bash
   # Delete release
   gh release delete vX.Y.Z --yes

   # Delete tag locally
   git tag -d vX.Y.Z

   # Delete tag remotely
   git push origin :refs/tags/vX.Y.Z

   # Notify users immediately
   ```

3. **Publish security advisory (if needed):**
   - Use `.github/SECURITY.md` process
   - Follow disclosure template
   - Coordinate with users

4. **Prepare fixed release:**
   - Follow hotfix process
   - Increment patch version
   - Clearly document fix in CHANGELOG

See `.github/RELEASE_CHECKLIST_TEMPLATE.md` for detailed rollback procedures.

## Release Checklist

Before each release, complete the checklist in `.github/RELEASE_CHECKLIST_TEMPLATE.md`:

```bash
# Copy template
cp .github/RELEASE_CHECKLIST_TEMPLATE.md .github/RELEASE_CHECKLIST_v{X.Y.Z}.md

# Fill out checklist
vim .github/RELEASE_CHECKLIST_v{X.Y.Z}.md

# Track progress
git add .github/RELEASE_CHECKLIST_v{X.Y.Z}.md
git commit -m "chore: Add release checklist for vX.Y.Z"
```

## Automation Details

### Automated Release Tagging

**Workflow:** `.github/workflows/release-tag.yml`

**Triggers:** Push to `main` branch

**Actions:**

1. Checkout repository
2. Install uv
3. Run cleanup
4. Extract version from `pyproject.toml`
5. Check if tag already exists
6. Create and push tag (if new)
7. Create GitHub Release with generated notes

**Requirements:**

- Version in `pyproject.toml` must be new
- Workflow requires `contents: write` permission

### Build Wheelhouse

**Workflow:** `.github/workflows/publish.yml`

**Triggers:** Release published

**Actions:**

1. Checkout repository at release tag
2. Set up Python 3.12
3. Install uv and sync dependencies
4. Run cleanup
5. Build package with `uv build`
6. Create wheelhouse archive
7. Upload as workflow artifact
8. Attach to GitHub Release

**Artifacts:**

- `hephaestus-{version}-wheelhouse.tar.gz`
- Retained for 30 days in workflow artifacts
- Permanently attached to release

## Version Bumping Script

For convenience, use this script to bump version:

```bash
#!/usr/bin/env bash
# scripts/bump_version.sh

set -euo pipefail

if [ $# -ne 1 ]; then
    echo "Usage: $0 <version>"
    echo "Example: $0 0.3.0"
    exit 1
fi

VERSION="$1"

# Validate version format
if ! [[ "$VERSION" =~ ^[0-9]+\.[0-9]+\.[0-9]+$ ]]; then
    echo "Error: Invalid version format. Use X.Y.Z"
    exit 1
fi

echo "Bumping version to $VERSION..."

# Update pyproject.toml
sed -i.bak "s/^version = \".*\"/version = \"$VERSION\"/" pyproject.toml
rm pyproject.toml.bak

# Update __init__.py if it has version
if grep -q "__version__" src/hephaestus/__init__.py; then
    sed -i.bak "s/__version__ = \".*\"/__version__ = \"$VERSION\"/" src/hephaestus/__init__.py
    rm src/hephaestus/__init__.py.bak
fi

echo "Version bumped to $VERSION"
echo ""
echo "Next steps:"
echo "1. Update CHANGELOG.md"
echo "2. git add pyproject.toml CHANGELOG.md"
echo "3. git commit -m 'chore: Prepare release v$VERSION'"
echo "4. git push origin main"
```

## Troubleshooting

### Tag Already Exists

```bash
# Delete local tag
git tag -d vX.Y.Z

# Delete remote tag
git push origin :refs/tags/vX.Y.Z

# Try again
```

### Workflow Failed

1. Check workflow logs in GitHub Actions
2. Common issues:
   - Network timeout: Re-run workflow
   - Test failure: Fix tests before release
   - Permission error: Check workflow permissions

### Release Notes Empty

GitHub auto-generates notes from PR titles. Ensure PRs have:

- Clear, descriptive titles
- Proper labels (enhancement, bug, documentation)
- Milestone assigned

### Wheelhouse Not Attached

1. Check Build Wheelhouse workflow status
2. Verify release was published (not draft)
3. Check workflow artifacts for archive
4. Manually attach if needed:
   ```bash
   gh release upload vX.Y.Z path/to/wheelhouse.tar.gz
   ```

## Best Practices

1. **Release regularly:** Small, frequent releases are better than large, infrequent ones
2. **Test thoroughly:** Use the release checklist every time
3. **Communicate clearly:** Write good CHANGELOG entries
4. **Document breaking changes:** Be explicit about what breaks
5. **Monitor post-release:** Watch for issues in the first 24 hours
6. **Learn from mistakes:** Update this guide based on experience

## Related Documentation

- [Release Checklist Template](/how-to/.github/RELEASE_CHECKLIST_TEMPLATE/)
- [Pre-Release Checklist](/docs/pre-release-checklist/)
- [CHANGELOG](/CHANGELOG/)
- [Semantic Versioning](https://semver.org/)
- [GitHub Release Documentation](https://docs.github.com/en/repositories/releasing-projects-on-github)

## Questions?

- Check existing releases for examples
- Review past release PRs
- Consult with previous release managers
- Open a discussion on GitHub

---

**Remember:** Releases should be boring. If it's exciting, something went wrong. ✅
