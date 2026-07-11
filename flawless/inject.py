"""Deliver transcribed text to the focused application.

Preference order (output = "auto"):
  1. ydotool type   (works everywhere if ydotoold is running)
  2. wtype          (wlroots compositors)
  3. xdotool type   (X11 sessions only)
  4. clipboard      (wl-copy / xclip) + notification to press Ctrl+V
"""

from __future__ import annotations

import os
import shutil
import subprocess


class InjectError(RuntimeError):
    pass


def _run(cmd: list[str], input_text: str | None = None) -> bool:
    env = os.environ.copy()
    # Fedora runs ydotoold as a system service; its socket lives in /tmp.
    env.setdefault("YDOTOOL_SOCKET", "/tmp/.ydotool_socket")
    try:
        proc = subprocess.run(
            cmd,
            input=input_text.encode() if input_text is not None else None,
            capture_output=True,
            timeout=15,
            env=env,
        )
        return proc.returncode == 0
    except (OSError, subprocess.TimeoutExpired):
        return False


def _is_wayland() -> bool:
    return os.environ.get("XDG_SESSION_TYPE", "").lower() == "wayland" or bool(
        os.environ.get("WAYLAND_DISPLAY")
    )


def available_typers() -> list[str]:
    tools = []
    if shutil.which("ydotool"):
        tools.append("ydotool")
    if shutil.which("wtype") and _is_wayland():
        tools.append("wtype")
    if shutil.which("xdotool") and not _is_wayland():
        tools.append("xdotool")
    return tools


def type_text(text: str) -> bool:
    """Try to type text directly into the focused window."""
    for tool in available_typers():
        if tool == "ydotool" and _run(["ydotool", "type", "--", text]):
            return True
        if tool == "wtype" and _run(["wtype", "--", text]):
            return True
        if tool == "xdotool" and _run(
            ["xdotool", "type", "--clearmodifiers", "--", text]
        ):
            return True
    return False


def copy_to_clipboard(text: str) -> bool:
    if shutil.which("wl-copy") and _run(["wl-copy"], input_text=text):
        return True
    if shutil.which("xclip") and _run(
        ["xclip", "-selection", "clipboard"], input_text=text
    ):
        return True
    return False


def deliver(text: str, mode: str = "auto") -> str:
    """Deliver text; returns how it was delivered: 'typed' or 'clipboard'.

    Raises InjectError when nothing worked.
    """
    if not text:
        raise InjectError("nothing to deliver (empty transcription)")
    if mode in ("auto", "type") and type_text(text):
        return "typed"
    if mode == "type":
        raise InjectError(
            "no typing tool worked; install ydotool (and enable ydotoold) or wtype"
        )
    if copy_to_clipboard(text):
        return "clipboard"
    raise InjectError("could not type or copy — install ydotool, wtype, or wl-clipboard")
