"""Hephaestus developer toolkit package."""

from importlib import import_module, metadata

__all__ = [
    "__version__",
    "events",
    "logging",
    "planning",
    "release",
    "resource_forks",
    "toolbox",
]


def _detect_version() -> str:
    try:
        return metadata.version("hephaestus")
    except metadata.PackageNotFoundError:  # pragma: no cover
        return "0.1.0"


__version__ = _detect_version()


# Re-export frequently used submodules for compatibility with existing imports.
events = import_module(".events", __name__)
logging = import_module(".logging", __name__)
planning = import_module(".planning", __name__)
release = import_module(".release", __name__)
resource_forks = import_module(".resource_forks", __name__)
toolbox = import_module(".toolbox", __name__)
