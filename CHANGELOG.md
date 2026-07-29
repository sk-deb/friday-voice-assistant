# Changelog

All notable changes to FRIDAY are recorded here. The format follows
[Keep a Changelog](https://keepachangelog.com/en/1.1.0/) and versions follow
[Semantic Versioning](https://semver.org/spec/v2.0.0.html).

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
