import mcp
import jsonref
import json
from typing import Callable, Optional, Dict, Any, List
from .utils import parse_function_signature


class Tool:
    def __init__(
        self,
        name: str,
        description: str,
        parameters: Optional[Dict[str, Any]],
        func: Callable,
        required: Optional[List] = None,
    ):
        self.name = name
        self.description = description
        self.func = func
        self.parameters = parameters
        self.required = required or []

    def __call__(self, *args, **kwargs):
        return self.func(*args, **kwargs)

    @classmethod
    def from_mcp(self, definition: mcp.types.Tool, func: Callable) -> "Tool":
        """
        Create a Tool instance from an MCP tool definition.
        """
        input_schema = {
            k: v
            for k, v in jsonref.replace_refs(definition.inputSchema).items()
            if k != "$defs"
        }
        return Tool(
            name=definition.name,
            description=definition.description,
            parameters=input_schema["properties"]
            if "properties" in input_schema
            else {},
            func=func,  # Functionality to be defined later
            required=input_schema.get("required", []),
        )
    
    @classmethod
    def from_callable(self, func: Callable) -> "Tool":
        """
        Create a Tool instance from a callable function.
        """
        signature = parse_function_signature(func)
        # docstring is used for description, if available
        if not signature.get("description"):
            signature["description"] = func.__doc__ or "No description provided."
        
        return Tool(
            name=signature["function"]["name"],
            description=signature["function"]["description"],
            parameters=signature.get("parameters", {}),
            func=func,
            required=signature.get("required", []),
        )

    def __repr__(self) -> str:
        return f"Tool(name={self.name}, description={self.description}, parameters={self.parameters}, required={self.required})"

    def to_llm_format(self) -> Dict[str, Any]:
        """
        Convert the Tool instance to a format suitable for LLM.
        """
        parameters = {
            "type": "object",
            "properties": {},
            "required": self.required,
        }
        for name, param in self.parameters.items():
            prop_info = {
                "type": param.get("type", "string"),
                "description": param.get("description", f"The '{name}' parameter"),
            }
            parameters["properties"][name] = prop_info
            if param.get("default", None):
                parameters["required"].append(name)

        data = {
            "type": "function",
            "function": {
                "name": self.name,
                "description": self.description,
                "parameters": parameters,
            },
        }
        return data


def prepare_tools(tools: List[dict]) -> str:
    """
    Prepare tool information for LLM processing.

    Args:
        tools: A list of dictionaries containing tool information

    Returns:
        A string representation of the tools
    """
    tool_info = []
    for tool in tools:
        if isinstance(tool, Tool):
            tool_info.append(tool.to_llm_format())
        else:
            print(f"tool is not a Tool instance: {tool}")
            tool_info.append(parse_function_signature(tool))
    return tool_info


def clean_tool_parameters(tool_spec: Tool, parameters):
    cleaned_parameters = {}
    for name, value in parameters.items():
        # Normalize nullish values
        if value is None or (
            isinstance(value, str) and value.strip().lower() in ("", "null", "none")
        ):
            continue
        # if not required and empty list, dict, or string, skip
        if name not in tool_spec.required and (
            (isinstance(value, list) and not value)
            or (isinstance(value, dict) and not value)
            or (isinstance(value, str) and not value.strip())
        ):
            continue
        else:
            cleaned_parameters[name] = value
    return cleaned_parameters


def ensure_typed_parameters(tool_spec: Tool, parameters):
    # If no parameters schema, return as-is
    if not tool_spec.parameters:
        return parameters
    typed_parameters = {}
    for name, value in parameters.items():
        # Normalize nullish values
        if value is None or (
            isinstance(value, str) and value.strip().lower() in ("", "null", "none")
        ):
            continue
        #
        # Convert based on schema type
        schema = tool_spec.parameters.get(name, {})
        t = schema.get("type")
        if t == "number":
            try:
                num = float(value)
                # Convert whole floats to int
                typed_parameters[name] = int(num) if num.is_integer() else num
            except (ValueError, TypeError):
                typed_parameters[name] = value
        elif t == "integer" and not isinstance(value, int):
            try:
                typed_parameters[name] = int(value)
            except (ValueError, TypeError):
                typed_parameters[name] = value
        elif t == "boolean" and not isinstance(value, bool):
            if isinstance(value, str):
                typed_parameters[name] = value.lower() in ("true", "yes", "1", "t", "y")
            else:
                typed_parameters[name] = bool(value)
        elif t == "array":
            # Parse JSON list
            if isinstance(value, str):
                try:
                    typed_parameters[name] = json.loads(value)
                except (ValueError, TypeError):
                    typed_parameters[name] = value
            else:
                typed_parameters[name] = value
        elif t == "object":
            # Parse JSON dict
            if isinstance(value, str):
                try:
                    typed_parameters[name] = json.loads(value)
                except (ValueError, TypeError):
                    typed_parameters[name] = value
            else:
                typed_parameters[name] = value
        else:
            # Default: use as-is
            typed_parameters[name] = value
    return typed_parameters


def parse_tool_parameters(tool_spec: Tool, parameters):
    cleaned_parameters = clean_tool_parameters(tool_spec, parameters)
    typed_parameters = ensure_typed_parameters(tool_spec, cleaned_parameters)
    return typed_parameters
