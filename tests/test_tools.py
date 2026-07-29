"""Tests for the tool layer: registry shape, shell gating, notes and memory."""

from __future__ import annotations

import tempfile
import unittest
from pathlib import Path

from friday.config import Settings
from friday.memory import Memory
from friday.tools import build_toolset, tool_names
from friday.tools.knowledge import make_memory_tools, make_note_tools
from friday.tools.system import get_current_time, make_shell_tool
from friday.tts import clean_for_speech, split_sentences


class ToolRegistryTests(unittest.TestCase):
    def setUp(self) -> None:
        self._tmp = tempfile.TemporaryDirectory()
        self.settings = Settings(data_dir=Path(self._tmp.name))
        self.memory = Memory(self.settings.db_path)

    def tearDown(self) -> None:
        self.memory.close()
        self._tmp.cleanup()

    def test_every_tool_is_callable_and_documented(self) -> None:
        tools = build_toolset(self.settings, self.memory)
        self.assertGreaterEqual(len(tools), 10)
        for tool in tools:
            self.assertTrue(callable(tool))
            self.assertTrue(
                (tool.__doc__ or "").strip(),
                f"{tool.__name__} needs a docstring; the model reads it",
            )

    def test_expected_tools_are_registered(self) -> None:
        names = tool_names(build_toolset(self.settings, self.memory))
        for expected in (
            "get_current_time",
            "run_shell_command",
            "remember_fact",
            "take_note",
        ):
            self.assertIn(expected, names)

    def test_shell_is_refused_unless_explicitly_allowed(self) -> None:
        blocked = make_shell_tool(self.settings)("echo hello")
        self.assertIn("disabled", blocked.lower())

    def test_shell_runs_when_allowed(self) -> None:
        allowed = Settings(data_dir=self.settings.data_dir, allow_shell=True)
        self.assertIn("hello", make_shell_tool(allowed)("echo hello"))

    def test_notes_round_trip(self) -> None:
        take_note, read_recent_notes = make_note_tools(self.settings)
        self.assertIn("no notes", read_recent_notes().lower())
        take_note("buy coffee")
        self.assertIn("buy coffee", read_recent_notes())

    def test_memory_tools_report_duplicates(self) -> None:
        remember, forget, listing = make_memory_tools(self.memory)
        self.assertEqual(remember("owner hates small talk"), "Noted.")
        self.assertIn("already", remember("owner hates small talk"))
        self.assertIn("small talk", listing())
        self.assertIn("1", forget("small talk"))

    def test_get_current_time_is_speakable(self) -> None:
        self.assertRegex(get_current_time(), r"\d{4}")


class SpeechCleanupTests(unittest.TestCase):
    def test_markdown_and_urls_are_stripped(self) -> None:
        cleaned = clean_for_speech("**Done** - see https://example.com `now`")
        self.assertNotIn("*", cleaned)
        self.assertNotIn("http", cleaned)

    def test_sentences_are_split_for_incremental_speech(self) -> None:
        self.assertEqual(
            split_sentences("One thing. Then another! Last?"),
            ["One thing.", "Then another!", "Last?"],
        )


if __name__ == "__main__":  # pragma: no cover
    unittest.main()
