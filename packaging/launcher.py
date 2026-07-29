"""Entry point for the packaged Windows build.

Running from source and running from a frozen ``friday.exe`` differ in three
ways, and this file is the only place that knows about them:

1. **Where data lives.** From source, ``~/.friday`` is fine. Installed under
   ``C:\\Program Files``, the install directory is read-only, so the database,
   notes and log must go to ``%APPDATA%\\Friday``.
2. **Where configuration comes from.** A ``.env`` sitting next to the exe (or in
   the data directory) is loaded before settings are read, so the owner can drop
   their Gemini key in without touching environment variables.
3. **The window closing instantly.** A double-clicked exe that crashes vanishes
   with the error. Here the window is held open so the message can be read.
"""

from __future__ import annotations

import os
import sys
from pathlib import Path


def _is_frozen() -> bool:
    return getattr(sys, "frozen", False)


def _install_dir() -> Path:
    """Directory holding the exe when frozen, else the repository root."""
    if _is_frozen():
        return Path(sys.executable).resolve().parent
    return Path(__file__).resolve().parent.parent


def _data_dir() -> Path:
    """Per-user, always-writable location for the database, notes and log."""
    appdata = os.getenv("APPDATA")
    if appdata:
        return Path(appdata) / "Friday"
    return Path.home() / ".friday"


def _prepare_environment() -> Path:
    data_dir = Path(os.getenv("FRIDAY_DATA_DIR") or _data_dir()).expanduser()
    data_dir.mkdir(parents=True, exist_ok=True)
    os.environ.setdefault("FRIDAY_DATA_DIR", str(data_dir))

    install_dir = _install_dir()

    # Bundled model files ship beside the exe; point the voice at them unless
    # the owner has already chosen their own.
    voices = install_dir / "voices"
    if voices.is_dir():
        os.environ.setdefault("FRIDAY_VOICE_DIR", str(voices))

    # Whisper caches multi-hundred-megabyte weights. Keeping them in APPDATA
    # means an uninstall does not force a re-download on reinstall.
    os.environ.setdefault("HF_HOME", str(data_dir / "models"))

    for candidate in (data_dir / ".env", install_dir / ".env"):
        if candidate.is_file():
            try:
                from dotenv import load_dotenv

                load_dotenv(candidate, override=False)
            except Exception:  # pragma: no cover - dotenv is optional
                pass
            break

    return data_dir


def _missing_key_notice(data_dir: Path) -> None:
    print("=" * 68)
    print(" FRIDAY needs a Gemini API key before she can think.")
    print("=" * 68)
    print()
    print(" 1. Get a free key from Google AI Studio.")
    print(" 2. Create this file:")
    print(f"      {data_dir / '.env'}")
    print(" 3. Put one line in it:")
    print("      GEMINI_API_KEY=your_key_here")
    print()
    print(" Then start FRIDAY again.")
    print()


def main() -> int:
    data_dir = _prepare_environment()

    if not os.getenv("GEMINI_API_KEY"):
        _missing_key_notice(data_dir)
        if _is_frozen():
            input("Press Enter to close... ")
        return 2

    from friday.__main__ import main as friday_main

    try:
        return friday_main()
    except Exception as exc:  # pragma: no cover - top level safety net
        print()
        print(f"FRIDAY stopped with an error: {exc}")
        print(f"Full details were written to {data_dir / 'friday.log'}")
        if _is_frozen():
            input("Press Enter to close... ")
        return 1


if __name__ == "__main__":
    sys.exit(main())
