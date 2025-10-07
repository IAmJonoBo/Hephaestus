# Tutorial: Getting Started with Hephaestus

This tutorial walks through the minimum steps required to install the toolkit, explore the CLI, and
ship your first refactoring workflow using the bundled wheelhouse distribution.

## 1. Prepare Your Environment

1. Install [uv](https://github.com/astral-sh/uv) if it is not already available.
2. Clone the repository or download a wheelhouse bundle:
   - Clone: `git clone https://github.com/IAmJonoBo/Hephaestus.git`
   - Wheelhouse: `uv run hephaestus release install --tag <latest-tag>`
3. Synchronise development dependencies:

   ```bash
   uv sync --extra dev --extra qa
   ```

## 2. Explore the CLI

List the top-level commands and review built-in help:

```bash
uv run hephaestus --help
```

Try a few high-signal subcommands:

- `uv run hephaestus tools refactor hotspots --limit 5`
- `uv run hephaestus tools qa profile quick`
- `uv run hephaestus plan`

## 3. Clean Up Your Workspace

Before you start editing, remove local cruft so rollouts stay reproducible.

```bash
uv run hephaestus cleanup --deep-clean
```

Add the pre-commit hooks to automate this in the future:

```bash
uv run pre-commit install
```

## 4. Run the Refactoring Toolkit

The toolkit ships advisory scripts you can customise for your repository.

```bash
uv run python hephaestus-toolkit/refactoring/scripts/scan_hotspots.py --limit 10
```

Review the generated report and copy any candidate issues into your backlog.

## 5. Validate Changes with QA Profiles

As you prototype a refactor, keep an eye on the QA profile thresholds:

```bash
uv run hephaestus tools qa coverage
uv run pytest
```

Aim to keep total coverage above 85% (the default gate baked into the CI configuration).

## 6. Package and Share

When you're ready to share the toolkit with another repository:

1. Run the release workflow locally to build a wheelhouse:

   ```bash
   uv build
   tar -czf hephaestus-wheelhouse.tar.gz dist/
   ```

2. Upload the archive as a GitHub Release asset or pass it directly to collaborators.
3. Consumers download and install via `hephaestus release install`.

## Next Steps

- Browse the [How-To guides](../how-to/) for task-oriented instructions.
- Review the [Architecture overview](../explanation/architecture.md) to understand the internal
  modules.
- Check the [CLI reference](../reference/cli.md) for option details.
