"""Unix-socket IPC between the daemon and the `flawless toggle/...` client."""

from __future__ import annotations

import os
import socket
from pathlib import Path


def socket_path() -> Path:
    runtime = os.environ.get("XDG_RUNTIME_DIR", f"/tmp/flawless-{os.getuid()}")
    return Path(runtime) / "flawless.sock"


def send_command(command: str, timeout: float = 300.0) -> str:
    """Send one command to the daemon, return its reply line.

    Long timeout: a STOP command waits for transcription to finish
    (first call may also download / load the model).
    """
    path = socket_path()
    if not path.exists():
        raise ConnectionError(
            f"daemon not running (no socket at {path}); start it with: flawless daemon"
        )
    with socket.socket(socket.AF_UNIX, socket.SOCK_STREAM) as s:
        s.settimeout(timeout)
        s.connect(str(path))
        s.sendall(command.encode() + b"\n")
        data = b""
        while not data.endswith(b"\n"):
            chunk = s.recv(4096)
            if not chunk:
                break
            data += chunk
    return data.decode().strip()
