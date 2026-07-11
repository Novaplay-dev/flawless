"""Desktop notifications via notify-send, silent no-op if unavailable."""

from __future__ import annotations

import shutil
import subprocess

_APP = "Flawless"


def notify(summary: str, body: str = "", urgency: str = "normal") -> None:
    if not shutil.which("notify-send"):
        return
    try:
        subprocess.run(
            [
                "notify-send",
                "--app-name", _APP,
                "--urgency", urgency,
                "--expire-time", "4000",
                "--hint", "string:x-canonical-private-synchronous:flawless",
                summary,
                body,
            ],
            capture_output=True,
            timeout=5,
        )
    except (OSError, subprocess.TimeoutExpired):
        pass
