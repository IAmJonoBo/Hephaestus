# Security Policy

## Supported Versions

We currently support the latest release of Hephaestus. Security updates are applied to the most recent version.

| Version  | Supported          |
| -------- | ------------------ |
| latest   | :white_check_mark: |
| < latest | :x:                |

## Reporting a Vulnerability

We take security vulnerabilities seriously. If you discover a security issue, please report it responsibly by following these steps:

### How to Report

1. **Do not** open a public GitHub issue for security vulnerabilities
2. Email security reports to: [opensource@hephaestus.dev](mailto:opensource@hephaestus.dev)
3. Include the following information in your report:
   - Description of the vulnerability
   - Steps to reproduce the issue
   - Potential impact
   - Suggested fix (if available)

### What to Expect

- **Initial Response**: Within 48 hours of receiving your report
- **Status Update**: Regular updates every 5-7 business days
- **Resolution Timeline**: We aim to address critical vulnerabilities within 14 days
- **Disclosure**: We will work with you to coordinate responsible disclosure once a fix is available

### Vulnerability Categories

We are particularly interested in reports related to:

- **Supply Chain**: Compromised dependencies, wheelhouse integrity, signature verification
- **Command Injection**: Unsafe subprocess execution, shell injection in CLI commands
- **Path Traversal**: File operations outside intended directories, unsafe cleanup operations
- **Denial of Service**: Hanging network calls, resource exhaustion
- **Information Disclosure**: Sensitive data leakage in logs, error messages, or telemetry

### Security Best Practices

When using Hephaestus:

1. **Verify Releases**: Always download releases from official GitHub Releases
2. **Audit Dependencies**: Run `pip-audit --strict` regularly
3. **Review Cleanup Paths**: Double-check `--extra-path` arguments before running cleanup
4. **Secure Tokens**: Use environment variables for GitHub tokens, never hardcode them
5. **Update Regularly**: Keep Hephaestus and its dependencies up to date

## Security Features

Hephaestus includes several security safeguards:

- **Cleanup Protection**: Guards against dangerous path operations (/, home directory)
- **Dependency Auditing**: Integrated `pip-audit` in guard-rails pipeline
- **Pre-commit Hooks**: Automated security checks before code is committed
- **Network Timeouts**: Configurable timeouts and retry logic for release downloads
- **Checksum Verification**: SHA-256 verification for wheelhouse downloads (in progress)

## Threat Model

For detailed threat modeling information, see the architecture decision records in `docs/adr/`.

## Security Updates

Security patches will be:

- Released as soon as fixes are available
- Announced in release notes with [SECURITY] prefix
- Backported to supported versions when necessary

Thank you for helping keep Hephaestus secure!
