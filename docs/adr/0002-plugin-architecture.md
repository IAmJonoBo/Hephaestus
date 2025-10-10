# ADR 0002: Plugin Architecture for Extensible Quality Gates

- Status: Sprint 3 Complete (2025-10-09)
- Date: 2025-01-11
- Last Updated: 2025-10-09
- Supersedes: N/A
- Superseded by: N/A

## Context

Hephaestus currently has a fixed set of quality gates (linting, formatting, type checking, testing, security audit) hard-coded into the `guard-rails` command and validation scripts. Different projects have different needs:

- Some teams want to add custom checks (e.g., SAST tools, contract testing, performance benchmarks)
- Others want to disable certain checks for specific workflows
- Integration with proprietary or organization-specific tooling is currently impossible
- The current approach requires code changes to add new quality gates

This limits Hephaestus's applicability across diverse projects and prevents teams from tailoring quality enforcement to their specific needs without forking the project.

### Motivating Use Cases

1. **Custom Security Scanning**: Teams want to integrate tools like Bandit, Safety, or proprietary security scanners
2. **Contract Testing**: API teams want to validate OpenAPI specs or GraphQL schemas as quality gates
3. **Performance Gates**: Some teams need performance regression detection in their quality pipeline
4. **Documentation Checks**: Teams want to enforce documentation standards (Markdown linting, spell checking)
5. **Custom Metrics**: Organizations want to enforce custom quality metrics (complexity thresholds, dependency rules)

### Current Limitations

- Adding a new quality gate requires modifying `validate_quality_gates.py` or `cli.py`
- No way to disable gates conditionally
- No extension points for custom logic
- Configuration is limited to command-line flags
- No way to share custom gates across projects

## Decision

We will implement a **plugin architecture** that allows declarative registration of custom quality gates through a combination of:

1. **Plugin Discovery System**: Plugins discovered via entry points or configuration files
2. **Plugin API**: Well-defined interface for quality gates with lifecycle hooks
3. **Configuration Schema**: YAML/TOML-based plugin configuration with validation
4. **Plugin Manifest**: Metadata about requirements, dependencies, and execution order

### Architecture

```
hephaestus/
├── src/hephaestus/
│   ├── plugins/
│   │   ├── __init__.py           # Plugin loader and registry
│   │   ├── base.py                # QualityGatePlugin base class
│   │   ├── builtin/               # Built-in plugins
│   │   │   ├── ruff_plugin.py     # Ruff linting
│   │   │   ├── mypy_plugin.py     # Type checking
│   │   │   ├── pytest_plugin.py   # Testing
│   │   │   └── ...
│   │   └── discovery.py           # Plugin discovery mechanism
│   └── cli.py                     # Uses plugin registry

plugins/                           # External plugins directory
├── bandit_plugin.py               # Example custom plugin
└── docs_plugin.py                 # Example docs plugin
```

### Plugin Interface

```python
from abc import ABC, abstractmethod
from dataclasses import dataclass
from typing import Optional

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
    details: Optional[dict] = None
    exit_code: int = 0

class QualityGatePlugin(ABC):
    """Base class for quality gate plugins."""

    @property
    @abstractmethod
    def metadata(self) -> PluginMetadata:
        """Return plugin metadata."""
        pass

    @abstractmethod
    def validate_config(self, config: dict) -> bool:
        """Validate plugin configuration."""
        pass

    @abstractmethod
    def run(self, config: dict) -> PluginResult:
        """Execute the quality gate check."""
        pass

    def setup(self) -> None:
        """Optional: Setup before running."""
        pass

    def teardown(self) -> None:
        """Optional: Cleanup after running."""
        pass
```

### Configuration Format

```yaml
# .hephaestus/plugins.yaml
plugins:
  # Built-in plugins (always available)
  builtin:
    - name: ruff
      enabled: true
      config:
        args: ["check", "."]

    - name: mypy
      enabled: true
      config:
        args: ["src", "tests"]

    - name: pytest
      enabled: true
      config:
        args: ["--cov=src", "--cov-report=xml"]

  # External plugins
  external:
    - name: bandit
      path: plugins/bandit_plugin.py
      enabled: true
      config:
        severity: medium
        confidence: high

    - name: docs-check
      package: hephaestus-docs-plugin
      enabled: true
      config:
        spell_check: true
        broken_links: true

  marketplace:
    - name: example-plugin
      version: "1.0.0"
      registry: "default"
      enabled: true
      config:
        severity: high
```

#### Marketplace Schema and Trust Policies

Phase 4 introduces a curated marketplace that ships signed manifests, dependency metadata, and a
trust policy so operators can consume community plugins safely.

- **Manifests** live under `plugin-templates/registry/*.toml`
- **Sigstore bundles** capture artefact digests in `plugin-templates/registry/*.sigstore`
- **Trust policies** are encoded in `plugin-templates/registry/trust-policy.toml`

Example manifest:

```toml
[plugin]
name = "example-plugin"
version = "1.0.0"
description = "Example quality gate plugin shipped via the marketplace registry."
category = "custom"
author = "Hephaestus Maintainers"

[plugin.compatibility]
hephaestus = ">=0.2.0"
python = ">=3.12"

[[plugin.dependencies]]
type = "plugin"
name = "ruff-check"
version = ">=0.1.0"

[[plugin.dependencies]]
type = "python"
name = "pytest"
version = ">=8.0"

[plugin.entrypoint]
path = "../example-plugin/example_plugin.py"

[plugin.signature]
bundle = "example-plugin.sigstore"
```

Trust policy excerpt:

```toml
[trust]
require_signature = true
allowed_identities = ["mailto:plugins@hephaestus.dev"]

[trust.plugins.example-plugin]
allowed_identities = ["mailto:plugins@hephaestus.dev"]
```

**Guarantees**:

1. **Version pinning** – requested versions must match the curated manifest and plugin metadata.
2. **Compatibility gates** – manifests express supported Hephaestus and Python ranges enforced at
   load time.
3. **Dependency resolution** – plugin and Python dependencies are resolved with
   `packaging.SpecifierSet` validation before registration.
4. **Signature verification** – Sigstore bundles must match the plugin artefact digest and trusted
   identities from the policy.
5. **Telemetry** – discovery emits `hephaestus.plugins.marketplace.{fetch,verified,dependencies_resolved,registered,errors}`
   counters for operational insight.

### Plugin Discovery

1. **Entry Points**: Plugins can register via setuptools entry points
2. **Configuration File**: Plugins defined in `.hephaestus/plugins.yaml`
3. **Environment Variable**: `HEPHAESTUS_PLUGIN_PATH` for custom plugin directories

### Execution Flow

```python
# Simplified example
def run_quality_gates(config_path: str) -> bool:
    # Load configuration
    config = load_plugin_config(config_path)

    # Discover and load plugins
    plugins = discover_plugins(config)

    # Validate plugins
    for plugin in plugins:
        if not plugin.validate_config(config.get(plugin.name, {})):
            raise ValueError(f"Invalid config for {plugin.name}")

    # Sort by execution order
    plugins.sort(key=lambda p: p.metadata.order)

    # Execute plugins
    results = []
    for plugin in plugins:
        if not config.is_enabled(plugin.name):
            continue

        plugin.setup()
        result = plugin.run(config.get(plugin.name, {}))
        plugin.teardown()
        results.append(result)

    # Aggregate results
    return all(r.success for r in results)
```

## Consequences

### Positive

1. **Extensibility**: Teams can add custom quality gates without modifying Hephaestus
2. **Reusability**: Plugins can be shared across projects and organizations
3. **Flexibility**: Each project can enable/disable gates as needed
4. **Standardization**: Common interface encourages consistent quality gate implementations
5. **Backward Compatibility**: Existing functionality becomes built-in plugins
6. **Ecosystem Growth**: Third-party plugins can extend Hephaestus capabilities

### Negative

1. **Complexity**: Plugin system adds architectural complexity
2. **Maintenance Burden**: Need to maintain stable plugin API across versions
3. **Documentation**: Requires comprehensive plugin development guide
4. **Testing**: Need to test plugin discovery, loading, and execution
5. **Migration**: Existing code needs refactoring to plugin architecture
6. **Security**: Plugins execute arbitrary code, need sandboxing/review process

### Risks

- **Breaking Changes**: Plugin API changes could break third-party plugins
- **Performance**: Plugin discovery and loading adds overhead
- **Security**: Malicious plugins could compromise security
- **Compatibility**: Plugin dependencies might conflict with Hephaestus dependencies

### Mitigation Strategies

1. **API Versioning**: Use semantic versioning for plugin API, maintain compatibility
2. **Plugin Validation**: Validate plugins before execution (checksums, signatures)
3. **Sandboxing**: Run plugins in isolated environments (future enhancement)
4. **Documentation**: Comprehensive plugin development guide and examples
5. **Testing**: Extensive test suite for plugin system
6. **Review Process**: Guidelines for reviewing third-party plugins

## Alternatives Considered

### 1. Configuration-Only Approach

**Description**: Allow custom commands via YAML configuration without Python plugins.

**Pros:**

- Simpler to implement
- No security concerns with arbitrary code execution
- Easier to configure

**Cons:**

- Limited to shell commands
- No access to Hephaestus internals
- Difficult to implement complex logic

**Why not chosen:** Too limiting for complex use cases requiring programmatic access.

### 2. Git Hooks Only

**Description**: Let teams use git hooks for custom quality gates.

**Pros:**

- No changes needed to Hephaestus
- Standard mechanism

**Cons:**

- Not integrated with guard-rails workflow
- No unified reporting
- Harder to share across projects

**Why not chosen:** Doesn't solve the integration problem, just pushes it elsewhere.

### 3. Fork and Customize

**Description**: Let teams fork Hephaestus and add custom gates.

**Pros:**

- Full control
- No plugin complexity

**Cons:**

- Maintenance burden
- Difficult to merge upstream changes
- Not reusable

**Why not chosen:** Doesn't scale, contradicts open-source best practices.

### 4. Webhook-Based Extension

**Description**: Call out to HTTP endpoints for custom checks.

**Pros:**

- Language agnostic
- Network-based isolation

**Cons:**

- Requires running services
- Network overhead
- Complex setup

**Why not chosen:** Too heavyweight for simple use cases, adds operational complexity.

## Implementation Plan

### Sprint 1: Foundation (Complete)

- [x] Design plugin API interface
- [x] Implement plugin base class
- [x] Create plugin registry
- [x] Add configuration schema
- [x] Write comprehensive tests

### Sprint 2: Migration & Discovery (Complete)

- [x] Refactor existing gates to plugins (built-in plugins implemented)
- [x] Implement plugin discovery (discovery mechanism complete with file and module loading)
- [x] Add plugin validation (configuration validation and plugin loading implemented)
- [x] Update guard-rails to use plugin system (experimental --use-plugins flag added in Sprint 3)
- [x] Maintain backward compatibility (built-in plugins available, standard mode remains default)

**Sprint 2 Status**: Discovery and configuration loading complete. Guard-rails integration completed in Sprint 3 with experimental flag for gradual adoption.

### Sprint 3: Ecosystem Development (Complete)

- [x] Document plugin development (comprehensive guide updated with Phase 2 features)
- [x] Create example plugins (examples added to documentation)
- [x] Integrate plugin system with guard-rails command (experimental --use-plugins flag implemented)
- [x] Publish plugin template (example plugin template created in plugin-templates/)
- [x] Build plugin catalog (catalog documentation created in docs/reference/)
- [x] Establish review process (review process documented in docs/how-to/)

**Sprint 3 Status**: Complete. Full plugin ecosystem established with guard-rails integration, example templates, catalog documentation, and review process. Users can opt-in to plugin-based execution with `--use-plugins` flag. Standard pipeline remains default for backward compatibility.

### Sprint 4: Advanced Features

- [ ] Add plugin dependency resolution
- [ ] Implement plugin versioning
- [ ] Add plugin marketplace/registry
- [ ] Sandbox plugin execution
- [ ] Add telemetry for plugin usage

## Follow-up Actions

- [x] Create plugin API design document (documented in ADR and development guide)
- [x] Implement plugin base class and registry (src/hephaestus/plugins/)
- [x] Refactor existing gates to plugins (built-in plugins in src/hephaestus/plugins/builtin/)
- [x] Write plugin development guide (docs/how-to/plugin-development.md)
- [x] Create example plugins and template (plugin-templates/example-plugin/)
- [x] Build plugin catalog (docs/reference/plugin-catalog.md)
- [x] Document review process (docs/how-to/plugin-review-process.md)

## References

- [Hephaestus Architecture](../explanation/architecture.md)
- [Quality Gates Guide](../how-to/quality-gates.md)
- [Plugin Development Guide](../how-to/plugin-development.md)
- [Plugin Catalog](../reference/plugin-catalog.md)
- [Plugin Review Process](../how-to/plugin-review-process.md)
- [Example Plugin Template](https://github.com/IAmJonoBo/Hephaestus/tree/main/plugin-templates/example-plugin/)
- [pytest plugin architecture](https://docs.pytest.org/en/stable/how-to/writing_plugins.html)
- [pre-commit hooks architecture](https://pre-commit.com/#creating-new-hooks)

## Appendix: Example Plugin

```python
# plugins/bandit_plugin.py
from hephaestus.plugins.base import QualityGatePlugin, PluginMetadata, PluginResult
import subprocess

class BanditPlugin(QualityGatePlugin):
    """Security linting with Bandit."""

    @property
    def metadata(self) -> PluginMetadata:
        return PluginMetadata(
            name="bandit",
            version="1.0.0",
            description="Security linting for Python code",
            author="Hephaestus Team",
            category="security",
            requires=["bandit>=1.7.0"],
            order=150,  # Run after linting
        )

    def validate_config(self, config: dict) -> bool:
        # Validate configuration
        severity = config.get("severity", "low")
        return severity in ["low", "medium", "high"]

    def run(self, config: dict) -> PluginResult:
        # Run bandit
        cmd = ["bandit", "-r", "src"]

        if "severity" in config:
            cmd.extend(["-ll", config["severity"]])

        try:
            result = subprocess.run(
                cmd,
                capture_output=True,
                text=True,
                check=False,
            )

            return PluginResult(
                success=result.returncode == 0,
                message=f"Bandit: {result.returncode == 0 and 'passed' or 'failed'}",
                details={"stdout": result.stdout, "stderr": result.stderr},
                exit_code=result.returncode,
            )
        except FileNotFoundError:
            return PluginResult(
                success=False,
                message="Bandit not installed",
                exit_code=127,
            )
```

## Status History

- 2025-01-11: Proposed (documented in ADR)
- 2025-10-09: Sprint 1 Complete - Foundation implemented
- 2025-10-09: Sprint 2 Complete - Built-in plugins and discovery implemented
- 2025-10-09: Sprint 3 Complete - Full ecosystem with guard-rails integration, templates, catalog, and review process
- Future: Sprint 4 - Advanced features (dependency resolution, versioning, marketplace)
