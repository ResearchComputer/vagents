"""
Dynamic CLI generator for VAgents packages

This module provides functionality to create dynamic CLI commands based on package argument definitions.
"""

import sys
import argparse
from typing import List, Dict, Any, Optional
from pathlib import Path

try:
    from vagents.manager.package import PackageManager, PackageArgumentParser
except ImportError:
    print(
        "Error: VAgents package manager not found. Please ensure VAgents is properly installed."
    )
    sys.exit(1)


class PackageCLI:
    """Dynamic CLI for package execution"""

    def __init__(self):
        self.pm = PackageManager()

    def create_package_parser(self, package_name: str) -> argparse.ArgumentParser:
        """Create an ArgumentParser for a specific package"""
        package_info = self.pm.get_package_info(package_name)
        if not package_info:
            raise ValueError(f"Package '{package_name}' not found")

        parser = argparse.ArgumentParser(
            prog=f"vagents run {package_name}",
            description=package_info.get(
                "description", f"Execute {package_name} package"
            ),
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

        # Add package-specific arguments
        arguments = package_info.get("arguments", [])
        for arg_def in arguments:
            self._add_argument_to_parser(parser, arg_def)

        return parser

    def _add_argument_to_parser(
        self, parser: argparse.ArgumentParser, arg_def: Dict[str, Any]
    ):
        """Add a single argument definition to the parser"""
        name = arg_def.get("name")
        if not name:
            return

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

    def execute_with_args(self, package_name: str, args: List[str]) -> Any:
        """Execute a package with parsed CLI arguments"""
        try:
            parser = self.create_package_parser(package_name)
            parsed_args = parser.parse_args(args)

            # Extract format and remove it from package args
            format_type = parsed_args.format
            delattr(parsed_args, "format")

            # Convert to dict and remove None values
            package_kwargs = {
                k: v for k, v in vars(parsed_args).items() if v is not None
            }

            # Execute package
            result = self.pm.execute_package(package_name, **package_kwargs)

            return result, format_type

        except SystemExit as e:
            if e.code == 0:
                # Help was displayed
                sys.exit(0)
            else:
                # Error in argument parsing
                raise ValueError(f"Invalid arguments for package {package_name}")


def run_package_with_dynamic_cli(package_name: str, args: List[str] = None):
    """Run a package with dynamic CLI parsing

    Args:
        package_name: Name of the package to run
        args: Command line arguments (if None, uses sys.argv)
    """
    if args is None:
        # Skip script name and extract just the package arguments
        args = sys.argv[1:]

    cli = PackageCLI()

    try:
        result, format_type = cli.execute_with_args(package_name, args)

        # Import formatting functions
        import json
        from rich.console import Console
        from rich.markdown import Markdown

        console = Console()

        # Display results based on format
        if format_type == "json":
            print(json.dumps(result, indent=2, default=str))
        elif format_type == "markdown":
            from vagents.entrypoint.package_manager import format_result_markdown

            markdown_output = format_result_markdown(
                result.result["content"], package_name
            )
            markdown = Markdown(markdown_output)
            console.print(markdown)
        elif format_type == "rich":
            from vagents.entrypoint.package_manager import format_result_rich

            format_result_rich(result.result["content"], package_name)
        elif format_type == "plain":
            print("✅ Package executed successfully!")
            print(f"\n📋 Execution Result for '{package_name}':")
            print("-" * 50)
            if isinstance(result, dict) or isinstance(result, list):
                print(json.dumps(result, indent=2, default=str))
            else:
                print(str(result))

    except ValueError as e:
        print(f"❌ Error: {e}", file=sys.stderr)
        sys.exit(1)
    except Exception as e:
        import traceback

        traceback.print_exc()
        print(f"❌ Error executing package: {e}", file=sys.stderr)
        sys.exit(1)


if __name__ == "__main__":
    if len(sys.argv) < 2:
        print("Usage: python package_cli.py <package_name> [args...]")
        sys.exit(1)

    package_name = sys.argv[1]
    package_args = sys.argv[2:]

    run_package_with_dynamic_cli(package_name, package_args)
