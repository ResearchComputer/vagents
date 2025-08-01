import typer
from vagents import __version__
from . import package_manager

app = typer.Typer(
    help="VAgents CLI - A framework for building scalable and efficient multi-tenant agentic AI systems"
)
app.add_typer(package_manager.app, name="pm", help="Package manager commands")


@app.command()
def chat():
    """Start the interactive chat interface."""
    from vagents.utils.chat import main as chat_main

    chat_main()


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
    typer.echo(
        "  � chat        - Start interactive chat interface with LLM and packages"
    )
    typer.echo("  �📦 pm          - Package manager (install, list, execute packages)")
    typer.echo("  📋 version     - Show version information")
    typer.echo("  ℹ️  info        - Show this information")
    typer.echo("\nFor help with any command, use: vagents <command> --help")
    typer.echo("\n💬 Chat Interface:")
    typer.echo("  vagents chat                              # Start interactive chat")
    typer.echo("  In chat: /help                            # Show chat commands")
    typer.echo("  In chat: /model gpt-4                     # Switch LLM model")
    typer.echo("  In chat: /pkg <name> <message>            # Execute package")
    typer.echo("\n📦 Package Manager Examples:")
    typer.echo("  vagents pm list                           # List installed packages")
    typer.echo("  vagents pm install <repo-url>             # Install a package")
    typer.echo("  vagents pm execute <package-name>         # Execute a package")
    typer.echo("  vagents pm create-template my-package     # Create package template")
    typer.echo("\n🚀 Get started:")
    typer.echo("  vagents chat                              # Start chatting!")
    typer.echo(
        "  vagents pm create-template my-first-package  # Create your first package"
    )


# For backward compatibility, keep the main command but make it an alias to info
@app.command(hidden=True)
def main():
    """Alias for info command."""
    info()


if __name__ == "__main__":
    app()
