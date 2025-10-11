"""Focused tests for marketplace plugin helpers."""

from __future__ import annotations

import base64
import hashlib
import json
from pathlib import Path

import pytest

from hephaestus import telemetry
from hephaestus.plugins import (
    MarketplaceDependency,
    MarketplaceManifest,
    PluginConfig,
    PluginMetadata,
    PluginRegistry,
    PluginResult,
    QualityGatePlugin,
    TrustPolicy,
    _ensure_marketplace_compatibility,
    _ensure_marketplace_dependencies,
    _load_marketplace_manifests,
    _load_marketplace_plugins,
    _load_trust_policy,
    _parse_marketplace_dependency,
    _verify_marketplace_signature,
    discover_plugins,
    load_plugin_config,
)
from hephaestus.plugins import registry as global_registry


@pytest.fixture(autouse=True)
def _telemetry_stub(monkeypatch: pytest.MonkeyPatch) -> list[tuple[str, dict[str, str]]]:
    """Capture telemetry calls so tests can assert on behaviour."""

    calls: list[tuple[str, dict[str, str]]] = []

    def _record(metric: str, *, attributes: dict[str, str] | None = None) -> None:
        calls.append((metric, attributes or {}))

    monkeypatch.setattr(telemetry, "record_counter", _record)

    return calls


def _make_manifest(tmp_path: Path, **overrides: object) -> MarketplaceManifest:
    """Return a MarketplaceManifest populated with sane defaults."""

    entry_path_override = overrides.get("entry_path")
    if isinstance(entry_path_override, Path):
        artifact = entry_path_override
    else:
        artifact = tmp_path / "plugin.py"
        artifact.write_text("print('ok')\n", encoding="utf-8")

    manifest_path = tmp_path / "manifest.toml"
    manifest_path.write_text("", encoding="utf-8")

    defaults: dict[str, object] = {
        "name": "example-plugin",
        "version": "1.0.0",
        "description": "Example plugin",
        "author": "Quality Team",
        "category": "custom",
        "entry_path": artifact,
        "entry_module": None,
        "dependencies": (),
        "hephaestus_spec": None,
        "python_spec": None,
        "signature_bundle": None,
        "manifest_path": manifest_path,
    }
    defaults.update(overrides)

    return MarketplaceManifest(**defaults)  # type: ignore[arg-type]


def test_parse_marketplace_dependency_aliases() -> None:
    dependency = _parse_marketplace_dependency(
        {"type": "python", "name": "packaging", "version": ">=23"}
    )

    assert dependency == MarketplaceDependency(kind="python", name="packaging", version=">=23")


def test_parse_marketplace_dependency_invalid_payload() -> None:
    assert _parse_marketplace_dependency({"type": "", "name": "tool"}) is None
    assert _parse_marketplace_dependency({"name": "tool"}) is None
    assert _parse_marketplace_dependency("not-a-dict") is None


def test_load_plugin_config_handles_edge_cases(tmp_path: Path) -> None:
    config_path = tmp_path / "plugins.toml"
    config_path.write_text('external = ["broken"]', encoding="utf-8")

    with pytest.raises(ValueError, match="Invalid plugin config"):
        load_plugin_config(config_path)

    config_path.write_text('marketplace = "invalid"', encoding="utf-8")

    with pytest.raises(ValueError, match="Invalid marketplace plugin config"):
        load_plugin_config(config_path)

    config_path.write_text(
        """
[marketplace]
name = "market-example"
registry = "embedded"
        """.strip(),
        encoding="utf-8",
    )

    configs = load_plugin_config(config_path)
    marketplace_configs = [cfg for cfg in configs if cfg.source == "marketplace"]
    assert marketplace_configs and marketplace_configs[0].name == "market-example"


def test_load_marketplace_manifests_enforces_registry_boundaries(tmp_path: Path) -> None:
    registry_root = tmp_path / "registry"
    registry_root.mkdir()

    safe_plugins = registry_root / "plugins"
    safe_plugins.mkdir()
    (safe_plugins / "safe.py").write_text("print('safe')\n", encoding="utf-8")

    (registry_root / "safe.toml").write_text(
        """
[plugin]
name = "safe"
version = "1.0.0"
description = "Safe plugin"
author = "Quality Team"
category = "custom"

[plugin.entrypoint]
path = "plugins/safe.py"
        """.strip(),
        encoding="utf-8",
    )

    (registry_root / "escape-entry.toml").write_text(
        """
[plugin]
name = "escape-entry"
version = "1.0.0"
description = "Escape entry"
author = "Quality Team"
category = "custom"

[plugin.entrypoint]
path = "../outside.py"
        """.strip(),
        encoding="utf-8",
    )

    (registry_root / "escape-signature.toml").write_text(
        """
[plugin]
name = "escape-signature"
version = "1.0.0"
description = "Escape signature"
author = "Quality Team"
category = "custom"

[plugin.entrypoint]
module = "escape.module"

[plugin.signature]
bundle = "../outside.sigstore"
        """.strip(),
        encoding="utf-8",
    )

    manifests = _load_marketplace_manifests(registry_root)

    assert set(manifests) == {"safe"}


def test_discover_plugins_uses_defaults(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.chdir(tmp_path)
    result = discover_plugins()
    try:
        assert result.is_registered("ruff-check")
    finally:
        global_registry.clear()


def test_load_trust_policy_with_plugin_override(tmp_path: Path) -> None:
    policy_path = tmp_path / "trust-policy.toml"
    policy_path.write_text(
        """
[trust]
require_signature = true
allowed_identities = ["mailto:team@example.com"]

[trust.plugins."example-plugin"]
allowed_identities = ["mailto:plugins@example.com"]
        """.strip(),
        encoding="utf-8",
    )

    policy = _load_trust_policy(tmp_path)

    assert policy.require_signature is True
    assert policy.identities_for("example-plugin") == ("mailto:plugins@example.com",)
    assert policy.identities_for("unknown") == ("mailto:team@example.com",)


def test_ensure_marketplace_compatibility_validates_versions(
    monkeypatch: pytest.MonkeyPatch, tmp_path: Path
) -> None:
    monkeypatch.setattr("hephaestus.plugins._current_hephaestus_version", lambda: "1.2.3")
    monkeypatch.setattr("hephaestus.plugins._python_version_string", lambda: "3.12.1")

    manifest = _make_manifest(
        tmp_path,
        hephaestus_spec=">=1.0,<2.0",
        python_spec=">=3.10",
    )

    _ensure_marketplace_compatibility(manifest)

    incompatible = _make_manifest(
        tmp_path,
        hephaestus_spec=">=2.0",
    )
    with pytest.raises(ValueError, match="requires Hephaestus"):
        _ensure_marketplace_compatibility(incompatible)

    bad_spec = _make_manifest(tmp_path, hephaestus_spec="not-a-spec")
    with pytest.raises(ValueError, match="invalid Hephaestus compatibility"):
        _ensure_marketplace_compatibility(bad_spec)


def test_ensure_marketplace_dependencies_enforces_python_packages(
    monkeypatch: pytest.MonkeyPatch, tmp_path: Path
) -> None:
    monkeypatch.setattr(
        "hephaestus.plugins.metadata.version",
        lambda name: {"packaging": "23.1"}[name],
    )

    manifest = _make_manifest(
        tmp_path,
        dependencies=(
            MarketplaceDependency(kind="plugin", name="other"),
            MarketplaceDependency(kind="python", name="packaging", version=">=24"),
        ),
    )

    with pytest.raises(ValueError, match="requires plugin 'other'"):
        _ensure_marketplace_dependencies(manifest, resolved_plugins=set())

    with pytest.raises(ValueError, match="does not satisfy"):
        _ensure_marketplace_dependencies(
            _make_manifest(
                tmp_path,
                dependencies=(
                    MarketplaceDependency(kind="python", name="packaging", version=">=24"),
                ),
            ),
            resolved_plugins={"example-plugin"},
        )

    satisfied = _make_manifest(
        tmp_path,
        dependencies=(
            MarketplaceDependency(kind="plugin", name="example-plugin"),
            MarketplaceDependency(kind="python", name="packaging", version=">=23"),
        ),
    )
    _ensure_marketplace_dependencies(
        satisfied,
        resolved_plugins={"example-plugin"},
    )

    unsupported = _make_manifest(
        tmp_path,
        dependencies=(MarketplaceDependency(kind="unknown", name="tool"),),
    )
    with pytest.raises(ValueError, match="unsupported dependency type"):
        _ensure_marketplace_dependencies(unsupported, resolved_plugins=set())


def test_load_marketplace_plugins_registers_plugin(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
    _telemetry_stub: list[tuple[str, dict[str, str]]],
) -> None:
    manifest = _make_manifest(
        tmp_path,
        name="market-example",
        version="1.0.0",
    )

    config = PluginConfig(
        name="market-example",
        enabled=True,
        config={},
        source="marketplace",
        version="1.0.0",
    )

    class DummyPlugin(QualityGatePlugin):
        @property
        def metadata(self) -> PluginMetadata:
            return PluginMetadata(
                name="market-example",
                version="1.0.0",
                description="",
                author="",
                category="custom",
                requires=[],
            )

        def validate_config(
            self, config: dict[str, object]
        ) -> bool:  # pragma: no cover - simple stub
            return True

        def run(self, config: dict[str, object]) -> PluginResult:
            return PluginResult(success=True, message="ok")

    monkeypatch.setattr(
        "hephaestus.plugins._instantiate_marketplace_plugin",
        lambda manifest: DummyPlugin(),
    )
    monkeypatch.setattr(
        "hephaestus.plugins._ensure_marketplace_compatibility",
        lambda manifest: None,
    )
    monkeypatch.setattr(
        "hephaestus.plugins._verify_marketplace_signature",
        lambda manifest, policy: None,
    )
    monkeypatch.setattr(
        "hephaestus.plugins._ensure_marketplace_dependencies",
        lambda manifest, resolved: None,
    )

    registry = PluginRegistry()
    _load_marketplace_plugins(
        configs=[config],
        manifests={"market-example": manifest},
        trust_policy=TrustPolicy(require_signature=False, default_identities=(), per_plugin={}),
        registry_instance=registry,
        marketplace_root=tmp_path,
    )

    assert registry.is_registered("market-example")

    metrics = {metric for metric, _ in _telemetry_stub}
    assert "hephaestus.plugins.marketplace.dependencies_resolved" in metrics
    assert "hephaestus.plugins.marketplace.registered" in metrics


def test_load_marketplace_plugins_version_mismatch(tmp_path: Path) -> None:
    manifest = _make_manifest(
        tmp_path,
        name="market-example",
        version="2.0.0",
    )

    config = PluginConfig(
        name="market-example",
        enabled=True,
        config={},
        source="marketplace",
        version="1.0.0",
    )

    registry = PluginRegistry()

    with pytest.raises(ValueError, match="version 1.0.0 is not available"):
        _load_marketplace_plugins(
            configs=[config],
            manifests={"market-example": manifest},
            trust_policy=TrustPolicy(require_signature=False, default_identities=(), per_plugin={}),
            registry_instance=registry,
            marketplace_root=tmp_path,
        )


def test_verify_marketplace_signature_respects_policy(tmp_path: Path) -> None:
    manifest = _make_manifest(tmp_path)
    policy = TrustPolicy(require_signature=True, default_identities=(), per_plugin={})

    with pytest.raises(ValueError, match="requires a signature"):
        _verify_marketplace_signature(manifest, policy)


def test_verify_marketplace_signature_requires_existing_bundle(tmp_path: Path) -> None:
    manifest = _make_manifest(
        tmp_path,
        signature_bundle=tmp_path / "missing.sigstore",
    )

    policy = TrustPolicy(require_signature=True, default_identities=(), per_plugin={})

    with pytest.raises(ValueError, match="signature bundle"):
        _verify_marketplace_signature(manifest, policy)


def test_verify_marketplace_signature_identity_enforcement(
    tmp_path: Path, _telemetry_stub: list[tuple[str, dict[str, str]]]
) -> None:
    artifact = tmp_path / "plugin.py"
    artifact.write_text("print('hello')\n", encoding="utf-8")

    digest = hashlib.sha256(artifact.read_bytes()).digest()
    bundle = {
        "messageSignature": {
            "messageDigest": {
                "algorithm": "sha256",
                "digest": base64.b64encode(digest).decode("ascii"),
            }
        },
        "verificationMaterial": {"identities": ["mailto:allowed@example.com"]},
    }

    signature_path = tmp_path / "bundle.sigstore"
    signature_path.write_text(json.dumps(bundle), encoding="utf-8")

    manifest = _make_manifest(tmp_path, signature_bundle=signature_path, entry_path=artifact)

    policy = TrustPolicy(
        require_signature=True,
        default_identities=("mailto:allowed@example.com",),
        per_plugin={},
    )

    _verify_marketplace_signature(manifest, policy)

    # The success path should record a verification counter.
    metrics = [metric for metric, _ in _telemetry_stub]
    assert "hephaestus.plugins.marketplace.verified" in metrics

    rejecting_policy = TrustPolicy(
        require_signature=True,
        default_identities=("mailto:other@example.com",),
        per_plugin={},
    )

    with pytest.raises(ValueError, match="identity checks"):
        _verify_marketplace_signature(manifest, rejecting_policy)


def test_verify_marketplace_signature_rejects_algorithm(tmp_path: Path) -> None:
    artifact = tmp_path / "plugin.py"
    artifact.write_text("print('data')\n", encoding="utf-8")

    bundle = {
        "messageSignature": {
            "messageDigest": {
                "algorithm": "sha1",
                "digest": base64.b64encode(b"dummy").decode("ascii"),
            }
        }
    }

    signature_path = tmp_path / "bundle.sigstore"
    signature_path.write_text(json.dumps(bundle), encoding="utf-8")

    manifest = _make_manifest(
        tmp_path,
        signature_bundle=signature_path,
        entry_path=artifact,
    )

    policy = TrustPolicy(require_signature=True, default_identities=(), per_plugin={})

    with pytest.raises(ValueError, match="unsupported digest algorithm"):
        _verify_marketplace_signature(manifest, policy)


def test_verify_marketplace_signature_rejects_non_file_artifact(tmp_path: Path) -> None:
    artifact_dir = tmp_path / "plugin-dir"
    artifact_dir.mkdir()

    bundle = {
        "messageSignature": {
            "messageDigest": {
                "algorithm": "sha256",
                "digest": base64.b64encode(b"dummy").decode("ascii"),
            }
        }
    }

    signature_path = tmp_path / "bundle.sigstore"
    signature_path.write_text(json.dumps(bundle), encoding="utf-8")

    manifest = _make_manifest(
        tmp_path,
        signature_bundle=signature_path,
        entry_path=artifact_dir,
    )

    policy = TrustPolicy(require_signature=True, default_identities=(), per_plugin={})

    with pytest.raises(ValueError, match="not a regular file"):
        _verify_marketplace_signature(manifest, policy)
