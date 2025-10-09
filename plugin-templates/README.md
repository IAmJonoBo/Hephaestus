# Hephaestus Plugin Templates

This directory contains templates and examples for creating custom quality gate plugins for Hephaestus.

## Overview

The plugin architecture (ADR-0002) enables teams to extend Hephaestus with custom quality checks without modifying the core codebase. These templates provide a starting point for plugin development.

## Available Templates

### [example-plugin/](example-plugin/)

A complete, production-ready example plugin demonstrating best practices:

- **Full implementation** of the `QualityGatePlugin` interface
- **Comprehensive tests** (94% coverage)
- **Configuration validation** with clear error messages
- **Error handling** for timeouts, missing tools, and edge cases
- **Documentation** including README, examples, and inline comments
- **Packaging** setup with pyproject.toml

## Quick Start

1. **Copy the template**:
   ```bash
   cp -r plugin-templates/example-plugin my-custom-plugin
   cd my-custom-plugin
   ```

2. **Customize the plugin**:
   - Rename `example_plugin.py` to match your plugin
   - Update metadata (name, version, description, author)
   - Implement your quality check logic in the `run` method
   - Update configuration validation in `validate_config`

3. **Write tests**:
   ```bash
   pytest test_example_plugin.py -v --cov
   ```

4. **Use with Hephaestus**:
   
   Add to `.hephaestus/plugins.toml`:
   ```toml
   [[external]]
   name = "my-custom-plugin"
   enabled = true
   path = "path/to/my_custom_plugin.py"
   config = { option1 = "value1" }
   ```

   Run with guard-rails:
   ```bash
   hephaestus guard-rails --use-plugins
   ```

## Plugin Development Guide

For detailed guidance on plugin development, see:

- [Plugin Development Guide](../docs/how-to/plugin-development.md)
- [Plugin API Reference](../docs/reference/plugin-catalog.md)
- [ADR-0002: Plugin Architecture](../docs/adr/0002-plugin-architecture.md)

## Plugin Requirements

All plugins must:

1. **Inherit from `QualityGatePlugin`**
2. **Implement required methods**:
   - `metadata` property (returns `PluginMetadata`)
   - `validate_config(config)` method
   - `run(config)` method (returns `PluginResult`)
3. **Handle errors gracefully**
4. **Include comprehensive tests** (>80% coverage)
5. **Document configuration options**

## Sharing Your Plugin

To share your plugin with the community:

1. Package it as a Python module
2. Publish to PyPI or a private repository
3. Submit to the [Plugin Catalog](../docs/reference/plugin-catalog.md)
4. Follow the [Plugin Review Process](../docs/how-to/plugin-review-process.md)

## Examples

### File-based Plugin

For simple plugins or prototypes:

```toml
[[external]]
name = "my-plugin"
enabled = true
path = "plugins/my_plugin.py"
config = { severity = "high" }
```

### Module-based Plugin

For packaged, installable plugins:

```toml
[[external]]
name = "org-compliance"
enabled = true
module = "myorg.hephaestus_plugins.compliance"
config = { policy_version = "2024.1" }
```

## Testing

Test your plugin before using it in production:

```bash
# Run unit tests
pytest test_my_plugin.py -v --cov

# Test with Hephaestus (dry run)
hephaestus guard-rails --use-plugins

# Lint and format
ruff check my_plugin.py
ruff format my_plugin.py

# Type check
mypy my_plugin.py
```

## Support

- **Documentation**: [Plugin Development Guide](../docs/how-to/plugin-development.md)
- **Issues**: [GitHub Issues](https://github.com/IAmJonoBo/Hephaestus/issues)
- **Discussions**: [GitHub Discussions](https://github.com/IAmJonoBo/Hephaestus/discussions)

## License

Plugin templates are provided under the same license as Hephaestus (MIT).
Your plugins can use any license you choose.
