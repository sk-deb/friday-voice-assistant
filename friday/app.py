"""Application orchestration: wires ears, transcriber, brain and voice together.

Three run modes share one turn implementation:

* ``text``  - typed input, no audio hardware needed. Best for development.
* ``ptt``   - press Enter, speak, release. Best first smoke test.
* ``wake``  - always-on, triggered by the wake word.
"""

from __future__ import annotations

import logging
import time

from .audio.ears import AudioUnavailableError, Ears
from .audio.wake import WakeWordDetector
from .config import Settings
from .i18n import LanguageState
from .llm import Brain
from .memory import Memory
from .stt import Transcriber
from .tools import build_toolset, tool_names
from .tts import Voice, build_speaker

log = logging.getLogger("friday.app")

CANCEL_PHRASES = {
    "stop",
    "stop.",
    "cancel",
    "never mind",
    "nevermind",
    "forget it",
}
RESET_PHRASES = {"new conversation", "start over", "reset", "forget this chat"}


class Friday:
    """The assistant. Construct, ``start()``, then run a mode."""

    def __init__(self, settings: Settings) -> None:
        self.settings = settings
        self.memory = Memory(settings.db_path)
        self.voice = Voice(build_speaker(settings.tts))
        self.language = LanguageState(
            settings.language.default_language, settings.language.languages
        )
        self.tools = build_toolset(settings, self.memory, self.language)
        self.brain = Brain(
            settings, tools=self.tools, memories=self.memory.as_prompt_block()
        )
        self.transcriber = Transcriber(settings.stt)
        self.ears: Ears | None = None

    # ------------------------------------------------------------- lifecycle
    def start(self, audio: bool = True) -> "Friday":
        log.info("Tools loaded: %s", ", ".join(tool_names(self.tools)))
        log.info("Languages: %s", self.settings.language.describe())
        self.brain.load()
        if audio:
            self.transcriber.load()
            self.ears = Ears(self.settings.audio).start()
        return self

    def close(self) -> None:
        if self.ears is not None:
            self.ears.close()
        self.voice.close()
        self.memory.close()

    def __enter__(self) -> "Friday":
        return self

    def __exit__(self, *_exc: object) -> None:
        self.close()

    # ------------------------------------------------------------------ core
    def say(self, text: str) -> None:
        """Speak, muting the microphone so FRIDAY never hears herself."""
        if not text:
            return
        print(f"{self.settings.name.upper()}: {text}")
        language = self.language.current
        if self.ears is not None:
            with self.ears.muted():
                self.voice.say(text, language)
        else:
            self.voice.say(text, language)

    def respond(self, text: str) -> str:
        """Run one brain turn, speaking each sentence as it arrives."""
        lowered = text.strip().lower()
        if lowered in CANCEL_PHRASES:
            return ""
        if lowered in RESET_PHRASES:
            self.brain.reset()
            fresh = self.language.current.fresh_start
            self.say(fresh)
            return fresh

        self.memory.log_turn("owner", text)
        started = time.monotonic()
        spoken: list[str] = []
        for sentence in self.brain.stream(text):
            spoken.append(sentence)
            self.say(sentence)
        reply = " ".join(spoken).strip()
        if reply:
            self.memory.log_turn(self.settings.name.lower(), reply)
        log.info("Turn completed in %.2fs", time.monotonic() - started)
        return reply

    def listen_once(self) -> str:
        """Record one utterance and transcribe it. Returns "" on silence."""
        if self.ears is None:
            raise AudioUnavailableError("Friday was started without audio")
        audio = self.ears.record_utterance()
        if audio is None:
            return ""

        text, detected = self.transcriber.transcribe_detect(audio)

        # Follow the owner into whatever language they just used, so the reply
        # is both generated and spoken in that language.
        previous = self.language.current
        current = self.language.observe(detected)
        if current is not previous:
            log.info("Language switched to %s", current.english_name)

        if text:
            print(f"YOU [{current.code}]: {text}")
        return text

    def voice_turn(self) -> str:
        text = self.listen_once()
        if not text:
            return ""
        return self.respond(text)

    # ----------------------------------------------------------------- modes
    def run_text(self) -> None:
        """Typed conversation. No microphone, no speakers required."""
        print(f"{self.settings.name} is listening. Ctrl-C to quit.")
        while True:
            try:
                text = input("you> ").strip()
            except (EOFError, KeyboardInterrupt):
                print()
                return
            if text.lower() in {"quit", "exit"}:
                return
            if text:
                self.respond(text)

    def run_push_to_talk(self) -> None:
        """Press Enter, speak, stop speaking. Repeat."""
        self.say(self.language.current.greeting.format(name=self.settings.name))
        while True:
            try:
                input("\n[Enter to talk, Ctrl-C to quit] ")
            except (EOFError, KeyboardInterrupt):
                print()
                return
            try:
                self.voice_turn()
            except KeyboardInterrupt:
                print()
                return

    def run_wake_word(self) -> None:
        """Always-on: wait for the wake word, then handle one turn."""
        if self.ears is None:
            raise AudioUnavailableError("Friday was started without audio")

        detector = WakeWordDetector(self.settings.wake).load()
        self.say(self.language.current.greeting.format(name=self.settings.name))

        try:
            for frame in self.ears.frames():
                if not detector.feed(frame):
                    continue
                if self.settings.wake.acknowledge:
                    self.say(self.language.current.acknowledge)
                self.ears.drain()
                self.voice_turn()
                detector.reset()
        except KeyboardInterrupt:
            print()
            return
