"""Microphone recording at 16 kHz mono (what Whisper expects)."""

from __future__ import annotations

import threading

import numpy as np
import sounddevice as sd

SAMPLE_RATE = 16000


class Recorder:
    """Start/stop microphone capture; returns float32 mono at 16 kHz."""

    def __init__(self, device: str = "", max_seconds: int = 120):
        self._device = device or None
        self._max_samples = max_seconds * SAMPLE_RATE
        self._chunks: list[np.ndarray] = []
        self._lock = threading.Lock()
        self._stream: sd.InputStream | None = None

    @property
    def recording(self) -> bool:
        return self._stream is not None

    def start(self) -> None:
        if self._stream is not None:
            return
        self._chunks = []

        def callback(indata, frames, time_info, status):
            with self._lock:
                total = sum(len(c) for c in self._chunks)
                if total < self._max_samples:
                    self._chunks.append(indata[:, 0].copy())

        device = self._device
        if device is not None and device.lstrip("-").isdigit():
            device = int(device)
        self._stream = sd.InputStream(
            samplerate=SAMPLE_RATE,
            channels=1,
            dtype="float32",
            device=device,
            callback=callback,
        )
        self._stream.start()

    def stop(self) -> np.ndarray:
        if self._stream is None:
            return np.zeros(0, dtype=np.float32)
        self._stream.stop()
        self._stream.close()
        self._stream = None
        with self._lock:
            if not self._chunks:
                return np.zeros(0, dtype=np.float32)
            audio = np.concatenate(self._chunks)
            self._chunks = []
        return audio


def duration(audio: np.ndarray) -> float:
    return len(audio) / SAMPLE_RATE


def list_devices() -> str:
    return str(sd.query_devices())
