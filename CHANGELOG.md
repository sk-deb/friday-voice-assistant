# Changelog

All notable changes to FRIDAY are recorded here. The format follows
[Keep a Changelog](https://keepachangelog.com/en/1.1.0/) and versions follow
[Semantic Versioning](https://semver.org/spec/v2.0.0.html).

## [1.1.0] - 2026-07-29

Eleven languages, and an installable Windows application.

### Added

- **Ten new languages** - Malayalam, Hindi, Tamil, Spanish, Italian, French,
  German, Chinese, Korean and Japanese join English. `friday/i18n.py` holds the
  registry: native names, spoken aliases, localized greeting and acknowledgement
  strings, and the suggested Piper voice per language.
- **Automatic language following** - Whisper reports the language it heard and
  FRIDAY replies in it, in the correct script. Guesses under 50% confidence are
  discarded so a mumbled English word is not mistaken for another language.
- **Three language tools** - `speak_in_language` locks a language,
  `follow_my_language` returns to automatic detection, `list_languages` reports
  what is available. Sixteen tools in total.
- **Language configuration** - `FRIDAY_LANGUAGE`, `FRIDAY_LANGUAGES`,
  `FRIDAY_AUTO_DETECT_LANGUAGE`, `FRIDAY_VOICE_DIR`, and per-language voice
  overrides `FRIDAY_PIPER_VOICE_<CODE>` / `FRIDAY_TTS_VOICE_<CODE>`.
- **CLI flags** - `--lang CODE` pins a language for one run, `--languages` lists
  them.
- **Per-language voice selection** - Piper picks the matching voice when it is
  installed; pyttsx3 scans installed system voices for a language match. Both
  fall back to the default voice with a log note instead of failing.
- **Windows packaging** - `packaging/friday.spec` (PyInstaller folder build with
  hidden imports for every lazily imported dependency),
  `packaging/launcher.py` (redirects data to `%APPDATA%\Friday`, loads `.env`
  beside the exe, holds the window open on error),
  `packaging/runtime_hook.py` (forces UTF-8 stdio so non-Latin scripts print),
  `packaging/build_windows.ps1` (one-command build) and
  `packaging/friday_installer.iss` (Inno Setup installer with Start Menu
  shortcuts per mode, optional autostart, and an uninstall that asks before
  deleting memory).
- **Release workflow** - `.github/workflows/release-windows.yml` builds the exe
  and installer on a Windows runner, on tag push or manual trigger.
- **Documentation** - `docs/LANGUAGES.md` and `docs/WINDOWS.md`.
- **Thirty new tests** - 53 total.

### Changed

- The default Whisper model is now `small` when more than one language is
  enabled, since `.en` models cannot transcribe anything else. English-only
  setups keep `base.en`. Explicit `.en` overrides are widened automatically.
- Sentence splitting understands CJK full-width punctuation and the Indic danda,
  so streamed speech is chunked correctly outside Latin scripts.
- `Speaker.speak()`, `Voice.say()` and `Transcriber.transcribe()` accept an
  optional language; `Transcriber.transcribe_detect()` returns the detected code.

### Known limitations

- Malayalam and Tamil transcription is materially weaker than European
  languages. `FRIDAY_WHISPER_MODEL=medium` helps at the cost of latency.
- No Piper voice exists for Malayalam, Tamil, Korean or Japanese, so those are
  spoken with the system voice. Windows has no Malayalam or Tamil voice at all.
- The installer is unsigned, so SmartScreen warns on first run.

## [1.0.0] - 2026-07-29

First working release. Local ears, local voice, local tools, cloud brain.

### Added

- **Voice pipeline** - continuous 30 ms capture via `sounddevice`, `webrtcvad`
  endpointing with a 300 ms pre-roll buffer so the first syllable survives, and
  a configurable silence tail to end a turn.
- **Wake word** - `openWakeWord` detector with score threshold and cooldown,
  defaulting to the pre-trained `hey_jarvis` model.
- **Speech to text** - `faster-whisper` wrapper, `base.en` on CPU by default,
  CUDA and `float16` supported through configuration alone.
- **Brain** - Gemini 2.5 Flash with automatic function calling, thinking
  disabled for latency, and sentence-level streaming with a non-streaming
  fallback.
- **Speech synthesis** - pluggable backends: Piper (offline neural), pyttsx3
  (system voice), and a null printer for headless machines. `auto` picks the
  best available.
- **Barge protection** - the microphone is muted and drained for the duration of
  every spoken reply, so FRIDAY never transcribes herself.
- **Memory** - SQLite fact store injected into the system prompt at startup,
  plus a full turn log.
- **Thirteen tools** - time, machine status, launch applications, open URLs, web
  search, clipboard read and write, gated shell execution, remember, forget,
  list facts, take note, read notes.
- **Three run modes** - `text` (no hardware), `ptt` (press Enter to talk),
  `wake` (always-on), plus `--say` for single-shot answers.
- **Configuration** - 30+ environment variables, all with working defaults, read
  in exactly one place.
- **`scripts/doctor.py`** - pre-flight check for every dependency, the `piper`
  binary, the API key and the resolved data directory.
- **Documentation** - architecture with a measured latency budget, setup with
  per-platform audio notes and three wake-word paths, full configuration
  reference, tool authoring guide, branching workflow, troubleshooting table,
  and a prior-art survey.
- **Tests** - 23 standard-library unit tests covering configuration, memory,
  the tool registry, shell gating and speech cleanup. No hardware required.
- **CI** - GitHub Actions running the suite on Python 3.10 through 3.12 with
  `ruff` lint and format checks.

### Security

- `run_shell_command` is disabled unless `FRIDAY_ALLOW_SHELL=true`, and logs
  every invocation at `WARNING`.
- `.env`, `*.sqlite3`, `notes.md`, logs and model weights are all git-ignored.

## Unreleased

Candidates for the next increments, each on its own branch:

- A custom "Friday" wake-word model to replace `hey_jarvis`.
- Barge-in: interrupting a reply mid-sentence.
- Calendar and email tools.
- Warming Whisper and TTS in parallel at startup.
