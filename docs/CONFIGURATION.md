# Configuration reference

Every setting is an environment variable, readable from a local `.env`. `friday/config.py` is the single source of truth; nothing else reads the environment.

## Identity

| Variable | Default | Notes |
| --- | --- | --- |
| `FRIDAY_NAME` | `Friday` | Used in the system prompt and startup announcement |
| `FRIDAY_OWNER` | `Srihari` | Who the assistant works for |
| `FRIDAY_PERSONA` | built-in | Full system prompt template; supports `{name}` and `{owner}` |
| `FRIDAY_DATA_DIR` | `~/.friday` | Database, notes and logs live here |
| `FRIDAY_LOG_LEVEL` | `INFO` | `DEBUG` for scores and timings |
| `FRIDAY_ALLOW_SHELL` | `false` | Arms `run_shell_command`. Read the warning below |

## Language model

| Variable | Default | Notes |
| --- | --- | --- |
| `GEMINI_API_KEY` | *(required)* | From <https://aistudio.google.com/apikey> |
| `FRIDAY_MODEL` | `gemini-2.5-flash` | `gemini-2.5-pro` is smarter and clearly slower |
| `FRIDAY_TEMPERATURE` | `0.7` | Lower for terser, more literal answers |
| `FRIDAY_THINKING_BUDGET` | `0` | Non-zero adds reasoning and 1-3 s of latency |
| `FRIDAY_MAX_OUTPUT_TOKENS` | `512` | Spoken replies should be short anyway |
| `FRIDAY_STREAM` | `true` | Sentence streaming; disable only when debugging |

## Audio capture

| Variable | Default | Notes |
| --- | --- | --- |
| `FRIDAY_SAMPLE_RATE` | `16000` | Whisper and webrtcvad both expect 16 kHz |
| `FRIDAY_FRAME_MS` | `30` | Must be 10, 20 or 30 - a webrtcvad constraint |
| `FRIDAY_SILENCE_TAIL_MS` | `900` | Quiet needed to end a turn. Biggest latency lever |
| `FRIDAY_MAX_UTTERANCE_S` | `20` | Hard ceiling on one command |
| `FRIDAY_MIN_UTTERANCE_MS` | `250` | Shorter bursts are discarded as noise |
| `FRIDAY_VAD_AGGRESSIVENESS` | `2` | 0-3. Raise it in a noisy room |
| `FRIDAY_PREROLL_MS` | `300` | Audio kept before speech is detected |
| `FRIDAY_INPUT_DEVICE` | system default | Name or index; list with `python -c "import sounddevice; print(sounddevice.query_devices())"` |

## Speech to text

| Variable | Default | Notes |
| --- | --- | --- |
| `FRIDAY_WHISPER_MODEL` | `base.en` | `tiny.en` is faster, `small.en` is more accurate |
| `FRIDAY_WHISPER_DEVICE` | `cpu` | `cuda` with an NVIDIA GPU |
| `FRIDAY_WHISPER_COMPUTE_TYPE` | `int8` | `float16` on GPU |
| `FRIDAY_WHISPER_LANGUAGE` | `en` | Use a multilingual model for anything else |
| `FRIDAY_WHISPER_BEAM_SIZE` | `1` | Greedy. Raise for accuracy at a latency cost |
| `FRIDAY_WHISPER_VAD_FILTER` | `true` | Second-pass silence trimming |

## Text to speech

| Variable | Default | Notes |
| --- | --- | --- |
| `FRIDAY_TTS_ENGINE` | `auto` | `auto`, `piper`, `pyttsx3` or `none` |
| `FRIDAY_PIPER_MODEL` | `voices/en_US-amy-medium.onnx` | Path to the `.onnx` voice |
| `FRIDAY_PIPER_SAMPLE_RATE` | `22050` | Must match the voice card |
| `FRIDAY_TTS_RATE` | `185` | pyttsx3 words per minute |
| `FRIDAY_TTS_VOICE` | system default | pyttsx3 voice identifier |

## Wake word

| Variable | Default | Notes |
| --- | --- | --- |
| `FRIDAY_WAKE_MODELS` | `hey_jarvis` | Comma-separated names or `.onnx` paths |
| `FRIDAY_WAKE_THRESHOLD` | `0.5` | Lower is more sensitive |
| `FRIDAY_WAKE_COOLDOWN_S` | `1.5` | Suppresses double triggers |
| `FRIDAY_WAKE_ACKNOWLEDGE` | `true` | Say "Yes?" before listening |

---

## Recommended profiles

**Fastest possible** - accuracy traded for response time.
```env
FRIDAY_WHISPER_MODEL=tiny.en
FRIDAY_SILENCE_TAIL_MS=600
FRIDAY_THINKING_BUDGET=0
FRIDAY_TTS_ENGINE=piper
```

**Most accurate** - for dictation and long commands.
```env
FRIDAY_WHISPER_MODEL=small.en
FRIDAY_WHISPER_BEAM_SIZE=5
FRIDAY_SILENCE_TAIL_MS=1200
FRIDAY_MAX_UTTERANCE_S=45
```

**Noisy room** - fewer false triggers, fewer clipped commands.
```env
FRIDAY_VAD_AGGRESSIVENESS=3
FRIDAY_WAKE_THRESHOLD=0.7
FRIDAY_PREROLL_MS=450
```

---

## A word on `FRIDAY_ALLOW_SHELL`

Enabling it lets the model run arbitrary commands as your user, chosen from your spoken words as transcribed by a speech model. Misheard words become real commands. Keep it off unless you are on a machine you own and are willing to lose. Every invocation is logged at `WARNING` level with the exact command.
