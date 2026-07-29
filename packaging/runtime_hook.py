"""Runs inside the frozen exe before any FRIDAY code imports.

PyInstaller executes runtime hooks first, which makes this the right place to
repair the few assumptions that libraries make about living in a normal Python
installation.
"""

from __future__ import annotations

import os
import sys
from pathlib import Path


def _bundle_dir() -> Path:
    # _MEIPASS is where PyInstaller unpacks bundled data.
    return Path(getattr(sys, "_MEIPASS", Path(__file__).resolve().parent))


def _fix_stdio() -> None:
    """Make non-Latin output printable.

    The Windows console defaults to a legacy code page, so printing Malayalam,
    Tamil, Chinese or Japanese raises UnicodeEncodeError and takes the whole
    program down. Forcing UTF-8 with replacement is the difference between a
    readable transcript and a crash.
    """
    os.environ.setdefault("PYTHONIOENCODING", "utf-8")
    os.environ.setdefault("PYTHONUTF8", "1")
    for stream in (sys.stdout, sys.stderr):
        try:
            stream.reconfigure(encoding="utf-8", errors="replace")
        except Exception:
            pass


def _fix_openwakeword() -> None:
    """Tell openWakeWord where its bundled models ended up.

    The library resolves model paths relative to its own package directory,
    which is inside the bundle and not where it expects.
    """
    models = _bundle_dir() / "openwakeword" / "resources" / "models"
    if models.is_dir():
        os.environ.setdefault("OPENWAKEWORD_MODEL_DIR", str(models))


def _quiet_noisy_libraries() -> None:
    # ONNX Runtime and Hugging Face print startup banners and progress bars that
    # bury the actual conversation.
    os.environ.setdefault("ORT_LOGGING_LEVEL", "3")
    os.environ.setdefault("HF_HUB_DISABLE_TELEMETRY", "1")
    os.environ.setdefault("TOKENIZERS_PARALLELISM", "false")


_fix_stdio()
_fix_openwakeword()
_quiet_noisy_libraries()
