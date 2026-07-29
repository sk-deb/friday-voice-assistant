"""The brain: Gemini with automatic function calling.

The google-genai SDK accepts plain Python callables as tools. It inspects type
hints and docstrings to build the schema, executes the call locally, then feeds
the result back to the model - so the tool bodies in ``friday/tools`` never need
any schema boilerplate.
"""

from __future__ import annotations

import logging
from typing import Callable, Iterator, Sequence

from .config import Settings

log = logging.getLogger("friday.llm")


class BrainUnavailableError(RuntimeError):
    """Raised when the model client cannot be constructed."""


class Brain:
    """A single stateful Gemini conversation."""

    def __init__(
        self,
        settings: Settings,
        tools: Sequence[Callable[..., object]] = (),
        memories: str = "",
    ) -> None:
        self.settings = settings
        self.tools = list(tools)
        self.memories = memories
        self._client = None
        self._config = None
        self._chat = None

    # ------------------------------------------------------------- lifecycle
    def load(self) -> "Brain":
        if not self.settings.llm.api_key:
            raise BrainUnavailableError(
                "GEMINI_API_KEY is not set. Copy .env.example to .env and add "
                "your key from https://aistudio.google.com/apikey"
            )
        try:
            from google import genai
            from google.genai import types
        except ImportError as exc:  # pragma: no cover - env dependent
            raise BrainUnavailableError(
                "google-genai missing. Install with: pip install google-genai"
            ) from exc

        llm = self.settings.llm
        self._client = genai.Client(api_key=llm.api_key)
        self._config = types.GenerateContentConfig(
            system_instruction=self.settings.system_prompt(self.memories),
            tools=self.tools or None,
            temperature=llm.temperature,
            max_output_tokens=llm.max_output_tokens,
            thinking_config=types.ThinkingConfig(
                thinking_budget=llm.thinking_budget
            ),
        )
        self._chat = self._client.chats.create(model=llm.model, config=self._config)
        log.info("Brain ready: %s with %d tools", llm.model, len(self.tools))
        return self

    def reset(self) -> None:
        """Start a fresh conversation, keeping tools and system prompt."""
        if self._client is None:
            return
        self._chat = self._client.chats.create(
            model=self.settings.llm.model, config=self._config
        )
        log.info("Conversation reset")

    # ------------------------------------------------------------------- api
    def ask(self, text: str) -> str:
        """Send a turn and return the complete reply."""
        if self._chat is None:
            raise BrainUnavailableError("Brain.load() was never called")
        try:
            response = self._chat.send_message(text)
        except Exception as exc:
            log.exception("Model call failed")
            return f"My connection to the model failed. {type(exc).__name__}."
        return (getattr(response, "text", "") or "").strip()

    def stream(self, text: str) -> Iterator[str]:
        """Yield sentence-sized chunks as they arrive.

        Falls back to a single blocking call if streaming is unsupported or
        fails mid-flight.
        """
        if self._chat is None:
            raise BrainUnavailableError("Brain.load() was never called")
        if not self.settings.llm.stream:
            reply = self.ask(text)
            if reply:
                yield reply
            return

        buffer = ""
        produced = False
        try:
            for chunk in self._chat.send_message_stream(text):
                piece = getattr(chunk, "text", "") or ""
                if not piece:
                    continue
                buffer += piece
                while True:
                    cut = _first_sentence_break(buffer)
                    if cut is None:
                        break
                    sentence, buffer = buffer[:cut].strip(), buffer[cut:].lstrip()
                    if sentence:
                        produced = True
                        yield sentence
            if buffer.strip():
                produced = True
                yield buffer.strip()
        except Exception as exc:
            log.warning("Streaming failed (%s); retrying without streaming", exc)
            if not produced:
                reply = self.ask(text)
                if reply:
                    yield reply


def _first_sentence_break(text: str) -> int | None:
    """Index just past the first sentence terminator followed by a space."""
    for index, char in enumerate(text):
        if char in ".!?" and index + 1 < len(text) and text[index + 1] in " \n":
            return index + 1
    return None
