from pathlib import Path

import pytest

from vagents.entrypoint.vibe import parse_package_args
from vagents.manager.package import PackageRegistry, PackageConfig


def test_vibe_parse_and_execute(tmp_path, capsys, monkeypatch):
    monkeypatch.setenv("VAGENTS_LM_FAKE", "1")
    # Ensure default base path resolves under this tmp HOME
    monkeypatch.setenv("HOME", str(tmp_path))
    home = Path(tmp_path)
    # PackageManager default base is ~/.vagents/packages
    manager_base = home / ".vagents" / "packages"
    manager_base.mkdir(parents=True, exist_ok=True)

    # PackageRegistry will put actual packages under manager_base / "packages"
    reg = PackageRegistry(manager_base)
    reg.packages_dir.mkdir(parents=True, exist_ok=True)

    pkg_dir = reg.packages_dir / "bar"
    pkg_dir.mkdir(parents=True)
    (pkg_dir / "mod.py").write_text(
        """
def main(content=None, **kw):
    return {"len": len(content) if content else 0}
"""
    )
    cfg = PackageConfig(
        name="bar",
        version="0.0.1",
        description="d",
        author="a",
        repository_url="https://example.com/bar.git",
        entry_point="mod.main",
    )
    reg.register_package(cfg, pkg_dir, commit_hash="deadbeef")

    # Call the argument parser/runner directly (no actual stdin here)
    # It will execute and print outputs; ensure no crash
    parse_package_args("bar", ["--format", "json"])  # should print JSON
    out = capsys.readouterr().out
    assert "\n" in out  # printed something
