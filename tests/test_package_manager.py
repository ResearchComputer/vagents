import json
from pathlib import Path

import pytest

from vagents.manager.package import (
    PackageRegistry,
    PackageManager,
    PackageConfig,
    PackageArgument,
)


def test_registry_isolated(tmp_path):
    reg = PackageRegistry(tmp_path)
    assert reg.list_packages() == {}

    cfg = PackageConfig(
        name="demo",
        version="0.0.1",
        description="desc",
        author="me",
        repository_url="https://example.com/repo.git",
        entry_point="mod.fn",
        arguments=[PackageArgument(name="verbose", type="bool")],
    )

    pkg_dir = tmp_path / "packages" / "demo"
    pkg_dir.mkdir(parents=True)
    reg.register_package(cfg, pkg_dir, commit_hash="abc123")

    assert reg.is_package_installed("demo") is True
    info = reg.get_package_info("demo")
    assert info["name"] == "demo"

    reg.unregister_package("demo")
    assert reg.is_package_installed("demo") is False


def test_execute_package_from_registry(tmp_path, monkeypatch):
    # Create isolated base path
    base = tmp_path
    (base / "packages").mkdir(parents=True)

    # Create a simple package with entry mod.py:function 'main'
    pkg_dir = base / "packages" / "foo"
    pkg_dir.mkdir(parents=True)
    (pkg_dir / "mod.py").write_text(
        """
def main(verbose=False, **kw):
    return {"ok": True, "verbose": verbose, **kw}
"""
    )

    # Register it
    reg = PackageRegistry(base)
    cfg = PackageConfig(
        name="foo",
        version="0.0.1",
        description="d",
        author="a",
        repository_url="https://example.com/foo.git",
        entry_point="mod.main",
    )
    reg.register_package(cfg, pkg_dir, commit_hash="deadbeef")

    pm = PackageManager(base_path=base)
    res = pm.execute_package("foo", verbose=True, x=1)
    # res may be a plain dict (legacy) or AgentOutput (new modules)
    if hasattr(res, "result"):
        data = res.result or {}
    else:
        data = res
    assert data["ok"] is True
    assert data["verbose"] is True
    assert data["x"] == 1
