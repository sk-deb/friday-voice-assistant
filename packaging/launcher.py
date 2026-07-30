"""Entry point for the packaged Windows build.

Running from source and running from a frozen ``friday.exe`` differ in four
ways, and this file is the only place that knows about them:

1. **Where data lives.** From source, ``~/.friday`` is fine. Installed under
   ``C:\\Program Files``, the install directory is read-only, so the database,
   notes and log must go to ``%APPDATA%\\Friday``.
2. **Where configuration comes from.** A ``.env`` sitting next to the exe (or in
   the data directory) is loaded before settings are read, so the owner can drop
   their Gemini key in without touching environment variables.
3. **The window closing instantly.** A double-clicked exe that crashes vanishes
   with the error. Here the window is held open so the message can be read -
   but only when someone is actually there to read it.
4. **Questions that need no key.** ``--version``, ``--languages`` and ``--help``
   answer from local data, so they must work before a key is configured.
"""

from __future__ import annotations

import os
import sys
from pathlib import Path

# Flags that only report local information. Gating these behind the API-key
# check made the exe unable to answer "which version are you?", which is exactly
# what a smoke test - and a confused owner - asks first.
KEYLESS_FLAGS = frozenset({"--version", "-V", "--languages", "--help", "-h"})


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


def _wants_pause() -> bool:
    """True only when a human is watching a window that is about to vanish.

    A double-clicked exe needs the pause. A build runner, a piped invocation or
    a redirected console has no stdin to read, and calling ``input()`` there
    raises ``EOFError`` - turning a clean exit code into a crash.
    """
    if not _is_frozen():
        return False
    if os.getenv("FRIDAY_NO_PAUSE") or os.getenv("CI"):
        return False
    try:
        return bool(sys.stdin and sys.stdin.isatty())
    except Exception:  # pragma: no cover - detached stdin
        return False


def _pause() -> None:
    if not _wants_pause():
        return
    try:
        input("Press Enter to close... ")
    except (EOFError, KeyboardInterrupt):  # pragma: no cover - no console
        pass


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


def _needs_key(argv: list[str]) -> bool:
    """False when every argument is an informational flag."""
    return not any(arg in KEYLESS_FLAGS for arg in argv)


def main(argv: list[str] | None = None) -> int:
    argv = list(sys.argv[1:] if argv is None else argv)
    data_dir = _prepare_environment()

    if _needs_key(argv) and not os.getenv("GEMINI_API_KEY"):
        _missing_key_notice(data_dir)
        _pause()
        return 2

    from friday.__main__ import main as friday_main

    try:
        return friday_main()
    except SystemExit as exc:  # argparse exits this way for --version/--help
        return int(exc.code or 0)
    except KeyboardInterrupt:
        print()
        return 130
    except Exception as exc:  # pragma: no cover - top level safety net
        print()
        print(f"FRIDAY stopped with an error: {exc}")
        print(f"Full details were written to {data_dir / 'friday.log'}")
        _pause()
        return 1


if __name__ == "__main__":
    sys.exit(main())
