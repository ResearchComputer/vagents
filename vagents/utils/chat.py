#!/usr/bin/env python3
"""
Terminal Chat Interface for VAgents

A simple, interactive chat interface that allows users to:
1. Chat with any LLM using the LM class
2. Use slash commands to select and trigger packages
3. Rich terminal UI with syntax highlighting and progress indicators
"""

import asyncio
import sys
import os
from typing import Dict, List, Optional, Any
from pathlib import Path

# Add the parent directory to sys.path to import vagents modules
sys.path.insert(0, str(Path(__file__).parent.parent))

import typer
from rich.console import Console
from rich.prompt import Prompt
from rich.panel import Panel
from rich.text import Text
from rich.markdown import Markdown
from rich.table import Table
from rich.columns import Columns
from rich.live import Live
from rich.layout import Layout

from vagents.core import LM
from vagents.manager.package import PackageManager
from vagents.utils.ui import toast, toast_progress


class ChatInterface:
    """Main chat interface class"""

    def __init__(self):
        self.console = Console()
        self.lm = None
        self.package_manager = PackageManager()
        self.current_model = "@auto"
        self.conversation_history = []
        self.available_packages = {}
        self.running = True

    def initialize(self):
        """Initialize the chat interface"""
        self.console.clear()
        self._show_welcome()
        self._load_packages()
        self._initialize_llm()

    def _show_welcome(self):
        """Display welcome message and help"""
        welcome_text = Text()
        welcome_text.append("🤖 ", style="blue")
        welcome_text.append("VAgents Chat Interface", style="bold blue")
        welcome_text.append("\n\nWelcome to the interactive chat interface!")

        help_table = Table(show_header=False, box=None, padding=(0, 2))
        help_table.add_column(style="cyan")
        help_table.add_column(style="white")

        help_table.add_row("💬", "Type your message and press Enter to chat")
        help_table.add_row("/help", "Show this help message")
        help_table.add_row(
            "/model <name>", "Switch to a different model (e.g., /model gpt-4)"
        )
        help_table.add_row("/packages", "List available packages")
        help_table.add_row("/pkg <name>", "Execute a package with your message")
        help_table.add_row("/history", "Show conversation history")
        help_table.add_row("/clear", "Clear conversation history")
        help_table.add_row("/quit", "Exit the chat interface")

        welcome_panel = Panel(
            welcome_text, title="Welcome", border_style="blue", padding=(1, 2)
        )

        help_panel = Panel(
            help_table, title="Available Commands", border_style="green", padding=(1, 2)
        )

        self.console.print(welcome_panel)
        self.console.print(help_panel)
        self.console.print()

    def _load_packages(self):
        """Load available packages"""
        try:
            packages = self.package_manager.list_packages()
            # packages is already a Dict[str, Dict] where keys are package names
            self.available_packages = packages
            if packages:
                toast(f"Loaded {len(packages)} packages", "success", duration=1.0)
            else:
                toast(
                    "No packages found. Use 'vagents pm install <repo-url>' to install packages.",
                    "info",
                    duration=2.0,
                )
        except Exception as e:
            toast(f"Error loading packages: {e}", "error", duration=2.0)

    def _initialize_llm(self):
        """Initialize the LM instance"""
        try:
            self.lm = LM(name=self.current_model)
            toast(f"Initialized model: {self.current_model}", "success", duration=1.0)
        except Exception as e:
            toast(f"Error initializing LM: {e}", "error", duration=2.0)

    def _show_status(self):
        """Show current status"""
        status_table = Table(show_header=False, box=None)
        status_table.add_column(style="cyan")
        status_table.add_column(style="white")

        status_table.add_row("Model:", self.current_model)
        status_table.add_row("Packages:", f"{len(self.available_packages)} available")
        status_table.add_row("History:", f"{len(self.conversation_history)} messages")

        status_panel = Panel(
            status_table, title="Status", border_style="yellow", padding=(0, 1)
        )

        self.console.print(status_panel)

    async def _chat_with_llm(self, message: str) -> str:
        """Send message to LLM and get response"""
        try:
            # Add user message to history
            self.conversation_history.append({"role": "user", "content": message})

            # Prepare messages for LLM (include conversation history)
            messages = self.conversation_history.copy()

            with toast_progress(f"Chatting with {self.current_model}...") as progress:
                progress.update("Sending message to LLM")

                # Call LLM
                response = await self.lm(messages=messages)

                progress.update("Processing response")

                # Extract content from response
                if isinstance(response, dict) and "choices" in response:
                    content = response["choices"][0]["message"]["content"]
                else:
                    content = str(response)

                # Add assistant response to history
                self.conversation_history.append(
                    {"role": "assistant", "content": content}
                )

                progress.update("Response received")

            return content

        except Exception as e:
            toast(f"Error chatting with LLM: {e}", "error", duration=3.0)
            return f"Error: {e}"

    async def _execute_package(self, package_name: str, message: str) -> str:
        """Execute a package with the given message"""
        try:
            if package_name not in self.available_packages:
                return f"Package '{package_name}' not found. Use /packages to see available packages."

            with toast_progress(f"Executing package: {package_name}") as progress:
                progress.update("Loading package")

                # Execute package
                result = self.package_manager.execute_package(
                    package_name, message=message
                )

                progress.update("Package executed successfully")

            return f"Package '{package_name}' result:\n{result}"

        except Exception as e:
            toast(f"Error executing package: {e}", "error", duration=3.0)
            return f"Error executing package '{package_name}': {e}"

    def _handle_slash_command(self, command: str) -> Optional[str]:
        """Handle slash commands"""
        parts = command[1:].split(maxsplit=1)
        cmd = parts[0].lower()
        args = parts[1] if len(parts) > 1 else ""

        if cmd == "help":
            self._show_welcome()
            return None

        elif cmd == "model":
            if args:
                old_model = self.current_model
                self.current_model = args
                self._initialize_llm()
                return f"Switched from '{old_model}' to '{self.current_model}'"
            else:
                return (
                    f"Current model: {self.current_model}\nUsage: /model <model_name>"
                )

        elif cmd == "packages":
            if not self.available_packages:
                return "No packages available. Install packages using 'vagents pm install <repo-url>'"

            table = Table(title="Available Packages")
            table.add_column("Name", style="cyan")
            table.add_column("Version", style="green")
            table.add_column("Description", style="white")

            for pkg_name, pkg_info in self.available_packages.items():
                table.add_row(
                    pkg_name,
                    pkg_info.get("version", "N/A"),
                    pkg_info.get("description", "No description"),
                )

            self.console.print(table)
            return None

        elif cmd == "pkg":
            if not args:
                return "Usage: /pkg <package_name> <message>"

            pkg_parts = args.split(maxsplit=1)
            if len(pkg_parts) < 2:
                return "Usage: /pkg <package_name> <message>"

            package_name, message = pkg_parts
            # This will be handled asynchronously
            return f"EXEC_PACKAGE:{package_name}:{message}"

        elif cmd == "history":
            if not self.conversation_history:
                return "No conversation history yet."

            history_text = Text()
            for i, msg in enumerate(
                self.conversation_history[-10:], 1
            ):  # Show last 10 messages
                role_style = "blue" if msg["role"] == "user" else "green"
                history_text.append(f"{i}. [{msg['role'].title()}]: ", style=role_style)
                history_text.append(
                    f"{msg['content'][:100]}...\n"
                    if len(msg["content"]) > 100
                    else f"{msg['content']}\n"
                )

            history_panel = Panel(
                history_text,
                title="Conversation History (Last 10 messages)",
                border_style="cyan",
            )
            self.console.print(history_panel)
            return None

        elif cmd == "clear":
            self.conversation_history.clear()
            return "Conversation history cleared."

        elif cmd == "quit" or cmd == "exit":
            self.running = False
            return "Goodbye! 👋"

        elif cmd == "status":
            self._show_status()
            return None

        else:
            return f"Unknown command: /{cmd}. Type /help for available commands."

    async def _process_message(self, user_input: str):
        """Process user input and generate response"""
        if user_input.startswith("/"):
            # Handle slash command
            result = self._handle_slash_command(user_input)

            if result:
                if result.startswith("EXEC_PACKAGE:"):
                    # Extract package execution details
                    _, package_name, message = result.split(":", 2)
                    response = await self._execute_package(package_name, message)
                else:
                    response = result

                if response:
                    response_panel = Panel(
                        Markdown(response),
                        title="System",
                        border_style="yellow",
                        padding=(1, 2),
                    )
                    self.console.print(response_panel)
        else:
            # Regular chat message
            if not self.lm:
                toast(
                    "LLM not initialized. Please check your configuration.",
                    "error",
                    duration=3.0,
                )
                return

            response = await self._chat_with_llm(user_input)

            # Display response
            response_panel = Panel(
                Markdown(response),
                title=f"🤖 {self.current_model}",
                border_style="blue",
                padding=(1, 2),
            )
            self.console.print(response_panel)

    async def run(self):
        """Main chat loop"""
        self.initialize()

        while self.running:
            try:
                # Get user input
                user_input = Prompt.ask(
                    "\n[bold cyan]You[/bold cyan]", console=self.console
                ).strip()

                if not user_input:
                    continue

                # Display user message
                user_panel = Panel(
                    user_input, title="👤 You", border_style="green", padding=(1, 2)
                )
                self.console.print(user_panel)

                # Process the message
                await self._process_message(user_input)

            except KeyboardInterrupt:
                self.console.print(
                    "\n\n[yellow]Interrupted by user. Type /quit to exit properly.[/yellow]"
                )
                continue
            except EOFError:
                self.console.print("\n\n[blue]Goodbye! 👋[/blue]")
                break
            except Exception as e:
                toast(f"Unexpected error: {e}", "error", duration=3.0)


def main():
    """Main entry point for the chat interface"""
    try:
        chat = ChatInterface()
        asyncio.run(chat.run())
    except KeyboardInterrupt:
        print("\n\nGoodbye! 👋")
    except Exception as e:
        print(f"Error: {e}")
        sys.exit(1)


if __name__ == "__main__":
    main()
