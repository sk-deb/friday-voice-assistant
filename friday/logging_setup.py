"""Logging configuration: readable console output plus a rotating file log."""

from __future__ import annotations

import logging
from logging.handlers import RotatingFileHandler
from pathlib import Path

_CONSOLE_FORMAT = "%(asctime)s  %(levelname)-7s %(name)-18s %(message)s"
_FILE_FORMAT = "%(asctime)s  %(levelname)-7s %(name)s  %(message)s"


def configure_logging(level: str = "INFO", log_file: Path | None = None) -> None:
    """Idempotently configure the root logger."""
    root = logging.getLogger()
    if getattr(root, "_friday_configured", False):
        root.setLevel(level)
        return

    root.setLevel(level)

    console = logging.StreamHandler()
    console.setFormatter(logging.Formatter(_CONSOLE_FORMAT, "%H:%M:%S"))
    root.addHandler(console)

    if log_file is not None:
        log_file.parent.mkdir(parents=True, exist_ok=True)
        file_handler = RotatingFileHandler(
            log_file, maxBytes=2_000_000, backupCount=3, encoding="utf-8"
        )
        file_handler.setFormatter(logging.Formatter(_FILE_FORMAT))
        root.addHandler(file_handler)

    # Third-party chatter we never want at INFO.
    for noisy in ("faster_whisper", "urllib3", "httpx", "google_genai"):
        logging.getLogger(noisy).setLevel(logging.WARNING)

    root._friday_configured = True  # type: ignore[attr-defined]
