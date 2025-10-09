---
title: "Welcome to the Hephaestus Toolkit Docs"
description: "Hephaestus streamlines refactoring and quality operations. These docs collect everything you need to plan rollouts, run the CLI, and keep automation evergreen...."
---

Hephaestus streamlines refactoring and quality operations. These docs collect everything you need to
plan rollouts, run the CLI, and keep automation evergreen.

## Quick Links

- Tutorials: [Getting Started](/tutorials/getting-started/)
- How-to guides: [Install from a Wheelhouse](/how-to/install-wheelhouse/), [Configure Your Editor](/how-to/editor-setup/)
- Explanation: [Architecture Overview](/explanation/architecture/), [Lifecycle Playbook](/lifecycle/)
- Reference: [CLI Reference](/reference/cli/), [CLI Autocompletion](/cli-completions/), [Pre-Release Checklist](/pre-release-checklist/)
- Appendix: [ADR Template](/adr/0000-template/)
- Toolkit Playbooks: [Refactoring Toolkit docs](/hephaestus-toolkit/refactoring/docs/README/)

## Getting Started

1. Install dependencies with `uv sync --extra dev --extra qa`.
2. Explore the CLI with `uv run hephaestus --help` and the workflows in `README.md`.
3. Follow the lifecycle playbook to move from discovery to delivery without surprises.
4. To bootstrap the toolkit anywhere—even without PyPI access—run `uv run hephaestus release install`
   to fetch and install the latest wheelhouse archive.

## Contributing

See [CONTRIBUTING.md](/CONTRIBUTING/) for branching, testing, and release guidance. The docs
are built with MkDocs Material—use `uv run mkdocs serve` for a live preview or `uv run mkdocs build`
to render static assets.
