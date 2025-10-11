# Frontier Standards Charter

This charter codifies the frontier-grade engineering standards for the Hephaestus toolkit. It
captures every enforced quality gate, the required developer behaviors, and the automation that keeps
those expectations evergreen. The goal is to make quality non-negotiable while remaining explicit
about the few approved places where judgment calls or waivers apply.

## Scope & Responsibilities

These standards apply to everyone who contributes to, packages, or operates Hephaestus. They cover the
full software development lifecycle:

- Discovery & technical planning
- Local development and environment hygiene
- Code quality, testing, and security validation
- Release management and supply-chain assurance
- Ongoing operations, observability, and currency management
- Documentation, knowledge capture, and AI/automation integration

## Guiding Principles

1. **Automate the baseline.** Every recurring control must be enforced by scripts, guard-rails, or
   CI workflows before it becomes policy.
2. **Fail closed on safety-critical paths.** Cleanup, release installation, and supply-chain
   verification abort rather than run with reduced coverage unless an explicit escape hatch is
   documented.
3. **Prefer typed, observable code.** Strict typing, structured logging, and telemetry hooks are the
   default—new code without them requires sign-off.
4. **Document as you deliver.** Diátaxis-aligned documentation is a release criterion, not an
   afterthought.
5. **Reproduce everything.** All environments are provisioned with `uv`, wheelhouses are signed, and
   every scripted action is idempotent.

## Lifecycle Standards

### 1. Discovery & Planning

| Requirement                                                     | Enforcement                                                                                          |
| --------------------------------------------------------------- | ---------------------------------------------------------------------------------------------------- |
| Architectural decisions captured as ADRs before large refactors | `docs/adr/` templates (ADR-0000)                                                                     |
| Execution plans reviewed for multi-week initiatives             | `hephaestus plan` command output and review meeting notes                                            |
| Risk and threat analysis refreshed yearly                       | [`docs/explanation/frontier-red-team-gap-analysis.md`](frontier-red-team-gap-analysis.md) & ADR-0001 |
| Roadmapping and gap tracking centralised                        | `Next_Steps.md`, `IMPLEMENTATION_SUMMARY.md`, project boards                                         |

### 2. Environment & Tooling Hygiene

| Requirement                               | Enforcement                                                                        |
| ----------------------------------------- | ---------------------------------------------------------------------------------- |
| Use `uv` for dependency management        | `uv sync --extra dev --extra qa` mandated by setup docs                            |
| Detect drift before shipping              | `uv run hephaestus guard-rails --drift` (required before PR open)                  |
| Prevent metadata cruft                    | Pre-commit `hephaestus cleanup` hook; `.github/workflows/macos-metadata-guard.yml` |
| Only operate within repo roots by default | `cleanup` safety rails guard `/`, home, system paths                               |

### 3. Development & Coding Standards

- Respect Ruff linting profile (`E`, `F`, `I`, `UP`, `B`, `C4`) and 100-character formatting enforced
  via `ruff check --select I --fix` + `ruff format`.
- Mypy strict mode (`disallow_untyped_defs`, `warn_return_any`, etc.) guards `src/` and
  `tests/`.
- New public APIs ship with docstrings, usage examples, and type annotations.
- Nested Typer command decorators are prohibited and blocked by `scripts/lint_nested_decorators.py`
  in pre-commit and CI.
- Structured logging uses `hephaestus.logging.get_logger()` with run IDs and operation IDs for every
  CLI entry point.

### 4. Testing & Quality Gates

| Gate                     | Threshold / Expectation                                                 | Primary Command                                                   | Automation                                                     |
| ------------------------ | ----------------------------------------------------------------------- | ----------------------------------------------------------------- | -------------------------------------------------------------- |
| Unit & integration tests | 100% pass, coverage ≥ 85%, warnings-as-errors                           | `uv run pytest`                                                   | CI (`ci.yml`), `guard-rails`, `validate_quality_gates.py`      |
| Linting                  | Zero Ruff violations                                                    | `uv run ruff check .`                                             | Pre-commit & CI                                                |
| Formatting               | Zero drift                                                              | `uv run ruff check --select I .` + `uv run ruff format --check .` | Pre-commit & CI                                                |
| Type safety              | No mypy errors                                                          | `uv run mypy src tests`                                           | Pre-commit & CI                                                |
| YAML hygiene             | No yamllint errors under `.trunk/configs/.yamllint.yaml`                | `uv run yamllint …`                                               | Guard-rails & quality gate script                              |
| Nested decorator lint    | Zero violations                                                         | `python3 scripts/lint_nested_decorators.py`                       | Pre-commit & CI                                                |
| Build reproducibility    | Wheels & sdists build cleanly                                           | `uv run uv build` (or `python3 -m build`)                         | `validate_quality_gates.py`, release workflows                 |
| Security audit           | `pip-audit --strict` clean (ignoring GHSA-4xh5-x5gv-qwph until patched) | `uv run pip-audit --strict --ignore-vuln GHSA-4xh5-x5gv-qwph`     | Guard-rails, scheduled `pip-audit.yml`                         |
| Workflow lint            | Actionlint passes                                                       | `bash scripts/run_actionlint.sh`                                  | Guard-rails, quality gate script, manual before workflow edits |

Run the full suite locally using either:

```bash
uv run hephaestus guard-rails
python3 scripts/validate_quality_gates.py
```

### 5. Security & Privacy

- Follow the disclosure process in [`SECURITY.md`](../../SECURITY.md); critical vulnerabilities target
  14-day remediation.
- Wheelhouse installs must verify SHA-256 manifests and Sigstore bundles unless `--allow-unsigned`
  is approved for an isolated environment.
- Release downloads enforce HTTPS, bounded retries, and sanitized asset names (`src/hephaestus/release.py`).
- Cleanup requires explicit confirmation for paths outside the repository and records JSON audit
  manifests under `.hephaestus/audit/` for compliance.
- Dependency hygiene is augmented by Dependabot, weekly `pip-audit` workflow, and pre-commit hooks.

### 6. Release Management

| Standard                                          | Mechanism                                                                      |
| ------------------------------------------------- | ------------------------------------------------------------------------------ |
| Semantic versioning applied (`MAJOR.MINOR.PATCH`) | Manual review via `docs/how-to/release-process.md`                             |
| Release prep checklist executed                   | [`docs/pre-release-checklist.md`](../pre-release-checklist.md)                 |
| Automated tagging & GitHub Releases               | `.github/workflows/release-tag.yml`                                            |
| Wheelhouse build & attachment                     | `.github/workflows/publish.yml`                                                |
| Installation verification                         | `uv run hephaestus release install --cleanup --remove-archive`                 |
| Rollback readiness                                | Procedures codified in pre-release checklist; gh release delete workflow       |
| Security attestation backlog                      | Sigstore bundles tracked in `Next_Steps.md` (status reported in charter notes) |

### 7. Operations & Currency

- **CI (uv with offline-ready install)**: `ci.yml` runs `uv sync`, `pytest`, builds wheelhouse artifacts,
  and executes offline QA on self-hosted runners.
- **CodeQL**: Weekly plus on-push/pull-request static analysis (`codeql.yml`).
- **Dependency Review**: Pull-request scans via `dependency-review.yml`.
- **pip-audit Scheduled Sweep**: Weekly security audit (`pip-audit.yml`).
- **Pre-commit Autoupdate**: Weekly hook refresh (`pre-commit-autoupdate.yml`).
- **TurboRepo Release Monitor**: Daily schedule to open issues when upstream TurboRepo releases change
  (`turborepo-monitor.yml` + `ops/turborepo-release.json`).
- **macOS Metadata Guard**: Prevents `.DS_Store` and friends from entering history.
- **Dependabot**: Weekly package and GitHub Action updates (`.github/dependabot.yml`).

Each workflow must remain green before a release; failures block the release checklist until
resolved or explicitly waived by the maintainer of record.

### 8. Observability & Telemetry

- CLI commands default to human-readable logs but must support `--log-format json` for machine
  ingestion (`docs/how-to/ai-agent-integration.md`).
- Telemetry events are defined in `src/hephaestus/telemetry.py`; every new command registers
  structured events with run IDs.
- OpenTelemetry spans are tracked in `Next_Steps.md` & ADR-0003; once delivered they will be
  mandatory for long-running operations.

### 9. Documentation & Knowledge Management

- All user-facing features require updates to the Diátaxis docs (`docs/how-to/`, `docs/reference/`,
  `docs/tutorials/`, `docs/explanation/`).
- README quick-start commands must remain accurate for the latest release; changes to CLI signatures
  update `docs/reference/cli.md` and `schemas`.
- Rollback playbooks, safety guides, and AI integration guides are canonical references and must be
  updated with new options or flags.

### 10. AI & Automation Readiness

- Export schemas with `hephaestus schema --output schemas.json` whenever the CLI surface changes.
- Maintain deterministic command outputs (Rich tables, JSON logs) to keep AI integrations reliable.
- Link AI-facing guidance in [`docs/how-to/ai-agent-integration.md`](../how-to/ai-agent-integration.md).
- Guard-rails `--drift` output must list remediation commands to keep agent remediation consistent.

## Quality Gate Escape Hatches

If a gate fails:

1. Investigate locally with the single-gate command listed above.
2. If the failure stems from known external constraints (e.g., `pip-audit` SSL trust chains in
   constrained containers), document the waiver in the PR description and re-run in a compliant
   environment before release.
3. Long-lived waivers require an issue in the tracker plus an entry in `Next_Steps.md` with owner and
   target date.

## Developer Workflow Checklist

1. `uv sync --extra dev --extra qa`
2. `uv run hephaestus guard-rails --drift`
3. Implement changes with lint/type/format hooks active.
4. `uv run hephaestus guard-rails` (or `python3 scripts/validate_quality_gates.py`)
5. Update docs + changelog; export schemas if CLI changed.
6. Ensure all GitHub Actions workflows are green; resolve or document any failures.
7. Submit PR with links to relevant docs/tests and checklist ticked.
8. Before release: follow the pre-release checklist and confirm wheelhouse install.

## Governance & Review Cadence

- **Quarterly**: Review this charter, frontier gap analysis, and `Next_Steps.md` to capture new
  threats or automation opportunities.
- **Monthly**: Audit workflow run history for flaky gates or drift, refresh dependency locks, and
  review Sigstore attestation coverage.
- **Per Release**: Validate charter alignment via checklist sign-off and ensure documentation is
  synchronized.

## References

- [Quality Gate Guide](../how-to/quality-gates.md)
- [Operating Safely](../how-to/operating-safely.md)
- [Testing Guide](../how-to/testing.md)
- [Release Process](../how-to/release-process.md)
- [AI Agent Integration](../how-to/ai-agent-integration.md)
- [Evergreen Lifecycle Playbook](../lifecycle.md)
- [Frontier Red Team & Gap Analysis](frontier-red-team-gap-analysis.md)
- [`scripts/README.md`](../../scripts/README.md)
- [`src/hephaestus/cli.py`](../../src/hephaestus/cli.py) and [`src/hephaestus/cli/`](../../src/hephaestus/cli/)
- GitHub Actions workflows under `.github/workflows/`

---

Maintaining frontier status means treating this charter as executable policy. When a new tool,
workflow, or risk emerges, update the automation first, then amend the charter so that expectations
stay aligned with reality.
