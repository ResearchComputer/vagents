from vagents.entrypoint.package_manager import format_result_markdown


def test_format_result_markdown_basic():
    data = {"a": 1, "b": {"c": 2}, "list": [1, {"x": 3}]}
    out = format_result_markdown(data, "pkg")
    assert "Package Execution Result" in out
    assert "a" in out and "b" in out and "list" in out
