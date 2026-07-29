"""Language support for FRIDAY.

One registry drives everything language-related: which Whisper code to use,
which Piper voice to prefer, and what FRIDAY says when she wakes up. Adding a
language means adding one entry here - no other module needs to change.

Whisper understands all of these. Quality is not uniform: European languages
are excellent, Chinese, Japanese and Korean are good, and Malayalam, Hindi and
Tamil improve markedly with a larger model (``small`` or ``medium``).
"""

from __future__ import annotations

from dataclasses import dataclass

__all__ = [
    "Language",
    "LanguageState",
    "LANGUAGES",
    "DEFAULT_LANGUAGE",
    "resolve",
    "describe_languages",
    "multilingual_model",
    "language_instruction",
]


@dataclass(frozen=True)
class Language:
    """Everything FRIDAY needs to know to work in one language.

    ``code`` is the ISO-639-1 code Whisper and Gemini both understand.
    ``piper_voice`` is a voice name from the Piper voice collection, or "" when
    no Piper voice exists yet - those languages fall back to the system voice.
    """

    code: str
    english_name: str
    native_name: str
    aliases: tuple[str, ...] = ()
    piper_voice: str = ""
    greeting: str = "{name} online."
    acknowledge: str = "Yes?"
    fresh_start: str = "Fresh start."

    @property
    def label(self) -> str:
        return f"{self.english_name} ({self.native_name})"


LANGUAGES: dict[str, Language] = {
    "en": Language(
        code="en",
        english_name="English",
        native_name="English",
        aliases=("english",),
        piper_voice="en_US-amy-medium",
        greeting="{name} online.",
        acknowledge="Yes?",
        fresh_start="Fresh start.",
    ),
    "ml": Language(
        code="ml",
        english_name="Malayalam",
        native_name="മലയാളം",
        aliases=("malayalam", "mallu", "kerala"),
        greeting="{name} തയ്യാറാണ്.",
        acknowledge="എന്താണ്?",
        fresh_start="പുതിയ തുടക്കം.",
    ),
    "hi": Language(
        code="hi",
        english_name="Hindi",
        native_name="हिन्दी",
        aliases=("hindi", "hindustani"),
        greeting="{name} ऑनलाइन है।",
        acknowledge="जी?",
        fresh_start="नई शुरुआत।",
    ),
    "ta": Language(
        code="ta",
        english_name="Tamil",
        native_name="தமிழ்",
        aliases=("tamil",),
        greeting="{name} தயாராக உள்ளது.",
        acknowledge="சொல்லுங்க?",
        fresh_start="புதிய துடக்கம்.",
    ),
    "es": Language(
        code="es",
        english_name="Spanish",
        native_name="Español",
        aliases=("spanish", "espanol", "castellano"),
        piper_voice="es_ES-davefx-medium",
        greeting="{name} en línea.",
        acknowledge="¿Sí?",
        fresh_start="Empezamos de nuevo.",
    ),
    "it": Language(
        code="it",
        english_name="Italian",
        native_name="Italiano",
        aliases=("italian", "italiano"),
        piper_voice="it_IT-riccardo-x_low",
        greeting="{name} è online.",
        acknowledge="Sì?",
        fresh_start="Ricominciamo.",
    ),
    "fr": Language(
        code="fr",
        english_name="French",
        native_name="Français",
        aliases=("french", "francais"),
        piper_voice="fr_FR-siwis-medium",
        greeting="{name} est en ligne.",
        acknowledge="Oui ?",
        fresh_start="On repart de zéro.",
    ),
    "de": Language(
        code="de",
        english_name="German",
        native_name="Deutsch",
        aliases=("german", "deutsch"),
        piper_voice="de_DE-thorsten-medium",
        greeting="{name} ist online.",
        acknowledge="Ja?",
        fresh_start="Neuer Anfang.",
    ),
    "zh": Language(
        code="zh",
        english_name="Chinese",
        native_name="中文",
        aliases=("chinese", "mandarin", "putonghua"),
        piper_voice="zh_CN-huayan-medium",
        greeting="{name} 已上线。",
        acknowledge="在？",
        fresh_start="重新开始。",
    ),
    "ko": Language(
        code="ko",
        english_name="Korean",
        native_name="한국어",
        aliases=("korean", "hangul"),
        greeting="{name} 준비됐습니다.",
        acknowledge="네?",
        fresh_start="새로 시작합니다.",
    ),
    "ja": Language(
        code="ja",
        english_name="Japanese",
        native_name="日本語",
        aliases=("japanese", "nihongo"),
        greeting="{name} 起動しました。",
        acknowledge="はい？",
        fresh_start="最初からです。",
    ),
}

DEFAULT_LANGUAGE = LANGUAGES["en"]

# Whisper model sizes that are multilingual. The ``.en`` variants are not.
_MULTILINGUAL_SIZES = (
    "tiny",
    "base",
    "small",
    "medium",
    "large",
    "large-v1",
    "large-v2",
    "large-v3",
    "turbo",
)


def resolve(name: str | None) -> Language | None:
    """Look up a language by code, English name, native name or alias.

    Accepts what a person would actually say or type: ``ml``, ``Malayalam``,
    ``മലയാളം``, ``mallu``, ``ZH-CN``. Returns None when nothing matches.
    """
    if not name:
        return None

    needle = name.strip().lower().replace("_", "-")
    if not needle:
        return None

    # "zh-cn", "en-us", "pt-br" -> take the primary subtag
    primary = needle.split("-")[0]

    for language in LANGUAGES.values():
        if needle in {language.code, language.english_name.lower()}:
            return language
        if primary == language.code:
            return language
        if needle == language.native_name.lower():
            return language
        if needle in language.aliases:
            return language
    return None


def enabled_languages(codes: list[str]) -> list[Language]:
    """Resolve a list of user-supplied names, preserving order, English first."""
    found: list[Language] = []
    for code in codes:
        language = resolve(code)
        if language is not None and language not in found:
            found.append(language)
    return found or [DEFAULT_LANGUAGE]


def describe_languages(languages: list[Language]) -> str:
    """Human-readable list, for logs and the ``list_languages`` tool."""
    return ", ".join(language.label for language in languages)


def multilingual_model(model: str) -> str:
    """Return a Whisper model name that is not English-only.

    ``base.en`` becomes ``base``. Anything already multilingual is returned
    unchanged, so an explicit ``FRIDAY_WHISPER_MODEL=medium`` is respected.
    """
    if model.endswith(".en"):
        stripped = model[:-3]
        if stripped in _MULTILINGUAL_SIZES:
            return stripped
    return model


def language_instruction(default: Language, allowed: list[Language]) -> str:
    """The paragraph appended to the system prompt to make FRIDAY multilingual."""
    if len(allowed) <= 1 and default.code == "en":
        return ""

    names = ", ".join(language.english_name for language in allowed)
    return (
        "\nLanguage rules:\n"
        f"- You understand and speak: {names}.\n"
        "- Always reply in the same language the owner just used, even if it "
        "changes mid-conversation. Match their script, not a transliteration.\n"
        "- If the owner mixes two languages in one sentence, reply in the one "
        "they used for the main verb.\n"
        f"- When the language is genuinely unclear, use {default.english_name}.\n"
        "- Numbers, dates and units belong in the language you are speaking.\n"
        "- Never announce which language you are using. Just use it.\n"
    )


class LanguageState:
    """The language currently in use, shared between the ears, voice and tools.

    Mutable on purpose: the transcriber can detect a switch and the owner can
    force one with the ``speak_in_language`` tool, and both need the voice to
    follow immediately.
    """

    def __init__(
        self, default: Language | None = None, allowed: list[Language] | None = None
    ) -> None:
        self.default = default or DEFAULT_LANGUAGE
        self.allowed = allowed or [self.default]
        self.current = self.default
        self.locked = False

    def set(self, name: str, lock: bool = False) -> Language | None:
        """Switch language by name or code. Returns the Language, or None."""
        language = resolve(name)
        if language is None or language not in self.allowed:
            return None
        self.current = language
        self.locked = lock
        return language

    def observe(self, code: str | None) -> Language:
        """Follow a language detected from speech, unless the owner locked one."""
        if self.locked:
            return self.current
        language = resolve(code)
        if language is not None and language in self.allowed:
            self.current = language
        return self.current

    def reset(self) -> None:
        self.current = self.default
        self.locked = False
