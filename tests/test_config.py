"""Tests for configuration loading and the system prompt."""

from __future__ import annotations

import os
import unittest
from unittest import mock

from friday.config import AudioSettings, Settings


class AudioSettingsTests(unittest.TestCase):
    def test_frame_len_matches_frame_duration(self) -> None:
        audio = AudioSettings(sample_rate=16_000, frame_ms=30)
        self.assertEqual(audio.frame_len, 480)

    def test_env_overrides_are_applied(self) -> None:
        with mock.patch.dict(os.environ, {"FRIDAY_SILENCE_TAIL_MS": "600"}):
            self.assertEqual(AudioSettings.from_env().silence_tail_ms, 600)

    def test_invalid_numbers_fall_back_to_defaults(self) -> None:
        with mock.patch.dict(os.environ, {"FRIDAY_FRAME_MS": "not-a-number"}):
            self.assertEqual(AudioSettings.from_env().frame_ms, 30)


class SettingsTests(unittest.TestCase):
    def test_shell_is_disabled_by_default(self) -> None:
        self.assertFalse(Settings().allow_shell)

    def test_boolean_env_parsing(self) -> None:
        with mock.patch.dict(os.environ, {"FRIDAY_ALLOW_SHELL": "true"}):
            self.assertTrue(Settings.from_env().allow_shell)
        with mock.patch.dict(os.environ, {"FRIDAY_ALLOW_SHELL": "nope"}):
            self.assertFalse(Settings.from_env().allow_shell)

    def test_system_prompt_interpolates_identity(self) -> None:
        prompt = Settings(name="Friday", owner="Srihari").system_prompt()
        self.assertIn("You are Friday, Srihari's personal assistant.", prompt)
        self.assertNotIn("{name}", prompt)

    def test_system_prompt_appends_memories(self) -> None:
        prompt = Settings().system_prompt("- likes short answers")
        self.assertIn("Things you already know", prompt)
        self.assertIn("likes short answers", prompt)

    def test_derived_paths_live_under_data_dir(self) -> None:
        settings = Settings()
        self.assertEqual(settings.db_path.parent, settings.data_dir)
        self.assertEqual(settings.notes_path.parent, settings.data_dir)
        self.assertEqual(settings.log_path.parent, settings.data_dir)


if __name__ == "__main__":  # pragma: no cover
    unittest.main()
