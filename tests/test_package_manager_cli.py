from typer.testing import CliRunner

from vagents.entrypoint.package_manager import app as pm_app


runner = CliRunner()


def test_pm_status(tmp_path, monkeypatch):
    monkeypatch.setenv("HOME", str(tmp_path))
    result = runner.invoke(pm_app, ["status"])
    assert result.exit_code == 0
    assert "VAgents Package Manager Status" in result.stdout


def test_pm_list_table(tmp_path, monkeypatch):
    monkeypatch.setenv("HOME", str(tmp_path))
    result = runner.invoke(pm_app, ["list", "--format", "table"])
    assert result.exit_code == 0
    # If empty registry, shows friendly message
    out = result.stdout.strip()
    assert out == "No packages installed." or "Name" in out
