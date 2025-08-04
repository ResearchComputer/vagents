#!/usr/bin/env python3
"""
VAgents Package Runner

A standalone script to run VAgents packages with their defined CLI arguments.
This bypasses typer complexity and provides direct argument parsing.
"""

import sys
import json
import argparse
from pathlib import Path
from typing import List

# Import VAgents modules
try:
    from vagents.manager.package import PackageManager
    from vagents.entrypoint.package_manager import (
        format_result_rich,
        format_result_markdown,
    )
    from rich.console import Console
    from rich.markdown import Markdown
    from rich.table import Table
except ImportError as e:
    print(f"Error: Could not import VAgents modules: {e}")
    print("Please ensure VAgents is properly installed.")
    sys.exit(1)


def list_packages():
    """List all available packages"""
    pm = PackageManager()
    packages = pm.list_packages()

    if not packages:
        print("📦 No packages found")
        return

    console = Console()
    table = Table(
        title="Available VAgents Packages",
        show_header=True,
        header_style="bold magenta",
    )
    table.add_column("Package", style="cyan", no_wrap=True)
    table.add_column("Version", style="green")
    table.add_column("Author", style="blue")
    table.add_column("Description", style="white")

    for package_name in sorted(packages):
        package_info = pm.get_package_info(package_name)
        if package_info:
            table.add_row(
                package_name,
                package_info.get("version", "Unknown"),
                package_info.get("author", "Unknown"),
                package_info.get("description", "No description")[:60]
                + ("..." if len(package_info.get("description", "")) > 60 else ""),
            )

    console.print(table)
    print(f"\n💡 Use 'vibe help <package_name>' to see package details")
    print(f"🚀 Use 'vibe run <package_name>' to execute a package")


def install_package(package_path: str):
    """Install a package from a git URL or local path"""
    pm = PackageManager()

    print(f"📦 Installing package from: {package_path}")

    try:
        # Check if it's a local directory
        if Path(package_path).exists() and Path(package_path).is_dir():
            print(f"❌ Error: Local directory installation not directly supported")
            print(f"💡 Tip: The package needs to be in a git repository.")
            print(f"   Initialize git and push to a remote repository first:")
            print(f"   cd {package_path}")
            print(f"   git init")
            print(f"   git add .")
            print(f"   git commit -m 'Initial commit'")
            print(f"   git remote add origin <your-repo-url>")
            print(f"   git push -u origin main")
            print(f"   Then install with: vibe install <your-repo-url>")
            sys.exit(1)
        else:
            print(f"🌐 Installing from git repository: {package_path}")
            result = pm.install_package(package_path)

        if result:
            print(f"✅ Package installed successfully!")
            # Get package info to display details
            packages = pm.list_packages()
            # Try to find the newly installed package by matching the repository URL
            for package_name, package_info in packages.items():
                if package_info.get("repository_url") == package_path:
                    print(f"📦 Package name: {package_info.get('name', package_name)}")
                    print(
                        f"📋 Description: {package_info.get('description', 'No description')}"
                    )
                    print(f"👤 Author: {package_info.get('author', 'Unknown')}")
                    print(f"🏷️  Version: {package_info.get('version', 'Unknown')}")
                    break
        else:
            print("❌ Installation failed")
            sys.exit(1)

    except Exception as e:
        print(f"❌ Error installing package: {e}")
        sys.exit(1)


def remove_package(package_name: str):
    """Remove an installed package"""
    pm = PackageManager()

    # Check if package exists
    if not pm.get_package_info(package_name):
        print(f"❌ Package '{package_name}' not found")
        sys.exit(1)

    print(f"🗑️  Removing package: {package_name}")

    try:
        result = pm.uninstall_package(package_name)
        if result:
            print(f"✅ Package '{package_name}' removed successfully!")
        else:
            print(f"❌ Failed to remove package '{package_name}'")
            sys.exit(1)
    except Exception as e:
        print(f"❌ Error removing package: {e}")
        sys.exit(1)


def show_package_help(package_name: str):
    """Show help for a specific package"""
    pm = PackageManager()
    package_info = pm.get_package_info(package_name)

    if not package_info:
        print(f"❌ Package '{package_name}' not found")
        return

    print(f"\n📦 Package: {package_name}")
    print(f"📋 Description: {package_info.get('description', 'No description')}")
    print(f"👤 Author: {package_info.get('author', 'Unknown')}")
    print(f"🏷️  Version: {package_info.get('version', 'Unknown')}")

    arguments = package_info.get("arguments", [])
    if arguments:
        print(f"\n🔧 Available Arguments:")
        print("-" * 50)

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

            print(f"  {arg_display}")
            print(f"    {arg_help}")

            if arg_required:
                print("    (Required)")
            elif arg_default is not None:
                print(f"    (Default: {arg_default})")

            print("")  # Empty line for spacing

    else:
        print(f"\n📝 This package does not define any CLI arguments.")

    # Show usage examples
    print(f"\n💡 Usage Examples:")
    print(f"  vibe run {package_name}")
    print(f"  cat file.txt | vibe run {package_name}")
    print(f"  echo 'some text' | vibe run {package_name} --verbose")

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
            print(f"  vibe run {package_name} {' '.join(example_args)}")
            print(f"  cat data.json | vibe run {package_name} {' '.join(example_args)}")

    print(f"\n📨 Pipe Support:")
    print(f"  When using pipes, stdin content is automatically passed to the package.")
    print(f"  The content is available as 'input', 'stdin', or custom parameter name.")
    print(
        f"  Use --stdin-as to specify how stdin should be passed (input, content, data, text)."
    )


def parse_package_args(package_name: str, args: List[str]):
    """Parse arguments for a specific package and execute it"""
    import argparse

    pm = PackageManager()
    package_info = pm.get_package_info(package_name)

    if not package_info:
        print(f"❌ Package '{package_name}' not found")
        sys.exit(1)

    # Check if there's input from stdin (pipe)
    stdin_input = None
    if not sys.stdin.isatty():
        try:
            stdin_input = sys.stdin.read().strip()
        except Exception as e:
            print(f"⚠️  Warning: Could not read from stdin: {e}", file=sys.stderr)

    # Create argument parser
    parser = argparse.ArgumentParser(
        prog=f"vibe run {package_name}",
        description=package_info.get("description", f"Execute {package_name} package"),
        formatter_class=argparse.RawDescriptionHelpFormatter,
    )

    # Add format option
    parser.add_argument(
        "--format",
        "-f",
        choices=["rich", "plain", "json", "markdown"],
        default="rich",
        help="Output format (default: rich)",
    )

    # Add stdin option to handle piped input
    if stdin_input:
        parser.add_argument(
            "--stdin-as",
            choices=["input", "content", "data", "text"],
            default="input",
            help="How to pass stdin content to the package (default: input)",
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

    # Parse arguments
    try:
        parsed_args = parser.parse_args(args)
    except SystemExit as e:
        if e.code == 0:  # Help was displayed
            sys.exit(0)
        else:
            sys.exit(1)

    # Extract format and remove it from package args
    format_type = parsed_args.format
    delattr(parsed_args, "format")

    # Handle stdin input
    stdin_param = None
    if stdin_input:
        stdin_param = getattr(parsed_args, "stdin_as", "input")
        if hasattr(parsed_args, "stdin_as"):
            delattr(parsed_args, "stdin_as")

    # Convert to dict and remove None values
    package_kwargs = {k: v for k, v in vars(parsed_args).items() if v is not None}

    # Add stdin content as a parameter if present
    if stdin_input:
        package_kwargs[stdin_param] = stdin_input

        # Also provide it as 'stdin' for backward compatibility
        if stdin_param != "stdin":
            package_kwargs["stdin"] = stdin_input

    # Execute package
    try:
        # Show info about stdin input if present
        if stdin_input:
            stdin_preview = (
                stdin_input[:100] + "..." if len(stdin_input) > 100 else stdin_input
            )
            print(
                f"📥 Received {len(stdin_input)} characters from stdin", file=sys.stderr
            )
            print(f"🔍 Preview: {repr(stdin_preview)}", file=sys.stderr)
            print("", file=sys.stderr)  # Empty line

        result = pm.execute_package(package_name, **package_kwargs)

        # Display results
        console = Console()

        if format_type == "json":
            print(json.dumps(result, indent=2, default=str))
        elif format_type == "markdown":
            markdown_output = format_result_markdown(result, package_name)
            markdown = Markdown(markdown_output)
            console.print(markdown)
        elif format_type == "rich":
            format_result_rich(result, package_name)
        elif format_type == "plain":
            print("✅ Package executed successfully!")
            print(f"\n📋 Execution Result for '{package_name}':")
            print("-" * 50)
            if isinstance(result, dict) or isinstance(result, list):
                print(json.dumps(result, indent=2, default=str))
            else:
                print(str(result))

    except Exception as e:
        import traceback

        traceback.print_exc()
        print(f"❌ Error executing package: {e}")
        sys.exit(1)


def main():
    """Main entry point"""
    if len(sys.argv) < 2:
        print("VAgents Package Runner")
        print("Usage:")
        print("  vibe run <package_name> [args...]")
        print("  vibe help <package_name>")
        print("  vibe list")
        print("  vibe install <package_path_or_url>")
        print("  vibe remove <package_name>")
        print("\nPipe Support:")
        print("  cat file.txt | vibe run <package_name> [args...]")
        print("  echo 'data' | vibe run <package_name> --stdin-as content")
        print("\nExamples:")
        print("  vibe list")
        print("  vibe install ./my-package.json")
        print("  vibe install https://example.com/package.json")
        print("  vibe remove my-package")
        print("  vibe run code-review --history 2 --verbose")
        print("  cat results.txt | vibe run summarize")
        print("  vibe help code-review")
        sys.exit(1)

    command = sys.argv[1]

    if command == "list":
        list_packages()
    elif command == "install" and len(sys.argv) >= 3:
        package_path = sys.argv[2]
        install_package(package_path)
    elif command == "remove" and len(sys.argv) >= 3:
        package_name = sys.argv[2]
        remove_package(package_name)
    elif command == "help" and len(sys.argv) >= 3:
        package_name = sys.argv[2]
        show_package_help(package_name)
    elif command == "run" and len(sys.argv) >= 3:
        package_name = sys.argv[2]
        package_args = sys.argv[3:]
        parse_package_args(package_name, package_args)
    else:
        print("Invalid command. Use 'list', 'install', 'remove', 'run', or 'help'.")
        print("Run 'vibe' without arguments to see usage information.")
        sys.exit(1)


if __name__ == "__main__":
    main()
