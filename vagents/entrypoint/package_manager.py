"""
VAgents Package Manager CLI

Command-line interface for the VAgents Package Manager that allows users to
install, manage, and execute packages from remote git repositories.
"""

import typer
import sys
import json
from pathlib import Path
from typing import List, Optional, Any, Dict
import sys
from rich.console import Console
from rich.markdown import Markdown
from rich.panel import Panel
from rich.json import JSON
from rich.tree import Tree
from rich.table import Table

try:
    from vagents.manager.package import PackageManager
except ImportError:
    typer.echo(
        "Error: VAgents package manager not found. Please ensure VAgents is properly installed."
    )
    sys.exit(1)

# Create console for rich output
console = Console()

# Default packages repository for bare name resolution
DEFAULT_PACKAGES_REPO = "https://github.com/vagents-ai/packages"


def _looks_like_url(value: str) -> bool:
    return (
        value.startswith("http://")
        or value.startswith("https://")
        or value.startswith("git@")
    )


def _looks_like_path(value: str) -> bool:
    return (
        value in (".", "..")
        or value.startswith("/")
        or value.startswith("./")
        or value.startswith("../")
        or ("/" in value)
    )


# Create the typer app for package manager commands
app = typer.Typer(
    help="VAgents Package Manager - Manage and execute code packages from git repositories",
    context_settings={"allow_extra_args": True, "allow_interspersed_args": False},
)


def format_result_rich(result: Any, package_name: str) -> None:
    """Format and display results using rich formatting"""
    # Create a panel with the package execution result
    console.print(
        f"\n[bold green]✅ Package '{package_name}' executed successfully![/bold green]"
    )
    # Display result in a nice panel
    if isinstance(result, dict):
        # Create a tree structure for dictionary results
        tree = Tree(f"[bold blue]📋 Execution Result[/bold blue]")
        _add_dict_to_tree(tree, result)
        console.print(
            Panel(
                tree, title=f"[bold]{package_name}[/bold] Output", border_style="green"
            )
        )
    elif isinstance(result, str):
        # Display string as markdown if it looks like markdown, otherwise as text
        if any(marker in result for marker in ["#", "*", "`", "-", "|"]):
            markdown = Markdown(result)
            console.print(
                Panel(
                    markdown,
                    title=f"[bold]{package_name}[/bold] Output",
                    border_style="green",
                )
            )
        else:
            console.print(
                Panel(
                    result,
                    title=f"[bold]{package_name}[/bold] Output",
                    border_style="green",
                )
            )
    else:
        # For other types, convert to string and display
        console.print(
            Panel(
                str(result),
                title=f"[bold]{package_name}[/bold] Output",
                border_style="green",
            )
        )


def format_result_markdown(result: Any, package_name: str) -> str:
    """Format results as markdown string"""
    markdown_content = f"# Package Execution Result: {package_name}\n\n"
    markdown_content += "## ✅ Status: Success\n\n"

    if isinstance(result, dict):
        markdown_content += "## 📋 Output\n\n"
        markdown_content += _dict_to_markdown(result)
    elif isinstance(result, list) or isinstance(result, tuple):
        markdown_content += "## 📋 Output (List)\n\n"
        for i, item in enumerate(result):
            markdown_content += f"### Item {i + 1}\n\n"
            if isinstance(item, dict):
                markdown_content += _dict_to_markdown(item)
            else:
                markdown_content += f"```\n{item}\n```\n\n"
    elif isinstance(result, str):
        markdown_content += "## 📋 Output\n\n"
        if any(marker in result for marker in ["#", "*", "`", "-", "|"]):
            # Already markdown-like content
            markdown_content += result + "\n\n"
        else:
            # Plain text, wrap in code block
            markdown_content += f"```\n{result}\n```\n\n"
    else:
        markdown_content += "## 📋 Output\n\n"
        markdown_content += f"```\n{str(result)}\n```\n\n"

    return markdown_content


def _add_dict_to_tree(
    tree: Tree, data: Dict, max_depth: int = 3, current_depth: int = 0
) -> None:
    """Recursively add dictionary items to a tree"""
    if current_depth >= max_depth:
        tree.add("[dim]... (max depth reached)[/dim]")
        return

    for key, value in data.items():
        if isinstance(value, dict):
            if value:  # Only add non-empty dicts
                branch = tree.add(f"[bold cyan]{key}[/bold cyan]")
                _add_dict_to_tree(branch, value, max_depth, current_depth + 1)
            else:
                tree.add(f"[bold cyan]{key}[/bold cyan]: [dim]{{}}[/dim]")
        elif isinstance(value, list) or isinstance(value, tuple):
            if value:  # Only add non-empty lists
                branch = tree.add(
                    f"[bold yellow]{key}[/bold yellow] ([dim]{len(value)} items[/dim])"
                )
                for i, item in enumerate(value[:5]):  # Limit to first 5 items
                    if isinstance(item, dict):
                        item_branch = branch.add(f"[dim]Item {i+1}[/dim]")
                        _add_dict_to_tree(
                            item_branch, item, max_depth, current_depth + 1
                        )
                    else:
                        branch.add(f"[dim]Item {i+1}:[/dim] {str(item)[:100]}")
                if len(value) > 5:
                    branch.add("[dim]... and more[/dim]")
            else:
                tree.add(f"[bold yellow]{key}[/bold yellow]: [dim][][/dim]")
        else:
            # Truncate long values
            value_str = str(value)
            if len(value_str) > 100:
                value_str = value_str[:97] + "..."
            tree.add(f"[bold green]{key}[/bold green]: {value_str}")


def _dict_to_markdown(data: Dict, level: int = 0) -> str:
    """Convert dictionary to markdown format"""
    markdown = ""
    indent = "  " * level

    for key, value in data.items():
        if isinstance(value, dict):
            markdown += f"{indent}- **{key}**:\n"
            markdown += _dict_to_markdown(value, level + 1)
        elif isinstance(value, list) or isinstance(value, tuple):
            markdown += f"{indent}- **{key}**: [{len(value)} items]\n"
            for i, item in enumerate(value[:3]):  # Show first 3 items
                if isinstance(item, dict):
                    markdown += f"{indent}  - Item {i+1}:\n"
                    markdown += _dict_to_markdown(item, level + 2)
                else:
                    markdown += f"{indent}  - `{str(item)[:50]}`\n"
            if len(value) > 3:
                markdown += f"{indent}  - ... and {len(value) - 3} more\n"
        else:
            value_str = str(value)
            if len(value_str) > 200:
                value_str = value_str[:197] + "..."
            markdown += f"{indent}- **{key}**: `{value_str}`\n"

    return markdown


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
        "arguments": [
            {
                "name": "verbose",
                "type": "bool",
                "help": "Enable verbose output",
                "short": "v",
            },
            {
                "name": "config",
                "type": "str",
                "help": "Configuration file path",
                "short": "c",
            },
        ],
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

def main(verbose=False, config=None, input=None, stdin=None, **kwargs):
    """
    Main entry point for the {name} package

    Args:
        verbose (bool): Enable verbose output
        config (str): Configuration file path
        input (str): Input content (from stdin when using pipes)
        stdin (str): Standard input content (alias for input)
        **kwargs: Additional keyword arguments

    Returns:
        dict: Result of the package execution
    """
    # Handle stdin input (input and stdin are aliases)
    content = input or stdin

    result = {{
        "message": f"Hello from {name} package!",
        "verbose": verbose,
        "config": config,
        "has_input": content is not None,
        "input_length": len(content) if content else 0,
        "additional_args": kwargs
    }}

    if verbose:
        print(f"Verbose mode enabled for {name}")
        if config:
            print(f"Using config file: {{config}}")
        if content:
            print(f"Processing {{len(content)}} characters of input")
            print(f"Input preview: {{repr(content[:100])}}")

    # Process the input content if provided
    if content:
        result["processed_input"] = {{
            "length": len(content),
            "lines": len(content.splitlines()) if content else 0,
            "words": len(content.split()) if content else 0,
            "first_line": content.splitlines()[0] if content and content.splitlines() else None
        }}

        # Example processing based on content
        if "error" in content.lower():
            result["analysis"] = "Input contains error messages"
        elif "success" in content.lower():
            result["analysis"] = "Input contains success messages"
        else:
            result["analysis"] = "Input analyzed successfully"

    return result


if __name__ == "__main__":
    # Example: python {name}.py --verbose --config myconfig.json
    # Example with pipe: echo "test data" | python {name}.py --verbose
    import sys

    # Check for stdin input when run directly
    stdin_content = None
    if not sys.stdin.isatty():
        stdin_content = sys.stdin.read().strip()

    result = main(verbose=True, input=stdin_content)
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

### Command Line Interface

```bash
# Basic usage
vagents pm run {name}

# With verbose output
vagents pm run {name} --verbose

# With configuration file
vagents pm run {name} --config myconfig.json

# Combined options
vagents pm run {name} --verbose --config myconfig.json

# Using with pipes
cat data.txt | vagents pm run {name} --verbose
echo "process this" | vagents pm run {name}

# Using vibe runner (simpler syntax)
vibe run {name} --verbose
cat results.json | vibe run {name} --config analysis.yaml
```

### Programmatic Usage

```python
from vagents.manager.package import PackageManager

pm = PackageManager()

# Basic execution
result = pm.execute_package("{name}", verbose=True, config="myconfig.json")
print(result)

# With input content
content = "data to process"
result = pm.execute_package("{name}", input=content, verbose=True)
print(result)
```

## Pipe Support

This package supports reading from stdin when used with pipes:

```bash
# Process file content
cat myfile.txt | vibe run {name}

# Process command output
ls -la | vibe run {name} --verbose

# Chain with other commands
curl -s https://api.example.com/data | vibe run {name} --config api.yaml
```

When using pipes, the stdin content is automatically passed to your package's main function as the `input` parameter (also available as `stdin`).

## CLI Arguments

This package supports the following command line arguments:

- `--verbose, -v`: Enable verbose output (flag)
- `--config, -c`: Configuration file path (string)

## Configuration

See `package.yaml` for package configuration, including argument definitions.

## Development

To modify this package:

1. Clone the repository
2. Make your changes to the main function and argument definitions
3. Update the version in `package.yaml`
4. Commit and push changes
5. Users can update with `vagents pm update {name}`

### Adding New Arguments

To add new CLI arguments, update the `arguments` section in `package.yaml`:

```yaml
arguments:
  - name: "new_arg"
    type: "str"
    help: "Description of the new argument"
    short: "n"
    required: false
    default: null
```

Then update your main function to accept the new parameter.
"""

    with open(output_path / "README.md", "w") as f:
        f.write(readme)

    return output_path


@app.command()
def install(
    repo_url: str = typer.Argument(
        ..., help="Git repository URL or local directory path"
    ),
    branch: str = typer.Option(
        "main", "--branch", "-b", help="Git branch (default: main)"
    ),
    force: bool = typer.Option(
        False, "--force", "-f", help="Force reinstall if package exists"
    ),
):
    """Install a package from a git repository, local directory, or bare name.

    Examples:
        vagents pm install https://github.com/user/repo.git
        vagents pm install https://github.com/user/repo.git/path/to/subdir
        vagents pm install ./local/package
        vagents pm install code-review  # resolves to {DEFAULT_PACKAGES_REPO}/code-review
    """
    try:
        pm = PackageManager()

        path = Path(repo_url).expanduser()
        if _looks_like_path(repo_url) and path.exists() and path.is_dir():
            typer.echo(f"Installing package from local directory {path}...")
            success = pm.install_local_package(str(path), force)
        else:
            # Resolve bare name to default packages repo subdirectory
            resolved_spec = repo_url
            if not _looks_like_url(repo_url):
                resolved_spec = (
                    f"{DEFAULT_PACKAGES_REPO.rstrip('/')}/{repo_url.lstrip('/')}"
                )
                typer.echo(f"Resolved package name to: {resolved_spec}")
            typer.echo(f"Installing package from {resolved_spec}...")
            success = pm.install_package(resolved_spec, branch, force)

        if success:
            typer.echo(
                f"✅ Successfully installed package from {resolved_spec}", color="green"
            )
        else:
            typer.echo(f"❌ Failed to install package from {resolved_spec}", color="red")
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


@app.command(name="list")
def list_cmd(
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


@app.command(
    context_settings={"allow_extra_args": True, "allow_interspersed_args": False}
)
def run(
    ctx: typer.Context,
    package_name: str = typer.Argument(..., help="Name of the package to execute"),
):
    """Execute a package with its defined CLI arguments.

    This command dynamically parses arguments based on the package's argument definition.
    Use 'vagents pm help-package <name>' to see available arguments for a package.

    Examples:
        vagents pm run code-review --history 2 --verbose
        vagents pm run analyzer --config config.json --output results.txt
    """
    try:
        # Import here to avoid circular imports
        import argparse

        pm = PackageManager()
        package_info = pm.get_package_info(package_name)

        if not package_info:
            typer.echo(f"❌ Package '{package_name}' not found", color="red")
            raise typer.Exit(1)

        # Get remaining arguments that weren't consumed by typer
        remaining_args = ctx.args

        # Create argument parser for this package
        parser = argparse.ArgumentParser(
            prog=f"vagents pm run {package_name}",
            description=package_info.get(
                "description", f"Execute {package_name} package"
            ),
            add_help=False,  # We'll handle help display ourselves
        )

        # Add format option
        parser.add_argument(
            "--format",
            "-f",
            choices=["rich", "plain", "json", "markdown"],
            default="rich",
            help="Output format (default: rich)",
        )

        # Add package-specific arguments
        arguments = package_info.get("arguments", [])
        for arg_def in arguments:
            name = arg_def.get("name")
            if not name:
                continue

            arg_type = arg_def.get("type", "str")
            help_text = arg_def.get("help", "")
            default = arg_def.get("default")
            required = arg_def.get("required", False)
            choices = arg_def.get("choices", [])
            short = arg_def.get("short")

            # Build argument names
            arg_names = [f"--{name}"]
            if short:
                arg_names.append(f"-{short}")

            # Build kwargs for add_argument
            kwargs = {
                "help": help_text,
                "default": default,
            }

            # Handle different argument types
            if arg_type == "bool":
                kwargs["action"] = "store_true"
            elif arg_type == "int":
                kwargs["type"] = int
            elif arg_type == "float":
                kwargs["type"] = float
            elif arg_type == "list":
                kwargs["nargs"] = "*"
            else:  # str
                kwargs["type"] = str

            if choices:
                kwargs["choices"] = choices

            if required and arg_type != "bool":
                kwargs["required"] = True

            parser.add_argument(*arg_names, **kwargs)

        # Attempt to read stdin if piped
        stdin_input = None
        try:
            if not sys.stdin.isatty():
                stdin_input = sys.stdin.read()
        except Exception:
            stdin_input = None

        # Parse the remaining arguments
        try:
            if "--help" in remaining_args or "-h" in remaining_args:
                parser.print_help()
                raise typer.Exit(0)

            parsed_args = parser.parse_args(remaining_args)
        except SystemExit as e:
            if e.code == 0:
                raise typer.Exit(0)
            else:
                typer.echo(
                    f"❌ Invalid arguments for package {package_name}", color="red"
                )
                parser.print_help()
                raise typer.Exit(1)

        # Extract format and remove it from package args
        format_type = parsed_args.format
        delattr(parsed_args, "format")

        # Convert to dict and remove None values
        package_kwargs = {k: v for k, v in vars(parsed_args).items() if v is not None}

        # If we have stdin content and the package did not explicitly receive an input param, add it
        if stdin_input:
            if (
                "input" not in package_kwargs
                and "stdin" not in package_kwargs
                and "content" not in package_kwargs
            ):
                package_kwargs["input"] = stdin_input

        # Execute package
        result = pm.execute_package(package_name, **package_kwargs)

        # Display results based on format
        if format_type == "json":
            typer.echo(json.dumps(result, indent=2, default=str))
        elif format_type == "markdown":
            markdown_output = format_result_markdown(result, package_name)
            markdown = Markdown(markdown_output)
            console.print(markdown)
        elif format_type == "rich":
            format_result_rich(result, package_name)
        elif format_type == "plain":
            # Provide a short success message before the raw/plain output
            typer.echo("✅ Package executed successfully!")
            typer.echo(f"\n📋 Execution Result for '{package_name}':")
            typer.echo("-" * 50)
            if isinstance(result, dict) or isinstance(result, list):
                typer.echo(json.dumps(result, indent=2, default=str))
            else:
                typer.echo(str(result))

    except ValueError as e:
        typer.echo(f"❌ Error: {e}", color="red")
        raise typer.Exit(1)
    except Exception as e:
        import traceback

        traceback.print_exc()
        typer.echo(f"❌ Error executing package: {e}", color="red")
        raise typer.Exit(1)

        # Display results based on format
        if format_type == "json":
            typer.echo(json.dumps(result, indent=2, default=str))
        elif format_type == "markdown":
            markdown_output = format_result_markdown(result, package_name)
            markdown = Markdown(markdown_output)
            console.print(markdown)
        elif format_type == "rich":
            format_result_rich(result, package_name)
        elif format_type == "plain":
            typer.echo("✅ Package executed successfully!", color="green")
            typer.echo(f"\n📋 Execution Result for '{package_name}':")
            typer.echo("-" * 50)
            if isinstance(result, dict) or isinstance(result, list):
                typer.echo(json.dumps(result, indent=2, default=str))
            else:
                typer.echo(str(result))

    except ValueError as e:
        typer.echo(f"❌ Package not found: {e}", color="red")
        raise typer.Exit(1)
    except Exception as e:
        import traceback

        traceback.print_exc()
        typer.echo(f"❌ Error executing package: {e}", color="red")
        raise typer.Exit(1)


@app.command()
def run_legacy(
    package_name: str = typer.Argument(..., help="Name of the package to execute"),
    args: Optional[List[str]] = typer.Option(
        None, "--args", help="Arguments to pass to the package"
    ),
    kwargs_json: Optional[str] = typer.Option(
        None, "--kwargs", help="JSON string of keyword arguments"
    ),
    format: str = typer.Option(
        "rich", "--format", "-f", help="Output format: rich, plain, json, markdown"
    ),
):
    """Execute a package with legacy argument parsing (for backward compatibility)."""
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

        # Execute the package
        result = pm.execute_package(package_name, *execute_args, **execute_kwargs)

        # Display results based on format
        if format == "json":
            typer.echo(json.dumps(result, indent=2, default=str))
        elif format == "markdown":
            markdown_output = format_result_markdown(result, package_name)
            markdown = Markdown(markdown_output)
            console.print(markdown)
        elif format == "rich":
            format_result_rich(result, package_name)
        elif format == "plain":
            typer.echo("✅ Package executed successfully!", color="green")
            typer.echo(f"\n📋 Execution Result for '{package_name}':")
            typer.echo("-" * 50)
            if isinstance(result, dict) or isinstance(result, list):
                typer.echo(json.dumps(result, indent=2, default=str))
            else:
                typer.echo(str(result))
        else:
            typer.echo(
                f"❌ Unknown format: {format}. Use: rich, plain, json, markdown",
                color="red",
            )
            raise typer.Exit(1)

    except ValueError as e:
        typer.echo(f"❌ Package not found: {e}", color="red")
        raise typer.Exit(1)
    except Exception as e:
        import traceback

        traceback.print_exc()
        typer.echo(f"❌ Error executing package: {e}", color="red")
        raise typer.Exit(1)


@app.command()
def help_package(
    package_name: str = typer.Argument(..., help="Name of the package to show help for")
):
    """Show help for a specific package including its CLI arguments."""
    try:
        pm = PackageManager()
        package_info = pm.get_package_info(package_name)

        if not package_info:
            typer.echo(f"❌ Package '{package_name}' not found", color="red")
            raise typer.Exit(1)

        # Display package information
        typer.echo(f"\n📦 Package: {package_name}")
        typer.echo(
            f"📋 Description: {package_info.get('description', 'No description')}"
        )
        typer.echo(f"👤 Author: {package_info.get('author', 'Unknown')}")
        typer.echo(f"🏷️  Version: {package_info.get('version', 'Unknown')}")

        arguments = package_info.get("arguments", [])
        if arguments:
            typer.echo(f"\n🔧 Available Arguments:")
            typer.echo("-" * 50)

            for arg in arguments:
                arg_name = arg.get("name", "unnamed")
                arg_type = arg.get("type", "str")
                arg_help = arg.get("help", "No description")
                arg_short = arg.get("short", "")
                arg_required = arg.get("required", False)
                arg_default = arg.get("default")

                # Format argument display
                arg_display = f"--{arg_name}"
                if arg_short:
                    arg_display += f", -{arg_short}"

                if arg_type != "bool":
                    arg_display += f" <{arg_type}>"

                typer.echo(f"  {arg_display}")
                typer.echo(f"    {arg_help}")

                if arg_required:
                    typer.echo("    (Required)")
                elif arg_default is not None:
                    typer.echo(f"    (Default: {arg_default})")

                typer.echo("")  # Empty line for spacing

        else:
            typer.echo(f"\n📝 This package does not define any CLI arguments.")

        # Show usage examples
        typer.echo(f"\n💡 Usage Examples:")
        typer.echo(f"  vagents pm run {package_name}")

        if arguments:
            # Generate example with some arguments
            example_args = []
            for arg in arguments[:2]:  # Show first 2 arguments as example
                arg_name = arg.get("name")
                arg_type = arg.get("type", "str")
                if arg_type == "bool":
                    example_args.append(f"--{arg_name}")
                else:
                    example_value = (
                        "value"
                        if arg_type == "str"
                        else "123"
                        if arg_type == "int"
                        else "1.5"
                    )
                    example_args.append(f"--{arg_name} {example_value}")

            if example_args:
                typer.echo(f"  vagents pm run {package_name} {' '.join(example_args)}")

    except Exception as e:
        typer.echo(f"❌ Error: {e}", color="red")
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
