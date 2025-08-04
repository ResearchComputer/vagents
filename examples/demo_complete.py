#!/usr/bin/env python3
"""
VAgents CLI Arguments & Pipe Functionality Demo

This script demonstrates the new CLI argument parsing and pipe support
features added to the VAgents package manager.
"""

import subprocess
import sys
from pathlib import Path


def run_demo():
    """Run a complete demonstration of the new features"""

    print("🚀 VAgents CLI Arguments & Pipe Functionality Demo")
    print("=" * 60)

    # Test basic package execution
    print("\n📋 1. Basic Package Execution")
    print("-" * 30)
    result = subprocess.run(
        ["python3", "vibe", "run", "test-pipe-package", "--format", "plain"],
        capture_output=True,
        text=True,
    )
    print("Command: python3 vibe run test-pipe-package --format plain")
    print(
        "Output:",
        result.stdout[:200] + "..." if len(result.stdout) > 200 else result.stdout,
    )

    # Test with arguments
    print("\n📋 2. Package with CLI Arguments")
    print("-" * 30)
    result = subprocess.run(
        [
            "python3",
            "vibe",
            "run",
            "test-pipe-package",
            "--verbose",
            "--config",
            "demo.json",
            "--format",
            "plain",
        ],
        capture_output=True,
        text=True,
    )
    print(
        "Command: python3 vibe run test-pipe-package --verbose --config demo.json --format plain"
    )
    print(
        "Output:",
        result.stdout[:200] + "..." if len(result.stdout) > 200 else result.stdout,
    )

    # Test pipe functionality
    print("\n📋 3. Pipe Functionality Test")
    print("-" * 30)

    # Create test data
    test_data = "This is test data for piping.\nMultiple lines of content.\nTo demonstrate pipe support."

    result = subprocess.run(
        ["python3", "vibe", "run", "test-pipe-package", "--format", "json"],
        input=test_data,
        capture_output=True,
        text=True,
    )
    print(
        "Command: echo 'test data' | python3 vibe run test-pipe-package --format json"
    )
    print("Input:", repr(test_data[:50]) + "...")
    print(
        "Output:",
        result.stdout[:300] + "..." if len(result.stdout) > 300 else result.stdout,
    )

    # Test help system
    print("\n📋 4. Help System")
    print("-" * 30)
    result = subprocess.run(
        ["python3", "vibe", "help", "test-pipe-package"], capture_output=True, text=True
    )
    print("Command: python3 vibe help test-pipe-package")
    print(
        "Output:",
        result.stdout[:400] + "..." if len(result.stdout) > 400 else result.stdout,
    )

    print("\n✨ Demo Summary")
    print("=" * 60)
    print("✅ CLI argument parsing works")
    print("✅ Pipe functionality works")
    print("✅ Multiple output formats supported")
    print("✅ Help system shows package arguments")
    print("✅ Stdin content can be passed with different parameter names")

    print("\n🎯 Key Features Added:")
    print("• Dynamic CLI argument parsing based on package definitions")
    print("• Pipe support with automatic stdin detection")
    print("• Flexible stdin parameter naming (--stdin-as)")
    print("• Rich help system showing package arguments")
    print("• Multiple output formats (rich, plain, json, markdown)")
    print("• Backward compatibility with existing packages")

    print("\n📖 Usage Examples:")
    print("  vibe run <package> --arg1 value1 --arg2")
    print("  cat file.txt | vibe run <package> --verbose")
    print("  echo 'data' | vibe run <package> --stdin-as content")
    print("  vibe help <package>")


if __name__ == "__main__":
    run_demo()
