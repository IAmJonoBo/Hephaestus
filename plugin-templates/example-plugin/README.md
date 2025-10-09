# Example Plugin Template for Hephaestus

This template demonstrates how to create a custom quality gate plugin for Hephaestus.

## Quick Start

1. Copy this template directory to your project
2. Rename `example_plugin.py` to match your plugin name
3. Update the plugin metadata and implementation
4. Add your plugin to `.hephaestus/plugins.toml`
5. Test with `hephaestus guard-rails --use-plugins`

## Structure

```text
example-plugin/
├── README.md                 # This file
├── example_plugin.py         # Plugin implementation
├── test_example_plugin.py    # Plugin tests
├── pyproject.toml            # Dependencies (optional)
└── plugins.toml.example      # Example configuration
```

## Usage

### File-based Plugin

Add to `.hephaestus/plugins.toml`:

```toml
[[external]]
name = "example-plugin"
enabled = true
path = "path/to/example_plugin.py"
config = { severity = "high" }
```

### Module-based Plugin (installed package)

```toml
[[external]]
name = "example-plugin"
enabled = true
module = "my_package.example_plugin"
config = { severity = "high" }
```

## Development

1. **Test your plugin**:

   ```bash
   pytest test_example_plugin.py
   ```

2. **Run with Hephaestus**:

   ```bash
   hephaestus guard-rails --use-plugins
   ```

3. **Lint and format**:

   ```bash
   ruff check example_plugin.py
   ruff format example_plugin.py
   ```

## Plugin Requirements

- Must inherit from `QualityGatePlugin`
- Must implement `metadata`, `validate_config`, and `run` methods
- Should handle errors gracefully
- Should return meaningful `PluginResult` objects

## Publishing

To share your plugin:

1. Package as a Python module
2. Publish to PyPI or private repository
3. Document configuration options
4. Add examples and tests

## Support

- [Plugin Development Guide](../../docs/how-to/plugin-development.md)
- [ADR-0002: Plugin Architecture](../../docs/adr/0002-plugin-architecture.md)
- [Plugin API Reference](../../docs/reference/plugins.md)
