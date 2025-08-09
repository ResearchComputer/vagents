from typer.testing import CliRunner

from vagents.entrypoint.main import app


def test_main_commands_exist():
    runner = CliRunner()
    # version
    r = runner.invoke(app, ["version"])
    assert r.exit_code == 0
    # info
    r = runner.invoke(app, ["info"])
    assert r.exit_code == 0
