"""Language tools: let the owner steer which language FRIDAY speaks.

Detection usually handles this on its own - speak Tamil and FRIDAY answers in
Tamil. These tools exist for the cases detection cannot cover: pinning one
language for a whole session, or asking what is available.
"""

from __future__ import annotations

from collections.abc import Callable

from ..i18n import LanguageState, describe_languages

__all__ = ["make_language_tools"]


def make_language_tools(state: LanguageState) -> list[Callable[..., str]]:
    """Build tools bound to the shared language state."""

    def speak_in_language(language: str) -> str:
        """Switch to speaking a specific language and stay in it.

        Use this when the owner explicitly asks for a language, for example
        'speak Malayalam', 'answer in French from now on', or 'switch to
        Japanese'. Accepts a code or a name: 'ml', 'Malayalam', 'French'.
        """
        chosen = state.set(language, lock=True)
        if chosen is None:
            return (
                f"I do not have {language}. "
                f"I can use: {describe_languages(state.allowed)}"
            )
        return f"Now speaking {chosen.english_name}."

    def follow_my_language() -> str:
        """Stop forcing one language and follow whatever the owner speaks.

        Use this when the owner says something like 'go back to detecting',
        'just follow me', or 'stop forcing English'.
        """
        state.locked = False
        return "I will follow whichever language you use."

    def list_languages() -> str:
        """List the languages this assistant can understand and speak."""
        return (
            f"Currently {state.current.english_name}. "
            f"Available: {describe_languages(state.allowed)}"
        )

    return [speak_in_language, follow_my_language, list_languages]
