"""Whisper transcription via faster-whisper (CTranslate2, fully local)."""

from __future__ import annotations

import numpy as np

from .config import Config
from .transliterate import cyrillic_to_latin


class Transcriber:
    """Lazy-loading wrapper around faster_whisper.WhisperModel."""

    def __init__(self, cfg: Config):
        self._cfg = cfg
        self._model = None

    def load(self) -> None:
        if self._model is None:
            from faster_whisper import WhisperModel

            self._model = WhisperModel(
                self._cfg.model,
                device=self._cfg.device,
                compute_type=self._cfg.compute_type,
            )

    def transcribe(self, audio: np.ndarray, language: str | None = None) -> str:
        """audio: float32 mono at 16 kHz. Returns cleaned text."""
        if len(audio) == 0:
            return ""
        self.load()
        lang = language or self._cfg.language
        segments, info = self._model.transcribe(
            audio,
            language=None if lang == "auto" else lang,
            vad_filter=True,
            beam_size=5,
        )
        text = " ".join(seg.text.strip() for seg in segments).strip()
        detected = info.language if lang == "auto" else lang
        if detected == "sr" and self._cfg.serbian_latin:
            text = cyrillic_to_latin(text)
        return text

    def transcribe_file(self, path: str, language: str | None = None) -> str:
        self.load()
        lang = language or self._cfg.language
        segments, info = self._model.transcribe(
            path,
            language=None if lang == "auto" else lang,
            vad_filter=True,
            beam_size=5,
        )
        text = " ".join(seg.text.strip() for seg in segments).strip()
        detected = info.language if lang == "auto" else lang
        if detected == "sr" and self._cfg.serbian_latin:
            text = cyrillic_to_latin(text)
        return text
