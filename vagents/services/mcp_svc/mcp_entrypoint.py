import os
import asyncio
from mcp.client.stdio import StdioServerParameters
from vagents.services.mcp_svc.sse_server import SSEServerSettings, run_sse_server


def start_mcp(
    mcp_uri: str,
    port: int = 8080,
):
    print(f"Starting MCP server with URI: {mcp_uri}")
    command = mcp_uri.split(" ")[0]
    args = mcp_uri.split(" ")[1:]
    args = " ".join(args)
    # load envs from systems
    envs = os.environ.copy()
    stdio_params = StdioServerParameters(
        command=command,
        args=[*args.split(" ")],
        env=envs,
    )
    sse_settings = SSEServerSettings(
        bind_host="0.0.0.0",
        port=port,
        allow_origins=["*"],
        log_level="INFO",
    )
    asyncio.run(
        run_sse_server(
            stdio_params,
            sse_settings,
        )
    )
