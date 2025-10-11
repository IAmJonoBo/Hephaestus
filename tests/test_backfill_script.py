import importlib.abc
import importlib.util
import sys
from pathlib import Path
from types import ModuleType

import pytest

from hephaestus.backfill import BackfillRunSummary

SCRIPT_PATH = Path(__file__).resolve().parents[1] / "scripts" / "backfill_sigstore_bundles.py"


def load_backfill_script() -> ModuleType:
    spec = importlib.util.spec_from_file_location("backfill_script", SCRIPT_PATH)
    if spec is None or spec.loader is None:  # pragma: no cover - defensive
        raise RuntimeError("Unable to load backfill script")
    module = importlib.util.module_from_spec(spec)
    loader = spec.loader
    loader.exec_module(module)
    return module


def test_script_main_invokes_shared_runner(monkeypatch: pytest.MonkeyPatch, tmp_path: Path) -> None:
    """The standalone script should delegate to the shared `run_backfill` callable."""

    module = load_backfill_script()

    summary = BackfillRunSummary(
        successes=[{"version": "v0.2.3", "status": "backfilled"}],
        failures=[],
        inventory_path=tmp_path / "inventory.json",
        versions=["v0.2.3"],
        dry_run=True,
    )

    captured_kwargs: dict[str, object] = {}

    def fake_run_backfill(**kwargs: object) -> BackfillRunSummary:
        captured_kwargs.update(kwargs)
        return summary

    monkeypatch.setenv("GITHUB_TOKEN", "token-123")
    monkeypatch.setenv("SIGSTORE_INVENTORY_PATH", str(tmp_path / "inventory.json"))
    monkeypatch.setattr(module, "run_backfill", fake_run_backfill)
    monkeypatch.setattr(
        sys, "argv", ["backfill_sigstore_bundles.py", "--version", "v0.2.3", "--dry-run"]
    )

    exit_code = module.main()

    assert exit_code == 0
    assert captured_kwargs["token"] == "token-123"
    assert captured_kwargs["version"] == "v0.2.3"
    assert captured_kwargs["dry_run"] is True


def test_script_main_propagates_failures(monkeypatch: pytest.MonkeyPatch, tmp_path: Path) -> None:
    """The script should exit non-zero when the run summary contains failures."""

    module = load_backfill_script()

    summary = BackfillRunSummary(
        successes=[],
        failures=[{"version": "v0.1.0", "error": "boom"}],
        inventory_path=tmp_path / "inventory.json",
        versions=["v0.1.0"],
        dry_run=False,
    )

    def fake_run_backfill(**_: object) -> BackfillRunSummary:
        return summary

    monkeypatch.setenv("GITHUB_TOKEN", "token-123")
    monkeypatch.setattr(module, "run_backfill", fake_run_backfill)
    monkeypatch.setattr(sys, "argv", ["backfill_sigstore_bundles.py"])

    exit_code = module.main()

    assert exit_code == 1
