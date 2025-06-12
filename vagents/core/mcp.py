import mcp
import json
import asyncio
import traceback
from fastmcp import Client
from typing import Any, List, Callable, Optional
from fastmcp.client.transports import SSETransport

from vagents.core import Tool
from vagents.utils import logger
from vagents.managers import MCPManager, MCPServerArgs

from .tool import parse_tool_parameters

class MCPClient:
    def __init__(self, serverparams: List[MCPServerArgs]) -> None:
        self.manager = MCPManager()
        self.serverparams = serverparams
        self._tools = None
        self._tools_server_mapping = {}

    async def ensure_ready(self, additional_tools: List[Callable]=None) -> None:
        await self.start_mcp(self.serverparams)
        self._tools, self._tools_server_mapping = await self.fetch_tools()
        self._tools.extend(Tool.from_callable(tool) for tool in additional_tools or [])
        
    async def fetch_tools(self):
        servers = self.manager.get_all_servers()
        tools = []
        tool_server_mapping = {}
        for server in servers:
            transport: SSETransport = SSETransport(url=server)
            async with Client(transport) as client:
                server_tools = await client.list_tools()
                for tool in server_tools:
                    tool_name = tool.name
                    wrapped_tool = Tool.from_mcp(tool, func=self.call_tool)
                    tools.append(wrapped_tool)
                    tool_server_mapping[tool_name] = server
        return tools, tool_server_mapping

    async def list_tools(self, hide_tools: List[str] = None):
        if self._tools is None:
            self._tools, self._tools_server_mapping = await self.fetch_tools()
        if hide_tools is not None:
            return [x for x in self._tools if x.name not in hide_tools]
        else:
            return self._tools

    async def call_tool(self, *args, **kwargs):
        tool_name = kwargs.get("name") or kwargs.get("tool_name")
        if not tool_name:
            raise ValueError("Tool name not provided")
        # Initialize _tools_server_mapping if None or empty
        first_server = self._tools_server_mapping.get(tool_name)
        # Find the tool specification
        if not self._tools:
            self._tools, self._tools_server_mapping = await self.fetch_tools()
        tool_spec = next((x for x in self._tools if x.name == tool_name), None)

        if not tool_spec:
            raise ValueError(f"Tool {tool_name} not found.")

        # Convert parameters to the correct types based on the tool's schema
        parameters = kwargs.get("parameters", {})
        parameters = json.loads(parameters) if isinstance(parameters, str) else parameters
        
        if kwargs.get("override"):
            if tool_name in kwargs["override"]:
                override = kwargs["override"][tool_name]
                parameters.update(override)

        typed_parameters = parse_tool_parameters(
            tool_spec=tool_spec, parameters=parameters
        )
        logger.debug(f"[{tool_name}] typed_parameters: {typed_parameters}")

        response = await self._execute_tool(
            server=first_server,
            tool_name=tool_name,
            typed_parameters=typed_parameters,
        )

        return response

    async def _execute_tool(
            self,
            server: Optional[str],
            tool_name: str,
            typed_parameters: dict,
        ):
        if server:
            try:
                transport: SSETransport = SSETransport(url=server)
                async with Client(transport) as client:
                    responses = await client.call_tool(
                        name=tool_name,
                        arguments=typed_parameters,
                    )
                    if isinstance(responses, List):
                        responses = [parse_mcp_response(r) for r in responses]
                        responses = "\n\n".join(responses)
                    return responses
            except Exception as e:
                logger.error(f"Error calling tool {tool_name} on server {server}: {e}")
                logger.error(traceback.format_exc())
                raise e
        else:
            # execute the tool directly
            tool = [x for x in self._tools if x.name == tool_name]
            if not tool:
                raise ValueError(f"Tool {tool_name} not found.")
            tool = tool[0]
            try:
                response = await tool.func(**typed_parameters)
                return response
            except Exception as e:
                logger.error(f"Error executing tool {tool_name}: {e}")
                logger.error(traceback.format_exc())
                raise e

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


def parse_mcp_response(resp) -> str:
    if isinstance(resp, mcp.types.TextContent):
        return resp.text
    elif isinstance(resp, mcp.types.ImageContent):
        raise NotImplementedError("Image content is not supported yet.")
    elif isinstance(resp, str):
        return resp
    else:
        raise ValueError(f"Unsupported response type: {type(resp)}")
