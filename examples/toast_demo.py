#!/usr/bin/env python3
"""
Demo script for the VAgents Chat Interface

This script demonstrates how to use the terminal chat interface features.
"""

import sys
import asyncio
from pathlib import Path

# Add the parent directory to sys.path to import vagents modules
sys.path.insert(0, str(Path(__file__).parent.parent))

from vagents.utils.ui import toast, toast_progress
from vagents.utils.chat import ChatInterface


def demo_ui_components():
    """Demonstrate the UI components"""
    print("🎨 VAgents UI Components Demo")
    print("=" * 40)

    # Demo toast messages
    print("\n1. Toast Messages:")
    toast("This is an info message", "info", duration=1.0)
    toast("This is a success message", "success", duration=1.0)
    toast("This is a warning message", "warning", duration=1.0)
    toast("This is an error message", "error", duration=1.0)

    # Demo progress context
    print("\n2. Progress Context:")
    with toast_progress("Processing demo data...") as progress:
        import time

        progress.update("Loading configuration")
        time.sleep(1)
        progress.update("Connecting to services")
        time.sleep(1)
        progress.update("Processing data")
        time.sleep(1)
        progress.update("Finalizing results")
        time.sleep(1)

    print("\n3. Chat Interface:")
    print(
        "Run 'python -m vagents.utils.chat' or 'vagents chat' to start the chat interface"
    )


async def demo_chat_features():
    """Demonstrate chat interface features programmatically"""
    print("\n🤖 Chat Interface Features Demo")
    print("=" * 40)

    # Create chat interface instance
    chat = ChatInterface()

    # Initialize without starting the main loop
    print("\n• Initializing chat interface...")
    chat.console.clear = lambda: None  # Disable clear for demo
    chat._show_welcome()

    print("\n• Loading packages...")
    chat._load_packages()

    print(f"\n• Found {len(chat.available_packages)} packages:")
    for name, pkg in chat.available_packages.items():
        print(f"  - {name}: {pkg.description}")

    print("\n• Testing slash commands...")
    commands_to_test = [
        "/help",
        "/model gpt-4",
        "/packages",
        "/status",
    ]

    for cmd in commands_to_test:
        print(f"\n  Testing: {cmd}")
        result = chat._handle_slash_command(cmd)
        if result:
            print(f"    Result: {result}")

    print("\n✅ Demo completed! Run 'vagents chat' to try the interactive interface.")


def main():
    """Main demo function"""
    print("🚀 VAgents Demo")
    print("Choose a demo:")
    print("1. UI Components Demo")
    print("2. Chat Features Demo")
    print("3. Both")

    try:
        choice = input("\nEnter your choice (1-3): ").strip()

        if choice in ["1", "3"]:
            demo_ui_components()

        if choice in ["2", "3"]:
            asyncio.run(demo_chat_features())

        if choice not in ["1", "2", "3"]:
            print("Invalid choice. Running UI demo...")
            demo_ui_components()

    except KeyboardInterrupt:
        print("\n\nDemo interrupted. Goodbye! 👋")
    except Exception as e:
        print(f"\nError running demo: {e}")


if __name__ == "__main__":
    main()
