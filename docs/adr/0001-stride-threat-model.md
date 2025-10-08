# ADR-001: STRIDE Threat Model for Hephaestus CLI and Release Pipeline

**Status:** Accepted  
**Date:** 2025-01-08  
**Last Updated:** 2025-01-XX  
**Authors:** Security Review Team  
**Reviewers:** Platform Engineering

## Context

Hephaestus is a developer toolkit that provides CLI commands for code quality, refactoring, workspace cleanup, and release management. The tool has access to:

- Local filesystem (with potential for destructive operations)
- Network resources (GitHub API, release downloads)
- Subprocess execution (external tools like ruff, mypy, pytest)
- Sensitive credentials (GitHub tokens)

This document applies the STRIDE threat modeling framework to identify security risks and recommend mitigations.

## STRIDE Analysis

### Spoofing Identity

**Threat:** Attacker impersonates a legitimate release source or GitHub API endpoint

**Attack Scenarios:**

1. DNS spoofing redirects release downloads to malicious servers
2. Man-in-the-middle attack intercepts GitHub API calls
3. Compromised GitHub account publishes malicious releases

**Existing Mitigations:**

- HTTPS for all network communications
- GitHub token authentication

**Recommended Mitigations:**

- ✅ Implement SHA-256 checksum verification for wheelhouse downloads
- ✅ Add Sigstore attestation for cryptographic proof of provenance
- ✅ Pin expected repository patterns
- Consider certificate pinning for critical endpoints

**Priority:** High

---

### Tampering with Data

**Threat:** Attacker modifies release artifacts, configuration files, or code during transit or at rest

**Attack Scenarios:**

1. Wheelhouse archive modified during download (network MITM)
2. Release assets replaced on compromised GitHub account
3. Configuration files (pyproject.toml, .pre-commit-config.yaml) tampered with
4. Source code modifications not caught by guard rails

**Existing Mitigations:**

- HTTPS encryption in transit
- Pre-commit hooks enforce code quality
- Guard rails pipeline validates code before commit

**Recommended Mitigations:**

- ✅ Implement SHA-256 checksum verification with published manifests
- ✅ Add Sigstore signatures for releases
- Consider read-only configuration defaults
- Implement file integrity monitoring for critical configs

**Priority:** High

---

### Repudiation

**Threat:** Actions are performed without audit trail, making it impossible to prove who did what

**Attack Scenarios:**

1. Cleanup command deletes files without logging what was removed
2. Release installation happens without record of which version was installed
3. Guard rails failures don't persist logs for review

**Existing Mitigations:**

- CLI outputs actions to stdout with Rich formatting
- Git history tracks code changes

**Recommended Mitigations:**

- ✅ Implement structured JSON logging with timestamps and user context
- Add optional audit log file for destructive operations
- Include release installation history in metadata file
- Emit cleanup manifests before deletion

**Priority:** Medium

---

### Information Disclosure

**Threat:** Sensitive information is exposed through logs, error messages, or telemetry

**Attack Scenarios:**

1. GitHub tokens appear in error messages or debug output
2. File paths expose sensitive directory structure
3. Telemetry inadvertently collects PII or sensitive data
4. Cached release archives contain sensitive build information

**Existing Mitigations:**

- Tokens read from environment variables
- No telemetry currently implemented

**Recommended Mitigations:**

- ✅ Sanitize all error messages to remove tokens
- Implement token redaction in logs (show only first/last 4 chars)
- Make telemetry opt-in with clear privacy policy
- Document what data is collected and why
- Add `--redact-paths` option for sensitive directory names

**Priority:** Medium

---

### Denial of Service

**Threat:** Resource exhaustion or hanging operations prevent legitimate use

**Attack Scenarios:**

1. Slow or malicious HTTP endpoint causes indefinite hang during release download
2. Infinite retry loop exhausts network resources
3. Cleanup command recursively processes massive directory trees
4. Guard rails subprocess hangs indefinitely

**Existing Mitigations:**

- Configurable timeout for release downloads (DEFAULT_TIMEOUT)
- Max retries limit (DEFAULT_MAX_RETRIES)

**Recommended Mitigations:**

- ✅ Implement exponential backoff with jitter for retries
- ✅ Add circuit breaker pattern for repeated failures
- Set maximum depth for directory traversal in cleanup
- Add timeout for each guard rail subprocess
- Implement progress indicators for long-running operations

**Priority:** Medium

---

### Elevation of Privilege

**Threat:** Attacker gains unauthorized access or executes code with elevated permissions

**Attack Scenarios:**

1. Cleanup command with `--extra-path /` deletes system files
2. Command injection through unsafe subprocess calls
3. Path traversal in release asset extraction
4. Privilege escalation through setuid binaries in cleanup target

**Existing Mitigations:**

- Git repository root detection limits scope
- Subprocess uses list form (not shell=True)

**Recommended Mitigations:**

- ✅ Refuse cleanup on dangerous paths (/, /home, /usr, /etc) unless `--allow-outside-root`
- ✅ Validate all subprocess arguments (no shell injection)
- ✅ Sanitize release asset filenames (strip .., /, path separators)
- Add confirmation prompt for operations outside repository
- Implement dry-run mode for previewing destructive operations
- Drop privileges when possible (run as non-root)

**Priority:** High

## Attack Surface Analysis

### 1. CLI Entry Points

**Surface:**

- User-provided arguments (paths, URLs, tokens)
- Environment variables (GITHUB_TOKEN)
- Configuration files (pyproject.toml, refactor.config.yaml)

**Risks:**

- Command injection via unsanitized arguments
- Path traversal via user-provided paths
- Token leakage through error messages

**Mitigations:**

- ✅ Use typer type validation for all inputs
- ✅ Sanitize and validate all file paths
- ✅ Redact tokens in all output

---

### 2. Network Operations

**Surface:**

- GitHub API calls
- Release asset downloads
- CDN requests

**Risks:**

- Man-in-the-middle attacks
- Compromised CDN nodes
- Slow/malicious endpoints (DoS)

**Mitigations:**

- ✅ HTTPS only, no HTTP fallback
- ✅ Timeout and retry with backoff
- ✅ Checksum verification
- Consider certificate pinning

---

### 3. Filesystem Operations

**Surface:**

- Cleanup deletion operations
- Release extraction
- Log file writes
- Configuration file reads

**Risks:**

- Accidental data loss
- Path traversal
- Symlink attacks
- Permission issues

**Mitigations:**

- ✅ Path validation and sanitization
- ✅ Dangerous path blocklist
- ✅ Dry-run mode
- Check for symlinks before deletion
- Validate extracted file paths

---

### 4. Subprocess Execution

**Surface:**

- ruff, mypy, pytest, pip-audit invocations
- git commands
- poetry/uv commands

**Risks:**

- Command injection
- Unexpected tool behavior
- Tool vulnerabilities
- Resource exhaustion

**Mitigations:**

- ✅ Use list form for subprocess.run (not shell=True)
- ✅ Validate tool availability before execution
- ✅ Set timeout for all subprocesses
- Pin tool versions in development
- Audit subprocess output for sensitive data

## Security Requirements

### Authentication & Authorization

- [ ] Token validation before GitHub API calls
- [x] Fine-grained token permissions documentation
- [ ] Token expiration handling

### Data Protection

- [x] HTTPS for all network traffic
- [x] SHA-256 checksum verification for downloads
- [x] Sigstore attestation validation
- [x] Token redaction in logs

### Input Validation

- [x] Type validation via typer
- [x] Path sanitization and validation
- [x] URL validation (scheme, domain allowlist)
- [x] Asset filename sanitization

### Audit & Monitoring

- [x] Structured logging (JSON format)
- [x] Audit trail for destructive operations
- [x] Release installation history
- [ ] Telemetry with privacy controls (planned Q2 2025, ADR-0003)

### Error Handling

- [x] User-friendly error messages
- [x] No sensitive data in errors
- [x] Graceful degradation on failures
- [x] Circuit breaker for repeated failures

## Secure Coding Practices

1. **Least Privilege:** Run with minimum required permissions
2. **Defense in Depth:** Multiple layers of validation
3. **Fail Secure:** Default to safe behavior on errors
4. **Privacy by Design:** Opt-in telemetry, minimal data collection
5. **Secure Defaults:** Conservative settings out of the box

## Implementation Roadmap

### Phase 1: Critical Security (High Priority) ✅ COMPLETE

- [x] Implement checksum verification for releases
- [x] Add dangerous path blocklist for cleanup
- [x] Sanitize release asset filenames
- [x] Add token redaction in logs

### Phase 2: Hardening (Medium Priority) ✅ COMPLETE

- [x] Implement structured JSON logging
- [x] Add exponential backoff and circuit breakers
- [x] Create dry-run mode for cleanup
- [x] Add confirmation prompts for risky operations

### Phase 3: Advanced Features (Low Priority)

- [x] Sigstore attestation validation
- [ ] Certificate pinning (deferred - not required for current threat model)
- [ ] Privacy-preserving telemetry (planned Q2 2025, see ADR-0003)
- [x] Automated security testing in CI (CodeQL implemented)

## Review & Updates

This threat model should be reviewed:

- Quarterly by the security team
- After major feature additions
- After security incidents
- When new attack vectors are discovered

**Next Review:** 2025-04-08

## References

- [OWASP Threat Modeling](https://owasp.org/www-community/Threat_Modeling)
- [Microsoft STRIDE](https://learn.microsoft.com/en-us/azure/security/develop/threat-modeling-tool-threats)
- [NIST SP 800-154: Guide to Data-Centric System Threat Modeling](https://csrc.nist.gov/publications/detail/sp/800-154/draft)

## Conclusion

Hephaestus has a moderate attack surface due to its filesystem operations, network access, and subprocess execution. The highest priority threats are:

1. **Tampering/Spoofing:** Compromised releases (needs checksum verification)
2. **Elevation of Privilege:** Dangerous cleanup operations (needs path validation)
3. **Denial of Service:** Hanging network calls (needs timeouts/backoff)

Implementing the recommended mitigations will significantly improve the security posture. The roadmap provides a phased approach to addressing threats based on risk and priority.

## Status History

- **2025-01-08:** Draft - Initial STRIDE threat model completed
- **2025-01-11:** Accepted - All high-priority mitigations implemented:
  - ✅ SHA-256 checksum verification for releases
  - ✅ Sigstore attestation support
  - ✅ Dangerous path protection in cleanup
  - ✅ Network timeouts and exponential backoff
  - ✅ SECURITY.md published with disclosure process
