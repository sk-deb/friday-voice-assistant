"""Tests for the language registry, detection follow-through and prompts."""

from __future__ import annotations

import os
import tempfile
import unittest
from pathlib import Path
from unittest import mock

from friday.config import LanguageSettings, Settings, SttSettings, TtsSettings
from friday.i18n import (
    LANGUAGES,
    LanguageState,
    language_instruction,
    multilingual_model,
    resolve,
)
from friday.memory import Memory
from friday.tools import build_toolset, tool_names
from friday.tools.language import make_language_tools
from friday.tts import split_sentences

EXPECTED = ("en", "ml", "hi", "ta", "es", "it", "fr", "de", "zh", "ko", "ja")


class RegistryTests(unittest.TestCase):
    def test_every_requested_language_is_present(self) -> None:
        for code in EXPECTED:
            self.assertIn(code, LANGUAGES)

    def test_entries_are_fully_populated(self) -> None:
        for code, language in LANGUAGES.items():
            self.assertEqual(code, language.code)
            self.assertTrue(language.english_name)
            self.assertTrue(language.native_name)
            self.assertIn("{name}", language.greeting)
            self.assertTrue(language.acknowledge)
            self.assertTrue(language.fresh_start)

    def test_non_english_greetings_are_not_english(self) -> None:
        self.assertNotEqual(LANGUAGES["ml"].greeting, LANGUAGES["en"].greeting)
        self.assertNotEqual(LANGUAGES["ja"].acknowledge, LANGUAGES["en"].acknowledge)


class ResolveTests(unittest.TestCase):
    def test_resolves_by_code_name_native_and_alias(self) -> None:
        for spoken in ("ml", "Malayalam", "MALAYALAM", "മലയാളം", "mallu"):
            found = resolve(spoken)
            self.assertIsNotNone(found, spoken)
            self.assertEqual(found.code, "ml")

    def test_resolves_regional_tags(self) -> None:
        self.assertEqual(resolve("zh-CN").code, "zh")
        self.assertEqual(resolve("en_US").code, "en")

    def test_unknown_and_blank_return_none(self) -> None:
        self.assertIsNone(resolve("klingon"))
        self.assertIsNone(resolve(""))
        self.assertIsNone(resolve(None))


class ModelSelectionTests(unittest.TestCase):
    def test_english_only_models_are_widened(self) -> None:
        self.assertEqual(multilingual_model("base.en"), "base")
        self.assertEqual(multilingual_model("small.en"), "small")

    def test_already_multilingual_models_are_untouched(self) -> None:
        self.assertEqual(multilingual_model("medium"), "medium")
        self.assertEqual(multilingual_model("large-v3"), "large-v3")

    def test_multilingual_default_is_not_english_only(self) -> None:
        settings = SttSettings.from_env(LanguageSettings())
        self.assertFalse(settings.model.endswith(".en"))
        self.assertTrue(settings.auto_detect)

    def test_english_only_setup_keeps_the_fast_model(self) -> None:
        english = LanguageSettings(default="en", enabled=["en"])
        settings = SttSettings.from_env(english)
        self.assertEqual(settings.model, "base.en")
        self.assertFalse(settings.auto_detect)

    def test_explicit_model_override_is_widened_not_ignored(self) -> None:
        with mock.patch.dict(os.environ, {"FRIDAY_WHISPER_MODEL": "medium.en"}):
            self.assertEqual(SttSettings.from_env(LanguageSettings()).model, "medium")


class LanguageSettingsTests(unittest.TestCase):
    def test_all_languages_enabled_by_default(self) -> None:
        codes = [lang.code for lang in LanguageSettings().languages]
        for code in EXPECTED:
            self.assertIn(code, codes)

    def test_enabled_list_can_be_narrowed(self) -> None:
        narrow = LanguageSettings(default="ml", enabled=["ml", "en"])
        self.assertEqual([lang.code for lang in narrow.languages], ["ml", "en"])
        self.assertEqual(narrow.default_language.code, "ml")
        self.assertTrue(narrow.multilingual)

    def test_default_is_always_available_even_if_omitted(self) -> None:
        odd = LanguageSettings(default="ta", enabled=["en"])
        self.assertIn("ta", [lang.code for lang in odd.languages])

    def test_unknown_names_are_ignored(self) -> None:
        codes = [lang.code for lang in LanguageSettings(enabled=["en", "elvish"]).languages]
        self.assertEqual(codes, ["en"])

    def test_env_overrides(self) -> None:
        env = {"FRIDAY_LANGUAGE": "hi", "FRIDAY_LANGUAGES": "hi,en,ta"}
        with mock.patch.dict(os.environ, env):
            settings = LanguageSettings.from_env()
        self.assertEqual(settings.default_language.code, "hi")
        self.assertEqual([lang.code for lang in settings.languages], ["hi", "en", "ta"])


class SystemPromptTests(unittest.TestCase):
    def test_multilingual_prompt_names_the_languages(self) -> None:
        prompt = Settings().system_prompt()
        self.assertIn("Malayalam", prompt)
        self.assertIn("Japanese", prompt)
        self.assertIn("same language the owner just used", prompt)

    def test_english_only_prompt_stays_clean(self) -> None:
        english = Settings(language=LanguageSettings(default="en", enabled=["en"]))
        self.assertNotIn("Language rules", english.system_prompt())

    def test_instruction_is_empty_for_english_only(self) -> None:
        self.assertEqual(language_instruction(LANGUAGES["en"], [LANGUAGES["en"]]), "")


class LanguageStateTests(unittest.TestCase):
    def setUp(self) -> None:
        allowed = [LANGUAGES["en"], LANGUAGES["ml"], LANGUAGES["ja"]]
        self.state = LanguageState(LANGUAGES["en"], allowed)

    def test_detection_switches_language(self) -> None:
        self.assertEqual(self.state.observe("ml").code, "ml")

    def test_unknown_or_disabled_detection_is_ignored(self) -> None:
        self.state.observe("ml")
        self.assertEqual(self.state.observe("fr").code, "ml")
        self.assertEqual(self.state.observe(None).code, "ml")

    def test_locking_beats_detection(self) -> None:
        self.state.set("ja", lock=True)
        self.assertEqual(self.state.observe("ml").code, "ja")
        self.state.locked = False
        self.assertEqual(self.state.observe("ml").code, "ml")

    def test_set_rejects_disabled_languages(self) -> None:
        self.assertIsNone(self.state.set("tamil"))
        self.assertEqual(self.state.current.code, "en")

    def test_reset_returns_to_default(self) -> None:
        self.state.set("ja", lock=True)
        self.state.reset()
        self.assertEqual(self.state.current.code, "en")
        self.assertFalse(self.state.locked)


class LanguageToolTests(unittest.TestCase):
    def setUp(self) -> None:
        self._tmp = tempfile.TemporaryDirectory()
        self.settings = Settings(data_dir=Path(self._tmp.name))
        self.memory = Memory(self.settings.db_path)

    def tearDown(self) -> None:
        self.memory.close()
        self._tmp.cleanup()

    def test_language_tools_are_registered(self) -> None:
        names = tool_names(build_toolset(self.settings, self.memory))
        for expected in ("speak_in_language", "follow_my_language", "list_languages"):
            self.assertIn(expected, names)

    def test_switching_locks_and_reports(self) -> None:
        state = LanguageState(LANGUAGES["en"], [LANGUAGES["en"], LANGUAGES["ta"]])
        speak, follow, listing = make_language_tools(state)

        self.assertIn("Tamil", speak("tamil"))
        self.assertTrue(state.locked)
        self.assertEqual(state.current.code, "ta")

        self.assertIn("follow", follow().lower())
        self.assertFalse(state.locked)
        self.assertIn("Tamil", listing())

    def test_unsupported_language_lists_alternatives(self) -> None:
        state = LanguageState(LANGUAGES["en"], [LANGUAGES["en"]])
        speak, _follow, _listing = make_language_tools(state)
        reply = speak("Klingon")
        self.assertIn("do not have", reply)
        self.assertIn("English", reply)


class ScriptTests(unittest.TestCase):
    def test_cjk_and_indic_sentences_are_split(self) -> None:
        self.assertEqual(
            split_sentences("今日は晴れ。気温は22度。"),
            ["今日は晴れ。", "気温は22度。"],
        )
        self.assertEqual(
            split_sentences("नमस्ते। सब ठीक है।"),
            ["नमस्ते।", "सब ठीक है।"],
        )

    def test_piper_voice_paths_are_per_language(self) -> None:
        tts = TtsSettings()
        self.assertIn("de_DE", tts.piper_model_for(LANGUAGES["de"]))
        # Malayalam has no Piper voice yet, so it must fall back, not crash.
        self.assertEqual(tts.piper_model_for(LANGUAGES["ml"]), tts.piper_model)

    def test_per_language_voice_override_wins(self) -> None:
        with mock.patch.dict(os.environ, {"FRIDAY_PIPER_VOICE_ML": "voices/ml.onnx"}):
            tts = TtsSettings.from_env()
        self.assertEqual(tts.piper_model_for(LANGUAGES["ml"]), "voices/ml.onnx")


if __name__ == "__main__":  # pragma: no cover
    unittest.main()
