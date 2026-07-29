"""Tool registry.

``build_toolset`` assembles the callables handed to the model. Tools that need
state (settings, memory) are produced by factory functions so the tool bodies
stay dependency-free.
"""

from __future__ import annotations

from collections.abc import Callable

from ..config import Settings
from ..i18n import LanguageState
from ..memory import Memory
from .knowledge import make_memory_tools, make_note_tools
from .language import make_language_tools
from .system import (
    get_current_time,
    get_machine_status,
    make_shell_tool,
    open_application,
    open_url,
    read_clipboard,
    search_the_web,
    write_clipboard,
)

__all__ = ["build_toolset", "tool_names"]


def build_toolset(
    settings: Settings,
    memory: Memory,
    language: LanguageState | None = None,
) -> list[Callable[..., object]]:
    """Return every tool FRIDAY should be able to call."""
    tools: list[Callable[..., object]] = [
        get_current_time,
        get_machine_status,
        open_application,
        open_url,
        search_the_web,
        read_clipboard,
        write_clipboard,
        make_shell_tool(settings),
    ]
    tools.extend(make_memory_tools(memory))
    tools.extend(make_note_tools(settings))
    tools.extend(
        make_language_tools(
            language
            or LanguageState(
                settings.language.default_language, settings.language.languages
            )
        )
    )
    return tools


def tool_names(tools: list[Callable[..., object]]) -> list[str]:
    return [getattr(tool, "__name__", repr(tool)) for tool in tools]
