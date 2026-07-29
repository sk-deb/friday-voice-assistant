# Languages

FRIDAY speaks eleven languages and switches between them on her own. Say
something in Malayalam and the reply comes back in Malayalam; switch to English
mid-sentence and she follows.

## Supported languages

| Code | Language | Native name | Voice quality out of the box |
|------|----------|-------------|------------------------------|
| `en` | English | English | Excellent (Piper neural voice) |
| `ml` | Malayalam | മലയാളം | System voice only |
| `hi` | Hindi | हिन्दी | System voice only |
| `ta` | Tamil | தமிழ் | System voice only |
| `es` | Spanish | Español | Good (Piper voice available) |
| `it` | Italian | Italiano | Good (Piper voice available) |
| `fr` | French | Français | Good (Piper voice available) |
| `de` | German | Deutsch | Good (Piper voice available) |
| `zh` | Chinese (Mandarin) | 中文 | Good (Piper voice available) |
| `ko` | Korean | 한국어 | System voice only |
| `ja` | Japanese | 日本語 | System voice only |

List them at any time:

```bash
python -m friday --languages
```

## Be honest about what is good and what is rough

The three parts of the pipeline are not equally strong in every language.

**Understanding you (Whisper).** Strong in Spanish, French, German, Italian,
Chinese, Japanese and Korean. Noticeably weaker in Malayalam and Tamil, and
middling in Hindi — these three have far less training data, so expect to repeat
yourself sometimes and to see occasional wrong words. Using a bigger model helps
a lot here (see below).

**Thinking (Gemini).** Genuinely strong in all eleven. This is the part you will
complain about least.

**Speaking back.** This is the weak link. Piper, the good-sounding offline voice,
has no reliable Malayalam, Tamil, Korean or Japanese voice, so those fall back to
the Windows system voice. Windows can read Hindi, Japanese, Korean and Chinese
well if you install the language pack; Malayalam and Tamil have no Microsoft
voice at all and will be read by an English voice, which sounds wrong. The text
on screen is still correct.

If Malayalam or Tamil speech output matters to you, tell me and we can add a
cloud TTS backend — that is the only way to get good quality today, and it means
those sentences leave your machine.

## Choosing the speech model

English-only models cannot transcribe anything else, so FRIDAY upgrades the
model automatically the moment more than one language is enabled:

| Setting | Model used | Download | Speed on CPU |
|---------|-----------|----------|--------------|
| English only | `base.en` | ~75 MB | fastest |
| Multilingual (default) | `small` | ~500 MB | ~2× slower |
| Recommended for Malayalam / Tamil / Hindi | `medium` | ~1.5 GB | ~4× slower |

```bash
# Better accuracy for Indian languages, at the cost of latency
FRIDAY_WHISPER_MODEL=medium
```

This is the main trade-off in the whole feature: multilingual means a bigger
download and roughly a second more delay per turn than the English-only setup you
had before.

## Making detection more reliable

Detection improves sharply when FRIDAY is not guessing between all eleven
languages. Enable only what you actually speak:

```bash
FRIDAY_LANGUAGES=en,ml,hi
FRIDAY_LANGUAGE=en
```

Or pin one language for a whole session and skip detection entirely:

```bash
python -m friday --lang ml
```

To go back to the original fast English-only behaviour:

```bash
FRIDAY_LANGUAGES=en
```

## Asking her to switch, out loud

Three tools are available to the model, so plain speech works:

- *"Speak to me in Tamil from now on"* → locks Tamil until told otherwise
- *"Just follow whatever language I use"* → back to automatic detection
- *"Which languages do you speak?"* → lists them

## Better voices

Download Piper voices from the `rhasspy/piper-voices` repository on Hugging
Face. Each voice is two files, `<voice>.onnx` and `<voice>.onnx.json`, and both
go in your `voices/` folder.

The voices FRIDAY looks for by default:

| Code | Piper voice |
|------|-------------|
| `en` | `en_US-amy-medium` |
| `es` | `es_ES-davefx-medium` |
| `it` | `it_IT-riccardo-x_low` |
| `fr` | `fr_FR-siwis-medium` |
| `de` | `de_DE-thorsten-medium` |
| `zh` | `zh_CN-huayan-medium` |

Anything missing falls back to the default voice with a note in the log — never
a crash. Point at a specific file per language if you prefer:

```bash
FRIDAY_PIPER_VOICE_HI=voices/hi_IN-custom-medium.onnx
FRIDAY_TTS_VOICE_JA=HKEY_LOCAL_MACHINE\...\Tokens\MSTTS_V110_jaJP_Haruka
```

### Installing Windows system voices

For Hindi, Japanese, Korean and Chinese, install the Microsoft voice:

1. Settings → Time & language → Language & region → **Add a language**
2. Pick the language, and tick **Speech** among the optional features
3. Restart FRIDAY — the matching voice is picked up automatically

## How it works

1. Whisper transcribes the audio and reports which language it heard, along with
   a confidence score. Guesses below 0.5 are discarded, so a mumbled English
   "yes" is not mistaken for Japanese.
2. If that language is enabled, it becomes the current language for the turn.
3. The system prompt tells Gemini to reply in the owner's language, in the proper
   script rather than transliteration, and never to announce the switch.
4. The speaker picks the best available voice for that language.

A language locked with `speak_in_language` ignores step 2 until unlocked.

Relevant code: `friday/i18n.py` (registry and state), `friday/stt.py`
(detection), `friday/tts.py` (voice selection), `friday/tools/language.py`
(spoken commands).
