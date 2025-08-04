#!/usr/bin/env python3
"""
Demo script to test VAgents package CLI argument support

This creates a simple package template and demonstrates how to use the new CLI argument parsing.
"""

import sys
import tempfile
import shutil
from pathlib import Path

# Add the vagents to Python path
sys.path.insert(0, str(Path(__file__).parent))

from vagents.entrypoint.package_manager import create_package_template
from vagents.manager.package import PackageManager


def create_demo_package():
    """Create a demo package with CLI arguments"""

    with tempfile.TemporaryDirectory() as temp_dir:
        temp_path = Path(temp_dir)

        # Create the demo package
        package_name = "demo-cli-package"
        package_path = create_package_template(package_name, temp_dir)

        print(f"✅ Created demo package at: {package_path}")

        # Update the package.yaml to include better CLI arguments
        config_file = package_path / "package.yaml"

        updated_config = """name: demo-cli-package
version: 1.0.0
description: A demo VAgents package with CLI arguments
author: Demo Author
repository_url: https://github.com/demo/demo-cli-package.git
entry_point: demo-cli-package.main
dependencies: []
python_version: ">=3.8"
tags:
  - vagents
  - package
  - demo
arguments:
  - name: "history"
    type: "int"
    help: "Number of history items to process"
    short: "h"
    default: 5
    required: false
  - name: "verbose"
    type: "bool"
    help: "Enable verbose output"
    short: "v"
    required: false
  - name: "config"
    type: "str"
    help: "Configuration file path"
    short: "c"
    required: false
  - name: "output"
    type: "str"
    help: "Output file path"
    short: "o"
    required: false
  - name: "mode"
    type: "str"
    help: "Processing mode"
    choices: ["fast", "normal", "detailed"]
    default: "normal"
    required: false
"""

        with open(config_file, "w") as f:
            f.write(updated_config)

        # Update the main.py file to handle these arguments
        main_file = package_path / f"{package_name}.py"

        updated_main = '''"""
demo-cli-package - A VAgents Package with CLI Arguments

This demonstrates how to create a VAgents package that accepts CLI arguments.
"""

def main(history=5, verbose=False, config=None, output=None, mode="normal", **kwargs):
    """
    Main entry point for the demo-cli-package

    Args:
        history (int): Number of history items to process
        verbose (bool): Enable verbose output
        config (str): Configuration file path
        output (str): Output file path
        mode (str): Processing mode (fast, normal, detailed)
        **kwargs: Additional keyword arguments

    Returns:
        dict: Result of the package execution
    """
    result = {
        "message": "Hello from demo-cli-package!",
        "parameters": {
            "history": history,
            "verbose": verbose,
            "config": config,
            "output": output,
            "mode": mode
        },
        "additional_args": kwargs
    }

    if verbose:
        print(f"🔧 Processing with mode: {mode}")
        print(f"📊 History items to process: {history}")
        if config:
            print(f"⚙️  Using config file: {config}")
        if output:
            print(f"📁 Output will be saved to: {output}")

    # Simulate some processing based on mode
    if mode == "fast":
        result["processing_time"] = "0.5 seconds"
        result["details"] = "Quick processing completed"
    elif mode == "normal":
        result["processing_time"] = "2.3 seconds"
        result["details"] = "Standard processing completed"
    elif mode == "detailed":
        result["processing_time"] = "5.7 seconds"
        result["details"] = "Detailed analysis completed with full report"

    return result


if __name__ == "__main__":
    # Example usage when run directly
    result = main(verbose=True, mode="detailed")
    print(result)
'''

        with open(main_file, "w") as f:
            f.write(updated_main)

        print(f"📝 Updated package files:")
        print(f"   - {config_file}")
        print(f"   - {main_file}")

        # Copy the demo package to a permanent location for testing
        demo_dir = Path.cwd() / "demo-packages"
        demo_dir.mkdir(exist_ok=True)

        permanent_package_path = demo_dir / package_name
        if permanent_package_path.exists():
            shutil.rmtree(permanent_package_path)

        shutil.copytree(package_path, permanent_package_path)

        print(f"📦 Demo package copied to: {permanent_package_path}")

        return permanent_package_path


def test_package_manager():
    """Test the package manager with the demo package"""

    # Create demo package
    package_path = create_demo_package()

    print("\n" + "=" * 60)
    print("🧪 TESTING PACKAGE MANAGER")
    print("=" * 60)

    try:
        # Initialize package manager
        pm = PackageManager()

        # Install the demo package from local path
        # For demo purposes, we'll simulate this by directly registering
        from vagents.manager.package import PackageConfig, PackageArgument

        # Load package config
        import yaml

        with open(package_path / "package.yaml", "r") as f:
            config_data = yaml.safe_load(f)

        # Create PackageConfig with arguments
        arguments = [
            PackageArgument(**arg_def) for arg_def in config_data.get("arguments", [])
        ]

        config = PackageConfig(
            name=config_data["name"],
            version=config_data["version"],
            description=config_data["description"],
            author=config_data["author"],
            repository_url=config_data["repository_url"],
            entry_point=config_data["entry_point"],
            dependencies=config_data.get("dependencies", []),
            python_version=config_data.get("python_version", ">=3.8"),
            tags=config_data.get("tags", []),
            arguments=arguments,
        )

        # Register the package
        pm.register_package(config, package_path)

        print(f"✅ Registered package: {config.name}")

        # Test different execution scenarios
        test_cases = [
            {"name": "Basic execution (no args)", "kwargs": {}},
            {"name": "With verbose flag", "kwargs": {"verbose": True}},
            {
                "name": "With history and mode",
                "kwargs": {"history": 10, "mode": "fast", "verbose": True},
            },
            {
                "name": "Full argument set",
                "kwargs": {
                    "history": 15,
                    "verbose": True,
                    "config": "my-config.json",
                    "output": "results.txt",
                    "mode": "detailed",
                },
            },
        ]

        for i, test_case in enumerate(test_cases, 1):
            print(f"\n📋 Test {i}: {test_case['name']}")
            print("-" * 40)

            try:
                result = pm.execute_package(config.name, **test_case["kwargs"])
                print(f"✅ Success!")
                print(f"📊 Result: {result}")

            except Exception as e:
                print(f"❌ Error: {e}")

        # Test package info
        print(f"\n📦 Package Information:")
        print("-" * 40)
        package_info = pm.get_package_info(config.name)
        if package_info:
            print(f"Name: {package_info['name']}")
            print(f"Version: {package_info['version']}")
            print(f"Arguments: {len(package_info.get('arguments', []))} defined")
            for arg in package_info.get("arguments", []):
                print(f"  - --{arg['name']} ({arg['type']}): {arg['help']}")

    except Exception as e:
        import traceback

        traceback.print_exc()
        print(f"❌ Test failed: {e}")

    finally:
        # Cleanup
        if package_path.exists():
            shutil.rmtree(package_path.parent)
            print(f"\n🧹 Cleaned up demo package directory")


if __name__ == "__main__":
    print("🚀 VAgents CLI Arguments Demo")
    print("=" * 50)

    test_package_manager()

    print("\n✨ Demo completed!")
    print("\n📖 To test manually:")
    print("   1. Create a package template: vagents pm create-template my-test")
    print("   2. Install a package: vagents pm install <repo-url>")
    print(
        "   3. Run with arguments: vagents pm run <package-name> --verbose --config file.json"
    )
    print("   4. Get help: vagents pm help-package <package-name>")
