import shutil
import textwrap
from pathlib import Path
from typing import Any, NoReturn

import pytest

from hephaestus import telemetry
from hephaestus.plugins import PluginResult

PROJECT_ROOT = Path(__file__).resolve().parent.parent
DEFAULT_MARKETPLACE_ROOT = PROJECT_ROOT / "plugin-templates" / "registry"


def test_plugin_system_imports() -> None:
    """Test that plugin system can be imported."""
    from hephaestus.plugins import (
        PluginConfig,
        PluginMetadata,
        PluginRegistry,
        PluginResult,
        QualityGatePlugin,
        discover_plugins,
        load_plugin_config,
    )

    assert PluginMetadata is not None
    assert PluginResult is not None
    assert QualityGatePlugin is not None
    assert PluginRegistry is not None
    assert PluginConfig is not None
    assert discover_plugins is not None
    assert load_plugin_config is not None


def test_builtin_plugins_available() -> None:
    """Test that built-in plugins are available."""
    from hephaestus.plugins.builtin import (
        MypyPlugin,
        PipAuditPlugin,
        PytestPlugin,
        RuffCheckPlugin,
        RuffFormatPlugin,
    )

    # Should be able to instantiate
    ruff_check = RuffCheckPlugin()
    assert ruff_check.metadata.name == "ruff-check"
    assert ruff_check.metadata.category == "linting"

    ruff_format = RuffFormatPlugin()
    assert ruff_format.metadata.name == "ruff-format"

    mypy = MypyPlugin()
    assert mypy.metadata.name == "mypy"

    pytest_plugin = PytestPlugin()
    assert pytest_plugin.metadata.name == "pytest"

    pip_audit = PipAuditPlugin()
    assert pip_audit.metadata.name == "pip-audit"


def test_plugin_config_validation() -> None:
    """Test plugin configuration validation."""
    from hephaestus.plugins.builtin import RuffCheckPlugin

    plugin = RuffCheckPlugin()

    # Valid config
    assert plugin.validate_config({"paths": ["src", "tests"]}) is True

    # Empty config should be valid
    assert plugin.validate_config({}) is True

    # Invalid paths type - should raise ValueError
    with pytest.raises(ValueError, match="paths"):
        plugin.validate_config({"paths": "not-a-list"})


def test_plugin_execution_with_missing_tool(monkeypatch: pytest.MonkeyPatch) -> None:
    """Test that plugins handle missing tools gracefully."""
    from hephaestus.plugins import PluginResult
    from hephaestus.plugins.builtin import RuffCheckPlugin

    plugin = RuffCheckPlugin()

    def raise_missing(*_args: Any, **_kwargs: Any) -> NoReturn:
        raise FileNotFoundError("ruff command not found")

    monkeypatch.setattr("subprocess.run", raise_missing)

    result = plugin.run({})

    assert isinstance(result, PluginResult)
    assert result.success is False
    assert result.exit_code == 127
    assert "not" in result.message.lower()


def test_plugin_discovery_with_no_config() -> None:
    """Test plugin discovery when no config file exists."""
    from hephaestus.plugins import PluginRegistry, discover_plugins

    registry = PluginRegistry()

    # Discover with non-existent config path
    result_registry = discover_plugins(
        config_path=Path("/nonexistent/config.toml"),
        registry_instance=registry,
        marketplace_root=DEFAULT_MARKETPLACE_ROOT,
    )

    # Should still load built-in plugins
    assert result_registry is not None
    plugins = result_registry.all_plugins()
    assert len(plugins) >= 5  # At least the 5 built-in plugins


def test_plugin_registry_ordering() -> None:
    """Test that plugins are sorted by execution order."""
    from hephaestus.plugins import PluginMetadata, PluginRegistry, QualityGatePlugin

    class EarlyPlugin(QualityGatePlugin):
        @property
        def metadata(self) -> PluginMetadata:
            return PluginMetadata(
                name="early",
                version="1.0",
                description="Early plugin",
                author="test",
                category="test",
                requires=[],
                order=10,
            )

        def validate_config(self, config: dict[str, Any]) -> bool:
            return True

        def run(self, config: dict[str, Any]) -> PluginResult:
            from hephaestus.plugins import PluginResult

            return PluginResult(success=True, message="ok")

    class LatePlugin(QualityGatePlugin):
        @property
        def metadata(self) -> PluginMetadata:
            return PluginMetadata(
                name="late",
                version="1.0",
                description="Late plugin",
                author="test",
                category="test",
                requires=[],
                order=100,
            )

        def validate_config(self, config: dict[str, Any]) -> bool:
            return True

        def run(self, config: dict[str, Any]) -> PluginResult:
            from hephaestus.plugins import PluginResult

            return PluginResult(success=True, message="ok")

    registry = PluginRegistry()
    registry.register(LatePlugin())
    registry.register(EarlyPlugin())

    plugins = registry.all_plugins()
    assert plugins[0].metadata.name == "early"
    assert plugins[1].metadata.name == "late"


def test_plugin_lifecycle_hooks() -> None:
    """Test plugin setup and teardown hooks."""
    from hephaestus.plugins import PluginMetadata, PluginResult, QualityGatePlugin

    setup_called: list[bool] = []
    teardown_called: list[bool] = []

    class LifecyclePlugin(QualityGatePlugin):
        @property
        def metadata(self) -> PluginMetadata:
            return PluginMetadata(
                name="lifecycle",
                version="1.0",
                description="Test lifecycle",
                author="test",
                category="test",
                requires=[],
            )

        def validate_config(self, config: dict[str, Any]) -> bool:
            return True

        def run(self, config: dict[str, Any]) -> PluginResult:
            return PluginResult(success=True, message="ok")

        def setup(self) -> None:
            setup_called.append(True)

        def teardown(self) -> None:
            teardown_called.append(True)

    plugin = LifecyclePlugin()

    # Setup and teardown should be callable
    plugin.setup()
    assert len(setup_called) == 1

    plugin.run({})

    plugin.teardown()
    assert len(teardown_called) == 1


def _write_plugin_config(tmp_path: Path, version: str = "1.0.0") -> Path:
    config_dir = tmp_path / ".hephaestus"
    config_dir.mkdir()
    config_path = config_dir / "plugins.toml"
    config_path.write_text(
        textwrap.dedent(
            f"""
            [builtin]
            [builtin.ruff-check]
            enabled = true

            [[marketplace]]
            name = "example-plugin"
            version = "{version}"
            registry = "default"
            enabled = true

            [marketplace.config]
            severity = "high"
            """
        ).strip()
        + "\n",
        encoding="utf-8",
    )
    return config_path


def _capture_counters(monkeypatch: pytest.MonkeyPatch) -> list[tuple[str, int, dict[str, Any]]]:
    captured: list[tuple[str, int, dict[str, Any]]] = []

    def fake_counter(name: str, value: int = 1, attributes: dict[str, Any] | None = None) -> None:
        captured.append((name, value, attributes or {}))

    monkeypatch.setattr(telemetry, "record_counter", fake_counter)
    return captured


def _copy_registry(tmp_path: Path) -> Path:
    registry_root = tmp_path / "registry"
    shutil.copytree(DEFAULT_MARKETPLACE_ROOT, registry_root)
    example_source = PROJECT_ROOT / "plugin-templates" / "example-plugin"
    shutil.copytree(example_source, tmp_path / "example-plugin")
    return registry_root


def test_marketplace_discovery_validates_signature_and_dependencies(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    from hephaestus.plugins import PluginRegistry, discover_plugins

    config_path = _write_plugin_config(tmp_path)
    captured = _capture_counters(monkeypatch)

    registry = PluginRegistry()
    discover_plugins(
        config_path=config_path,
        registry_instance=registry,
        marketplace_root=DEFAULT_MARKETPLACE_ROOT,
    )

    plugin = registry.get("example-plugin")
    assert plugin.metadata.version == "1.0.0"

    counter_names = {name for name, _, _ in captured}
    assert "hephaestus.plugins.marketplace.fetch" in counter_names
    assert "hephaestus.plugins.marketplace.verified" in counter_names
    assert "hephaestus.plugins.marketplace.dependencies_resolved" in counter_names


def test_marketplace_version_mismatch_raises(tmp_path: Path) -> None:
    from hephaestus.plugins import PluginRegistry, discover_plugins

    config_path = _write_plugin_config(tmp_path, version="9.9.9")
    registry = PluginRegistry()

    with pytest.raises(ValueError, match="version 9.9.9"):
        discover_plugins(
            config_path=config_path,
            registry_instance=registry,
            marketplace_root=DEFAULT_MARKETPLACE_ROOT,
        )


def test_marketplace_dependency_resolution_blocks_missing_python(tmp_path: Path) -> None:
    from hephaestus.plugins import PluginRegistry, discover_plugins

    registry_root = _copy_registry(tmp_path)

    manifest_path = registry_root / "example-plugin.toml"
    manifest_path.write_text(
        textwrap.dedent(
            """
            [plugin]
            name = "example-plugin"
            version = "1.0.0"
            description = "Example quality gate plugin"
            category = "custom"
            author = "Hephaestus Maintainers"

            [plugin.compatibility]
            hephaestus = ">=0.2.0"
            python = ">=3.12"

                [[plugin.dependencies]]
                type = "python"
                name = "totally-uninstalled-package"
                version = ">=99.0"

                [plugin.entrypoint]
                path = "artifacts/example_plugin.py"

                [plugin.signature]
                bundle = "example-plugin.sigstore"
                """
        ).strip()
        + "\n",
        encoding="utf-8",
    )

    config_path = _write_plugin_config(tmp_path)
    registry = PluginRegistry()

    with pytest.raises(ValueError, match="totally-uninstalled-package"):
        discover_plugins(
            config_path=config_path,
            registry_instance=registry,
            marketplace_root=registry_root,
        )


def test_marketplace_trust_policy_enforced(tmp_path: Path) -> None:
    from hephaestus.plugins import PluginRegistry, discover_plugins

    registry_root = _copy_registry(tmp_path)

    trust_policy = registry_root / "trust-policy.toml"
    trust_policy.write_text(
        textwrap.dedent(
            """
            [trust]
            require_signature = true
            allowed_identities = ["mailto:other@hephaestus.dev"]
            """
        ).strip()
        + "\n",
        encoding="utf-8",
    )

    config_path = _write_plugin_config(tmp_path)
    registry = PluginRegistry()

    with pytest.raises(ValueError, match="trust policy"):
        discover_plugins(
            config_path=config_path,
            registry_instance=registry,
            marketplace_root=registry_root,
        )


def test_marketplace_dependency_resolution_requires_registered_plugins(tmp_path: Path) -> None:
    from hephaestus import plugins as plugins_module

    manifest = plugins_module.MarketplaceManifest(
        name="dependent-plugin",
        version="1.0.0",
        description="",
        author="tester",
        category="custom",
        entry_path=tmp_path / "plugin.py",
        entry_module=None,
        dependencies=(
            plugins_module.MarketplaceDependency(kind="plugin", name="upstream", version=None),
        ),
        hephaestus_spec=None,
        python_spec=None,
        signature_bundle=None,
        manifest_path=tmp_path / "manifest.toml",
    )

    with pytest.raises(ValueError, match="requires plugin 'upstream'"):
        plugins_module._ensure_marketplace_dependencies(
            manifest, resolved_plugins={"dependent-plugin"}
        )

    unsupported = plugins_module.MarketplaceManifest(
        name="unsupported",
        version="1.0.0",
        description="",
        author="tester",
        category="custom",
        entry_path=tmp_path / "plugin.py",
        entry_module=None,
        dependencies=(
            plugins_module.MarketplaceDependency(kind="service", name="external", version="1"),
        ),
        hephaestus_spec=None,
        python_spec=None,
        signature_bundle=None,
        manifest_path=tmp_path / "manifest.toml",
    )

    with pytest.raises(ValueError, match="unsupported dependency type"):
        plugins_module._ensure_marketplace_dependencies(unsupported, resolved_plugins=set())


def test_marketplace_signature_enforcement_covers_required_paths(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    import base64
    import json

    from hephaestus import plugins as plugins_module

    manifest_path = tmp_path / "manifest.toml"
    manifest_path.write_text("{}", encoding="utf-8")

    policy = plugins_module.TrustPolicy(
        require_signature=True, default_identities=(), per_plugin={}
    )
    manifest = plugins_module.MarketplaceManifest(
        name="unsigned",
        version="1.0.0",
        description="",
        author="tester",
        category="custom",
        entry_path=None,
        entry_module="unsigned:main",
        dependencies=(),
        hephaestus_spec=None,
        python_spec=None,
        signature_bundle=None,
        manifest_path=manifest_path,
    )

    captured = _capture_counters(monkeypatch)
    with pytest.raises(ValueError, match="requires a signature"):
        plugins_module._verify_marketplace_signature(manifest, policy)

    counter_names = {name for name, _, _ in captured}
    assert "hephaestus.plugins.marketplace.errors" in counter_names

    plugin_path = tmp_path / "plugin.py"
    plugin_path.write_text("print('hi')\n", encoding="utf-8")

    bundle_path = tmp_path / "bundle.json"
    bundle_payload = {
        "messageSignature": {
            "messageDigest": {
                "algorithm": "sha256",
                "digest": base64.b64encode(b"mismatch").decode("ascii"),
            }
        },
        "verificationMaterial": {"identities": ["mailto:unsigned@example.com"]},
    }
    bundle_path.write_text(json.dumps(bundle_payload), encoding="utf-8")

    manifest_with_bundle = plugins_module.MarketplaceManifest(
        name="unsigned",
        version="1.0.0",
        description="",
        author="tester",
        category="custom",
        entry_path=plugin_path,
        entry_module=None,
        dependencies=(),
        hephaestus_spec=None,
        python_spec=None,
        signature_bundle=bundle_path,
        manifest_path=manifest_path,
    )

    with pytest.raises(ValueError, match="digest mismatch"):
        plugins_module._verify_marketplace_signature(
            manifest_with_bundle,
            plugins_module.TrustPolicy(
                require_signature=False, default_identities=(), per_plugin={}
            ),
        )


def test_marketplace_signature_identity_policy(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    import base64
    import hashlib
    import json

    from hephaestus import plugins as plugins_module

    plugin_path = tmp_path / "plugin.py"
    plugin_path.write_text("print('hello')\n", encoding="utf-8")
    digest = hashlib.sha256(plugin_path.read_bytes()).digest()

    bundle_path = tmp_path / "bundle.json"
    bundle_payload = {
        "messageSignature": {
            "messageDigest": {
                "algorithm": "sha256",
                "digest": base64.b64encode(digest).decode("ascii"),
            }
        },
        "verificationMaterial": {"identities": ["mailto:other@example.com"]},
    }
    bundle_path.write_text(json.dumps(bundle_payload), encoding="utf-8")

    manifest = plugins_module.MarketplaceManifest(
        name="policy-plugin",
        version="1.0.0",
        description="",
        author="tester",
        category="custom",
        entry_path=plugin_path,
        entry_module=None,
        dependencies=(),
        hephaestus_spec=None,
        python_spec=None,
        signature_bundle=bundle_path,
        manifest_path=tmp_path / "manifest.toml",
    )

    policy = plugins_module.TrustPolicy(
        require_signature=True,
        default_identities=("mailto:allowed@example.com",),
        per_plugin={},
    )

    captured = _capture_counters(monkeypatch)
    with pytest.raises(ValueError, match="identity"):
        plugins_module._verify_marketplace_signature(manifest, policy)

    counter_names = {name for name, _, _ in captured}
    assert "hephaestus.plugins.marketplace.errors" in counter_names


def test_marketplace_signature_allows_per_plugin_policy(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    import base64
    import hashlib
    import json

    from hephaestus import plugins as plugins_module

    plugin_path = tmp_path / "plugin.py"
    plugin_path.write_text("print('hello')\n", encoding="utf-8")
    digest = hashlib.sha256(plugin_path.read_bytes()).digest()

    bundle_path = tmp_path / "bundle.json"
    bundle_payload = {
        "messageSignature": {
            "messageDigest": {
                "algorithm": "sha256",
                "digest": base64.b64encode(digest).decode("ascii"),
            }
        },
        "verificationMaterial": {"identities": ["mailto:allowed@example.com"]},
    }
    bundle_path.write_text(json.dumps(bundle_payload), encoding="utf-8")

    manifest = plugins_module.MarketplaceManifest(
        name="policy-plugin",
        version="1.0.0",
        description="",
        author="tester",
        category="custom",
        entry_path=plugin_path,
        entry_module=None,
        dependencies=(),
        hephaestus_spec=None,
        python_spec=None,
        signature_bundle=bundle_path,
        manifest_path=tmp_path / "manifest.toml",
    )

    policy = plugins_module.TrustPolicy(
        require_signature=True,
        default_identities=(),
        per_plugin={"policy-plugin": ("mailto:allowed@example.com",)},
    )

    captured = _capture_counters(monkeypatch)
    plugins_module._verify_marketplace_signature(manifest, policy)

    counter_names = {name for name, _, _ in captured}
    assert "hephaestus.plugins.marketplace.verified" in counter_names


def test_marketplace_python_compatibility_enforced(tmp_path: Path) -> None:
    from hephaestus import plugins as plugins_module

    manifest = plugins_module.MarketplaceManifest(
        name="compatibility-test",
        version="1.0.0",
        description="",
        author="tester",
        category="custom",
        entry_path=tmp_path / "plugin.py",
        entry_module=None,
        dependencies=(),
        hephaestus_spec=None,
        python_spec=">=99.0",
        signature_bundle=None,
        manifest_path=tmp_path / "manifest.toml",
    )

    with pytest.raises(ValueError, match="Python"):
        plugins_module._ensure_marketplace_compatibility(manifest)


def test_marketplace_python_dependency_version_constraints() -> None:
    from hephaestus import plugins as plugins_module

    satisfied = plugins_module.MarketplaceDependency(kind="python", name="pytest", version=">=0")
    plugins_module._ensure_python_dependency(satisfied)

    with pytest.raises(ValueError, match="does not satisfy"):
        plugins_module._ensure_python_dependency(
            plugins_module.MarketplaceDependency(kind="python", name="pytest", version="==0.0.0")
        )

    with pytest.raises(ValueError, match="invalid version constraint"):
        plugins_module._ensure_python_dependency(
            plugins_module.MarketplaceDependency(kind="python", name="pytest", version="not-a-spec")
        )


def test_parse_marketplace_dependency_variants() -> None:
    from hephaestus import plugins as plugins_module

    assert plugins_module._parse_marketplace_dependency("invalid") is None

    parsed = plugins_module._parse_marketplace_dependency(
        {"type": "python", "name": "pytest", "version": ">=0"}
    )
    assert parsed is not None
    assert parsed.kind == "python"
    assert parsed.name == "pytest"


def test_instantiate_marketplace_plugin_from_path() -> None:
    from hephaestus import plugins as plugins_module

    plugin_path = PROJECT_ROOT / "plugin-templates" / "example-plugin" / "example_plugin.py"
    manifest = plugins_module.MarketplaceManifest(
        name="example-plugin",
        version="1.0.0",
        description="Example",
        author="Tester",
        category="custom",
        entry_path=plugin_path,
        entry_module=None,
        dependencies=(),
        hephaestus_spec=None,
        python_spec=None,
        signature_bundle=None,
        manifest_path=plugin_path,
    )

    plugin = plugins_module._instantiate_marketplace_plugin(manifest)
    assert plugin.metadata.name == "example-plugin"


def test_instantiate_marketplace_plugin_validates_metadata(tmp_path: Path) -> None:
    from hephaestus import plugins as plugins_module

    plugin_source = tmp_path / "custom_plugin.py"
    plugin_source.write_text(
        """
from hephaestus.plugins import PluginMetadata, PluginResult, QualityGatePlugin


class CustomPlugin(QualityGatePlugin):
    @property
    def metadata(self) -> PluginMetadata:
        return PluginMetadata(
            name="custom-plugin",
            version="2.0.0",
            description="",
            author="tester",
            category="custom",
            requires=[],
        )

    def validate_config(self, config: dict[str, object]) -> bool:
        return True

    def run(self, config: dict[str, object]) -> PluginResult:
        return PluginResult(success=True, message="ok")
""",
        encoding="utf-8",
    )

    manifest = plugins_module.MarketplaceManifest(
        name="custom-plugin",
        version="1.0.0",
        description="",
        author="tester",
        category="custom",
        entry_path=plugin_source,
        entry_module=None,
        dependencies=(),
        hephaestus_spec=None,
        python_spec=None,
        signature_bundle=None,
        manifest_path=plugin_source,
    )

    with pytest.raises(ValueError, match="version"):
        plugins_module._instantiate_marketplace_plugin(manifest)


def test_plugin_result_with_details() -> None:
    """Test that plugin results can include detailed information."""
    from hephaestus.plugins import PluginResult

    result = PluginResult(
        success=True,
        message="Check passed",
        details={
            "files_checked": 42,
            "violations": 0,
            "duration": 2.5,
        },
        exit_code=0,
    )

    assert result.success is True
    assert result.details is not None
    assert result.details["files_checked"] == 42
    assert result.exit_code == 0
