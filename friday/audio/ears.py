"""Microphone capture with voice-activity-detected utterance segmentation.

A single input stream is opened for the lifetime of the process and every 30 ms
frame is pushed onto a queue. Consumers either:

* iterate ``frames()`` continuously (wake-word detection), or
* call ``record_utterance()`` which blocks until speech starts and returns once
  the speaker has been quiet for ``silence_tail_ms``.

The stream can be muted while FRIDAY is speaking so she never transcribes
herself.
"""

from __future__ import annotations

import collections
import contextlib
import logging
import queue
from typing import Iterator

from ..config import AudioSettings

log = logging.getLogger("friday.ears")


class AudioUnavailableError(RuntimeError):
    """Raised when the audio stack cannot be initialised."""


class Ears:
    """Blocking microphone reader with VAD-based endpointing."""

    def __init__(self, settings: AudioSettings) -> None:
        self.settings = settings
        self._queue: queue.Queue[bytes] = queue.Queue()
        self._muted = False
        self._stream = None
        self._vad = None
        self._np = None

    # ------------------------------------------------------------- lifecycle
    def start(self) -> "Ears":
        try:
            import numpy as np
            import sounddevice as sd
            import webrtcvad
        except ImportError as exc:  # pragma: no cover - env dependent
            raise AudioUnavailableError(
                "Audio dependencies missing. Install with: "
                "pip install sounddevice webrtcvad numpy"
            ) from exc

        self._np = np
        self._vad = webrtcvad.Vad(self.settings.vad_aggressiveness)

        try:
            self._stream = sd.InputStream(
                samplerate=self.settings.sample_rate,
                channels=1,
                dtype="int16",
                blocksize=self.settings.frame_len,
                device=self.settings.input_device,
                callback=self._on_audio,
            )
            self._stream.start()
        except Exception as exc:  # pragma: no cover - env dependent
            raise AudioUnavailableError(f"Could not open microphone: {exc}") from exc

        log.info(
            "Microphone open (%d Hz, %d ms frames, VAD %d)",
            self.settings.sample_rate,
            self.settings.frame_ms,
            self.settings.vad_aggressiveness,
        )
        return self

    def close(self) -> None:
        if self._stream is not None:
            with contextlib.suppress(Exception):
                self._stream.stop()
                self._stream.close()
            self._stream = None

    def __enter__(self) -> "Ears":
        return self.start()

    def __exit__(self, *_exc: object) -> None:
        self.close()

    # ---------------------------------------------------------------- muting
    @contextlib.contextmanager
    def muted(self) -> Iterator[None]:
        """Drop incoming audio for the duration of the block."""
        self._muted = True
        try:
            yield
        finally:
            self.drain()
            self._muted = False

    def drain(self) -> None:
        """Discard everything currently buffered."""
        while True:
            try:
                self._queue.get_nowait()
            except queue.Empty:
                return

    # -------------------------------------------------------------- internals
    def _on_audio(self, indata, _frames, _time, status) -> None:
        if status:  # pragma: no cover - hardware dependent
            log.debug("Audio status: %s", status)
        if not self._muted:
            self._queue.put(bytes(indata))

    # ------------------------------------------------------------------- api
    def frames(self) -> Iterator[bytes]:
        """Yield raw 16-bit mono frames forever."""
        while True:
            yield self._queue.get()

    def is_speech(self, frame: bytes) -> bool:
        assert self._vad is not None, "Ears.start() was never called"
        try:
            return self._vad.is_speech(frame, self.settings.sample_rate)
        except Exception:  # pragma: no cover - malformed frame length
            return False

    def record_utterance(self):
        """Block until the user speaks, then return float32 audio in [-1, 1].

        Returns ``None`` when the utterance was too short to be real speech.
        """
        assert self._np is not None, "Ears.start() was never called"
        cfg = self.settings
        preroll = collections.deque(maxlen=max(1, cfg.preroll_ms // cfg.frame_ms))
        voiced: list[bytes] = []
        silence_ms = 0
        total_ms = 0
        started = False

        for frame in self.frames():
            speech = self.is_speech(frame)

            if not started:
                preroll.append(frame)
                if speech:
                    started = True
                    voiced.extend(preroll)
                continue

            voiced.append(frame)
            total_ms += cfg.frame_ms
            silence_ms = 0 if speech else silence_ms + cfg.frame_ms

            if silence_ms >= cfg.silence_tail_ms:
                break
            if total_ms >= cfg.max_utterance_s * 1000:
                log.debug("Utterance hit the %ds ceiling", cfg.max_utterance_s)
                break

        speech_ms = total_ms - silence_ms
        if speech_ms < cfg.min_utterance_ms:
            log.debug("Discarded %d ms blip", speech_ms)
            return None

        pcm = self._np.frombuffer(b"".join(voiced), dtype=self._np.int16)
        return pcm.astype(self._np.float32) / 32768.0
