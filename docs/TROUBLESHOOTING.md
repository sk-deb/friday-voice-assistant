# Troubleshooting

Always start with:

```bash
python scripts/doctor.py
python -m friday --mode ptt --verbose
tail -f ~/.friday/friday.log
```

---

## It will not start

**`GEMINI_API_KEY is not set`**
Copy `.env.example` to `.env` and add your key. If the file exists but is ignored, `python-dotenv` is probably missing: `pip install python-dotenv`. You can also export the variable in your shell.

**`faster-whisper is not installed`** or a similar `*UnavailableError`
The message contains the exact `pip install` line. Every heavy dependency reports itself this way.

**`No input device found` / `AudioUnavailableError`**
List devices with `python -c "import sounddevice; print(sounddevice.query_devices())"` and set `FRIDAY_INPUT_DEVICE` to a name or index. On macOS, confirm your terminal has microphone permission.

---

## It does not hear me

| Symptom | Cause | Fix |
| --- | --- | --- |
| Wake word never triggers | Threshold too high | Lower `FRIDAY_WAKE_THRESHOLD` toward 0.3 and watch scores with `--verbose` |
| Wake word triggers constantly | Threshold too low, or noise | Raise to 0.6-0.7, raise `FRIDAY_VAD_AGGRESSIVENESS` |
| Recording ends mid-sentence | Silence tail too short | Raise `FRIDAY_SILENCE_TAIL_MS` to 1200 |
| Recording never ends | Constant background noise | Raise `FRIDAY_VAD_AGGRESSIVENESS` to 3 |
| First word always missing | Pre-roll too small | Raise `FRIDAY_PREROLL_MS` to 450 |
| Everything transcribes as silence | Wrong input device or muted hardware | Set `FRIDAY_INPUT_DEVICE`, check OS input level |

---

## Transcription is wrong

- Upgrade the model: `FRIDAY_WHISPER_MODEL=small.en`.
- Raise `FRIDAY_WHISPER_BEAM_SIZE` to 5. Slower, noticeably better.
- Non-English speech needs a multilingual model - drop the `.en` suffix and set `FRIDAY_WHISPER_LANGUAGE`.
- A strong accent that Whisper handles poorly is best fixed by fine-tuning; see [PRIOR_ART.md](PRIOR_ART.md).
- Persistent hallucinated phrases during silence usually mean `FRIDAY_WHISPER_VAD_FILTER` got disabled.

---

## It talks to itself in a loop

This means the mute path is not working. `Friday.say()` wraps speech in `ears.muted()`; if you added a custom speak path, wrap it the same way. Using headphones eliminates the problem entirely.

---

## It is too slow

Check the per-turn timing in the log (`Turn completed in N.NNs`), then attack the largest term:

1. `FRIDAY_SILENCE_TAIL_MS=600` - usually the single biggest win.
2. `FRIDAY_WHISPER_MODEL=tiny.en`, or move to `cuda` with `float16`.
3. Confirm `FRIDAY_THINKING_BUDGET=0`.
4. Confirm `FRIDAY_STREAM=true` - without it nothing is spoken until generation finishes.
5. Switch to Piper; pyttsx3 has a slow cold start on some platforms.

See the latency budget in [ARCHITECTURE.md](ARCHITECTURE.md).

---

## Speech output problems

**Silent, but logs show replies**
`FRIDAY_TTS_ENGINE` may be `none`, or every backend failed and fell back to printing. The log line `No TTS backend available` confirms it.

**`piper binary not found on PATH`**
`pip install piper-tts` inside the same virtualenv, or set `FRIDAY_TTS_ENGINE=pyttsx3`.

**Piper output sounds like static**
`FRIDAY_PIPER_SAMPLE_RATE` does not match the voice. Check the voice's `.onnx.json` card - most medium voices are 22050.

**Linux: pyttsx3 raises on init**
`sudo apt install espeak-ng`.

---

## Model and tool problems

**"My connection to the model failed"**
Network, an invalid key, or rate limiting. The exception type is in the log at DEBUG level.

**A tool is never called**
The docstring is too vague. Make it specific and include an example argument. Verify the tool is in the startup registry log line.

**The wrong tool gets called**
Two descriptions overlap. Sharpen the distinction between them.

**Shell commands are refused**
By design. Set `FRIDAY_ALLOW_SHELL=true` and read the warning in [CONFIGURATION.md](CONFIGURATION.md) first.

---

## Memory problems

**Facts are forgotten between runs**
Check that `~/.friday` is writable and that `FRIDAY_DATA_DIR` is not pointing somewhere temporary.

**A wrong fact keeps resurfacing**
Say "forget \<topic\>", or wipe everything:

```bash
rm ~/.friday/friday.sqlite3
```

Remembered facts are loaded into the system prompt only at startup, so restart after editing them directly.
