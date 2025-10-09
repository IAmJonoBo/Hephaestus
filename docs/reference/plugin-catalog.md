# Plugin Catalog

This document catalogs available Hephaestus quality gate plugins, both built-in and community-developed.

## Built-in Plugins

These plugins are included with Hephaestus and available by default when using `--use-plugins`.

### ruff-check

**Category**: Linting  
**Version**: 1.0.0  
**Execution Order**: 10 (early)

Python linting with Ruff. Fast and comprehensive linting for Python code.

**Configuration**:
```toml
[builtin.ruff-check]
enabled = true
config.paths = ["."]
config.args = ["--select", "E,F,W,I,N,B,UP"]
```

**Requirements**: `ruff>=0.8.0`

---

### ruff-format

**Category**: Formatting  
**Version**: 1.0.0  
**Execution Order**: 20

Code formatting check with Ruff. Ensures consistent code style.

**Configuration**:
```toml
[builtin.ruff-format]
enabled = true
config.check = true  # Check mode (don't modify files)
config.paths = ["."]
```

**Requirements**: `ruff>=0.8.0`

---

### mypy

**Category**: Type Checking  
**Version**: 1.0.0  
**Execution Order**: 30

Static type checking with Mypy. Catches type errors before runtime.

**Configuration**:
```toml
[builtin.mypy]
enabled = true
config.paths = ["src", "tests"]
config.args = ["--strict"]
```

**Requirements**: `mypy>=1.14.0`

---

### pytest

**Category**: Testing  
**Version**: 1.0.0  
**Execution Order**: 40

Test execution with pytest and coverage reporting.

**Configuration**:
```toml
[builtin.pytest]
enabled = true
config.min_coverage = 85.0
config.args = ["--cov=src", "--cov-report=xml"]
```

**Requirements**: `pytest>=8.0.0`, `pytest-cov>=7.0.0`

---

### pip-audit

**Category**: Security  
**Version**: 1.0.0  
**Execution Order**: 50 (late)

Security audit of Python dependencies. Checks for known vulnerabilities.

**Configuration**:
```toml
[builtin.pip-audit]
enabled = true
config.args = ["--strict"]
config.ignore_vulns = ["GHSA-4xh5-x5gv-qwph"]
```

**Requirements**: `pip-audit>=2.9.0`

---

## Community Plugins

Community-developed plugins that extend Hephaestus functionality.

> **Note**: Community plugins are maintained by third parties. Review plugin code and dependencies before use.

### Example Plugin Template

**Category**: Custom  
**Author**: Hephaestus Team  
**Version**: 1.0.0  
**Repository**: [plugin-templates/example-plugin](../../../plugin-templates/example-plugin/)

Template for creating custom quality gate plugins. Demonstrates best practices and includes comprehensive tests.

**Usage**:
```toml
[[external]]
name = "example-plugin"
enabled = true
path = "plugin-templates/example-plugin/example_plugin.py"
config.severity = "high"
```

---

## Plugin Categories

Plugins are organized into the following categories:

- **linting**: Code quality and style checks
- **formatting**: Code formatting verification
- **type-checking**: Static type analysis
- **testing**: Test execution and coverage
- **security**: Security scanning and vulnerability detection
- **custom**: Custom quality checks

## Contributing Plugins

Want to add your plugin to this catalog? See:

1. [Plugin Development Guide](../how-to/plugin-development.md)
2. [Plugin Review Process](../how-to/plugin-review-process.md)
3. Submit a pull request with your plugin details

## Plugin Requirements

To be listed in this catalog, plugins must:

1. Follow the [QualityGatePlugin API](../how-to/plugin-development.md#plugin-api)
2. Include comprehensive tests
3. Have clear documentation
4. Specify all dependencies
5. Follow semantic versioning
6. Be actively maintained

## Support

- Report issues with built-in plugins: [GitHub Issues](https://github.com/IAmJonoBo/Hephaestus/issues)
- For community plugins: Contact the plugin author
- General plugin development: [Plugin Development Guide](../how-to/plugin-development.md)
