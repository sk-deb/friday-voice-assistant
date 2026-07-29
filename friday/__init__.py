"""FRIDAY - a local-first voice assistant with a cloud brain.

The capture, transcription, speech and tool layers run entirely on this
machine. The only outbound call is the language model request.
"""

from __future__ import annotations

__version__ = "1.0.0"
__all__ = ["__version__", "load_settings", "Settings"]

from .config import Settings, load_settings
