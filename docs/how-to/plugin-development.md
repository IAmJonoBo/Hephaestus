# Plugin Development Guide (ADR-0002)

**Status**: Phase 2 (Discovery & Configuration) - Discovery implemented

## Overview

Hephaestus supports a plugin architecture for extending quality gates with custom checks. This allows teams to add project-specific quality gates without modifying Hephaestus core.

**Current Implementation Status:**
- ✅ Phase 1: Plugin API specification and registry
- ✅ Phase 2: Built-in plugins and discovery mechanism
- ⏳ Phase 3: Integration with guard-rails command (planned)
- ⏳ Phase 4: Plugin marketplace and advanced features (planned)

## Quick Start

### Example Plugin

```python
from hephaestus.plugins import QualityGatePlugin, PluginMetadata, PluginResult

class MyCustomPlugin(QualityGatePlugin):
    """Example custom quality gate plugin."""

    @property
    def metadata(self) -> PluginMetadata:
        return PluginMetadata(
            name="my-custom-check",
            version="1.0.0",
            description="My custom quality check",
            author="Your Name",
            category="custom",
            requires=[],  # Python dependencies
            order=100,  # Execution order (lower = earlier)
        )

    def validate_config(self, config: dict) -> bool:
        """Validate plugin configuration."""
        # Check that required config keys exist
        return True

    def run(self, config: dict) -> PluginResult:
        """Execute the quality check."""
        # Perform your custom check
        success = True  # Replace with actual logic

        return PluginResult(
            success=success,
            message="Custom check passed",
            details={"files_checked": 42},
            exit_code=0 if success else 1,
        )
```

## Plugin API

### PluginMetadata

Describes your plugin:

```python
@dataclass
class PluginMetadata:
    name: str          # Unique plugin identifier
    version: str       # Semantic version
    description: str   # Human-readable description
    author: str        # Author name
    category: str      # "linting", "testing", "security", "custom"
    requires: list[str]  # Python package dependencies
    order: int = 100   # Execution order (lower runs first)
```

### PluginResult

Returned from `run()` method:

```python
@dataclass
class PluginResult:
    success: bool                # Did the check pass?
    message: str                 # Status message
    details: dict | None = None  # Additional data
    exit_code: int = 0          # Process exit code
```

### QualityGatePlugin

Base class for all plugins:

```python
class QualityGatePlugin(ABC):
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

## Plugin Registry

Register and manage plugins:

```python
from hephaestus.plugins import registry

# Register a plugin
plugin = MyCustomPlugin()
registry.register(plugin)

# Check if registered
if registry.is_registered("my-custom-check"):
    plugin = registry.get("my-custom-check")

# Get all plugins (sorted by order)
all_plugins = registry.all_plugins()
```

## Plugin Configuration

### Configuration File

Plugins can be configured via `.hephaestus/plugins.toml`:

```toml
# Configure built-in plugins
[builtin]
ruff-check = true
ruff-format = { enabled = true, config = { check = true } }
mypy = true
pytest = { enabled = true, config = { min_coverage = 85 } }
pip-audit = { enabled = true, config = { ignore_vulns = ["GHSA-xxx"] } }

# Add external plugins
[[external]]
name = "custom-security-check"
enabled = true
path = "/path/to/custom_plugin.py"
config = { severity = "high" }

[[external]]
name = "org-compliance-check"
enabled = true
module = "myorg.hephaestus_plugins.compliance"
config = { policy_version = "2024.1" }
```

### Plugin Discovery

Load plugins from configuration:

```python
from pathlib import Path
from hephaestus.plugins import discover_plugins, load_plugin_config

# Auto-discover plugins from .hephaestus/plugins.toml
registry = discover_plugins()

# Or specify custom config path
config_path = Path("custom-plugins.toml")
registry = discover_plugins(config_path)

# Just load config without registering
configs = load_plugin_config(config_path)
for config in configs:
    print(f"Plugin: {config.name}, Enabled: {config.enabled}")
```

## Built-in Plugins

Hephaestus includes several built-in quality gate plugins:

1. **ruff-check**: Python linting with Ruff
2. **ruff-format**: Python code formatting with Ruff
3. **mypy**: Static type checking
4. **pytest**: Test execution with coverage
5. **pip-audit**: Security vulnerability scanning

These can be configured individually in `plugins.toml`.

## Creating External Plugins

### File-based Plugin

Create a Python file with your plugin:

```python
# my_custom_plugin.py
from hephaestus.plugins import QualityGatePlugin, PluginMetadata, PluginResult

class SecurityAuditPlugin(QualityGatePlugin):
    """Custom security audit plugin."""

    @property
    def metadata(self) -> PluginMetadata:
        return PluginMetadata(
            name="security-audit",
            version="1.0.0",
            description="Custom security audit for sensitive files",
            author="Security Team",
            category="security",
            requires=["pyyaml"],
            order=90,
        )

    def validate_config(self, config: dict) -> bool:
        """Validate that severity level is specified."""
        severity = config.get("severity", "medium")
        return severity in ["low", "medium", "high", "critical"]

    def run(self, config: dict) -> PluginResult:
        """Run security audit."""
        severity = config.get("severity", "medium")
        
        # Your security check logic here
        issues_found = []
        
        if issues_found:
            return PluginResult(
                success=False,
                message=f"Found {len(issues_found)} security issues",
                details={"issues": issues_found},
                exit_code=1,
            )
        
        return PluginResult(
            success=True,
            message="No security issues found",
            exit_code=0,
        )
```

Reference it in `.hephaestus/plugins.toml`:

```toml
[[external]]
name = "security-audit"
enabled = true
path = "./my_custom_plugin.py"
config = { severity = "high" }
```

### Module-based Plugin

Package your plugin as a Python module:

```python
# myorg/hephaestus_plugins/compliance.py
from hephaestus.plugins import QualityGatePlugin, PluginMetadata, PluginResult

class CompliancePlugin(QualityGatePlugin):
    @property
    def metadata(self) -> PluginMetadata:
        return PluginMetadata(
            name="org-compliance",
            version="1.0.0",
            description="Organization compliance checks",
            author="Compliance Team",
            category="custom",
            requires=["requests"],
            order=95,
        )

    def validate_config(self, config: dict) -> bool:
        return "policy_version" in config

    def run(self, config: dict) -> PluginResult:
        policy_version = config["policy_version"]
        
        # Your compliance check logic
        compliant = True
        
        return PluginResult(
            success=compliant,
            message=f"Compliance check passed (policy {policy_version})",
            exit_code=0 if compliant else 1,
        )
```

Install and configure:

```bash
pip install myorg-hephaestus-plugins
```

```toml
[[external]]
name = "org-compliance"
enabled = true
module = "myorg.hephaestus_plugins.compliance"
config = { policy_version = "2024.1" }
```

## Current Limitations

Phase 2 implementation provides:

- ✅ Plugin API specification
- ✅ Base classes and interfaces
- ✅ Plugin registry
- ✅ Plugin discovery from configuration files
- ✅ Built-in plugins (ruff, mypy, pytest, pip-audit)
- ✅ External plugin loading (file-based and module-based)
- ❌ Not yet: Direct integration with guard-rails command
- ❌ Not yet: Plugin dependency resolution
- ❌ Not yet: Plugin marketplace

## Future Phases

- **Phase 3** (Sprint 3): 
  - Integration with guard-rails command
  - Example plugin templates
  - Plugin catalog documentation
  
- **Phase 4** (Sprint 4): 
  - Plugin marketplace/registry
  - Plugin versioning
  - Dependency resolution
  - Advanced plugin features

## Testing Plugins

### Unit Testing

```python
import pytest
from your_plugin import MyCustomPlugin
from hephaestus.plugins import PluginResult

def test_plugin_metadata():
    """Test plugin metadata is correctly defined."""
    plugin = MyCustomPlugin()
    metadata = plugin.metadata
    
    assert metadata.name == "my-custom-check"
    assert metadata.version == "1.0.0"
    assert metadata.category == "custom"

def test_plugin_validates_config():
    """Test configuration validation."""
    plugin = MyCustomPlugin()
    
    valid_config = {"severity": "high"}
    assert plugin.validate_config(valid_config) is True
    
    invalid_config = {"severity": "invalid"}
    assert plugin.validate_config(invalid_config) is False

def test_plugin_execution():
    """Test plugin runs successfully."""
    plugin = MyCustomPlugin()
    config = {"severity": "medium"}
    
    result = plugin.run(config)
    
    assert isinstance(result, PluginResult)
    assert result.success in [True, False]
    assert isinstance(result.message, str)
    assert isinstance(result.exit_code, int)
```

### Integration Testing

```python
from hephaestus.plugins import discover_plugins, PluginRegistry
from pathlib import Path

def test_plugin_discovery(tmp_path):
    """Test plugin is discovered from config."""
    # Create plugin file
    plugin_file = tmp_path / "custom_plugin.py"
    plugin_file.write_text("""
from hephaestus.plugins import QualityGatePlugin, PluginMetadata, PluginResult

class TestPlugin(QualityGatePlugin):
    @property
    def metadata(self):
        return PluginMetadata(
            name="test-plugin",
            version="1.0.0",
            description="Test",
            author="Test",
            category="custom",
            requires=[],
        )
    
    def validate_config(self, config):
        return True
    
    def run(self, config):
        return PluginResult(success=True, message="Test passed")
""")
    
    # Create config
    config_file = tmp_path / "plugins.toml"
    config_file.write_text(f"""
[[external]]
name = "test-plugin"
enabled = true
path = "{plugin_file}"
""")
    
    # Discover plugins
    registry = PluginRegistry()
    discover_plugins(config_file, registry)
    
    # Verify plugin is registered
    assert registry.is_registered("test-plugin")
    plugin = registry.get("test-plugin")
    
    # Test execution
    result = plugin.run({})
    assert result.success is True
```

## Best Practices

1. **Keep plugins focused**: One check per plugin
2. **Use descriptive names**: Clear, unique plugin names
3. **Validate configuration**: Check all required config in `validate_config()`
4. **Handle errors gracefully**: Catch exceptions and return failed result
5. **Document thoroughly**: Clear docstrings and metadata
6. **Test extensively**: Unit tests for all plugin functionality

## Related Documentation

- [ADR-0002: Plugin Architecture](../adr/0002-plugin-architecture.md)
- [Quality Gates Guide](quality-gates.md)
- [Architecture Overview](../explanation/architecture.md)
