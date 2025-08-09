from pathlib import Path

from vagents.manager.package import (
    PackageManager,
    PackageRegistry,
    PackageConfig,
    PackageArgument,
)
from vagents.core import AgentOutput


def _setup_pm(tmp_path: Path) -> PackageManager:
    pm = PackageManager(base_path=tmp_path)
    pm.registry.packages_dir.mkdir(parents=True, exist_ok=True)
    return pm


def test_execute_function_with_input_mapping(tmp_path):
    pm = _setup_pm(tmp_path)
    pkg_dir = pm.registry.packages_dir / "demo1"
    pkg_dir.mkdir(parents=True)
    (pkg_dir / "mod.py").write_text(
        """
def main(input=None, **kw):
    return {"got": bool(input), "value": input}
"""
    )
    cfg = PackageConfig(
        name="demo1",
        version="0.0.1",
        description="d",
        author="a",
        repository_url="https://example.com/demo1.git",
        entry_point="mod.main",
    )
    pm.registry.register_package(cfg, pkg_dir, commit_hash="x")

    out = pm.execute_package("demo1", input="hello")
    assert isinstance(out, dict)
    assert out["got"] is True and out["value"] == "hello"


def test_execute_function_with_agent_input_detection(tmp_path):
    pm = _setup_pm(tmp_path)
    pkg_dir = pm.registry.packages_dir / "demo2"
    pkg_dir.mkdir(parents=True)
    (pkg_dir / "mod.py").write_text(
        """
def main(agent_input=None, **kw):
    # Echo payload keys for verification
    return {"keys": sorted(list((agent_input.payload or {}).keys()))}
"""
    )
    cfg = PackageConfig(
        name="demo2",
        version="0.0.1",
        description="d",
        author="a",
        repository_url="https://example.com/demo2.git",
        entry_point="mod.main",
        arguments=[PackageArgument(name="flag", type="bool")],
    )
    pm.registry.register_package(cfg, pkg_dir, commit_hash="x")

    res = pm.execute_package("demo2", flag=True, extra=1)
    # Coerced to AgentOutput
    assert isinstance(res, AgentOutput)
    assert "keys" in (res.result or {})
    assert "flag" in (res.result or {})["keys"]


def test_execute_agentmodule_class(tmp_path):
    pm = _setup_pm(tmp_path)
    pkg_dir = pm.registry.packages_dir / "demo3"
    pkg_dir.mkdir(parents=True)
    (pkg_dir / "mod.py").write_text(
        """
from vagents.core import AgentModule, AgentInput, AgentOutput

class Runner(AgentModule):
    async def forward(self, input: AgentInput) -> AgentOutput:
        return AgentOutput(input_id=input.id, result={"n": 1})
"""
    )
    cfg = PackageConfig(
        name="demo3",
        version="0.0.1",
        description="d",
        author="a",
        repository_url="https://example.com/demo3.git",
        entry_point="mod.Runner",
    )
    pm.registry.register_package(cfg, pkg_dir, commit_hash="x")

    out = pm.execute_package("demo3")
    assert isinstance(out, AgentOutput)
    assert (out.result or {}).get("n") == 1
