import re
import zmq
import psutil
import tempfile
import subprocess
import zmq.asyncio
from typing import Optional


def cleanup_bash_output(output: str) -> str:
    # Clean up the output by removing terminal control sequences, removes escape sequences starting with
    # ESC (0x1b), followed by...
    # ... any characters, an '@' character, any characters, ending with '#' or '$'
    output = re.sub("\x1b.+@.+[#|$] ", "", output)
    # ... '[' and any combination of digits and semicolons, ending with a letter (a-z or A-Z)
    output = re.sub("\x1b\\[[0-9;]*[a-zA-Z]", "", output)
    # ... ']' and any digits, a semicolon, any characters except BEL (0x07), and ending with BEL
    output = re.sub("\x1b\\][0-9]*;[^\x07]*\x07", "", output)
    # ... '[?2004' and either 'h' or 'l'
    output = re.sub("\x1b\\[?2004[hl]", "", output)

    # Remove BEL characters (0x07)
    output = re.sub("\x07", "", output)
    return output


def get_ipc_endpoint(endpoint_name: Optional[str] = None) -> str:
    if endpoint_name is None:
        name = tempfile.NamedTemporaryFile(delete=False).name
        return f"ipc://{name}"
    return f"ipc:///tmp/tmp-{endpoint_name}"


def get_zmq_socket(context: zmq.Context, socket_type: zmq.SocketType, endpoint: str):
    mem = psutil.virtual_memory()
    total_mem = mem.total / 1024**3
    available_mem = mem.available / 1024**3
    if total_mem > 32 and available_mem > 16:
        buf_size = int(0.5 * 1024**3)
    else:
        buf_size = -1

    socket = context.socket(socket_type)
    if socket_type == zmq.PUSH:
        socket.setsockopt(zmq.SNDHWM, 0)
        socket.setsockopt(zmq.SNDBUF, buf_size)
        socket.connect(endpoint)
    elif socket_type == zmq.PULL:
        socket.setsockopt(zmq.RCVHWM, 0)
        socket.setsockopt(zmq.RCVBUF, buf_size)
        socket.bind(endpoint)
    elif socket_type == zmq.PUB:  # Added PUB support
        socket.setsockopt(zmq.SNDHWM, 0)
        socket.setsockopt(zmq.SNDBUF, buf_size)
        socket.bind(endpoint)
    elif socket_type == zmq.SUB:  # Added SUB support
        socket.setsockopt(zmq.RCVHWM, 0)
        socket.setsockopt(zmq.RCVBUF, buf_size)
        socket.setsockopt_string(zmq.SUBSCRIBE, "")
        socket.connect(endpoint)
    else:
        raise ValueError(f"Unsupported socket type: {socket_type}")

    return socket


def is_async_command(command: str) -> bool:
    """
    Returns True if the command contains an unquoted '&' that isn't part of '&&'.
    This is a heuristic to detect background operations.
    """
    # Remove contents of any single or double quoted strings.
    command_no_quotes = re.sub(r'(["\']).*?\1', "", command)
    # Search for an unquoted, standalone '&'
    return re.search(r"(?<!&)&(?!&)", command_no_quotes) is not None


def run_command(command):
    """
    Executes an arbitrary shell command using Bash.

    If the command contains background operations (detected by an unquoted '&'),
    it is launched asynchronously and this function returns the PID of the shell process.

    Otherwise, the command is executed synchronously and its standard output is returned.

    Raises:
        subprocess.CalledProcessError: if the synchronous command fails.
    """
    if is_async_command(command):
        # Launch asynchronously (the shell returns immediately)
        process = subprocess.Popen(command, shell=True, executable="/bin/bash")
        return 0, str(process.pid)
    else:
        # Run synchronously, capturing the output.
        result = subprocess.run(
            command, shell=True, executable="/bin/bash", capture_output=True, text=True
        )
        if result.returncode != 0:
            return result.returncode, result.stderr.strip()
        return result.returncode, cleanup_bash_output(result.stdout.strip())
