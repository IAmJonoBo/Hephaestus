"""Helpers for constructing external command invocations."""

from __future__ import annotations

from collections.abc import Iterable, Sequence
from shutil import which

DEFAULT_PIP_AUDIT_ARGS = ("--strict",)


def build_pip_audit_command(
    extra_args: Sequence[str] | None = None,
    ignore_vulns: Iterable[str] | None = None,
    *,
    prefer_uv_run: bool = False,
) -> list[str]:
    """Construct the command used to invoke ``pip-audit``.

    If ``pip-audit`` is not available on ``PATH`` the helper attempts to fall back
    to ``uvx`` (or ``uv x``) so environments without a pre-installed tool can still
    run the audit. When ``prefer_uv_run`` is set we assume the surrounding tooling
    is already using ``uv run`` (e.g. guard rails) and skip resolution checks to
    keep behaviour identical to the existing pipeline.
    """

    resolved_args = list(extra_args or DEFAULT_PIP_AUDIT_ARGS)
    resolved_ignores = list(ignore_vulns or [])

    if prefer_uv_run:
        command = ["uv", "run", "pip-audit"]
    else:
        command = _resolve_pip_audit_executable()

    full_command = command + resolved_args
    for vuln in resolved_ignores:
        full_command.extend(["--ignore-vuln", vuln])

    return full_command


def _resolve_pip_audit_executable() -> list[str]:
    """Resolve the best available way to invoke ``pip-audit``."""

    if which("pip-audit"):
        return ["pip-audit"]

    if which("uvx"):
        return ["uvx", "pip-audit"]

    if which("uv"):
        return ["uv", "x", "pip-audit"]

    # Fall back to the raw command so callers still receive a helpful
    # ``FileNotFoundError`` when nothing is available.
    return ["pip-audit"]
