"""Tests for built-in quality gate plugins (ADR-0002 Sprint 2)."""

from __future__ import annotations

from unittest.mock import MagicMock, patch

import pytest

from hephaestus.plugins import PluginResult
from hephaestus.plugins.builtin import (
    MypyPlugin,
    PipAuditPlugin,
    PytestPlugin,
    RuffCheckPlugin,
    RuffFormatPlugin,
)


class TestRuffCheckPlugin:
    """Tests for RuffCheckPlugin."""

    def test_metadata_structure(self) -> None:
        """Test that plugin metadata is properly structured."""
        plugin = RuffCheckPlugin()
        metadata = plugin.metadata

        assert metadata.name == "ruff-check"
        assert metadata.category == "linting"
        assert "ruff" in metadata.requires[0].lower()
        assert metadata.order == 10

    def test_validate_config_accepts_valid(self) -> None:
        """Test that valid configuration is accepted."""
        plugin = RuffCheckPlugin()

        assert plugin.validate_config({})
        assert plugin.validate_config({"paths": ["."]})
        assert plugin.validate_config({"args": ["--fix"]})
        assert plugin.validate_config({"paths": ["src"], "args": ["--fix"]})

    def test_validate_config_rejects_invalid_paths(self) -> None:
        """Test that invalid paths configuration is rejected."""
        plugin = RuffCheckPlugin()

        with pytest.raises(ValueError, match="'paths' must be a list"):
            plugin.validate_config({"paths": "."})

    def test_validate_config_rejects_invalid_args(self) -> None:
        """Test that invalid args configuration is rejected."""
        plugin = RuffCheckPlugin()

        with pytest.raises(ValueError, match="'args' must be a list"):
            plugin.validate_config({"args": "--fix"})

    @patch("subprocess.run")
    def test_run_success(self, mock_run) -> None:  # type: ignore[no-untyped-def]
        """Test successful execution."""
        mock_run.return_value = MagicMock(returncode=0, stdout="All checks passed", stderr="")

        plugin = RuffCheckPlugin()
        result = plugin.run({})

        assert result.success
        assert "passed" in result.message
        assert result.exit_code == 0

    @patch("subprocess.run")
    def test_run_failure(self, mock_run) -> None:  # type: ignore[no-untyped-def]
        """Test failed execution."""
        mock_run.return_value = MagicMock(returncode=1, stdout="", stderr="Found issues")

        plugin = RuffCheckPlugin()
        result = plugin.run({})

        assert not result.success
        assert "failed" in result.message
        assert result.exit_code == 1

    @patch("subprocess.run", side_effect=FileNotFoundError)
    def test_run_missing_tool(self, mock_run) -> None:  # type: ignore[no-untyped-def]
        """Test handling of missing tool."""
        plugin = RuffCheckPlugin()
        result = plugin.run({})

        assert not result.success
        assert "not installed" in result.message
        assert result.exit_code == 127


class TestRuffFormatPlugin:
    """Tests for RuffFormatPlugin."""

    def test_metadata_structure(self) -> None:
        """Test that plugin metadata is properly structured."""
        plugin = RuffFormatPlugin()
        metadata = plugin.metadata

        assert metadata.name == "ruff-format"
        assert metadata.category == "formatting"
        assert metadata.order == 20

    def test_validate_config_check_flag(self) -> None:
        """Test check flag validation."""
        plugin = RuffFormatPlugin()

        assert plugin.validate_config({"check": True})
        assert plugin.validate_config({"check": False})

        with pytest.raises(ValueError, match="'check' must be a boolean"):
            plugin.validate_config({"check": "true"})


class TestMypyPlugin:
    """Tests for MypyPlugin."""

    def test_metadata_structure(self) -> None:
        """Test that plugin metadata is properly structured."""
        plugin = MypyPlugin()
        metadata = plugin.metadata

        assert metadata.name == "mypy"
        assert metadata.category == "type-checking"
        assert metadata.order == 30

    def test_default_paths(self) -> None:
        """Test that default paths are src and tests."""
        plugin = MypyPlugin()

        with patch("subprocess.run") as mock_run:
            mock_run.return_value = MagicMock(returncode=0, stdout="", stderr="")
            plugin.run({})

            call_args = mock_run.call_args[0][0]
            assert "src" in call_args
            assert "tests" in call_args


class TestPytestPlugin:
    """Tests for PytestPlugin."""

    def test_metadata_structure(self) -> None:
        """Test that plugin metadata is properly structured."""
        plugin = PytestPlugin()
        metadata = plugin.metadata

        assert metadata.name == "pytest"
        assert metadata.category == "testing"
        assert "pytest" in metadata.requires[0].lower()
        assert metadata.order == 40

    def test_validate_config_min_coverage(self) -> None:
        """Test min_coverage validation."""
        plugin = PytestPlugin()

        assert plugin.validate_config({"min_coverage": 85})
        assert plugin.validate_config({"min_coverage": 85.5})

        with pytest.raises(ValueError, match="'min_coverage' must be a number"):
            plugin.validate_config({"min_coverage": "85"})

    @patch("subprocess.run")
    def test_run_with_custom_coverage(self, mock_run) -> None:  # type: ignore[no-untyped-def]
        """Test execution with custom coverage threshold."""
        mock_run.return_value = MagicMock(returncode=0, stdout="", stderr="")

        plugin = PytestPlugin()
        plugin.run({"min_coverage": 90.0})

        call_args = mock_run.call_args[0][0]
        assert "--cov-fail-under=90.0" in call_args


class TestPipAuditPlugin:
    """Tests for PipAuditPlugin."""

    def test_metadata_structure(self) -> None:
        """Test that plugin metadata is properly structured."""
        plugin = PipAuditPlugin()
        metadata = plugin.metadata

        assert metadata.name == "pip-audit"
        assert metadata.category == "security"
        assert metadata.order == 50

    def test_validate_config_ignore_vulns(self) -> None:
        """Test ignore_vulns validation."""
        plugin = PipAuditPlugin()

        assert plugin.validate_config({"ignore_vulns": []})
        assert plugin.validate_config({"ignore_vulns": ["CVE-2024-1234"]})

        with pytest.raises(ValueError, match="'ignore_vulns' must be a list"):
            plugin.validate_config({"ignore_vulns": "CVE-2024-1234"})

    @patch("subprocess.run")
    def test_run_with_ignored_vulns(self, mock_run) -> None:  # type: ignore[no-untyped-def]
        """Test execution with ignored vulnerabilities."""
        mock_run.return_value = MagicMock(returncode=0, stdout="", stderr="")

        plugin = PipAuditPlugin()
        plugin.run({"ignore_vulns": ["CVE-2024-1234", "CVE-2024-5678"]})

        call_args = mock_run.call_args[0][0]
        assert "--ignore-vuln" in call_args
        assert "CVE-2024-1234" in call_args
        assert "CVE-2024-5678" in call_args


class TestPluginIntegration:
    """Integration tests for plugin system."""

    def test_all_plugins_have_unique_names(self) -> None:
        """Test that all built-in plugins have unique names."""
        plugins = [
            RuffCheckPlugin(),
            RuffFormatPlugin(),
            MypyPlugin(),
            PytestPlugin(),
            PipAuditPlugin(),
        ]

        names = [p.metadata.name for p in plugins]
        assert len(names) == len(set(names)), "Plugin names must be unique"

    def test_all_plugins_have_valid_order(self) -> None:
        """Test that all plugins have valid execution orders."""
        plugins = [
            RuffCheckPlugin(),
            RuffFormatPlugin(),
            MypyPlugin(),
            PytestPlugin(),
            PipAuditPlugin(),
        ]

        orders = [p.metadata.order for p in plugins]
        assert all(o > 0 for o in orders), "Orders must be positive"
        assert orders == sorted(orders), "Orders should be sequential"

    def test_all_plugins_implement_required_methods(self) -> None:
        """Test that all plugins implement required interface."""
        plugins = [
            RuffCheckPlugin(),
            RuffFormatPlugin(),
            MypyPlugin(),
            PytestPlugin(),
            PipAuditPlugin(),
        ]

        for plugin in plugins:
            # All plugins must have metadata
            assert hasattr(plugin, "metadata")
            assert plugin.metadata is not None

            # All plugins must validate config
            assert callable(plugin.validate_config)
            assert plugin.validate_config({})  # Empty config should be valid

            # All plugins must be runnable
            assert callable(plugin.run)

    def test_plugin_result_structure(self) -> None:
        """Test that plugin results have consistent structure."""

        @patch("subprocess.run")
        def check_result(mock_run):  # type: ignore[no-untyped-def]
            mock_run.return_value = MagicMock(returncode=0, stdout="", stderr="")

            plugins = [
                RuffCheckPlugin(),
                RuffFormatPlugin(),
                MypyPlugin(),
                PytestPlugin(),
                PipAuditPlugin(),
            ]

            for plugin in plugins:
                result = plugin.run({})
                assert isinstance(result, PluginResult)
                assert hasattr(result, "success")
                assert hasattr(result, "message")
                assert hasattr(result, "details")
                assert hasattr(result, "exit_code")

        check_result()
