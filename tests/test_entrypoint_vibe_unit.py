from vagents.entrypoint import package_cli


def test_dynamic_cli_executes_with_plain_format(monkeypatch):
    # Set up a fake PM with a single package and expect execute call
    class FakePM:
        def __init__(self):
            self.info = {
                "name": "demo",
                "description": "desc",
                "entry_point": "m.f",
                "arguments": [
                    {"name": "verbose", "type": "bool"},
                    {"name": "arg", "type": "str"},
                ],
            }
            self.called = None

        def get_package_info(self, name):
            return self.info if name == "demo" else None

        def execute_package(self, name, **kw):
            self.called = (name, kw)
            return {"ok": True, **kw}

    cli = package_cli.PackageCLI()
    fake = FakePM()
    cli.pm = fake

    res, fmt = cli.execute_with_args(
        "demo", ["--format", "plain", "--verbose", "--arg", "x"]
    )
    assert fmt == "plain"
    assert res["ok"] is True
    assert fake.called[0] == "demo"
    assert fake.called[1]["verbose"] is True
    assert fake.called[1]["arg"] == "x"
