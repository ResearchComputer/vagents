import ast
import json
import inspect
import textwrap
import importlib
from typing import Callable
from functools import lru_cache
from typing import AsyncGenerator, List, Any
from vagents.core.protocol import OutResponse
from vagents.core.session import Session
from vagents.core.protocol import InRequest 

class ImportFinder(ast.NodeVisitor):
    def __init__(self):
        self.packages = set()

    def visit_Import(self, node):
        for alias in node.names:
            # Get the base package name (before any dots)
            base_package = alias.name.split(".")[0]
            self.packages.add(base_package)

    def visit_ImportFrom(self, node):
        if node.module:  # for "from x import y" statements
            # Get the base package name (before any dots)
            base_package = node.module.split(".")[0]
            self.packages.add(base_package)


def parse_function_signature(func: Callable):
    signature = inspect.signature(func)
    parameters = {
        "type": "object",
        "properties": {},
        "required": [],
    }
    for name, param in signature.parameters.items():
        prop_info = {
            "type": "string",
            "description": f"The '{name}' parameter",
        }
        parameters["properties"][name] = prop_info
        if param.default is param.empty:
            parameters["required"].append(name)

    data = {
        "type": "function",
        "function": {
            "name": func.__name__,
            "description": func.__doc__ or "This function has no description.",
            "parameters": parameters,
        },
    }
    return data

BASE_BUILTIN_MODULES = [
    "collections",
    "datetime",
    "itertools",
    "math",
    "queue",
    "random",
    "re",
    "stat",
    "statistics",
    "time",
    "unicodedata",
]


def get_source(obj) -> str:
    if not (isinstance(obj, type) or callable(obj)):
        raise TypeError(f"Expected class or callable, got {type(obj)}")
    return textwrap.dedent(inspect.getsource(obj)).strip()


def instance_to_source(instance, base_cls=None):
    """Convert an instance to its class source code representation."""
    cls = instance.__class__
    class_name = cls.__name__

    # Start building class lines
    class_lines = []
    if base_cls:
        class_lines.append(f"class {class_name}({base_cls.__name__}):")
    else:
        class_lines.append(f"class {class_name}:")

    # Add docstring if it exists and differs from base
    if cls.__doc__ and (not base_cls or cls.__doc__ != base_cls.__doc__):
        class_lines.append(f'    """{cls.__doc__}"""')

    # Add class-level attributes
    class_attrs = {
        name: value
        for name, value in cls.__dict__.items()
        if not name.startswith("__")
        and not callable(value)
        and not (
            base_cls and hasattr(base_cls, name) and getattr(base_cls, name) == value
        )
    }

    for name, value in class_attrs.items():
        if isinstance(value, str):
            # multiline value
            if "\n" in value:
                escaped_value = value.replace('"""', r"\"\"\"")  # Escape triple quotes
                class_lines.append(f'    {name} = """{escaped_value}"""')
            else:
                class_lines.append(f"    {name} = {json.dumps(value)}")
        else:
            class_lines.append(f"    {name} = {repr(value)}")

    if class_attrs:
        class_lines.append("")

    # Add methods
    methods = {
        name: func
        for name, func in cls.__dict__.items()
        if callable(func)
        and not (
            base_cls
            and hasattr(base_cls, name)
            and getattr(base_cls, name).__code__.co_code == func.__code__.co_code
        )
    }

    for name, method in methods.items():
        method_source = get_source(method)
        # Clean up the indentation
        method_lines = method_source.split("\n")
        first_line = method_lines[0]
        indent = len(first_line) - len(first_line.lstrip())
        method_lines = [line[indent:] for line in method_lines]
        method_source = "\n".join(
            ["    " + line if line.strip() else line for line in method_lines]
        )
        class_lines.append(method_source)
        class_lines.append("")

    # Find required imports using ImportFinder
    import_finder = ImportFinder()
    import_finder.visit(ast.parse("\n".join(class_lines)))
    required_imports = import_finder.packages

    # Build final code with imports
    final_lines = []

    # Add base class import if needed
    if base_cls:
        final_lines.append(f"from {base_cls.__module__} import {base_cls.__name__}")

    # Add discovered imports
    for package in required_imports:
        final_lines.append(f"import {package}")

    if final_lines:  # Add empty line after imports
        final_lines.append("")

    # Add the class code
    final_lines.extend(class_lines)

    return "\n".join(final_lines)




async def stream_llm_response(
    llm_stream: AsyncGenerator[Any, None], # Changed from str to Any
    session: Session,
    query: InRequest,
    assistant_role_name: str = "assistant"
) -> AsyncGenerator[OutResponse, None]:
    """
    Handles streaming of LLM responses, passing through dictionary events
    and collecting raw text chunks for history.

    Args:
        llm_stream: The asynchronous generator yielding chunks from the LLM.
                    Can yield strings for text content or dicts for structured events.
        session: The current session object.
        query: The input request object.
        assistant_role_name: The role name to use for the assistant's message in history.

    Yields:
        OutResponse: An OutResponse object for each item in the stream or final update.
    """
    history_snapshot = list(session.history)  # Shallow copy
    collected_text_chunks: List[str] = []
    # Heuristic: store text from the last seen 'tool_result' dict if no raw text chunks appear.
    text_from_last_tool_result: str | None = None

    async for item in llm_stream:
        if isinstance(item, str):
            if item:  # Ensure string item is not empty
                collected_text_chunks.append(item)
                yield OutResponse(
                    output=item,
                    session=history_snapshot,
                    id=query.id,
                    input=query.input,
                    module=query.module,
                    type="stream_chunk"
                )
        elif isinstance(item, dict):
            # If the item is a dictionary, pass it through.
            # Heuristically capture 'result' text from 'tool_result' type events.
            if item.get("type") == "tool_result" and isinstance(item.get("result"), str):
                text_from_last_tool_result = item["result"]
            
            yield OutResponse(
                output=item, # The whole dictionary is the output
                session=history_snapshot,
                id=query.id,
                input=query.input,
                module=query.module,
                type=item.get("type", "stream_event") # Use item's type or a default
            )
        # Other types of items in the stream will be ignored by this version.

    final_text_for_history = "".join(collected_text_chunks)
    if not final_text_for_history and text_from_last_tool_result:
        # If no raw text chunks were collected, use the text from the last tool_result dict.
        final_text_for_history = text_from_last_tool_result

    if final_text_for_history: # Only append if there was some text identified
        session.append({"role": assistant_role_name, "content": final_text_for_history})

    # Yield a final message with the updated history
    yield OutResponse(
        output="", # Or final_text_for_history if client needs it again
        session=session.history, # Send history *after* potential update
        id=query.id,
        input=query.input,
        module=query.module,
        type="stream_end"
    )
