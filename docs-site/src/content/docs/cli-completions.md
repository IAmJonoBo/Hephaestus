---
title: "CLI Autocompletion"
description: "Hephaestus is built with Typer (Click under the hood) and ships native shell completion scripts. The steps below install completions once per machine so..."
---

Hephaestus is built with Typer (Click under the hood) and ships native shell completion scripts. The
steps below install completions once per machine so subcommands and options appear automatically.

## Quick Install

```bash
uv run hephaestus --install-completion
```

Typer detects your current shell and prints the install location. Follow the on-screen guidance to
source the generated file (usually by appending a line to your shell profile).

## Manual Installation

If you prefer explicit control, generate the completion script and point your shell at it manually.
Replace `$SHELL` with `bash`, `zsh`, or `fish` as appropriate.

```bash
uv run hephaestus --show-completion $SHELL > ~/.config/hephaestus/completions.$SHELL
```

Add the following lines to your shell profile:

- **Bash** (`~/.bashrc` or `~/.bash_profile`):

  ```bash
  source ~/.config/hephaestus/completions.bash
  ```

- **Zsh** (`~/.zshrc`):

  ```bash
  autoload -U compinit && compinit
  source ~/.config/hephaestus/completions.zsh
  ```

- **Fish** (`~/.config/fish/config.fish`):

  ```fish
  source ~/.config/hephaestus/completions.fish
  ```

## Keeping Completions Fresh

Regenerate the scripts whenever the CLI gains new commands:

```bash
uv run hephaestus --show-completion $SHELL > ~/.config/hephaestus/completions.$SHELL
```

For contributors using the dev container, completions are pre-wired (see `.devcontainer` notes) so no
additional setup is required.
