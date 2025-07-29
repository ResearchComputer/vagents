import typer
from vagents import __version__
from . import package_manager

app = typer.Typer(
    help="VAgents CLI - A framework for building scalable and efficient multi-tenant agentic AI systems"
)
app.add_typer(package_manager.app, name="pm", help="Package manager commands")


@app.command()
def version():
    """Display the version of the VAgents package."""
    typer.echo(f"VAgents version: {__version__}")


@app.command()
def info():
    """Welcome message and basic information."""
    typer.echo("🤖 Welcome to VAgents CLI!")
    typer.echo(
        "\nVAgents is a framework for building scalable and efficient multi-tenant agentic AI systems."
    )
    typer.echo("\n📋 Available commands:")
    typer.echo("  📦 pm          - Package manager (install, list, execute packages)")
    typer.echo("  📋 version     - Show version information")
    typer.echo("  ℹ️  info        - Show this information")
    typer.echo("\nFor help with any command, use: vagents <command> --help")
    typer.echo("\n📦 Package Manager Examples:")
    typer.echo("  vagents pm list                           # List installed packages")
    typer.echo("  vagents pm install <repo-url>             # Install a package")
    typer.echo("  vagents pm execute <package-name>         # Execute a package")
    typer.echo("  vagents pm create-template my-package     # Create package template")
    typer.echo("\n🚀 Get started by creating your first package:")
    typer.echo("  vagents pm create-template my-first-package")


# For backward compatibility, keep the main command but make it an alias to info
@app.command(hidden=True)
def main():
    """Alias for info command."""
    info()


if __name__ == "__main__":
    app()
