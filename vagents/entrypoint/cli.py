import typer
from typer import Typer
from vagents.utils import dataclass_to_cli
from vagents.services.vagent_svc.args import ServerArgs

app: Typer  = typer.Typer()

@app.command()
@dataclass_to_cli
def serve(
    args: ServerArgs
) -> None:
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


if __name__ == "__main__":
    app()