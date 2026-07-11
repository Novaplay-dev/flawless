"""Flawless daemon: owns the microphone, the model, and the unix socket.

Commands (one line per connection):
  TOGGLE          start recording, or stop + transcribe + deliver
  START           start recording
  STOP            stop recording, transcribe, deliver
  CANCEL          stop recording, discard audio
  STATUS          -> "idle" | "recording"
  LANG <code>     switch language (en|de|sr|auto) for this session + config
  QUIT            shut the daemon down
"""

from __future__ import annotations

import os
import signal
import socket
import sys
import threading

from . import SUPPORTED_LANGUAGES
from .audio import Recorder, duration
from .config import load, save
from .inject import InjectError, deliver
from .ipc import socket_path
from .notify import notify
from .transcriber import Transcriber


class Daemon:
    def __init__(self):
        self.cfg = load()
        self.recorder = Recorder(self.cfg.input_device, self.cfg.max_seconds)
        self.transcriber = Transcriber(self.cfg)
        self._busy = threading.Lock()  # serialize toggle/stop handling
        self._stop_event = threading.Event()

    # ---- notifications ------------------------------------------------
    def _notify(self, summary: str, body: str = "", urgency: str = "normal"):
        if self.cfg.notifications:
            notify(summary, body, urgency)

    # ---- command handlers ---------------------------------------------
    def handle(self, command: str) -> str:
        cmd, _, arg = command.strip().partition(" ")
        cmd = cmd.upper()
        if cmd == "STATUS":
            return "recording" if self.recorder.recording else "idle"
        if cmd == "TOGGLE":
            return self._stop_and_transcribe() if self.recorder.recording else self._start()
        if cmd == "START":
            return self._start() if not self.recorder.recording else "already recording"
        if cmd == "STOP":
            return self._stop_and_transcribe() if self.recorder.recording else "not recording"
        if cmd == "CANCEL":
            if self.recorder.recording:
                self.recorder.stop()
                self._notify("Recording cancelled", urgency="low")
                return "cancelled"
            return "not recording"
        if cmd == "LANG":
            return self._set_language(arg.strip().lower())
        if cmd == "QUIT":
            self._stop_event.set()
            return "bye"
        return f"unknown command: {cmd}"

    def _start(self) -> str:
        with self._busy:
            try:
                self.recorder.start()
            except Exception as e:  # no mic, portaudio error, ...
                self._notify("Microphone error", str(e), urgency="critical")
                return f"error: {e}"
            lang = SUPPORTED_LANGUAGES.get(self.cfg.language, self.cfg.language)
            self._notify("Recording…", f"Language: {lang}. Toggle again to stop.")
            return "recording"

    def _stop_and_transcribe(self) -> str:
        with self._busy:
            audio = self.recorder.stop()
            if duration(audio) < 0.3:
                self._notify("Too short", "No speech captured.", urgency="low")
                return "too short"
            self._notify("Transcribing…", f"{duration(audio):.1f}s of audio")
            try:
                text = self.transcriber.transcribe(audio)
            except Exception as e:
                self._notify("Transcription failed", str(e), urgency="critical")
                return f"error: {e}"
            if not text:
                self._notify("No speech detected", urgency="low")
                return "empty"
            try:
                how = deliver(text, self.cfg.output)
            except InjectError as e:
                self._notify("Delivery failed", str(e), urgency="critical")
                return f"error: {e}"
            preview = text if len(text) <= 80 else text[:77] + "…"
            if how == "clipboard":
                self._notify("Copied — press Ctrl+V", preview)
            else:
                self._notify("Typed", preview, urgency="low")
            return f"{how}: {text}"

    def _set_language(self, lang: str) -> str:
        if lang not in SUPPORTED_LANGUAGES:
            return f"error: language must be one of {', '.join(SUPPORTED_LANGUAGES)}"
        self.cfg.language = lang
        save(self.cfg)
        self._notify("Language switched", SUPPORTED_LANGUAGES[lang])
        return f"language set to {lang}"

    # ---- socket loop ----------------------------------------------------
    def run(self, preload: bool = True) -> int:
        path = socket_path()
        path.parent.mkdir(parents=True, exist_ok=True)
        if path.exists():
            # Is another daemon alive on it?
            probe = socket.socket(socket.AF_UNIX, socket.SOCK_STREAM)
            try:
                probe.settimeout(2)
                probe.connect(str(path))
                probe.sendall(b"STATUS\n")
                if probe.recv(64):
                    print("flawless daemon already running", file=sys.stderr)
                    return 1
            except OSError:
                path.unlink()  # stale socket
            finally:
                probe.close()

        if preload:
            threading.Thread(target=self._preload, daemon=True).start()

        server = socket.socket(socket.AF_UNIX, socket.SOCK_STREAM)
        server.bind(str(path))
        os.chmod(path, 0o600)
        server.listen(4)
        server.settimeout(1.0)

        for sig in (signal.SIGINT, signal.SIGTERM):
            signal.signal(sig, lambda *_: self._stop_event.set())

        print(f"flawless daemon listening on {path}")
        try:
            while not self._stop_event.is_set():
                try:
                    conn, _ = server.accept()
                except socket.timeout:
                    continue
                threading.Thread(
                    target=self._serve_client, args=(conn,), daemon=True
                ).start()
        finally:
            server.close()
            path.unlink(missing_ok=True)
            if self.recorder.recording:
                self.recorder.stop()
        print("flawless daemon stopped")
        return 0

    def _preload(self):
        try:
            self.transcriber.load()
            print(f"model '{self.cfg.model}' loaded")
        except Exception as e:
            print(f"model preload failed: {e}", file=sys.stderr)
            self._notify("Model load failed", str(e), urgency="critical")

    def _serve_client(self, conn: socket.socket):
        with conn:
            try:
                conn.settimeout(600)
                data = b""
                while not data.endswith(b"\n"):
                    chunk = conn.recv(4096)
                    if not chunk:
                        return
                    data += chunk
                reply = self.handle(data.decode())
                conn.sendall(reply.encode() + b"\n")
            except OSError:
                pass
