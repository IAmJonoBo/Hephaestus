#!/usr/bin/env python3
"""Lint script to detect nested Typer command decorators.

This script prevents regression of the guard-rails availability bug where commands
were accidentally defined inside other functions, making them unavailable until
the parent function was executed.

Usage:
    python scripts/lint_nested_decorators.py [paths...]

Exit codes:
    0: No nested decorators found
    1: Nested decorators detected or error occurred
"""

from __future__ import annotations

import argparse
import ast
import sys
from pathlib import Path
from typing import NamedTuple


class NestedDecoratorViolation(NamedTuple):
    """Represents a detected nested decorator violation."""

    file: Path
    line: int
    function_name: str
    decorator_name: str
    parent_function: str


class NestedDecoratorChecker(ast.NodeVisitor):
    """AST visitor that detects Typer command decorators inside function definitions."""

    # Typer app command decorators to check for
    COMMAND_DECORATORS = {
        "app.command",
        "tools_app.command",
        "refactor_app.command",
        "qa_app.command",
        "release_app.command",
    }

    def __init__(self, filepath: Path) -> None:
        self.filepath = filepath
        self.violations: list[NestedDecoratorViolation] = []
        self.function_stack: list[str] = []

    def visit_FunctionDef(self, node: ast.FunctionDef) -> None:
        """Visit function definitions and check for nested command decorators."""
        # Check if this function has a command decorator while inside another function
        if self.function_stack:
            for decorator in node.decorator_list:
                decorator_name = self._get_decorator_name(decorator)
                if decorator_name and self._is_command_decorator(decorator_name):
                    self.violations.append(
                        NestedDecoratorViolation(
                            file=self.filepath,
                            line=node.lineno,
                            function_name=node.name,
                            decorator_name=decorator_name,
                            parent_function=self.function_stack[-1],
                        )
                    )

        # Push this function onto the stack and visit children
        self.function_stack.append(node.name)
        self.generic_visit(node)
        self.function_stack.pop()

    def visit_AsyncFunctionDef(self, node: ast.AsyncFunctionDef) -> None:
        """Visit async function definitions (same logic as regular functions)."""
        if self.function_stack:
            for decorator in node.decorator_list:
                decorator_name = self._get_decorator_name(decorator)
                if decorator_name and self._is_command_decorator(decorator_name):
                    self.violations.append(
                        NestedDecoratorViolation(
                            file=self.filepath,
                            line=node.lineno,
                            function_name=node.name,
                            decorator_name=decorator_name,
                            parent_function=self.function_stack[-1],
                        )
                    )

        self.function_stack.append(node.name)
        self.generic_visit(node)
        self.function_stack.pop()

    def _get_decorator_name(self, decorator: ast.expr) -> str | None:
        """Extract the name from a decorator node."""
        if isinstance(decorator, ast.Name):
            return decorator.id
        elif isinstance(decorator, ast.Attribute):
            parts = []
            node = decorator
            while isinstance(node, ast.Attribute):
                parts.append(node.attr)
                node = node.value
            if isinstance(node, ast.Name):
                parts.append(node.id)
            return ".".join(reversed(parts))
        elif isinstance(decorator, ast.Call):
            # Handle @app.command() style decorators
            return self._get_decorator_name(decorator.func)
        return None

    def _is_command_decorator(self, decorator_name: str) -> bool:
        """Check if a decorator name matches a Typer command decorator."""
        return any(decorator_name.startswith(cmd_dec) for cmd_dec in self.COMMAND_DECORATORS)


def check_file(filepath: Path) -> list[NestedDecoratorViolation]:
    """Check a single Python file for nested decorator violations."""
    try:
        content = filepath.read_text(encoding="utf-8")
        tree = ast.parse(content, filename=str(filepath))
        checker = NestedDecoratorChecker(filepath)
        checker.visit(tree)
        return checker.violations
    except SyntaxError as e:
        print(f"Syntax error in {filepath}: {e}", file=sys.stderr)
        return []
    except Exception as e:
        print(f"Error processing {filepath}: {e}", file=sys.stderr)
        return []


def main() -> int:
    """Main entry point for the linter."""
    parser = argparse.ArgumentParser(
        description="Detect nested Typer command decorators that cause registration bugs."
    )
    parser.add_argument(
        "paths",
        nargs="*",
        type=Path,
        default=[Path("src/hephaestus")],
        help="Files or directories to check (default: src/hephaestus)",
    )
    args = parser.parse_args()

    all_violations: list[NestedDecoratorViolation] = []

    for path in args.paths:
        if path.is_file() and path.suffix == ".py":
            all_violations.extend(check_file(path))
        elif path.is_dir():
            for py_file in path.rglob("*.py"):
                all_violations.extend(check_file(py_file))
        else:
            print(f"Skipping non-Python file: {path}", file=sys.stderr)

    if all_violations:
        print("❌ Nested decorator violations detected:", file=sys.stderr)
        print(file=sys.stderr)
        for violation in all_violations:
            print(
                f"  {violation.file}:{violation.line}: "
                f"Command '@{violation.decorator_name}' on function '{violation.function_name}' "
                f"is nested inside '{violation.parent_function}'",
                file=sys.stderr,
            )
        print(file=sys.stderr)
        print(
            "Commands must be defined at module scope to be registered properly.",
            file=sys.stderr,
        )
        print(
            "See Next_Steps.md for context on the guard-rails availability bug.",
            file=sys.stderr,
        )
        return 1

    print("✅ No nested decorator violations found.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
