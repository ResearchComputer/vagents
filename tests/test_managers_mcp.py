"""
Tests for vagents.managers.mcp_manager module.
"""
import pytest
from unittest.mock import AsyncMock, MagicMock, patch
from vagents.managers.mcp_manager import MCPManager, MCPServerArgs, MCPServerVisibility


class TestMCPServerArgs:
    """Test the MCPServerArgs dataclass."""

    def test_mcp_server_args_creation(self):
        """Test basic MCPServerArgs creation."""
        args = MCPServerArgs(
            command="python", args=["server.py"], visiblity=MCPServerVisibility.PUBLIC
        )

        assert args.command == "python"
        assert args.args == ["server.py"]
        assert args.visiblity == MCPServerVisibility.PUBLIC
        assert args.remote_addr is None

    def test_mcp_server_args_with_remote_addr(self):
        """Test MCPServerArgs with remote address."""
        args = MCPServerArgs(remote_addr="http://example.com:8080")

        assert args.remote_addr == "http://example.com:8080"
        assert args.command is None

    def test_from_dict_with_command(self):
        """Test creating MCPServerArgs from dict with command."""
        data = {
            "command": "node",
            "args": ["app.js", "--port", "3000"],
            "visiblity": "session",
        }

        args = MCPServerArgs.from_dict(data)

        assert args.command == "node"
        assert args.args == ["app.js", "--port", "3000"]
        assert args.visiblity == MCPServerVisibility.SESSION

    def test_from_dict_with_remote_addr(self):
        """Test creating MCPServerArgs from dict with remote address."""
        data = {"remote_addr": "http://remote.server:9000"}

        args = MCPServerArgs.from_dict(data)

        assert args.remote_addr == "http://remote.server:9000"

    def test_from_dict_invalid_format(self):
        """Test creating MCPServerArgs from invalid dict format."""
        data = {"invalid": "data"}

        with pytest.raises(ValueError, match="Invalid MCPServerArgs data format"):
            MCPServerArgs.from_dict(data)

    def test_to_mcp_uri_with_command(self):
        """Test converting to MCP URI with command."""
        args = MCPServerArgs(command="python", args=["server.py", "--debug"])

        uri = args.to_mcp_uri()

        assert uri == "python server.py --debug"

    def test_to_mcp_uri_with_remote_addr(self):
        """Test converting to MCP URI with remote address."""
        args = MCPServerArgs(remote_addr="http://example.com:8080")

        uri = args.to_mcp_uri()

        assert uri == "http://example.com:8080"


class TestMCPManager:
    """Test the MCPManager class."""

    def test_mcp_manager_initialization(self):
        """Test MCPManager initialization."""
        manager = MCPManager()

        assert hasattr(manager, "_ports")
        assert hasattr(manager, "_addresses")
        assert hasattr(manager, "_args")
        assert manager._ports == []
        assert manager._addresses == []
        assert manager._args == []

    def test_get_all_servers_empty(self):
        """Test getting all servers when none are running."""
        manager = MCPManager()

        servers = manager.get_all_servers()

        assert servers == []

    def test_get_all_servers_with_ports(self):
        """Test getting all servers with managed ports."""
        manager = MCPManager()
        manager._ports = [8080, 8081]
        manager._addresses = ["http://external.com:9000"]

        servers = manager.get_all_servers()

        expected = [
            "http://localhost:8080/sse",
            "http://localhost:8081/sse",
            "http://external.com:9000",
        ]
        assert servers == expected

    @pytest.mark.asyncio
    async def test_register_running_mcp_server(self):
        """Test registering a running external MCP server."""
        manager = MCPManager()

        await manager.register_running_mcp_server("http://external.server:8080")

        assert "http://external.server:8080" in manager._addresses

    @pytest.mark.asyncio
    @patch("vagents.managers.mcp_manager.find_open_port")
    @patch.object(MCPManager, "start_worker")
    async def test_start_mcp_server_basic(self, mock_start_worker, mock_find_port):
        """Test starting a basic MCP server."""
        mock_find_port.return_value = 8080
        mock_start_worker.return_value = None

        manager = MCPManager()
        args = MCPServerArgs(command="python", args=["server.py"])

        await manager.start_mcp_server(args)

        assert len(manager._args) == 1
        assert manager._args[0] == args
        assert 8080 in manager._ports
        mock_start_worker.assert_called_once()

    @pytest.mark.asyncio
    @patch("vagents.managers.mcp_manager.find_open_port")
    @patch.object(MCPManager, "start_worker")
    @patch("vagents.managers.mcp_manager.subprocess.check_output")
    async def test_start_mcp_server_wait_until_ready(
        self, mock_subprocess, mock_start_worker, mock_find_port
    ):
        """Test starting MCP server and waiting until ready."""
        mock_find_port.return_value = 8080
        mock_start_worker.return_value = None
        mock_subprocess.return_value = b"OK"

        manager = MCPManager()
        args = MCPServerArgs(command="python", args=["server.py"])

        await manager.start_mcp_server(args, wait_until_ready=True)

        mock_subprocess.assert_called_once_with(
            ["curl", "-s", "http://localhost:8080/"]
        )

    @pytest.mark.asyncio
    async def test_start_mcp_server_already_running(self):
        """Test starting an MCP server that's already running."""
        manager = MCPManager()
        args = MCPServerArgs(
            command="python", args=["server.py"], visiblity=MCPServerVisibility.PUBLIC
        )

        # Add server to args list to simulate it's already running
        manager._args.append(args)

        with patch("vagents.managers.mcp_manager.logger") as mock_logger:
            await manager.start_mcp_server(args)

            # Should log warning and not start another server
            mock_logger.warning.assert_called_once()
            assert len(manager._args) == 1  # Still only one server


class TestMCPServerVisibility:
    """Test the MCPServerVisibility enum."""

    def test_visibility_enum_values(self):
        """Test MCPServerVisibility enum values."""
        assert MCPServerVisibility.PUBLIC.value == "public"
        assert MCPServerVisibility.SESSION.value == "session"
        assert MCPServerVisibility.USER.value == "user"
