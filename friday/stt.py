"""Local speech-to-text using faster-whisper (CTranslate2).

The model is loaded once and reused. On CPU, ``base.en`` with ``int8`` is the
sweet spot; on an NVIDIA GPU use ``device=cuda`` and ``compute_type=float16``.
"""

from __future__ import annotations

import logging
import time

from .config import SttSettings

log = logging.getLogger("friday.stt")


class SttUnavailableError(RuntimeError):
    """Raised when faster-whisper cannot be loaded."""


class Transcriber:
    """Thin wrapper around ``faster_whisper.WhisperModel``."""

    def __init__(self, settings: SttSettings) -> None:
        self.settings = settings
        self._model = None

    def load(self) -> "Transcriber":
        try:
            from faster_whisper import WhisperModel
        except ImportError as exc:  # pragma: no cover - env dependent
            raise SttUnavailableError(
                "faster-whisper missing. Install with: pip install faster-whisper"
            ) from exc

        started = time.monotonic()
        self._model = WhisperModel(
            self.settings.model,
            device=self.settings.device,
            compute_type=self.settings.compute_type,
        )
        log.info(
            "Whisper '%s' ready on %s/%s in %.1fs",
            self.settings.model,
            self.settings.device,
            self.settings.compute_type,
            time.monotonic() - started,
        )
        return self

    def transcribe(self, audio, language: str | None = None) -> str:
        """Transcribe float32 mono audio at 16 kHz. Returns "" on silence."""
        text, _detected = self.transcribe_detect(audio, language=language)
        return text

    def transcribe_detect(
        self, audio, language: str | None = None
    ) -> tuple[str, str | None]:
        """Transcribe and report which language was heard.

        When ``auto_detect`` is on and no language is forced, Whisper decides
        the language itself from the first seconds of audio - that is what lets
        the owner switch from English to Malayalam mid-conversation without
        touching a setting. The detected code is returned so the voice can
        follow along.
        """
        if self._model is None:
            raise SttUnavailableError("Transcriber.load() was never called")
        if audio is None or len(audio) == 0:
            return "", None

        forced = language or (
            None if self.settings.auto_detect else self.settings.language
        )

        started = time.monotonic()
        segments, info = self._model.transcribe(
            audio,
            language=forced,
            beam_size=self.settings.beam_size,
            vad_filter=self.settings.vad_filter,
            condition_on_previous_text=False,
        )
        text = " ".join(segment.text.strip() for segment in segments).strip()

        detected = forced or getattr(info, "language", None)
        probability = getattr(info, "language_probability", None)

        # A confident guess on a very short clip is often wrong; ignore weak ones
        # so a mumbled English "yes" is not heard as Japanese.
        if forced is None and probability is not None and probability < 0.5:
            log.debug("Ignoring weak language guess %s (%.2f)", detected, probability)
            detected = None

        log.debug(
            "Transcribed %.1fs of audio in %.2fs [%s]: %r",
            len(audio) / 16_000,
            time.monotonic() - started,
            detected or "unknown",
            text,
        )
        return text, detected
