"""Command line entry point: ``python -m friday``."""

from __future__ import annotations

import argparse
import logging
import os
import sys

from . import __version__
from .app import Friday
from .config import load_settings
from .i18n import LANGUAGES, resolve
from .logging_setup import configure_logging

log = logging.getLogger("friday.cli")


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        prog="friday",
        description="A local-first voice assistant with a cloud brain.",
    )
    parser.add_argument(
        "--mode",
        choices=("wake", "ptt", "text"),
        default="ptt",
        help="wake: always-on wake word. ptt: press Enter to talk. "
        "text: typed input, no audio. Default: ptt",
    )
    parser.add_argument(
        "--lang",
        metavar="CODE",
        help="Force a language for this run, e.g. ml, hi, ta, es, ja. "
        "Without it, the language is detected from your speech.",
    )
    parser.add_argument(
        "--languages",
        action="store_true",
        help="List the supported languages and exit.",
    )
    parser.add_argument(
        "--say",
        metavar="TEXT",
        help="Answer a single prompt and exit. Implies --mode text.",
    )
    parser.add_argument(
        "--verbose", "-v", action="store_true", help="Log at DEBUG level."
    )
    parser.add_argument("--version", action="version", version=f"friday {__version__}")
    return parser


def main(argv: list[str] | None = None) -> int:
    args = build_parser().parse_args(argv)

    if args.languages:
        for language in LANGUAGES.values():
            print(f"  {language.code}  {language.label}")
        return 0

    # --lang is just a friendlier way to set the environment variable, so the
    # rest of the application keeps reading configuration from exactly one place.
    if args.lang:
        chosen = resolve(args.lang)
        if chosen is None:
            print(f"Unknown language: {args.lang}. Try --languages.")
            return 2
        os.environ["FRIDAY_LANGUAGE"] = chosen.code
        os.environ["FRIDAY_AUTO_DETECT_LANGUAGE"] = "false"

    settings = load_settings()
    configure_logging(
        "DEBUG" if args.verbose else settings.log_level, settings.log_path
    )

    needs_audio = args.mode != "text" and not args.say

    try:
        with Friday(settings) as friday:
            friday.start(audio=needs_audio)

            if args.say:
                friday.respond(args.say)
                return 0
            if args.mode == "text":
                friday.run_text()
            elif args.mode == "ptt":
                friday.run_push_to_talk()
            else:
                friday.run_wake_word()
    except KeyboardInterrupt:
        print()
        return 130
    except Exception as exc:
        log.error("%s: %s", type(exc).__name__, exc)
        log.debug("Traceback", exc_info=True)
        return 1
    return 0


if __name__ == "__main__":  # pragma: no cover
    sys.exit(main())
