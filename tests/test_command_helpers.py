"""Tests for command helper utilities."""

from __future__ import annotations

from collections.abc import Callable

import pytest

from hephaestus.command_helpers import build_pip_audit_command


def _resolver(mapping: dict[str, str | None]) -> Callable[[str], str | None]:
    def _inner(name: str) -> str | None:
        return mapping.get(name)

    return _inner


def test_build_pip_audit_command_direct(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr(
        "hephaestus.command_helpers.which",
        _resolver({"pip-audit": "/usr/bin/pip-audit"}),
    )

    command = build_pip_audit_command(prefer_uv_run=False)

    assert command[:2] == ["pip-audit", "--strict"]


def test_build_pip_audit_command_falls_back_to_uvx(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr(
        "hephaestus.command_helpers.which",
        _resolver({"uvx": "/usr/bin/uvx"}),
    )

    command = build_pip_audit_command(extra_args=["--foo"], prefer_uv_run=False)

    assert command[:2] == ["uvx", "pip-audit"]
    assert "--foo" in command


def test_build_pip_audit_command_uses_uv_x(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr(
        "hephaestus.command_helpers.which",
        _resolver({"uv": "/usr/bin/uv"}),
    )

    command = build_pip_audit_command(ignore_vulns=["GHSA-1234"], prefer_uv_run=False)

    assert command[:3] == ["uv", "x", "pip-audit"]
    assert command[-2:] == ["--ignore-vuln", "GHSA-1234"]
