#!/usr/bin/env python3
"""
Test runner script for the vagents project.

This script provides an easy way to run all tests with various options.
"""

import sys
import subprocess
import argparse
import os
from pathlib import Path


def run_command(cmd, description):
    """Run a command and handle its output."""
    print(f"\n{'='*60}")
    print(f"🧪 {description}")
    print(f"{'='*60}")
    print(f"Running: {' '.join(cmd)}")
    print()

    result = subprocess.run(cmd, capture_output=False)

    if result.returncode == 0:
        print(f"✅ {description} - PASSED")
    else:
        print(f"❌ {description} - FAILED")
        return False

    return True


def main():
    parser = argparse.ArgumentParser(description="Run vagents test suite")
    parser.add_argument(
        "--coverage", action="store_true", help="Run tests with coverage report"
    )
    parser.add_argument(
        "--verbose", "-v", action="store_true", help="Run tests in verbose mode"
    )
    parser.add_argument("--fast", action="store_true", help="Skip slow tests")
    parser.add_argument(
        "--specific",
        type=str,
        help="Run specific test file or test function (e.g., test_optimizers.py or test_optimizers.py::TestOptimizeAwaitSequences::test_single_await_no_optimization)",
    )
    parser.add_argument(
        "--install-deps",
        action="store_true",
        help="Install test dependencies before running tests",
    )

    args = parser.parse_args()

    # Change to project root directory
    project_root = Path(__file__).parent
    os.chdir(project_root)

    success = True

    # Install dependencies if requested
    if args.install_deps:
        success &= run_command(
            [sys.executable, "-m", "pip", "install", "-e", ".[dev]"],
            "Installing test dependencies",
        )
        if not success:
            return 1

    # Build pytest command
    pytest_cmd = [sys.executable, "-m", "pytest"]

    if args.verbose:
        pytest_cmd.append("-v")

    if args.fast:
        pytest_cmd.extend(["-m", "not slow"])

    if args.coverage:
        pytest_cmd.extend(
            [
                "--cov=vagents",
                "--cov-report=html",
                "--cov-report=term-missing",
                "--cov-report=xml",
            ]
        )

    # Add specific test if provided
    if args.specific:
        if args.specific.endswith(".py"):
            pytest_cmd.append(f"tests/{args.specific}")
        else:
            pytest_cmd.append(f"tests/{args.specific}")
    else:
        pytest_cmd.append("tests/")

    # Run the tests
    success &= run_command(pytest_cmd, "Running pytest")

    if args.coverage and success:
        print(f"\n📊 Coverage report generated in htmlcov/index.html")

    if success:
        print(f"\n🎉 All tests passed!")
        return 0
    else:
        print(f"\n💥 Some tests failed!")
        return 1


if __name__ == "__main__":
    sys.exit(main())
