"""
Tests for vagents.core.tool module.
"""
import pytest
from unittest.mock import MagicMock, patch
from vagents.core.tool import Tool
import mcp.types


class TestTool:
    """Test the Tool class."""

    def test_tool_initialization(self):
        """Test Tool initialization with basic parameters."""

        def sample_func(x, y):
            return x + y

        tool = Tool(
            name="add_numbers",
            description="Adds two numbers",
            parameters={"x": {"type": "integer"}, "y": {"type": "integer"}},
            func=sample_func,
            required=["x", "y"],
        )

        assert tool.name == "add_numbers"
        assert tool.description == "Adds two numbers"
        assert tool.func == sample_func
        assert tool.parameters == {"x": {"type": "integer"}, "y": {"type": "integer"}}
        assert tool.required == ["x", "y"]

    def test_tool_initialization_default_required(self):
        """Test Tool initialization with default empty required list."""

        def sample_func():
            return "test"

        tool = Tool(
            name="test_tool", description="Test tool", parameters={}, func=sample_func
        )

        assert tool.required == []

    def test_tool_call(self):
        """Test calling a tool function."""

        def multiply(x, y):
            return x * y

        tool = Tool(
            name="multiply",
            description="Multiplies two numbers",
            parameters={"x": {"type": "number"}, "y": {"type": "number"}},
            func=multiply,
            required=["x", "y"],
        )

        result = tool(3, 4)
        assert result == 12

    def test_tool_call_with_kwargs(self):
        """Test calling a tool function with keyword arguments."""

        def greet(name, greeting="Hello"):
            return f"{greeting}, {name}!"

        tool = Tool(
            name="greet",
            description="Greets a person",
            parameters={"name": {"type": "string"}, "greeting": {"type": "string"}},
            func=greet,
            required=["name"],
        )

        result = tool(name="Alice", greeting="Hi")
        assert result == "Hi, Alice!"

    @patch("jsonref.replace_refs")
    def test_from_mcp_basic(self, mock_replace_refs):
        """Test creating Tool from MCP tool definition."""
        # Mock MCP tool definition
        mcp_tool = MagicMock()
        mcp_tool.name = "mcp_test_tool"
        mcp_tool.description = "MCP test tool description"
        mcp_tool.inputSchema = {
            "type": "object",
            "properties": {"param1": {"type": "string"}, "param2": {"type": "integer"}},
            "required": ["param1"],
        }

        # Mock jsonref.replace_refs to return the schema as-is
        mock_replace_refs.return_value = mcp_tool.inputSchema

        def mock_func():
            return "mcp_result"

        tool = Tool.from_mcp(mcp_tool, mock_func)

        assert tool.name == "mcp_test_tool"
        assert tool.description == "MCP test tool description"
        assert tool.func == mock_func
        assert tool.parameters == {
            "param1": {"type": "string"},
            "param2": {"type": "integer"},
        }
        assert tool.required == ["param1"]

    @patch("jsonref.replace_refs")
    def test_from_mcp_no_properties(self, mock_replace_refs):
        """Test creating Tool from MCP tool definition without properties."""
        mcp_tool = MagicMock()
        mcp_tool.name = "simple_tool"
        mcp_tool.description = "Simple tool"
        mcp_tool.inputSchema = {"type": "object"}

        mock_replace_refs.return_value = mcp_tool.inputSchema

        def mock_func():
            return "simple_result"

        tool = Tool.from_mcp(mcp_tool, mock_func)

        assert tool.name == "simple_tool"
        assert tool.description == "Simple tool"
        assert tool.parameters == {}
        assert tool.required == []

    @patch("jsonref.replace_refs")
    def test_from_mcp_with_defs(self, mock_replace_refs):
        """Test creating Tool from MCP tool definition with $defs."""
        mcp_tool = MagicMock()
        mcp_tool.name = "complex_tool"
        mcp_tool.description = "Complex tool"
        mcp_tool.inputSchema = {
            "type": "object",
            "properties": {"data": {"type": "object"}},
            "$defs": {"SomeDefinition": {"type": "string"}},
            "required": ["data"],
        }

        mock_replace_refs.return_value = mcp_tool.inputSchema

        def mock_func():
            return "complex_result"

        tool = Tool.from_mcp(mcp_tool, mock_func)

        # $defs should be excluded from parameters
        assert "$defs" not in tool.parameters
        assert tool.parameters == {"data": {"type": "object"}}
        assert tool.required == ["data"]

    @patch("vagents.core.tool.parse_function_signature")
    def test_from_callable_basic(self, mock_parse_signature):
        """Test creating Tool from callable function."""

        def test_function(x: int, y: str = "default") -> str:
            """Test function that does something."""
            return f"{y}: {x}"

        # Mock the parse_function_signature return value to match actual structure
        mock_parse_signature.return_value = {
            "type": "function",
            "function": {
                "name": "test_function",
                "description": "Test function that does something.",
                "parameters": {
                    "type": "object",
                    "properties": {
                        "x": {"type": "integer", "description": "The 'x' parameter"},
                        "y": {"type": "string", "description": "The 'y' parameter"},
                    },
                    "required": ["x"],
                },
            },
        }

        tool = Tool.from_callable(test_function)

        assert tool.name == "test_function"
        assert tool.description == "Test function that does something."
        assert tool.func == test_function
        assert "x" in tool.parameters
        assert "y" in tool.parameters
        assert tool.required == ["x"]

        mock_parse_signature.assert_called_once_with(test_function)

    @patch("vagents.core.tool.parse_function_signature")
    def test_from_callable_no_docstring(self, mock_parse_signature):
        """Test creating Tool from callable without docstring."""

        def simple_func():
            return "result"

        mock_parse_signature.return_value = {
            "type": "function",
            "function": {
                "name": "simple_func",
                "description": "This function has no description.",
                "parameters": {"type": "object", "properties": {}, "required": []},
            },
        }

        tool = Tool.from_callable(simple_func)

        assert tool.name == "simple_func"
        assert tool.description == "This function has no description."
        assert tool.func == simple_func
        assert tool.parameters == {}
        assert tool.required == []

    def test_tool_with_async_function(self):
        """Test Tool with async function."""

        async def async_func(value):
            return value * 2

        tool = Tool(
            name="async_tool",
            description="Async tool",
            parameters={"value": {"type": "integer"}},
            func=async_func,
            required=["value"],
        )

        assert tool.name == "async_tool"
        assert tool.func == async_func

    def test_tool_representation(self):
        """Test string representation of Tool."""

        def sample_func():
            return "test"

        tool = Tool(
            name="test_tool",
            description="Test description",
            parameters={"param": {"type": "string"}},
            func=sample_func,
        )

        # Tool should have meaningful attributes accessible
        assert hasattr(tool, "name")
        assert hasattr(tool, "description")
        assert hasattr(tool, "func")
        assert hasattr(tool, "parameters")
        assert hasattr(tool, "required")

    def test_tool_with_complex_parameters(self):
        """Test Tool with complex parameter definitions."""

        def complex_func(data, options):
            return f"Processed {data} with {options}"

        complex_params = {
            "data": {
                "type": "object",
                "properties": {"id": {"type": "integer"}, "name": {"type": "string"}},
            },
            "options": {"type": "array", "items": {"type": "string"}},
        }

        tool = Tool(
            name="complex_tool",
            description="Tool with complex parameters",
            parameters=complex_params,
            func=complex_func,
            required=["data"],
        )

        assert tool.parameters == complex_params
        assert tool.required == ["data"]

    def test_tool_none_parameters(self):
        """Test Tool with None parameters."""

        def simple_func():
            return "result"

        tool = Tool(
            name="simple_tool",
            description="Simple tool",
            parameters=None,
            func=simple_func,
        )

        assert tool.parameters is None
        assert tool.required == []
