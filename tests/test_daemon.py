"""Daemon logic tests with recorder/transcriber/delivery stubbed out."""

import numpy as np
import pytest

from flawless.audio import SAMPLE_RATE
from flawless.daemon import Daemon


class FakeRecorder:
    def __init__(self, audio=None):
        self.recording = False
        self._audio = audio if audio is not None else np.zeros(SAMPLE_RATE, np.float32)

    def start(self):
        self.recording = True

    def stop(self):
        self.recording = False
        return self._audio


@pytest.fixture
def daemon(monkeypatch, tmp_path):
    monkeypatch.setenv("XDG_CONFIG_HOME", str(tmp_path))
    d = Daemon.__new__(Daemon)
    import threading

    from flawless.config import Config

    d.cfg = Config(notifications=False)
    d.recorder = FakeRecorder()
    d.transcriber = None
    d._busy = threading.Lock()
    d._stop_event = threading.Event()
    return d


def test_status_idle(daemon):
    assert daemon.handle("STATUS") == "idle"


def test_toggle_starts_recording(daemon):
    assert daemon.handle("TOGGLE") == "recording"
    assert daemon.handle("STATUS") == "recording"


def test_toggle_stop_delivers(daemon, monkeypatch):
    class FakeTranscriber:
        def transcribe(self, audio):
            return "hallo welt"

    daemon.transcriber = FakeTranscriber()
    monkeypatch.setattr("flawless.daemon.deliver", lambda text, mode: "typed")
    daemon.handle("TOGGLE")
    assert daemon.handle("TOGGLE") == "typed: hallo welt"


def test_too_short_recording(daemon):
    daemon.recorder = FakeRecorder(np.zeros(100, np.float32))
    daemon.handle("START")
    assert daemon.handle("STOP") == "too short"


def test_cancel(daemon):
    daemon.handle("START")
    assert daemon.handle("CANCEL") == "cancelled"
    assert daemon.handle("STATUS") == "idle"


def test_lang_switch(daemon):
    assert daemon.handle("LANG sr") == "language set to sr"
    assert daemon.cfg.language == "sr"


def test_lang_invalid(daemon):
    assert daemon.handle("LANG fr").startswith("error")


def test_unknown_command(daemon):
    assert daemon.handle("DANCE").startswith("unknown command")
