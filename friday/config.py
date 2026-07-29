"""Central configuration for FRIDAY.

Every tunable lives here and is overridable through environment variables or a
local ``.env`` file. No other module reads ``os.environ`` directly.
"""

from __future__ import annotations

import os
from dataclasses import dataclass, field
from pathlib import Path


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
class SttSettings:
    """Local speech-to-text (faster-whisper / CTranslate2)."""

    model: str = "base.en"
    device: str = "cpu"
    compute_type: str = "int8"
    language: str = "en"
    beam_size: int = 1
    vad_filter: bool = True

    @classmethod
    def from_env(cls) -> "SttSettings":
        return cls(
            model=_str("FRIDAY_WHISPER_MODEL", "base.en"),
            device=_str("FRIDAY_WHISPER_DEVICE", "cpu"),
            compute_type=_str("FRIDAY_WHISPER_COMPUTE_TYPE", "int8"),
            language=_str("FRIDAY_WHISPER_LANGUAGE", "en"),
            beam_size=_int("FRIDAY_WHISPER_BEAM_SIZE", 1),
            vad_filter=_bool("FRIDAY_WHISPER_VAD_FILTER", True),
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

    @classmethod
    def from_env(cls) -> "TtsSettings":
        return cls(
            engine=_str("FRIDAY_TTS_ENGINE", "auto").lower(),
            piper_model=_str("FRIDAY_PIPER_MODEL", "voices/en_US-amy-medium.onnx"),
            piper_sample_rate=_int("FRIDAY_PIPER_SAMPLE_RATE", 22_050),
            rate=_int("FRIDAY_TTS_RATE", 185),
            voice=os.getenv("FRIDAY_TTS_VOICE") or None,
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
        if memories:
            prompt += "\nThings you already know about the owner:\n" + memories
        return prompt

    @classmethod
    def from_env(cls) -> "Settings":
        data_dir = Path(
            _str("FRIDAY_DATA_DIR", str(Path.home() / ".friday"))
        ).expanduser()
        return cls(
            name=_str("FRIDAY_NAME", "Friday"),
            owner=_str("FRIDAY_OWNER", "Srihari"),
            data_dir=data_dir,
            log_level=_str("FRIDAY_LOG_LEVEL", "INFO").upper(),
            allow_shell=_bool("FRIDAY_ALLOW_SHELL", False),
            audio=AudioSettings.from_env(),
            stt=SttSettings.from_env(),
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
