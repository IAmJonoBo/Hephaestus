"""Command schema export for AI agent integration."""

from __future__ import annotations

import inspect
from dataclasses import dataclass, field
from typing import Any, get_type_hints

import typer
from pydantic import BaseModel, Field


class ParameterSchema(BaseModel):
    """Schema for a command parameter."""

    name: str
    type: str
    required: bool = False
    default: Any | None = None
    help: str | None = None
    choices: list[str] | None = None


class CommandSchema(BaseModel):
    """Schema describing a CLI command for AI agents."""

    name: str
    help: str | None = None
    parameters: list[ParameterSchema] = Field(default_factory=list)
    parent: str | None = None
    examples: list[str] = Field(default_factory=list)
    expected_output: str | None = None
    retry_hints: list[str] = Field(default_factory=list)


@dataclass
class CommandRegistry:
    """Registry of all available commands with metadata."""

    commands: list[CommandSchema] = field(default_factory=list)

    def to_json_dict(self) -> dict[str, Any]:
        """Export registry as JSON-serializable dictionary."""
        return {
            "version": "1.0",
            "commands": [cmd.model_dump() for cmd in self.commands],
        }


def extract_command_schemas(app: typer.Typer, parent: str | None = None) -> list[CommandSchema]:
    """Extract command schemas from a Typer application.

    Args:
        app: Typer application to extract schemas from
        parent: Parent command name for nested commands

    Returns:
        List of command schemas with metadata for AI agents
    """
    schemas: list[CommandSchema] = []

    # Extract registered commands
    if hasattr(app, "registered_commands"):
        for command_info in app.registered_commands:
            command = command_info.callback
            if command is None:
                continue

            command_name = command_info.name or command.__name__.replace("_", "-")
            full_name = f"{parent} {command_name}" if parent else command_name

            # Extract docstring
            help_text = inspect.getdoc(command)

            # Extract parameters
            parameters = _extract_parameters(command, command_info)

            # Create schema
            schema = CommandSchema(
                name=full_name,
                help=help_text,
                parameters=parameters,
                parent=parent,
            )

            # Add command-specific metadata
            _add_command_metadata(schema)

            schemas.append(schema)

    # Extract registered groups
    if hasattr(app, "registered_groups"):
        for group_info in app.registered_groups:
            group_app = group_info.typer_instance
            group_name = group_info.name
            full_group_name = f"{parent} {group_name}" if parent else group_name

            # Recursively extract subcommands
            sub_schemas = extract_command_schemas(group_app, parent=full_group_name)
            schemas.extend(sub_schemas)

    return schemas


def _extract_parameters(command: Any, command_info: Any) -> list[ParameterSchema]:
    """Extract parameter schemas from a command function."""
    parameters: list[ParameterSchema] = []

    # Get function signature
    try:
        sig = inspect.signature(command)
        type_hints = get_type_hints(command)
    except (ValueError, TypeError):
        return parameters

    for param_name, param in sig.parameters.items():
        # Skip context parameters
        if param_name in ("ctx", "context"):
            continue

        # Get type annotation
        param_type = type_hints.get(param_name, param.annotation)
        type_str = _format_type(param_type)

        # Check if parameter is required
        required = param.default is inspect.Parameter.empty

        # Extract default value
        default = None if param.default is inspect.Parameter.empty else param.default

        # Try to extract help text from Annotated metadata
        help_text = None
        if hasattr(param_type, "__metadata__"):
            for metadata in param_type.__metadata__:
                if isinstance(metadata, typer.models.OptionInfo) or isinstance(
                    metadata, typer.models.ArgumentInfo
                ):
                    help_text = metadata.help
                    break

        parameters.append(
            ParameterSchema(
                name=param_name,
                type=type_str,
                required=required,
                default=default,
                help=help_text,
            )
        )

    return parameters


def _format_type(type_annotation: Any) -> str:
    """Format a type annotation as a readable string."""
    if type_annotation is inspect.Parameter.empty:
        return "any"

    # Handle Annotated types
    if hasattr(type_annotation, "__origin__"):
        origin = type_annotation.__origin__
        if origin is not None:
            origin_name = getattr(origin, "__name__", str(origin))
            return origin_name.lower()

    # Handle basic types
    if hasattr(type_annotation, "__name__"):
        return type_annotation.__name__.lower()

    return str(type_annotation)


def _add_command_metadata(schema: CommandSchema) -> None:
    """Add command-specific examples, expected outputs, and retry hints."""

    # Add examples based on command name
    if "cleanup" in schema.name:
        schema.examples = [
            "hephaestus cleanup",
            "hephaestus cleanup --deep-clean",
            "hephaestus cleanup --python-cache --extra-path /tmp/build",
        ]
        schema.expected_output = "Table showing cleaned paths and sizes"
        schema.retry_hints = [
            "If cleanup fails with permission errors, check file permissions",
            "If dangerous path error occurs, use a safe project directory",
        ]

    elif "guard-rails" in schema.name:
        schema.examples = [
            "hephaestus guard-rails",
            "hephaestus guard-rails --no-format",
        ]
        schema.expected_output = "Table showing check results (passed/failed)"
        schema.retry_hints = [
            "If checks fail, address the reported issues and retry",
            "Use --no-format to skip auto-formatting during review",
        ]

    elif "release install" in schema.name:
        schema.examples = [
            "hephaestus release install",
            "hephaestus release install --tag v1.0.0",
            "hephaestus release install --repository owner/repo",
        ]
        schema.expected_output = "Download progress and installation summary"
        schema.retry_hints = [
            "If download fails, check network connectivity and retry",
            "If signature verification fails, use --allow-unsigned (not recommended)",
            "If GitHub API rate limit reached, set GITHUB_TOKEN",
        ]

    elif "rankings" in schema.name:
        schema.examples = [
            "hephaestus tools refactor rankings",
            "hephaestus tools refactor rankings --strategy coverage_first",
            "hephaestus tools refactor rankings --limit 10",
        ]
        schema.expected_output = "Table ranking modules by refactoring priority"
        schema.retry_hints = [
            "Requires analytics sources configured in settings",
            "If no data loaded, check analytics file paths in config",
        ]

    elif "hotspots" in schema.name:
        schema.examples = [
            "hephaestus tools refactor hotspots",
            "hephaestus tools refactor hotspots --limit 5",
        ]
        schema.expected_output = "Table listing high-churn modules"
        schema.retry_hints = []

    elif "opportunities" in schema.name:
        schema.examples = [
            "hephaestus tools refactor opportunities",
        ]
        schema.expected_output = "Table listing refactoring opportunities"
        schema.retry_hints = []

    elif "plan" in schema.name:
        schema.examples = [
            "hephaestus plan",
        ]
        schema.expected_output = "Table showing project execution plan"
        schema.retry_hints = []

    elif "version" in schema.name:
        schema.examples = [
            "hephaestus version",
        ]
        schema.expected_output = "Version string (e.g., 'Hephaestus v0.1.0')"
        schema.retry_hints = []
