#!/usr/bin/env python3
"""CLI helper to emit hotspot analytics using the Hephaestus toolbox."""

from __future__ import annotations

import sys
from collections.abc import Callable, Iterable
from importlib import import_module
from pathlib import Path
from typing import TYPE_CHECKING

if TYPE_CHECKING:  # pragma: no cover - typing only
    from hephaestus.toolbox import Hotspot, ToolkitSettings

Analyzer = Callable[["ToolkitSettings"], Iterable["Hotspot"]]
Loader = Callable[[], "ToolkitSettings"]


def main() -> None:
    analyze_hotspots, load_settings = _resolve_toolbox()
    settings = load_settings()
    for hotspot in analyze_hotspots(settings):
        print(f"{hotspot.path}: churn={hotspot.churn}, coverage={hotspot.coverage:.0%}")


def _resolve_toolbox() -> tuple[Analyzer, Loader]:
    try:
        module = import_module("hephaestus.toolbox")
        return module.analyze_hotspots, module.load_settings
    except ModuleNotFoundError:  # pragma: no cover - fallback for local execution
        project_root = Path(__file__).resolve().parents[3]
        source_root = project_root / "src"
        if str(source_root) not in sys.path:
            sys.path.insert(0, str(source_root))
        module = import_module("hephaestus.toolbox")
        return module.analyze_hotspots, module.load_settings


if __name__ == "__main__":
    main()
