"""Offline wake-word detection built on openWakeWord.

openWakeWord ships pre-trained models such as ``hey_jarvis``. To answer to
"Friday" specifically, train a custom model and point ``FRIDAY_WAKE_MODELS`` at
the resulting ``.onnx`` path. See docs/SETUP.md.
"""

from __future__ import annotations

import logging
import time

from ..config import WakeSettings

log = logging.getLogger("friday.wake")


class WakeWordUnavailableError(RuntimeError):
    """Raised when openWakeWord cannot be loaded."""


class WakeWordDetector:
    """Stateful detector fed one audio frame at a time."""

    def __init__(self, settings: WakeSettings) -> None:
        self.settings = settings
        self._model = None
        self._np = None
        self._last_fired = 0.0

    def load(self) -> WakeWordDetector:
        try:
            import numpy as np
            import openwakeword
            from openwakeword.model import Model
        except ImportError as exc:  # pragma: no cover - env dependent
            raise WakeWordUnavailableError(
                "openWakeWord missing. Install with: pip install openwakeword"
            ) from exc

        self._np = np
        try:
            openwakeword.utils.download_models()
        except Exception as exc:  # pragma: no cover - offline is fine
            log.debug("Skipping wake-word model download: %s", exc)

        self._model = Model(wakeword_models=list(self.settings.models))
        log.info("Wake word armed: %s", ", ".join(self.settings.models))
        return self

    def feed(self, frame: bytes) -> bool:
        """Return True when a wake word fired on this frame."""
        if self._model is None or self._np is None:
            raise WakeWordUnavailableError("WakeWordDetector.load() was never called")

        now = time.monotonic()
        if now - self._last_fired < self.settings.cooldown_s:
            return False

        pcm = self._np.frombuffer(frame, dtype=self._np.int16)
        scores = self._model.predict(pcm)
        if not scores:
            return False

        best_name = max(scores, key=scores.get)
        best_score = scores[best_name]
        if best_score < self.settings.threshold:
            return False

        log.info("Wake word '%s' (%.2f)", best_name, best_score)
        self._last_fired = now
        self.reset()
        return True

    def reset(self) -> None:
        if self._model is not None:
            try:
                self._model.reset()
            except Exception:  # pragma: no cover - version dependent
                pass
