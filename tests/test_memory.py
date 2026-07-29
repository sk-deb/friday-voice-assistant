"""Tests for the SQLite memory layer. Standard library only."""

from __future__ import annotations

import tempfile
import unittest
from pathlib import Path

from friday.memory import Memory


class MemoryTests(unittest.TestCase):
    def setUp(self) -> None:
        self._tmp = tempfile.TemporaryDirectory()
        self.memory = Memory(Path(self._tmp.name) / "test.sqlite3")

    def tearDown(self) -> None:
        self.memory.close()
        self._tmp.cleanup()

    def test_remember_is_idempotent(self) -> None:
        self.assertTrue(self.memory.remember("Owner drinks black coffee"))
        self.assertFalse(self.memory.remember("Owner drinks black coffee"))
        self.assertEqual(len(self.memory.facts()), 1)

    def test_blank_facts_are_ignored(self) -> None:
        self.assertFalse(self.memory.remember("   "))
        self.assertEqual(self.memory.facts(), [])

    def test_forget_matches_substrings(self) -> None:
        self.memory.remember("Owner works at ZenvX")
        self.memory.remember("Owner lives in Colombo")
        self.assertEqual(self.memory.forget("ZenvX"), 1)
        self.assertEqual(self.memory.facts(), ["Owner lives in Colombo"])

    def test_forget_blank_is_a_noop(self) -> None:
        self.memory.remember("Owner lives in Colombo")
        self.assertEqual(self.memory.forget(""), 0)
        self.assertEqual(len(self.memory.facts()), 1)

    def test_prompt_block_is_oldest_first(self) -> None:
        self.memory.remember("first")
        self.memory.remember("second")
        self.assertEqual(self.memory.as_prompt_block(), "- first\n- second")

    def test_turn_log_round_trips(self) -> None:
        self.memory.log_turn("owner", "what time is it")
        self.memory.log_turn("friday", "Just past three.")
        turns = self.memory.recent_turns()
        self.assertEqual([turn["role"] for turn in turns], ["owner", "friday"])


if __name__ == "__main__":  # pragma: no cover
    unittest.main()
