"""Central configuration for FRIDAY.

Every tunable lives here and is overridable through environment variables or a
local ``.env`` file. No other module reads ``os.environ`` directly.
"""

from __future__ import annotations

import os
from dataclasses import dataclass, field
from pathlib import Path

from .i18n import (
    DEFAULT_LANGUAGE,
    LANGUAGES,
    Language,
    describe_languages,
    enabled_languages,
    language_instruction,
    multilingual_model,
    resolve,
)


def _str(key: str, default: str) -> str:
    value = os.getenv(key)
    return default if value is None or value == "" else value


def _int(key: str, default: int) -> int:
    try:
        return int(_str(key, str(default)))
    except ValueError:
        return default


def _float(key: str, default: float) -> float:
    try:
        return float(_str(key, str(default)))
    except ValueError:
        return default


def _bool(key: str, default: bool) -> bool:
    return _str(key, "1" if default else "0").strip().lower() in {
        "1",
        "true",
        "yes",
        "on",
    }


def _list(key: str, default: list[str]) -> list[str]:
    raw = os.getenv(key)
    if not raw:
        return list(default)
    return [item.strip() for item in raw.split(",") if item.strip()]


@dataclass(frozen=True)
class AudioSettings:
    """Microphone capture and voice-activity detection."""

    sample_rate: int = 16_000
    frame_ms: int = 30
    silence_tail_ms: int = 900
    max_utterance_s: int = 20
    min_utterance_ms: int = 250
    vad_aggressiveness: int = 2
    preroll_ms: int = 300
    input_device: str | None = None

    @property
    def frame_len(self) -> int:
        """Samples per frame. webrtcvad accepts only 10, 20 or 30 ms frames."""
        return int(self.sample_rate * self.frame_ms / 1000)

    @classmethod
    def from_env(cls) -> "AudioSettings":
        return cls(
            sample_rate=_int("FRIDAY_SAMPLE_RATE", 16_000),
            frame_ms=_int("FRIDAY_FRAME_MS", 30),
            silence_tail_ms=_int("FRIDAY_SILENCE_TAIL_MS", 900),
            max_utterance_s=_int("FRIDAY_MAX_UTTERANCE_S", 20),
            min_utterance_ms=_int("FRIDAY_MIN_UTTERANCE_MS", 250),
            vad_aggressiveness=_int("FRIDAY_VAD_AGGRESSIVENESS", 2),
            preroll_ms=_int("FRIDAY_PREROLL_MS", 300),
            input_device=os.getenv("FRIDAY_INPUT_DEVICE") or None,
        )


@dataclass(frozen=True)
class LanguageSettings:
    """Which languages FRIDAY works in.

    ``default`` is the fallback when detection is unsure. ``enabled`` is the set
    she is allowed to switch into. Narrowing ``enabled`` to the languages you
    actually speak measurably improves detection accuracy.
    """

    default: str = "en"
    enabled: list[str] = field(default_factory=lambda: list(LANGUAGES))
    auto_detect: bool = True

    @property
    def default_language(self) -> Language:
        return resolve(self.default) or DEFAULT_LANGUAGE

    @property
    def languages(self) -> list[Language]:
        """Enabled languages, with the default guaranteed to be present."""
        found = enabled_languages(self.enabled)
        fallback = self.default_language
        if fallback not in found:
            found.insert(0, fallback)
        return found

    @property
    def multilingual(self) -> bool:
        """True when anything other than English-only is in play."""
        return len(self.languages) > 1 or self.default_language.code != "en"

    def describe(self) -> str:
        return describe_languages(self.languages)

    @classmethod
    def from_env(cls) -> "LanguageSettings":
        return cls(
            default=_str("FRIDAY_LANGUAGE", "en"),
            enabled=_list("FRIDAY_LANGUAGES", list(LANGUAGES)),
            auto_detect=_bool("FRIDAY_AUTO_DETECT_LANGUAGE", True),
        )


@dataclass(frozen=True)
class SttSettings:
    """Local speech-to-text (faster-whisper / CTranslate2)."""

    model: str = "base.en"
    device: str = "cpu"
    compute_type: str = "int8"
    language: str = "en"
    beam_size: int = 1
    vad_filter: bool = True
    auto_detect: bool = False

    @classmethod
    def from_env(cls, language: "LanguageSettings | None" = None) -> "SttSettings":
        language = language or LanguageSettings()

        # English-only models are both faster and better - but they cannot
        # transcribe anything else, so multilingual setups need a bigger model.
        # ``small`` is the smallest that handles Malayalam and Tamil usably.
        fallback_model = "small" if language.multilingual else "base.en"
        model = _str("FRIDAY_WHISPER_MODEL", fallback_model)
        if language.multilingual:
            model = multilingual_model(model)

        return cls(
            model=model,
            device=_str("FRIDAY_WHISPER_DEVICE", "cpu"),
            compute_type=_str("FRIDAY_WHISPER_COMPUTE_TYPE", "int8"),
            language=_str("FRIDAY_WHISPER_LANGUAGE", language.default_language.code),
            beam_size=_int("FRIDAY_WHISPER_BEAM_SIZE", 1),
            vad_filter=_bool("FRIDAY_WHISPER_VAD_FILTER", True),
            auto_detect=language.multilingual and language.auto_detect,
        )


@dataclass(frozen=True)
class LlmSettings:
    """Gemini settings. This is the only component that touches the network."""

    api_key: str = ""
    model: str = "gemini-2.5-flash"
    temperature: float = 0.7
    thinking_budget: int = 0
    max_output_tokens: int = 512
    stream: bool = True

    @classmethod
    def from_env(cls) -> "LlmSettings":
        return cls(
            api_key=_str("GEMINI_API_KEY", ""),
            model=_str("FRIDAY_MODEL", "gemini-2.5-flash"),
            temperature=_float("FRIDAY_TEMPERATURE", 0.7),
            thinking_budget=_int("FRIDAY_THINKING_BUDGET", 0),
            max_output_tokens=_int("FRIDAY_MAX_OUTPUT_TOKENS", 512),
            stream=_bool("FRIDAY_STREAM", True),
        )


@dataclass(frozen=True)
class TtsSettings:
    """Text-to-speech. ``auto`` prefers Piper and falls back to pyttsx3."""

    engine: str = "auto"  # auto | piper | pyttsx3 | none
    piper_model: str = "voices/en_US-amy-medium.onnx"
    piper_sample_rate: int = 22_050
    rate: int = 185
    voice: str | None = None
    voice_dir: str = "voices"
    piper_voices: dict[str, str] = field(default_factory=dict)
    system_voices: dict[str, str] = field(default_factory=dict)

    def piper_model_for(self, language: Language) -> str:
        """Path to the Piper voice for a language, or the default voice.

        Resolution order: an explicit ``FRIDAY_PIPER_VOICE_<CODE>`` override,
        then the registry's suggested voice inside ``voice_dir``, then the
        default model. Existence is checked by the speaker, not here.
        """
        override = self.piper_voices.get(language.code)
        if override:
            return override
        if language.piper_voice:
            return f"{self.voice_dir}/{language.piper_voice}.onnx"
        return self.piper_model

    def system_voice_for(self, language: Language) -> str | None:
        """Explicit system-voice id for a language, when one was configured."""
        return self.system_voices.get(language.code) or self.voice

    @classmethod
    def from_env(cls) -> "TtsSettings":
        # Per-language overrides: FRIDAY_PIPER_VOICE_ML, FRIDAY_TTS_VOICE_JA, ...
        piper_voices: dict[str, str] = {}
        system_voices: dict[str, str] = {}
        for code in LANGUAGES:
            piper = os.getenv(f"FRIDAY_PIPER_VOICE_{code.upper()}")
            if piper:
                piper_voices[code] = piper
            system = os.getenv(f"FRIDAY_TTS_VOICE_{code.upper()}")
            if system:
                system_voices[code] = system

        return cls(
            engine=_str("FRIDAY_TTS_ENGINE", "auto").lower(),
            piper_model=_str("FRIDAY_PIPER_MODEL", "voices/en_US-amy-medium.onnx"),
            piper_sample_rate=_int("FRIDAY_PIPER_SAMPLE_RATE", 22_050),
            rate=_int("FRIDAY_TTS_RATE", 185),
            voice=os.getenv("FRIDAY_TTS_VOICE") or None,
            voice_dir=_str("FRIDAY_VOICE_DIR", "voices"),
            piper_voices=piper_voices,
            system_voices=system_voices,
        )


@dataclass(frozen=True)
class WakeSettings:
    """Offline wake-word detection (openWakeWord)."""

    models: list[str] = field(default_factory=lambda: ["hey_jarvis"])
    threshold: float = 0.5
    cooldown_s: float = 1.5
    acknowledge: bool = True

    @classmethod
    def from_env(cls) -> "WakeSettings":
        return cls(
            models=_list("FRIDAY_WAKE_MODELS", ["hey_jarvis"]),
            threshold=_float("FRIDAY_WAKE_THRESHOLD", 0.5),
            cooldown_s=_float("FRIDAY_WAKE_COOLDOWN_S", 1.5),
            acknowledge=_bool("FRIDAY_WAKE_ACKNOWLEDGE", True),
        )


DEFAULT_PERSONA = """You are {name}, {owner}'s personal assistant.

Hard rules:
- Your replies are spoken aloud. Never use markdown, bullet points, emoji,
  code fences or raw URLs. Write words a person would actually say.
- Default to one or two sentences. Go longer only when explicitly asked.
- Prefer calling a tool over guessing. If a tool fails, say what failed.
- If you do not know something, say so in five words or fewer.
- Be dry, competent and a little witty. Never say "As an AI".
- Never read out long lists. Summarise, then offer to continue.
"""


@dataclass(frozen=True)
class Settings:
    """Top-level, immutable application settings."""

    name: str = "Friday"
    owner: str = "Srihari"
    data_dir: Path = Path.home() / ".friday"
    log_level: str = "INFO"
    allow_shell: bool = False
    language: LanguageSettings = field(default_factory=LanguageSettings)
    audio: AudioSettings = field(default_factory=AudioSettings)
    stt: SttSettings = field(default_factory=SttSettings)
    llm: LlmSettings = field(default_factory=LlmSettings)
    tts: TtsSettings = field(default_factory=TtsSettings)
    wake: WakeSettings = field(default_factory=WakeSettings)
    persona: str = DEFAULT_PERSONA

    @property
    def db_path(self) -> Path:
        return self.data_dir / "friday.sqlite3"

    @property
    def notes_path(self) -> Path:
        return self.data_dir / "notes.md"

    @property
    def log_path(self) -> Path:
        return self.data_dir / "friday.log"

    def system_prompt(self, memories: str = "") -> str:
        prompt = self.persona.format(name=self.name, owner=self.owner)
        prompt += language_instruction(
            self.language.default_language, self.language.languages
        )
        if memories:
            prompt += "\nThings you already know about the owner:\n" + memories
        return prompt

    @classmethod
    def from_env(cls) -> "Settings":
        data_dir = Path(
            _str("FRIDAY_DATA_DIR", str(Path.home() / ".friday"))
        ).expanduser()
        language = LanguageSettings.from_env()
        return cls(
            name=_str("FRIDAY_NAME", "Friday"),
            owner=_str("FRIDAY_OWNER", "Srihari"),
            data_dir=data_dir,
            log_level=_str("FRIDAY_LOG_LEVEL", "INFO").upper(),
            allow_shell=_bool("FRIDAY_ALLOW_SHELL", False),
            language=language,
            audio=AudioSettings.from_env(),
            stt=SttSettings.from_env(language),
            llm=LlmSettings.from_env(),
            tts=TtsSettings.from_env(),
            wake=WakeSettings.from_env(),
            persona=_str("FRIDAY_PERSONA", DEFAULT_PERSONA),
        )


def load_settings() -> Settings:
    """Load ``.env`` when python-dotenv is available, then build Settings."""
    try:  # optional dependency
        from dotenv import load_dotenv

        load_dotenv()
    except ImportError:  # pragma: no cover - dotenv is optional
        pass

    settings = Settings.from_env()
    settings.data_dir.mkdir(parents=True, exist_ok=True)
    return settings
