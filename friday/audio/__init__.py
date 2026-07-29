"""Audio input: microphone capture, voice activity detection, wake word."""

from __future__ import annotations

__all__ = ["Ears", "WakeWordDetector"]

from .ears import Ears
from .wake import WakeWordDetector
