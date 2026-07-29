# Setup

## 1. Requirements

- Python 3.10 or newer
- A microphone and speakers
- A Gemini API key (free tier is sufficient) from <https://aistudio.google.com/apikey>
- Roughly 1 GB of disk for the Whisper and wake-word models

## 2. Install

```bash
git clone https://github.com/sk-deb/friday-voice-assistant.git
cd friday-voice-assistant

python3 -m venv .venv
source .venv/bin/activate        # Windows: .venv\Scripts\activate

pip install -r requirements.txt
```

### Platform audio notes

**macOS**
```bash
brew install portaudio
```
Grant microphone permission to your terminal in System Settings, Privacy and Security, Microphone. Without it the stream opens and returns silence forever.

**Debian / Ubuntu**
```bash
sudo apt install portaudio19-dev python3-dev espeak-ng ffmpeg
```
`espeak-ng` is what pyttsx3 drives on Linux.

**Windows**

No extra system packages. If `webrtcvad` fails to build, install the prebuilt wheel:
```bash
pip install webrtcvad-wheels
```

## 3. Configure

```bash
cp .env.example .env
```

Edit `.env` and set at minimum:

```env
GEMINI_API_KEY=your-key-here
FRIDAY_OWNER=Srihari
```

Every other variable has a working default. See [CONFIGURATION.md](CONFIGURATION.md).

## 4. Verify

```bash
python scripts/doctor.py
```

This checks each required import, each optional import, the `piper` binary, your API key and the resolved data directory. Fix anything marked `MISSING` before continuing.

## 5. First run

Start with the mode that has the fewest moving parts and work upward:

```bash
python -m friday --mode text   # brain and tools only
python -m friday --mode ptt    # adds microphone, Whisper and TTS
python -m friday --mode wake   # adds always-on wake word
```

The first `ptt` run downloads the Whisper model; expect a delay of a minute or two.

---

## Better voice: Piper

pyttsx3 works everywhere and sounds like a 2009 satnav. Piper is offline, neural and dramatically better.

```bash
pip install piper-tts
mkdir -p voices && cd voices

# Any voice from https://huggingface.co/rhasspy/piper-voices
curl -LO https://huggingface.co/rhasspy/piper-voices/resolve/main/en/en_US/amy/medium/en_US-amy-medium.onnx
curl -LO https://huggingface.co/rhasspy/piper-voices/resolve/main/en/en_US/amy/medium/en_US-amy-medium.onnx.json
```

```env
FRIDAY_TTS_ENGINE=piper
FRIDAY_PIPER_MODEL=voices/en_US-amy-medium.onnx
```

With `FRIDAY_TTS_ENGINE=auto` (the default) FRIDAY tries Piper first and silently falls back to pyttsx3 if the binary or voice file is missing.

---

## Making the wake word actually be "Friday"

openWakeWord ships pre-trained models for `hey_jarvis`, `alexa` and `hey_mycroft`. There is no Friday model, so pick one of three paths.

**A. Ship with `hey_jarvis` (zero effort).** The default. Good enough while you build.

**B. Train a custom model (about an hour, free).** Use openWakeWord's automatic training notebook: <https://github.com/dscripka/openWakeWord>. It synthesises thousands of samples of your phrase with TTS, trains, and exports an `.onnx`. Mixing in 30-50 recordings of your own voice raises real-world accuracy noticeably. Then:

```env
FRIDAY_WAKE_MODELS=/absolute/path/to/friday.onnx
```

**C. Picovoice Porcupine (five minutes, free personal tier).** Type any phrase in the console, download the model. Requires swapping `friday/audio/wake.py` for the Porcupine SDK - the `WakeWordDetector` interface is two methods (`load`, `feed`) precisely so this stays a small change.

### Tuning sensitivity

```env
FRIDAY_WAKE_THRESHOLD=0.5     # lower = more sensitive, more false triggers
FRIDAY_WAKE_COOLDOWN_S=1.5    # minimum gap between triggers
```

Run with `--verbose` to watch scores and pick a threshold just above your ambient noise floor.

---

## Optional: GPU acceleration

With an NVIDIA GPU and CUDA-enabled CTranslate2:

```env
FRIDAY_WHISPER_DEVICE=cuda
FRIDAY_WHISPER_COMPUTE_TYPE=float16
FRIDAY_WHISPER_MODEL=small.en
```

That typically takes transcription from ~1.2 s to under 200 ms while also improving accuracy.

---

## Optional: run at login

**macOS** - create `~/Library/LaunchAgents/com.friday.assistant.plist` with a `ProgramArguments` array invoking `.venv/bin/python -m friday --mode wake`, then `launchctl load` it.

**Linux (systemd user unit)** - `~/.config/systemd/user/friday.service`:

```ini
[Unit]
Description=FRIDAY voice assistant

[Service]
ExecStart=%h/friday-voice-assistant/.venv/bin/python -m friday --mode wake
WorkingDirectory=%h/friday-voice-assistant
Restart=on-failure

[Install]
WantedBy=default.target
```

```bash
systemctl --user enable --now friday
journalctl --user -u friday -f
```
