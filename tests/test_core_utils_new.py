"""
Tests for vagents.core.utils module.
"""
import pytest
from vagents.core.utils import parse_function_signature


class TestParseFunctionSignature:
    """Test the parse_function_signature function."""

    def test_simple_function(self):
        """Test parsing a simple function signature."""

        def simple_func(x: int, y: str) -> str:
            """A simple function."""
            return f"{x}: {y}"

        result = parse_function_signature(simple_func)

        assert result["type"] == "function"
        assert result["function"]["name"] == "simple_func"
        assert result["function"]["description"] == "A simple function."
        assert "x" in result["function"]["parameters"]["properties"]
        assert "y" in result["function"]["parameters"]["properties"]
        assert result["function"]["parameters"]["required"] == ["x", "y"]

    def test_function_with_optional_params(self):
        """Test parsing function with optional parameters."""

        def func_with_defaults(required: str, optional: int = 42):
            """Function with default values."""
            return f"{required}: {optional}"

        result = parse_function_signature(func_with_defaults)

        assert result["function"]["name"] == "func_with_defaults"
        assert "required" in result["function"]["parameters"]["properties"]
        assert "optional" in result["function"]["parameters"]["properties"]
        assert result["function"]["parameters"]["required"] == ["required"]
        # optional param should not be in required list

    def test_function_no_docstring(self):
        """Test parsing function without docstring."""

        def no_doc_func(param):
            return param

        result = parse_function_signature(no_doc_func)

        assert result["function"]["name"] == "no_doc_func"
        assert result["function"]["description"] == "This function has no description."
        assert "param" in result["function"]["parameters"]["properties"]

    def test_function_no_params(self):
        """Test parsing function with no parameters."""

        def no_params_func():
            """Function with no parameters."""
            return "constant"

        result = parse_function_signature(no_params_func)

        assert result["function"]["name"] == "no_params_func"
        assert result["function"]["description"] == "Function with no parameters."
        assert result["function"]["parameters"]["properties"] == {}
        assert result["function"]["parameters"]["required"] == []
