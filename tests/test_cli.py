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
