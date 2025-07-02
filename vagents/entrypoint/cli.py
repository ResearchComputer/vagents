import typer
from typer import Typer
from vagents.utils import dataclass_to_cli
from vagents.services.vagent_svc.args import ServerArgs

from typing import Optional, List

app: Typer = typer.Typer()


@app.command()
@dataclass_to_cli
def serve(args: ServerArgs) -> None:
    """Spin up the server"""
    from vagents.services.vagent_svc.server import start_server

    start_server(args)


@app.command()
def start_mcp(mcp_uri: str, port: int = 8080, debug: bool = False):
    from vagents.services import start_mcp

    if debug:
        # print envs variables
        import os

        print("--- envs:")
        for key, value in os.environ.items():
            print(f"{key}: {value}")

    start_mcp(
        mcp_uri=mcp_uri,
        port=port,
    )


@app.command()
def version() -> None:
    from vagents import __version__

    typer.echo(f"vAgents version: {__version__}")


@app.command()
def register(
    module_path: str,
    host: str = "http://localhost:8080",
    mcp_configs: Optional[List[str]] = None,
) -> None:
    """Register modules with the vagents server"""
    typer.echo("Registering modules with the vagents server...")
    from vagents.utils import VClient

    client: VClient = VClient(base_url=host, api_key="")
    client.register_module(path=module_path, force=False, mcp_configs=None)


if __name__ == "__main__":
    app()
