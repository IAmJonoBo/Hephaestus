---
title: "Editor Setup"
description: "Use these quick steps to align your editor with the tooling that ships in Hephaestus. The configuration keeps formatting, linting, and typing feedback..."
---

Use these quick steps to align your editor with the tooling that ships in Hephaestus. The
configuration keeps formatting, linting, and typing feedback consistent with CI so contributors see
issues locally before they reach a pull request.

## Universal Settings

Hephaestus includes a project-wide `.editorconfig`. Most modern editors respect it automatically.
If yours does not, install an EditorConfig plugin so indentation and whitespace behaviour match the
repository defaults.

Key defaults:

- UTF-8 encoding and LF line endings
- Four-space indentation for Python
- Two-space indentation for YAML, JSON, Markdown, shell scripts, and web assets
- Trailing whitespace trimmed on save and final newlines ensured

## Visual Studio Code

1. Install the recommended extensions (VS Code prompts automatically when opening the workspace).
   - Python (`ms-python.python`)
   - Black Formatter (`ms-python.black-formatter`)
   - Ruff (`charliermarsh.ruff`)
   - Ruff Format (`charliermarsh.ruff-format`)
   - Pylance (`ms-python.vscode-pylance`)
   - UV (`astral-sh.uv`)
2. Reload VS Code so the extensions activate, then run `uv sync --extra dev --extra qa` to install
   tool dependencies.
3. Enable the "Format on Save" option or add the following snippet to your user settings:

   ```json
   {
     "editor.formatOnSave": true,
     "editor.codeActionsOnSave": {
       "source.fixAll.ruff": "explicit"
     }
   }
   ```

4. Install pre-commit hooks with `uv run pre-commit install` to keep linting and typing feedback in
   sync with CI.

## PyCharm / IntelliJ IDEA

- Install the **EditorConfig** plugin (bundled by default) and ensure "Use tab character" is
  disabled for Python projects.
- Configure Black as the formatter and Ruff as an external tool or via the Ruff plugin to mirror the
  command line experience.
- Point the interpreter at the UV-managed virtual environment (`.venv`) so type checking and pytest
  discovery use the same dependencies as CI.

## Neovim

- Install `editorconfig.nvim` (or equivalent) to honour the shared configuration.
- Use `null-ls` or `conform.nvim` to wire Black and Ruff formatters, and configure the `mypy` linter
  through `nvim-lint` or `ALE` for inline typing diagnostics.
- Consider the `astral-sh/uv.nvim` plugin to manage environments with UV commands directly from
  Neovim.

## Troubleshooting

- If Ruff or Black appear to conflict, run `uv run pre-commit run ruff-format --all-files` to reset
  the workspace.
- If your editor cannot locate the virtual environment, create one with `uv sync --extra dev` and
  reselect it in your IDE settings.
- For CI parity, always finish a feature branch by running the quickstart commands listed in
  `README.md` or the pre-release checklist in `docs/pre-release-checklist.md`.
- Need the tooling without PyPI access? Run `uv run hephaestus release install` to download and
  install the latest wheelhouse from GitHub Releases directly into your current environment.
