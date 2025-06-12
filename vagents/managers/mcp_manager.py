import uuid
import time
import subprocess
from enum import Enum
from typing import Optional, List
from dataclasses import dataclass
from vagents.utils import find_open_port, logger

from .worker_manager import DockerWorkerManager

DEFAULT_MCP_IMAGE = "ghcr.io/xiaozheyao/vagent.mcp:0.0.1"

class MCPServerVisibility(Enum):
    PUBLIC = "public"
    SESSION = "session"
    USER = "user"

@dataclass
class MCPServerArgs:
    command: Optional[str] = None
    args: Optional[List[str]] = None
    remote_addr: Optional[str] = None
    visiblity: MCPServerVisibility = MCPServerVisibility.PUBLIC
    envs: Optional[dict] = None

    @classmethod
    def from_mcp_uri(cls, mcp_uri: str) -> "MCPServerArgs":
        command = mcp_uri.split("://")[0]
        args = mcp_uri.split("://")[1].split("/")
        return cls(command=command, args=args)

    def to_mcp_uri(self) -> str:
        if self.remote_addr:
            return self.remote_addr
        return f"{self.command} {' '.join(self.args)}"

    @classmethod
    def from_dict(cls, data: dict) -> "MCPServerArgs":
        if "remote_addr" in data:
            return cls(remote_addr=data["remote_addr"])
        elif "command" in data and "args" in data:
            return cls(
                command=data["command"],
                args=data.get("args", []),
                visiblity=MCPServerVisibility(data.get("visiblity", "public")),
                envs=data.get("envs", None),
            )
        else:
            raise ValueError("Invalid MCPServerArgs data format. Must contain 'remote_addr' or 'command' and 'args'.")

class MCPManager(DockerWorkerManager):
    def __init__(self):
        super().__init__()
        self._ports = []
        self._addresses = []
        self._args: List[MCPServerArgs] = []

    def get_all_servers(self) -> List[str]:
        managed_servers = [
            f"http://localhost:{port}/sse" for port in self._ports
        ]
        outside_servers = self._addresses
        return managed_servers + outside_servers

    async def register_running_mcp_server(
        self,
        address: str,
    ):
        self._addresses.append(address)

    async def start_mcp_server(
        self,
        mcp_args: MCPServerArgs,
        image: Optional[str] = None,
        wait_until_ready: bool = False,
    ):
        public_servers = [
            x.to_mcp_uri()
            for x in self._args
            if x.visiblity == MCPServerVisibility.PUBLIC
            and x.to_mcp_uri() == mcp_args.to_mcp_uri()
        ]
        if len(public_servers) > 0:
            logger.warning(
                f"Server {mcp_args.to_mcp_uri()} is already running and visible."
            )
            return
        logger.info(f"Running servers: {[x.to_mcp_uri() for x in self._args]}")
        self._args.append(mcp_args)

        worker_id = f"mcp-{uuid.uuid4().hex[:4]}"
        mcp_uri = mcp_args.to_mcp_uri()
        worker_command = ["bash", "-c", f"vagents start-mcp '{mcp_uri}' --debug"]
        host_port = find_open_port()

        await self.start_worker(
            worker_id,
            worker_owner=worker_id,
            worker_image=image or DEFAULT_MCP_IMAGE,
            worker_command=worker_command,
            host_port=host_port,
            bind_tmp=True,
            envs=mcp_args.envs,
        )
        if wait_until_ready:
            while True:
                try:
                    subprocess.check_output(
                        ["curl", "-s", f"http://localhost:{host_port}/"]
                    )
                    logger.info(f"MCP server {mcp_uri} is ready on port {host_port}")
                    break
                except subprocess.CalledProcessError:
                    logger.info(
                        f"Waiting for MCP server {mcp_uri} to be ready on port {host_port}..."
                    )
                    time.sleep(1)
        self._ports.append(host_port)
