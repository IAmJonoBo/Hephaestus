"""Tests for the nested decorator linter."""

from __future__ import annotations

import sys
import tempfile
from pathlib import Path

# Add scripts to path for import
sys.path.insert(0, str(Path(__file__).parent.parent / "scripts"))

from lint_nested_decorators import check_file  # type: ignore[import-not-found]


def test_detects_nested_command_decorator() -> None:
    """Test that nested command decorators are detected."""
    code = '''
import typer

app = typer.Typer()

def outer_function():
    """Outer function."""
    
    @app.command()
    def nested_command():
        """This should be detected as a violation."""
        pass
'''
    with tempfile.NamedTemporaryFile(mode="w", suffix=".py", delete=False) as f:
        f.write(code)
        f.flush()
        filepath = Path(f.name)

    try:
        violations = check_file(filepath)
        assert len(violations) == 1
        assert violations[0].function_name == "nested_command"
        assert violations[0].parent_function == "outer_function"
        assert "app.command" in violations[0].decorator_name
    finally:
        filepath.unlink()


def test_allows_module_level_command_decorators() -> None:
    """Test that module-level command decorators are allowed."""
    code = '''
import typer

app = typer.Typer()

@app.command()
def module_level_command():
    """This should be allowed."""
    pass
'''
    with tempfile.NamedTemporaryFile(mode="w", suffix=".py", delete=False) as f:
        f.write(code)
        f.flush()
        filepath = Path(f.name)

    try:
        violations = check_file(filepath)
        assert len(violations) == 0
    finally:
        filepath.unlink()


def test_detects_nested_in_multiple_levels() -> None:
    """Test that deeply nested decorators are detected."""
    code = '''
import typer

tools_app = typer.Typer()

def outer():
    """Outer function."""
    
    def middle():
        """Middle function."""
        
        @tools_app.command()
        def deeply_nested():
            """Should be detected."""
            pass
'''
    with tempfile.NamedTemporaryFile(mode="w", suffix=".py", delete=False) as f:
        f.write(code)
        f.flush()
        filepath = Path(f.name)

    try:
        violations = check_file(filepath)
        assert len(violations) == 1
        assert violations[0].function_name == "deeply_nested"
        assert violations[0].parent_function == "middle"
    finally:
        filepath.unlink()


def test_handles_different_typer_apps() -> None:
    """Test that different Typer app names are detected."""
    code = '''
import typer

refactor_app = typer.Typer()
qa_app = typer.Typer()
release_app = typer.Typer()

def wrapper():
    """Wrapper function."""
    
    @refactor_app.command()
    def cmd1():
        pass
    
    @qa_app.command()
    def cmd2():
        pass
    
    @release_app.command()
    def cmd3():
        pass
'''
    with tempfile.NamedTemporaryFile(mode="w", suffix=".py", delete=False) as f:
        f.write(code)
        f.flush()
        filepath = Path(f.name)

    try:
        violations = check_file(filepath)
        assert len(violations) == 3
        assert {v.function_name for v in violations} == {"cmd1", "cmd2", "cmd3"}
    finally:
        filepath.unlink()


def test_ignores_non_command_decorators() -> None:
    """Test that non-command decorators are ignored."""
    code = '''
import typer

app = typer.Typer()

def outer():
    """Outer function."""
    
    @staticmethod
    def not_a_command():
        """This should not be flagged."""
        pass
    
    @app.callback()
    def also_not_a_command():
        """Callbacks are not commands."""
        pass
'''
    with tempfile.NamedTemporaryFile(mode="w", suffix=".py", delete=False) as f:
        f.write(code)
        f.flush()
        filepath = Path(f.name)

    try:
        violations = check_file(filepath)
        assert len(violations) == 0
    finally:
        filepath.unlink()
