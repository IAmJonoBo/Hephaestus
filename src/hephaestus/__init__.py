"""Hephaestus developer toolkit package."""

from importlib import metadata

__all__ = ["__version__"]


def _detect_version() -> str:
    try:
        return metadata.version("hephaestus")
    except metadata.PackageNotFoundError:  # pragma: no cover
        return "0.1.0"


__version__ = _detect_version()
