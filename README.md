# FRIDAY

**A local-first voice assistant with a cloud brain.**

Capture, wake word, transcription, speech synthesis, memory and tool execution all run on your machine. The only outbound network call is the language model request. That is the whole design thesis: keep the latency-sensitive, privacy-sensitive parts local, and rent the intelligence.

```
  microphone ──▶ wake word ──▶ VAD endpointing ──▶ Whisper (local)
                                                       │
                                                       ▼
                                            Gemini + function calling
                                                       │
                     local tools ◀── automatic ────────┤
                                                       ▼
  speakers  ◀────── Piper / system TTS ◀────── streamed sentences
```

---

## Features

| | |
| --- | --- |
| **Offline ears** | `faster-whisper` transcription, `webrtcvad` endpointing, `openWakeWord` trigger |
| **Cloud brain** | Gemini 2.5 Flash with automatic function calling, thinking disabled for latency |
| **Streaming speech** | Replies are spoken sentence-by-sentence as they generate |
| **Never hears itself** | The microphone is muted for the duration of each spoken reply |
| **Persistent memory** | SQLite fact store injected into the system prompt on every boot |
| **Eleven languages** | English, Malayalam, Hindi, Tamil, Spanish, Italian, French, German, Chinese, Korean, Japanese - detected automatically |
| **Real tools** | Time, apps, URLs, web search, clipboard, machine status, notes, memory, language, shell |
| **Safe by default** | The shell tool is disarmed unless you explicitly enable it |
| **Three run modes** | `text` for development, `ptt` for smoke tests, `wake` for always-on |
| **Installable on Windows** | PyInstaller + Inno Setup pipeline produces `FridaySetup.exe` |

---

## Quick start

```bash
git clone https://github.com/sk-deb/friday-voice-assistant.git
cd friday-voice-assistant

python3 -m venv .venv && source .venv/bin/activate
pip install -r requirements.txt

cp .env.example .env          # then paste your Gemini API key
python scripts/doctor.py      # verifies every dependency and your key

python -m friday --mode text  # no microphone needed
python -m friday --mode ptt   # press Enter, then speak
python -m friday --mode wake  # always-on
```

Get a free API key at <https://aistudio.google.com/apikey>.

Full install notes, including per-platform audio setup and Piper voices, are in [docs/SETUP.md](docs/SETUP.md).

---

## Usage

```bash
python -m friday --mode text            # typed conversation
python -m friday --mode ptt             # push to talk
python -m friday --mode wake            # wake word, always listening
python -m friday --say "what time is it"  # single shot, then exit
python -m friday --mode ptt --verbose   # DEBUG logging
python -m friday --languages            # list supported languages
python -m friday --lang ml --mode ptt   # pin Malayalam, skip detection
```

Spoken control phrases: **"stop"** or **"never mind"** aborts a turn, **"new conversation"** clears context, **"speak to me in Tamil"** locks a language.

---

## Languages

Speak any of eleven languages and FRIDAY answers in the same one, without being told to switch:

| | |
| --- | --- |
| **Excellent** | English, Spanish, French, German, Italian, Chinese, Japanese |
| **Good** | Korean, Hindi |
| **Usable, expect mistakes** | Malayalam, Tamil |

Multilingual mode automatically upgrades Whisper from `base.en` to `small`, which is a larger download and roughly a second slower per turn. Malayalam, Tamil, Korean and Japanese have no Piper voice yet and are spoken with the system voice. Both trade-offs, and how to tune them, are documented in [docs/LANGUAGES.md](docs/LANGUAGES.md).

To restore the original English-only speed: `FRIDAY_LANGUAGES=en`.

---

## Install as a Windows app

```powershell
powershell -ExecutionPolicy Bypass -File packaging\build_windows.ps1
```

Produces `dist\Friday\friday.exe` and `dist\installer\FridaySetup.exe`, with Start Menu shortcuts for each mode and settings in `%APPDATA%\Friday`.

No Windows machine handy? The **Windows build** GitHub Actions workflow builds the installer on a Windows runner and uploads it as an artifact. Full instructions: [docs/WINDOWS.md](docs/WINDOWS.md).

---

## Repository layout

```
friday/
├── friday/
│   ├── __main__.py        CLI entry point
│   ├── app.py             orchestration and the three run modes
│   ├── config.py          all settings, env-driven, immutable
│   ├── i18n.py            language registry, detection state, prompts
│   ├── llm.py             Gemini chat, streaming, function calling
│   ├── stt.py             faster-whisper wrapper with language detection
│   ├── tts.py             Piper / pyttsx3 / null backends, per-language voices
│   ├── memory.py          SQLite facts and turn log
│   ├── logging_setup.py   console plus rotating file logs
│   ├── audio/
│   │   ├── ears.py        capture, VAD endpointing, mute-while-speaking
│   │   └── wake.py        openWakeWord detector with cooldown
│   └── tools/
│       ├── system.py      time, apps, URLs, clipboard, status, shell
│       ├── knowledge.py   memory and note tools
│       └── language.py    switch, follow and list languages
├── packaging/             PyInstaller spec, launcher, build script, installer
├── docs/                  architecture, setup, configuration, languages, Windows
├── scripts/doctor.py      pre-flight environment check
└── tests/                 standard-library unit tests
```

---

## Documentation

| Document | What it covers |
| --- | --- |
| [docs/ARCHITECTURE.md](docs/ARCHITECTURE.md) | Component design, data flow, latency budget, design decisions |
| [docs/SETUP.md](docs/SETUP.md) | Install, platform audio notes, Piper voices, custom "Friday" wake word |
| [docs/CONFIGURATION.md](docs/CONFIGURATION.md) | Every environment variable and sensible tuning ranges |
| [docs/LANGUAGES.md](docs/LANGUAGES.md) | The eleven languages, per-language quality, voices, detection tuning |
| [docs/WINDOWS.md](docs/WINDOWS.md) | Building the exe, installing the app, where data lives |
| [docs/TOOLS.md](docs/TOOLS.md) | The tool contract and how to add your own |
| [docs/BRANCHING.md](docs/BRANCHING.md) | Branch-per-update workflow used in this repository |
| [docs/TROUBLESHOOTING.md](docs/TROUBLESHOOTING.md) | Symptom-to-fix table |
| [docs/PRIOR_ART.md](docs/PRIOR_ART.md) | Projects surveyed before building, and what was borrowed |

---

## Security notes

- Secrets live in `.env`, which is git-ignored. Never commit a key.
- `run_shell_command` executes arbitrary commands and is **disabled by default**. Set `FRIDAY_ALLOW_SHELL=true` only on a machine you own.
- Transcripts, remembered facts and notes are stored unencrypted under `~/.friday`. Delete that directory to wipe FRIDAY's memory.
- Prompt text and transcribed speech are sent to Google's API. Audio never leaves the machine.

---

## Development

```bash
pip install -r requirements-dev.txt
python -m unittest discover -s tests -t .    # 53 tests, no hardware needed
ruff check . && ruff format --check .
```

Contribution and branch conventions: [CONTRIBUTING.md](CONTRIBUTING.md).

## License

MIT. See [LICENSE](LICENSE).
