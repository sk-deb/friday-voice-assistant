"""Memory and note-taking tools, bound to a Memory instance at build time."""

from __future__ import annotations

import datetime as _dt
from typing import Callable

from ..config import Settings
from ..memory import Memory


def make_memory_tools(memory: Memory) -> list[Callable[..., str]]:
    """Return tools that read and write FRIDAY's long-term memory."""

    def remember_fact(fact: str) -> str:
        """Store a durable fact about the owner or their preferences."""
        return "Noted." if memory.remember(fact) else "I already knew that."

    def forget_fact(topic: str) -> str:
        """Delete remembered facts that mention the given topic."""
        removed = memory.forget(topic)
        if removed == 0:
            return "I had nothing stored about that."
        return f"Forgot {removed} thing{'s' if removed != 1 else ''}."

    def list_remembered_facts() -> str:
        """List what is currently remembered about the owner."""
        facts = memory.facts(limit=25)
        if not facts:
            return "I have not stored anything yet."
        return "; ".join(facts)

    return [remember_fact, forget_fact, list_remembered_facts]


def make_note_tools(settings: Settings) -> list[Callable[..., str]]:
    """Return tools that append to and read the local notes file."""

    def take_note(text: str) -> str:
        """Append a timestamped line to the owner's local notes file."""
        settings.notes_path.parent.mkdir(parents=True, exist_ok=True)
        stamp = _dt.datetime.now().strftime("%Y-%m-%d %H:%M")
        with settings.notes_path.open("a", encoding="utf-8") as handle:
            handle.write(f"- {stamp} - {text}\n")
        return "Written down."

    def read_recent_notes(count: int = 5) -> str:
        """Read back the most recent notes. Count defaults to five."""
        if not settings.notes_path.exists():
            return "There are no notes yet."
        lines = [
            line.strip("- \n")
            for line in settings.notes_path.read_text(encoding="utf-8").splitlines()
            if line.strip()
        ]
        if not lines:
            return "There are no notes yet."
        return " | ".join(lines[-max(1, count) :])

    return [take_note, read_recent_notes]
