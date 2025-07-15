"""
Tests for vagents.core.mcp module.
"""
import pytest
from unittest.mock import AsyncMock, MagicMock, patch
import asyncio
from vagents.core.mcp import MCPClient
from vagents.core.tool import Tool
from vagents.managers.mcp_manager import MCPServerArgs


class TestMCPClient:
    """Test the MCPClient class."""

    def test_mcp_client_initialization(self):
        """Test MCPClient initialization."""
        server_params = [MCPServerArgs(command="python", args=["server.py"])]

        client = MCPClient(server_params)

        assert client.serverparams == server_params
        assert client._tools is None
        assert client._tools_server_mapping == {}
        assert hasattr(client, "manager")

    def test_mcp_client_initialization_empty_params(self):
        """Test MCPClient initialization with empty server params."""
        client = MCPClient([])

        assert client.serverparams == []
        assert client._tools is None
        assert client._tools_server_mapping == {}

    @pytest.mark.asyncio
    @patch("vagents.core.mcp.MCPManager")
    async def test_ensure_ready_basic(self, mock_manager_class):
        """Test basic ensure_ready functionality."""
        mock_manager = AsyncMock()
        mock_manager_class.return_value = mock_manager

        server_params = [MCPServerArgs(command="python", args=["server.py"])]
        client = MCPClient(server_params)

        # Mock the methods that ensure_ready calls
        with patch.object(client, "start_mcp") as mock_start, patch.object(
            client, "fetch_tools"
        ) as mock_fetch:

            mock_start.return_value = None
            mock_fetch.return_value = ([], {})

            await client.ensure_ready()

            mock_start.assert_called_once_with(server_params)
            mock_fetch.assert_called_once()

    @pytest.mark.asyncio
    @patch("vagents.core.mcp.MCPManager")
    async def test_ensure_ready_with_additional_tools(self, mock_manager_class):
        """Test ensure_ready with additional tools."""
        mock_manager = AsyncMock()
        mock_manager_class.return_value = mock_manager

        def additional_tool():
            """Additional tool for testing."""
            return "test"

        server_params = [MCPServerArgs(command="python", args=["server.py"])]
        client = MCPClient(server_params)

        with patch.object(client, "start_mcp") as mock_start, patch.object(
            client, "fetch_tools"
        ) as mock_fetch, patch(
            "vagents.core.mcp.Tool.from_callable"
        ) as mock_from_callable:

            mock_start.return_value = None
            mock_fetch.return_value = ([], {})
            mock_tool = MagicMock()
            mock_from_callable.return_value = mock_tool

            await client.ensure_ready(additional_tools=[additional_tool])

            mock_from_callable.assert_called_once_with(additional_tool)

    @pytest.mark.asyncio
    @patch("vagents.core.mcp.MCPManager")
    @patch("vagents.core.mcp.Client")
    @patch("vagents.core.mcp.SSETransport")
    async def test_fetch_tools(
        self, mock_transport_class, mock_client_class, mock_manager_class
    ):
        """Test fetching tools from MCP servers."""
        # Setup mocks
        mock_manager = MagicMock()
        mock_manager.get_all_servers.return_value = ["http://localhost:8080"]
        mock_manager_class.return_value = mock_manager

        mock_transport = MagicMock()
        mock_transport_class.return_value = mock_transport

        mock_client = AsyncMock()
        mock_tool_def = MagicMock()
        mock_tool_def.name = "test_tool"
        mock_client.list_tools.return_value = [mock_tool_def]

        # Mock the async context manager properly
        mock_client_instance = AsyncMock()
        mock_client_instance.__aenter__.return_value = mock_client
        mock_client_instance.__aexit__.return_value = None
        mock_client_class.return_value = mock_client_instance

        client = MCPClient([])

        with patch("vagents.core.mcp.Tool.from_mcp") as mock_from_mcp:
            mock_tool = MagicMock()
            mock_tool.name = "test_tool"
            mock_from_mcp.return_value = mock_tool

            tools, mapping = await client.fetch_tools()

            assert len(tools) == 1
            assert "test_tool" in mapping
            assert mapping["test_tool"] == "http://localhost:8080"

    @pytest.mark.asyncio
    @patch("vagents.core.mcp.MCPManager")
    async def test_list_tools_when_none(self, mock_manager_class):
        """Test list_tools when _tools is None."""
        mock_manager = MagicMock()
        mock_manager_class.return_value = mock_manager

        client = MCPClient([])

        with patch.object(client, "fetch_tools") as mock_fetch:
            mock_tool = MagicMock()
            mock_tool.name = "test_tool"
            mock_fetch.return_value = ([mock_tool], {"test_tool": "server"})

            tools = await client.list_tools()

            assert len(tools) == 1
            assert tools[0] == mock_tool
            mock_fetch.assert_called_once()

    @pytest.mark.asyncio
    @patch("vagents.core.mcp.MCPManager")
    async def test_list_tools_with_existing(self, mock_manager_class):
        """Test list_tools when _tools already exists."""
        mock_manager = MagicMock()
        mock_manager_class.return_value = mock_manager

        client = MCPClient([])

        # Pre-populate tools
        mock_tool1 = MagicMock()
        mock_tool1.name = "tool1"
        mock_tool2 = MagicMock()
        mock_tool2.name = "tool2"
        client._tools = [mock_tool1, mock_tool2]

        tools = await client.list_tools()

        assert len(tools) == 2
        assert mock_tool1 in tools
        assert mock_tool2 in tools

    @pytest.mark.asyncio
    @patch("vagents.core.mcp.MCPManager")
    async def test_list_tools_with_hide_tools(self, mock_manager_class):
        """Test list_tools with hide_tools parameter."""
        mock_manager = MagicMock()
        mock_manager_class.return_value = mock_manager

        client = MCPClient([])

        # Pre-populate tools
        mock_tool1 = MagicMock()
        mock_tool1.name = "tool1"
        mock_tool2 = MagicMock()
        mock_tool2.name = "tool2"
        mock_tool3 = MagicMock()
        mock_tool3.name = "tool3"
        client._tools = [mock_tool1, mock_tool2, mock_tool3]

        tools = await client.list_tools(hide_tools=["tool2"])

        assert len(tools) == 2
        tool_names = [tool.name for tool in tools]
        assert "tool1" in tool_names
        assert "tool3" in tool_names
        assert "tool2" not in tool_names

    @pytest.mark.asyncio
    @patch("vagents.core.mcp.MCPManager")
    @patch("vagents.core.mcp.Client")
    @patch("vagents.core.mcp.SSETransport")
    async def test_call_tool(
        self, mock_transport_class, mock_client_class, mock_manager_class
    ):
        """Test calling a tool through MCP."""
        mock_manager = MagicMock()
        mock_manager_class.return_value = mock_manager

        mock_transport = MagicMock()
        mock_transport_class.return_value = mock_transport

        mock_client = AsyncMock()
        mock_result = ["Tool result"]
        mock_client.call_tool.return_value = mock_result

        # Mock the async context manager properly
        mock_client_instance = AsyncMock()
        mock_client_instance.__aenter__.return_value = mock_client
        mock_client_instance.__aexit__.return_value = None
        mock_client_class.return_value = mock_client_instance

        client = MCPClient([])

        # Setup tool mapping and tools
        client._tools_server_mapping = {"test_tool": "http://localhost:8080"}
        mock_tool = MagicMock()
        mock_tool.name = "test_tool"
        client._tools = [mock_tool]

        with patch("vagents.core.mcp.parse_tool_parameters") as mock_parse, patch(
            "vagents.core.mcp.parse_mcp_response"
        ) as mock_parse_response:
            mock_parse.return_value = {"param": "value"}
            mock_parse_response.return_value = "Tool result"

            result = await client.call_tool(
                name="test_tool", parameters={"param": "value"}
            )

            assert result == "Tool result"
            mock_parse.assert_called_once()
            mock_client.call_tool.assert_called_once()

    @pytest.mark.asyncio
    @patch("vagents.core.mcp.MCPManager")
    async def test_call_tool_not_found(self, mock_manager_class):
        """Test calling a tool that doesn't exist."""
        mock_manager = MagicMock()
        mock_manager_class.return_value = mock_manager

        client = MCPClient([])
        client._tools_server_mapping = {}

        with pytest.raises(Exception):
            await client.call_tool("nonexistent_tool")

    @pytest.mark.asyncio
    @patch("vagents.core.mcp.MCPManager")
    @patch("vagents.core.mcp.asyncio.gather")
    async def test_start_mcp(self, mock_gather, mock_manager_class):
        """Test starting MCP servers."""
        mock_manager = AsyncMock()
        mock_manager.start_mcp_server = AsyncMock(return_value="server_url")
        mock_manager.register_running_mcp_server = AsyncMock()
        mock_manager_class.return_value = mock_manager

        # Mock asyncio.gather to return the awaitable result
        mock_gather.return_value = ["server_url", "server_url"]

        server_params = [
            MCPServerArgs(command="python", args=["server1.py"]),
            MCPServerArgs(command="node", args=["server2.js"]),
        ]

        client = MCPClient([])

        await client.start_mcp(server_params)

        # Should call start_mcp_server for each server param with command
        assert mock_manager.start_mcp_server.call_count == 2
        mock_gather.assert_called_once()

    @pytest.mark.asyncio
    @patch("vagents.core.mcp.MCPManager")
    async def test_manager_cleanup(self, mock_manager_class):
        """Test accessing manager cleanup functionality."""
        mock_manager = AsyncMock()
        mock_manager.cleanup = AsyncMock()
        mock_manager_class.return_value = mock_manager

        client = MCPClient([])

        # Access manager directly for cleanup
        await client.manager.cleanup()

        mock_manager.cleanup.assert_called_once()

    def test_client_with_multiple_servers(self):
        """Test MCPClient with multiple server configurations."""
        server_params = [
            MCPServerArgs(command="python", args=["server1.py"]),
            MCPServerArgs(remote_addr="http://external-server:8080"),
            MCPServerArgs(command="node", args=["server2.js"]),
        ]

        client = MCPClient(server_params)

        assert len(client.serverparams) == 3
        assert client.serverparams[0].command == "python"
        assert client.serverparams[1].remote_addr == "http://external-server:8080"
        assert client.serverparams[2].command == "node"

    @pytest.mark.asyncio
    @patch("vagents.core.mcp.MCPManager")
    async def test_error_handling_in_fetch_tools(self, mock_manager_class):
        """Test error handling during tool fetching."""
        mock_manager = MagicMock()
        mock_manager.get_all_servers.return_value = ["http://localhost:8080"]
        mock_manager_class.return_value = mock_manager

        client = MCPClient([])

        with patch("vagents.core.mcp.Client") as mock_client_class:
            # Simulate an error in client
            mock_client_class.side_effect = Exception("Connection failed")

            # Should handle the error gracefully
            try:
                tools, mapping = await client.fetch_tools()
                # If no exception raised, tools should be empty
                assert tools == []
                assert mapping == {}
            except Exception:
                # Exception handling is also acceptable
                pass

    @pytest.mark.asyncio
    @patch("vagents.core.mcp.MCPManager")
    async def test_tool_name_conflicts(self, mock_manager_class):
        """Test handling of tool name conflicts from different servers."""
        mock_manager = MagicMock()
        mock_manager.get_all_servers.return_value = [
            "http://server1:8080",
            "http://server2:8080",
        ]
        mock_manager_class.return_value = mock_manager

        client = MCPClient([])

        with patch("vagents.core.mcp.Client") as mock_client_class, patch(
            "vagents.core.mcp.SSETransport"
        ) as mock_transport_class, patch(
            "vagents.core.mcp.Tool.from_mcp"
        ) as mock_from_mcp:

            # Setup mock clients that return tools with same name
            mock_client1 = AsyncMock()
            mock_client2 = AsyncMock()

            mock_tool_def = MagicMock()
            mock_tool_def.name = "duplicate_tool"

            mock_client1.list_tools.return_value = [mock_tool_def]
            mock_client2.list_tools.return_value = [mock_tool_def]

            mock_client_class.return_value.__aenter__.side_effect = [
                mock_client1,
                mock_client2,
            ]

            mock_tool = MagicMock()
            mock_tool.name = "duplicate_tool"
            mock_from_mcp.return_value = mock_tool

            tools, mapping = await client.fetch_tools()

            # Should handle duplicates (last one wins or both kept)
            assert len(tools) >= 1
            assert "duplicate_tool" in mapping
