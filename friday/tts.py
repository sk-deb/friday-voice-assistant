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
from pathlib import Path
from typing import Iterable, Protocol

from .config import TtsSettings

log = logging.getLogger("friday.tts")

_SENTENCE_END = re.compile(r"(?<=[.!?])\s+")
_UNSPEAKABLE = re.compile(r"[*_`#>]|https?://\S+")


def clean_for_speech(text: str) -> str:
    """Strip markdown noise and URLs the model should not have produced."""
    return _UNSPEAKABLE.sub(" ", text).replace("  ", " ").strip()


def split_sentences(text: str) -> list[str]:
    return [part.strip() for part in _SENTENCE_END.split(text) if part.strip()]


class Speaker(Protocol):
    """Anything that can turn a string into sound."""

    def speak(self, text: str) -> None: ...

    def close(self) -> None: ...


class NullSpeaker:
    """Prints instead of speaking."""

    def speak(self, text: str) -> None:
        print(f"[tts] {text}")

    def close(self) -> None:
        pass


class Pyttsx3Speaker:
    """System TTS through pyttsx3. Reliable everywhere, robotic."""

    def __init__(self, settings: TtsSettings) -> None:
        import pyttsx3

        self._engine = pyttsx3.init()
        self._engine.setProperty("rate", settings.rate)
        if settings.voice:
            self._engine.setProperty("voice", settings.voice)

    def speak(self, text: str) -> None:
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

    def speak(self, text: str) -> None:
        import numpy as np
        import sounddevice as sd

        result = subprocess.run(
            [
                "piper",
                "--model",
                self.settings.piper_model,
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

    candidates: Iterable[str]
    if engine == "auto":
        candidates = ("piper", "pyttsx3")
    else:
        candidates = (engine,)

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

    def say(self, text: str) -> None:
        cleaned = clean_for_speech(text)
        if not cleaned:
            return
        for sentence in split_sentences(cleaned):
            self.speaker.speak(sentence)

    def close(self) -> None:
        self.speaker.close()
