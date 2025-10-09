---
title: "Refactoring Toolkit Map"
description: "Hephaestus ships advisory tooling under the hephaestus-toolkit/refactoring/ directory. Use this reference to understand the major components when wiring the..."
---
Hephaestus ships advisory tooling under the `hephaestus-toolkit/refactoring/` directory. Use this
reference to understand the major components when wiring the toolkit into another repository or CI
pipeline.

## Directory Walkthrough

| Path                          | Purpose                                                                            |
| ----------------------------- | ---------------------------------------------------------------------------------- |
| `config/refactor.config.yaml` | Baseline configuration toggling hotspot scanning, codemods, characterization, etc. |
| `docs/PLAN.md`                | Step-by-step rollout plan for introducing the toolkit safely.                      |
| `docs/PLAYBOOK.md`            | Operational playbook capturing intent, actors, and implementation guidance.        |
| `docs/README.md`              | Overview of the toolkit assets shipped in this folder.                             |
| `ci/workflow.partial.yml`     | GitHub Actions fragment for embedding toolkit checks into existing pipelines.      |
| `scripts/scan_hotspots.py`    | Entry point for churn and hotspot analysis.                                        |
| `scripts/` (other modules)    | Helpers for codemods, verification, and advisory reporting.                        |

## Usage Patterns

- Start with `docs/PLAN.md` to scope an adoption rollout, then tailor `refactor.config.yaml` to your
  repository structure and risk thresholds.
- Drop `ci/workflow.partial.yml` into your CI pipeline or import sections of it to run hotspot scans
  and characterization tests as advisory checks during pull requests.
- Extend the scripts in `scripts/` to codify additional refactoring heuristics or to integrate with
  internal tooling.

## Related Documentation

- [`docs/explanation/architecture.md`](/explanation/architecture/) for a conceptual overview of
  how the toolkit aligns with the core package.
- [`docs/how-to/install-wheelhouse.md`](/how-to/install-wheelhouse/) for instructions on
  distributing the packaged tooling.
- [`docs/tutorials/getting-started.md`](/tutorials/getting-started/) for the first-run workflow.
