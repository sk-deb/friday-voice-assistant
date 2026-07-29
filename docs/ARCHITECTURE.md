# Architecture

## Design thesis

A voice assistant has two very different kinds of work:

1. **Reflexes** - capturing audio, deciding when you stopped talking, transcribing, speaking, running commands. These must be fast, must work when the internet does not, and involve raw audio of your home.
2. **Thinking** - understanding intent, choosing tools, composing an answer. This benefits enormously from a frontier model and is not worth self-hosting on a laptop.

FRIDAY puts every reflex on-device and rents only the thinking. One outbound HTTPS call per turn, carrying text, never audio.

---

## Turn lifecycle

```
1. Ears.frames()              30 ms int16 frames, continuous
2. WakeWordDetector.feed()    openWakeWord scores each frame, cooldown-gated
3. Ears.record_utterance()    pre-roll buffer + VAD, ends on 900 ms of silence
4. Transcriber.transcribe()   faster-whisper, float32 mono at 16 kHz
5. Brain.stream()             Gemini turn; SDK executes tool calls locally
6. Voice.say()                each sentence spoken as it arrives, mic muted
7. Memory.log_turn()          owner and assistant turns persisted to SQLite
```

### Why a pre-roll buffer

VAD only reports speech after it has already begun. Without a 300 ms rolling buffer, the first syllable of every command is clipped and Whisper hallucinates a replacement. `Ears` keeps the last 10 frames and prepends them once speech is confirmed.

### Why the microphone is muted while speaking

Without it, FRIDAY transcribes her own reply, treats it as a new command, and loops forever. `Ears.muted()` is a context manager that drops incoming frames and drains the queue on exit, which is both simpler and more reliable than acoustic echo cancellation.

### Why streaming matters more than model choice

Perceived latency is time-to-first-word, not time-to-last-word. `Brain.stream()` emits complete sentences as tokens arrive and `Voice` speaks each one immediately, so the reply starts while the model is still generating. This cuts perceived latency roughly in half for anything longer than one sentence.

---

## Module responsibilities

| Module | Responsibility | Never does |
| --- | --- | --- |
| `config.py` | Own every tunable, read the environment once | Import heavy dependencies |
| `audio/ears.py` | Capture, endpoint, mute | Transcribe or interpret |
| `audio/wake.py` | Score frames, apply cooldown | Record utterances |
| `stt.py` | Audio to text | Post-process meaning |
| `llm.py` | Conversation state, streaming, tool dispatch | Touch audio |
| `tts.py` | Text to sound, backend selection | Decide what to say |
| `tools/` | Side effects on the local machine | Call the model |
| `memory.py` | Durable facts and turn log | Decide what is worth remembering |
| `app.py` | Wire everything, own the run modes | Contain component logic |

Every heavy dependency (`faster_whisper`, `sounddevice`, `openwakeword`, `google.genai`, `pyttsx3`) is imported lazily inside the component that needs it, and each raises a specific `*UnavailableError` with the exact `pip install` line. Consequence: the test suite and `--mode text` run on a machine with no audio stack at all.

---

## Tool execution

Tools are plain Python callables. The google-genai SDK reads type hints and docstrings to build the schema, invokes the function locally, feeds the return value back to the model, and continues the turn. There is no schema boilerplate anywhere in this repository.

Consequences that shape the tool contract:

- Signatures use only `str`, `int`, `bool` - no dataclasses, no unions.
- The docstring **is** the tool description the model reads.
- Return values are short strings meant to be spoken.
- Failures return a sentence, never raise. A raised exception aborts the whole turn.

Stateful tools are produced by factories (`make_shell_tool`, `make_memory_tools`, `make_note_tools`) that close over settings or the memory handle, so the tool bodies stay dependency-free and trivially testable.

---

## Latency budget

Measured on an 8-core laptop CPU, `base.en`, Gemini 2.5 Flash with thinking disabled.

| Stage | Typical | Dominant lever |
| --- | --- | --- |
| Wake word scoring | 10-50 ms | none needed |
| VAD silence tail | 900 ms | `FRIDAY_SILENCE_TAIL_MS`, floor around 500 ms |
| Whisper transcription | 0.6-1.5 s | `tiny.en`, or CUDA with `float16` |
| Gemini first token | 0.4-0.9 s | `thinking_budget=0`, shorter system prompt |
| First spoken word | 0.2-0.4 s | Piper over pyttsx3, sentence streaming |
| **Time to first word** | **~1.8-2.8 s** | |

The silence tail is the largest fixed cost and the cheapest thing to tune. Below roughly 500 ms, natural mid-sentence pauses start cutting you off.

---

## Deliberate non-goals for v1.0

- **No local LLM.** A 7B model on a laptop is slower and markedly worse at tool selection than Flash. Revisit when hardware or small models improve.
- **No barge-in.** Interrupting mid-reply needs a duplex audio path; the mute-while-speaking approach forecloses it. Planned for v1.2.
- **No always-on transcription.** Wake-word gating is what keeps this from being a surveillance device.
- **No GUI.** A terminal is the correct interface for something you talk to.

See [PRIOR_ART.md](PRIOR_ART.md) for the projects that informed these choices.
