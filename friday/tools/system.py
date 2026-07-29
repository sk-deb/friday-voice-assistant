"""System tools exposed to the model.

Every public function here is handed to Gemini as a callable tool, so:

* type hints must be simple (str, int, bool),
* the docstring is the tool description the model actually reads,
* the return value must be a short string the model can speak.
"""

from __future__ import annotations

import datetime as _dt
import logging
import os
import platform
import shutil
import subprocess
import webbrowser
from typing import Callable

from ..config import Settings

log = logging.getLogger("friday.tools.system")

MAX_TOOL_OUTPUT = 4_000


def get_current_time() -> str:
    """Return the current local date and time."""
    return _dt.datetime.now().strftime("%A %d %B %Y, %I:%M %p")


def open_application(name: str) -> str:
    """Open a desktop application by name, for example 'chrome' or 'spotify'."""
    system = platform.system()
    try:
        if system == "Darwin":
            subprocess.Popen(["open", "-a", name])
        elif system == "Windows":
            os.startfile(name)  # type: ignore[attr-defined]
        else:
            if shutil.which(name) is None:
                return f"No executable called {name} on PATH."
            subprocess.Popen([name])
    except Exception as exc:
        log.warning("open_application(%s) failed: %s", name, exc)
        return f"Could not open {name}: {exc}"
    return f"Opened {name}."


def open_url(url: str) -> str:
    """Open a URL in the default web browser."""
    if not url.startswith(("http://", "https://")):
        url = "https://" + url
    webbrowser.open(url)
    return "Opened it."


def search_the_web(query: str) -> str:
    """Open a web search for the query in the default browser."""
    from urllib.parse import quote_plus

    webbrowser.open("https://duckduckgo.com/?q=" + quote_plus(query))
    return "Searching the web for " + query + "."


def read_clipboard() -> str:
    """Read the current text contents of the system clipboard."""
    try:
        import pyperclip
    except ImportError:
        return "Clipboard support is not installed."
    try:
        return (pyperclip.paste() or "")[:MAX_TOOL_OUTPUT] or "The clipboard is empty."
    except Exception as exc:
        return f"Could not read the clipboard: {exc}"


def write_clipboard(text: str) -> str:
    """Copy text to the system clipboard."""
    try:
        import pyperclip
    except ImportError:
        return "Clipboard support is not installed."
    try:
        pyperclip.copy(text)
    except Exception as exc:
        return f"Could not write to the clipboard: {exc}"
    return "Copied."


def get_machine_status() -> str:
    """Report basic host status: platform, CPU count and free disk space."""
    usage = shutil.disk_usage(os.path.expanduser("~"))
    free_gb = usage.free / 1_000_000_000
    return (
        f"{platform.system()} {platform.release()}, "
        f"{os.cpu_count()} CPU cores, "
        f"{free_gb:.0f} gigabytes free."
    )


def make_shell_tool(settings: Settings) -> Callable[[str], str]:
    """Build the shell tool, disarmed unless FRIDAY_ALLOW_SHELL is enabled."""

    def run_shell_command(command: str) -> str:
        """Run a shell command on this machine and return its output."""
        if not settings.allow_shell:
            return (
                "Shell access is disabled. The owner must set "
                "FRIDAY_ALLOW_SHELL to true."
            )
        log.warning("Running shell command: %s", command)
        try:
            completed = subprocess.run(
                command,
                shell=True,
                capture_output=True,
                text=True,
                timeout=30,
            )
        except subprocess.TimeoutExpired:
            return "The command timed out after thirty seconds."
        except Exception as exc:
            return f"The command failed: {exc}"

        output = (completed.stdout or completed.stderr or "").strip()
        if not output:
            return f"Done, exit code {completed.returncode}, no output."
        return output[:MAX_TOOL_OUTPUT]

    return run_shell_command
