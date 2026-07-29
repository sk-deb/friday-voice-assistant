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
| **Real tools** | Time, apps, URLs, web search, clipboard, machine status, notes, memory, shell |
| **Safe by default** | The shell tool is disarmed unless you explicitly enable it |
| **Three run modes** | `text` for development, `ptt` for smoke tests, `wake` for always-on |

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
```

Spoken control phrases: **"stop"** or **"never mind"** aborts a turn, **"new conversation"** clears context.

---

## Repository layout

```
friday/
├── friday/
│   ├── __main__.py        CLI entry point
│   ├── app.py             orchestration and the three run modes
│   ├── config.py          all settings, env-driven, immutable
│   ├── llm.py             Gemini chat, streaming, function calling
│   ├── stt.py             faster-whisper wrapper
│   ├── tts.py             Piper / pyttsx3 / null backends
│   ├── memory.py          SQLite facts and turn log
│   ├── logging_setup.py   console plus rotating file logs
│   ├── audio/
│   │   ├── ears.py        capture, VAD endpointing, mute-while-speaking
│   │   └── wake.py        openWakeWord detector with cooldown
│   └── tools/
│       ├── system.py      time, apps, URLs, clipboard, status, shell
│       └── knowledge.py   memory and note tools
├── docs/                  architecture, setup, configuration, tools, branching
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
python -m unittest discover -s tests -t .    # 23 tests, no hardware needed
ruff check . && ruff format --check .
```

Contribution and branch conventions: [CONTRIBUTING.md](CONTRIBUTING.md).

## License

MIT. See [LICENSE](LICENSE).
