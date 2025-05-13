import mcp
import asyncio
from fastmcp import Client
from typing import Any, List

from vagents.core import Tool
from vagents.managers import MCPManager, MCPServerArgs
from vagents.utils import logger
from .tool import parse_tool_parameters


class MCPClient:
    def __init__(self, serverparams: List[MCPServerArgs]):
        self.manager = MCPManager()
        self.serverparams = serverparams
        self._tools = None
        self._tools_server_mapping = {}

    async def ensure_ready(self):
        await self.start_mcp(self.serverparams)
        self._tools, self._tools_server_mapping = await self.fetch_tools()

    async def fetch_tools(self):
        servers = self.manager.get_all_servers()
        tools = []
        tool_server_mapping = {}
        for server in servers:
            async with Client(server) as client:
                server_tools = await client.list_tools()
                for tool in server_tools:
                    tool_name = tool.name
                    wrapped_tool = Tool.from_mcp(tool, func=self.call_tool)
                    tools.append(wrapped_tool)
                    tool_server_mapping[tool_name] = server
        return tools, tool_server_mapping

    async def list_tools(self):
        if self._tools is None:
            self._tools, self._tools_server_mapping = await self.fetch_tools()
        return self._tools

    async def call_tool(self, *args, **kwargs):
        tool_name = kwargs.get("name") or kwargs.get("tool_name")
        if not tool_name:
            raise ValueError("Tool name not provided")

        # Initialize _tools_server_mapping if None or empty
        first_server = self._tools_server_mapping.get(tool_name)
        if not first_server:
            raise ValueError(f"Tool {tool_name} not found.")

        # Find the tool specification
        if not self._tools:
            self._tools, self._tools_server_mapping = await self.fetch_tools()

        tool_spec = next((x for x in self._tools if x.name == tool_name), None)
        if not tool_spec:
            raise ValueError(f"Tool {tool_name} not found.")

        # Convert parameters to the correct types based on the tool's schema
        parameters = kwargs.get("parameters", {})

        typed_parameters = parse_tool_parameters(
            tool_spec=tool_spec, parameters=parameters
        )
        print(f"Calling [{tool_name}] with parameters: {typed_parameters}")
        try:
            async with Client(first_server) as client:
                response = await client.call_tool(
                    name=tool_name,
                    arguments=typed_parameters,
                )
                print(f"Response from [{tool_name}]: {response}")
                # Process the response
                if isinstance(response, List):
                    responses = [parse_response(r) for r in response]
                return responses

        except Exception as e:
            logger.error(f"Error calling tool {tool_name}: {e}.")
            return f"Error calling tool: {e}"

    async def start_mcp(self, args: List[MCPServerArgs]):
        tasks = [
            self.manager.start_mcp_server(arg, wait_until_ready=True)
            for arg in args
            if arg.command
        ]
        for arg in args:
            if arg.remote_addr:
                await self.manager.register_running_mcp_server(arg.remote_addr)
        # If there are no tasks, we don't need to await anything
        if tasks:
            await asyncio.gather(*tasks)


def parse_response(resp) -> str:
    if isinstance(resp, mcp.types.TextContent):
        return resp.text
    elif isinstance(resp, mcp.types.ImageContent):
        raise NotImplementedError("Image content is not supported yet.")
    elif isinstance(resp, str):
        return resp
    else:
        raise ValueError(f"Unsupported response type: {type(resp)}")
