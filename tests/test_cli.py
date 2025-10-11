"""CLI smoke tests for the Hephaestus toolkit."""

from __future__ import annotations

import sys
from importlib import import_module
from pathlib import Path
from types import ModuleType
from typing import Any

import pytest
from typer.testing import CliRunner

from hephaestus.backfill import BackfillRunSummary

release_cli = import_module("hephaestus.cli.release")
cleanup_cli = import_module("hephaestus.cli.cleanup")

ROOT = Path(__file__).resolve().parents[1]
SRC = ROOT / "src"
if str(SRC) not in sys.path:
    sys.path.insert(0, str(SRC))

runner = CliRunner()


def _load_modules() -> tuple[ModuleType, ModuleType]:
    toolkit = import_module("hephaestus")
    cli = import_module("hephaestus.cli")
    return toolkit, cli


def test_version_command_displays_version() -> None:
    toolkit, cli = _load_modules()
    result = runner.invoke(cli.app, ["version"])
    assert result.exit_code == 0
    assert toolkit.__version__ in result.stdout


def test_hotspots_command_uses_default_config() -> None:
    _, cli = _load_modules()
    result = runner.invoke(cli.app, ["tools", "refactor", "hotspots", "--limit", "2"])
    assert result.exit_code == 0
    assert "Refactor Hotspots" in result.stdout


def test_qa_profile_command_lists_profile_data() -> None:
    _, cli = _load_modules()
    result = runner.invoke(cli.app, ["tools", "qa", "profile", "quick"])
    assert result.exit_code == 0
    assert "QA Profile: quick" in result.stdout


def test_plan_command_renders_execution_plan() -> None:
    _, cli = _load_modules()
    result = runner.invoke(cli.app, ["plan"])
    assert result.exit_code == 0
    assert "Execution Plan" in result.stdout
    assert "Gather Evidence" in result.stdout


def test_release_install_forwards_sigstore_options(
    monkeypatch: pytest.MonkeyPatch, tmp_path: Path
) -> None:
    _, cli = _load_modules()

    download_kwargs: dict[str, Any] = {}
    archive_path = tmp_path / "hephaestus-1.2.3-wheelhouse.tar.gz"
    archive_path.write_bytes(b"wheelhouse")
    bundle_path = tmp_path / "hephaestus-1.2.3-wheelhouse.sigstore"
    bundle_path.write_text("sigstore", encoding="utf-8")

    def fake_download_wheelhouse(
        *,
        repository: str,
        destination_dir: Path,
        tag: str | None,
        asset_pattern: str,
        manifest_pattern: str | None,
        sigstore_bundle_pattern: str | None,
        token: str | None,
        overwrite: bool,
        extract: bool,
        allow_unsigned: bool,
        require_sigstore: bool,
        **kwargs: Any,
    ) -> Any:
        download_kwargs.update(
            {
                "repository": repository,
                "destination_dir": destination_dir,
                "tag": tag,
                "asset_pattern": asset_pattern,
                "manifest_pattern": manifest_pattern,
                "sigstore_bundle_pattern": sigstore_bundle_pattern,
                "allow_unsigned": allow_unsigned,
                "require_sigstore": require_sigstore,
                "extract": extract,
                "token": token,
                "overwrite": overwrite,
            }
        )
        # Add any extra keyword arguments to download_kwargs for assertion
        download_kwargs.update(kwargs)

        asset = release_cli.release_module.ReleaseAsset(
            name=archive_path.name,
            download_url="https://example.invalid/archive.tar.gz",
            size=archive_path.stat().st_size,
        )
        return release_cli.release_module.ReleaseDownload(
            asset=asset,
            archive_path=archive_path,
            extracted_path=None,
            manifest_path=None,
            sigstore_path=bundle_path,
        )

    monkeypatch.setattr(
        release_cli.release_module,
        "download_wheelhouse",
        fake_download_wheelhouse,
    )

    install_calls: list[tuple[tuple[Any, ...], dict[str, Any]]] = []

    def fake_install_from_archive(*args: Any, **kwargs: Any) -> None:
        install_calls.append((args, kwargs))

    monkeypatch.setattr(
        release_cli.release_module,
        "install_from_archive",
        fake_install_from_archive,
    )

    identities = [
        "github-actions@github.com",
        "https://example.invalid/repos/IAmJonoBo/Hephaestus/*",
    ]

    result = runner.invoke(
        cli.app,
        [
            "release",
            "install",
            "--repository",
            "IAmJonoBo/Hephaestus",
            "--destination",
            str(tmp_path),
            "--sigstore-pattern",
            "*wheelhouse*.sigstore",
            "--require-sigstore",
            "--sigstore-identity",
            identities[0],
            "--sigstore-identity",
            identities[1],
        ],
    )

    assert result.exit_code == 0
    assert "Installed wheelhouse" in result.stdout

    assert download_kwargs["repository"] == "IAmJonoBo/Hephaestus"
    assert download_kwargs["destination_dir"].resolve() == tmp_path.resolve()
    assert download_kwargs["sigstore_bundle_pattern"] == "*wheelhouse*.sigstore"
    assert download_kwargs["require_sigstore"] is True
    assert download_kwargs["allow_unsigned"] is False
    assert download_kwargs["sigstore_identities"] == identities
    assert download_kwargs["extract"] is False
    assert download_kwargs["tag"] is None
    assert (
        download_kwargs["manifest_pattern"] == release_cli.release_module.DEFAULT_MANIFEST_PATTERN
    )
    assert download_kwargs["timeout"] == release_cli.release_module.DEFAULT_TIMEOUT
    assert download_kwargs["max_retries"] == release_cli.release_module.DEFAULT_MAX_RETRIES

    assert install_calls, "Expected install_from_archive to be invoked"
    install_args, install_kwargs = install_calls[0]
    assert install_args[0] == archive_path
    assert install_kwargs["upgrade"] is True
    assert install_kwargs["cleanup"] is False


def test_release_install_can_remove_archive(
    monkeypatch: pytest.MonkeyPatch, tmp_path: Path
) -> None:
    """Ensure --remove-archive deletes the downloaded artefact."""

    _, cli = _load_modules()

    archive_path = tmp_path / "hephaestus-9.9.9-wheelhouse.tar.gz"
    archive_path.write_bytes(b"wheelhouse")

    def fake_download_wheelhouse(**_kwargs: Any) -> Any:
        asset = release_cli.release_module.ReleaseAsset(
            name=archive_path.name,
            download_url="https://example.invalid/archive.tar.gz",
            size=archive_path.stat().st_size,
        )
        return release_cli.release_module.ReleaseDownload(
            asset=asset,
            archive_path=archive_path,
            extracted_path=None,
            manifest_path=None,
            sigstore_path=None,
        )

    monkeypatch.setattr(
        release_cli.release_module,
        "download_wheelhouse",
        fake_download_wheelhouse,
    )

    monkeypatch.setattr(
        release_cli.release_module,
        "install_from_archive",
        lambda *_args, **_kwargs: None,
    )

    result = runner.invoke(
        cli.app,
        [
            "release",
            "install",
            "--destination",
            str(tmp_path),
            "--remove-archive",
        ],
    )

    assert result.exit_code == 0
    assert not archive_path.exists()


def test_release_install_supports_test_pypi_source(monkeypatch: pytest.MonkeyPatch) -> None:
    """Selecting the test-pypi source should call the PyPI installer helper."""

    _, cli = _load_modules()

    def _fail_download(**_kwargs: Any) -> None:
        raise AssertionError("download_wheelhouse should not run for PyPI sources")

    monkeypatch.setattr(release_cli.release_module, "download_wheelhouse", _fail_download)

    captured: dict[str, Any] = {}

    def _fake_install_from_pypi(**kwargs: Any) -> None:
        captured.update(kwargs)

    monkeypatch.setattr(release_cli.release_module, "install_from_pypi", _fake_install_from_pypi)

    result = runner.invoke(
        cli.app,
        [
            "release",
            "install",
            "--source",
            "test-pypi",
            "--tag",
            "v0.3.0rc1",
            "--no-upgrade",
        ],
    )

    assert result.exit_code == 0
    assert captured["project"] == "hephaestus-toolkit"
    assert captured["version"] == "0.3.0rc1"
    assert captured["index_url"] == "https://test.pypi.org/simple/"
    assert captured["extra_index_url"] == "https://pypi.org/simple/"
    assert captured["upgrade"] is False


def test_release_install_help_succeeds() -> None:
    """Ensure release install help renders despite complex option wiring."""

    _, cli = _load_modules()

    result = runner.invoke(cli.app, ["release", "install", "--help"])

    assert result.exit_code == 0
    assert "Download the Hephaestus wheelhouse" in result.stdout
    # Check for sigstore-identity without ANSI codes by removing color codes
    import re

    clean_stdout = re.sub(r"\x1b\[[0-9;]*m", "", result.stdout)
    assert "--sigstore-identity" in clean_stdout


def test_release_backfill_invokes_shared_runner(
    monkeypatch: pytest.MonkeyPatch, tmp_path: Path
) -> None:
    """Backfill command should call the shared run_backfill helper."""

    _, cli = _load_modules()

    monkeypatch.setenv("GITHUB_TOKEN", "token-123")

    captured_kwargs: dict[str, object] = {}

    def fake_run_backfill(**kwargs: object) -> BackfillRunSummary:
        captured_kwargs.update(kwargs)
        return BackfillRunSummary(
            successes=[{"version": "v0.2.3", "status": "backfilled"}],
            failures=[],
            inventory_path=tmp_path / "inventory.json",
            versions=["v0.2.3"],
            dry_run=True,
        )

    monkeypatch.setattr("hephaestus.cli.release.run_backfill", fake_run_backfill)

    result = runner.invoke(
        cli.app,
        ["release", "backfill", "--version", "v0.2.3", "--dry-run"],
    )

    assert result.exit_code == 0
    assert "Backfill completed successfully" in result.stdout
    assert captured_kwargs["token"] == "token-123"
    assert captured_kwargs["version"] == "v0.2.3"
    assert captured_kwargs["dry_run"] is True


def test_release_backfill_handles_failures(monkeypatch: pytest.MonkeyPatch, tmp_path: Path) -> None:
    """Backfill command should surface failures returned by run_backfill."""

    _, cli = _load_modules()

    monkeypatch.setenv("GITHUB_TOKEN", "token-123")

    def fake_run_backfill(**_: object) -> BackfillRunSummary:
        return BackfillRunSummary(
            successes=[],
            failures=[{"version": "v0.2.3", "error": "boom"}],
            inventory_path=tmp_path / "inventory.json",
            versions=["v0.2.3"],
            dry_run=False,
        )

    monkeypatch.setattr("hephaestus.cli.release.run_backfill", fake_run_backfill)

    result = runner.invoke(cli.app, ["release", "backfill"])

    assert result.exit_code == 1
    assert "Backfill failed" in result.stdout


def test_release_backfill_requires_token(monkeypatch: pytest.MonkeyPatch) -> None:
    """The backfill command should still validate the GitHub token."""

    _, cli = _load_modules()

    monkeypatch.delenv("GITHUB_TOKEN", raising=False)

    result = runner.invoke(cli.app, ["release", "backfill"])

    assert result.exit_code == 1
    assert "GITHUB_TOKEN" in result.stdout


def test_qa_coverage_command_displays_gaps() -> None:
    _, cli = _load_modules()
    result = runner.invoke(cli.app, ["tools", "qa", "coverage"])
    assert result.exit_code == 0
    assert "Coverage Gaps" in result.stdout
    assert "Uncovered Lines" in result.stdout


def test_cleanup_command_removes_macos_cruft(tmp_path: Path) -> None:
    _, cli = _load_modules()
    workspace = tmp_path / "workspace"
    workspace.mkdir()
    (workspace / ".DS_Store").write_text("metadata", encoding="utf-8")

    result = runner.invoke(cli.app, ["cleanup", str(workspace)])

    assert result.exit_code == 0
    assert "Cleanup Preview" in result.stdout
    assert "Cleanup Summary" in result.stdout
    assert "Cleanup completed successfully" in result.stdout
    assert "Audit manifest" in result.stdout
    assert not (workspace / ".DS_Store").exists()

    audit_dir = workspace / ".hephaestus" / "audit"
    manifests = list(audit_dir.glob("cleanup-*.json"))
    assert manifests, "Expected cleanup manifest to be written"


def test_cleanup_command_handles_missing_path(tmp_path: Path) -> None:
    _, cli = _load_modules()
    missing = tmp_path / "missing"

    result = runner.invoke(cli.app, ["cleanup", str(missing)])

    assert result.exit_code == 0
    assert "No files would be removed by cleanup." in result.stdout
    assert "No files required removal" in result.stdout


def test_cleanup_command_reports_errors(monkeypatch: pytest.MonkeyPatch, tmp_path: Path) -> None:
    import hephaestus.cleanup as cleanup

    _, cli = _load_modules()
    workspace = tmp_path / "workspace"
    workspace.mkdir()

    def _broken_run_cleanup(*_args: Any, **_kwargs: Any) -> cleanup.CleanupResult:
        result = cleanup.CleanupResult()
        result.errors.append((workspace, "boom"))
        return result

    monkeypatch.setattr(cleanup, "run_cleanup", _broken_run_cleanup)

    result = runner.invoke(cli.app, ["cleanup", str(workspace)])

    assert result.exit_code == 1
    assert "Cleanup Errors" in result.stdout


def test_cleanup_dry_run_flag_skips_deletion(tmp_path: Path) -> None:
    _, cli = _load_modules()
    workspace = tmp_path / "workspace"
    workspace.mkdir()
    target = workspace / ".DS_Store"
    target.write_text("metadata", encoding="utf-8")

    result = runner.invoke(cli.app, ["cleanup", str(workspace), "--dry-run"])

    assert result.exit_code == 0
    assert "Dry-run complete; no changes were made." in result.stdout
    assert target.exists()


def test_cleanup_requires_confirmation_for_outside_root(tmp_path: Path) -> None:
    _, cli = _load_modules()
    workspace = tmp_path / "workspace"
    workspace.mkdir()
    target = workspace / ".DS_Store"
    target.write_text("metadata", encoding="utf-8")
    outside = tmp_path / "outside"
    outside.mkdir()

    result = runner.invoke(
        cli.app,
        ["cleanup", str(workspace), "--extra-path", str(outside)],
        input="no\n",
    )

    assert result.exit_code == 0
    assert "Confirmation Required" in result.stdout
    assert "Cleanup aborted before removing any files." in result.stdout
    assert target.exists()
    assert outside.exists()


def test_cleanup_accepts_max_depth_parameter(tmp_path: Path) -> None:
    """Test that cleanup command accepts --max-depth parameter."""
    _, cli = _load_modules()
    workspace = tmp_path / "workspace"
    workspace.mkdir()
    (workspace / ".DS_Store").write_text("metadata", encoding="utf-8")

    result = runner.invoke(cli.app, ["cleanup", str(workspace), "--max-depth", "5", "--dry-run"])

    assert result.exit_code == 0
    assert "Dry-run complete" in result.stdout


def test_guard_rails_runs_expected_commands(monkeypatch: pytest.MonkeyPatch) -> None:
    _, cli = _load_modules()

    cleanup_calls: list[tuple[tuple[Any, ...], dict[str, Any]]] = []

    def _fake_cleanup(*args: Any, **kwargs: Any) -> None:
        cleanup_calls.append((args, kwargs))

    monkeypatch.setattr(cleanup_cli, "cleanup", _fake_cleanup)

    executed: list[list[str]] = []

    def _fake_run(command: list[str], *, check: bool, timeout: int | None = None) -> None:
        assert check is True
        executed.append(command)

    # Patch subprocess module globally since it's imported locally in the function
    import subprocess

    monkeypatch.setattr(subprocess, "run", _fake_run)

    result = runner.invoke(cli.app, ["guard-rails"])

    assert result.exit_code == 0
    assert cleanup_calls
    assert cleanup_calls[0][1]["deep_clean"] is True
    assert executed == [
        ["uv", "run", "ruff", "check", "."],
        ["uv", "run", "ruff", "check", "--select", "I", "--fix", "."],
        ["uv", "run", "ruff", "format", "."],
        [
            "uv",
            "run",
            "yamllint",
            "-c",
            ".yamllint",
            ".github/",
            ".pre-commit-config.yaml",
            "hephaestus-toolkit/",
        ],
        ["bash", "scripts/run_actionlint.sh"],
        ["uv", "run", "mypy", "src", "tests"],
        ["uv", "run", "pytest"],
        ["uv", "run", "pip-audit", "--strict", "--ignore-vuln", "GHSA-4xh5-x5gv-qwph"],
    ]
    assert "Guard rails completed successfully" in result.stdout


def test_guard_rails_command_is_registered() -> None:
    _, cli = _load_modules()
    command_names = {command.name for command in cli.app.registered_commands}
    assert "guard-rails" in command_names


def test_guard_rails_can_skip_format(monkeypatch: pytest.MonkeyPatch) -> None:
    _, cli = _load_modules()
    monkeypatch.setattr(cleanup_cli, "cleanup", lambda *args, **kwargs: None)

    executed: list[list[str]] = []

    def _fake_run(command: list[str], *, check: bool, timeout: int | None = None) -> None:
        executed.append(command)

    # Patch subprocess module globally since it's imported locally in the function
    import subprocess

    monkeypatch.setattr(subprocess, "run", _fake_run)

    result = runner.invoke(cli.app, ["guard-rails", "--no-format"])

    assert result.exit_code == 0
    assert ["uv", "run", "ruff", "format", "."] not in executed
    assert ["bash", "scripts/run_actionlint.sh"] in executed


def test_guard_rails_plugin_mode_with_no_plugins(monkeypatch: pytest.MonkeyPatch) -> None:
    """Test guard-rails falls back to standard mode when no plugins loaded."""
    _, cli = _load_modules()
    monkeypatch.setattr(cleanup_cli, "cleanup", lambda *args, **kwargs: None)

    # Mock the plugin discovery to return empty registry
    from hephaestus.plugins import PluginRegistry

    def _fake_discover_plugins(*args: Any, **kwargs: Any) -> PluginRegistry:
        return PluginRegistry()  # Empty registry

    monkeypatch.setattr("hephaestus.plugins.discover_plugins", _fake_discover_plugins)

    executed: list[list[str]] = []

    def _fake_run(command: list[str], *, check: bool, timeout: int | None = None) -> None:
        executed.append(command)

    # Patch subprocess module globally since it's imported locally in the function
    import subprocess

    monkeypatch.setattr(subprocess, "run", _fake_run)

    result = runner.invoke(cli.app, ["guard-rails", "--use-plugins"])

    # Should fall back to standard pipeline when no plugins
    assert result.exit_code == 0
    assert "No plugins loaded" in result.stdout
    assert "Falling back to standard pipeline" in result.stdout
    # Standard pipeline should have run
    assert ["uv", "run", "ruff", "check", "."] in executed


def test_guard_rails_plugin_mode_flag_available() -> None:
    """Test guard-rails --use-plugins flag is available."""
    _, cli = _load_modules()
    result = runner.invoke(cli.app, ["guard-rails", "--help"])
    assert result.exit_code == 0
    assert "plugins" in result.stdout
    assert "ADR-002" in result.stdout or "experimental" in result.stdout


def test_wheelhouse_sanitize_removes_metadata(tmp_path: Path) -> None:
    _, cli = _load_modules()
    wheelhouse = tmp_path / "wheelhouse"
    wheelhouse.mkdir()
    target = wheelhouse / ".DS_Store"
    target.write_text("metadata", encoding="utf-8")

    result = runner.invoke(cli.app, ["wheelhouse", "sanitize", str(wheelhouse)])

    assert result.exit_code == 0
    assert "Removed resource fork artefact" in result.stdout
    assert not target.exists()


def test_wheelhouse_sanitize_dry_run(tmp_path: Path) -> None:
    _, cli = _load_modules()
    wheelhouse = tmp_path / "wheelhouse"
    wheelhouse.mkdir()
    target = wheelhouse / "._shadow"
    target.write_text("metadata", encoding="utf-8")

    result = runner.invoke(cli.app, ["wheelhouse", "sanitize", str(wheelhouse), "--dry-run"])

    assert result.exit_code == 0
    assert "Resource fork artefacts (dry run)" in result.stdout
    assert target.exists()


def test_wheelhouse_verify_no_findings(tmp_path: Path) -> None:
    _, cli = _load_modules()
    wheelhouse = tmp_path / "wheelhouse"
    wheelhouse.mkdir()

    result = runner.invoke(cli.app, ["wheelhouse", "verify", str(wheelhouse), "--no-strict"])

    assert result.exit_code == 0
    assert "No resource fork artefacts detected." in result.stdout


def test_wheelhouse_verify_strict_failure(tmp_path: Path) -> None:
    _, cli = _load_modules()
    wheelhouse = tmp_path / "wheelhouse"
    wheelhouse.mkdir()
    target = wheelhouse / ".DS_Store"
    target.write_text("metadata", encoding="utf-8")

    result = runner.invoke(cli.app, ["wheelhouse", "verify", str(wheelhouse)])

    assert result.exit_code == 1
    assert "Resource fork artefacts detected" in result.stdout
    assert target.exists()


def test_schema_command_exports_json() -> None:
    """Test that schema command exports command schemas as JSON."""
    _, cli = _load_modules()
    result = runner.invoke(cli.app, ["schema"])
    assert result.exit_code == 0
    assert "version" in result.stdout
    assert "commands" in result.stdout


def test_schema_command_with_output_file(tmp_path: Path) -> None:
    """Test schema command writing to file."""
    _, cli = _load_modules()
    output_file = tmp_path / "schemas.json"
    result = runner.invoke(cli.app, ["schema", "--output", str(output_file)])
    assert result.exit_code == 0
    assert output_file.exists()
    content = output_file.read_text()
    assert "version" in content
    assert "commands" in content


def test_invalid_log_format_raises_error() -> None:
    """Test that invalid log format is rejected."""
    _, cli = _load_modules()
    result = runner.invoke(cli.app, ["--log-format", "invalid", "version"])
    assert result.exit_code != 0
    # Error message is in the exception/stderr
    assert result.exception is not None


def test_invalid_log_level_raises_error() -> None:
    """Test that invalid log level is rejected."""
    _, cli = _load_modules()
    result = runner.invoke(cli.app, ["--log-level", "TRACE", "version"])
    assert result.exit_code != 0
    # Error message is in the exception/stderr
    assert result.exception is not None


def test_guard_rails_drift_mode_no_drift() -> None:
    """Test guard-rails --drift when no drift is detected."""
    _, cli = _load_modules()
    from hephaestus.drift import ToolVersion

    # Mock drift detection to return no drifted tools

    def mock_detect_drift(_path: Path | None = None) -> list[ToolVersion]:
        # Create actual ToolVersion instances
        return [ToolVersion(name="ruff", expected="0.14.0", actual="0.14.0")]

    import hephaestus.drift as drift_mod

    original_detect = drift_mod.detect_drift
    drift_mod.detect_drift = mock_detect_drift  # type: ignore[assignment]

    try:
        result = runner.invoke(cli.app, ["guard-rails", "--drift"])
        assert result.exit_code == 0
        assert "All tools are up to date" in result.stdout
    finally:
        drift_mod.detect_drift = original_detect


def test_guard_rails_drift_mode_auto_remediate(monkeypatch: pytest.MonkeyPatch) -> None:
    """guard-rails --drift --auto-remediate should execute remediation commands."""

    _, cli = _load_modules()
    from hephaestus.drift import ToolVersion

    def _fake_detect(_path: Path | None = None) -> list[ToolVersion]:
        return [ToolVersion(name="ruff", expected="0.14.0", actual="0.13.0")]

    class _Result:
        command = "uv sync"
        exit_code = 0
        stdout = "synced"
        stderr = ""

    def _fake_apply(commands: list[str]) -> list[Any]:
        assert commands
        return [_Result()]

    import hephaestus.drift as drift_mod

    monkeypatch.setattr(drift_mod, "detect_drift", _fake_detect)
    monkeypatch.setattr(drift_mod, "apply_remediation_commands", _fake_apply)

    result = runner.invoke(cli.app, ["guard-rails", "--drift", "--auto-remediate"])

    assert result.exit_code == 0
    assert "Applied remediation" in result.stdout


def test_refactor_opportunities_command() -> None:
    """Test refactor opportunities command."""
    _, cli = _load_modules()
    result = runner.invoke(cli.app, ["tools", "refactor", "opportunities"])
    assert result.exit_code == 0
    assert "Refactor Opportunities" in result.stdout


def test_refactor_rankings_command() -> None:
    """Test refactor rankings command."""
    _, cli = _load_modules()
    result = runner.invoke(cli.app, ["tools", "refactor", "rankings"])
    # Command may exit with 1 if no analytics sources are configured
    assert "Refactor Rankings" in result.stdout or "No analytics sources" in result.stdout
