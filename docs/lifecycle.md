# Evergreen Lifecycle Playbook

This guide maps the Hephaestus toolkit to the full software development lifecycle and highlights the
upgrades we now ship to keep the project evergreen from discovery through long-term operations. Each
phase lists the core intent, the tooling we rely on, and practical tips for maximising developer
experience (DX), user experience (UX), and code quality (CQ).

## Overview Matrix

| Stage                    | Purpose                               | Tooling & Techniques                                                                                                | Outcomes                                           |
| ------------------------ | ------------------------------------- | ------------------------------------------------------------------------------------------------------------------- | -------------------------------------------------- |
| Discovery                | Capture product and technical context | Architecture Decision Records (ADRs), `hephaestus plan`                                                             | Shared understanding of the refactor mission       |
| Planning                 | Align scope, owners, and guard rails  | Rich-rendered execution plans, Diátaxis documentation, roadmap issues                                               | Clear backlog and review cadence                   |
| Development              | Implement changes with fast feedback  | `pre-commit`, Ruff, Black, PyUpgrade, Typer CLI workflows, type-driven toolbox, automated `hephaestus cleanup` hook | Consistent codebase with ergonomic CLI flows       |
| Testing                  | Safeguard behaviour and coverage      | Pytest with coverage gating, cleanup pre-flight for CI, characterization harness templates                          | Confident refactors with measurable coverage       |
| Security & Quality Gates | Catch regressions early               | Mypy, Pip Audit, QA profiles, coverage thresholds, repo cleanup sweeps                                              | Automated quality floor with actionable reports    |
| Release                  | Publish and document change           | Automated Release Tagging workflow, semantic version policy, deep-clean stage                                       | Repeatable, traceable releases                     |
| Deployment               | Package and ship artefacts            | `uv` environments, pip-installable package, cleanup script                                                          | Predictable install and clean substrate            |
| Operations               | Observe, upgrade, and respond         | TurboRepo Release Monitor, Dependabot, Ops README                                                                   | Proactive dependency hygiene and response triggers |
| Feedback                 | Bake learnings back in                | Issue templates, ADR rollups, docs updates                                                                          | Continuous improvement loop                        |

## Stage Details

### 1. Discovery

- **ADRs**: Capture the why behind large decisions using the `docs/adr` directory (start with
  `adr-template.md`). The template keeps reviews light-weight while providing auditability.
- **Toolkit Plan Command**: `uv run hephaestus plan` produces vibrant terminals that help workshop
  the phases, highlight blocked work, and onboard new collaborators quickly.

### 2. Planning

- **Diátaxis-Aligned Docs**: The refactoring playbooks and the new lifecycle guide document both
  tutorials and explanations so teams can move from theory to execution rapidly.
- **Backlog Hygiene**: Use GitHub Project boards or Issues linked from plan steps. The optional
  `ops/roadmap.md` template (see below) can be copied per initiative.

### 3. Development

- **Pre-Commit**: Install the hooks one time with `uv run pre-commit install` to ensure Ruff, Black,
  PyUpgrade, Mypy, and Pip Audit run before every commit.
- **Cleanup Guard Rail**: The pre-commit configuration now runs `uv run hephaestus cleanup` on commit
  and push stages so macOS metadata never lands in history.
- **Type-Driven Helpers**: The toolbox exposes typed dataclasses (`Hotspot`, `CoverageGap`,
  `RefactorOpportunity`) so IDEs and editors surface completions automatically.
- **CLI Ergonomics**: New README coverage showcases how to drive hotspot triage, QA profile
  inspection, and execution plans straight from the command line.

### 4. Testing

- **Coverage Gates**: Pytest defaults now emit XML + terminal reports and fail when coverage drops
  below 85%.
- **CI Pre-Flight Cleanup**: The main CI workflow executes `uv run hephaestus cleanup` immediately
  after syncing dependencies so linting, typing, and tests always start from a pristine tree.
- **Characterisation Harnesses**: The toolkit scripts provide scaffolding for protecting behaviour
  during refactors—extend them with targeted regression tests as you modernise modules.
- **Matrix CI**: Tests execute across Python 3.12 and 3.13 ensuring future compatibility.

### 5. Security & Quality Gates

- **Static Typing**: `uv run mypy` guards the toolbox and CLI for contract drift; the CI workflow
  fails fast on new typing issues.
- **Security Audits**: Pip Audit runs on every mainline CI sweep (and locally via pre-commit) so
  vulnerable dependencies never linger.
- **Coverage + QA Profiles**: Tight coupling between toolkit settings and QA profiles keeps rollouts
  honest about the guard rails they promise.

### 6. Release

- **Automated Release Tagging**: Pushes to `main` automatically tag new versions based on
  `pyproject.toml` and publish GitHub Releases with changelog-ready artefacts.
- **Wheelhouse Distribution**: The `Build Wheelhouse` workflow assembles wheels and sdists via
  `uv build`, stores them as a downloadable GitHub Actions artefact, and attaches the bundle to each
  GitHub Release so consumers can install without a PyPI publish.
- **Wheelhouse Consumption**: Run `uv run hephaestus release install --tag <tag>` from any project to
  download the matching release archive, install its wheels into the active environment, and keep the
  toolkit versions aligned even before PyPI publication.
- **Deep-Clean Stage**: The release workflow installs `uv` and performs `uv run hephaestus cleanup
--deep-clean` before version detection so archives and tags never include workspace cruft.
- **Semantic Version Discipline**: Bump the `version` field using semver semantics—patch for safety
  fixes, minor for new features, major for breaking changes.
- **Pre-Release Checklist**: Run through `docs/pre-release-checklist.md` before pushing the final
  changes to confirm automation parity, forcing a local cleanup sweep and re-running guard rails.

### 7. Deployment

- **`uv` Environments**: A locked dependency graph (`uv.lock`) plus the CI sync step make runtime
  parity trivial.
- **Packaging**: The project remains pip-installable (`pip install hephaestus`) and ready for PyPI
  or internal indices; consider enabling the publishing workflow in `.github/workflows` when the
  first release candidate is ready.
- **Cleanup Script**: `./cleanup-macos-cruft.sh --deep-clean` keeps artefacts out of release
  archives and ensures reproducible builds, and the automation hooks ensure those commands run
  automatically during CI, releases, and pre-commit flows.

### 8. Operations

- **TurboRepo Monitor**: Nightly checks compare the pinned version with upstream and open issues if
  an upgrade is available.
- **Dependabot**: Weekly dependency nudges cover both Python packages and GitHub Actions.
- **Operational Docs**: `ops/README.md` documents the release observation flow. Extend with runbooks
  for environment-specific steps as deployment needs grow.

### 9. Feedback & Continuous Improvement

- **Issue Templates & Labels**: Combine ADR updates with labelled issues (`dx`, `ux`, `quality`) to
  track improvement work explicitly.
- **Metrics Dashboards**: Export coverage artefacts and hotspot scans to dashboards for trend
  analysis and to celebrate improvements with the wider org.

## Quickstart Commands

```bash
uv sync --extra dev --extra qa
uv run pre-commit install
uv run pre-commit run --all-files
uv run ruff check .
uv run mypy src tests
uv run pytest
uv run pip-audit --strict
```

## Next Potential Enhancements

1. **Docs Site**: Stand up an MkDocs Material site that consumes the Diátaxis-ready documentation for
   richer navigation and search.
2. **CodeQL Security Scans**: Add GitHub's CodeQL workflow to deepen static analysis beyond pip-audit.
3. **Runtime Telemetry**: Instrument CLI commands with optional OpenTelemetry spans to capture usage
   patterns while respecting privacy.
4. **Publish to PyPI**: Wire the release workflow to publish tagged versions directly to PyPI and
   generate release notes using `git-cliff`.

Staying evergreen is a journey. This playbook keeps the loop tight so engineering teams can refactor
confidently, deliver delightful experiences, and maintain uncompromising quality.
