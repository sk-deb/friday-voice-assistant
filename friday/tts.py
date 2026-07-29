"""Text-to-speech with a pluggable backend.

Backends, in order of preference when ``engine=auto``:

1. **Piper** - offline neural TTS, natural sounding, needs a voice model.
2. **pyttsx3** - the OS voice. Always available, sounds like 2009.
3. **Null** - prints only. Used in tests and on headless machines.

Replies are split into sentences and spoken one at a time so speech starts
before the model has finished generating.
"""

from __future__ import annotations

import logging
import re
import shutil
import subprocess
from collections.abc import Iterable
from pathlib import Path
from typing import Protocol

from .config import TtsSettings
from .i18n import DEFAULT_LANGUAGE, Language

log = logging.getLogger("friday.tts")

# Latin scripts end sentences with . ! ? - CJK uses its own full-width marks,
# and Devanagari, Malayalam and Tamil all use the danda for a full stop.
_SENTENCE_END = re.compile(r"(?<=[.!?\u3002\uff01\uff1f\u0964\u0965])\s*")
_UNSPEAKABLE = re.compile(r"[*_`#>]|https?://\S+")


def clean_for_speech(text: str) -> str:
    """Strip markdown noise and URLs the model should not have produced."""
    return _UNSPEAKABLE.sub(" ", text).replace("  ", " ").strip()


def split_sentences(text: str) -> list[str]:
    """Split into speakable sentences across Latin, CJK and Indic punctuation."""
    return [part.strip() for part in _SENTENCE_END.split(text) if part.strip()]


class Speaker(Protocol):
    """Anything that can turn a string into sound."""

    def speak(self, text: str, language: Language | None = None) -> None: ...

    def close(self) -> None: ...


class NullSpeaker:
    """Prints instead of speaking."""

    def speak(self, text: str, language: Language | None = None) -> None:
        tag = (language or DEFAULT_LANGUAGE).code
        print(f"[tts:{tag}] {text}")

    def close(self) -> None:
        pass


class Pyttsx3Speaker:
    """System TTS through pyttsx3. Reliable everywhere, robotic."""

    def __init__(self, settings: TtsSettings) -> None:
        import pyttsx3

        self.settings = settings
        self._engine = pyttsx3.init()
        self._engine.setProperty("rate", settings.rate)
        if settings.voice:
            self._engine.setProperty("voice", settings.voice)

        self._installed = self._catalogue()
        self._current: str | None = None

    def _catalogue(self) -> list[tuple[str, str, tuple[str, ...]]]:
        """Snapshot the installed system voices as (id, name, language tags)."""
        catalogue: list[tuple[str, str, tuple[str, ...]]] = []
        try:
            for voice in self._engine.getProperty("voices"):
                langs: list[str] = []
                for raw in getattr(voice, "languages", []) or []:
                    if isinstance(raw, bytes):
                        raw = raw.decode("utf-8", "ignore").strip("\x05\x00 ")
                    if raw:
                        langs.append(str(raw).lower())
                catalogue.append((voice.id, (voice.name or "").lower(), tuple(langs)))
        except Exception as exc:  # pragma: no cover - driver dependent
            log.debug("Could not enumerate system voices: %s", exc)
        return catalogue

    def _voice_for(self, language: Language) -> str | None:
        """Find an installed system voice that can pronounce this language.

        Windows exposes SAPI voices with tags like ``ja-JP``; macOS and
        espeak-ng report names instead. Both are checked, and configuration
        always wins.
        """
        configured = self.settings.system_voice_for(language)
        if configured:
            return configured

        code = language.code
        english = language.english_name.lower()
        for voice_id, name, langs in self._installed:
            if any(tag == code or tag.startswith(f"{code}-") for tag in langs):
                return voice_id
            if english in name or f"\\{code}-" in voice_id.lower():
                return voice_id
        return None

    def speak(self, text: str, language: Language | None = None) -> None:
        language = language or DEFAULT_LANGUAGE
        wanted = self._voice_for(language)
        if wanted and wanted != self._current:
            try:
                self._engine.setProperty("voice", wanted)
                self._current = wanted
            except Exception as exc:  # pragma: no cover - driver dependent
                log.debug("Could not switch to voice %s: %s", wanted, exc)
        elif not wanted and language.code != "en":
            log.info(
                "No installed system voice for %s - it will be read with the "
                "default voice and sound wrong. See docs/LANGUAGES.md",
                language.english_name,
            )

        self._engine.say(text)
        self._engine.runAndWait()

    def close(self) -> None:
        try:
            self._engine.stop()
        except Exception:  # pragma: no cover - driver dependent
            pass


class PiperSpeaker:
    """Offline neural TTS. Streams raw PCM from the piper CLI to the sound card."""

    def __init__(self, settings: TtsSettings) -> None:
        self.settings = settings
        if shutil.which("piper") is None:
            raise RuntimeError("piper binary not found on PATH")
        if not Path(settings.piper_model).exists():
            raise RuntimeError(f"piper voice not found: {settings.piper_model}")

        import numpy  # noqa: F401  (validated up front, used in speak)
        import sounddevice  # noqa: F401

        self._warned: set[str] = set()

    def _model_for(self, language: Language) -> str:
        """Per-language voice when it is installed, default voice otherwise."""
        candidate = self.settings.piper_model_for(language)
        if Path(candidate).exists():
            return candidate
        if language.code not in self._warned:
            self._warned.add(language.code)
            log.info(
                "No Piper voice at %s for %s - using the default voice. "
                "See docs/LANGUAGES.md to install one.",
                candidate,
                language.english_name,
            )
        return self.settings.piper_model

    def speak(self, text: str, language: Language | None = None) -> None:
        import numpy as np
        import sounddevice as sd

        result = subprocess.run(
            [
                "piper",
                "--model",
                self._model_for(language or DEFAULT_LANGUAGE),
                "--output_raw",
            ],
            input=text.encode("utf-8"),
            capture_output=True,
            check=False,
        )
        if result.returncode != 0:
            log.warning("piper failed: %s", result.stderr.decode("utf-8", "ignore"))
            return

        audio = np.frombuffer(result.stdout, dtype=np.int16)
        sd.play(audio, self.settings.piper_sample_rate)
        sd.wait()

    def close(self) -> None:
        pass


def build_speaker(settings: TtsSettings) -> Speaker:
    """Instantiate the best available backend for the requested engine."""
    engine = settings.engine

    if engine == "none":
        return NullSpeaker()

    candidates: Iterable[str] = ("piper", "pyttsx3") if engine == "auto" else (engine,)

    for candidate in candidates:
        try:
            if candidate == "piper":
                speaker = PiperSpeaker(settings)
            elif candidate == "pyttsx3":
                speaker = Pyttsx3Speaker(settings)
            else:
                log.warning("Unknown TTS engine %r", candidate)
                continue
            log.info("TTS backend: %s", candidate)
            return speaker
        except Exception as exc:
            log.info("TTS backend %s unavailable (%s)", candidate, exc)

    log.warning("No TTS backend available - falling back to printing")
    return NullSpeaker()


class Voice:
    """Sentence-at-a-time speaking on top of a Speaker backend."""

    def __init__(self, speaker: Speaker) -> None:
        self.speaker = speaker

    def say(self, text: str, language: Language | None = None) -> None:
        cleaned = clean_for_speech(text)
        if not cleaned:
            return
        for sentence in split_sentences(cleaned):
            self.speaker.speak(sentence, language)

    def close(self) -> None:
        self.speaker.close()
