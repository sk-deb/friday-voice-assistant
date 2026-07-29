#!/usr/bin/env python3
"""Environment check: verify every FRIDAY dependency before a first run.

Usage:
    python scripts/doctor.py

Exits non-zero when a required component is missing.
"""

from __future__ import annotations

import importlib
import shutil
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

REQUIRED = [
    ("google.genai", "google-genai", "language model client"),
    ("faster_whisper", "faster-whisper", "local speech to text"),
    ("sounddevice", "sounddevice", "microphone capture"),
    ("numpy", "numpy", "audio buffers"),
    ("webrtcvad", "webrtcvad", "voice activity detection"),
]
OPTIONAL = [
    ("openwakeword", "openwakeword", "always-on wake word"),
    ("pyttsx3", "pyttsx3", "fallback text to speech"),
    ("pyperclip", "pyperclip", "clipboard tools"),
    ("dotenv", "python-dotenv", ".env loading"),
]

OK = "  ok  "
MISSING = "MISSING"
WARN = " warn "


def check(module: str) -> bool:
    try:
        importlib.import_module(module)
        return True
    except Exception:
        return False


def main() -> int:
    failures = 0

    print("Required")
    for module, package, purpose in REQUIRED:
        present = check(module)
        failures += 0 if present else 1
        status = OK if present else MISSING
        print(f"  [{status}] {package:<16} {purpose}")
        if not present:
            print(f"           pip install {package}")

    print("\nOptional")
    for module, package, purpose in OPTIONAL:
        status = OK if check(module) else WARN
        print(f"  [{status}] {package:<16} {purpose}")

    print("\nBinaries")
    piper = shutil.which("piper")
    print(f"  [{OK if piper else WARN}] piper            {piper or 'not on PATH'}")

    print("\nConfiguration")
    try:
        from friday.config import load_settings

        settings = load_settings()
        key_state = "set" if settings.llm.api_key else "NOT SET"
        print(f"  [{OK if settings.llm.api_key else MISSING}] GEMINI_API_KEY   {key_state}")
        failures += 0 if settings.llm.api_key else 1
        print(f"  [{OK}] data directory   {settings.data_dir}")
        print(f"  [{OK}] whisper model    {settings.stt.model} on {settings.stt.device}")
        print(f"  [{OK}] wake models      {', '.join(settings.wake.models)}")

        detect = "auto-detect" if settings.stt.auto_detect else "fixed"
        print(
            f"  [{OK}] languages        "
            f"{len(settings.language.languages)} enabled, {detect} "
            f"(default {settings.language.default_language.english_name})"
        )
        # An .en model silently transcribes every language as garbled English,
        # which looks like a bad microphone rather than a configuration error.
        if settings.language.multilingual and settings.stt.model.endswith(".en"):
            print(
                f"  [{WARN}] whisper model    "
                f"{settings.stt.model} cannot transcribe non-English speech"
            )
        voiceless = [
            language.english_name
            for language in settings.language.languages
            if not language.piper_voice
        ]
        if voiceless:
            print(
                f"  [{WARN}] system voice     "
                f"{', '.join(voiceless)} have no Piper voice "
                "(see docs/LANGUAGES.md)"
            )
        print(f"  [{OK}] shell tool       {'armed' if settings.allow_shell else 'disabled'}")
    except Exception as exc:
        failures += 1
        print(f"  [{MISSING}] settings failed to load: {exc}")

    print()
    if failures:
        print(f"{failures} problem(s) to fix before FRIDAY will run.")
        return 1
    print("All clear. Try: python -m friday --mode ptt")
    return 0


if __name__ == "__main__":
    sys.exit(main())
