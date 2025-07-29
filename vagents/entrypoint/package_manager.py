"""
VAgents Package Manager CLI

Command-line interface for the VAgents Package Manager that allows users to
install, manage, and execute packages from remote git repositories.
"""

import typer
import sys
import json
from pathlib import Path
from typing import List, Optional

try:
    from vagents.manager.package import PackageManager
except ImportError:
    typer.echo(
        "Error: VAgents package manager not found. Please ensure VAgents is properly installed."
    )
    sys.exit(1)

# Create the typer app for package manager commands
app = typer.Typer(
    help="VAgents Package Manager - Manage and execute code packages from git repositories"
)


def create_package_template(name: str, output_dir: str = "."):
    """Create a template package structure"""
    output_path = Path(output_dir) / name
    output_path.mkdir(parents=True, exist_ok=True)

    # Create package configuration
    config = {
        "name": name,
        "version": "1.0.0",
        "description": f"A VAgents package: {name}",
        "author": "Your Name",
        "repository_url": f"https://github.com/yourusername/{name}.git",
        "entry_point": f"{name}.main",
        "dependencies": [],
        "python_version": ">=3.8",
        "tags": ["vagents", "package"],
    }

    config_file = output_path / "package.yaml"
    try:
        import yaml

        with open(config_file, "w") as f:
            yaml.dump(config, f, default_flow_style=False)
    except ImportError:
        # Fallback to JSON if PyYAML is not available
        import json

        config_file = output_path / "package.json"
        with open(config_file, "w") as f:
            json.dump(config, f, indent=2)

    # Create main module
    main_code = f'''"""
{name} - A VAgents Package

This is the main module for the {name} package.
"""

def main(*args, **kwargs):
    """
    Main entry point for the {name} package

    Args:
        *args: Positional arguments
        **kwargs: Keyword arguments

    Returns:
        dict: Result of the package execution
    """
    return {{
        "message": "Hello from {name} package!",
        "args": args,
        "kwargs": kwargs
    }}


if __name__ == "__main__":
    result = main()
    print(result)
'''

    with open(output_path / f"{name}.py", "w") as f:
        f.write(main_code)

    # Create README
    readme = f"""# {name}

A VAgents package for {name}.

## Description

{config["description"]}

## Installation

Install this package using the VAgents package manager:

```bash
vagents pm install {config["repository_url"]}
```

## Usage

```python
from vagents.manager.package import PackageManager

pm = PackageManager()
result = pm.execute_package("{name}")
print(result)
```

## Configuration

See `package.yaml` for package configuration.

## Development

To modify this package:

1. Clone the repository
2. Make your changes
3. Update the version in `package.yaml`
4. Commit and push changes
5. Users can update with `vagents pm update {name}`
"""

    with open(output_path / "README.md", "w") as f:
        f.write(readme)

    return output_path


@app.command()
def install(
    repo_url: str = typer.Argument(..., help="Git repository URL"),
    branch: str = typer.Option(
        "main", "--branch", "-b", help="Git branch (default: main)"
    ),
    force: bool = typer.Option(
        False, "--force", "-f", help="Force reinstall if package exists"
    ),
):
    """Install a package from a git repository."""
    try:
        pm = PackageManager()

        typer.echo(f"Installing package from {repo_url}...")
        success = pm.install_package(repo_url, branch, force)

        if success:
            typer.echo(
                f"✅ Successfully installed package from {repo_url}", color="green"
            )
        else:
            typer.echo(f"❌ Failed to install package from {repo_url}", color="red")
            raise typer.Exit(1)

    except Exception as e:
        typer.echo(f"❌ Error: {e}", color="red")
        raise typer.Exit(1)


@app.command()
def uninstall(
    package_name: str = typer.Argument(..., help="Name of the package to uninstall")
):
    """Uninstall a package."""
    try:
        pm = PackageManager()

        typer.echo(f"Uninstalling package '{package_name}'...")
        success = pm.uninstall_package(package_name)

        if success:
            typer.echo(
                f"✅ Successfully uninstalled package '{package_name}'", color="green"
            )
        else:
            typer.echo(f"❌ Failed to uninstall package '{package_name}'", color="red")
            raise typer.Exit(1)

    except Exception as e:
        typer.echo(f"❌ Error: {e}", color="red")
        raise typer.Exit(1)


@app.command()
def update(
    package_name: str = typer.Argument(..., help="Name of the package to update"),
    branch: str = typer.Option(
        "main", "--branch", "-b", help="Git branch (default: main)"
    ),
):
    """Update a package to the latest version."""
    try:
        pm = PackageManager()

        typer.echo(f"Updating package '{package_name}'...")
        success = pm.update_package(package_name, branch)

        if success:
            typer.echo(
                f"✅ Successfully updated package '{package_name}'", color="green"
            )
        else:
            typer.echo(f"❌ Failed to update package '{package_name}'", color="red")
            raise typer.Exit(1)

    except Exception as e:
        typer.echo(f"❌ Error: {e}", color="red")
        raise typer.Exit(1)


@app.command()
def list(
    format: str = typer.Option(
        "table", "--format", "-f", help="Output format: table, json"
    ),
    verbose: bool = typer.Option(
        False, "--verbose", "-v", help="Show detailed information"
    ),
):
    """List installed packages."""
    try:
        pm = PackageManager()
        packages = pm.list_packages()

        if not packages:
            typer.echo("No packages installed.")
            return

        if format == "json":
            typer.echo(json.dumps(packages, indent=2))
        else:
            if verbose:
                # Detailed table format
                typer.echo(
                    f"{'Name':<20} {'Version':<10} {'Author':<15} {'Description':<40}"
                )
                typer.echo("-" * 85)
                for name, info in packages.items():
                    desc = info.get("description", "")
                    if len(desc) > 37:
                        desc = desc[:37] + "..."
                    author = info.get("author", "Unknown")[:12]
                    typer.echo(
                        f"{name:<20} {info.get('version', 'N/A'):<10} {author:<15} {desc:<40}"
                    )
            else:
                # Simple table format
                typer.echo(f"{'Name':<20} {'Version':<10} {'Description':<50}")
                typer.echo("-" * 80)
                for name, info in packages.items():
                    desc = info.get("description", "")
                    if len(desc) > 47:
                        desc = desc[:47] + "..."
                    typer.echo(
                        f"{name:<20} {info.get('version', 'N/A'):<10} {desc:<50}"
                    )

    except Exception as e:
        typer.echo(f"❌ Error: {e}", color="red")
        raise typer.Exit(1)


@app.command()
def info(package_name: str = typer.Argument(..., help="Name of the package")):
    """Show detailed package information."""
    try:
        pm = PackageManager()
        package_info = pm.get_package_info(package_name)

        if package_info:
            typer.echo(json.dumps(package_info, indent=2))
        else:
            typer.echo(f"❌ Package '{package_name}' not found", color="red")
            raise typer.Exit(1)

    except Exception as e:
        typer.echo(f"❌ Error: {e}", color="red")
        raise typer.Exit(1)


@app.command()
def search(
    query: Optional[str] = typer.Option(None, "--query", "-q", help="Search query"),
    tags: Optional[List[str]] = typer.Option(
        None, "--tags", "-t", help="Filter by tags"
    ),
):
    """Search packages by name, description, or tags."""
    try:
        pm = PackageManager()
        packages = pm.search_packages(query, tags)

        if not packages:
            typer.echo("No packages found matching the criteria.")
            return

        typer.echo(f"{'Name':<20} {'Version':<10} {'Description':<50}")
        typer.echo("-" * 80)
        for name, info in packages.items():
            desc = info.get("description", "")
            if len(desc) > 47:
                desc = desc[:47] + "..."
            typer.echo(f"{name:<20} {info.get('version', 'N/A'):<10} {desc:<50}")

    except Exception as e:
        typer.echo(f"❌ Error: {e}", color="red")
        raise typer.Exit(1)


@app.command()
def execute(
    package_name: str = typer.Argument(..., help="Name of the package to execute"),
    args: Optional[List[str]] = typer.Option(
        None, "--args", help="Arguments to pass to the package"
    ),
    kwargs_json: Optional[str] = typer.Option(
        None, "--kwargs", help="JSON string of keyword arguments"
    ),
    output_format: str = typer.Option(
        "pretty", "--output", "-o", help="Output format: pretty, json"
    ),
):
    """Execute a package."""
    try:
        pm = PackageManager()

        # Parse arguments
        execute_args = args or []
        execute_kwargs = {}

        if kwargs_json:
            try:
                execute_kwargs = json.loads(kwargs_json)
            except json.JSONDecodeError:
                typer.echo("❌ Invalid JSON in --kwargs parameter", color="red")
                raise typer.Exit(1)

        typer.echo(f"Executing package '{package_name}'...")

        # Execute the package
        result = pm.execute_package(package_name, *execute_args, **execute_kwargs)

        # Display results
        if output_format == "json":
            typer.echo(json.dumps(result, indent=2, default=str))
        else:
            typer.echo("✅ Package executed successfully!", color="green")
            typer.echo("\n📋 Execution Result:")
            typer.echo(json.dumps(result, indent=2, default=str))

    except ValueError as e:
        typer.echo(f"❌ Package not found: {e}", color="red")
        raise typer.Exit(1)
    except Exception as e:
        typer.echo(f"❌ Error executing package: {e}", color="red")
        raise typer.Exit(1)


@app.command("create-template")
def create_template(
    name: str = typer.Argument(..., help="Name of the package"),
    output_dir: str = typer.Option(
        ".", "--output-dir", "-o", help="Output directory (default: current)"
    ),
):
    """Create a new package template."""
    try:
        package_path = create_package_template(name, output_dir)
        typer.echo(f"✅ Package template '{name}' created successfully!", color="green")
        typer.echo(f"📁 Location: {package_path}")
        typer.echo(f"\n📝 Next steps:")
        typer.echo(
            f"  1. Edit {package_path}/{name}.py to implement your functionality"
        )
        typer.echo(f"  2. Update {package_path}/package.yaml with your package details")
        typer.echo(f"  3. Initialize git repository and push to remote")
        typer.echo(f"  4. Install with: vagents pm install <your-repo-url>")

    except Exception as e:
        typer.echo(f"❌ Error creating template: {e}", color="red")
        raise typer.Exit(1)


@app.command()
def status():
    """Show package manager status and statistics."""
    try:
        pm = PackageManager()
        packages = pm.list_packages()

        typer.echo("📊 VAgents Package Manager Status")
        typer.echo("-" * 40)
        typer.echo(f"📁 Base directory: {pm.base_path}")
        typer.echo(f"📦 Installed packages: {len(packages)}")

        if packages:
            typer.echo(f"\n📋 Package Summary:")
            for name, info in packages.items():
                status_icon = "✅" if info.get("status") == "installed" else "⚠️"
                typer.echo(f"  {status_icon} {name} v{info.get('version', 'N/A')}")

        # Show disk usage
        try:
            total_size = sum(
                sum(
                    f.stat().st_size
                    for f in Path(pm.registry.packages_dir).glob("**/*")
                    if f.is_file()
                )
                for _ in [None]  # Just to make it a generator expression
            )
            size_mb = total_size / (1024 * 1024)
            typer.echo(f"💾 Total disk usage: {size_mb:.2f} MB")
        except Exception:
            pass

    except Exception as e:
        typer.echo(f"❌ Error: {e}", color="red")
        raise typer.Exit(1)


if __name__ == "__main__":
    app()
