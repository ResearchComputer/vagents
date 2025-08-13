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
    from vagents.core import AgentOutput
    from rich.console import Console
    from rich.markdown import Markdown
    from rich.table import Table
except ImportError as e:
    print(f"Error: Could not import VAgents modules: {e}")
    print("Please ensure VAgents is properly installed.")
    sys.exit(1)


HELP_FLAGS = {"-h", "--help"}

# Default packages repository for bare name resolution
DEFAULT_PACKAGES_REPO = "https://github.com/vagents-ai/packages"


def _looks_like_url(value: str) -> bool:
    return (
        value.startswith("http://")
        or value.startswith("https://")
        or value.startswith("git@")
    )


def _looks_like_path(value: str) -> bool:
    # Treat as path only if clearly specified as such
    # Absolute or relative indicators or contains a path separator
    return (
        value in (".", "..")
        or value.startswith("/")
        or value.startswith("./")
        or value.startswith("../")
        or ("/" in value)
    )


def _print_global_help() -> None:
    print("VAgents Package Runner")
    print("Usage:")
    print("  vibe run <package_name> [args...]")
    print("  vibe help <package_name>")
    print("  vibe list")
    print("  vibe install [--force|-f] [--branch|-b <branch>] <package_path_or_url>")
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


def _print_subcommand_help(command: str) -> None:
    cmd = command.strip().lower()
    if cmd == "install":
        print(
            "Usage: vibe install [--force|-f] [--branch|-b <branch>] <package_path_or_url>"
        )
        print(
            "\nInstall a package from a local directory, a git repository URL, or by bare name."
        )
        print("- Local directory: vibe install ./path/to/package_dir")
        print(
            "- Git repository:  vibe install https://github.com/user/repo.git[/subdir]"
        )
        print(
            f"- Bare name (resolved to default repo): vibe install code-review  => {DEFAULT_PACKAGES_REPO}/code-review"
        )
        print("\nOptions:")
        print("  -f, --force        Force reinstall if package exists")
        print(
            "  -b, --branch BR    Git branch to use when installing from a repo (default: main)"
        )
        return
    if cmd == "remove":
        print("Usage: vibe remove <package_name>")
        print("\nRemove an installed package by name.")
        return
    if cmd == "list":
        print("Usage: vibe list")
        print("\nList all installed packages.")
        return
    if cmd == "help":
        print("Usage: vibe help <package_name>")
        print("\nShow details and available arguments for a package.")
        return
    if cmd == "run":
        print(
            "Usage: vibe run [--format|-f <rich|plain|json|markdown>] <package_name> [package_args...]"
        )
        print("\nExecute a package. Use 'vibe help <package_name>' for its arguments.")
        print("Tip: 'vibe run <package_name> -h' also shows package-specific help.")
        return
    _print_global_help()


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


def install_package(package_path: str, branch: str = "main", force: bool = False):
    """Install a package from a git URL or local path"""
    pm = PackageManager()

    print(f"📦 Installing package from: {package_path}")

    try:
        # Treat as local only if the argument clearly looks like a filesystem path
        if (
            _looks_like_path(package_path)
            and Path(package_path).expanduser().exists()
            and Path(package_path).is_dir()
        ):
            print(f"📁 Detected local directory. Validating and installing locally...")
            result = pm.install_local_package(package_path, force)
        else:
            # Resolve bare names to default packages repository subdirectory
            resolved_spec = package_path
            if not _looks_like_url(package_path):
                resolved_spec = (
                    f"{DEFAULT_PACKAGES_REPO.rstrip('/')}/{package_path.lstrip('/')}"
                )
                print(f"🔎 Resolved package name to: {resolved_spec}")
            print(
                f"🌐 Installing from git repository: {resolved_spec} (branch: {branch})"
            )
            result = pm.install_package(resolved_spec, branch, force)

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
                # If installed locally, repository_url may be file://...
                for package_name, package_info in packages.items():
                    repo = package_info.get("repository_url", "")
                    if (
                        repo.startswith("file://")
                        and Path(repo.replace("file://", "")).resolve()
                        == Path(package_path).resolve()
                    ):
                        print(
                            f"📦 Package name: {package_info.get('name', package_name)}"
                        )
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


def parse_package_args(package_name: str, args: List[str], format_type: str = "rich"):
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

    # Output format is primarily handled by the parent 'vibe run' command. However,
    # when this helper is invoked directly (e.g., in tests), support the long
    # '--format' flag here as a convenience. Do NOT consume short '-f' to avoid
    # conflicts with package short flags (e.g., '-f' as '--file').
    effective_format = format_type
    remaining_args: List[str] = list(args)

    # Extract and remove any '--format' occurrences from remaining_args
    # Supported values: rich | plain | json | markdown
    try:
        cleaned_args: List[str] = []
        i = 0
        while i < len(remaining_args):
            token = remaining_args[i]
            if token == "--format":
                # Value should be the next token if present and not another flag
                value = None
                if i + 1 < len(remaining_args) and not remaining_args[i + 1].startswith(
                    "-"
                ):
                    value = remaining_args[i + 1]
                    i += 2
                else:
                    i += 1
                if value in ("rich", "plain", "json", "markdown"):
                    effective_format = value
                continue  # skip adding '--format' and its value
            if token.startswith("--format="):
                value = token.split("=", 1)[1]
                if value in ("rich", "plain", "json", "markdown"):
                    effective_format = value
                i += 1
                continue  # skip adding this token
            # Keep all other tokens (including any '-f' for the package itself)
            cleaned_args.append(token)
            i += 1
        remaining_args = cleaned_args
    except Exception:
        # Best-effort: if anything goes wrong, fall back to original args
        remaining_args = list(args)

    # Create argument parser
    parser = argparse.ArgumentParser(
        prog=f"vibe run {package_name}",
        description=package_info.get("description", f"Execute {package_name} package"),
        formatter_class=argparse.RawDescriptionHelpFormatter,
    )

    # Note: output format is handled by the parent 'vibe run' command

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
        parsed_args = parser.parse_args(remaining_args)
    except SystemExit as e:
        if e.code == 0:  # Help was displayed
            sys.exit(0)
        else:
            sys.exit(1)

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

        if effective_format == "json":
            print(json.dumps(result, indent=2, default=str))
        elif effective_format == "markdown":
            markdown_output = format_result_markdown(
                result.result["content"], package_name
            )
            markdown = Markdown(markdown_output)
            console.print(markdown)
        elif effective_format == "rich":
            format_result_rich(result.result["content"], package_name)
        elif effective_format == "plain":
            if isinstance(result, dict) or isinstance(result, list):
                print(json.dumps(result, indent=2, default=str))
            elif isinstance(result, AgentOutput):
                print(result.result.get("content", ""))
            else:
                print(str(result))

    except Exception as e:
        import traceback

        traceback.print_exc()
        print(f"❌ Error executing package: {e}")
        sys.exit(1)


def main():
    """Main entry point"""
    # Global help
    if len(sys.argv) < 2 or sys.argv[1] in HELP_FLAGS:
        _print_global_help()
        sys.exit(0)

    command = sys.argv[1]

    if command == "list":
        # Support: vibe list -h/--help
        if any(arg in HELP_FLAGS for arg in sys.argv[2:]):
            _print_subcommand_help("list")
            sys.exit(0)
        list_packages()
        return

    if command == "install":
        # Parse options: --force/-f and --branch/-b before the path
        args = sys.argv[2:]
        if not args or any(arg in HELP_FLAGS for arg in args):
            _print_subcommand_help("install")
            sys.exit(0 if (args and any(arg in HELP_FLAGS for arg in args)) else 1)

        force = False
        branch = "main"
        positional_paths: List[str] = []

        i = 0
        while i < len(args):
            a = args[i]
            if a in ("--force", "-f"):
                force = True
                i += 1
                continue
            if a in ("--branch", "-b"):
                if i + 1 >= len(args):
                    print("❌ Missing value for --branch")
                    _print_subcommand_help("install")
                    sys.exit(1)
                branch = args[i + 1]
                i += 2
                continue
            if a.startswith("-"):
                print(f"❌ Unknown option: {a}")
                _print_subcommand_help("install")
                sys.exit(1)
            # Non-flag positional argument => a path/url
            positional_paths.append(a)
            i += 1

        if len(positional_paths) == 0:
            print("❌ Missing <package_path_or_url>")
            _print_subcommand_help("install")
            sys.exit(1)
        if len(positional_paths) > 1:
            print("❌ Multiple <package_path_or_url> values provided")
            _print_subcommand_help("install")
            sys.exit(1)

        package_path = positional_paths[0]

        install_package(package_path, branch=branch, force=force)
        return

    if command == "remove":
        if len(sys.argv) < 3 or any(arg in HELP_FLAGS for arg in sys.argv[2:]):
            _print_subcommand_help("remove")
            sys.exit(
                0
                if (
                    len(sys.argv) >= 3
                    and any(arg in HELP_FLAGS for arg in sys.argv[2:])
                )
                else 1
            )
        package_name = sys.argv[2]
        remove_package(package_name)
        return

    if command == "help":
        if len(sys.argv) < 3 or any(arg in HELP_FLAGS for arg in sys.argv[2:]):
            _print_subcommand_help("help")
            sys.exit(
                0
                if (
                    len(sys.argv) >= 3
                    and any(arg in HELP_FLAGS for arg in sys.argv[2:])
                )
                else 1
            )
        package_name = sys.argv[2]
        show_package_help(package_name)
        return

    if command == "run":
        # Support: vibe run -h
        run_args = sys.argv[2:]
        if not run_args or any(arg in HELP_FLAGS for arg in run_args):
            _print_subcommand_help("run")
            sys.exit(0 if run_args else 1)

        # Accept global --format only BEFORE the package name for clarity:
        #   vibe run --format json <package> [args...]
        # Any '-f' appearing after the package name belongs to the package (e.g., '--file/-f').
        format_override = "rich"
        if run_args and run_args[0] in ("--format", "-f"):
            if len(run_args) < 2:
                print("❌ Missing value for --format")
                _print_subcommand_help("run")
                sys.exit(1)
            format_override = run_args[1]
            remaining: List[str] = run_args[2:]
        else:
            remaining = run_args

        if not remaining:
            print("❌ Missing <package_name>")
            _print_subcommand_help("run")
            sys.exit(1)

        package_name = remaining[0]
        package_args = remaining[1:]

        # Disallow legacy placement of --format (long form) after the package name for clarity
        # Allow short '-f' to be used by packages (commonly as '--file').
        if any(arg == "--format" for arg in package_args):
            print(
                "❌ Place --format/-f before the package name: 'vibe run --format json <package>'"
            )
            _print_subcommand_help("run")
            sys.exit(1)

        parse_package_args(package_name, package_args, format_type=format_override)
        return

    print("Invalid command. Use 'list', 'install', 'remove', 'run', or 'help'.")
    print("Run 'vibe' without arguments to see usage information.")
    sys.exit(1)


if __name__ == "__main__":
    main()
