# Welcome to the Hephaestus Toolkit Docs

Hephaestus streamlines refactoring and quality operations. These docs collect everything you need to
plan rollouts, run the CLI, and keep automation evergreen.

## Quick Links

- [Lifecycle Playbook](lifecycle.md)
- [Editor Setup](editor-setup.md)
- [CLI Autocompletion](cli-completions.md)
- [Pre-Release Checklist](pre-release-checklist.md)
- [Architecture Decision Records](adr/0000-template.md)
- [Toolkit Playbooks](../hephaestus-toolkit/refactoring/docs/README.md)

## Getting Started

1. Install dependencies with `uv sync --extra dev --extra qa`.
2. Explore the CLI with `uv run hephaestus --help` and the workflows in `README.md`.
3. Follow the lifecycle playbook to move from discovery to delivery without surprises.
4. To bootstrap the toolkit anywhere—even without PyPI access—run `uv run hephaestus release install`
   to fetch and install the latest wheelhouse archive.

## Contributing

See [CONTRIBUTING.md](../CONTRIBUTING.md) for branching, testing, and release guidance. The docs
are built with MkDocs Material—use `uv run docs-serve` for a live preview or `uv run docs-build` to
render static assets.
