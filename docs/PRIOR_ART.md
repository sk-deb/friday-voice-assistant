# Prior art

Before writing any code, existing open-source "Jarvis" assistants were surveyed to find out what actually works in practice and where people lose weeks. This document records what was examined, what was taken, and what was deliberately rejected.

---

## Projects surveyed

### isair/jarvis
<https://github.com/isair/jarvis> - the most mature of the lot: ~1,450 stars, 435 commits, a real installer and an evaluation suite.

**Taken:** the evidence that a fully local pipeline is viable; the pattern of a persistent memory store feeding the prompt; tool-calling as the core interaction model rather than intent parsing.
**Rejected:** full local inference. On a laptop a small local model is both slower and clearly worse at choosing tools than Gemini Flash. FRIDAY keeps everything local *except* the model.

### Reezxy/Jarvis---Local-Voice-assistant
<https://github.com/Reezxy/Jarvis---Local-Voice-assistant> - fully offline macOS assistant, GGUF weights plus Whisper, zero API keys.

**Taken:** the pattern of resolving models through a local cache so first run downloads and later runs are instant.
**Rejected:** macOS-only assumptions in the audio layer.

### InterGenJLU/jarvis
<https://github.com/InterGenJLU/jarvis> - GPU-focused, AMD ROCm, a fine-tuned Whisper and Kokoro TTS.

**Taken:** two hard-won facts. First, PyTorch and CTranslate2 can be made to coexist but the install order matters, which is why `requirements.txt` here is deliberately conservative. Second, fine-tuning Whisper on your own accent beats every prompt-level workaround - the right answer for a strong regional accent.

### dscripka/openWakeWord
<https://github.com/dscripka/openWakeWord> - the wake-word framework FRIDAY uses. Ships `hey_jarvis`, `alexa`, `hey_mycroft`.

**Taken:** the whole wake stage. Free, offline, ONNX, ~10 ms per frame.
**Caveat found in the wild:** the official Colab training notebook has been broken for a while. A working local path is to synthesise training samples with a TTS model, train locally and export `.onnx`. Alternatively Picovoice Porcupine gives a custom phrase in five minutes on a free personal tier. Both routes are documented in [SETUP.md](SETUP.md).

### Others reviewed briefly

| Project | Takeaway |
| --- | --- |
| <https://github.com/ggml-org/whisper.cpp> | The fastest CPU route if Python overhead ever becomes the bottleneck |
| <https://github.com/cjpais/Handy> | Push-to-talk done well; validated shipping `ptt` as the default mode |
| <https://github.com/Eduardovasquezn/ai-voice-assistant> | Clean minimal loop, but no wake word or memory |
| <https://github.com/jim-schwoebel/nala_assistant> | Broad skill surface; a caution against scope creep |
| <https://github.com/Staceadam/voice-assistant-example> | Useful as the simplest possible reference implementation |

---

## What every project got wrong that FRIDAY fixes

**1. Clipped first syllables.** Almost every simple implementation starts recording only after VAD confirms speech, losing the first 200-300 ms. FRIDAY keeps a 300 ms rolling pre-roll buffer and prepends it.

**2. Hearing itself.** Several projects loop forever because the assistant transcribes its own reply. FRIDAY mutes the input stream for the duration of each spoken sentence and drains the queue afterwards.

**3. Speaking only after full generation.** Waiting for the complete reply doubles perceived latency. FRIDAY streams sentences and speaks the first one while the rest is still generating.

**4. Hard crashes on missing dependencies.** An `ImportError` at import time on a machine without a microphone makes a project untestable. Every heavy dependency here is imported lazily and raises a specific error containing the exact install command - which is why `--mode text` and the full test suite run on a bare machine.

**5. An armed shell tool by default.** Letting a speech model run arbitrary commands out of the box is a genuinely bad idea. `run_shell_command` is present, disarmed, and logs every invocation at `WARNING`.

---

## Licensing note

No code was copied from any of these projects. What was taken was architectural knowledge and a list of failure modes. FRIDAY is an independent MIT-licensed implementation.
