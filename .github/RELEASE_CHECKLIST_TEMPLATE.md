# Release Checklist: vX.Y.Z

Use this checklist for each release to ensure quality and consistency.

## Pre-Release Validation

### Code Quality
- [ ] All tests passing locally: `pytest`
- [ ] Test coverage ≥85%: Check coverage report
- [ ] Linting clean: `ruff check .`
- [ ] Formatting correct: `ruff format --check .`
- [ ] Type checking passes: `mypy src tests`
- [ ] No nested decorator violations: `python3 scripts/lint_nested_decorators.py src/hephaestus`
- [ ] Security audit clean: `pip-audit --strict --ignore-vuln GHSA-4xh5-x5gv-qwph`
- [ ] Guard rails pass: `hephaestus guard-rails`
- [ ] All quality gates pass: `python3 scripts/validate_quality_gates.py`

### Environment & Dependencies
- [ ] No tool version drift: `hephaestus guard-rails --drift`
- [ ] Dependencies up to date: Check Dependabot/Renovate PRs
- [ ] Python 3.12+ compatibility verified
- [ ] Python 3.13 compatibility verified (CI matrix)
- [ ] No known security vulnerabilities in dependencies

### Documentation
- [ ] CHANGELOG.md updated with new version section
- [ ] README.md reflects current features
- [ ] All new features documented in `docs/`
- [ ] CLI reference updated if commands changed
- [ ] Migration guide added if breaking changes
- [ ] Example code tested and working
- [ ] All internal links verified
- [ ] Version badges updated (if applicable)

### Version Management
- [ ] Version bumped in `pyproject.toml`
- [ ] Version consistent across all files
- [ ] Git tags fetched: `git fetch --tags`
- [ ] No existing tag for this version: `git tag | grep vX.Y.Z`
- [ ] Branch up to date with main: `git pull origin main`
- [ ] No uncommitted changes: `git status`

## Release Process

### 1. Prepare Release Branch (if needed)
```bash
# For major/minor releases, create release branch
git checkout -b release/vX.Y.Z
```

### 2. Final Cleanup
```bash
# Deep clean workspace
hephaestus cleanup --deep-clean

# Run comprehensive validation
hephaestus guard-rails

# Verify no drift
hephaestus guard-rails --drift
```

### 3. Update Documentation
- [ ] Update CHANGELOG.md:
  ```markdown
  ## [X.Y.Z] - YYYY-MM-DD
  
  ### Added
  - Feature 1
  
  ### Changed
  - Change 1
  
  ### Fixed
  - Bug fix 1
  
  ### Security
  - Security improvement 1
  ```

- [ ] Update README.md "What's New" section (if major/minor)
- [ ] Update any version references in documentation

### 4. Commit Changes
```bash
# Stage changes
git add CHANGELOG.md pyproject.toml README.md docs/

# Commit with clear message
git commit -m "chore: Prepare release vX.Y.Z

- Update version to X.Y.Z
- Update CHANGELOG with release notes
- Update documentation
"

# Push to remote
git push origin release/vX.Y.Z  # or main for patch releases
```

### 5. Create Release PR (for major/minor)
- [ ] Open PR from release branch to main
- [ ] Title: "Release vX.Y.Z"
- [ ] Description includes highlights from CHANGELOG
- [ ] All CI checks pass
- [ ] At least one approval received
- [ ] Merge PR to main

### 6. Tag and Release
The automated workflow will:
- [ ] Detect version change on main
- [ ] Run cleanup
- [ ] Create git tag `vX.Y.Z`
- [ ] Push tag to remote
- [ ] Create GitHub Release with generated notes

**Manual verification:**
```bash
# Pull latest main
git checkout main
git pull origin main

# Verify tag created
git fetch --tags
git tag | grep vX.Y.Z

# Check GitHub Release
gh release view vX.Y.Z
```

### 7. Wheelhouse Build
The automated workflow will:
- [ ] Build package artifacts
- [ ] Create wheelhouse archive
- [ ] Upload as workflow artifact
- [ ] Attach to GitHub Release

**Manual verification:**
```bash
# Check release assets
gh release view vX.Y.Z

# Should see: hephaestus-X.Y.Z-wheelhouse.tar.gz
```

## Post-Release Validation

### Installation Testing
- [ ] Test fresh install from PyPI (when available):
  ```bash
  pip install hephaestus==X.Y.Z
  hephaestus --version
  ```

- [ ] Test wheelhouse install:
  ```bash
  hephaestus release install --repository IAmJonoBo/Hephaestus --tag vX.Y.Z
  ```

- [ ] Verify all commands work:
  ```bash
  hephaestus --help
  hephaestus guard-rails --help
  hephaestus cleanup --help
  hephaestus tools --help
  hephaestus release --help
  hephaestus schema --help
  ```

### Smoke Tests
- [ ] Run guard-rails in test project
- [ ] Run cleanup in test project
- [ ] Export schema: `hephaestus schema`
- [ ] Check drift: `hephaestus guard-rails --drift`
- [ ] Get rankings (if analytics configured)

### Documentation Verification
- [ ] Documentation site builds: `mkdocs build`
- [ ] Documentation site renders correctly: `mkdocs serve`
- [ ] All links work (manual check key pages)
- [ ] Examples in docs work as written

### Communication
- [ ] Update project board/issues with release number
- [ ] Close milestone (if using milestones)
- [ ] Post release announcement (if major/minor):
  - [ ] GitHub Discussions
  - [ ] Team chat/Slack
  - [ ] Social media (if applicable)
  - [ ] Update project showcase (if applicable)

### Monitoring
- [ ] Watch for new issues related to release
- [ ] Monitor download/install metrics
- [ ] Check for security alerts
- [ ] Review CI/CD health

## Rollback Procedure (if needed)

If critical issues are discovered after release:

### Immediate Actions
1. **Assess severity:**
   - Critical: Data loss, security vulnerability
   - High: Feature broken, major regression
   - Medium: Minor bug, degraded UX
   - Low: Cosmetic issue, documentation error

2. **For Critical/High issues:**
   ```bash
   # Delete the release
   gh release delete vX.Y.Z --yes
   
   # Delete the tag
   git push origin :refs/tags/vX.Y.Z
   git tag -d vX.Y.Z
   
   # Publish security advisory if needed
   # See docs/pre-release-checklist.md for advisory template
   ```

3. **For Medium/Low issues:**
   - Plan patch release vX.Y.Z+1
   - Document workaround in release notes
   - Add to CHANGELOG

### Recovery Steps
- [ ] Identify root cause
- [ ] Create hotfix branch: `git checkout -b hotfix/vX.Y.Z+1`
- [ ] Apply fix with tests
- [ ] Run full quality gates
- [ ] Fast-track PR review
- [ ] Release patch version
- [ ] Communicate fix availability

### Post-Mortem
- [ ] Document what went wrong
- [ ] Update release checklist to prevent recurrence
- [ ] Improve tests/validation
- [ ] Share lessons learned with team

## Release Notes Template

Use this template for GitHub Release description:

```markdown
# Hephaestus vX.Y.Z

[Short description of release theme/focus]

## Highlights

- ✨ Major feature 1
- 🎯 Major feature 2
- 🔒 Security improvement

## What's Changed

### Added
- Feature 1 description (#PR)
- Feature 2 description (#PR)

### Changed
- Change 1 description (#PR)
- Change 2 description (#PR)

### Fixed
- Bug fix 1 description (#PR)
- Bug fix 2 description (#PR)

### Security
- Security fix 1 description (#PR)

## Installation

### Using pip
\`\`\`bash
pip install hephaestus==X.Y.Z
\`\`\`

### Using wheelhouse
\`\`\`bash
hephaestus release install --repository IAmJonoBo/Hephaestus --tag vX.Y.Z
\`\`\`

### From source
\`\`\`bash
git clone https://github.com/IAmJonoBo/Hephaestus.git
cd Hephaestus
git checkout vX.Y.Z
uv sync --extra dev --extra qa
\`\`\`

## Documentation

- [Getting Started](https://github.com/IAmJonoBo/Hephaestus/blob/vX.Y.Z/docs/tutorials/getting-started.md)
- [CHANGELOG](https://github.com/IAmJonoBo/Hephaestus/blob/vX.Y.Z/CHANGELOG.md)
- [Full Documentation](https://github.com/IAmJonoBo/Hephaestus/tree/vX.Y.Z/docs)

## Contributors

Special thanks to all contributors! 🎉

[List of contributors from GitHub]

## Full Changelog

[Link to full changelog comparison]
```

## Version Numbering Guide

Hephaestus follows [Semantic Versioning](https://semver.org/):

- **MAJOR (X.0.0)**: Incompatible API changes
  - Breaking changes to command signatures
  - Removed commands or features
  - Changed configuration format requiring migration

- **MINOR (0.X.0)**: New features, backward compatible
  - New commands
  - New command options
  - New ranking strategies
  - Enhanced functionality

- **PATCH (0.0.X)**: Bug fixes, backward compatible
  - Bug fixes
  - Documentation updates
  - Performance improvements
  - Security patches

## Sign-Off

- [ ] Release Manager: @username
- [ ] Reviewer: @username
- [ ] Date: YYYY-MM-DD
- [ ] Release Status: ✅ Completed / ⚠️ Rolled Back / 🔄 In Progress

---

**Release completed successfully! 🎉**

Next steps:
- Monitor for issues
- Plan next release features
- Update roadmap
