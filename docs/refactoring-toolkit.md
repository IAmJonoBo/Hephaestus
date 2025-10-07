# Refactoring Toolkit

The refactoring toolkit ships alongside the CLI to streamline codebase upgrades. Dive into the
resources within `hephaestus-toolkit/refactoring/` for configuration, scripts, and playbooks.

## Directory Map

- `config/` — Baseline configuration (`refactor.config.yaml`) that you can extend for your repo.
- `docs/` — Playbooks and implementation notes; start with `README.md` and `PLAYBOOK.md`.
- `scripts/` — Automation helpers for hotspot scans, codemods, and verification harnesses.
- `ci/` — Workflow fragments and presets for integrating the toolkit into existing pipelines.

## Next Steps

- Read the [Refactoring Toolkit README](https://github.com/IAmJonoBo/Hephaestus/tree/main/hephaestus-toolkit/refactoring/docs/README.md)
  for a conceptual overview.
- Tailor `config/refactor.config.yaml` to your project layout.
- Use the CLI commands under `tools refactor` to rank hotspots and identify opportunity clusters.
- When you're ready to consume wheelhouse artefacts, rely on `hephaestus release install` or the
  helpers in `hephaestus.release` to download and install the latest toolkit bundles from GitHub
  releases without needing PyPI access.
