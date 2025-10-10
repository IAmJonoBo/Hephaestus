---
title: "Pre-Release Automation Checklist"
description: "Use this quick checklist before cutting a release to ensure the repository is pristine and all automation hooks have run: 1. Confirm automation parity - [ ] uv..."
---

Use this quick checklist before cutting a release to ensure the repository is pristine and all automation hooks have run:

1. **Confirm automation parity**
   - [ ] `uv sync --extra dev --extra qa`
   - [ ] `uv run pre-commit run --all-files`
   - [ ] `uv run hephaestus cleanup --deep-clean`

2. **Verify quality gates locally**
   - [ ] `uv run ruff check .`
   - [ ] `uv run mypy src tests`
   - [ ] `uv run pytest`

3. **Run packaging sanity checks**
   - [ ] `uv run hephaestus cleanup --deep-clean` (repeat to confirm clean tree)
   - [ ] Remove temporary artefacts (`dist/`, `build/`, coverage caches) if present—these
         directories are `.gitignore`d but cleaning them locally keeps release diffs obvious
   - [ ] Confirm the latest release will have a wheelhouse by spot-checking the `Build Wheelhouse`
         workflow and ensuring the zipped artefact downloads successfully
   - [ ] Dry-run the installer with `uv run hephaestus release install --cleanup --remove-archive`
         against the latest tag to verify the wheelhouse installs cleanly from GitHub Releases

4. **Review documentation**
   - [ ] Update `docs/lifecycle.md` and `README.md` if automation changed
   - [ ] Record release notes / changelog summary

5. **Tag and release**
   - When ready, push to `main`—the release workflow will perform the final cleanup sweep and tag automatically.

---

## Rollback Procedures

If a release is found to be broken or contains security vulnerabilities, follow these steps to roll back safely.

### Immediate Actions

1. **Stop the Bleeding**
   - [ ] Document the issue with reproduction steps
   - [ ] Determine severity (Critical, High, Medium, Low)
   - [ ] Notify stakeholders immediately if severity is High or Critical

2. **Identify Last Known Good Version**

   ```bash
   # List recent releases
   gh release list --repo IAmJonoBo/Hephaestus --limit 10

   # Review specific release
   gh release view v0.1.0 --repo IAmJonoBo/Hephaestus
   ```

3. **Advise Users to Pin to Safe Version**
   - Create a pinned GitHub issue announcing the problem
   - Update README.md with warning banner
   - Send notification through established channels

   ```bash
   # Users should pin to last known good version
   hephaestus release install --tag v0.0.9
   ```

### Release Revocation

4. **Delete Bad Release** (if necessary)

   ```bash
   # Delete the problematic release
   gh release delete v0.1.0 --repo IAmJonoBo/Hephaestus --yes

   # Delete the tag
   git tag -d v0.1.0
   git push origin :refs/tags/v0.1.0
   ```

5. **Publish Security Advisory** (for security issues)
   - Navigate to Repository → Security → Advisories
   - Click "New draft security advisory"
   - Fill in:
     - Title: Clear description of the issue
     - Description: Impact, affected versions, workarounds
     - Severity: Use CVSS calculator
     - Affected versions: Specify version range
   - Publish when fix is ready

### Fix and Recovery

6. **Prepare Fixed Version**
   - [ ] Identify root cause of the issue
   - [ ] Implement fix on `main` branch
   - [ ] Add regression test to prevent recurrence
   - [ ] Update CHANGELOG.md with fix details
   - [ ] Bump version (use patch version for hotfixes)

7. **Release Hotfix**
   - [ ] Run full pre-release checklist above
   - [ ] Tag new release (e.g., v0.1.1)
   - [ ] Verify wheelhouse builds successfully
   - [ ] Test installation from new release

8. **Announce Resolution**
   - [ ] Update pinned issue with resolution
   - [ ] Remove warning banner from README.md
   - [ ] Publish security advisory (if applicable)
   - [ ] Send "all clear" notification to users

### Post-Incident Review

9. **Document Learnings**
   - [ ] Write post-mortem in `docs/incidents/YYYY-MM-DD-description.md`
   - [ ] Identify gaps in testing, automation, or monitoring
   - [ ] Update ADRs if architectural changes needed
   - [ ] Schedule preventive improvements

10. **Improve Processes**
    - [ ] Add automated checks to prevent recurrence
    - [ ] Update pre-release checklist with new items
    - [ ] Enhance CI/CD gates if needed
    - [ ] Train team on lessons learned

### Rollback Decision Matrix

| Severity     | Issue Type                                        | Action                                   | Timeline    |
| ------------ | ------------------------------------------------- | ---------------------------------------- | ----------- |
| **Critical** | Remote code execution, data loss, security breach | Immediate revocation + security advisory | < 1 hour    |
| **High**     | Broken core functionality, dependency CVE         | Fast-track hotfix + pin advisory         | < 4 hours   |
| **Medium**   | Non-critical bugs, performance degradation        | Scheduled hotfix in next release         | < 48 hours  |
| **Low**      | Cosmetic issues, documentation errors             | Fix in next regular release              | Next sprint |

### Automation Opportunities

Future enhancements to streamline rollback:

- [ ] `hephaestus release revoke` command to automate deletion
- [ ] CI workflow to test rollback procedures
- [ ] Automated security advisory creation from template
- [ ] Slack/email integration for incident notifications
- [ ] Rollback smoke test suite

### Related Documentation

- [Security Policy](/SECURITY/) - Vulnerability disclosure process
- [STRIDE Threat Model](/./adr/0001-stride-threat-model/) - Risk analysis
- [Operating Safely](/./how-to/operating-safely/) - Safe usage practices

---

Remember: A smooth rollback process requires practice. Consider running rollback drills quarterly to ensure the team is prepared.
