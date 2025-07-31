import time
from typing import Optional, Union, Literal
from contextlib import contextmanager
from rich.console import Console
from rich.panel import Panel
from rich.progress import (
    Progress,
    SpinnerColumn,
    TextColumn,
    BarColumn,
    TimeElapsedColumn,
)
from rich.text import Text
from rich.live import Live

# Global console instance
_console = Console()


def toast(
    message: str,
    status: Literal["info", "success", "warning", "error"] = "info",
    duration: Optional[float] = None,
    spinner: bool = False,
) -> None:
    """
    Displays a toast message to the user with rich formatting.

    Args:
        message: The message to display
        status: The type of message (info, success, warning, error)
        duration: How long to display the message (None for instant display)
        spinner: Whether to show a spinner animation
    """
    # Color mapping for different status types
    status_colors = {
        "info": "blue",
        "success": "green",
        "warning": "yellow",
        "error": "red",
    }

    # Icon mapping for different status types
    status_icons = {"info": "ℹ️", "success": "✅", "warning": "⚠️", "error": "❌"}

    color = status_colors.get(status, "blue")
    icon = status_icons.get(status, "ℹ️")

    # Create styled text
    styled_text = Text()
    styled_text.append(f"{icon} ", style=color)
    styled_text.append(message, style=color)

    if spinner and duration:
        # Show spinner with message for specified duration
        with _console.status(styled_text, spinner="dots"):
            time.sleep(duration)
    elif duration:
        # Show message for specified duration
        panel = Panel(styled_text, border_style=color, padding=(0, 1))
        _console.print(panel)
        time.sleep(duration)
    else:
        # Show message instantly
        panel = Panel(styled_text, border_style=color, padding=(0, 1))
        _console.print(panel)


@contextmanager
def toast_progress(description: str = "Processing..."):
    """
    Context manager for displaying progress with a toast-style interface.

    Args:
        description: Description of the ongoing process

    Usage:
        with toast_progress("Loading data...") as progress:
            # Your code here
            progress.update("Step 1 complete")
            # More code...
            progress.update("Step 2 complete")
    """

    class ProgressUpdater:
        def __init__(self, live_display):
            self.live = live_display
            self.steps = []

        def update(self, step_message: str):
            """Update the progress with a new step message."""
            self.steps.append(f"✅ {step_message}")
            # Update the display with current steps
            text = Text()
            text.append("🔄 ", style="blue")
            text.append(description, style="blue bold")
            text.append("\n")
            for step in self.steps[-5:]:  # Show last 5 steps
                text.append(f"  {step}\n", style="green")

            panel = Panel(text, border_style="blue", padding=(0, 1))
            self.live.update(panel)

    # Initial display
    initial_text = Text()
    initial_text.append("🔄 ", style="blue")
    initial_text.append(description, style="blue bold")
    initial_panel = Panel(initial_text, border_style="blue", padding=(0, 1))

    with Live(initial_panel, console=_console, refresh_per_second=4) as live:
        updater = ProgressUpdater(live)
        try:
            yield updater
        finally:
            # Final success message
            final_text = Text()
            final_text.append("✅ ", style="green")
            final_text.append("Complete!", style="green bold")
            final_panel = Panel(final_text, border_style="green", padding=(0, 1))
            live.update(final_panel)
            time.sleep(0.5)  # Brief pause to show completion


def toast_with_progress_bar(message: str, total: int, update_callback=None) -> Progress:
    """
    Creates a toast-style progress bar for long-running operations.

    Args:
        message: Description of the operation
        total: Total number of steps
        update_callback: Optional callback function called on each update

    Returns:
        Progress object that can be used to update the progress

    Usage:
        progress = toast_with_progress_bar("Processing files...", total=100)
        task_id = progress.add_task("Processing", total=100)

        for i in range(100):
            # Do some work
            progress.update(task_id, advance=1)

        progress.stop()
    """
    progress = Progress(
        SpinnerColumn(),
        TextColumn("[bold blue]{task.description}"),
        BarColumn(),
        TextColumn("[progress.percentage]{task.percentage:>3.0f}%"),
        TimeElapsedColumn(),
        console=_console,
    )

    return progress
