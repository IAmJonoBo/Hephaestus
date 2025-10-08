"""Tests for command schema export."""

from __future__ import annotations

import json
from typing import Annotated

import typer

from hephaestus.schema import CommandSchema, extract_command_schemas


def test_extract_command_schemas_basic() -> None:
    """Test extracting schemas from a simple Typer app."""
    app = typer.Typer()

    @app.command()
    def hello(name: str) -> None:
        """Say hello to someone."""
        typer.echo(f"Hello {name}")

    schemas = extract_command_schemas(app)

    assert len(schemas) == 1
    assert schemas[0].name == "hello"
    assert schemas[0].help == "Say hello to someone."
    assert len(schemas[0].parameters) == 1
    assert schemas[0].parameters[0].name == "name"


def test_extract_command_schemas_with_options() -> None:
    """Test extracting schemas with optional parameters."""
    app = typer.Typer()

    @app.command()
    def greet(
        name: Annotated[str, typer.Argument(help="Name to greet")],
        formal: Annotated[bool, typer.Option(help="Use formal greeting")] = False,
    ) -> None:
        """Greet someone."""
        pass

    schemas = extract_command_schemas(app)

    assert len(schemas) == 1
    assert len(schemas[0].parameters) == 2

    name_param = schemas[0].parameters[0]
    assert name_param.name == "name"
    assert name_param.help == "Name to greet"

    formal_param = schemas[0].parameters[1]
    assert formal_param.name == "formal"
    assert formal_param.help == "Use formal greeting"
    assert formal_param.default is False


def test_extract_command_schemas_nested_groups() -> None:
    """Test extracting schemas from nested command groups."""
    app = typer.Typer()
    tools_app = typer.Typer()

    @tools_app.command()
    def analyze() -> None:
        """Analyze the code."""
        pass

    app.add_typer(tools_app, name="tools")

    schemas = extract_command_schemas(app)

    # Should extract the nested command
    assert len(schemas) >= 1
    analyze_cmd = next((s for s in schemas if "analyze" in s.name), None)
    assert analyze_cmd is not None
    assert analyze_cmd.parent == "tools"


def test_command_schema_metadata_cleanup() -> None:
    """Test that cleanup command gets proper metadata."""
    from hephaestus.schema import _add_command_metadata

    schema = CommandSchema(name="cleanup", help="Clean workspace")
    _add_command_metadata(schema)

    assert len(schema.examples) > 0
    assert "hephaestus cleanup" in schema.examples
    assert schema.expected_output is not None
    assert len(schema.retry_hints) > 0


def test_command_schema_metadata_guard_rails() -> None:
    """Test that guard-rails command gets proper metadata."""
    from hephaestus.schema import _add_command_metadata

    schema = CommandSchema(name="guard-rails", help="Run guard rails")
    _add_command_metadata(schema)

    assert len(schema.examples) > 0
    assert any("guard-rails" in ex for ex in schema.examples)
    assert schema.expected_output is not None


def test_command_schema_metadata_rankings() -> None:
    """Test that rankings command gets proper metadata."""
    from hephaestus.schema import _add_command_metadata

    schema = CommandSchema(name="tools refactor rankings", help="Rank modules")
    _add_command_metadata(schema)

    assert len(schema.examples) > 0
    assert any("rankings" in ex for ex in schema.examples)
    assert "analytics" in schema.retry_hints[0].lower()


def test_command_registry_to_json() -> None:
    """Test converting command registry to JSON."""
    from hephaestus.schema import CommandRegistry

    registry = CommandRegistry()
    registry.commands = [
        CommandSchema(
            name="test",
            help="Test command",
            examples=["hephaestus test"],
        )
    ]

    json_dict = registry.to_json_dict()

    assert "version" in json_dict
    assert "commands" in json_dict
    assert len(json_dict["commands"]) == 1
    assert json_dict["commands"][0]["name"] == "test"

    # Should be JSON-serializable
    json_str = json.dumps(json_dict)
    assert "test" in json_str
