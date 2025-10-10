"""Plugin architecture for extensible quality gates (ADR-0002).

This module provides the foundation for a plugin-based quality gate system,
allowing custom quality checks to be added without modifying Hephaestus core.

Phase 1 (Complete): API specification and registry
Phase 2 (Complete): Built-in plugins
Phase 3 (This update): Plugin discovery and configuration loading
"""

from __future__ import annotations

import base64
import fnmatch
import hashlib
import importlib
import importlib.util
import json
import logging
import sys
import time
from abc import ABC, abstractmethod
from dataclasses import dataclass
from importlib import metadata
from pathlib import Path
from typing import Any

try:
    import tomli as tomllib  # type: ignore  # Python < 3.11
except ImportError:
    import tomllib

from packaging.specifiers import SpecifierSet
from packaging.version import InvalidVersion, Version

from hephaestus import telemetry

__all__ = [
    "PluginMetadata",
    "PluginResult",
    "QualityGatePlugin",
    "PluginRegistry",
    "execute_plugin",
    "PluginConfig",
    "discover_plugins",
    "load_plugin_config",
]

logger = logging.getLogger(__name__)


@dataclass
class PluginMetadata:
    """Metadata about a quality gate plugin."""

    name: str
    version: str
    description: str
    author: str
    category: str  # "linting", "testing", "security", "custom"
    requires: list[str]  # Dependencies
    order: int = 100  # Execution order (lower = earlier)


@dataclass
class PluginResult:
    """Result of running a plugin."""

    success: bool
    message: str
    details: dict[str, Any] | None = None
    exit_code: int = 0


@dataclass(frozen=True)
class MarketplaceDependency:
    """Dependency declared inside a marketplace manifest."""

    kind: str
    name: str
    version: str | None = None


@dataclass(frozen=True)
class MarketplaceManifest:
    """Parsed marketplace manifest information."""

    name: str
    version: str
    description: str
    author: str
    category: str
    entry_path: Path | None
    entry_module: str | None
    dependencies: tuple[MarketplaceDependency, ...]
    hephaestus_spec: str | None
    python_spec: str | None
    signature_bundle: Path | None
    manifest_path: Path

    def artifact_path(self) -> Path:
        """Return the filesystem path of the plugin artefact."""

        if self.entry_path is not None:
            return self.entry_path
        raise ValueError(
            f"Marketplace plugin {self.name!r} does not declare a filesystem entrypoint."
        )


@dataclass(frozen=True)
class TrustPolicy:
    """Trust policy controlling signature enforcement for marketplace plugins."""

    require_signature: bool
    default_identities: tuple[str, ...]
    per_plugin: dict[str, tuple[str, ...]]

    def identities_for(self, plugin_name: str) -> tuple[str, ...]:
        """Return the allowed identities for *plugin_name*."""

        return self.per_plugin.get(plugin_name, self.default_identities)


def _is_within_directory(path: Path, root: Path) -> bool:
    """Return ``True`` if *path* resides within *root*."""

    try:
        path.relative_to(root)
        return True
    except ValueError:
        return False


class QualityGatePlugin(ABC):
    """Base class for quality gate plugins.

    Example:
        class MyPlugin(QualityGatePlugin):
            @property
            def metadata(self) -> PluginMetadata:
                return PluginMetadata(
                    name="my-plugin",
                    version="1.0.0",
                    description="My custom quality check",
                    author="Me",
                    category="custom",
                    requires=[],
                    order=100,
                )

            def validate_config(self, config: dict) -> bool:
                return True

            def run(self, config: dict) -> PluginResult:
                return PluginResult(success=True, message="Check passed")
    """

    @property
    @abstractmethod
    def metadata(self) -> PluginMetadata:
        """Return plugin metadata."""
        pass

    @abstractmethod
    def validate_config(self, config: dict[str, Any]) -> bool:
        """Validate plugin configuration.

        Args:
            config: Configuration dictionary for this plugin

        Returns:
            True if configuration is valid

        Raises:
            ValueError: If configuration is invalid
        """
        pass

    @abstractmethod
    def run(self, config: dict[str, Any]) -> PluginResult:
        """Execute the quality gate check.

        Args:
            config: Configuration dictionary for this plugin

        Returns:
            Result of the quality gate execution
        """
        pass

    def setup(self) -> None:  # noqa: B027 - intentional hook with default no-op implementation
        """Optional: Setup before running.

        Override this method if your plugin needs to perform setup
        operations before executing the quality check.

        Default implementation does nothing.
        """

    def teardown(self) -> None:  # noqa: B027 - intentional hook with default no-op implementation
        """Optional: Cleanup after running.

        Override this method if your plugin needs to perform cleanup
        operations after executing the quality check.

        Default implementation does nothing.
        """


@dataclass
class PluginConfig:
    """Configuration for a plugin from config file."""

    name: str
    enabled: bool = True
    config: dict[str, Any] | None = None
    module: str | None = None  # For importable plugins
    path: str | None = None  # For file-based plugins
    version: str | None = None
    registry: str | None = None
    source: str = "external"


class PluginRegistry:
    """Registry for quality gate plugins with discovery support."""

    def __init__(self) -> None:
        self._plugins: dict[str, QualityGatePlugin] = {}

    def register(self, plugin: QualityGatePlugin) -> None:
        """Register a quality gate plugin.

        Args:
            plugin: Plugin instance to register

        Raises:
            ValueError: If plugin name is already registered
        """
        name = plugin.metadata.name
        if name in self._plugins:
            raise ValueError(f"Plugin {name!r} already registered")
        self._plugins[name] = plugin

    def get(self, name: str) -> QualityGatePlugin:
        """Retrieve a registered plugin by name.

        Args:
            name: Plugin name to look up

        Returns:
            The registered plugin

        Raises:
            KeyError: If plugin name is not registered
        """
        try:
            return self._plugins[name]
        except KeyError as exc:
            raise KeyError(f"Plugin {name!r} not registered") from exc

    def all_plugins(self) -> list[QualityGatePlugin]:
        """Return all registered plugins.

        Returns:
            List of all registered plugins, sorted by execution order
        """
        return sorted(self._plugins.values(), key=lambda p: p.metadata.order)

    def is_registered(self, name: str) -> bool:
        """Check if a plugin is registered.

        Args:
            name: Plugin name to check

        Returns:
            True if plugin is registered
        """
        return name in self._plugins

    def clear(self) -> None:
        """Clear all registered plugins.

        Useful for testing and reloading plugins.
        """
        self._plugins.clear()


def execute_plugin(
    plugin: QualityGatePlugin,
    config: dict[str, Any] | None = None,
) -> PluginResult:
    """Execute a plugin with telemetry instrumentation."""

    plugin_config = config or {}
    metadata = plugin.metadata
    base_attributes = {
        "plugin": metadata.name,
        "version": metadata.version,
        "category": metadata.category,
    }

    telemetry.record_counter("hephaestus.plugins.invocations", attributes=base_attributes)
    start_time = time.perf_counter()

    try:
        with telemetry.trace_operation(
            "plugins.execute",
            plugin=metadata.name,
            version=metadata.version,
            category=metadata.category,
        ):
            result = plugin.run(plugin_config)
    except Exception as exc:  # noqa: BLE001 - propagate plugin failures with telemetry
        telemetry.record_counter(
            "hephaestus.plugins.errors",
            attributes={**base_attributes, "error": exc.__class__.__name__},
        )
        telemetry.record_histogram(
            "hephaestus.plugins.duration",
            time.perf_counter() - start_time,
            attributes={**base_attributes, "status": "error"},
        )
        raise

    telemetry.record_counter(
        "hephaestus.plugins.success" if result.success else "hephaestus.plugins.failures",
        attributes=base_attributes,
    )
    telemetry.record_histogram(
        "hephaestus.plugins.duration",
        time.perf_counter() - start_time,
        attributes={**base_attributes, "status": "success" if result.success else "failure"},
    )

    return result


def load_plugin_config(config_path: Path | None = None) -> list[PluginConfig]:
    """Load plugin configuration from TOML file.

    Args:
        config_path: Path to plugin configuration file.
                    Defaults to .hephaestus/plugins.toml in current directory.

    Returns:
        List of plugin configurations

    Raises:
        FileNotFoundError: If config file doesn't exist
        ValueError: If config file is invalid
    """
    if config_path is None:
        config_path = Path.cwd() / ".hephaestus" / "plugins.toml"

    if not config_path.exists():
        logger.debug("No plugin config file found", extra={"path": str(config_path)})
        return []

    logger.debug("Loading plugin config", extra={"path": str(config_path)})

    try:
        with open(config_path, "rb") as f:
            data = tomllib.load(f)
    except Exception as e:
        raise ValueError(f"Failed to parse plugin config: {e}") from e

    plugins = []

    # Load built-in plugins config
    builtin = data.get("builtin", {})
    for name, config in builtin.items():
        if not isinstance(config, dict):
            config = {"enabled": config}
        plugins.append(
            PluginConfig(
                name=name,
                enabled=config.get("enabled", True),
                config=config.get("config", {}),
                source="builtin",
            )
        )

    # Load external plugins config
    external = data.get("external", [])
    for plugin_data in external:
        if not isinstance(plugin_data, dict):
            raise ValueError(f"Invalid plugin config: {plugin_data}")

        plugins.append(
            PluginConfig(
                name=plugin_data.get("name", ""),
                enabled=plugin_data.get("enabled", True),
                config=plugin_data.get("config", {}),
                module=plugin_data.get("module"),
                path=plugin_data.get("path"),
                version=plugin_data.get("version"),
                registry=plugin_data.get("registry"),
                source="external",
            )
        )

    marketplace = data.get("marketplace", [])
    if isinstance(marketplace, dict):
        marketplace = [marketplace]

    for entry in marketplace:
        if not isinstance(entry, dict):
            raise ValueError(f"Invalid marketplace plugin config: {entry!r}")

        plugins.append(
            PluginConfig(
                name=str(entry.get("name", "")),
                enabled=entry.get("enabled", True),
                config=entry.get("config", {}),
                version=entry.get("version"),
                registry=entry.get("registry"),
                source="marketplace",
            )
        )

    return plugins


def discover_plugins(
    config_path: Path | None = None,
    registry_instance: PluginRegistry | None = None,
    marketplace_root: Path | None = None,
) -> PluginRegistry:
    """Discover and load plugins from configuration.

    This function:
    1. Loads plugin configuration from file
    2. Loads built-in plugins
    3. Discovers and loads external plugins
    4. Registers all enabled plugins

    Args:
        config_path: Path to plugin configuration file
        registry_instance: Registry to use. If None, uses global registry.
        marketplace_root: Root directory containing curated marketplace manifests.

    Returns:
        Registry with discovered plugins

    Raises:
        ValueError: If plugin loading fails
    """
    if registry_instance is None:
        registry_instance = registry

    # Ensure we always honour the latest configuration by starting from a clean
    # registry snapshot. This prevents previously enabled plugins from
    # remaining registered after being disabled in configuration files.
    registry_instance.clear()

    # Load plugin configurations
    configs = load_plugin_config(config_path)
    resolved_marketplace_root = marketplace_root or _default_marketplace_root()

    # Load built-in plugins
    try:
        from hephaestus.plugins.builtin import (
            MypyPlugin,
            PipAuditPlugin,
            PytestPlugin,
            RuffCheckPlugin,
            RuffFormatPlugin,
        )

        builtin_plugins: dict[str, type[QualityGatePlugin]] = {
            "ruff-check": RuffCheckPlugin,
            "ruff-format": RuffFormatPlugin,
            "mypy": MypyPlugin,
            "pytest": PytestPlugin,
            "pip-audit": PipAuditPlugin,
        }

        # Register built-in plugins based on config
        for plugin_name, plugin_class in builtin_plugins.items():
            # Check if explicitly disabled in config
            plugin_config = next(
                (c for c in configs if c.name == plugin_name),
                PluginConfig(name=plugin_name, enabled=True),
            )

            if plugin_config.enabled:
                try:
                    plugin_instance = plugin_class()
                    if not registry_instance.is_registered(plugin_name):
                        registry_instance.register(plugin_instance)
                        logger.debug("Registered built-in plugin", extra={"plugin": plugin_name})
                except Exception as e:
                    logger.warning(
                        "Failed to load built-in plugin",
                        extra={"plugin": plugin_name, "error": str(e)},
                    )

    except ImportError as e:
        logger.debug("Built-in plugins not available", extra={"error": str(e)})

    # Load external plugins
    for plugin_config in configs:
        if plugin_config.source != "external":
            continue

        if plugin_config.module or plugin_config.path:
            try:
                _load_external_plugin(plugin_config, registry_instance)
            except Exception as e:
                logger.warning(
                    "Failed to load external plugin",
                    extra={"plugin": plugin_config.name, "error": str(e)},
                )

    marketplace_configs = [cfg for cfg in configs if cfg.source == "marketplace" and cfg.enabled]
    if marketplace_configs:
        manifests = _load_marketplace_manifests(resolved_marketplace_root)
        trust_policy = _load_trust_policy(resolved_marketplace_root)
        _load_marketplace_plugins(
            configs=marketplace_configs,
            manifests=manifests,
            trust_policy=trust_policy,
            registry_instance=registry_instance,
            marketplace_root=resolved_marketplace_root,
        )

    return registry_instance


def _default_marketplace_root() -> Path:
    """Return the default on-disk marketplace registry location."""

    return Path(__file__).resolve().parents[3] / "plugin-templates" / "registry"


def _load_marketplace_manifests(root: Path) -> dict[str, MarketplaceManifest]:
    """Load marketplace manifests from *root*."""

    manifests: dict[str, MarketplaceManifest] = {}

    if not root.exists():
        logger.debug("Marketplace registry root missing", extra={"root": str(root)})
        return manifests

    for manifest_path in root.glob("*.toml"):
        if manifest_path.name == "trust-policy.toml":
            continue

        try:
            with manifest_path.open("rb") as handle:
                data = tomllib.load(handle)
        except Exception as exc:  # pragma: no cover - defensive logging
            logger.warning(
                "Failed to parse marketplace manifest",
                extra={"path": str(manifest_path), "error": str(exc)},
            )
            continue

        plugin_data = data.get("plugin")
        if not isinstance(plugin_data, dict):
            logger.warning(
                "Marketplace manifest missing [plugin] table",
                extra={"path": str(manifest_path)},
            )
            continue

        name = str(plugin_data.get("name", "")).strip()
        version = str(plugin_data.get("version", "")).strip()
        if not name or not version:
            logger.warning(
                "Marketplace manifest missing name or version",
                extra={"path": str(manifest_path)},
            )
            continue

        description = str(plugin_data.get("description", "")).strip()
        author = str(plugin_data.get("author", "")).strip()
        category = str(plugin_data.get("category", "custom")).strip() or "custom"

        entry_data = plugin_data.get("entrypoint", {})
        entry_path: Path | None = None
        entry_module: str | None = None
        registry_root = manifest_path.parent.resolve()
        skip_manifest = False
        if isinstance(entry_data, dict):
            entry_path_value = entry_data.get("path")
            if isinstance(entry_path_value, str) and entry_path_value.strip():
                candidate = (registry_root / entry_path_value).resolve()
                if not _is_within_directory(candidate, registry_root):
                    logger.warning(
                        "Marketplace manifest entrypoint escaped registry root",
                        extra={
                            "path": str(manifest_path),
                            "entrypoint": entry_path_value,
                        },
                    )
                    skip_manifest = True
                else:
                    entry_path = candidate
            module_value = entry_data.get("module")
            if isinstance(module_value, str) and module_value.strip():
                entry_module = module_value.strip()

        compatibility = plugin_data.get("compatibility", {})
        hephaestus_spec: str | None = None
        python_spec: str | None = None
        if isinstance(compatibility, dict):
            hephaestus_value = compatibility.get("hephaestus")
            python_value = compatibility.get("python")
            if isinstance(hephaestus_value, str):
                hephaestus_spec = hephaestus_value.strip() or None
            if isinstance(python_value, str):
                python_spec = python_value.strip() or None

        raw_dependencies = plugin_data.get("dependencies", [])
        dependencies: list[MarketplaceDependency] = []
        if isinstance(raw_dependencies, list):
            for raw_dependency in raw_dependencies:
                dependency = _parse_marketplace_dependency(raw_dependency)
                if dependency is not None:
                    dependencies.append(dependency)

        signature_data = plugin_data.get("signature", {})
        bundle_path: Path | None = None
        if isinstance(signature_data, dict):
            bundle_value = signature_data.get("bundle")
            if isinstance(bundle_value, str) and bundle_value.strip():
                candidate = (registry_root / bundle_value).resolve()
                if not _is_within_directory(candidate, registry_root):
                    logger.warning(
                        "Marketplace manifest signature bundle escaped registry root",
                        extra={
                            "path": str(manifest_path),
                            "bundle": bundle_value,
                        },
                    )
                    skip_manifest = True
                else:
                    bundle_path = candidate

        if skip_manifest:
            continue

        manifests[name] = MarketplaceManifest(
            name=name,
            version=version,
            description=description,
            author=author,
            category=category,
            entry_path=entry_path,
            entry_module=entry_module,
            dependencies=tuple(dependencies),
            hephaestus_spec=hephaestus_spec,
            python_spec=python_spec,
            signature_bundle=bundle_path,
            manifest_path=manifest_path.resolve(),
        )

    return manifests


def _parse_marketplace_dependency(raw_dependency: Any) -> MarketplaceDependency | None:
    if not isinstance(raw_dependency, dict):
        return None

    kind_value = raw_dependency.get("type") or raw_dependency.get("kind")
    name_value = raw_dependency.get("name")

    if not isinstance(kind_value, str) or not isinstance(name_value, str):
        return None

    kind = kind_value.strip().lower()
    name = name_value.strip()
    if not kind or not name:
        return None

    version_value = raw_dependency.get("version")
    version = str(version_value).strip() if isinstance(version_value, str) else None
    return MarketplaceDependency(kind=kind, name=name, version=version)


def _load_trust_policy(root: Path) -> TrustPolicy:
    policy_path = root / "trust-policy.toml"
    if not policy_path.exists():
        return TrustPolicy(require_signature=False, default_identities=(), per_plugin={})

    try:
        with policy_path.open("rb") as handle:
            payload = tomllib.load(handle)
    except Exception as exc:  # pragma: no cover - defensive logging
        logger.warning(
            "Failed to parse marketplace trust policy",
            extra={"path": str(policy_path), "error": str(exc)},
        )
        return TrustPolicy(require_signature=False, default_identities=(), per_plugin={})

    trust_section = payload.get("trust", {})
    if not isinstance(trust_section, dict):
        trust_section = {}

    require_signature = bool(trust_section.get("require_signature", False))
    raw_identities = trust_section.get("allowed_identities", [])
    if isinstance(raw_identities, str):
        raw_identities = [raw_identities]
    default_identities = tuple(
        identity.strip()
        for identity in raw_identities
        if isinstance(identity, str) and identity.strip()
    )

    per_plugin: dict[str, tuple[str, ...]] = {}
    plugins_section = trust_section.get("plugins", {})
    if isinstance(plugins_section, dict):
        for plugin_name, plugin_policy in plugins_section.items():
            if not isinstance(plugin_policy, dict) or not isinstance(plugin_name, str):
                continue
            plugin_identities = plugin_policy.get("allowed_identities", [])
            if isinstance(plugin_identities, str):
                plugin_identities = [plugin_identities]
            per_plugin[plugin_name] = tuple(
                identity.strip()
                for identity in plugin_identities
                if isinstance(identity, str) and identity.strip()
            )

    return TrustPolicy(
        require_signature=require_signature,
        default_identities=default_identities,
        per_plugin=per_plugin,
    )


def _current_hephaestus_version() -> str:
    for candidate in ("hephaestus-toolkit", "hephaestus"):
        try:
            return metadata.version(candidate)
        except metadata.PackageNotFoundError:
            continue

    pyproject = Path(__file__).resolve().parents[3] / "pyproject.toml"
    if pyproject.exists():
        try:
            with pyproject.open("rb") as handle:
                payload = tomllib.load(handle)
            project = payload.get("project", {})
            if isinstance(project, dict):
                version_value = project.get("version")
                if isinstance(version_value, str):
                    return version_value
        except Exception:  # pragma: no cover - fallback path
            logger.debug("Failed to derive version from pyproject", exc_info=True)

    return "0.0.0"


def _python_version_string() -> str:
    return ".".join(str(part) for part in sys.version_info[:3])


def _ensure_marketplace_compatibility(manifest: MarketplaceManifest) -> None:
    hephaestus_version = _current_hephaestus_version()
    python_version = _python_version_string()

    if manifest.hephaestus_spec:
        try:
            spec = SpecifierSet(manifest.hephaestus_spec)
            current = Version(hephaestus_version)
        except (InvalidVersion, ValueError) as exc:
            raise ValueError(
                f"Marketplace plugin {manifest.name!r} declared invalid Hephaestus compatibility."
            ) from exc
        if current not in spec:
            raise ValueError(
                f"Marketplace plugin {manifest.name!r} requires Hephaestus {manifest.hephaestus_spec},"
                f" current version is {hephaestus_version}."
            )

    if manifest.python_spec:
        try:
            spec = SpecifierSet(manifest.python_spec)
            current = Version(python_version)
        except (InvalidVersion, ValueError) as exc:
            raise ValueError(
                f"Marketplace plugin {manifest.name!r} declared invalid Python compatibility."
            ) from exc
        if current not in spec:
            raise ValueError(
                f"Marketplace plugin {manifest.name!r} requires Python {manifest.python_spec},"
                f" current version is {python_version}."
            )


def _ensure_python_dependency(dependency: MarketplaceDependency) -> None:
    try:
        installed_version = metadata.version(dependency.name)
    except metadata.PackageNotFoundError as exc:
        raise ValueError(
            f"Marketplace plugin dependency {dependency.name!r} is not installed."
        ) from exc

    if dependency.version:
        try:
            spec = SpecifierSet(dependency.version)
            current = Version(installed_version)
        except (InvalidVersion, ValueError) as exc:
            raise ValueError(
                f"Marketplace plugin dependency {dependency.name!r} has an invalid version constraint."
            ) from exc
        if current not in spec:
            raise ValueError(
                f"Marketplace plugin dependency {dependency.name!r}=={installed_version} does not satisfy {dependency.version}."
            )


def _ensure_marketplace_dependencies(
    manifest: MarketplaceManifest,
    resolved_plugins: set[str],
) -> None:
    for dependency in manifest.dependencies:
        if dependency.kind == "plugin":
            if dependency.name not in resolved_plugins:
                raise ValueError(
                    f"Marketplace plugin {manifest.name!r} requires plugin {dependency.name!r}"
                    " which is not available."
                )
        elif dependency.kind == "python":
            _ensure_python_dependency(dependency)
        else:
            raise ValueError(
                f"Marketplace plugin {manifest.name!r} declared unsupported dependency type {dependency.kind!r}."
            )


def _verify_marketplace_signature(
    manifest: MarketplaceManifest,
    trust_policy: TrustPolicy,
) -> None:
    attributes = {"plugin": manifest.name, "version": manifest.version}
    telemetry.record_counter(
        "hephaestus.plugins.marketplace.fetch",
        attributes=attributes,
    )

    def _fail(reason: str, message: str, *, exc: Exception | None = None) -> None:
        telemetry.record_counter(
            "hephaestus.plugins.marketplace.errors",
            attributes={**attributes, "reason": reason},
        )
        if exc is not None:
            raise ValueError(message) from exc
        raise ValueError(message)

    bundle_path = manifest.signature_bundle
    if bundle_path is None:
        if trust_policy.require_signature:
            _fail(
                "missing-signature",
                f"Marketplace trust policy requires a signature for {manifest.name!r}.",
            )
        return

    if not bundle_path.is_file():
        _fail(
            "missing-bundle",
            (
                f"Marketplace plugin {manifest.name!r} signature bundle"
                f" at {bundle_path} is not accessible."
            ),
        )

    try:
        payload = json.loads(bundle_path.read_text(encoding="utf-8"))
    except Exception as exc:
        _fail(
            "invalid-bundle",
            f"Marketplace plugin {manifest.name!r} signature bundle could not be parsed.",
            exc=exc,
        )

    if not isinstance(payload, dict):
        _fail(
            "invalid-structure",
            f"Marketplace plugin {manifest.name!r} signature bundle structure was invalid.",
        )

    message_signature = payload.get("messageSignature", {})
    if not isinstance(message_signature, dict):
        _fail(
            "missing-messageSignature",
            f"Marketplace plugin {manifest.name!r} signature bundle missing messageSignature section.",
        )

    digest_info = message_signature.get("messageDigest", {})
    if not isinstance(digest_info, dict):
        _fail(
            "missing-digest",
            f"Marketplace plugin {manifest.name!r} signature bundle missing digest information.",
        )

    algorithm = str(digest_info.get("algorithm", "")).lower()
    if algorithm not in {"sha256", "sha2_256"}:
        _fail(
            "unsupported-algorithm",
            f"Marketplace plugin {manifest.name!r} signature bundle used unsupported digest algorithm {algorithm!r}.",
        )

    digest_value = digest_info.get("digest")
    if not isinstance(digest_value, str) or not digest_value:
        _fail(
            "missing-digest-value",
            f"Marketplace plugin {manifest.name!r} signature bundle missing digest value.",
        )

    try:
        expected_digest = base64.b64decode(digest_value).hex()
    except Exception as exc:
        _fail(
            "invalid-digest-encoding",
            f"Marketplace plugin {manifest.name!r} signature bundle digest was not valid base64.",
            exc=exc,
        )

    artifact_path = manifest.artifact_path()
    if not artifact_path.is_file():
        _fail(
            "missing-artifact",
            (
                f"Marketplace plugin {manifest.name!r} entrypoint"
                f" {artifact_path} is not a regular file."
            ),
        )

    actual_digest = hashlib.sha256(artifact_path.read_bytes()).hexdigest()
    if actual_digest != expected_digest:
        _fail(
            "digest-mismatch",
            f"Marketplace plugin {manifest.name!r} signature digest mismatch.",
        )

    identities: list[str] = []
    verification_material = payload.get("verificationMaterial", {})
    if isinstance(verification_material, dict):
        raw_identities = verification_material.get("identities", [])
        if isinstance(raw_identities, list):
            identities = [
                identity.strip()
                for identity in raw_identities
                if isinstance(identity, str) and identity.strip()
            ]

    allowed_patterns = trust_policy.identities_for(manifest.name)
    if allowed_patterns and not any(
        fnmatch.fnmatchcase(identity, pattern)
        for identity in identities
        for pattern in allowed_patterns
    ):
        _fail(
            "identity-mismatch",
            f"Marketplace plugin {manifest.name!r} failed trust policy identity checks.",
        )

    telemetry.record_counter(
        "hephaestus.plugins.marketplace.verified",
        attributes={
            **attributes,
            "identity": identities[0] if identities else "unknown",
        },
    )


def _instantiate_marketplace_plugin(manifest: MarketplaceManifest) -> QualityGatePlugin:
    if manifest.entry_module:
        plugin_class = _load_from_module(manifest.entry_module)
    else:
        artifact_path = manifest.artifact_path()
        plugin_class = _load_from_path(manifest.name, str(artifact_path))

    plugin_instance = plugin_class()
    metadata_obj = plugin_instance.metadata
    if metadata_obj.name != manifest.name:
        raise ValueError(
            f"Marketplace manifest name {manifest.name!r} does not match plugin metadata {metadata_obj.name!r}."
        )
    if metadata_obj.version != manifest.version:
        raise ValueError(
            f"Marketplace manifest version {manifest.version!r} does not match plugin metadata {metadata_obj.version!r}."
        )
    return plugin_instance


def _load_marketplace_plugins(
    *,
    configs: list[PluginConfig],
    manifests: dict[str, MarketplaceManifest],
    trust_policy: TrustPolicy,
    registry_instance: PluginRegistry,
    marketplace_root: Path,
) -> None:
    resolved_plugins = {plugin.metadata.name for plugin in registry_instance.all_plugins()}
    pending = list(configs)

    while pending:
        progressed = False
        for config in list(pending):
            manifest = manifests.get(config.name)
            if manifest is None:
                raise ValueError(
                    f"Marketplace plugin {config.name!r} not found in registry {marketplace_root}."
                )

            if config.version and config.version != manifest.version:
                raise ValueError(
                    f"Marketplace plugin {config.name!r} version {config.version} is not available"
                    f" (registry provides {manifest.version})."
                )

            try:
                _ensure_marketplace_compatibility(manifest)
                _verify_marketplace_signature(manifest, trust_policy)
                _ensure_marketplace_dependencies(manifest, resolved_plugins)
            except ValueError as exc:
                telemetry.record_counter(
                    "hephaestus.plugins.marketplace.errors",
                    attributes={
                        "plugin": manifest.name,
                        "reason": exc.__class__.__name__,
                    },
                )
                raise

            telemetry.record_counter(
                "hephaestus.plugins.marketplace.dependencies_resolved",
                attributes={
                    "plugin": manifest.name,
                    "version": manifest.version,
                },
            )

            plugin_instance = _instantiate_marketplace_plugin(manifest)
            if not registry_instance.is_registered(manifest.name):
                registry_instance.register(plugin_instance)
                telemetry.record_counter(
                    "hephaestus.plugins.marketplace.registered",
                    attributes={
                        "plugin": manifest.name,
                        "version": manifest.version,
                    },
                )

            resolved_plugins.add(manifest.name)
            pending.remove(config)
            progressed = True

        if not progressed:
            unresolved = ", ".join(sorted(cfg.name for cfg in pending))
            raise ValueError(f"Unable to resolve marketplace plugin dependencies: {unresolved}.")


def _find_plugin_class(module: Any) -> type[QualityGatePlugin] | None:
    """Find QualityGatePlugin subclass in a module."""
    for attr_name in dir(module):
        attr = getattr(module, attr_name)
        if (
            isinstance(attr, type)
            and issubclass(attr, QualityGatePlugin)
            and attr is not QualityGatePlugin
        ):
            return attr
    return None


def _load_from_module(module_name: str) -> type[QualityGatePlugin]:
    """Load plugin class from importable module."""
    try:
        module = importlib.import_module(module_name)
        plugin_class = _find_plugin_class(module)
        if plugin_class is None:
            raise ValueError(f"No QualityGatePlugin class found in module {module_name}")
        return plugin_class
    except ImportError as e:
        raise ValueError(f"Failed to import plugin module {module_name}: {e}") from e


def _load_from_path(plugin_name: str, path: str) -> type[QualityGatePlugin]:
    """Load plugin class from file path."""
    path_obj = Path(path)
    if not path_obj.exists():
        raise ValueError(f"Plugin path does not exist: {path}")

    try:
        spec = importlib.util.spec_from_file_location(plugin_name, path)
        if spec is None or spec.loader is None:
            raise ValueError(f"Failed to load plugin from {path}")

        module = importlib.util.module_from_spec(spec)
        sys.modules[plugin_name] = module
        spec.loader.exec_module(module)

        plugin_class = _find_plugin_class(module)
        if plugin_class is None:
            raise ValueError(f"No QualityGatePlugin class found in {path}")
        return plugin_class
    except Exception as e:
        raise ValueError(f"Failed to load plugin from {path}: {e}") from e


def _load_external_plugin(config: PluginConfig, registry_instance: PluginRegistry) -> None:
    """Load an external plugin from module or file path.

    Args:
        config: Plugin configuration
        registry_instance: Registry to register plugin in

    Raises:
        ValueError: If plugin cannot be loaded
    """
    if not config.enabled:
        return

    if not config.module and not config.path:
        raise ValueError(f"Plugin {config.name} has neither 'module' nor 'path' specified")

    if config.module:
        plugin_class = _load_from_module(config.module)
    else:
        if config.path is None:
            raise ValueError(f"Plugin {config.name} has neither 'module' nor 'path' specified")
        plugin_class = _load_from_path(config.name, config.path)

    try:
        plugin_instance = plugin_class()
        if not registry_instance.is_registered(config.name):
            registry_instance.register(plugin_instance)
            logger.info("Loaded external plugin", extra={"plugin": config.name})
    except Exception as e:
        raise ValueError(f"Failed to instantiate plugin {config.name}: {e}") from e


# Global registry instance
registry = PluginRegistry()
