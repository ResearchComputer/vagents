import os
from pathlib import Path

import pytest

from vagents.manager.package import (
    PackageManager,
    PackageConfig,
    PackageArgument,
    GitRepository,
)


def _config(name: str) -> PackageConfig:
    return PackageConfig(
        name=name,
        version="0.0.1",
        description="d",
        author="a",
        repository_url=f"https://example.com/{name}.git",
        entry_point="mod.main",
        arguments=[PackageArgument(name="verbose", type="bool")],
    )


def test_install_package_success_no_subdir(tmp_path, monkeypatch):
    monkeypatch.setenv("HOME", str(tmp_path))
    pm = PackageManager(base_path=tmp_path)

    # Pretend git clone works
    monkeypatch.setattr(GitRepository, "clone", lambda *a, **k: True, raising=True)
    # No subdir path => extract_subdirectory unused; safe to keep default
    monkeypatch.setattr(
        GitRepository, "get_commit_hash", lambda *a, **k: "cafebabe", raising=True
    )

    # Bypass validation and file checks
    monkeypatch.setattr(
        PackageManager,
        "_validate_package_structure",
        lambda self, p: _config("demo"),
        raising=True,
    )

    # Make copytree a no-op that ensures destination exists
    import shutil as _sh

    def fake_copytree(src, dst):
        Path(dst).mkdir(parents=True, exist_ok=True)
        # Touch entry file to be safe
        (Path(dst) / "mod.py").write_text("def main(**kw):\n    return {'ok': True}\n")
        return str(dst)

    monkeypatch.setattr(_sh, "copytree", fake_copytree, raising=True)

    ok = pm.install_package("https://github.com/user/repo.git")
    assert ok is True
    assert pm.registry.is_package_installed("demo") is True

    # Installing again without force should fail
    ok2 = pm.install_package("https://github.com/user/repo.git")
    assert ok2 is False


def test_install_package_with_subdir_and_update_and_uninstall(tmp_path, monkeypatch):
    monkeypatch.setenv("HOME", str(tmp_path))
    pm = PackageManager(base_path=tmp_path)

    # Mock git operations
    monkeypatch.setattr(GitRepository, "clone", lambda *a, **k: True, raising=True)
    monkeypatch.setattr(
        GitRepository, "extract_subdirectory", lambda *a, **k: True, raising=True
    )
    monkeypatch.setattr(
        GitRepository, "get_commit_hash", lambda *a, **k: "deadbeef", raising=True
    )

    # Copytree to create files
    import shutil as _sh

    def fake_copytree(src, dst):
        Path(dst).mkdir(parents=True, exist_ok=True)
        (Path(dst) / "mod.py").write_text("def main(**kw):\n    return {'ok': True}\n")
        return str(dst)

    monkeypatch.setattr(_sh, "copytree", fake_copytree, raising=True)

    # Return config with name=alpha
    monkeypatch.setattr(
        PackageManager,
        "_validate_package_structure",
        lambda self, p: _config("alpha"),
        raising=True,
    )

    ok = pm.install_package("https://github.com/user/repo.git/packages/pkg")
    assert ok is True
    assert pm.registry.is_package_installed("alpha") is True

    # update should call install_package(force=True) under the hood
    calls = {"args": None}

    def fake_install(url, branch="main", force=False):
        calls["args"] = (url, branch, force)
        return True

    monkeypatch.setattr(pm, "install_package", fake_install, raising=True)
    assert pm.update_package("alpha") is True
    assert calls["args"][2] is True

    # uninstall removes the directory and unregisters
    assert pm.uninstall_package("alpha") is True
    assert pm.registry.is_package_installed("alpha") is False


def test_execute_package_with_cli_args(tmp_path, monkeypatch):
    monkeypatch.setenv("HOME", str(tmp_path))
    pm = PackageManager(base_path=tmp_path)
    # Prepare a real package dir with mod.py implementing a bool arg and a list
    pkg_dir = pm.registry.packages_dir / "beta"
    pkg_dir.mkdir(parents=True)
    (pkg_dir / "mod.py").write_text(
        """
def main(verbose=False, tags=None, **kw):
    return {"verbose": bool(verbose), "tags": list(tags or [])}
"""
    )
    cfg = _config("beta")
    # add a list argument too
    cfg.arguments.append(PackageArgument(name="tags", type="list"))
    pm.registry.register_package(cfg, pkg_dir, commit_hash="1")

    out = pm.execute_package_with_cli_args("beta", ["--verbose", "--tags", "a", "b"])
    assert out["verbose"] is True
    assert out["tags"] == ["a", "b"]
