from pathlib import Path

import pytest
from typer.testing import CliRunner

from vagents.entrypoint.main import app
from vagents.manager.package import PackageRegistry, PackageConfig


runner = CliRunner()


def register_local_test_package(
    registry_base: Path,
    name: str,
    module_py: str,
    entry: str,
    args_def: list | None = None,
):
    # PackageManager default base is HOME/.vagents/packages
    manager_base = registry_base / ".vagents" / "packages"
    manager_base.mkdir(parents=True, exist_ok=True)

    reg = PackageRegistry(manager_base)
    # Actual packages live in reg.packages_dir (manager_base / "packages")
    reg.packages_dir.mkdir(parents=True, exist_ok=True)
    pkg_dir = reg.packages_dir / name
    pkg_dir.mkdir(parents=True, exist_ok=True)
    (pkg_dir / f"{entry.split('.')[0]}.py").write_text(module_py)

    cfg = PackageConfig(
        name=name,
        version="1.0.0",
        description=f"pkg {name}",
        author="tester",
        repository_url=f"https://example.com/{name}.git",
        entry_point=entry,
        arguments=args_def or [],
    )
    reg.register_package(cfg, pkg_dir, commit_hash="cafebabe")


def test_pm_run_plain_output(tmp_path, monkeypatch, capsys):
    monkeypatch.setenv("HOME", str(tmp_path))
    base = tmp_path  # HOME
    module_py = (
        "def main(input=None, **kw):\n"
        "    return {'ok': True, 'len': len(input) if input else 0}\n"
    )
    register_local_test_package(base, "pkg1", module_py, "mod.main")

    # Run with plain output
    result = runner.invoke(app, ["pm", "run", "pkg1", "--format", "plain"])  # no stdin
    assert result.exit_code == 0
    assert "Package executed successfully" in result.stdout


def test_pm_run_markdown_output_with_args(tmp_path, monkeypatch):
    monkeypatch.setenv("HOME", str(tmp_path))
    base = tmp_path  # HOME
    module_py = (
        "def main(verbose=False, **kw):\n"
        "    return {'ok': True, 'verbose': verbose}\n"
    )
    register_local_test_package(
        base,
        "pkg2",
        module_py,
        "mod.main",
        args_def=[{"name": "verbose", "type": "bool", "help": "Verbose"}],
    )

    result = runner.invoke(
        app, ["pm", "run", "pkg2", "--format", "markdown", "--verbose"]
    )
    assert result.exit_code == 0
    # markdown output rendered via rich should include the title text
    assert "Package Execution Result" in result.stdout
