# Plugin Development Guide (ADR-0002)

**Status**: Phase 1 (Foundation) - API specification only

## Overview

Hephaestus supports a plugin architecture for extending quality gates with custom checks. This allows teams to add project-specific quality gates without modifying Hephaestus core.

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

## Phase 1 Limitations

Current Phase 1 implementation provides:
- ✅ Plugin API specification
- ✅ Base classes and interfaces
- ✅ Plugin registry
- ❌ Not yet: Plugin discovery
- ❌ Not yet: Configuration file support
- ❌ Not yet: Built-in plugins
- ❌ Not yet: Integration with guard-rails command

## Future Phases

- **Phase 2** (v0.4.0): Refactor existing gates to plugins, add discovery
- **Phase 3** (v0.5.0): Plugin catalog, example plugins, documentation
- **Phase 4** (v0.6.0): Marketplace, versioning, dependency resolution

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
