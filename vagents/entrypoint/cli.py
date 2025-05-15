import typer

app = typer.Typer()

@app.command()
def serve(
    port: int = typer.Option(8000, help="Port to run the server on"),
    host: str = typer.Option("0.0.0.0", help="Host to bind the server to"),
):
    from vagents.services.vagent_svc.server import start_server
    start_server(port)

@app.command()
def version():
    from vagents import __version__
    typer.echo(f"vAgents version: {__version__}")


if __name__ == "__main__":
    app()