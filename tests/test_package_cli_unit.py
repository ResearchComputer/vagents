import pytest

from vagents.entrypoint.package_cli import PackageCLI


class _FakePM:
    def __init__(self, package_info=None):
        self._info = package_info or {
            "name": "demo",
            "description": "demo package",
            "entry_point": "mod.main",
            "arguments": [
                {"name": "verbose", "type": "bool", "help": "verbose", "short": "v"},
                {"name": "count", "type": "int", "help": "count"},
                {"name": "ratio", "type": "float", "help": "ratio"},
                {"name": "tags", "type": "list", "help": "tags"},
                {"name": "name", "type": "str", "help": "name"},
            ],
        }
        self.last_exec = None

    def get_package_info(self, package_name: str):
        if package_name != self._info["name"]:
            return None
        return self._info

    def execute_package(self, package_name: str, **kwargs):
        self.last_exec = (package_name, kwargs)
        return {"ok": True, "received": kwargs}


def test_package_cli_parser_and_execute():
    cli = PackageCLI()
    # Inject fake package manager
    cli.pm = _FakePM()

    parser = cli.create_package_parser("demo")
    args_list = [
        "--format",
        "plain",
        "--verbose",
        "--count",
        "3",
        "--ratio",
        "2.5",
        "--tags",
        "a",
        "b",
        "--name",
        "bob",
    ]

    # Ensure parser accepts and types are correct
    ns = parser.parse_args(args_list)
    assert ns.format == "plain"
    assert ns.verbose is True
    assert ns.count == 3
    assert abs(ns.ratio - 2.5) < 1e-9
    assert ns.tags == ["a", "b"]
    assert ns.name == "bob"

    result, fmt = cli.execute_with_args("demo", args_list)
    assert fmt == "plain"
    assert result["ok"] is True
    # Ensure arguments flowed through
    assert result["received"]["verbose"] is True
    assert result["received"]["count"] == 3


def test_package_cli_missing_package_raises():
    cli = PackageCLI()
    fake = _FakePM()
    # Change the available package name so lookup fails
    fake._info["name"] = "other"
    cli.pm = fake

    with pytest.raises(ValueError):
        _ = cli.create_package_parser("demo")
