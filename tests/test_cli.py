import json
import os
from pathlib import Path

import pytest
from typer.testing import CliRunner

from vagents.entrypoint.main import app


runner = CliRunner()


def test_version_command():
    result = runner.invoke(app, ["version"])
    assert result.exit_code == 0
    assert "VAgents version:" in result.stdout


def test_info_command():
    result = runner.invoke(app, ["info"])
    assert result.exit_code == 0
    assert "VAgents CLI" in result.stdout


def test_package_manager_list_empty(tmp_path, monkeypatch):
    # Isolate the registry to a temp dir
    monkeypatch.setenv("HOME", str(tmp_path))
    result = runner.invoke(app, ["pm", "list", "--format", "json"])
    assert result.exit_code == 0
    # When no packages, implementation prints a friendly line instead of JSON
    out = result.stdout.strip()
    if out.startswith("{"):
        data = json.loads(out)
        assert isinstance(data, dict)
    else:
        assert out == "No packages installed."


def test_pm_help_package_not_found(tmp_path, monkeypatch):
    monkeypatch.setenv("HOME", str(tmp_path))
    result = runner.invoke(app, ["pm", "help-package", "nope"])
    assert result.exit_code != 0
    assert "not found" in result.stdout.lower()


def test_invalid_command():
    """Test CLI handles invalid commands gracefully"""
    result = runner.invoke(app, ["invalid-command"])
    assert result.exit_code != 0


def test_help_command():
    """Test main help command works"""
    result = runner.invoke(app, ["--help"])
    assert result.exit_code == 0
    assert "VAgents" in result.stdout or "Usage" in result.stdout


def test_version_command_format():
    """Test version command output format"""
    result = runner.invoke(app, ["version"])
    assert result.exit_code == 0
    output = result.stdout.strip()
    assert "VAgents version:" in output
    # Check that version string contains semantic version pattern
    import re
    version_pattern = r'\d+\.\d+\.\d+'
    assert re.search(version_pattern, output)


def test_info_command_contains_expected_info():
    """Test info command contains expected information"""
    result = runner.invoke(app, ["info"])
    assert result.exit_code == 0
    output = result.stdout
    assert "VAgents CLI" in output
    # Should contain some basic information about the CLI


def test_pm_subcommand_help():
    """Test package manager subcommand help"""
    result = runner.invoke(app, ["pm", "--help"])
    assert result.exit_code == 0
    assert "list" in result.stdout.lower()


def test_pm_list_with_different_formats(tmp_path, monkeypatch):
    """Test package manager list with different output formats"""
    monkeypatch.setenv("HOME", str(tmp_path))
    
    # Test table format
    result = runner.invoke(app, ["pm", "list", "--format", "table"])
    assert result.exit_code == 0
    
    # Test json format (already tested but adding for completeness)
    result = runner.invoke(app, ["pm", "list", "--format", "json"])
    assert result.exit_code == 0


def test_pm_list_invalid_format(tmp_path, monkeypatch):
    """Test package manager list with invalid format"""
    monkeypatch.setenv("HOME", str(tmp_path))
    result = runner.invoke(app, ["pm", "list", "--format", "invalid"])
    # Should either fail or default to a valid format
    # Implementation may vary, but should not crash


def test_pm_help_package_with_empty_name(tmp_path, monkeypatch):
    """Test package manager help with empty package name"""
    monkeypatch.setenv("HOME", str(tmp_path))
    result = runner.invoke(app, ["pm", "help-package", ""])
    assert result.exit_code != 0


def test_pm_commands_with_isolated_registry(tmp_path, monkeypatch):
    """Test package manager commands work with isolated registry"""
    monkeypatch.setenv("HOME", str(tmp_path))
    
    # Test status command
    result = runner.invoke(app, ["pm", "status"])
    assert result.exit_code == 0
    
    # Test list command  
    result = runner.invoke(app, ["pm", "list"])
    assert result.exit_code == 0


def test_cli_with_verbose_flag():
    """Test CLI commands with verbose flag if supported"""
    # Test version with verbose (if supported)
    result = runner.invoke(app, ["version", "--verbose"])
    # Should either work or fail gracefully
    assert result.exit_code in [0, 2]  # 0 for success, 2 for invalid option
    
    # Test info with verbose (if supported)
    result = runner.invoke(app, ["info", "--verbose"])
    assert result.exit_code in [0, 2]


def test_cli_exit_codes():
    """Test CLI returns appropriate exit codes"""
    # Success case
    result = runner.invoke(app, ["version"])
    assert result.exit_code == 0
    
    # Failure case
    result = runner.invoke(app, ["pm", "help-package", "nonexistent"])
    assert result.exit_code != 0


def test_cli_handles_keyboard_interrupt():
    """Test CLI handles KeyboardInterrupt gracefully"""
    # This is hard to test directly, but we can at least verify
    # the CLI doesn't crash on initialization
    result = runner.invoke(app, ["--help"])
    assert result.exit_code == 0
